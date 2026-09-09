"""미러 조작 모듈 (010 T013~T015 · FR-318·FR-344 · research R5).

이 파일이 지키는 것은 셋이다.

1. **두 미러 모듈의 경계** — `screencast.py` 는 `Input` 을 모르고 `input.py` 는 프레임을
   모른다. 010 이 조작을 열었지만 그 성질은 유지된다 (research R5). 경계가 무너지면
   FR-336(조작과 프레임이 서로를 막지 않는다)이 구조가 아니라 약속이 된다.
2. **명령 목록이 상한이다** (FR-344). 목록 밖 CDP 명령이 이 통로로 나가지 않는다.
3. **누른 포인터가 남지 않는다** (FR-318). 채널이 닫힐 때 서버가 `pointer.up` 을 보낸다 —
   클라이언트의 성실함에 기대지 않는다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from itb.mirror import input as mirror_input
from itb.mirror import screencast as sc
from itb.mirror.input import (
    ALLOWED_COMMANDS,
    MirrorCommandForbiddenError,
    TabInput,
)


class FakeCDP:
    """보낸 명령을 기록하는 CDP 세션."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self.detached = False

    async def send(self, command: str, params: dict[str, Any] | None = None) -> None:
        self.sent.append((command, dict(params or {})))

    async def detach(self) -> None:
        self.detached = True


class FakeContext:
    def __init__(self, cdp: FakeCDP) -> None:
        self._cdp = cdp

    async def new_cdp_session(self, _page: object) -> FakeCDP:
        return self._cdp


class FakePage:
    def __init__(self) -> None:
        self.cdp = FakeCDP()
        self.context = FakeContext(self.cdp)


async def attached() -> tuple[TabInput, FakeCDP]:
    page = FakePage()
    controller = TabInput(page, 0)  # type: ignore[arg-type]
    await controller.attach()
    return controller, page.cdp


def commands(cdp: FakeCDP) -> list[str]:
    return [name for name, _ in cdp.sent]


# ─── research R5: 두 모듈의 경계 (T013) ──────────────────────────────────────


def test_screencast_still_refuses_input_commands() -> None:
    """프레임 모듈의 명령 목록이 **늘지 않았다** (research R5 · FR-047a 의 잔여 성질).

    010 이 뒤집은 것은 「미러가 조작 경로를 갖지 않는다」가 아니라 「조작 경로가 아예
    없다」다. 조작은 `input.py` 가 자기 목록으로 담당하고, 이 파일에서 조작 명령을 보내려는
    시도는 계속 거부되어야 한다. 그러지 않으면 조작이 프레임 전달과 같은 CDP 세션을
    타게 되고, 그것이 FR-336 이 금지하는 상태다.
    """
    assert sc._ALLOWED_COMMANDS == {
        "Page.startScreencast",
        "Page.stopScreencast",
        "Page.screencastFrameAck",
    }


def test_the_two_mirror_modules_do_not_import_each_other() -> None:
    """`input.py` 는 프레임을 모르고 `screencast.py` 는 조작을 모른다 (research R5).

    **모듈을 나눈 기준이 「무엇을 모르는가」다.** 한쪽이 다른 쪽을 임포트하면 그 기준이
    사라지고, 두 통로가 서로를 막지 않는다는 성질을 코드에서 읽을 수 없게 된다.
    `lint-imports` 가 아니라 여기서 재는 이유는 이 관계가 계층 규칙이 아니라 **같은
    패키지 안의 두 모듈 사이의 약속**이기 때문이다.
    """
    input_src = Path(mirror_input.__file__).read_text(encoding="utf-8")
    cast_src = Path(sc.__file__).read_text(encoding="utf-8")

    input_imports = [
        line
        for line in input_src.splitlines()
        if line.startswith(("import ", "from ")) and "screencast" in line
    ]
    cast_imports = [
        line
        for line in cast_src.splitlines()
        if line.startswith(("import ", "from ")) and "mirror.input" in line
    ]
    assert input_imports == [], f"조작 모듈이 프레임 모듈을 임포트한다: {input_imports}"
    assert cast_imports == [], f"프레임 모듈이 조작 모듈을 임포트한다: {cast_imports}"


