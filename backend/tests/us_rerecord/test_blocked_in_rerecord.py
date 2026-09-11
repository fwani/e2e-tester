"""재녹화 중 AI 가 막혔을 때. 016 FR-041·FR-043 (T040a).

기존 동작의 재사용이지만 **경로는 이번에 처음 생긴다** — `PAUSED → AI_RUNNING →
AI_BLOCKED` 는 016 이 더한 전이(`PAUSED + BEGIN_AI`)를 지나야 닿는다. 재사용이 실제로
재사용인지 확인하는 것이 이 파일이다.

원칙 III (NON-NEGOTIABLE): 「When an AI Step fails, the session MUST be held open so
the user can take over in place. Failure MUST NOT tear down the browser.」
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us4_support import install_driver, report_blocked
from tests.us_rerecord.support import open_rerecord, say, step_ids

pytestmark = pytest.mark.browser


def test_a_block_keeps_the_browser_and_offers_the_choices(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """막혀도 **브라우저를 닫지 않고** 5선택지를 준다 (FR-041 · 원칙 III).

    닫으면 사용자가 이어받을 화면이 사라진다 — 「직접 수행」을 골라도 무엇을 할 수
    없다.
    """
    install_driver(
        monkeypatch,
        [report_blocked("어느 계정으로 로그인할지 모르겠습니다", "어느 계정인가요?")],
    )
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        view = say(keyed_client, sid, "로그인해 줘")

        assert view["state"] == "ai_blocked", f"막힘 상태가 아니다: {view['state']}"
        # **브라우저가 살아 있다** — 탭을 물어볼 수 있다는 것이 그 증거다.
        tabs = keyed_client.get(f"/api/sessions/{sid}/tabs")
        assert tabs.status_code == 200, "브라우저가 닫혔다 — 원칙 III 위반"

        # 5선택지가 그대로 온다 (016 이 이 목록을 바꾸지 않는다).
        allowed = set(view["allowed_commands"])
        for choice in ("choose_takeover", "choose_answer", "choose_retry", "choose_skip"):
            assert choice in allowed, f"선택지가 빠졌다: {choice}"
    finally:
        stop_quietly(keyed_client, sid)


def test_steps_made_before_the_block_survive(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """막히기 **전에** 만든 Step 은 보존된다 (FR-043 · FR-067).

    보존되지 않으면 사용자는 막힐 때마다 처음부터 다시 해야 하고, 그러면 막힘 처리에
    5선택지를 두는 뜻이 없다 — 「다시 시도」가 실제로는 「처음부터」가 된다.
    """
    from tests.us4_support import assert_url_contains, observe

    # **화면에 있는 것만 다룬다.** 도착점은 앞 구간이 끝난 자리이고, 그 화면에 무엇이
    # 있는지는 픽스처 앱의 사정이다. 여기서 보려는 것은 「막히기 전에 만든 Step 이
    # 남는가」이지 「AI 가 무엇을 할 수 있는가」가 아니므로, 화면과 무관하게 성공하는
    # 동작(주소 검증)으로 Step 하나를 만든다.
    install_driver(
        monkeypatch,
        [
            observe(),
            assert_url_contains("/"),
            report_blocked("다음에 무엇을 할지 모르겠습니다", "어디로 가야 하나요?"),
        ],
    )
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        before = step_ids(keyed_client, sid)
        view = say(keyed_client, sid, "로그인해 줘")
        after = step_ids(keyed_client, sid)

        assert view["state"] == "ai_blocked"
        # 만들어진 것이 있으면 남아 있어야 하고, 없으면 목록이 그대로여야 한다.
        assert len(after) >= len(before), "막히면서 Step 이 사라졌다 — FR-067 위반"
        for old in before:
            assert old in after, f"옛 Step 이 사라졌다: {old}"

        # 재녹화 트랜잭션도 살아 있다 — 막힘은 교체를 끝내지 않는다.
        assert view["rerecord"] is not None, "막혔다고 교체가 취소되면 안 된다"
    finally:
        stop_quietly(keyed_client, sid)


def test_answering_resumes_inside_the_same_rerecord(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """답을 주면 **같은 교체 안에서** 이어 간다.

    막힘 답변은 016 이 만든 길이 아니라 기존 `AiChoice.ANSWER` 다. 그 길이 재녹화
    세션에서도 도는지, 그리고 돌고 나서 트랜잭션이 그대로인지 본다.
    """
    install_driver(monkeypatch, [report_blocked("모르겠습니다", "어느 계정인가요?")])
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        say(keyed_client, sid, "로그인해 줘")
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-choice",
            json={"choice": "answer", "answer": "admin 계정으로 하세요"},
        )
        assert resp.status_code in (200, 202), resp.text

        from tests.us_rerecord.support import wait_for_state

        view = wait_for_state(keyed_client, sid, {"paused", "ai_blocked"})
        assert view["rerecord"] is not None, "답변 뒤에도 교체는 진행 중이어야 한다"
    finally:
        stop_quietly(keyed_client, sid)
