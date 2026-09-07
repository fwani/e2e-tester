"""읽기 전용 미러. CDP `Page.startScreencast` (research R3, FR-047).

**이 모듈은 CDP `Input` 도메인을 임포트하지도 호출하지도 않는다** (FR-047a). 미러가 조작
경로를 갖지 않는다는 요구사항을 주석이 아니라 코드 구조로 지킨다 — 여기서 보내는 CDP 명령은
아래 `_ALLOWED_COMMANDS` 에 열거된 것뿐이고, 그 목록을 벗어난 전송은 함수 자체가 거절한다.

**전용 CDP 세션을 쓴다.** 러너가 쓰는 `Page` 객체의 API를 경유하지 않으므로 미러가 러너의
명령과 경쟁하지 않는다. 이 분리가 FR-047b(미러가 끊겨도 실행 무영향)를 구조로 만든다.

**끊김은 백프레셔로 처리된다.** ack 를 멈추면 3프레임 뒤 자연히 정지하고 예외가 나지 않는다
(T006 실측). 그래서 전송 실패 시 특별한 처리를 하지 않는다 — ack 만 멈춘다.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

from playwright.async_api import CDPSession, Page

FORMAT = "jpeg"
QUALITY = 60
MAX_WIDTH = 1280
MAX_HEIGHT = 800
EVERY_NTH_FRAME = 1
"""T006 실측에서 5~10 fps · 약 17 KB/프레임을 낸 설정 (research R3·R8)."""

FALLBACK_INTERVAL_S = 1.0
"""스크린캐스트를 시작할 수 없을 때의 강등 주기. 1 fps (research R3 폴백)."""

IDLE_INTERVAL_S = 2.0
"""무프레임 감시 주기 (005 FR-160).

**CDP `Page.startScreencast` 는 화면이 변할 때만 프레임을 만든다.** 정적 화면에서는 시작
직후 한 장이 전부이고 그 뒤로는 아무것도 오지 않는다 — 실측으로 확인했다(구독 후 정적 화면
5초에 0건, 화면을 한 번 바꾸면 1건, 계속 변하면 약 10 fps).

그래서 마지막 프레임 후 이 시간이 지나면 스크린샷 한 장을 같은 이벤트로 보낸다. 대상 앱을
막 열었을 때와 오래 기다리는 Step 에서 미러가 비던 것이 이것으로 잡힌다 — 정확히 사용자가
화면을 가장 보고 싶은 두 순간이다 (U-24).

강등(1 fps)보다 느린 주기다. 강등은 스크린캐스트를 **못 쓰는** 경우이고 이것은 잘 쓰고
있지만 화면이 조용한 경우다.
"""

_ALLOWED_COMMANDS = frozenset(
    {"Page.startScreencast", "Page.stopScreencast", "Page.screencastFrameAck"}
)
"""미러가 보낼 수 있는 CDP 명령 전체. `Input.*` 은 여기 없다 (FR-047a).