def test_the_two_command_lists_do_not_overlap() -> None:
    """두 목록의 교집합은 비어 있다. 같은 명령이 두 통로로 나갈 수 있으면 상한이 흐려진다."""
    assert ALLOWED_COMMANDS & sc._ALLOWED_COMMANDS == frozenset()


# ─── FR-344: 명령 목록이 상한이다 (T014) ─────────────────────────────────────


def test_allowed_commands_are_exactly_the_contract_list() -> None:
    """목록이 계약(contracts §2)과 같다. **조용히 늘지 않는다.**

    목록을 두는 이유는 나중에 "잠깐 이 CDP 명령 하나만" 이 들어오는 것을 막기 위해서다.
    늘리려면 이 검증이 먼저 실패하고, 그 자리에서 무엇을 여는지 적게 된다.
    """
    assert ALLOWED_COMMANDS == {
        "Input.dispatchMouseEvent",
        "Input.dispatchKeyEvent",
        "Input.insertText",
        "Input.imeSetComposition",
        "DOM.setFileInputFiles",
    }


def test_no_script_execution_command_is_allowed() -> None:
    """페이지 스크립트 실행·임의 브라우저 제어 경로가 없다 (FR-344 · 헌법 보안 요건)."""
    forbidden = {
        "Runtime.evaluate",
        "Runtime.callFunctionOn",
        "Page.navigate",
        "Page.addScriptToEvaluateOnNewDocument",
        "Browser.close",
        "Network.setCookies",
    }
    assert ALLOWED_COMMANDS & forbidden == frozenset()


@pytest.mark.asyncio
async def test_send_rejects_commands_outside_the_list() -> None:
    """목록 밖 전송은 함수 자체가 거절한다 (FR-344)."""
    cdp = FakeCDP()
    with pytest.raises(MirrorCommandForbiddenError):
        await mirror_input._send(cdp, "Runtime.evaluate", {"expression": "1"})  # type: ignore[arg-type]
    assert cdp.sent == [], "거절한 명령이 실제로 나갔다"


@pytest.mark.asyncio
async def test_dispatch_rejects_unknown_event_kinds() -> None:
    """사건 종류 목록도 상한이다 (data-model §1).

    채널 경계의 검증과 **이중으로** 막는다. 채널을 우회해 이 모듈을 직접 부르는 경로가
    나중에 생겨도 목록 밖은 나가지 않는다.
    """
    controller, cdp = await attached()
    with pytest.raises(MirrorCommandForbiddenError):
        await controller.dispatch({"kind": "script.eval", "text": "alert(1)"})
    assert cdp.sent == []


@pytest.mark.asyncio
async def test_dispatch_without_attach_is_refused() -> None:
    """세션이 붙지 않은 상태에서는 조작을 받지 않는다."""
    controller = TabInput(FakePage(), 0)  # type: ignore[arg-type]
    with pytest.raises(MirrorCommandForbiddenError):
        await controller.dispatch({"kind": "pointer.move", "x": 1, "y": 1})


