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
from tests.us_rerecord.support import (
    open_rerecord,
    say,
    step_ids,
    turns,
    wait_for_state,
)

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


def test_the_block_survives_a_reload(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**화면을 새로 고쳐도 막힘이 남는다** (2026-09-11 사용자 보고).

    ## 무엇이 문제였나

    사유·질문·선택지는 `ai_blocked` **이벤트로만** 갔다. 이벤트는 그 순간 붙어 있던
    화면에게만 간다 — 목록으로 나갔다 「이어서 보기」로 돌아온 화면은 상태가
    `ai_blocked` 인 것만 알고 무엇이 막았는지도, 무엇을 물었는지도, 무엇을 고를 수
    있는지도 몰랐다.

    실측에서 그 화면은 「고를 선택지가 없습니다」를 그렸고, 대화 패널은 「위의 답변 칸에
    알려 주세요」라고 말하는데 **그 칸이 없었다.** 남은 길은 세션을 버리는 것뿐이었다.

    005 U-18 이 같은 형태였고 그 고침이 `step_results` 였다 — 이벤트 없이도 화면이
    복원되게 한다. 이 검사는 **이벤트를 한 번도 보지 않고** 세션 조회만으로 막힘을
    복원할 수 있는지 본다.
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
        say(keyed_client, sid, "로그인해 줘")

        # **새로 붙은 화면이 하는 일 그대로** — 세션을 조회한다. 이벤트는 없다.
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        blocked = view.get("blocked")

        assert blocked is not None, (
            "세션 조회에 막힘이 없다 — 새로 고친 화면은 무엇이 막았는지 알 수 없다"
        )
        assert "어느 계정" in blocked["reason"]
        assert blocked["question"] == "어느 계정인가요?", (
            "질문이 없으면 화면이 답 칸을 무엇에 대해 여는지 말할 수 없다"
        )
        # 고를 것이 함께 온다 — 「고를 선택지가 없습니다」가 바로 이것이 없어서였다.
        assert "answer" in blocked["choices"]
        assert "takeover" in blocked["choices"]
    finally:
        stop_quietly(keyed_client, sid)


def test_the_block_is_gone_after_it_is_answered(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**지난 막힘은 남지 않는다.**

    상태가 아니라 마지막 결과만 보고 실으면, 이어받아 진행한 세션에도 막힘이 계속
    붙어 있다 — 화면은 답 칸을 다시 그리고 사용자는 이미 끝난 질문에 또 답한다.
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
        say(keyed_client, sid, "로그인해 줘")
        assert keyed_client.get(f"/api/sessions/{sid}").json()["blocked"] is not None

        # 사람이 답한다. 이 턴은 아무것도 하지 않고 끝난다.
        install_driver(monkeypatch, [])
        answered = keyed_client.post(
            f"/api/sessions/{sid}/ai-choice",
            json={"choice": "answer", "answer": "admin 계정으로 하세요"},
        )
        assert answered.status_code == 200, answered.text
        wait_for_state(keyed_client, sid, {"paused"})

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["blocked"] is None, "지난 막힘이 남아 있다 — 화면이 답 칸을 다시 연다"

        # **답과 그 뒤의 응답이 대화에 남는다** (2026-09-11 사용자 보고).
        # 남지 않으면 새로 고쳤을 때 사용자가 무엇을 알려 줬는지가 사라진다.
        said = [t["text"] for t in turns(keyed_client, sid) if t["role"] == "user"]
        assert any("admin 계정" in text for text in said), said
    finally:
        stop_quietly(keyed_client, sid)
