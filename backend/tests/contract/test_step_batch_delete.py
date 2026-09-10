"""복수 삭제 계약. 011 FR-380~FR-388 · contracts/api-contract.md §1.

## 왜 새 엔드포인트인가

011 이전에 삭제는 `DELETE /steps/{step_id}` 하나뿐이었다. 뒤의 12개를 지우려면 12번
호출하고 12번 확인해야 했고 — 사용자 보고 4번이 그것이다 — **중간에 끊기면 부분 적용이
남았다.**

## 이 파일이 재는 것

계약의 네 축이다.

1. 형식 — `step_ids` 는 1개 이상, 각 항목 1~100자, 정의되지 않은 필드 거절
2. 응답 — 기존 편집 응답과 **같은 형**(`steps`·`edit_warnings`·`current_step_index`)
3. **원자성** — 하나라도 거절되면 아무것도 지워지지 않는다 (FR-388)
4. 게이트 — 다른 편집과 같이 `PAUSED` 에서만 받는다 (FR-035a)

3번이 이 엔드포인트의 존재 이유다. 나머지 셋은 기존 규칙을 깨지 않았다는 확인이다.
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


def _target() -> TargetLocator:
    return TargetLocator(css=Candidate(value="#a", status=CandidateStatus.VERIFIED))


class _FakeSession:
    """상태 게이트와 목록 조작만 재면 되므로 브라우저 없는 대역을 쓴다."""

    def __init__(self, state: SessionState) -> None:
        self.state = state
        self.session_id = "batch"
        self.test_id = None
        self.current_step_index = 2
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
def paused_client(client: TestClient) -> Iterator[tuple[TestClient, str]]:
    """Step 5개를 가진 일시정지 세션. 실행 위치는 2 (앞의 둘이 이미 실행됐다)."""
    session = _FakeSession(SessionState.PAUSED)
    work = SessionWork(
        session=session,  # type: ignore[arg-type]
        recorder=_FakeRecorder(),  # type: ignore[arg-type]
        steps=[
            ClickStep(id="step-01", label="하나", target=_target()),
            FillStep(id="step-02", label="둘", target=_target(), value="v"),
            ClickStep(id="step-03", label="셋", target=_target()),
            ClickStep(id="step-04", label="넷", target=_target()),
            ClickStep(id="step-05", label="다섯", target=_target()),
        ],
    )
    sessions_mod._WORK["batch"] = work
    try:
        yield client, "batch"
    finally:
        sessions_mod._WORK.pop("batch", None)


def _ids(work: SessionWork) -> list[str]:
    return [s.id for s in work.steps]


# ─── 1. 형식 ────────────────────────────────────────────────────────────────


def test_empty_list_is_rejected(paused_client: tuple[TestClient, str]) -> None:
    """대상이 0개인 요청은 받지 않는다. 지울 것이 없는 삭제는 조작이 아니다."""
    client, sid = paused_client
    resp = client.post(f"/api/sessions/{sid}/steps:delete", json={"step_ids": []})
    assert resp.status_code == 422, resp.text
    assert _ids(sessions_mod._WORK[sid]) == [
        "step-01",
        "step-02",
        "step-03",
        "step-04",
        "step-05",
    ]


def test_unknown_field_is_rejected(paused_client: tuple[TestClient, str]) -> None:
    """`extra="forbid"` — 오타가 조용히 무시되지 않는다."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete",
        json={"step_ids": ["step-01"], "stepIds": ["step-02"]},
    )
    assert resp.status_code == 422, resp.text


# ─── 2. 응답 ────────────────────────────────────────────────────────────────


def test_response_shape_matches_other_edits(paused_client: tuple[TestClient, str]) -> None:
    """다른 편집과 **같은 형**이다. 화면이 응답마다 다른 처리를 갖지 않게 한다."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-04", "step-05"]}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"steps", "edit_warnings", "current_step_index"}
    assert [s["id"] for s in body["steps"]] == ["step-01", "step-02", "step-03"]


def test_deletes_all_at_once(paused_client: tuple[TestClient, str]) -> None:
    """띄어져 있는 것도 한 번에 지운다 — 체크로 고른 것은 연속이 아닐 수 있다."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-01", "step-03", "step-05"]}
    )
    assert resp.status_code == 200, resp.text
    assert [s["id"] for s in resp.json()["steps"]] == ["step-02", "step-04"]