# ─── contracts §2 의 표: 사건 → CDP 명령 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_each_event_kind_maps_to_the_contracted_command() -> None:
    """계약의 표대로 변환된다. 표와 코드가 갈리면 화면과 대상 페이지가 갈린다."""
    expected = [
        ({"kind": "pointer.down", "x": 10, "y": 20, "button": "left"}, "Input.dispatchMouseEvent"),
        ({"kind": "pointer.up", "x": 10, "y": 20, "button": "left"}, "Input.dispatchMouseEvent"),
        ({"kind": "pointer.move", "x": 11, "y": 21}, "Input.dispatchMouseEvent"),
        ({"kind": "wheel", "x": 5, "y": 5, "deltaX": 0, "deltaY": 300}, "Input.dispatchMouseEvent"),
        ({"kind": "key.down", "key": "a", "code": "KeyA"}, "Input.dispatchKeyEvent"),
        ({"kind": "key.up", "key": "a", "code": "KeyA"}, "Input.dispatchKeyEvent"),
        ({"kind": "text.insert", "text": "주문"}, "Input.insertText"),
        ({"kind": "ime.compose", "text": "주"}, "Input.imeSetComposition"),
        ({"kind": "ime.commit", "text": "주문"}, "Input.insertText"),
        ({"kind": "file.attach", "paths": ["a.txt"]}, "DOM.setFileInputFiles"),
    ]
    for event, command in expected:
        controller, cdp = await attached()
        await controller.dispatch(event)
        assert commands(cdp) == [command], f"{event['kind']} 가 {commands(cdp)} 로 갔다"


@pytest.mark.asyncio
async def test_wheel_carries_the_deltas() -> None:
    """휠이 이동량을 그대로 싣는다. 싣지 않으면 스크롤이 일어나지 않는다."""
    controller, cdp = await attached()
    await controller.dispatch({"kind": "wheel", "x": 5, "y": 5, "deltaX": 0, "deltaY": 300})
    _, params = cdp.sent[0]
    assert params["type"] == "mouseWheel"
    assert params["deltaY"] == 300


@pytest.mark.asyncio
async def test_composition_range_is_clamped_to_the_text() -> None:
    """조합 구간이 문자열을 벗어나지 않는다.

    CDP 는 범위를 벗어난 값에 어떻게 반응하는지 보장하지 않는다. 여기서 좁히는 편이
    대상 페이지가 예상 밖으로 반응하는 것보다 낫다.
    """
    controller, cdp = await attached()
    await controller.dispatch({"kind": "ime.compose", "text": "주문", "compositionRange": [5, 99]})
    _, params = cdp.sent[0]
    assert params["selectionStart"] == 2
    assert params["selectionEnd"] == 2


# ─── FR-318: 누른 포인터가 남지 않는다 (T015) ────────────────────────────────


@pytest.mark.asyncio
async def test_drag_carries_the_button_while_moving() -> None:
    """누른 채 이동하면 그 버튼을 실어 보낸다 — 끌어놓기의 중간이다.

    `buttons` 가 0 이면 대상 페이지는 끌기가 아니라 단순 이동으로 읽고 `dragover` 가
    발생하지 않는다. 그러면 끌어놓기 녹화가 조용히 실패한다.
    """
    controller, cdp = await attached()
    await controller.dispatch({"kind": "pointer.down", "x": 10, "y": 10, "button": "left"})
    await controller.dispatch({"kind": "pointer.move", "x": 50, "y": 60})

    _, move = cdp.sent[1]
    assert move["type"] == "mouseMoved"
    assert move["buttons"] == 1, "누른 버튼이 이동 사건에 실리지 않았다"


@pytest.mark.asyncio
async def test_detach_releases_a_pressed_pointer(  # noqa: D103
) -> None:
    """누른 상태에서 통로를 닫으면 서버가 `pointer.up` 을 보낸다 (FR-318 · contracts §2).

    **클라이언트의 성실함에 기대지 않는다.** 끌어놓기 도중 탭이 닫히거나 연결이 끊기는
    것을 클라이언트는 알 수 없고, 그때 대상 페이지는 누른 상태로 남는다.
    """
    controller, cdp = await attached()
    await controller.dispatch({"kind": "pointer.down", "x": 10, "y": 10, "button": "left"})
    assert controller.pressed_buttons == ("left",)

    await controller.detach()

    releases = [p for name, p in cdp.sent if p.get("type") == "mouseReleased"]
    assert releases, "닫을 때 놓음을 보내지 않았다 — 대상 페이지가 누른 상태로 남는다"
    assert releases[-1]["x"] == 10
    assert controller.pressed_buttons == ()
    assert cdp.detached, "CDP 세션이 닫히지 않았다"


