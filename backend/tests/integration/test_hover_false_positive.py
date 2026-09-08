"""hover 판정의 오탐 (FR-023c, TC-007 step-16 회귀).

**무엇이 잘못됐나.** hover Step 은 사람이 "이 hover 를 기록해" 라고 말해서 만들어지지
않는다. 주입 스크립트가 **화면이 바뀌었는가**로 추론한다. 추론이므로 다른 이유로 화면이
바뀌면 오탐이 난다.

실측(TC-007): 화면 이동 직후 이름 없는 로딩 덮개(`div.overlay`)가 포인터 밑에 있는 동안
로딩이 끝나 화면이 바뀌었다. 그 변화가 hover 의 효과로 판정돼 Step 이 만들어졌고,

- 표시는 "div 에 마우스 올리기" — 사람이 읽어도 무엇을 하려던 Step 인지 알 수 없다
- 후보는 위치 경로(`main#app-main > div > div:nth-of-type(1)`) **하나뿐**이었다
- 재실행에서 그 경로가 다시 덮개를 가리켰고, 덮개 위의 로딩 표시가 포인터를 가로막아
  **10초를 쓰고 실패**했다 (`STEP_FAILED`)

**정상 hover 를 함께 잃지 않는지도 같은 화면에서 본다.** 오탐을 막는다며 hover 기록 자체를
좁히면 FR-023c 가 무너진다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from tests.step_wait import wait_for_steps

OVERLAY_CSS = "#app-main > .shell > .overlay"
SETTLE_S = 1.2
"""덮개가 걷히는 시간(600ms)보다 넉넉히. 걷히는 변화가 hover 창 안에 들어와야 한다."""


def _record(client: TestClient, fixture_app: str) -> list[dict[str, Any]]:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/overlay.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            # 덮개 위에 포인터를 둔 채 덮개가 걷히기를 기다린다 — 오탐의 조건이다.
            await p.hover(OVERLAY_CSS, force=True)
            await asyncio.sleep(SETTLE_S)
            # 정상 hover: 메뉴를 여는 버튼.
            await p.hover("button.trigger")
            await asyncio.sleep(0.6)

        client.portal.call(act)  # type: ignore[attr-defined]
        return wait_for_steps(
            client, sid, lambda s: any(x["type"] == "hover" for x in s)
        )
    finally:
        stop_quietly(client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_nameless_overlay_does_not_become_a_hover_step(
    project_client: TestClient, fixture_app: str
) -> None:
    """이름 없는 덮개는 hover Step 이 되지 않는다.

    위치 경로 하나로만 지목되는 요소의 hover 는 의도를 표현할 수 없고, 재실행에서 그
    자리에 있는 다른 것을 잡는다.
    """
    steps = _record(project_client, fixture_app)
    hovers = [s for s in steps if s["type"] == "hover"]

    nameless = [
        s
        for s in hovers
        if not (s["target"].get("accessible_name") or s["target"].get("text"))
    ]
    assert not nameless, (
        "이름 없는 요소가 hover Step 이 됐다 — 재실행에서 반드시 실패한다: "
        f"{[(s['label'], (s['target'].get('css') or {}).get('value')) for s in nameless]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_a_real_hover_menu_is_still_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """정상 hover 메뉴는 그대로 기록된다 (FR-023c 가 무너지지 않는다)."""
    steps = _record(project_client, fixture_app)
    hovers = [s for s in steps if s["type"] == "hover"]
    assert any(s["target"].get("accessible_name") == "메뉴" for s in hovers), (
        f"메뉴를 여는 hover 가 사라졌다: {[s['label'] for s in hovers]}"
    )
