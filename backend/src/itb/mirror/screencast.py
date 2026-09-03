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

    async def _forward(self, params: dict[str, Any]) -> None:
        metadata = params.get("metadata") or {}
        await self._emit(
            "mirror_frame",
            tab=self._tab_index,
            data=params.get("data", ""),
            width=int(metadata.get("deviceWidth") or MAX_WIDTH),
            height=int(metadata.get("deviceHeight") or MAX_HEIGHT),
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
        import base64

        while self._running:
            try:
                shot = await self._page.screenshot(type="jpeg", quality=QUALITY, timeout=3000)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - 화면이 닫혔거나 이동 중이다
                await asyncio.sleep(FALLBACK_INTERVAL_S)
                continue
            await self._emit(
                "mirror_frame",
                tab=self._tab_index,
                data=base64.b64encode(shot).decode("ascii"),
                width=MAX_WIDTH,
                height=MAX_HEIGHT,
            )
            await asyncio.sleep(FALLBACK_INTERVAL_S)