@pytest.mark.asyncio
async def test_release_happens_before_the_session_closes() -> None:
    """놓음이 세션을 닫기 **전에** 나간다. 순서가 반대면 보낼 통로가 없다."""
    controller, cdp = await attached()
    await controller.dispatch({"kind": "pointer.down", "x": 1, "y": 2, "button": "left"})
    await controller.detach()
    # detach() 뒤에도 기록이 남아 있으면 놓음이 먼저 나갔다는 뜻이다.
    assert any(p.get("type") == "mouseReleased" for _, p in cdp.sent)


@pytest.mark.asyncio
async def test_a_released_pointer_is_not_released_twice() -> None:
    """정상적으로 놓은 포인터는 다시 놓지 않는다. 두 번 놓으면 대상 페이지가 클릭을 둘로 읽는다."""
    controller, cdp = await attached()
    await controller.dispatch({"kind": "pointer.down", "x": 1, "y": 2, "button": "left"})
    await controller.dispatch({"kind": "pointer.up", "x": 1, "y": 2, "button": "left"})
    before = len([p for _, p in cdp.sent if p.get("type") == "mouseReleased"])
    await controller.detach()
    after = len([p for _, p in cdp.sent if p.get("type") == "mouseReleased"])
    assert after == before == 1


@pytest.mark.asyncio
async def test_release_survives_a_broken_session() -> None:
    """놓음이 실패해도 예외가 새지 않는다 (FR-348).

    조작 채널의 장애가 실행을 실패시켜서는 안 된다. 채널을 닫는 경로에서 예외가 나가면
    그 예외는 세션 정리 경로를 타고 실행으로 번진다.
    """

    class BrokenCDP(FakeCDP):
        async def send(self, command: str, params: dict[str, Any] | None = None) -> None:
            msg = "연결이 끊겼다"
            raise RuntimeError(msg)

    page = FakePage()
    page.cdp = BrokenCDP()
    page.context = FakeContext(page.cdp)  # type: ignore[assignment]
    controller = TabInput(page, 0)  # type: ignore[arg-type]
    await controller.attach()
    controller._pressed["left"] = (1.0, 2.0)

    await controller.detach()  # 예외가 새면 여기서 터진다
    assert controller.pressed_buttons == ()


# ─── FR-329: 민감 값이 이 모듈에 머무르지 않는다 (T051) ─────────────────────


def test_the_module_does_not_log_or_store_event_payloads() -> None:
    """조작 사건의 값을 남기지 않는다 (FR-329 · 헌법 보안 요건).

    미러 경로로도 비밀번호가 흐른다. 이 모듈이 사건을 로그로 남기거나 목록에 쌓으면 그
    값이 평문으로 남는다. **치환은 리코더가 Step 을 만드는 자리에서 일어나고**(기존
    파이프라인), 이 모듈은 값을 지나 보내기만 해야 한다.

    누른 포인터 추적(`_pressed`)은 좌표와 버튼만 담는다 — 문자열을 담지 않는다.
    """
    src = Path(mirror_input.__file__).read_text(encoding="utf-8")
    assert "logging" not in src, "조작 모듈이 로깅을 붙였다 — 민감 값이 로그로 샌다"
    assert "print(" not in src


@pytest.mark.asyncio
async def test_pressed_state_holds_no_text() -> None:
    """추적 상태에 문자열이 쌓이지 않는다 (FR-329)."""
    controller, _ = await attached()
    await controller.dispatch({"kind": "pointer.down", "x": 1, "y": 2, "button": "left"})
    await controller.dispatch({"kind": "text.insert", "text": "비밀번호평문"})
    assert controller._pressed == {"left": (1.0, 2.0)}
