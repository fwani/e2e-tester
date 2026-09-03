"""편집 엔드포인트 계약. FR-035a·FR-043a (T094). contracts/rest-api.md §일시정지 중 편집.

**게이트가 이 계약의 핵심이다.** 편집은 `PAUSED` 에서만 받는다. 다른 상태에서 받으면
정의는 바뀌었는데 브라우저는 그 사이에 계속 조작되고 있어, 어느 시점의 화면에 대해 편집한
것인지 아무도 모르게 된다.

브라우저를 띄우지 않고 세션 작업 상태를 직접 만든다 — 게이트 판정은 상태 값 하나에만
의존하므로, 실제 브라우저를 띄우면 검증하려는 것과 무관한 시간과 실패 원인이 늘어난다.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from itb.api.routes import sessions as sessions_mod
from itb.api.routes.sessions import SessionWork
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep, FillStep
from itb.execution.state_machine import SessionState

EDIT_ENDPOINTS: list[tuple[str, str, dict[str, Any] | None]] = [
    ("post", "/steps", {"step": {}}),
    ("patch", "/steps/step-01", {"label": "바꾼 이름"}),
    ("delete", "/steps/step-01", None),
    ("post", "/steps:reorder", {"order": ["step-01"]}),
    ("post", "/assertions", {"kind": "url", "value": "https://example.com"}),
    ("post", "/steps/step-01/repick", {"slot": "target"}),
]
"""FR-035a 게이트가 걸려야 하는 엔드포인트 전부."""


def _target() -> TargetLocator:
    return TargetLocator(css=Candidate(value="#a", status=CandidateStatus.VERIFIED))


class _FakeSession:
    """상태 게이트만 판정하면 되므로 브라우저 없는 대역을 쓴다."""

    def __init__(self, state: SessionState) -> None:
        self.state = state
        self.session_id = "fake"
        self.test_id = None
        self.current_step_index = 1
        self.edit_warnings: list[str] = []
        self.active_tab_index = 0
        self.mirrored_tab_index = 0
        self.emitted: list[tuple[str, dict[str, Any]]] = []

    def open_tabs(self) -> list[object]:
        return []

    def find_tab(self, _index: int) -> None:
        return None

    def add_edit_warning(self, message: str) -> None:
        self.edit_warnings.append(message)

    async def publish_edit_warnings(self) -> None:
        return None

    async def emit(self, event_type: str, **payload: Any) -> None:
        self.emitted.append((event_type, payload))

    async def bring_tab_to_front(self, _index: int) -> None:
        return None


class _FakeRecorder:
    test_id_attribute = "data-testid"
    warnings: list[str] = []  # noqa: RUF012 - 대역이며 인스턴스마다 바뀌지 않는다
    sensitive_captures: list[object] = []  # noqa: RUF012

    def seed_step_seq(self, _existing: int) -> None:
        return None


@pytest.fixture
def worked_client(client: TestClient) -> Iterator[tuple[TestClient, str]]:
    """편집 대상 Step 이 있는 가짜 세션을 등록한 클라이언트."""
    session = _FakeSession(SessionState.REPLAYING)
    work = SessionWork(
        session=session,  # type: ignore[arg-type]
        recorder=_FakeRecorder(),  # type: ignore[arg-type]
        steps=[
            ClickStep(id="step-01", label="첫 클릭", target=_target()),
            FillStep(id="step-02", label="입력", target=_target(), value="v"),
        ],
    )
    work.session.current_step_index = 1
    sessions_mod._WORK["fake"] = work
    try:
        yield client, "fake"
    finally:
        sessions_mod._WORK.pop("fake", None)


@pytest.mark.parametrize(("method", "path", "body"), EDIT_ENDPOINTS)
def test_edit_requires_paused(
    worked_client: tuple[TestClient, str], method: str, path: str, body: dict | None
) -> None:
    """FR-035a — `PAUSED` 가 아니면 `409 NOT_PAUSED`."""
    client, sid = worked_client
    call = getattr(client, method)
    resp = call(f"/api/sessions/{sid}{path}", **({"json": body} if body else {}))
    assert resp.status_code == 409, f"{method} {path} → {resp.status_code} {resp.text}"
    error = resp.json()["error"]
    assert error["code"] == "NOT_PAUSED"
    assert error["detail"]["state"] == "replaying"
    assert "일시정지" in error["message"]


def test_unknown_session_is_404(client: TestClient) -> None:
    resp = client.delete("/api/sessions/없는세션/steps/step-01")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_delete_returns_steps_and_warnings(
    worked_client: tuple[TestClient, str],
) -> None:
    """편집 응답은 `steps` + `edit_warnings` + `current_step_index` 다."""
    client, sid = worked_client
    sessions_mod._WORK[sid].session.state = SessionState.PAUSED  # type: ignore[attr-defined]

    resp = client.delete(f"/api/sessions/{sid}/steps/step-01")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"steps", "edit_warnings", "current_step_index"}
    assert [s["id"] for s in body["steps"]] == ["step-02"]
    assert body["edit_warnings"], "이미 실행된 Step 을 지웠으므로 경고가 있어야 한다"
    assert body["current_step_index"] == 0


def test_missing_step_is_404(worked_client: tuple[TestClient, str]) -> None:
    client, sid = worked_client
    sessions_mod._WORK[sid].session.state = SessionState.PAUSED  # type: ignore[attr-defined]
    resp = client.delete(f"/api/sessions/{sid}/steps/step-99")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_reorder_rejects_mismatched_set(worked_client: tuple[TestClient, str]) -> None:
    """부분 적용하지 않는다 — 절반만 옮긴 목록은 사용자가 의도한 어떤 상태도 아니다."""
    client, sid = worked_client
    sessions_mod._WORK[sid].session.state = SessionState.PAUSED  # type: ignore[attr-defined]
    resp = client.post(
        f"/api/sessions/{sid}/steps:reorder", json={"order": ["step-02"]}
    )
    assert resp.status_code == 400
    detail = resp.json()["error"]["detail"]
    assert detail["expected"] == ["step-01", "step-02"]


def test_insert_rejects_invalid_step_shape(
    worked_client: tuple[TestClient, str],
) -> None:
    """FR-085 — 경계에서 검증한다. 형식이 틀리면 사유를 그대로 알린다."""
    client, sid = worked_client
    sessions_mod._WORK[sid].session.state = SessionState.PAUSED  # type: ignore[attr-defined]
    resp = client.post(
        f"/api/sessions/{sid}/steps", json={"step": {"type": "click", "id": "나쁜id"}}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_insert_at_pause_position_keeps_it_next(
    worked_client: tuple[TestClient, str],
) -> None:
    """일시정지 위치에 넣은 Step 이 **다음에 실행될 것**이 된다.

    위치를 밀면 사용자가 방금 넣은 Step 이 조용히 건너뛰어진다.
    """
    client, sid = worked_client
    work = sessions_mod._WORK[sid]
    work.session.state = SessionState.PAUSED  # type: ignore[attr-defined]

    resp = client.post(
        f"/api/sessions/{sid}/steps",
        json={
            "step": {
                "id": "step-09",
                "type": "navigate",
                "label": "이동",
                "url": "https://example.com",
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_step_index"] == 1
    assert body["steps"][1]["id"] == "step-09"
    assert body["edit_warnings"] == []


def test_repick_on_step_without_slot_is_rejected(
    worked_client: tuple[TestClient, str],
) -> None:
    """`drop_target` 이 없는 Step 에 그 슬롯을 요구하면 거절한다 (T166).

    조용히 무시하면 사용자는 갱신됐다고 오해한다.
    """
    client, sid = worked_client
    sessions_mod._WORK[sid].session.state = SessionState.PAUSED  # type: ignore[attr-defined]
    resp = client.post(
        f"/api/sessions/{sid}/steps/step-01/repick", json={"slot": "drop_target"}
    )
    assert resp.status_code == 400
    assert "drop_target" in resp.json()["error"]["message"]
