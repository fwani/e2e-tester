"""조작 채널 (010 T021~T022 · FR-315·FR-341·FR-342 · contracts §2 · data-model §3).

이 파일이 지키는 것은 둘이다.

1. **관찰 국면에 열린 채널은 존재할 수 없다** (FR-315·FR-342). 화면이 안 보내는 것에
   의존하지 않는다 — 채널 자체가 사건을 받지 않아야 한다. 화면 단에서만 막으면 화면을
   우회한 조작 경로가 남는다.
2. **경계를 벗어난 값은 버려진다. 잘려서 전달되지 않는다** (FR-341). 좌표를 화면 안으로
   밀어 넣으면 사용자가 누르지 않은 요소가 눌리고, 문자열을 자르면 의도하지 않은 값이
   대상 페이지에 들어간다 — 둘 다 조용히 잘못된 Step 을 만든다.
"""

from __future__ import annotations

from typing import Any

import pytest

from itb.api.ws.control_channel import (
    EVENT_KINDS,
    MAX_FILE_IDS,
    ChannelState,
    ControlChannel,
    ControlChannelRegistry,
    ControlRejected,
    validate,
)
from itb.execution.state_machine import SessionState, is_control_phase
from itb.mirror.input import MAX_TEXT_LENGTH

FRAME = {"frame_width": 1600.0, "frame_height": 1200.0, "tabs": {0, 1}}


def ok(event: dict[str, Any], **over: Any) -> dict[str, Any]:
    return validate(event, **{**FRAME, **over})


def refused(event: dict[str, Any], **over: Any) -> str:
    with pytest.raises(ControlRejected) as exc:
        validate(event, **{**FRAME, **over})
    return exc.value.reason


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    async def send_json(self, message: dict[str, Any]) -> None:
        self.sent.append(message)

    async def close(self) -> None:
        self.closed = True


class FakeInput:
    """`TabInput` 자리. 누른 포인터를 놓았는지만 본다."""

    def __init__(self) -> None:
        self.released = 0
        self.tab_index = 0

    async def release_pressed(self) -> None:
        self.released += 1


async def opened() -> tuple[ControlChannel, FakeSocket, FakeInput]:
    channel = ControlChannel("s1")
    socket, controller = FakeSocket(), FakeInput()
    await channel.open(socket, controller)
    return channel, socket, controller


# ─── FR-342: 국면이 채널의 개폐를 정한다 (T021) ──────────────────────────────


def test_control_phases_are_exactly_the_contract_table() -> None:
    """조작 국면이 계약(contracts §1)의 표와 같다.

    표와 코드가 갈리면 화면은 켤 수 있다고 그리고 채널은 거절한다 — 사용자는 클릭해 보고
    나서 알게 된다 (FR-319 가 금지하는 상태다).
    """
    control = {s for s in SessionState if is_control_phase(s)}
    assert control == {
        SessionState.RECORDING,
        SessionState.TAKEOVER_RECORDING,
        SessionState.PAUSED,
    }


def test_observation_phases_never_allow_control() -> None:
    """실행 중·AI 수행 중에는 조작 국면이 아니다 (FR-315).

    러너가 전진하는 중에 사람 조작이 끼어들면 같은 Step 이 두 번 돈다.
    """
    for state in (
        SessionState.REPLAYING,
        SessionState.AI_RUNNING,
        SessionState.AI_BLOCKED,
        SessionState.STARTING,
    ):
        assert not is_control_phase(state), f"{state} 를 조작 국면으로 읽었다"


def test_terminal_phases_never_allow_control() -> None:
    """종료·유실 뒤에는 조작 국면이 아니다 (FR-347).

    마지막 프레임이 남아 있어도 보낼 대상이 없다.
    """
    for state in (
        SessionState.COMPLETED,
        SessionState.FAILED,
        SessionState.STOPPED,
        SessionState.LOST,
        SessionState.REVIEW,
    ):
        assert not is_control_phase(state)


