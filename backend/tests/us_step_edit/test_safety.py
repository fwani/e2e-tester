"""안전과 보존. 026 FR-018·FR-036·FR-038·FR-039·FR-040 · SC-004 (Polish).

analyze 가 찾은 커버리지 갭을 메운다. 전부 **「설계는 맞는데 검사가 없어 회귀를 볼 수
없는」** 형태였다.

가장 중요한 것은 `test_an_ai_edit_and_a_human_edit_are_indistinguishable` 이다 —
헌법 원칙 I 은 NON-NEGOTIABLE 이고, 그것을 지키는지 보는 검사가 이 하나다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us4_support import failing_driver, fill_password, install_driver, observe
from tests.us_rerecord.support import say
from tests.us_step_edit.support import open_step_edit, step_edit_of

pytestmark = pytest.mark.browser

SECRET = "step-edit-secret-not-a-real-one-9d2"


def saved_ids(client: TestClient, test_id: str) -> list[str]:
    return [s["id"] for s in client.get(f"/api/tests/{test_id}").json()["steps"]]


def step_of(client: TestClient, sid: str, step_id: str) -> dict[str, object]:
    steps = client.get(f"/api/sessions/{sid}").json()["steps"]
    return next(s for s in steps if s["id"] == step_id)


# ─── 원칙 I — 저장 형식에서 구별되지 않는다 (FR-018 · SC-004) ────────────────


def test_an_ai_edit_and_a_human_edit_are_indistinguishable(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**헌법 원칙 I (NON-NEGOTIABLE).**

    AI 가 고친 Step 과 사람이 같은 편집을 한 Step 이 저장 형식에서 구별되지 않아야
    한다. 작성 주체가 저장 형식에 남으면 「Human 과 AI 가 같은 테스트를 작성한다」는
    이 제품의 약속이 무너진다.

    두 세션에서 **같은 순수 함수**(`itb.execution.step_edits.update_step`)를 지나게
    하고 결과를 비교한다 — AI 의 `update_step` 도구가 그 함수를 부르고, 사람의
    `PATCH /steps/{id}` 도 같은 함수를 부른다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    # ① 사람이 고친다 — 수정 세션 밖, 기존 편집 경로
    human_sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(human_sid, str)
    try:
        resp = keyed_client.patch(
            f"/api/sessions/{human_sid}/steps/{target}", json={"label": "같은 이름"}
        )
        assert resp.status_code == 200, resp.text
        by_human = step_of(keyed_client, human_sid, target)
    finally:
        stop_quietly(keyed_client, human_sid)

    # ② 같은 편집을 다시 — 이번에는 AI 의 도구가 지나는 함수로
    ai_sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(ai_sid, str)
    try:
        from itb.api.routes.sessions import work_of  # noqa: PLC0415
        from itb.execution.step_edits import update_step  # noqa: PLC0415

        w = work_of(ai_sid)
        result = update_step(w.steps, w.current_step_index, target, label="같은 이름")
        w.steps = result.steps
        by_agent = step_of(keyed_client, ai_sid, target)
    finally:
        stop_quietly(keyed_client, ai_sid)

    # **`author` 는 예외다.** 헌법 원칙 I 이 provenance 를 메타데이터로 허용한다 —
    # 「MAY be recorded as metadata, but MUST NOT change how the Step executes」.
    # 금지되는 것은 작성 주체가 **실행이나 구조를 바꾸는 것**이고, 이 검사가 보는 것도
    # 그쪽이다. `author` 를 빼고 나머지가 한 글자도 다르지 않아야 한다.
    without_author = {k: v for k, v in by_human.items() if k != "author"}
    assert without_author == {k: v for k, v in by_agent.items() if k != "author"}, (
        "AI 가 고친 Step 과 사람이 고친 Step 이 저장 형식에서 구별된다 — 원칙 I 위반"
    )
    assert set(by_human) == set(by_agent), "한쪽에만 있는 필드가 생겼다 — 구조가 갈렸다"


# ─── 민감값 (FR-040) ────────────────────────────────────────────────────────


def test_a_secret_typed_while_fixing_becomes_a_reference(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """수정 중에 들어가는 값도 **기존 녹화와 같은 규칙**을 받는다 (FR-040).

    대화 이력·컨텍스트를 보는 검사와 **다른 경로**다 — 이쪽은 정의에 저장되는 값이다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(sid, str)
    try:
        install_driver(monkeypatch, [observe(), fill_password(SECRET)])
        say(keyed_client, sid, "비밀번호를 채워 줘")

        blob = repr(keyed_client.get(f"/api/sessions/{sid}").json()["steps"])
        assert SECRET not in blob, "평문 비밀번호가 정의에 들어갔다"
    finally:
        stop_quietly(keyed_client, sid)


