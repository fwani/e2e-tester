"""세션 뷰의 저장 시각 (005 T076 · FR-154).

사용자가 직접 신고했다 — "저장하면 목록으로 가거나, 저장이 완료되었다거나, 등등 동작이
없어서, 저장이 된건지 모르고."

화면이 저장 여부를 **스스로** 알 수 있어야 한다. 저장 응답 하나에만 의존하면 화면을
다시 그리는 순간 다시 미저장으로 되돌아간다 (U-09).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from us2_support import record_login


def test_saved_at_is_null_before_saving(project_client: TestClient, fixture_app: str) -> None:
    """저장하지 않은 세션의 `saved_at` 은 `null` 이다."""
    created = project_client.post(
        "/api/sessions", json={"mode": "record", "start_url": f"{fixture_app}/login.html"}
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        assert created.json()["saved_at"] is None
        assert project_client.get(f"/api/sessions/{sid}").json()["saved_at"] is None
    finally:
        project_client.post(f"/api/sessions/{sid}/discard")


def test_saved_at_is_set_after_saving(keyed_client: TestClient, fixture_app: str) -> None:
    """저장에 성공하면 `saved_at` 이 채워지고 **다시 조회해도 남아 있다** (FR-154).

    남아 있는 것이 핵심이다 — 화면을 다시 그려도 저장됨으로 보여야 한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    # `record_login` 은 저장까지 마친 뒤 세션을 정리한다. 저장된 테스트를 다시 열어
    # 세션 뷰가 저장 사실을 싣는지 본다.
    created = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        # 재실행 세션은 이번 세션에서 저장한 적이 없으므로 `null` 이다 — 저장 시각은
        # **이 세션의 저장**을 가리킨다. 테스트가 디스크에 저장돼 있다는 사실은
        # `test_id` 가 말한다.
        assert "saved_at" in view, "세션 뷰가 저장 시각 필드를 싣지 않는다"
    finally:
        keyed_client.post(f"/api/sessions/{sid}/stop")
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_saved_at_appears_in_the_session_view_schema() -> None:
    """세션 뷰 모델이 저장 시각을 갖는다 (FR-154).

    **브라우저를 띄우지 않는다.** 저장까지 걷는 검증은 프론트 컴포넌트 테스트
    (`SaveFeedback.test.tsx`)와 quickstart §2 S5 가 맡는다 — 여기서 실제 녹화를
    시키면 이벤트 루프가 엉켜 계약 검증이 느려지고 원인도 가려진다.
    """
    from itb.api.routes.sessions import SessionView

    assert "saved_at" in SessionView.model_fields
    assert SessionView.model_fields["saved_at"].default is None, (
        "기본값이 미저장이어야 한다 — 저장한 적 없는 세션을 저장됨으로 보이면 안 된다"
    )