@pytest.mark.asyncio
async def test_an_open_channel_refuses_events_in_observation_phases() -> None:
    """**열려 있어도** 관찰 국면에서는 사건을 받지 않는다 (FR-315·FR-342).

    국면 전이와 채널 닫기 사이에는 아무리 짧아도 창이 있다. 그 창에서 채널이 사건을 받으면
    사람 조작이 러너와 겹친다 — 그래서 채널 상태만 보지 않고 국면을 함께 본다.
    """
    channel, _, _ = await opened()
    assert channel.can_accept(SessionState.RECORDING)
    assert not channel.can_accept(SessionState.REPLAYING)
    assert not channel.can_accept(SessionState.AI_RUNNING)
    assert not channel.can_accept(SessionState.LOST)


@pytest.mark.asyncio
async def test_a_closed_channel_refuses_even_in_a_control_phase() -> None:
    """닫힌 채널은 조작 국면에서도 받지 않는다. 두 조건은 AND 다."""
    channel = ControlChannel("s1")
    assert channel.state is ChannelState.CLOSED
    assert not channel.can_accept(SessionState.RECORDING)


@pytest.mark.asyncio
async def test_closing_sends_a_reason_before_it_closes() -> None:
    """닫을 때 **사유를 먼저 보낸다** (contracts §2 · SC-516).

    사유 없이 끊으면 클라이언트는 이유 없이 끊긴 것으로 보고, 사용자에게는 조용한 실패가
    된다.
    """
    channel, socket, _ = await opened()
    await channel.close("실행 중에는 미러에서 조작할 수 없습니다.")

    assert socket.sent, "사유를 보내지 않고 닫았다"
    last = socket.sent[-1]
    assert last["type"] == "control_state"
    assert last["state"] == "closed"
    assert "실행 중" in last["reason"]
    assert socket.closed
    assert channel.state is ChannelState.CLOSED


@pytest.mark.asyncio
async def test_closing_releases_pressed_pointers() -> None:
    """닫을 때 누른 채로 남은 포인터를 놓는다 (FR-318 · contracts §2).

    끌어놓기 도중 국면이 바뀌면 대상 페이지가 누른 상태로 남는다. 클라이언트의 성실함에
    의존하지 않는다 — 클라이언트는 서버가 닫는 순간을 미리 알 수 없다.
    """
    channel, _, controller = await opened()
    await channel.close("국면이 바뀌었습니다.")
    assert controller.released == 1


@pytest.mark.asyncio
async def test_suspend_keeps_the_socket_but_stops_accepting() -> None:
    """프레임이 끊기면 `suspended` 로 내린다 — 닫지 않는다 (FR-346 · data-model §3).

    닫으면 프레임이 잠깐 끊긴 것과 국면이 바뀐 것이 화면에서 같아 보인다. 사용자는
    「화면이 멈춘 것」과 「페이지가 멈춘 것」을 구분할 수 있어야 한다.
    """
    channel, socket, controller = await opened()
    await channel.suspend("화면이 끊겼습니다.")

    assert channel.state is ChannelState.SUSPENDED
    assert not channel.can_accept(SessionState.RECORDING)
    assert not socket.closed, "일시 중단이 소켓을 닫았다"
    assert controller.released == 1, "중단할 때도 누른 포인터를 놓아야 한다"

    await channel.resume()
    assert channel.state is ChannelState.OPEN
    assert channel.can_accept(SessionState.RECORDING)


@pytest.mark.asyncio
async def test_registry_drops_the_channel_when_the_session_ends() -> None:
    """세션이 사라지면 채널도 사라진다 (FR-347)."""
    registry = ControlChannelRegistry()
    channel = registry.channel("s1")
    socket = FakeSocket()
    await channel.open(socket, FakeInput())

    await registry.drop("s1", "세션을 종료했습니다.")

    assert registry.get("s1") is None
    assert socket.closed