def test_the_secret_never_appears_in_the_chat_history(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """대화 이력에도 남지 않는다 (FR-041 · SC-008)."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(sid, str)
    try:
        install_driver(monkeypatch, [observe(), fill_password(SECRET)])
        say(keyed_client, sid, "비밀번호를 채워 줘")

        history = keyed_client.get(f"/api/sessions/{sid}/chat").json()
        assert SECRET not in repr(history)
    finally:
        stop_quietly(keyed_client, sid)


# ─── 실패해도 보존한다 (FR-036·FR-038) ──────────────────────────────────────


def test_a_model_failure_keeps_what_was_done_so_far(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """언어모델 호출이 실패해도 **그때까지의 수정은 보존된다** (FR-038).

    도구 호출 상한과 **다른 실패 경로**다. 여기서 목록을 되돌리면 사용자는 자기가
    시킨 일이 통째로 사라지는 것을 본다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        before = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]

        from itb.authoring import agent as agent_mod  # noqa: PLC0415

        monkeypatch.setattr(
            agent_mod, "_sdk_driver", failing_driver(RuntimeError("모델을 부를 수 없습니다"))
        )
        keyed_client.post(f"/api/sessions/{sid}/chat", json={"text": "이 버튼 말고 저 버튼"})

        after = keyed_client.get(f"/api/sessions/{sid}").json()
        assert after["steps"] == before, "실패가 목록을 건드렸다"
        assert after["step_edit"] is not None, "실패가 트랜잭션을 조용히 닫았다"
    finally:
        stop_quietly(keyed_client, sid)


def test_a_blocked_agent_does_not_close_the_browser(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AI 가 막혀도 **브라우저를 닫지 않는다** (FR-036 · 헌법 원칙 III).

    막힌 자리에서 사람이 이어받을 수 있어야 한다 — 그것이 이 제품의 성질이고,
    새 세션 모드에서도 같아야 한다.
    """
    from tests.us4_support import report_blocked  # noqa: PLC0415

    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[-1])
    assert isinstance(sid, str)
    try:
        install_driver(monkeypatch, [observe(), report_blocked("어느 버튼인지 모르겠습니다")])
        say(keyed_client, sid, "그 버튼 눌러")

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] in {"ai_blocked", "paused"}, view["state"]
        assert view["step_edit"] is not None, "막힘이 수정을 닫았다"
    finally:
        stop_quietly(keyed_client, sid)


# ─── 세션 유실 (FR-039) ─────────────────────────────────────────────────────


def test_losing_the_session_says_what_happened_to_the_edit(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """세션이 유실되면 **확정되지 않은 수정의 운명이 명확해야** 한다 (FR-039).

    조용히 두면 사용자는 고쳐진 목록을 원본으로 착각한 채 저장한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(sid, str)
    view = step_edit_of(keyed_client, sid)
    assert view is not None

    # 중지가 세션을 끝낸다 — 유실의 통제된 형태다.
    stop_quietly(keyed_client, sid)
    after = keyed_client.get(f"/api/sessions/{sid}")
    if after.status_code == 200:
        # 세션이 남아 있으면 수정 상태가 **정리되어** 있어야 한다.
        assert after.json().get("step_edit") is None or after.json()["state"] in {
            "review",
            "stopped",
            "lost",
        }
