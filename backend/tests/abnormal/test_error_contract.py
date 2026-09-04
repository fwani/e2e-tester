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
