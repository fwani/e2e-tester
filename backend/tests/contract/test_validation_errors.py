"""요청 검증 실패(422)가 **앱 전체에서** 계약 형태로 나오는지 확인한다. DR-022·DR-030.

FastAPI 기본 응답은 `{"detail": [...]}` 이고 계약은 `{"error": {...}}` 다. 형태가
어긋나면 프런트엔드 추출기(`frontend/src/api/client.ts`)가 읽지 못하고 "요청이
실패했습니다 (422)." 라는 폴백만 남는다. 사용자가 "키 쌍 만들기를 하면 422 가 난다"고
겪은 것의 실체가 이것이다 (research R3).

**한 엔드포인트만 보지 않는다.** 전역 핸들러가 목적이므로 여러 엔드포인트에서 확인한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# (경로, 본문, 기대하는 위반 필드) — 서로 다른 검증 규칙을 하나씩 건드린다
CASES = [
    pytest.param("/api/keys/generate", {"passphrase": "short"}, "passphrase", id="min_length"),
    pytest.param(
        "/api/keys/generate", {"passphrase": "x" * 300}, "passphrase", id="max_length"
    ),
    pytest.param("/api/keys/generate", {"nope": 1}, "nope", id="extra_forbidden"),
    pytest.param("/api/sessions", {}, "mode", id="missing_required"),
    pytest.param(
        "/api/sessions", {"mode": "record", "start_url": "ftp://x"}, "start_url", id="pattern"
    ),
    pytest.param("/api/sessions", {"mode": "hologram"}, "mode", id="literal"),
]


@pytest.mark.parametrize(("path", "body", "field"), CASES)
def test_validation_error_uses_contract_shape(
    client: TestClient, path: str, body: dict, field: str
) -> None:
    resp = client.post(path, json=body)

    assert resp.status_code == 422, resp.text
    payload = resp.json()

    # 이것이 이 테스트의 핵심이다. 기본 형태가 새어 나오면 실패한다.
    assert "error" in payload, f"계약 형태가 아니다: {payload}"
    assert "detail" not in payload or isinstance(payload.get("detail"), type(None)), (
        f"FastAPI 기본 형태가 그대로 나갔다: {payload}"
    )

    error = payload["error"]
    assert error["code"] == "DEFINITION_INVALID"
    assert error["message"], "메시지가 비어 있으면 사용자가 원인을 알 수 없다"
    assert field in error["message"], f"어느 항목인지 메시지에 없다: {error['message']}"

    fields = error["detail"]["fields"]
    assert [f["loc"] for f in fields] == [field]
    assert fields[0]["reason"], "사유가 비어 있으면 조치할 수 없다"


def test_message_is_korean_not_raw_status(client: TestClient) -> None:
    """원시 상태 코드나 pydantic 내부 타입 이름이 사용자에게 가지 않아야 한다 (SC-107)."""
    resp = client.post("/api/keys/generate", json={"passphrase": "short"})
    message = resp.json()["error"]["message"]

    assert "422" not in message
    assert "string_too_short" not in message
    assert "8자 이상" in message, f"제약이 무엇인지 알려주지 않는다: {message}"


def test_multiple_violations_are_all_reported(client: TestClient) -> None:
    """항목이 여러 개 잘못됐으면 전부 알린다. 하나만 고치고 다시 막히면 안 된다."""
    resp = client.post("/api/sessions", json={"mode": "nope", "test_id": "bad-id"})

    assert resp.status_code == 422
    fields = resp.json()["error"]["detail"]["fields"]
    assert {f["loc"] for f in fields} == {"mode", "test_id"}


def test_input_value_is_not_echoed(client: TestClient) -> None:
    """검증 오류가 입력값을 되비추지 않는다.

    거절된 값이 민감 값일 수 있다. 오류 메시지를 타고 화면·로그로 새면 헌법 보안
    요구(민감 값 마스킹) 위반이다.
    """
    secret = "hunter2"  # 8자 미만이라 거절된다 — 거절된 값이 되비쳐지는지가 요점이다
    resp = client.post("/api/keys/generate", json={"passphrase": secret})

    assert resp.status_code == 422
    assert secret not in resp.text, f"입력값이 응답에 그대로 있다: {resp.text}"
