"""조작 채널. 새 WebSocket (010 T016~T020 · contracts/mirror-control.md §2 · research R4).

**관찰 소켓과 방향이 반대인 별개의 소켓이다.** `session_events.py` 의 계약 — 서버 →
클라이언트 단방향, 클라이언트는 명령을 보내지 않는다 — 은 **그대로 유지된다.** 그 계약을
깨는 대신 소켓을 하나 더 두는 이유는 둘이다 (research R4).

1. 한 소켓이 프레임 밀기와 조작 받기를 같이 하면 **조작 폭주가 프레임 전달을 막고 그 역도
   성립한다.** FR-336 이 금지하는 상태다.
2. 조작 채널이 끊겨도 관찰은 그대로여야 하고, 그 역도 같다 (FR-348 · FR-047b).

**채널이 조작 가능 여부를 강제한다** (FR-342). 화면이 안 보내는 것에 의존하지 않는다 —
관찰 국면으로 전이하면 서버가 **사유와 함께** 닫고, 그 뒤로는 소켓 자체가 수립되지 않는다.
화면 단에서만 막으면 화면을 우회한 조작 경로가 남는다.

**조작 성공 응답을 보내지 않는다** (contracts §5 불변식 5). 성공의 증거는 프레임이다.
응답을 기다리게 만들면 다음 키가 앞 키의 전달 완료를 기다리게 되고 (FR-327a), 조작 전달과
프레임 수신이 서로를 막는다 (FR-336).

**Step 을 만들지 않는다.** 조작은 대상 브라우저의 입력이 될 뿐이고 Step 은 리코더가 만든다
(헌법 원칙 I · research R1).
"""

from __future__ import annotations

import contextlib
from enum import StrEnum
from typing import Any

from itb.execution.state_machine import SessionState, is_control_phase
from itb.mirror.input import KNOWN_MODIFIERS, MAX_TEXT_LENGTH

EVENT_KINDS = frozenset(
    {
        "pointer.down",
        "pointer.up",
        "pointer.move",
        "wheel",
        "key.down",
        "key.up",
        "text.insert",
        "ime.compose",
        "ime.commit",
        "file.attach",
    }
)
"""채널이 받는 사건 종류 전체 (data-model §1 · FR-344).

**이 목록이 채널의 상한이다.** 여기 없는 것은 사건을 버리고 사유를 돌려준다. 미러의
`_ALLOWED_COMMANDS` 가 프레임 쪽에서 지키던 성질 — "이 통로로는 정해진 것만 나간다" — 을
방향만 바꾸어 유지한다 (research R5).
"""

_BUTTONS = frozenset({"left", "middle", "right"})

_POINTER_KINDS = frozenset({"pointer.down", "pointer.up", "pointer.move", "wheel"})
_BUTTON_KINDS = frozenset({"pointer.down", "pointer.up"})
_TEXT_KINDS = frozenset({"text.insert", "ime.compose", "ime.commit"})
_KEY_KINDS = frozenset({"key.down", "key.up"})

MAX_KEY_LENGTH = 32
"""키 이름 길이 상한. `"Backspace"`·`"ArrowLeft"` 가 가장 긴 축이다."""

MAX_FILE_IDS = 16
"""한 번에 지정할 수 있는 파일 개수 (FR-337a 와 짝을 이룬다)."""


class ChannelState(StrEnum):
    """채널 상태 (data-model §3)."""

    CLOSED = "closed"
    """열려 있지 않다. 사건을 받지 않는다."""

    OPEN = "open"
    """조작 국면이고 채널이 붙어 있다. 사건을 받는다."""

    SUSPENDED = "suspended"
    """붙어 있으나 지금은 받지 않는다 — 프레임이 끊겼다 (FR-346).

    **닫는 것과 다르다.** 닫으면 클라이언트가 다시 붙어야 하고, 프레임이 잠깐 끊긴 것과
    국면이 바뀐 것이 화면에서 같아 보인다. 사용자는 「화면이 멈춘 것」과 「페이지가 멈춘
    것」을 구분할 수 있어야 한다.
    """


