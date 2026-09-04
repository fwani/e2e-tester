"""T013 — 오류 계약이 스스로를 지키는지 훑는다 (RG-104-1 · EC-003 · EC-005).

개별 사례를 하나씩 확인하지 않는다. **모든 오류 코드**를 훑어 분류와 다음 행동이 빠진 것이
없는지 본다. 코드를 새로 만들고 대응표에 넣지 않으면 여기서 실패한다.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.domain.error import CATEGORY, NEXT_ACTION, Category, ErrorBody, ErrorCode
from tests.abnormal.catalogue import _LEAK

# ─── 대응표 전수성 (RG-104-1) ───────────────────────────────────────────────


def test_every_code_has_a_category() -> None:
    """분류가 빠진 코드가 있으면 그 코드의 오류는 분류되지 않은 채 나간다 (EC-001)."""
    missing = sorted(c.value for c in ErrorCode if c not in CATEGORY)
    assert not missing, f"분류가 없는 오류 코드: {missing}"


def test_every_code_has_a_next_action() -> None:
    """다음 행동은 비어 있을 수 없다 (EC-004)."""
    missing = sorted(c.value for c in ErrorCode if not NEXT_ACTION.get(c, "").strip())
    assert not missing, f"다음 행동이 없는 오류 코드: {missing}"


def test_category_table_has_no_stray_entries() -> None:
    """존재하지 않는 코드가 대응표에 남아 있으면 코드 삭제가 조용히 지나간 것이다."""
    known = set(ErrorCode)
    assert not (set(CATEGORY) - known), f"알 수 없는 코드가 대응표에 있다: {set(CATEGORY) - known}"
    assert not (set(NEXT_ACTION) - known), f"알 수 없는 코드: {set(NEXT_ACTION) - known}"


@pytest.mark.parametrize("code", list(ErrorCode), ids=lambda c: c.value)
def test_body_fills_category_and_next_action_from_the_code(code: ErrorCode) -> None:
    """호출부가 분류를 정하지 못한다 — 코드에서 결정된다 (EC-002)."""
    body = ErrorBody(code=code, message="테스트")
    assert body.category is CATEGORY[code]
    assert body.next_action.strip()


def test_caller_cannot_override_the_category() -> None:
    """분류를 손으로 적으면 코드와 어긋난다. 계약이 그것을 허용하지 않는다."""
    body = ErrorBody(code=ErrorCode.STEP_LIST_EMPTY, category=Category.BROKEN, message="x")
    assert body.category is Category.BLOCKED, "호출부가 넘긴 분류가 대응표를 이겼다"


# ─── 깨진 것과 막은 것의 구별 (EC-003) ──────────────────────────────────────


def test_internal_error_is_the_only_broken_code() -> None:
    """`broken` 코드가 정상 거부와 섞이면 분류 자체가 성립하지 않는다."""
    broken = {c.value for c, cat in CATEGORY.items() if cat is Category.BROKEN}
    assert broken == {"INTERNAL_ERROR"}, f"예상 밖의 broken 코드: {broken}"


def _app_that_crashes() -> FastAPI:
    """처리되지 않은 오류를 내는 경로를 붙인 앱. 제품 코드는 건드리지 않는다."""
    app = create_app()

    @app.get("/api/__crash__")
    async def _crash() -> None:
        raise RuntimeError("의도적으로 처리하지 않은 오류")

    return app


def test_unhandled_error_is_distinguishable_from_a_normal_rejection() -> None:
    """이 라운드가 존재하는 이유. 003 이전에는 둘 다 `DEFINITION_INVALID` 였다."""
    with TestClient(_app_that_crashes(), raise_server_exceptions=False) as client:
        crash = client.get("/api/__crash__")
        rejection = client.get("/api/project")  # 프로젝트가 열리지 않은 상태의 정상 거부

    assert crash.status_code == 500
    assert crash.json()["error"]["code"] == "INTERNAL_ERROR"
    assert crash.json()["error"]["category"] == "broken"

    assert rejection.status_code == 404
    assert rejection.json()["error"]["category"] == "blocked"

    # 코드만 보고 구별된다 — 메시지 문구를 해석할 필요가 없다 (EC-002)
    assert crash.json()["error"]["code"] != rejection.json()["error"]["code"]


def test_unhandled_error_leaks_no_internals() -> None:
    """스택도 내부 경로도 나가지 않는다. 진단은 서버 로그가 맡는다 (EC-005)."""
    with TestClient(_app_that_crashes(), raise_server_exceptions=False) as client:
        body = client.get("/api/__crash__").json()["error"]

    blob = json.dumps(body, ensure_ascii=False)
    leak = _LEAK.search(blob)
    assert leak is None, f"내부 정보가 노출됐다: {leak.group(0) if leak else ''!r}"
    assert "의도적으로 처리하지 않은 오류" not in blob, "예외 메시지가 그대로 나갔다"
    assert body["next_action"].strip(), "깨진 것에도 다음 행동이 있어야 한다"


# ─── 요청 검증 실패도 같은 규약을 따른다 ────────────────────────────────────


def test_validation_failure_follows_the_contract(client: TestClient) -> None:
    """422 도 분류와 다음 행동을 담는다. 이것이 없으면 앱의 모든 422 가 원인 불명이 된다."""
    resp = client.post("/api/project/create", json={})
    assert resp.status_code == 422
    body = resp.json()["error"]
    assert body["category"] == "blocked"
    assert body["next_action"].strip()
    assert body["message"].strip()


# ─── 상태 위반 거부는 지금 무엇이 가능한지 함께 말한다 (003 AP-020) ─────────


def test_state_violation_says_what_is_possible_now(project_client: TestClient) -> None:
    """"안 된다" 만 말하는 거부를 남기지 않는다.

    가능한 명령을 함께 주지 않으면 사용자는 되는 것을 하나씩 눌러 보며 찾아야 한다.
    목록은 상태 기계가 소유한 것을 그대로 읽으므로 여기와 어긋날 수 없다.

    상태 위반 거부는 두 갈래다 — 편집 게이트(`NOT_PAUSED`)와 전이 게이트
    (`INVALID_TRANSITION`). **둘 다** 본다. 한쪽만 고치면 다른 쪽에서 같은 막다른 골목이
    남는다.
    """
    from itb.execution.state_machine import SessionState, allowed_commands

    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": project_client.get("/api/project").json()[
            "default_start_url"
        ]},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        # ① 편집 게이트 — 녹화 중에는 Step 을 편집할 수 없다
        edit = project_client.post(
            f"/api/sessions/{sid}/steps",
            json={"step": {"type": "close_tab", "id": "step-01", "label": "탭 닫기"}},
        )
        assert edit.status_code == 409, edit.text
        detail = edit.json()["error"]["detail"]
        assert detail.get("allowed"), f"가능한 명령이 실리지 않았다: {detail}"
        assert set(detail["allowed"]) == {
            c.value for c in allowed_commands(SessionState(detail["state"]))
        }, "실린 목록이 상태 기계의 판정과 다르다"

        # ② 전이 게이트 — 녹화 중에는 이어서 실행할 것이 없다
        resumed = project_client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 409, resumed.text
        detail = resumed.json()["error"]["detail"]
        assert detail.get("allowed"), f"가능한 명령이 실리지 않았다: {detail}"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")
