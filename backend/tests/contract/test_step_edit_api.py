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
    # 009 — 손으로 넣는 입구도 같은 게이트를 지난다 (FR-306).
    ("post", "/steps:manual", {"spec": {"kind": "navigate", "url": "/a"}}),
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


# ─── 009 T022 · POST /steps:manual (FR-290·FR-306 · 계약 §4-2) ──────────────


def _paused(worked_client: tuple[TestClient, str]) -> tuple[TestClient, str]:
    client, sid = worked_client
    sessions_mod._WORK[sid].session.state = SessionState.PAUSED  # type: ignore[attr-defined]
    return client, sid


@pytest.mark.parametrize(
    ("spec", "expect_type"),
    [
        ({"kind": "navigate", "url": "/orders"}, "navigate"),
        ({"kind": "close_tab", "tab": 0}, "close_tab"),
        ({"kind": "assert_url", "url": "/done"}, "assertion"),
        ({"kind": "assert_text", "value": "완료"}, "assertion"),
    ],
)
def test_manual_네_종류를_넣을_수_있다(
    worked_client: tuple[TestClient, str], spec: dict[str, Any], expect_type: str
) -> None:
    client, sid = _paused(worked_client)

    resp = client.post(f"/api/sessions/{sid}/steps:manual", json={"spec": spec})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"steps", "edit_warnings", "current_step_index"}
    assert any(s["type"] == expect_type for s in body["steps"])


def test_manual_at_을_생략하면_일시정지_위치에_들어간다(
    worked_client: tuple[TestClient, str],
) -> None:
    """`InsertStepRequest` 와 같은 규칙이다 (`step_edits._clamp`)."""
    client, sid = _paused(worked_client)

    resp = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": "/orders"}},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 일시정지 위치는 1 이었다 — 그 자리에 들어간다.
    assert body["steps"][1]["type"] == "navigate"


def test_manual_넣은_step_이_다음에_실행된다(
    worked_client: tuple[TestClient, str],
) -> None:
    """실행 위치를 밀지 않는다 — 밀면 방금 넣은 Step 이 조용히 건너뛰어진다.

    `step_edits.insert_step` 의 규칙이며, 새 입구에도 그대로 적용된다.
    """
    client, sid = _paused(worked_client)

    resp = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": "/orders"}},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_step_index"] == 1
    assert body["steps"][body["current_step_index"]]["type"] == "navigate"


def test_manual_은_기존_step_added_이벤트를_쓴다(
    worked_client: tuple[TestClient, str],
) -> None:
    """새 이벤트를 만들지 않는다 — 화면이 같은 일을 두 가지로 듣게 하지 않는다."""
    client, sid = _paused(worked_client)

    client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": "/orders"}, "at": 0},
    )

    emitted = sessions_mod._WORK[sid].session.emitted  # type: ignore[attr-defined]
    kinds = [e[0] for e in emitted]
    assert "step_added" in kinds
    payload = next(p for k, p in emitted if k == "step_added")
    assert payload["at_index"] == 0


@pytest.mark.parametrize("kind", ["click", "fill", "select", "hover", "drag"])
def test_manual_요소를_요구하는_종류는_거절한다(
    worked_client: tuple[TestClient, str], kind: str
) -> None:
    """원칙 IV — 요청 모델에 그 종류가 없다 (FR-287)."""
    client, sid = _paused(worked_client)

    resp = client.post(
        f"/api/sessions/{sid}/steps:manual", json={"spec": {"kind": kind, "url": "/x"}}
    )

    assert resp.status_code == 422, resp.text


def test_manual_거절_응답에_넘어온_값이_실리지_않는다(
    worked_client: tuple[TestClient, str],
) -> None:
    """003 EC-005 — 이 입구도 같은 규칙을 지킨다."""
    client, sid = _paused(worked_client)
    secret = "비밀번호1234"

    resp = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "fill", "value": secret}},
    )

    assert resp.status_code == 422
    assert secret not in resp.text


def test_기존_입구의_거절_규칙이_그대로다(worked_client: tuple[TestClient, str]) -> None:
    """회귀 — 새 입구를 더하면서 기존 입구를 좁히지 않았다 (research R2)."""
    client, sid = _paused(worked_client)
    secret = "비밀번호1234"

    resp = client.post(
        f"/api/sessions/{sid}/steps",
        json={"step": {"type": "fill", "id": "나쁜id", "value": secret}},
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    assert secret not in resp.text


def test_세_입구가_같은_목록을_만든다(worked_client: tuple[TestClient, str]) -> None:
    """research R2 의 전제 — 삽입 규칙이 갈리지 않는다.

    같은 위치에 같은 종류를 넣으면 완성 Step 입구와 서술 입구의 결과가 같아야 한다.
    정의 편집 입구는 세션이 없으므로 `test_definition_edit_api.py` 가 본다.
    """
    client, sid = _paused(worked_client)
    raw = {
        "type": "navigate",
        "id": "step-09",
        "label": "주소로 이동 — /orders",
        "url": "/orders",
    }

    by_raw = client.post(f"/api/sessions/{sid}/steps", json={"step": raw, "at": 0})
    assert by_raw.status_code == 200, by_raw.text
    first = by_raw.json()["steps"][0]

    # 되돌리고 서술 입구로 같은 자리에 넣는다.
    assert client.delete(f"/api/sessions/{sid}/steps/step-09").status_code == 200
    by_spec = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": "/orders"}, "at": 0},
    )
    assert by_spec.status_code == 200, by_spec.text
    second = by_spec.json()["steps"][0]

    # id 만 다르다 — 자리·종류·라벨·작성자·값이 같다.
    assert {k: v for k, v in first.items() if k != "id"} == {
        k: v for k, v in second.items() if k != "id"
    }
