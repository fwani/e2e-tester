"""읽기 전용 미러. CDP `Page.startScreencast` (research R3, FR-047).

**이 모듈은 CDP `Input` 도메인을 임포트하지도 호출하지도 않는다.** 여기서 보내는 CDP
명령은 아래 `_ALLOWED_COMMANDS` 에 열거된 것뿐이고, 그 목록을 벗어난 전송은 함수 자체가
거절한다.

**010 이 미러 조작을 열었지만 이 성질은 그대로다** (research R5). 010 이 뒤집은 것은
「미러가 조작 경로를 갖지 않는다」가 아니라 「조작 경로가 아예 없다」다. 조작은
`mirror/input.py` 가 **자기 CDP 세션과 자기 명령 목록**으로 담당하고, 이 파일은 프레임만
다루는 모듈로 남는다. 목록도 그대로 둔다 — 여기서 조작 명령을 보내려는 시도는 계속
거부되어야 한다. 두 모듈이 서로를 임포트하지 않는 것이 FR-336(조작과 프레임이 서로를
막지 않는다)을 파일 경계로 만든다. `tests/unit/test_mirror_input.py` 가 이것을 고정한다.

**전용 CDP 세션을 쓴다.** 러너가 쓰는 `Page` 객체의 API를 경유하지 않으므로 미러가 러너의
명령과 경쟁하지 않는다. 이 분리가 FR-047b(미러가 끊겨도 실행 무영향)를 구조로 만든다.

**끊김은 백프레셔로 처리된다.** ack 를 멈추면 3프레임 뒤 자연히 정지하고 예외가 나지 않는다
(T006 실측). 그래서 전송 실패 시 특별한 처리를 하지 않는다 — ack 만 멈춘다.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
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

CONTROL_IDLE_INTERVAL_S = 0.25
"""**조작 국면의** 무프레임 감시 주기 (010 FR-335 · research R8).

조작이 화면을 바꾸면 프레임이 온다 — 실측 중앙값 25ms 다. 화면을 바꾸지 않는 조작(초점
이동, 값이 같은 입력)은 프레임을 만들지 않고, 그때 기존 2초 감시가 채워 준다.

**2초는 조작 피드백으로 너무 길다.** 사용자는 그 2초를 「내 클릭이 안 먹었다」로 읽고 같은
곳을 다시 누른다 — FR-334 가 금지하는 상태다. 조작 국면에서만 주기를 줄이는 것으로
충분하다는 것이 research R8 의 판단이다.

