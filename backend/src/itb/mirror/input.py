"""미러 조작. CDP `Input` 도메인 (010 T009~T011 · research R1·R2·R5).

**이 모듈은 프레임을 모른다.** `mirror/screencast.py` 를 임포트하지 않고, 그 역도 아니다.
분리의 기준은 「무엇을 모르는가」다 — `screencast.py` 는 `Input` 을 모르고 `input.py` 는
프레임을 모른다. 이 경계가 FR-336(조작과 프레임이 서로를 막지 않는다)을 파일 단위로
만든다. `tests/unit/test_mirror_input.py` 가 양방향으로 고정한다.

**전용 CDP 세션을 쓴다.** 러너가 쓰는 `Page` 객체의 고수준 API(`page.mouse`·
`page.keyboard`)를 경유하지 않는다. 그것을 쓰면 러너 명령과 경쟁하고, 미러가 전용 세션을
쓰는 이유(FR-047b)가 조작에서만 사라진다.

**자기 명령 목록을 가진다** (FR-344). `screencast.py` 의 `_ALLOWED_COMMANDS` 가 프레임
쪽에서 지키던 성질 — "여기로는 정해진 것만 나간다" — 을 조작 쪽에서 유지한다. 목록을 두는
이유는 나중에 "잠깐 이 CDP 명령 하나만" 이 들어오는 것을 막기 위해서다. 임의의 브라우저
제어나 페이지 스크립트 실행이 이 통로로 가능해서는 안 된다.

**Step 을 만들지 않는다.** 조작은 대상 브라우저의 입력이 될 뿐이고, Step 은 대상 페이지의
리코더가 만든다. 주입한 입력은 페이지에서 `isTrusted: true` 이벤트가 되고 리코더는
`isTrusted` 를 검사하지 않으므로, 미러 조작과 창 조작이 리코더에게 **구분되지 않는다**
(research R1). 이것이 헌법 원칙 I 을 지키는 자리다 — 서버가 조작 사건을 Step 으로
변환하는 경로를 만들면 같은 조작이 경로에 따라 다른 Step 이 될 수 있는 구조가 생긴다.
"""

from __future__ import annotations

import contextlib
from typing import Any

from playwright.async_api import CDPSession, Page

ALLOWED_COMMANDS = frozenset(
    {
        "Input.dispatchMouseEvent",
        "Input.dispatchKeyEvent",
        "Input.insertText",
        "Input.imeSetComposition",
        "DOM.setFileInputFiles",
    }
)
"""이 모듈이 보낼 수 있는 CDP 명령 전체 (FR-344 · contracts §2).

`DOM.setFileInputFiles` 는 `Input` 이 아니지만 조작의 일부다 — 파일 선택 요구에 응답하는
유일한 수단이며, 그것이 없으면 파일 첨부 화면에서 녹화가 조용히 멈춘다 (research R6).
목록에 **명시적으로** 넣는 이유가 그것이다: 도메인이 다르다는 이유로 목록 밖에 두면,
목록이 상한이라는 성질이 첫 예외에서 무너진다.

`Page.*`·`Runtime.evaluate` 는 여기 없다. 페이지 스크립트 실행 경로를 이 통로에 두지
않는다.
"""

MAX_TEXT_LENGTH = 4096
"""한 사건이 실어 나를 수 있는 문자열 길이 상한 (FR-341).

붙여넣기 한 번이 이 값을 넘는 일은 드물고, 넘으면 **자르지 않고 거절한다** — 잘라서 보내면
대상 페이지에 사용자가 의도하지 않은 값이 들어가고 그 Step 이 그대로 저장된다.
"""

KNOWN_MODIFIERS = 0b1111
"""CDP 가 정의한 수정자 비트 — Alt(1)·Ctrl(2)·Meta(4)·Shift(8) (FR-341).

이 밖의 비트가 서 있으면 사건을 거절한다. 알 수 없는 비트를 그대로 넘기면 CDP 가 어떻게
해석할지 이 코드가 답할 수 없다.
"""

_BUTTONS = {"left": 1, "middle": 4, "right": 2}
"""버튼 이름 → CDP `buttons` 비트마스크. 목록 밖 이름은 경계에서 거절된다."""


