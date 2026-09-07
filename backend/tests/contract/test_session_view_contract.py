"""세션 뷰가 화면을 복원할 만큼 싣는다 (005 T010 · FR-171, contracts/rest-api.md §2).

WebSocket 계약은 이미 "끊기면 `GET /api/sessions/{sid}` 로 전체 상태를 다시 받는다" 였다.
문제는 **그 전체 상태에 Step 결과가 없었던 것**이다. 그래서 화면을 다시 그리면 그때까지의
성공·실패가 사라졌고(U-18), 실패 이벤트를 놓친 화면은 실패가 없었던 것처럼 보였다(U-05).

계약 테스트를 따로 두는 이유는 이 다섯 필드가 **화면 다섯 곳의 유일한 근거**이기 때문이다.
하나가 빠져도 서버는 정상으로 보이고 화면만 조용히 잃는다 — 통합 테스트가 잡기 어려운
형태의 회귀다.
"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from itb.api.routes.sessions import SessionView, StepProgress
from itb.domain.run_result import RunScope, StepOutcome

RESTORE_FIELDS = {
    "step_results": "Step별 결과 — 이벤트 없이 화면을 복원한다 (FR-171·U-18·U-05)",
    "pause_settled": "일시정지가 실제로 걸렸는가 — 전이 표시의 근거 (FR-142·U-04)",
    "run_scope": "이 실행이 전체인가 부분인가 (FR-152)",
    "run_start_index": "부분 실행이 어디서 시작했는가 (FR-149·FR-150)",
    "saved_at": "마지막 저장 시각 — 저장 성공을 화면이 스스로 안다 (FR-154·U-09)",
}


# ─── 모델 형태 ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("field", "why"), sorted(RESTORE_FIELDS.items()))
def test_session_view_declares_the_restore_field(field: str, why: str) -> None:
    assert field in SessionView.model_fields, f"{field} 가 세션 뷰에 없다 — {why}"


def test_step_progress_outcome_is_the_step_outcome_enum() -> None:
    """Step 결말은 **네 값 그대로**다 (FR-171, 헌법 원칙 I).

    005 가 넓힌 것은 실행 결말(`Outcome`)이고 Step 결말은 건드리지 않았다. 여기가
    문자열로 느슨해지면 화면이 `skipped` 와 `not_run` 을 구분할 근거를 잃는다 (U-21).
    """
    assert StepProgress.model_fields["outcome"].annotation is StepOutcome
    assert [o.value for o in StepOutcome] == ["pass", "fail", "skipped", "not_run"]


def test_step_progress_stays_minimal() -> None:
    """세션 뷰는 폴링 대상이다. 진단 정보는 결과 조회로 가져온다.

    로케이터 시도·오류 본문이 여기 들어오면 폴링마다 실행 전체를 실어 나른다.
    """
    assert set(StepProgress.model_fields) == {"step_id", "outcome", "duration_ms"}


def test_session_view_defaults_are_safe_before_any_run() -> None:
    """실행 전 기본값이 화면을 거짓말하게 하지 않는다.

    `pause_settled` 의 기본이 `False` 면 아무것도 하지 않은 세션이 "멈추는 중" 으로
    보인다. `run_scope` 의 기본이 `partial` 이면 전체 실행이 부분으로 표시된다.
    """
    fields = SessionView.model_fields
    assert fields["pause_settled"].default is True
    assert fields["run_scope"].default is RunScope.FULL
    assert fields["run_start_index"].default == 0
    assert fields["saved_at"].default is None
    assert fields["step_results"].default_factory is list  # type: ignore[comparison-overlap]


# ─── 실제 응답 ──────────────────────────────────────────────────────────────


def test_live_session_response_carries_every_restore_field(
    project_client: TestClient, fixture_app: str
) -> None:
    """진짜 응답이 다섯 필드를 싣는다.

    모델에만 있고 응답에서 빠지는 경우(직렬화 제외·별도 응답 모델)를 잡는다.
    """
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["session_id"]
    try:
        body = project_client.get(f"/api/sessions/{session_id}").json()
    finally:
        from us2_support import stop_quietly

        stop_quietly(project_client, session_id)

    missing = [f for f in RESTORE_FIELDS if f not in body]
    assert not missing, f"세션 응답에 없는 필드: {missing}"

    assert body["step_results"] == [], "실행 전인데 Step 결과가 있다"
    assert body["pause_settled"] is True
    assert body["run_scope"] == RunScope.FULL.value
    assert body["run_start_index"] == 0
    assert body["saved_at"] is None


def test_step_results_only_carry_steps_that_actually_ran() -> None:
    """아직 돌지 않은 Step 은 싣지 않는다.

    `not_run` 을 그대로 보내면 화면은 "결과가 있다" 와 "아직 없다" 를 구분하지 못하고,
    실행 전에도 모든 Step 이 결과를 가진 것처럼 보인다.
    """
    from itb.api.routes.sessions import _progress_of

    class _Result:
        def __init__(self, step_id: str, outcome: StepOutcome) -> None:
            self.step_id = step_id
            self.outcome = outcome
            self.duration_ms = 1

    class _Engine:
        results = [
            _Result("step-01", StepOutcome.PASS),
            _Result("step-02", StepOutcome.FAIL),
            _Result("step-03", StepOutcome.SKIPPED),
            _Result("step-04", StepOutcome.NOT_RUN),
        ]

    class _Work:
        engine = _Engine()

    progress = _progress_of(_Work())  # type: ignore[arg-type]

    assert [p.step_id for p in progress] == ["step-01", "step-02", "step-03"]
    assert StepOutcome.NOT_RUN not in [p.outcome for p in progress]


def test_saved_at_is_a_datetime_not_a_bool() -> None:
    """저장 **시각**이다. 불리언이면 "언제 저장했는가" 를 화면이 말할 수 없고,
    같은 세션에서 두 번째 저장을 첫 저장과 구분하지 못한다 (FR-154)."""
    annotation = SessionView.model_fields["saved_at"].annotation
    assert annotation == dt.datetime | None