def test_execution_index_moves_by_removed_count(
    paused_client: tuple[TestClient, str],
) -> None:
    """실행 위치 **앞**에서 지운 개수만큼 당긴다. 단건 삭제를 반복한 것과 같은 값이다."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-01", "step-02"]}
    )
    assert resp.status_code == 200, resp.text
    # 실행 위치는 2 였고 앞의 둘을 지웠으므로 0 이다.
    assert resp.json()["current_step_index"] == 0


def test_warning_is_raised_once(paused_client: tuple[TestClient, str]) -> None:
    """이미 실행된 Step 을 지우면 경고. **개수만큼 쌓지 않는다** (009 FR-311 과 같은 판단)."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-01", "step-02"]}
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["edit_warnings"]) == 1


def test_emits_one_event_with_all_ids(paused_client: tuple[TestClient, str]) -> None:
    """이벤트도 한 번이다. 개수만큼 쏘면 화면이 중간 상태를 그린다."""
    client, sid = paused_client
    client.post(f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-03", "step-04"]})
    emitted = sessions_mod._WORK[sid].session.emitted  # type: ignore[attr-defined]
    removed = [p for t, p in emitted if t == "steps_removed"]
    assert len(removed) == 1, f"이벤트가 {len(removed)}번 나갔다"
    assert removed[0]["step_ids"] == ["step-03", "step-04"]


# ─── 3. 원자성 (FR-388) ─────────────────────────────────────────────────────


def test_unknown_id_deletes_nothing(paused_client: tuple[TestClient, str]) -> None:
    """**이 엔드포인트의 존재 이유다.** 하나라도 없으면 아무것도 지워지지 않는다."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete",
        json={"step_ids": ["step-01", "step-99", "step-03"]},
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    assert _ids(sessions_mod._WORK[sid]) == [
        "step-01",
        "step-02",
        "step-03",
        "step-04",
        "step-05",
    ], "부분 적용이 남았다 — 원자적이지 않다"


def test_duplicate_id_deletes_nothing(paused_client: tuple[TestClient, str]) -> None:
    """중복을 조용히 걸러 진행하면 「3개 지웠습니다」라고 답한 뒤 2개가 지워진다."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete",
        json={"step_ids": ["step-01", "step-01", "step-03"]},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    assert len(sessions_mod._WORK[sid].steps) == 5, "부분 적용이 남았다"


def test_no_event_when_rejected(paused_client: tuple[TestClient, str]) -> None:
    """거절된 요청은 이벤트도 내지 않는다 — 화면이 지워진 줄 알면 안 된다."""
    client, sid = paused_client
    client.post(f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-99"]})
    emitted = sessions_mod._WORK[sid].session.emitted  # type: ignore[attr-defined]
    assert [t for t, _ in emitted if t == "steps_removed"] == []


def test_deleting_everything_is_allowed(paused_client: tuple[TestClient, str]) -> None:
    """Step 0개가 되어도 막지 않는다. 저장이 기존 규칙대로 막는다 (data-model §5)."""
    client, sid = paused_client
    resp = client.post(
        f"/api/sessions/{sid}/steps:delete",
        json={"step_ids": ["step-01", "step-02", "step-03", "step-04", "step-05"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["steps"] == []


# ─── 4. 게이트 (FR-035a) ────────────────────────────────────────────────────


def test_requires_paused(paused_client: tuple[TestClient, str]) -> None:
    """다른 편집과 같은 게이트를 지난다. 새 엔드포인트가 예외를 만들지 않는다."""
    client, sid = paused_client
    sessions_mod._WORK[sid].session.state = SessionState.REPLAYING  # type: ignore[attr-defined]
    resp = client.post(f"/api/sessions/{sid}/steps:delete", json={"step_ids": ["step-01"]})
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "NOT_PAUSED"
    assert len(sessions_mod._WORK[sid].steps) == 5


def test_unknown_session_is_404(client: TestClient) -> None:
    resp = client.post("/api/sessions/없는세션/steps:delete", json={"step_ids": ["step-01"]})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


# ─── 단건 삭제는 그대로 남는다 (research R9) ────────────────────────────────


def test_single_delete_still_works(paused_client: tuple[TestClient, str]) -> None:
    """배치가 단건을 **대체하지 않는다.** 한 개를 지우는 데 목록을 실을 이유가 없다."""
    client, sid = paused_client
    resp = client.delete(f"/api/sessions/{sid}/steps/step-05")
    assert resp.status_code == 200, resp.text
    assert [s["id"] for s in resp.json()["steps"]] == [
        "step-01",
        "step-02",
        "step-03",
        "step-04",
    ]