class MirrorCommandForbiddenError(RuntimeError):
    """조작 모듈이 목록 밖 CDP 명령을 보내려 했다 (FR-344).

    `screencast.MirrorInputForbiddenError` 와 **짝을 이룬다.** 그쪽은 프레임 모듈이 조작
    명령을 보내려는 것을 막고, 이쪽은 조작 모듈이 조작 아닌 명령을 보내려는 것을 막는다.
    두 목록의 교집합은 비어 있다.
    """


async def _send(cdp: CDPSession, command: str, params: dict[str, Any] | None = None) -> None:
    """CDP 명령 하나. **목록 밖은 함수 자체가 거절한다** (FR-344)."""
    if command not in ALLOWED_COMMANDS:
        msg = (
            f"미러 조작 통로는 {command} 를 보낼 수 없습니다. 이 통로로 갈 수 있는 것은 "
            "입력 사건과 파일 지정뿐입니다 (FR-344)."
        )
        raise MirrorCommandForbiddenError(msg)
    await cdp.send(command, params or {})


class TabInput:
    """탭 하나에 대한 조작. **보고 있는 탭**에 붙는다 (FR-317).

    활성 탭이 아니라 사용자가 보고 있는 탭이 대상이다. 활성 탭에 보내면 사용자가 보지 않는
    화면이 조작된다 — 그 조작은 되돌릴 수 없고, 무엇이 눌렸는지 화면에 나타나지도 않는다.

    **미해제 포인터를 기억한다** (FR-318 · contracts §2). `pointer.down` 뒤에
    `pointer.up` 이 오지 않은 채 채널이 닫히면 대상 페이지가 누른 상태로 남는다. 클라이언트
    가 성실하게 `up` 을 보낼 것이라는 가정에 기대지 않고 **서버가 보낸다.** 끌어놓기 도중
    브라우저 탭이 닫히거나 네트워크가 끊기는 것을 클라이언트가 알 방법이 없기 때문이다.
    """

    def __init__(self, page: Page, tab_index: int) -> None:
        self._page = page
        self._tab_index = tab_index
        self._cdp: CDPSession | None = None
        self._pressed: dict[str, tuple[float, float]] = {}
        """누른 채 놓지 않은 버튼 → 마지막 좌표. 채널을 닫을 때 여기로 `up` 을 보낸다."""

    @property
    def tab_index(self) -> int:
        return self._tab_index

    @property
    def attached(self) -> bool:
        return self._cdp is not None

    @property
    def pressed_buttons(self) -> tuple[str, ...]:
        """지금 누른 채로 있는 버튼들. 검증이 읽는다."""
        return tuple(self._pressed)

    async def attach(self) -> None:
        """전용 CDP 세션을 연다. 이미 열려 있으면 아무것도 하지 않는다."""
        if self._cdp is not None:
            return
        self._cdp = await self._page.context.new_cdp_session(self._page)

    async def detach(self) -> None:
        """세션을 닫는다. **닫기 전에 누른 포인터를 놓는다** (FR-318).

        순서가 중요하다 — 세션을 먼저 닫으면 `up` 을 보낼 통로가 사라진다.
        """
        await self.release_pressed()
        if self._cdp is None:
            return
        cdp, self._cdp = self._cdp, None
        with contextlib.suppress(Exception):
            await cdp.detach()

    async def release_pressed(self) -> None:
        """누른 채로 남은 포인터를 모두 놓는다 (FR-318).

        채널이 닫히거나 `suspended` 로 갈 때 서버가 부른다. 실패해도 예외를 내지 않는다 —
        조작 채널의 장애가 실행을 실패시켜서는 안 된다 (FR-348).
        """
        if self._cdp is None:
            self._pressed.clear()
            return
        for button, (x, y) in list(self._pressed.items()):
            with contextlib.suppress(Exception):
                await _send(
                    self._cdp,
                    "Input.dispatchMouseEvent",
                    {
                        "type": "mouseReleased",
                        "x": x,
                        "y": y,
                        "button": button,
                        "buttons": 0,
                        "clickCount": 1,
                    },
                )
        self._pressed.clear()

    # ─── 사건 → CDP 명령 (contracts §2 의 표) ──────────────────────────────

    async def dispatch(self, event: dict[str, Any]) -> None:
        """검증을 통과한 조작 사건 하나를 대상 브라우저에 전달한다.

        **좌표는 이미 대상 화면 좌표계로 도착한다** (data-model §1). 역변환은 프론트가
        한다 — 프레임의 실제 픽셀 크기를 아는 쪽이 거기이기 때문이다 (research R3).

        여기서 다시 검증하지 않는다. 검증은 채널 경계에서 한 번 일어나고
        (`api/ws/control_channel.py`), 두 곳에서 하면 어느 쪽이 진실인지 모호해진다.
        """
        if self._cdp is None:
            msg = "조작 세션이 붙어 있지 않습니다."
            raise MirrorCommandForbiddenError(msg)

        kind = event["kind"]
        handler = _HANDLERS.get(kind)
        if handler is None:
            msg = f"{kind} 는 이 통로로 보낼 수 없습니다 (FR-344)."
            raise MirrorCommandForbiddenError(msg)
        await handler(self, event)

    async def _pointer_down(self, event: dict[str, Any]) -> None:
        button = event.get("button", "left")
        x, y = float(event["x"]), float(event["y"])
        self._pressed[button] = (x, y)
        await self._mouse("mousePressed", event, button=button, buttons=_BUTTONS.get(button, 1))

    async def _pointer_up(self, event: dict[str, Any]) -> None:
        button = event.get("button", "left")
        self._pressed.pop(button, None)
        await self._mouse("mouseReleased", event, button=button, buttons=0)

    async def _pointer_move(self, event: dict[str, Any]) -> None:
        """이동. **누른 채 이동하면 그 버튼을 실어 보낸다** — 끌어놓기의 중간이다.

        `buttons` 가 0 이면 대상 페이지는 그것을 끌기가 아니라 단순 이동으로 읽고,
        `dragover` 가 발생하지 않는다.
        """
        buttons = 0
        for button in self._pressed:
            buttons |= _BUTTONS.get(button, 0)
        for button in self._pressed:
            self._pressed[button] = (float(event["x"]), float(event["y"]))
        await self._mouse("mouseMoved", event, button="none", buttons=buttons)

    async def _wheel(self, event: dict[str, Any]) -> None:
        await self._mouse(
            "mouseWheel",
            event,
            button="none",
            buttons=0,
            deltaX=float(event.get("deltaX", 0.0)),
            deltaY=float(event.get("deltaY", 0.0)),
        )

    async def _mouse(
        self,
        type_: str,
        event: dict[str, Any],
        *,
        button: str,
        buttons: int,
        **extra: float,
    ) -> None:
        assert self._cdp is not None  # noqa: S101 - dispatch 가 이미 확인했다
        params: dict[str, Any] = {
            "type": type_,
            "x": float(event["x"]),
            "y": float(event["y"]),
            "button": button,
            "buttons": buttons,
            "modifiers": int(event.get("modifiers", 0)),
        }
        if type_ in ("mousePressed", "mouseReleased"):
            params["clickCount"] = int(event.get("clickCount", 1))
        params.update(extra)
        await _send(self._cdp, "Input.dispatchMouseEvent", params)

    async def _key(self, event: dict[str, Any], *, type_: str) -> None:
        assert self._cdp is not None  # noqa: S101
        await _send(
            self._cdp,
            "Input.dispatchKeyEvent",
            {
                "type": type_,
                "key": event.get("key", ""),
                "code": event.get("code", ""),
                "modifiers": int(event.get("modifiers", 0)),
            },
        )

    async def _insert_text(self, event: dict[str, Any]) -> None:
        assert self._cdp is not None  # noqa: S101
        await _send(self._cdp, "Input.insertText", {"text": event.get("text", "")})

    async def _ime_compose(self, event: dict[str, Any]) -> None:
        """조합 중인 문자열을 대상 입력 요소에 **실시간으로** 넣는다 (FR-327 · research R2).

        확정이 아니다. 대상 페이지는 `compositionupdate` 와 `isComposing: true` 인 `input`
        을 받고, 리코더는 조합 중인 `input` 을 무시하므로 이 값이 Step 으로 새지 않는다
        (FR-326·FR-327c · M-10).
        """
        assert self._cdp is not None  # noqa: S101
        text = event.get("text", "")
        start, end = _composition_range(event, len(text))
        await _send(
            self._cdp,
            "Input.imeSetComposition",
            {
                "text": text,
                "selectionStart": start,
                "selectionEnd": end,
            },
        )

    async def _ime_commit(self, event: dict[str, Any]) -> None:
        """조합을 확정한다. `insertText` 가 `compositionend` 를 만든다 (research R2).

        **민감 입력의 치환은 여기서 하지 않는다** (T047 · FR-329). 이 모듈은 값을 대상
        브라우저로 지나 보낼 뿐이고, Step 은 대상 페이지의 리코더가 만든다. 따라서 기존
        치환 파이프라인(수집 → 검증 → 치환 → Step → 이벤트)이 미러 경로에도 그대로
        적용된다 — 리코더가 `type="password"` 를 보고 민감으로 판정하고, Python 쪽이
        변수 참조로 바꾼 뒤에야 이벤트가 나간다 (`recorder.js` 의 `sensitive` 필드).

        **여기서 한 번 더 치환하면 안 된다.** 치환 책임을 두 곳에 두면 어느 쪽이 빠졌는지
        알 수 없어지고, 이 모듈은 어느 요소가 비밀번호인지 알 방법도 없다 — 좌표와 문자열
        만 받기 때문이다. 그 무지가 이 모듈이 민감 값을 흘릴 수 없는 이유이기도 하다.
        """
        await self._insert_text(event)

    async def _file_attach(self, event: dict[str, Any]) -> None:
        """파일 선택 요소에 파일을 지정한다 (FR-337 · research R6).

        `backendNodeId` 를 함께 받는다 — 어느 요소에 넣을지는 파일 선택 요구를 가로챈
        쪽(`mirror/prompts.py`)이 안다. 이 모듈은 그것을 그대로 넘긴다.

        **순서 보장** (research 미해결 항목): 파일 지정은 조작 채널을 타고, 파일 자체는
        REST 로 먼저 올라간다. 채널이 사건 순서를 보장하므로 `file.attach` 와 그 뒤의
        조작 사이의 순서는 지켜진다. 업로드와의 순서는 클라이언트가 **업로드 응답을 받은
        뒤에** `file.attach` 를 보내는 것으로 지킨다 — 서버가 없는 파일을 기다리게 만드는
        경로를 두지 않는다.
        """
        assert self._cdp is not None  # noqa: S101
        params: dict[str, Any] = {"files": list(event.get("paths", []))}
        node = event.get("backendNodeId")
        if node is not None:
            params["backendNodeId"] = int(node)
        await _send(self._cdp, "DOM.setFileInputFiles", params)