@pytest.mark.asyncio
async def test_channel_never_touches_the_state_machine() -> None:
    """**채널의 어떤 상태 전이도 실행 상태 기계를 전이시키지 않는다** (contracts §5 불변식 4).

    조작 채널의 장애가 실행 실패가 되는 경로를 두지 않는다 (FR-348). 코드에서 재는 방법은
    이 모듈이 `next_state`·`Command` 를 아예 모르는 것이다.
    """
    import ast
    from pathlib import Path

    from itb.api.ws import control_channel

    tree = ast.parse(Path(control_channel.__file__).read_text(encoding="utf-8"))

    # 임포트로 재는 것이 요점이다 — 문자열 검색은 "부르지 않는다" 고 적은 주석까지 잡는다.
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)

    forbidden = {"next_state", "Command", "InvalidTransitionError"}
    assert imported & forbidden == set(), (
        f"조작 채널이 상태 기계의 전이 수단을 임포트한다: {imported & forbidden}"
    )

    # 호출도 없어야 한다. 지연 임포트로 들여와 부르는 경로를 막는다.
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } | {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "next_state" not in calls and "apply" not in calls, (
        "조작 채널이 상태 전이를 부른다 — 채널의 어떤 일도 실행 상태 기계를 "
        "전이시켜서는 안 된다 (contracts §5 불변식 4)"
    )


# ─── FR-341: 경계 검증 (T022) ────────────────────────────────────────────────


def test_event_kinds_are_exactly_the_data_model_list() -> None:
    """받는 사건 종류가 data-model §1 의 목록과 같다. **조용히 늘지 않는다** (FR-344)."""
    assert EVENT_KINDS == {
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


def test_unknown_kinds_are_refused() -> None:
    """목록 밖 사건은 버리고 사유를 돌려준다 (FR-344)."""
    for kind in ("script.eval", "cdp.send", "navigate", ""):
        assert "보낼 수 있는 사건이 아닙니다" in refused({"kind": kind})


def test_coordinates_outside_the_frame_are_refused_not_clamped() -> None:
    """화면 밖 좌표는 **거절한다. 밀어 넣지 않는다** (FR-341).

    밀어 넣으면 사용자가 누르지 않은 요소가 눌리고, 그 클릭이 Step 으로 저장된다. 무엇이
    잘못됐는지는 어디에도 나타나지 않는다.
    """
    for x, y in ((-1, 10), (1601, 10), (10, -1), (10, 1201)):
        reason = refused({"kind": "pointer.down", "x": x, "y": y, "button": "left"})
        assert "밖입니다" in reason
        assert "밀어 넣지 않고 거절합니다" in reason


def test_coordinates_on_the_edge_are_accepted() -> None:
    """경계값은 화면 안이다. 0 과 끝을 거절하면 화면 가장자리를 누를 수 없다."""
    assert ok({"kind": "pointer.down", "x": 0, "y": 0, "button": "left"})["x"] == 0.0
    assert ok({"kind": "pointer.up", "x": 1600, "y": 1200, "button": "left"})["y"] == 1200.0


def test_non_numeric_coordinates_are_refused() -> None:
    for value in ("10", None, True, float("nan")):
        assert refused({"kind": "pointer.move", "x": value, "y": 10})


def test_text_over_the_limit_is_refused_not_truncated() -> None:
    """상한을 넘는 문자열은 **자르지 않고 거절한다** (FR-341).

    자르면 대상 페이지에 사용자가 의도하지 않은 값이 들어가고 그 Step 이 그대로 저장된다.
    """
    reason = refused({"kind": "text.insert", "text": "가" * (MAX_TEXT_LENGTH + 1)})
    assert "잘라서 보내지 않고 거절합니다" in reason
    assert len(ok({"kind": "text.insert", "text": "가" * MAX_TEXT_LENGTH})["text"]) == (
        MAX_TEXT_LENGTH
    )


def test_unknown_modifier_bits_are_refused() -> None:
    """알 수 없는 수정자 비트를 그대로 넘기지 않는다 (FR-341).

    CDP 가 그 비트를 어떻게 해석할지 이 코드가 답할 수 없다.
    """
    assert ok({"kind": "key.down", "key": "a", "code": "KeyA", "modifiers": 0b1111})
    for bad in (16, 1024, -1):
        assert "알 수 없는 수정자" in refused(
            {"kind": "key.down", "key": "a", "code": "KeyA", "modifiers": bad}
        )


def test_unknown_buttons_are_refused() -> None:
    assert "알 수 없는 버튼" in refused({"kind": "pointer.down", "x": 1, "y": 1, "button": "back"})


def test_tabs_that_do_not_exist_are_refused() -> None:
    """없는 탭에는 보내지 않는다 (FR-341).

    번호를 그냥 넘기면 세션이 그 번호를 어떻게 해석할지 여기서 답할 수 없다.
    """
    assert "없습니다" in refused({"kind": "pointer.move", "x": 1, "y": 1, "tab": 7})
    assert ok({"kind": "pointer.move", "x": 1, "y": 1, "tab": 1})["tab"] == 1


def test_pointer_events_are_refused_before_the_first_frame() -> None:
    """프레임을 한 장도 못 받았으면 좌표를 보낼 근거가 없다 (FR-333).

    무엇을 클릭하는지 볼 수 없는 상태에서 좌표를 보내면, 그것은 조작이 아니라 추측이다.
    """
    reason = refused(
        {"kind": "pointer.down", "x": 10, "y": 10, "button": "left"},
        frame_width=None,
        frame_height=None,
    )
    assert "한 장도 받지 못해" in reason


def test_non_pointer_events_do_not_need_a_frame() -> None:
    """키 입력은 프레임이 없어도 성립한다 — 좌표를 쓰지 않기 때문이다.

    초점이 이미 어느 요소에 있으면 화면을 못 봐도 타이핑은 그 요소로 간다. 프레임 없음을
    이유로 키를 막으면 화면이 잠깐 끊긴 사이의 입력이 유실된다.
    """
    assert ok(
        {"kind": "key.down", "key": "a", "code": "KeyA"},
        frame_width=None,
        frame_height=None,
    )


def test_file_attach_limits_the_count() -> None:
    """파일 개수 상한 (FR-337a). 상한 없는 수신 경로를 두지 않는다."""
    assert ok({"kind": "file.attach", "fileIds": ["f1", "f2"]})["fileIds"] == ["f1", "f2"]
    assert "까지입니다" in refused(
        {"kind": "file.attach", "fileIds": [f"f{i}" for i in range(MAX_FILE_IDS + 1)]}
    )
    assert "지정할 파일이 없습니다" in refused({"kind": "file.attach", "fileIds": []})


def test_composition_range_must_be_two_integers() -> None:
    assert ok({"kind": "ime.compose", "text": "주", "compositionRange": [0, 1]})
    for bad in ("0,1", [1], [1, 2, 3], [1.5, 2]):
        assert "조합 구간" in refused(
            {"kind": "ime.compose", "text": "주", "compositionRange": bad}
        )


def test_validation_drops_unknown_fields() -> None:
    """검증을 지난 사건에는 **알려진 필드만** 남는다.

    사용자가 보낸 것을 그대로 CDP 로 넘기면, 목록에 없는 파라미터가 함께 간다. 무엇이
    나가는지는 이 함수가 만든 사전이 정한다.
    """
    clean = ok(
        {
            "kind": "pointer.down",
            "x": 1,
            "y": 2,
            "button": "left",
            "cdpParams": {"interceptDrags": True},
            "__proto__": "x",
        }
    )
    assert set(clean) == {"kind", "tab", "modifiers", "x", "y", "button"}


def test_non_object_events_are_refused() -> None:
    for bad in ("pointer.down", 42, None, ["pointer.down"]):
        assert "객체여야 합니다" in refused(bad)  # type: ignore[arg-type]
