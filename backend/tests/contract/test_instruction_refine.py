"""지시문 정제 — 계약과 경계 (025 US4 · T044~T046).

## 이 파일이 지키는 성질

**정제는 관문이 아니다** (FR-020). 실패해도 200 이고, 화면은 원문으로 진행하는 길을
연다. 400 으로 돌려주면 화면이 오류로 다루고, 그러면 정제가 작성을 막는다 — 이 기능의
경계가 정확히 그 반대다.

두 번째로 중요한 것은 **구체값 보존**이다 (FR-015). 등록의 주소와 수정의 주소가 다르다면
그 둘은 다른 값으로 남아야 한다. 하나로 합치는 순간 그 차이를 요점으로 삼는 테스트가
무의미해진다 — 이 기능에서 가장 위험한 실패다.

## 자격 증명 없이 돈다

`refine_instruction` 을 갈아 끼운다. 갈아 끼우는 것은 「모델이 무엇을 돌려주는가」이고,
검증되는 것은 그 뒤의 경로 전부 — 변환·치환·응답 형태다.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from itb.authoring.plan import Constraint, ConstraintScope, PlanItem, WorkPlan
from itb.authoring.refine import RefineResult, _plan_from_payload, _scrub_credentials


def _install(monkeypatch: pytest.MonkeyPatch, result: RefineResult) -> None:
    async def fake(_instruction: str, _config: Any = None) -> RefineResult:
        return result

    from itb.api.routes import ai as ai_mod

    monkeypatch.setattr("itb.authoring.refine.refine_instruction", fake)
    # 라우터가 함수 안에서 임포트하므로 모듈 속성을 갈아 끼우면 충분하다.
    assert ai_mod.router is not None


def test_success_returns_the_plan(
    keyed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """정제에 성공하면 계획이 온다."""
    _install(
        monkeypatch,
        RefineResult(
            refined=True,
            plan=WorkPlan(
                items=[PlanItem("i1", 1, "로그인한다")],
                constraints=[Constraint("기존 데이터를 쓰지 않는다")],
            ),
            notes=["자격 증명 1건을 변수 참조로 바꿨습니다."],
        ),
    )

    got = keyed_client.post("/api/ai/refine", json={"instruction": "로그인한다"})

    assert got.status_code == 200, got.text
    body = got.json()
    assert body["refined"] is True
    assert body["plan"]["items"][0]["text"] == "로그인한다"
    assert body["notes"]


def test_failure_is_also_two_hundred(
    keyed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**정제 실패는 200 이다** (FR-020).

    400 이면 화면이 오류로 다루고, 그러면 정제가 작성의 관문이 된다. 이 기능의 경계가
    정확히 그 반대다 — 실패해도 원문으로 진행할 수 있어야 한다.
    """
    _install(
        monkeypatch,
        RefineResult(refined=False, notes=["지시문을 정제하지 못했습니다."]),
    )

    got = keyed_client.post("/api/ai/refine", json={"instruction": "로그인한다"})

    assert got.status_code == 200, (
        "정제 실패가 오류 상태로 돌아왔다. 화면이 이것을 오류로 다루면 정제가 작성을 "
        "막는 관문이 된다 (FR-020)."
    )
    body = got.json()
    assert body["refined"] is False
    assert body["plan"] is None
    assert body["notes"]


def test_empty_instruction_is_refused_at_the_boundary(keyed_client: TestClient) -> None:
    """빈 지시문은 요청 검증에서 거절된다 — 정제 실패와 다른 사건이다."""
    got = keyed_client.post("/api/ai/refine", json={"instruction": ""})

    assert got.status_code == 422


def test_concrete_values_survive_in_their_own_places() -> None:
    """**자리마다 다른 값이 각각 남는다** (FR-015).

    이 기능에서 가장 위험한 실패다. 등록의 주소와 수정의 주소를 하나로 합치면 그 차이를
    요점으로 삼는 테스트가 무의미해진다.
    """
    plan = _plan_from_payload(
        {
            "items": [
                {"text": "새 메뉴를 등록한다"},
                {"text": "메뉴를 수정한다"},
            ],
            "constraints": [
                {"text": "연결 주소는 https://a.example 를 쓴다", "scope": "item", "item_index": 1},
                {"text": "연결 주소는 https://b.example 로 바꾼다", "scope": "item", "item_index": 2},
            ],
        }
    )

    texts = [c.text for c in plan.constraints]
    assert "https://a.example" in texts[0]
    assert "https://b.example" in texts[1]
    assert plan.constraints[0].item_id != plan.constraints[1].item_id