목록으로 두는 이유는 나중에 "잠깐 클릭 하나만" 이 들어오는 것을 막기 위해서다.
"""


class MirrorInputForbiddenError(RuntimeError):
    """미러가 조작 명령을 보내려 했다. FR-047a 위반이므로 실행 시점에 막는다."""


async def _send(cdp: CDPSession, command: str, params: dict[str, Any] | None = None) -> None:
    if command not in _ALLOWED_COMMANDS:
        msg = (
            f"미러는 {command} 를 보낼 수 없습니다. 읽기 전용 표시 영역은 대상 브라우저로 "
            "입력을 전달하지 않습니다 (FR-047a)."
        )
        raise MirrorInputForbiddenError(msg)
    await cdp.send(command, params or {})


class TabScreencast:
    """탭 하나의 스크린캐스트. 한 번에 한 탭만 돌린다 (research R3).

    프레임은 주입받은 `emit` 으로 나간다 — 이 클래스는 WebSocket 을 모른다. 그래서 미러
    전송 실패가 이 클래스의 관심사가 아니게 되고, 실행 경로와 완전히 분리된다.
    """

    def __init__(self, page: Page, tab_index: int, emit: Any) -> None:
        self._page = page
        self._tab_index = tab_index
        self._emit = emit
        self._cdp: CDPSession | None = None
        self._acking = True
        self._degraded_task: asyncio.Task[None] | None = None
        self._running = False
        self._last_frame: dict[str, object] | None = None
        """마지막으로 보낸 프레임 (005 FR-162).

        **구독이 뒤늦게 붙어도 현재 화면을 줄 수 있게** 들고 있는다. 이전에는 유일한 초기
        프레임이 `POST /api/sessions` 안에서 발행되고, 프론트의 WebSocket 은 그 응답을
        받은 뒤에 붙었다. 구독자가 없는 동안 허브가 조용히 버렸으므로 정적 화면에서는
        한 장도 도달하지 않았다 (U-24).

        한 장만 들고 있는다 — 계약이 이미 "유실 가능 · 마지막 프레임만 그리면 된다" 이므로
        버퍼를 쌓을 이유가 없다.
        """
        self._idle_task: asyncio.Task[None] | None = None
        self._last_sent_at: float = 0.0

    @property
    def tab_index(self) -> int:
        return self._tab_index

    @property
    def running(self) -> bool:
        return self._running

    @property
    def degraded(self) -> bool:
        return self._degraded_task is not None

    # ─── 시작·정지 ─────────────────────────────────────────────────────────

    async def start(self) -> bool:
        """스크린캐스트를 시작한다. 시작하지 못하면 1fps 스크린샷으로 강등한다.

        돌려주는 값은 **강등 없이** 시작했는지 여부다.
        """
        if self._running:
            return not self.degraded
        self._running = True
        try:
            self._cdp = await self._page.context.new_cdp_session(self._page)
            self._cdp.on("Page.screencastFrame", self._on_frame)
            await _send(
                self._cdp,
                "Page.startScreencast",
                {
                    "format": FORMAT,
                    "quality": QUALITY,
                    "maxWidth": MAX_WIDTH,
                    "maxHeight": MAX_HEIGHT,
                    "everyNthFrame": EVERY_NTH_FRAME,
                },
            )
            # 005 FR-161 — **첫 프레임을 기다리지 않는다.**
            #
            # 스크린캐스트는 화면이 변할 때만 프레임을 만들고, 그 초기 한 장은 구독자가
            # 붙기 전에 발행되어 버려진다. 그래서 시작 직후 한 장을 직접 찍어 캐시에
            # 넣어 둔다 — 구독이 뒤늦게 붙어도 그 장을 받는다.
            #
            # 실패해도 무시한다. 감시 루프가 곧 다시 시도한다.
            with contextlib.suppress(Exception):
                await self._shoot_once()
            self._idle_task = asyncio.create_task(self._idle_loop())
            return True
        except MirrorInputForbiddenError:
            raise
        except Exception as exc:  # noqa: BLE001 - CDP 를 못 쓰는 환경도 있다
            self._cdp = None
            await self._emit(
                "mirror_degraded",
                mode="screenshot",
                reason=(
                    "스크린캐스트를 시작할 수 없어 1초에 한 장으로 표시합니다. "
                    f"({type(exc).__name__})"
                ),
            )
            # 005 FR-161 — 강등 경로도 **첫 장을 즉시 보장한다.**
            #
            # 루프에 맡기면 첫 프레임이 다음 이벤트 루프 차례로 밀린다. 정상 경로와
            # 강등 경로가 첫 프레임 보장에서 달라지면, 강등된 환경에서만 미리보기가
            # 늦게 뜨는 차이가 생기고 그것은 재현하기 어려운 결함이 된다.
            with contextlib.suppress(Exception):
                await self._shoot_once()
            self._degraded_task = asyncio.create_task(self._screenshot_loop())
            return False

    async def stop(self, reason: str | None = None) -> None:
        """정지한다. 실행에는 영향을 주지 않는다 (FR-047b)."""
        if not self._running:
            return
        self._running = False
        self._acking = False

        if self._degraded_task is not None:
            self._degraded_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._degraded_task
            self._degraded_task = None

        if self._idle_task is not None:
            self._idle_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._idle_task
            self._idle_task = None

        if self._cdp is not None:
            with contextlib.suppress(Exception):
                await _send(self._cdp, "Page.stopScreencast")
            with contextlib.suppress(Exception):
                await self._cdp.detach()
            self._cdp = None

        if reason is not None:
            await self._emit("mirror_stopped", reason=reason)

    def pause_acking(self) -> None:
        """ack 를 멈춘다. WebSocket 이 끊긴 경우의 정지 수단이다 (FR-047b).

        CDP 는 ack 가 없으면 몇 프레임 뒤 스스로 밀기를 멈춘다 — 예외도 나지 않는다.
        """
        self._acking = False

    # ─── 프레임 ────────────────────────────────────────────────────────────

    def _on_frame(self, params: dict[str, Any]) -> None:
        """CDP 이벤트 핸들러. 동기 호출이라 태스크로 넘긴다."""
        with contextlib.suppress(RuntimeError):
            asyncio.create_task(self._forward(params))  # noqa: RUF006

    async def _send_frame(self, data: str, width: int, height: int) -> None:
        """프레임 하나를 보내고 **마지막 프레임으로 기억한다** (005 FR-162).

        전송 경로를 한 곳으로 모으는 이유는 캐시가 빠지는 경로를 만들지 않기 위해서다 —
        스크린캐스트·강등 루프·무프레임 감시 셋이 모두 여기를 지난다.
        """
        payload: dict[str, object] = {
            "tab": self._tab_index,
            "data": data,
            "width": width,
            "height": height,
        }
        self._last_frame = payload
        self._last_sent_at = time.monotonic()
        await self._emit("mirror_frame", **payload)

    def last_frame(self) -> dict[str, object] | None:
        """구독이 붙을 때 보낼 마지막 프레임. 아직 한 장도 없으면 `None` (005 FR-162)."""
        return self._last_frame

    async def _forward(self, params: dict[str, Any]) -> None:
        metadata = params.get("metadata") or {}
        await self._send_frame(
            params.get("data", ""),
            int(metadata.get("deviceWidth") or MAX_WIDTH),
            int(metadata.get("deviceHeight") or MAX_HEIGHT),
        )
        if not self._acking or self._cdp is None:
            return
        with contextlib.suppress(Exception):
            await _send(
                self._cdp,
                "Page.screencastFrameAck",
                {"sessionId": params["sessionId"]},
            )

    async def _screenshot_loop(self) -> None:
        """강등 경로. 1초에 한 장씩 찍어 같은 이벤트로 보낸다."""
        while self._running:
            if not await self._shoot_once():
                await asyncio.sleep(FALLBACK_INTERVAL_S)
                continue
            await asyncio.sleep(FALLBACK_INTERVAL_S)

    async def _idle_loop(self) -> None:
        """무프레임 감시 (005 FR-160).

        스크린캐스트가 정상인데 **화면이 조용한** 구간을 메운다. 마지막 프레임 후
        `IDLE_INTERVAL_S` 가 지났으면 한 장 찍어 보낸다.

        **강등이 아니다** — `mirror_degraded` 를 발행하지 않는다. 강등 배너를 띄우면
        사용자는 문제가 있다고 읽는데, 이것은 정상 동작의 보완이다.

        **예외를 삼킨다.** 미러가 실행에 영향을 주지 않는다는 성질(FR-047b)을 이 루프가
        깨서는 안 된다.
        """
        while self._running:
            await asyncio.sleep(IDLE_INTERVAL_S / 2)
            if not self._running or self.degraded:
                continue
            quiet_for = time.monotonic() - self._last_sent_at
            if quiet_for < IDLE_INTERVAL_S:
                continue
            try:
                await self._shoot_once()
            except asyncio.CancelledError:
                raise
            # BLE001·S112 — 미러 실패는 실행에 영향을 주지 않는다 (FR-047b). 사유를
            # 남기지 않는 것도 의도다: 찍히지 않는 화면은 매 주기 같은 예외를 내므로
            # 로그를 채워 정작 봐야 할 실행 로그를 밀어낸다.
            except Exception:  # noqa: BLE001, S112
                continue

    async def _shoot_once(self) -> bool:
        """현재 화면을 한 장 찍어 보낸다. 보냈으면 True.

        **Playwright `page.screenshot` 을 쓴다** — CDP 가 아니다. 그래서 미러의 허용 CDP
        명령 목록(`_ALLOWED_COMMANDS`)에 아무것도 추가되지 않는다 (FR-047a).
        """
        import base64

        try:
            shot = await self._page.screenshot(type="jpeg", quality=QUALITY, timeout=3000)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - 화면이 닫혔거나 이동 중이다
            return False
        await self._send_frame(
            base64.b64encode(shot).decode("ascii"), MAX_WIDTH, MAX_HEIGHT
        )
        return True
