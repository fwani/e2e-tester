"""껍데기 여백을 누른 클릭 (TC-013 회귀).

사람이 버튼을 누르려다 그 **밖의 여백**을 누르면 눌린 것은 껍데기다. 실측(TC-013)에서
그런 Step 이 셋 나왔고, 표시 이름은 자식 텍스트를 전부 이어붙인 형태였다 —
`앱 관리온톨로지 관리데이터 관리프로젝트 관리`. 재실행에서는 아무 일도 하지 않는다.

**버튼으로 바꿔 주지 않는다.** 여백은 어느 요소를 뜻하는지 알 수 없다. 추측해서 하나를
고르면 사용자가 누르지 않은 것을 누르는 정의가 된다. 그래서 기록하지 않는다.

버튼 자기 패딩은 다르다 — 그것은 버튼을 누른 것이며 이미 버튼으로 기록된다(실측 확인).
이 검증이 지키는 것은 **버튼 밖**이다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from tests.step_wait import wait_for_steps


def _click(
    client: TestClient, fixture_app: str, selector: str, position: dict[str, float] | None
) -> list[dict[str, Any]]:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/container-gap.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.click(selector, position=position)
            await asyncio.sleep(0.5)

        client.portal.call(act)  # type: ignore[attr-defined]
        # 아무 Step 도 만들어지지 않는 것이 기대값인 경우가 있으므로 조건 없이 기다린다.
        return wait_for_steps(client, sid, lambda s: True)
    finally:
        stop_quietly(client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_clicking_the_gap_around_buttons_is_not_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """버튼을 품은 껍데기의 여백을 누른 클릭은 Step 이 되지 않는다."""
    steps = _click(project_client, fixture_app, ".row", {"x": 6, "y": 6})
    clicks = [s for s in steps if s["type"] == "click"]
    assert not clicks, (
        "껍데기 여백 클릭이 Step 으로 남았다: "
        f"{[(s['label'], (s['target'].get('css') or {}).get('value')) for s in clicks]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_the_button_itself_is_still_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """버튼 안쪽(패딩 포함)을 누르면 그대로 버튼으로 기록된다."""
    steps = _click(project_client, fixture_app, "[data-testid=save]", {"x": 4, "y": 4})
    clicks = [s for s in steps if s["type"] == "click"]
    assert [s["target"].get("tag") for s in clicks] == ["button"], (
        f"버튼 클릭이 사라졌거나 다른 것이 기록됐다: {[(s['type'], s['label']) for s in steps]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_a_custom_div_button_is_still_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """`addEventListener` 로만 동작하는 커스텀 버튼은 걸러지지 않는다.

    `role`·`tabindex`·`onclick` 이 없어 제품 눈에는 조작 대상으로 보이지 않는다. 그것만으로
    버리면 이런 요소를 쓰는 앱의 녹화가 통째로 깨진다 — 그래서 **컨트롤을 품고 있는지**를
    함께 본다. 이 요소는 품고 있지 않으므로 남아야 한다.
    """
    steps = _click(project_client, fixture_app, "[data-testid=fake]", None)
    clicks = [s for s in steps if s["type"] == "click"]
    assert clicks, (
        f"커스텀 버튼 클릭이 버려졌다: {[(s['type'], s['label']) for s in steps]}"
    )
    assert clicks[-1]["target"].get("tag") == "div"