def _composition_range(event: dict[str, Any], length: int) -> tuple[int, int]:
    """조합 중 선택 구간. 값이 없거나 범위를 벗어나면 문자열 끝으로 붙인다.

    CDP 는 범위를 벗어난 값에 어떻게 반응하는지 보장하지 않는다. 여기서 좁히는 편이
    대상 페이지가 예상 밖으로 반응하는 것보다 낫다.
    """
    raw = event.get("compositionRange")
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return length, length
    try:
        start, end = int(raw[0]), int(raw[1])
    except (TypeError, ValueError):
        return length, length
    start = max(0, min(start, length))
    end = max(start, min(end, length))
    return start, end


_HANDLERS: dict[str, Any] = {
    "pointer.down": TabInput._pointer_down,
    "pointer.up": TabInput._pointer_up,
    "pointer.move": TabInput._pointer_move,
    "wheel": TabInput._wheel,
    "key.down": lambda self, event: TabInput._key(self, event, type_="keyDown"),
    "key.up": lambda self, event: TabInput._key(self, event, type_="keyUp"),
    "text.insert": TabInput._insert_text,
    "ime.compose": TabInput._ime_compose,
    "ime.commit": TabInput._ime_commit,
    "file.attach": TabInput._file_attach,
}
"""사건 종류 → 처리 (contracts §2 의 표).

**이 사전이 상한이다.** 여기 없는 `kind` 는 `dispatch` 가 거절한다. 채널 경계의 검증
(`control_channel.py`)과 이중으로 막는 것은 의도다 — 채널을 우회해 이 모듈을 직접 부르는
경로가 나중에 생겨도 목록 밖은 나가지 않는다.
"""
