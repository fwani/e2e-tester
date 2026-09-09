"""재실행에서 **포인터가 클릭 위치에 남아 다음 대상을 가리는** 문제 (2026-09-09 사용자 보고).

보고 문장: 「step9번으로 클릭한 다음에 메뉴에 마우스가 그대로 있어서 확장된 형태라서 메뉴
뒤에 가려진 원천데이터를 클릭하지 못한다. 측정은 잘되었으나, 재실행시 클릭한 위치에 마우스가
가게되면서 발생한 문제로 보인다.」

## 진단

Playwright 의 ``click()`` 은 포인터를 요소 위로 옮기고 **그대로 둔다.** 녹화 때는 사람이 곧
마우스를 움직이므로 hover 로 열린 메뉴가 접히지만, 재생 때는 포인터가 머문다.

그리고 그것이 **교착이 된다**: Playwright 는 클릭 전에 히트 검사를 하고, 그 검사는 포인터를
옮기기 **전에** 한다. 「메뉴가 덮고 있다 → 검사 실패 → 재시도 → 포인터는 그대로 → 메뉴도
그대로」가 예산이 끝날 때까지 돈다.

## 왜 단위 검증만으로는 부족한가

`tests/unit/test_click_uncover_retry.py` 는 **호출 순서**를 잰다 — 가려졌으면 포인터를 비우고
누르는지. 그것으로는 「실제 브라우저에서 그 클릭이 통하는가」를 알 수 없다. 히트 검사도,
메뉴가 접히는 것도 브라우저가 하는 일이므로 여기서 한 번 실물로 확인한다.

정의를 **손으로 만든다.** 녹화를 지나면 「사람이 마우스를 움직였는가」가 섞여 들어가고,
재는 것은 재생이므로 그 변수를 없앤다.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import start_replay, stop_quietly, wait_for_run

MENU = "menu-trigger"
COVERED = "source-data"


def _definition(fixture_app: str) -> dict[str, Any]:
    """메뉴를 누른 뒤 그 메뉴에 가려지는 버튼을 누르는 정의.

    후보는 `test_id` 하나이고 `verified` 다 — 요소를 못 찾는 실패와 가려서 못 누르는 실패가
    섞이지 않게 한다. 재는 것은 후자다.
    """

    def click(step_id: str, label: str, test_id: str) -> dict[str, Any]:
        return {
            "type": "click",
            "id": step_id,
            "label": label,
            "author": "human",
            "tab": 0,
            # 예산을 짧게 둔다. **고쳐지지 않았으면 이 시간을 통째로 쓰고 실패한다** —
            # 그것이 사용자가 겪은 것이고, 검증이 오래 걸릴 이유는 없다.
            "timeout_ms": 4000,
            "frame_url": None,
            "target": {
                "test_id": {"value": test_id, "status": "verified"},
                "role": None,
                "role_status": "not_collected",
                "accessible_name": None,
                "label": None,
                "text": None,
                "css": None,
                "stable_attr": None,
                "tag": "button",
            },
        }

    return {
        "dsl_version": 1,
        "id": "TC-901",
        "name": "메뉴가 덮는 클릭",
        "authoring_mode": "record",
        "start_url": f"{fixture_app}/sticky-hover-menu.html",
        "browser": "chromium",
        "variables": [],
        "steps": [
            click("step-01", "메뉴 클릭", MENU),
            click("step-02", "원천데이터 클릭", COVERED),
        ],
    }


def _write(client: TestClient, fixture_app: str) -> str:
    """정의를 **저장소의 API 로** 쓴다.

    파일을 직접 쓰면 이름 규칙(`TC-nnn-<슬러그>.yaml`)을 검증이 사본으로 들게 되고, 규칙이
    바뀌는 날 이 검증만 조용히 못 찾는다. 모델로 만들어 넘기면 규칙은 한 곳에 남는다.
    """
    from itb.domain.test_case import Test

    repo = client.app.state.itb.repository
    test = Test.model_validate(_definition(fixture_app))
    repo.write_test(test)
    return str(test.id)


@pytest.mark.browser
def test_a_click_covered_by_a_hover_menu_still_lands(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**메뉴 뒤에 가려진 버튼을 누를 수 있다.**

    첫 Step 이 메뉴를 열고 포인터를 그 위에 남긴다. 둘째 Step 의 대상은 그 메뉴 뒤에 있다.
    고쳐지지 않았으면 둘째 Step 이 예산을 다 쓰고 `STEP_FAILED` 로 끝난다.
    """
    test_id = _write(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = wait_for_run(keyed_client, sid)
        outcomes = {s["step_id"]: s["outcome"] for s in view.get("step_results", [])}
        assert view["state"] == "completed", (
            f"가려진 클릭이 통하지 않았다: state={view['state']} outcomes={outcomes}"
        )
        assert outcomes.get("step-02") == "pass", outcomes
    finally:
        stop_quietly(keyed_client, sid)
