"""T023 — 화면(ui) 면의 이상 조작 18건을 판정한다. **실브라우저로 제품 화면을 연다** (RG-105).

시나리오마다 검증 함수를 쓰지 않는다. 목록을 읽어 등록된 실행 수단으로 펼친다 (research R8).

이 면은 제품 서버와 제품 화면을 **둘 다** 띄운다. 그래서 느리다 — 세션 동안 한 번만 띄우고
18건이 나눠 쓴다. 도구·포트가 없으면 건너뛰지 않고 실패한다 (RG-106).

**시나리오는 목록 순서대로 돈다.** 프로젝트 선택 화면(AS-007)은 프로젝트가 열리기 전에만
닿을 수 있고, 제품에 프로젝트를 닫는 경로가 없기 때문이다. 순서가 어긋나면 그 수단이
사유와 함께 실패한다 — 조용히 지나가지 않는다.

**그 제약은 이 파일 안의 순서만이 아니다** (005 T126). `product_ui` 는 세션 범위이므로
**같은 패키지의 다른 파일**이 먼저 돌아 프로젝트를 열면 AS-007 은 그대로 실패한다.
그래서 하니스를 쓰는 파일은 이름이 `test_ui_surface` 뒤에 와야 한다 —
`test_ui_surface_restore.py` 가 그 이유로 그 이름을 갖는다.
"""

from __future__ import annotations

import pytest

import tests.abnormal.drivers  # noqa: F401  (수단 등록 부작용)
from tests.abnormal.catalogue import DRIVERS, Scenario, judge, scenarios
from tests.abnormal.ui_context import UiContext

UI_SCENARIOS = scenarios("ui")


@pytest.mark.parametrize("scenario", UI_SCENARIOS, ids=[s.id for s in UI_SCENARIOS])
async def test_abnormal_screen_operation_is_handled(
    scenario: Scenario, ui_context: UiContext
) -> None:
    """이상 조작 하나를 화면에 가하고 판정 3축을 모두 잰다.

    수단이 없으면 **건너뛰지 않고 실패한다** (RG-106).
    """
    run = DRIVERS.get(scenario.id)
    assert run is not None, f"{scenario}\n  실행 수단이 등록되지 않았다 (RG-106)"

    judge(scenario, await run(ui_context))


def test_the_surface_has_scenarios() -> None:
    """목록을 못 읽은 채 통과하는 상태를 막는다."""
    assert len(UI_SCENARIOS) >= 15, f"ui 면 시나리오를 {len(UI_SCENARIOS)}건밖에 읽지 못했다"


def test_the_project_setup_scenario_runs_first() -> None:
    """프로젝트 선택 화면 시나리오가 화면 면의 **첫 번째**여야 한다.

    그 화면은 프로젝트가 열리기 전에만 닿을 수 있고, 제품에 프로젝트를 닫는 경로가
    없다. 목록 순서가 바뀌면 그 시나리오는 닿을 수 없는 화면을 기다리다 실패한다 —
    실패 사유가 "순서" 라는 것을 아는 데 시간이 걸리므로, 순서 자체를 여기서 못 박는다.
    """
    setup = [s for s in UI_SCENARIOS if s.target == "ProjectSetup"]
    assert setup, "ProjectSetup 시나리오가 목록에 없다"
    assert UI_SCENARIOS[0].target == "ProjectSetup", (
        f"화면 면의 첫 시나리오가 {UI_SCENARIOS[0].id}({UI_SCENARIOS[0].target}) 다. "
        "ProjectSetup 시나리오를 목록에서 화면 면 맨 앞으로 옮기세요 — 그 화면은 "
        "프로젝트가 열리기 전에만 닿을 수 있습니다."
    )
