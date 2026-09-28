"""요구한 경로가 보존된다 (020 T060 · FR-031·FR-032 · US1 AS-6 · US4).

## 먼저 — 이 검증이 **재지 못하는 것**

FR-031 은 「AI 가 요구한 동작을 할 수 없을 때 다른 경로로 대체하지 않는다」이다.
그 선택은 **모델의 판단**이고, 이 검증은 드라이버를 대본으로 갈아 끼우므로 바로 그
판단을 대체한다. 대본이 우회하지 않는다고 해서 모델이 우회하지 않는다는 뜻이 아니다.

**제품은 이 요구를 보장할 수 없다.** 지침 한 줄이 유일한 직접 방어이며, 그것은 모델이
어기면 막을 것이 없다. 이 한계는 spec 의 위험 표에도 적혀 있다.

그래서 이 파일은 **제품이 실제로 보장할 수 있는 셋**을 잡는다.

1. 지침에 그 규칙이 실제로 들어 있다 — 지워지면 여기서 실패한다
2. 우회하지 않기로 한 모델에게 **막다른 길을 주지 않는다** — `product_mismatch` 로
   보고하는 경로가 실제로 돈다
3. 그 보고에는 **질문이 붙지 않는다** — 답할 수 없는 질문 앞에 사용자를 세우지 않는다

`fixtures/sample-app/defective-save.html` 의 「빠른 저장」이 이 검증의 재료다. 그 버튼은
기대한 문구를 띄운다 — **우회할 수 있는데 하지 않아야** 「우회하지 않았다」가 뜻을 갖는다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly
from us4_support import (
    install_driver,
    observe,
    report_blocked,
    start_ai_session,
    wait_for_event,
)

from itb.authoring.agent import SYSTEM_PROMPT
from itb.authoring.nl_step import NL_STEP_SYSTEM_HINT

PAGE = "defective-save.html"


# ─── 1. 지침이 실제로 그 규칙을 담는다 (FR-001~FR-004·FR-031·FR-032) ─────────


@pytest.mark.parametrize(
    ("fragment", "why"),
    [
        ("지시문에서", "기대값의 출처가 지시문임을 말하지 않는다 (FR-001)"),
        ("화면에서 읽은 값으로 바꾸지 마세요", "관찰값 대체를 금지하지 않는다 (FR-001)"),
        ("값을 바꾸어 다시 시도하지 마세요", "재시도 금지가 없다 (FR-002)"),
        ("지어내지 마세요", "기대값을 지어내는 것을 금지하지 않는다 (FR-004)"),
        ("다른 경로로 대체하지", "우회 금지가 없다 (FR-031)"),
        ("product_mismatch", "우회 대신 무엇을 할지 말하지 않는다 (FR-023)"),
        ("사용자가 제품에 요구하는", "정의가 무엇인지 말하지 않는다 (FR-032)"),
    ],
)
def test_the_system_prompt_states_the_rule(fragment: str, why: str) -> None:
    """**이것이 FR-031 의 유일한 직접 방어다.**

    약한 방어이지만, 지워지지 않게 붙잡아 두는 것은 할 수 있다. 지침이 조용히 사라지면
    제품은 다시 버그를 정답으로 만든다.
    """
    assert fragment in SYSTEM_PROMPT, why


def test_the_action_rule_is_scoped_to_actions_only() -> None:
    """「성공한 것만 남는다」가 검증까지 덮으면 모델이 상충하는 두 규칙을 받는다.

    020 이전 문면이 정확히 그랬고, 그것이 이 기능이 고치는 원인 셋 중 하나다.
    """
    assert "화면을 조작하는 동작" in SYSTEM_PROMPT
    assert "검증은 다릅니다" in SYSTEM_PROMPT


def test_the_paused_path_carries_the_same_rule() -> None:
    """일시정지 중 자연어로 검증을 추가하는 경로도 같은 문제를 갖는다 (research R12).

    한쪽에만 규칙을 두면 「AI 작성에서는 지켜지는데 Step 추가에서는 안 지켜지는」 자리가
    생기고, 그 사실은 그 경로를 지나는 검증이 없을 때 드러나지 않는다.
    """
    assert "지시문에서" in NL_STEP_SYSTEM_HINT or "요청에서" in NL_STEP_SYSTEM_HINT
    assert "product_mismatch" in NL_STEP_SYSTEM_HINT


# ─── 2·3. 우회하지 않기로 한 모델에게 길이 있다 (FR-023·FR-024) ─────────────


def test_product_mismatch_reaches_the_user_without_a_question(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """제품이 요구와 다르게 동작해 막혔음을 **구별되는 종류로** 알린다.

    지금까지 이 상황은 「요소를 찾지 못했다」로 보고됐고, 사용자는 힌트를 주며 시간을
    쓴 뒤에야 제품 문제였음을 알았다.
    """
    reason = "저장해도 목록에 반영되지 않아 방금 만든 항목을 찾을 수 없습니다."
    install_driver(
        monkeypatch,
        [
            observe(0),
            # 모델이 「빠른 저장」으로 우회하지 않고 막힘을 고른 상황이다.
            report_blocked(reason=reason, question="어느 목록인가요?", kind="product_mismatch"),
        ],
    )
    sid = start_ai_session(
        keyed_client,
        fixture_app,
        "저장한 뒤 목록에서 방금 만든 항목을 찾는다.",
        page=PAGE,
    )
    try:
        payload = wait_for_event(event_log, "ai_blocked")
        assert payload["kind"] == "product_mismatch", payload
        assert payload["reason"] == reason
        # **질문이 버려진다.** 모델이 규칙을 어기고 실어 보내도 사용자 앞에 서지 않는다.
        assert payload["question"] is None, payload

        # 막다른 길이 아니다 — 사람이 이어받는 길은 그대로다 (FR-026).
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["blocked"]["kind"] == "product_mismatch"
        assert "takeover" in view["blocked"]["choices"]
    finally:
        stop_quietly(keyed_client, sid)


def test_ordinary_blocking_is_unchanged(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """모르는 것 때문에 막힌 경우는 그대로다 (FR-025).

    질문이 붙고, 사용자는 한 문장으로 풀 수 있다.
    """
    install_driver(
        monkeypatch,
        [observe(0), report_blocked(reason="어느 계정인지 모릅니다.", question="어느 계정입니까?")],
    )
    sid = start_ai_session(keyed_client, fixture_app, "로그인한다", page=PAGE)
    try:
        payload = wait_for_event(event_log, "ai_blocked")
        assert payload["kind"] == "needs_input", payload
        assert payload["question"] == "어느 계정입니까?"
    finally:
        stop_quietly(keyed_client, sid)
