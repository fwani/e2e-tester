"""조작 위치 전환 (010 T078~T080 · US5 · FR-349·FR-351·FR-353).

**실제 창은 폴백이다.** 미러 조작이 통하지 않는 상황이 있고 — 강등, 제품이 대신 받을 수
없는 브라우저 요구, 그리고 사용자가 그냥 창에서 하고 싶은 경우 — 그때 남는 수단이다.

이 파일이 재는 것은 셋이다.

1. **전환해도 세션 상태와 녹화가 유지된다** (FR-349). 창을 여는 것은 브라우저를 새로
   만드는 것이 아니라 이미 살아 있는 탭을 앞으로 가져오는 것이다.
2. **창을 띄울 수 없으면 사유와 함께 거절한다** (FR-351). 조용히 실패하면 사용자는 창이
   어딘가 열렸는데 못 찾는 것으로 읽고 찾아 헤맨다.
3. **제품이 스스로 창을 열지 않는다** (FR-353). 강등이나 처리할 수 없는 요구가 발생해도
   자동 전환은 일어나지 않는다 — 요청하지 않은 창은 그 자체로 조작 위치를 잃게 만들고,
   화면 없는 기계에서는 그 시도가 실패한다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from itb.execution.session import HEADLESS_ENV

SURFACE_PATH = "/api/sessions/{sid}/control-surface"


def _start(client: TestClient, fixture_app: str) -> str:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])


def _surface_of(client: TestClient, session_id: str) -> str:
    from itb.api.routes.sessions import work_of

    return work_of(session_id).control_surface


def _steps(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    return list(client.get(f"/api/sessions/{session_id}").json()["steps"])


@pytest.mark.browser
def test_the_default_surface_is_the_mirror(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**기본 조작 위치는 미러다** (data-model §6 · FR-352 이후).

    001 에서는 반대였다 — 조작은 실제 창에서 했고 미러는 관찰용이었다. 010 이 그것을
    뒤집으므로 기본값도 뒤집힌다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        assert _surface_of(keyed_client, session_id) == "mirror"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_the_product_never_opens_a_window_on_its_own(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**제품이 상황을 판단해 창을 열지 않는다** (FR-353).

    강등도, 처리할 수 없는 요구도 전환을 일으키지 않는다. 요청하지 않은 창이 뜨는 것은
    그 자체로 조작 위치를 잃게 만들고, 화면 없는 기계에서는 그 시도가 실패한다.

    강등과 `unsupported` 를 **실제로 일으켜** 확인한다 — 코드를 읽어 「그런 경로가
    없다」고 말하는 것보다, 그 사건 뒤에도 위치가 그대로인 것을 보는 편이 낫다.
    """
    from itb.api.routes.sessions import work_of

    session_id = _start(keyed_client, fixture_app)
    try:
        w = work_of(session_id)

        # 강등을 알린다 — 미러가 1 FPS 로 내려간 상태다.
        async def degrade() -> None:
            await w.session.emit(
                "mirror_degraded", mode="screenshot", reason="검증이 만든 강등"
            )

        keyed_client.portal.call(degrade)  # type: ignore[attr-defined]

        # 처리할 수 없는 요구를 알린다.
        assert w.prompts is not None
        w.prompts.announce_unsupported("인증 요구 팝업입니다.", "실제 창에서 처리하세요.")

        async def settle() -> None:
            await asyncio.sleep(0.4)

        keyed_client.portal.call(settle)  # type: ignore[attr-defined]

        assert _surface_of(keyed_client, session_id) == "mirror", (
            "제품이 스스로 조작 위치를 창으로 옮겼다 (FR-353 위반)"
        )
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_switching_keeps_the_session_and_the_recording(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """전환해도 **세션 상태와 녹화가 유지된다** (FR-349 · 헌법 원칙 III).

    창을 여는 것은 `BrowserContext` 를 새로 만드는 것이 아니라 이미 살아 있는 탭을 앞으로
    가져오는 것이다 — 인증·화면·입력값이 그대로 남는 이유가 그것이다.

    **창을 띄울 수 없는 환경에서는 거절이 정상이다.** 그때 이 검증은 「거절도 세션을
    건드리지 않는다」를 확인한다 — 어느 쪽이든 세션이 무사해야 한다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        before_state = keyed_client.get(f"/api/sessions/{session_id}").json()["state"]
        before_url = keyed_client.get(f"/api/sessions/{session_id}/tabs").json()["tabs"][0][
            "url"
        ]
        before_steps = len(_steps(keyed_client, session_id))

        switched = keyed_client.post(
            SURFACE_PATH.format(sid=session_id), json={"surface": "window"}
        )
        assert switched.status_code in (200, 400, 501), switched.text

        after = keyed_client.get(f"/api/sessions/{session_id}").json()
        assert after["state"] == before_state, "전환이 세션 상태를 바꿨다"
        assert (
            keyed_client.get(f"/api/sessions/{session_id}/tabs").json()["tabs"][0]["url"]
            == before_url
        ), "전환이 화면을 옮겼다"
        assert len(_steps(keyed_client, session_id)) == before_steps, (
            "전환이 Step 을 만들었다 — 조작 위치는 Step 이 아니다"
        )

        if switched.status_code == 200:
            assert switched.json()["surface"] == "window"
            assert _surface_of(keyed_client, session_id) == "window"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_switching_back_to_the_mirror_always_works(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """미러로 돌아오는 것은 **어느 환경에서나 된다.**

    창은 있어야 열리지만 미러는 언제나 있다. 돌아오는 길이 환경에 달려 있으면, 창을
    열지 못하는 기계에서 한 번 잘못 전환한 사용자는 갇힌다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        back = keyed_client.post(
            SURFACE_PATH.format(sid=session_id), json={"surface": "mirror"}
        )
        assert back.status_code == 200, back.text
        assert back.json()["surface"] == "mirror"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_a_headless_machine_refuses_with_a_reason(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**창을 띄울 수 없으면 사유와 함께 거절한다** (FR-351).

    조용히 실패하면 사용자는 창이 어딘가 열렸는데 못 찾는 것으로 읽고 찾아 헤맨다 —
    FR-339 가 금지하는 형태다.

    판정 함수를 갈아 끼워 화면 없는 기계를 재현한다. 실제 환경 변수를 지우는 방법은
    macOS 개발 기계에서 재현되지 않는다 (거기서는 창 서버가 항상 있다).
    """
    from itb.api.routes import control

    monkeypatch.setattr(control, "can_open_a_window", lambda: False)

    session_id = _start(keyed_client, fixture_app)
    try:
        refused = keyed_client.post(
            SURFACE_PATH.format(sid=session_id), json={"surface": "window"}
        )
        assert refused.status_code == 400, refused.text
        body = refused.json()["error"]
        assert "띄울 창이 없어" in body["message"]
        # **다음에 할 일을 말한다** — 막힌 사용자에게 남는 수단이 무엇인지.
        assert body["next_action"], "거절에 다음 행동이 없다"
        assert "미러" in body["next_action"]
        # 거절이 위치를 바꾸지 않았다.
        assert _surface_of(keyed_client, session_id) == "mirror"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_switching_to_the_window_closes_the_mirror_control_channel(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """창으로 옮기면 미러의 조작 통로가 닫힌다.

    두 위치에서 동시에 조작이 들어오면 같은 화면에 두 벌의 입력이 섞이고, 어느 조작이
    어느 Step 이 되었는지 아무도 답할 수 없다 — 세션당 한 조작자라는 가정과 같은 이유다.
    """
    from itb.api.routes import control

    session_id = _start(keyed_client, fixture_app)
    try:
        with keyed_client.websocket_connect(f"/api/sessions/{session_id}/control") as ws:
            assert ws.receive_json()["state"] == "open"

            # **판정은 세션 단위다** (사용자 보고 2026-09-09 이후).
            #
            # 예전에는 `can_open_a_window()` 만 물었다. 그것은 기계에 화면이 있는지만
            # 답하므로 macOS 에서는 언제나 참이고, **창 없이 띄운 세션에서도 이 검증이
            # 전환을 기대했다.** 제품도 같은 맹점을 갖고 있었으므로 그때는 통과했다 —
            # 검증이 결함과 같은 착각을 공유하면 결함을 잡지 못한다.
            session = keyed_client.app.state.itb.sessions.require(session_id)
            if control.window_unavailable_reason(session) is not None:
                pytest.skip("이 세션은 옮겨 갈 창이 없어 전환 자체가 거절된다")

            switched = keyed_client.post(
                SURFACE_PATH.format(sid=session_id), json={"surface": "window"}
            )
            assert switched.status_code == 200, switched.text

            closing = ws.receive_json()
            assert closing["type"] == "control_state"
            assert closing["state"] == "closed"
            assert "실제 브라우저 창" in (closing["reason"] or "")
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_a_windowless_session_refuses_with_its_own_reason(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**창 없이 띄운 세션은 옮겨 갈 창이 없다** (FR-351 · 사용자 보고 2026-09-09).

    > 실제창에서 조작하기 변환이 안됨

    판정이 기계만 보고 있었다. macOS·Windows 는 창 서버가 항상 있으므로 `can_open_a_window()`
    는 언제나 참이었고, 서버는 **창 없이 띄운 브라우저에도** 「옮겼다」고 200 을 돌려주며
    미러의 조작 통로를 닫았다. 창은 어디에도 뜨지 않으니 사용자에게 조작할 곳이 하나도
    남지 않는다 — 조용한 실패이며 FR-351 이 금지하는 형태다.

    Chromium 의 창 유무는 **띄울 때 정해지고 나중에 바뀌지 않는다.** 그래서 여기서 할 수
    있는 정직한 일은 사유를 말하는 것이고, 이 검증이 그 사유가 실제로 나오는지를 본다.

    창을 띄운 세션(`ITB_HEADLESS=false`)에서는 이 검증이 성립하지 않으므로 건너뛴다 —
    제품 기본값은 창 없음이다 (FR-352).
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        session = keyed_client.app.state.itb.sessions.require(session_id)
        if not session.headless:
            pytest.skip("창을 띄운 세션이다 — 이 검증의 조건이 아니다")

        refused = keyed_client.post(
            SURFACE_PATH.format(sid=session_id), json={"surface": "window"}
        )
        assert refused.status_code == 400, refused.text
        body = refused.json()["error"]
        assert "창 없이 떠 있어" in body["message"], body["message"]
        # **이 기계에서 고칠 수 있는 사유다.** 고치는 방법을 말하지 않으면 사용자는
        # 기계를 탓하고 물러선다.
        assert HEADLESS_ENV in body["next_action"], body["next_action"]
        assert "미러" in body["next_action"]
        # 거절이 위치를 바꾸지 않았다.
        assert _surface_of(keyed_client, session_id) == "mirror"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_the_view_carries_the_surface_and_why_the_window_is_out_of_reach(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """세션 조회가 **조작 위치와 창이 안 되는 이유**를 함께 싣는다 (FR-349·FR-351·FR-234).

    둘 다 이벤트로만 흐르면 **새로 고친 화면이 잊는다.** `SessionWork.control_surface` 는
    처음부터 이 목적으로 있었는데 응답에 실리지 않아 쓰이지 않는 값이었다 — 서버는
    「창」이라고 알고 화면은 「미러」라고 아는 상태가 만들어졌다.

    이유를 **문장으로** 싣는 이유는 화면이 같은 뜻의 문구를 따로 갖지 않게 하기 위해서다
    (`wording.ts` 의 O13 옆 주석). 화면은 이것을 받아 버튼을 **누르기 전에** 잠근다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        view = keyed_client.get(f"/api/sessions/{session_id}").json()
        assert view["control_surface"] == "mirror"

        session = keyed_client.app.state.itb.sessions.require(session_id)
        reason = view["window_unavailable_reason"]
        if session.headless:
            assert reason is not None, "창 없는 세션인데 이유가 비어 있다"
            assert "창" in reason
        else:
            assert reason is None, f"창이 있는 세션인데 막는 이유가 있다: {reason}"
    finally:
        stop_quietly(keyed_client, session_id)