def test_a_constraint_pointing_nowhere_becomes_global() -> None:
    """없는 항목을 가리킨 제약을 **버리지 않는다.**

    제약을 잃는 것이 이 기능에서 가장 해로운 실패다. 어느 항목인지 몰라도 「어기면 안
    되는 것」이라는 사실은 남는다.
    """
    plan = _plan_from_payload(
        {
            "items": [{"text": "로그인한다"}],
            "constraints": [{"text": "중요한 규칙", "scope": "item", "item_index": 99}],
        }
    )

    assert len(plan.constraints) == 1
    assert plan.constraints[0].scope is ConstraintScope.GLOBAL


def test_plaintext_credentials_are_replaced_by_a_reference() -> None:
    """**평문 자격 증명이 참조로 바뀐다** (FR-010 · research R10).

    계획은 매 턴 다시 실리므로, 평문이 남으면 노출 표면이 턴 수만큼 늘어난다.

    바꾼 사실을 함께 알린다 — 조용히 바꾸면 사용자는 자기가 적은 값이 쓰이는 줄 안다.
    """
    text, notes = _scrub_credentials("관리자 계정 platform1 / 비밀번호: Sup3rSecret! 로 로그인")

    assert "Sup3rSecret!" not in text
    assert "{{password}}" in text
    assert "platform1" in text, "계정명은 남아야 한다 — 어느 계정인지를 말하는 정보다"
    assert notes


def test_the_product_scrubs_even_if_the_model_did_not() -> None:
    """**모델의 치환을 믿고 끝내지 않는다.**

    모델이 규칙을 어겼을 때 막을 것이 없으면 평문이 매 턴 다시 실린다. 지침에만 적어
    두지 않고 제품이 한 번 더 본다 (`report_blocked` 가 종류에 따라 질문을 버리는 것과
    같은 판단).
    """
    plan = _plan_from_payload(
        {"items": [{"text": "비밀번호: Sup3rSecret! 로 로그인한다"}]}
    )

    assert "Sup3rSecret!" not in plan.items[0].text
    assert "{{password}}" in plan.items[0].text


def test_refine_is_called_once_per_session(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**정제는 작성 시작 전 한 번뿐이다** (FR-021).

    매 턴 다시 정제하면 비용이 턴 수만큼 늘고, 더 나쁘게는 **사용자가 고친 계획이
    덮인다** — 정제는 원문을 보고 만들므로 손댐을 알지 못한다.

    이 검증은 세션이 도는 동안 정제 경로가 불리지 않음을 본다. 구조상 그럴 수 없지만
    (세션 생성은 `refine` 을 부르지 않는다), 누군가 「매 턴 최신 계획을 만들자」로 바꾸면
    여기서 걸린다.
    """
    calls: list[str] = []

    async def counting(instruction: str, _config: Any = None) -> RefineResult:
        calls.append(instruction)
        return RefineResult(refined=False, notes=["세지 않는다"])

    monkeypatch.setattr("itb.authoring.refine.refine_instruction", counting)

    keyed_client.post("/api/ai/refine", json={"instruction": "로그인한다"})
    assert len(calls) == 1

    created = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "ai",
            "start_url": f"{fixture_app}/login.html",
            "ai_instruction": "로그인한다",
            "work_plan": {
                "items": [
                    {"id": "i1", "order": 1, "text": "로그인한다", "status": "pending"}
                ],
                "constraints": [],
                "source": "refined",
            },
        },
    )
    assert created.status_code == 201, created.text

    assert len(calls) == 1, (
        f"세션 생성이 정제를 다시 불렀다 ({len(calls)}회). 정제는 시작 전 한 번뿐이고, "
        "다시 부르면 사용자가 고친 계획이 덮인다 (FR-021)."
    )

    session_id = created.json()["session_id"]
    keyed_client.post(f"/api/sessions/{session_id}/stop", json={"save": False})