class ControlRejected(Exception):
    """사건을 거절했다. **버리고 사유를 돌려준다** — 잘라서 보내지 않는다 (FR-341).

    잘라 보내면 대상 페이지에 사용자가 의도하지 않은 값이 들어가고, 그 Step 이 그대로
    저장된다. 거절이 조용하면 사용자는 클릭했는데 아무 일도 없는 것으로 본다 (SC-516).
    """

    def __init__(self, reason: str, kind: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.kind = kind


def rejection(exc: ControlRejected) -> dict[str, Any]:
    """거절 사유 메시지 (contracts §2 서버 → 클라이언트)."""
    return {"type": "control_rejected", "reason": exc.reason, "kind": exc.kind}


def state_message(state: ChannelState, reason: str | None = None) -> dict[str, Any]:
    """채널 상태 메시지. **닫을 때 반드시 사유를 싣는다** (contracts §2).

    사유 없이 끊으면 클라이언트는 이유 없이 끊긴 것으로 보고, 사용자에게는 조용한 실패가
    된다 (SC-516).
    """
    return {"type": "control_state", "state": str(state), "reason": reason}


# ─── 경계 검증 (T016 · FR-341) ───────────────────────────────────────────────


def validate(
    event: Any,
    *,
    frame_width: float | None,
    frame_height: float | None,
    tabs: set[int],
) -> dict[str, Any]:
    """조작 사건 하나를 검증해 정규화한다. 어기면 `ControlRejected`.

    **하나라도 어기면 버린다. 잘라서 보내지 않는다** (FR-341 · data-model §1). 좌표를
    화면 안으로 밀어 넣으면 사용자가 누르지 않은 요소가 눌리고, 문자열을 자르면 의도하지
    않은 값이 대상 페이지에 들어간다. 어느 쪽도 조용히 잘못된 Step 을 만든다.

    `frame_width`·`frame_height` 는 **그 탭의 대상 화면 크기**다. `None` 이면 프레임을 한
    장도 받지 못한 상태이므로 포인터 사건을 받지 않는다 (FR-333) — 무엇을 조작하는지 볼
    수 없는 상태에서 좌표를 보낼 근거가 없다.
    """
    if not isinstance(event, dict):
        msg = "조작 사건은 객체여야 합니다."
        raise ControlRejected(msg)

    kind = event.get("kind")
    if not isinstance(kind, str) or kind not in EVENT_KINDS:
        msg = f"{kind!r} 는 이 통로로 보낼 수 있는 사건이 아닙니다."
        raise ControlRejected(msg, kind if isinstance(kind, str) else None)

    clean: dict[str, Any] = {"kind": kind}

    tab = event.get("tab", 0)
    if not isinstance(tab, int) or isinstance(tab, bool) or tab not in tabs:
        msg = f"탭 {tab} 이 이 세션에 없습니다."
        raise ControlRejected(msg, kind)
    clean["tab"] = tab

    clean["modifiers"] = _modifiers(event.get("modifiers", 0), kind)

    frame_seq = event.get("frameSeq")
    if frame_seq is not None:
        if not isinstance(frame_seq, int) or isinstance(frame_seq, bool) or frame_seq < 0:
            msg = "프레임 번호가 올바르지 않습니다."
            raise ControlRejected(msg, kind)
        clean["frameSeq"] = frame_seq

    if kind in _POINTER_KINDS:
        _require_frame(kind, frame_width, frame_height)
        clean["x"] = _coordinate(event.get("x"), frame_width, "x", kind)
        clean["y"] = _coordinate(event.get("y"), frame_height, "y", kind)

    if kind in _BUTTON_KINDS:
        button = event.get("button", "left")
        if button not in _BUTTONS:
            msg = f"{button!r} 는 알 수 없는 버튼입니다."
            raise ControlRejected(msg, kind)
        clean["button"] = button

    if kind == "wheel":
        clean["deltaX"] = _delta(event.get("deltaX", 0), kind)
        clean["deltaY"] = _delta(event.get("deltaY", 0), kind)

    if kind in _KEY_KINDS:
        clean["key"] = _short_text(event.get("key", ""), MAX_KEY_LENGTH, "키 이름", kind)
        clean["code"] = _short_text(event.get("code", ""), MAX_KEY_LENGTH, "키 코드", kind)

    if kind in _TEXT_KINDS:
        text = event.get("text", "")
        if not isinstance(text, str):
            msg = "문자열이어야 합니다."
            raise ControlRejected(msg, kind)
        if len(text) > MAX_TEXT_LENGTH:
            msg = (
                f"입력이 상한({MAX_TEXT_LENGTH}자)을 넘었습니다. "
                "잘라서 보내지 않고 거절합니다."
            )
            raise ControlRejected(msg, kind)
        clean["text"] = text

    if kind == "ime.compose":
        raw = event.get("compositionRange")
        if raw is not None:
            if (
                not isinstance(raw, (list, tuple))
                or len(raw) != 2
                or not all(isinstance(v, int) and not isinstance(v, bool) for v in raw)
            ):
                msg = "조합 구간은 정수 두 개여야 합니다."
                raise ControlRejected(msg, kind)
            clean["compositionRange"] = [int(raw[0]), int(raw[1])]

    if kind == "file.attach":
        clean["fileIds"] = _file_ids(event.get("fileIds"), kind)
        node = event.get("backendNodeId")
        if node is not None:
            if not isinstance(node, int) or isinstance(node, bool):
                msg = "요소 식별자가 올바르지 않습니다."
                raise ControlRejected(msg, kind)
            clean["backendNodeId"] = node

    return clean


def _require_frame(kind: str, width: float | None, height: float | None) -> None:
    """FR-333 — 프레임을 한 장도 받지 못했으면 좌표를 보낼 근거가 없다."""
    if width is None or height is None or width <= 0 or height <= 0:
        msg = (
            "아직 대상 화면을 한 장도 받지 못해 조작을 전달할 수 없습니다. "
            "화면이 표시되면 조작할 수 있습니다."
        )
        raise ControlRejected(msg, kind)


def _coordinate(value: Any, limit: float | None, axis: str, kind: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = f"{axis} 좌표가 수치가 아닙니다."
        raise ControlRejected(msg, kind)
    number = float(value)
    if number != number:  # NaN
        msg = f"{axis} 좌표를 읽을 수 없습니다."
        raise ControlRejected(msg, kind)
    assert limit is not None  # noqa: S101 - _require_frame 이 이미 확인했다
    if number < 0 or number > limit:
        msg = (
            f"{axis} 좌표 {number:g} 가 화면(0~{limit:g}) 밖입니다. "
            "화면 안으로 밀어 넣지 않고 거절합니다."
        )
        raise ControlRejected(msg, kind)
    return number


def _delta(value: Any, kind: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = "스크롤 이동량이 수치가 아닙니다."
        raise ControlRejected(msg, kind)
    number = float(value)
    if number != number or abs(number) == float("inf"):
        msg = "스크롤 이동량을 읽을 수 없습니다."
        raise ControlRejected(msg, kind)
    return number


def _modifiers(value: Any, kind: str) -> int:
    """수정자 비트. **알려진 비트만 허용한다** (FR-341).

    알 수 없는 비트를 그대로 넘기면 CDP 가 어떻게 해석할지 이 코드가 답할 수 없다.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "수정자는 정수여야 합니다."
        raise ControlRejected(msg, kind)
    if value < 0 or value & ~KNOWN_MODIFIERS:
        msg = f"알 수 없는 수정자 비트({value})입니다."
        raise ControlRejected(msg, kind)
    return value


def _short_text(value: Any, limit: int, label: str, kind: str) -> str:
    if not isinstance(value, str):
        msg = f"{label}이 문자열이 아닙니다."
        raise ControlRejected(msg, kind)
    if len(value) > limit:
        msg = f"{label}이 상한({limit}자)을 넘었습니다."
        raise ControlRejected(msg, kind)
    return value


def _file_ids(value: Any, kind: str) -> list[str]:
    if not isinstance(value, list) or not value:
        msg = "지정할 파일이 없습니다."
        raise ControlRejected(msg, kind)
    if len(value) > MAX_FILE_IDS:
        msg = f"한 번에 지정할 수 있는 파일은 {MAX_FILE_IDS}개까지입니다."
        raise ControlRejected(msg, kind)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            msg = "파일 식별자가 올바르지 않습니다."
            raise ControlRejected(msg, kind)
        out.append(item)
    return out


# ─── 채널 (T017~T019 · data-model §3) ────────────────────────────────────────


class ControlChannel:
    """세션 하나의 조작 채널. **세션당 최대 하나** (contracts §2 · 명세 Out of Scope).

    이미 열려 있으면 새 접속을 거절한다 — 한 세션당 한 조작자를 가정한다. 둘이 붙으면
    같은 화면에 두 사람의 조작이 섞이고, 어느 조작이 어느 Step 이 되었는지 아무도 답할 수
    없다.

    **채널은 실행 상태 기계를 전이시키지 않는다** (contracts §5 불변식 4 · FR-348). 여기서
    일어나는 어떤 일도 세션 상태를 바꾸지 않는다 — 조작 채널의 장애가 실행 실패가 되는
    경로를 두지 않는다. 이 클래스가 `next_state` 를 부르지 않는 것이 그 구현이다.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._state = ChannelState.CLOSED
        self._socket: Any = None
        self._input: Any = None
        """붙어 있는 `TabInput`. 채널이 닫힐 때 함께 닫힌다 (FR-318)."""

    @property
    def state(self) -> ChannelState:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state is ChannelState.OPEN

    @property
    def attached(self) -> bool:
        return self._socket is not None

    def can_accept(self, session_state: SessionState) -> bool:
        """지금 사건을 받는가. **국면과 채널 상태를 함께 본다.**"""
        return self._state is ChannelState.OPEN and is_control_phase(session_state)

    async def open(self, socket: Any, controller: Any) -> None:
        """채널을 연다. 이미 붙어 있으면 부르지 않는다 — 라우터가 먼저 거절한다."""
        self._socket = socket
        self._input = controller
        self._state = ChannelState.OPEN

    async def suspend(self, reason: str) -> None:
        """받지 않는 상태로 내린다 (FR-346). 누른 포인터를 먼저 놓는다 (FR-318).

        닫지 않는 이유는 위 `ChannelState.SUSPENDED` 에 적었다.
        """
        if self._state is not ChannelState.OPEN:
            return
        self._state = ChannelState.SUSPENDED
        await self._release()
        await self._notify(state_message(ChannelState.SUSPENDED, reason))

    async def resume(self) -> None:
        """프레임이 회복됐다 (data-model §3)."""
        if self._state is not ChannelState.SUSPENDED:
            return
        self._state = ChannelState.OPEN
        await self._notify(state_message(ChannelState.OPEN, None))

    async def close(self, reason: str) -> None:
        """서버가 닫는다 — 관찰 국면 전이(FR-342) 또는 세션 종료·유실(FR-347).

        **사유를 먼저 보내고 닫는다.** 사유 없이 끊으면 클라이언트가 이유 없이 끊긴 것으로
        보고, 사용자에게는 조용한 실패가 된다 (SC-516).
        """
        if self._state is ChannelState.CLOSED and self._socket is None:
            return
        self._state = ChannelState.CLOSED
        await self._release()
        await self._notify(state_message(ChannelState.CLOSED, reason))
        socket, self._socket = self._socket, None
        self._input = None
        if socket is not None:
            with contextlib.suppress(Exception):
                await socket.close()

    def detached(self) -> None:
        """클라이언트가 끊었다. 서버가 닫은 것과 구분한다 — 보낼 소켓이 이미 없다."""
        self._state = ChannelState.CLOSED
        self._socket = None
        self._input = None

    async def _release(self) -> None:
        """누른 채로 남은 포인터를 놓는다 (FR-318 · contracts §2).

        **클라이언트의 성실함에 의존하지 않는다.** 끌어놓기 도중 채널이 끊기는 것을
        클라이언트는 알 수 없고, 그때 대상 페이지는 누른 상태로 남는다.
        """
        if self._input is None:
            return
        with contextlib.suppress(Exception):
            await self._input.release_pressed()

    async def send_rejection(self, exc: ControlRejected) -> None:
        """거절 사유를 돌려준다 (FR-341 · SC-516).

        **조용히 버리지 않는다.** 사용자가 클릭했는데 아무 일도 일어나지 않는 것이
        SC-516 이 0건으로 두려는 상태다.
        """
        await self._notify(rejection(exc))

    async def _notify(self, message: dict[str, Any]) -> None:
        """상태 메시지 하나. **실패해도 예외를 내지 않는다** (FR-348)."""
        if self._socket is None:
            return
        with contextlib.suppress(Exception):
            await self._socket.send_json(message)


class ControlChannelRegistry:
    """세션 ID 별 채널 모음. `EventBroker` 와 같은 자리를 조작 쪽에서 맡는다."""

    def __init__(self) -> None:
        self._channels: dict[str, ControlChannel] = {}

    def get(self, session_id: str) -> ControlChannel | None:
        return self._channels.get(session_id)

    def channel(self, session_id: str) -> ControlChannel:
        channel = self._channels.get(session_id)
        if channel is None:
            channel = ControlChannel(session_id)
            self._channels[session_id] = channel
        return channel

    async def close(self, session_id: str, reason: str) -> None:
        """한 세션의 채널을 닫는다. 없으면 아무것도 하지 않는다."""
        channel = self._channels.get(session_id)
        if channel is not None:
            await channel.close(reason)

    async def drop(self, session_id: str, reason: str) -> None:
        """세션이 사라졌다. 채널을 닫고 등록도 지운다 (FR-347)."""
        channel = self._channels.pop(session_id, None)
        if channel is not None:
            await channel.close(reason)

    async def close_all(self, reason: str) -> None:
        for session_id in list(self._channels):
            await self.drop(session_id, reason)