**관찰 국면에서는 줄이지 않는다.** 그쪽에서 초당 네 장을 찍으면 실행 중인 브라우저를
갉아먹고, 얻는 것은 없다 — 사람이 조작하고 있지 않으므로 기다리게 만들 피드백도 없다.
"""

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


def _finite(value: Any) -> float:
    """메타데이터의 수치 하나를 유한한 실수로 읽는다. 읽을 수 없으면 0.

    CDP 가 보내는 값이므로 형이 보장된 것처럼 다루기 쉽지만, 미러가 예외를 내면 그것이
    프레임 전달을 끊는다 — 미러 실패는 실행에 영향을 주지 않아야 한다 (FR-047b).
    """
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if number != number or number in (float("inf"), float("-inf")):  # NaN·무한
        return 0.0
    return number


def _positive_scale(value: Any) -> float:
    """페이지 배율. 0 이하거나 읽을 수 없으면 1 로 본다.

    **0 을 그대로 넘기면 프론트의 역변환이 0 으로 나눈다.** 배율은 나눗셈의 분모이므로
    (data-model §2 역변환식) 여기서 막는 편이 싸다.
    """
    number = _finite(value)
    return number if number > 0 else 1.0


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
        self._control_phase = False
        """지금이 조작 국면인가 (010 FR-335).

        **미러가 스스로 판정하지 않는다.** 국면은 상태 기계가 알고, 여기는 통보를 받는다
        (FR-316 과 같은 이유). 이 값이 하는 일은 무프레임 감시 주기를 고르는 것 하나다.
        """
        self._frame_seq = itertools.count(1)
        """프레임 일련번호 (010 FR-331 · data-model §2).

        클라이언트가 보내는 조작 사건의 `frameSeq` 가 이 값을 가리킨다 — **그 좌표를
        계산한 근거가 어느 프레임이었는가.** 이번 범위에서 서버가 이 값으로 조작을
        거절하지는 않는다. 원격 조작의 본질적 한계(사용자가 본 화면이 이미 낡았을 수
        있다)는 감출 수 없기 때문이다. 진단에 필요하고, 정책을 넣을 자리를 남긴다.

        **탭마다 새로 센다.** 표시 탭이 바뀌면 `TabScreencast` 도 새로 만들어지므로
        번호가 1 부터 다시 시작한다 — 프레임의 `tab` 과 함께 읽어야 하는 값이다.
        """

    @property
    def tab_index(self) -> int:
        return self._tab_index

    @property
    def running(self) -> bool:
        return self._running

    @property
    def degraded(self) -> bool:
        return self._degraded_task is not None

    @property
    def control_phase(self) -> bool:
        """조작 국면인가. 탭을 갈아 끼울 때 새 스크린캐스트가 이 값을 이어받는다."""
        return self._control_phase

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

    def set_control_phase(self, active: bool) -> None:
        """조작 국면 여부를 알려 준다 (010 FR-335 · FR-339).

        조작 국면에서는 무프레임 감시가 빨라지고, ack 를 다시 켠다 — 조작해도 화면이
        바뀌지 않는 상태를 만들지 않기 위해서다 (아래 `_acking` 의 설명).
        """
        self._control_phase = active
        if active:
            # research R8 — **ack 가 멈추면 3프레임 뒤 프레임 밀기가 정지한다.** 그 상태는
            # 사용자에게 「조작해도 화면이 안 바뀐다」로 보인다. 조작 국면에 들어올 때
            # 반드시 다시 켠다: 그전에 통로가 끊겨 ack 를 멈춘 채로 남아 있을 수 있다.
            self._acking = True

    def idle_interval(self) -> float:
        """지금 쓸 무프레임 감시 주기 (010 FR-335)."""
        return CONTROL_IDLE_INTERVAL_S if self._control_phase else IDLE_INTERVAL_S

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

    async def _send_frame(
        self,
        data: str,
        width: int,
        height: int,
        *,
        page_scale: float = 1.0,
        offset_top: float = 0.0,
    ) -> None:
        """프레임 하나를 보내고 **마지막 프레임으로 기억한다** (005 FR-162).

        전송 경로를 한 곳으로 모으는 이유는 캐시가 빠지는 경로를 만들지 않기 위해서다 —
        스크린캐스트·강등 루프·무프레임 감시 셋이 모두 여기를 지난다. 010 이 좌표 변환의
        근거(`pageScale`·`offsetTop`·`seq`)를 더하면서 그 이유가 하나 늘었다: **세 경로가
        모두 같은 모양의 프레임을 내야** 프론트가 경로를 구분하지 않고 역변환할 수 있다
        (T006 · FR-331).

        `width`·`height` 의 의미는 **바뀌지 않는다** — 대상 화면 크기다. 프레임의 실제
        픽셀 크기는 보내지 않는다. 클라이언트가 `<img>` 에서 직접 읽는 편이 서버가 보낸
        값과 이미지가 어긋날 여지를 만들지 않는다 (data-model §2).

        **계약(contracts/mirror-control.md §4)은 이 필드를 `seq` 라 불렀다. `frameSeq` 로
        둔다.** 이벤트 봉투가 이미 `seq` 를 쓰고 있고(`SessionEventHub.publish`), 그 값은
        프론트에서 **서버 재시작 감지**의 근거다 — 뒤로 가면 전체 상태를 다시 받는다
        (`frontend/src/api/ws.ts`). 페이로드의 `seq` 는 봉투의 `seq` 를 덮으므로, 계약대로
        두면 탭을 바꿀 때마다(프레임 번호가 1 로 되돌아간다) 프론트가 서버 재시작으로 읽고
        헛되이 재동기화한다. 클라이언트가 되돌려 보내는 필드 이름이 이미 `frameSeq` 이므로
        (data-model §1) 양쪽이 같은 이름을 쓰게 되는 이점도 있다.
        """
        payload: dict[str, object] = {
            "tab": self._tab_index,
            "data": data,
            "width": width,
            "height": height,
            "pageScale": page_scale,
            "offsetTop": offset_top,
            "frameSeq": next(self._frame_seq),
        }
        self._last_frame = payload
        self._last_sent_at = time.monotonic()
        await self._emit("mirror_frame", **payload)

    def last_frame(self) -> dict[str, object] | None:
        """구독이 붙을 때 보낼 마지막 프레임. 아직 한 장도 없으면 `None` (005 FR-162)."""
        return self._last_frame

    async def _forward(self, params: dict[str, Any]) -> None:
        """스크린캐스트 프레임 하나. **메타데이터에서 좌표 변환의 근거를 꺼낸다** (T005).

        `Page.screencastFrame` 의 `metadata` 는 `pageScaleFactor` 와 `offsetTop` 을 실제로
        담고 있다 (research R3). 이전에는 `deviceWidth`·`deviceHeight` 둘만 읽었고, 그래서
        프론트는 배율과 상단 오프셋을 추정할 수밖에 없었다 — FR-331 이 금지하는 상태다.

        일반적인 데스크톱 크롬에서 두 값은 각각 1 과 0 이다. 그렇지 않은 환경에서만
        좌표가 어긋나고 원인이 드러나지 않는 것을 막기 위해 **값과 무관하게 전달한다.**
        """
        metadata = params.get("metadata") or {}
        await self._send_frame(
            params.get("data", ""),
            int(metadata.get("deviceWidth") or MAX_WIDTH),
            int(metadata.get("deviceHeight") or MAX_HEIGHT),
            page_scale=_positive_scale(metadata.get("pageScaleFactor")),
            offset_top=_finite(metadata.get("offsetTop")),
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
            interval = self.idle_interval()
            await asyncio.sleep(interval / 2)
            if not self._running or self.degraded:
                continue
            # 주기를 **매 회전마다 다시 읽는다.** 국면은 루프가 도는 동안 바뀐다 —
            # 시작 시점의 값을 잡아 두면 녹화를 켠 뒤에도 2초 주기로 돈다.
            quiet_for = time.monotonic() - self._last_sent_at
            if quiet_for < self.idle_interval():
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
        width, height = self._viewport()
        await self._send_frame(base64.b64encode(shot).decode("ascii"), width, height)
        return True

    def _viewport(self) -> tuple[int, int]:
        """대상 화면 크기 (T006 · FR-331).

        스크린샷 경로는 이전까지 `MAX_WIDTH`·`MAX_HEIGHT` 를 그대로 실었다. 그것은
        **스크린캐스트에 요청하는 상한**이지 대상 화면 크기가 아니다 — 실측에서 1280×800
        을 요청해 1067×800 을 받았다 (research R3). 두 값이 다르므로, 강등·무프레임 보충
        경로의 프레임으로 좌표를 역변환하면 어긋난다.

        `page.viewport_size` 를 읽을 수 없으면 종전 값으로 붙는다 — 미러가 예외로 실행을
        건드리지 않는다 (FR-047b).
        """
        with contextlib.suppress(Exception):
            size = self._page.viewport_size
            if size:
                return int(size["width"]), int(size["height"])
        return MAX_WIDTH, MAX_HEIGHT
