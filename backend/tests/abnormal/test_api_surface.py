"""T021 — 요청 경계(api) 면의 이상 조작 19건을 판정한다.

시나리오마다 검증 함수를 쓰지 않는다. 목록을 읽어 등록된 실행 수단으로 펼친다 (research R8).
시나리오가 늘어도 이 파일은 그대로다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import tests.abnormal.drivers  # noqa: F401  (수단 등록 부작용)
from tests.abnormal.catalogue import DRIVERS, Scenario, judge, scenarios
from tests.abnormal.context import ApiContext

API_SCENARIOS = scenarios("api")


@pytest.fixture
def api_context(
    project_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> ApiContext:
    return ApiContext(client=project_client, fixture_app=fixture_app, monkeypatch=monkeypatch)


@pytest.mark.parametrize("scenario", API_SCENARIOS, ids=[s.id for s in API_SCENARIOS])
def test_abnormal_operation_is_handled(scenario: Scenario, api_context: ApiContext) -> None:
    """이상 조작 하나를 가하고 판정 3축을 모두 잰다.

    수단이 없으면 **건너뛰지 않고 실패한다** (RG-106). 조용한 건너뛰기는 "전건 통과"를
    거짓으로 만든다.
    """
    run = DRIVERS.get(scenario.id)
    assert run is not None, f"{scenario}\n  실행 수단이 등록되지 않았다 (RG-106)"

    judge(scenario, run(api_context))


def test_the_surface_has_scenarios() -> None:
    """목록을 못 읽은 채 통과하는 상태를 막는다."""
    assert len(API_SCENARIOS) >= 15, f"api 면 시나리오를 {len(API_SCENARIOS)}건밖에 읽지 못했다"
