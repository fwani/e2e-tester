"""T022 — 외부 경계(boundary) 면의 이상 조작 14건을 판정한다.

시나리오마다 검증 함수를 쓰지 않는다. 목록을 읽어 등록된 실행 수단으로 펼친다 (research R8).
시나리오가 늘어도 이 파일은 그대로다.

이 면은 실제 브라우저를 띄운다 — 대상 사이트가 이상하게 굴 때 제품이 어떻게 되는지는
브라우저 없이 잴 수 없다. 그래서 요청 경계 면보다 느리다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import tests.abnormal.drivers  # noqa: F401  (수단 등록 부작용)
from itb.domain.error import ErrorCode
from tests.abnormal.boundary_context import HANG_PATH, BoundaryContext
from tests.abnormal.catalogue import DRIVERS, Scenario, judge, scenarios

BOUNDARY_SCENARIOS = scenarios("boundary")


@pytest.fixture
def boundary_context(
    project_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> BoundaryContext:
    return BoundaryContext(client=project_client, fixture_app=fixture_app, monkeypatch=monkeypatch)


@pytest.mark.parametrize("scenario", BOUNDARY_SCENARIOS, ids=[s.id for s in BOUNDARY_SCENARIOS])
def test_abnormal_boundary_is_handled(
    scenario: Scenario, boundary_context: BoundaryContext
) -> None:
    """이상 조작 하나를 가하고 판정 3축을 모두 잰다.

    수단이 없으면 **건너뛰지 않고 실패한다** (RG-106). 조용한 건너뛰기는 "전건 통과"를
    거짓으로 만든다.
    """
    run = DRIVERS.get(scenario.id)
    assert run is not None, f"{scenario}\n  실행 수단이 등록되지 않았다 (RG-106)"

    judge(scenario, run(boundary_context))


def test_the_surface_has_scenarios() -> None:
    """목록을 못 읽은 채 통과하는 상태를 막는다."""
    assert len(BOUNDARY_SCENARIOS) >= 12, (
        f"boundary 면 시나리오를 {len(BOUNDARY_SCENARIOS)}건밖에 읽지 못했다"
    )


def test_step_failure_reaches_the_screen_classified(
    project_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """Step 실패가 **분류를 달고** 화면 쪽으로 나가는지 실제 실행으로 확인한다.

    위의 수단들은 실행기가 낸 분류를 러너와 같은 함수로 계약 형태 본문으로 옮긴다.
    러너가 정말 그렇게 내보내는지를 여기서 따로 보지 않으면, 그 변환은 자기 자신을 재는
    것이 되어 판정축 ①이 무의미해진다 (EC-008·AP-031·AP-033).

    대상 사이트가 응답을 끝내지 않는 실행을 골랐다 — 원인이 명백히 제품 밖에 있고,
    그래서 `blocked` 여야 한다는 판정이 분명하다.
    """
    import pathlib

    from us2_support import replay

    from itb.domain.test_case import Test
    from itb.storage.repository import ProjectRepository

    root = pathlib.Path(project_client.get("/api/project").json()["root"])
    ProjectRepository.open(root).write_test(
        Test(
            id="TC-001",
            name="응답을 끝내지 않는 대상",
            authoring_mode="record",
            start_url=f"{fixture_app}/login.html",
            steps=[
                {
                    "type": "navigate",
                    "id": "step-01",
                    "label": "무응답 주소로 이동",
                    "url": f"{fixture_app}{HANG_PATH}",
                    "timeout_ms": 3000,
                }
            ],
        )
    )
    event_log.clear()

    view = replay(project_client, "TC-001")
    assert view["state"] == "failed", f"무응답 대상인데 실행이 {view['state']} 로 끝났다"

    failures = [p for name, p in event_log if name == "step_failed"]
    assert failures, f"step_failed 가 나오지 않았다. 관측: {sorted({n for n, _ in event_log})}"

    body = failures[0].get("error")
    assert body is not None, "step_failed 에 계약 형태 오류 본문이 없다 (EC-008)"
    assert body["code"] == ErrorCode.TARGET_UNREACHABLE.value, (
        f"대상 쪽 사정인데 {body['code']} 로 나갔다 (AP-031)"
    )
    assert body["category"] == "blocked", (
        "대상 사이트가 응답하지 않은 것을 제품이 깨진 것으로 보이게 했다 (AP-031)"
    )
    assert body["next_action"].strip(), "다음 행동이 비어 있다 (EC-004)"
