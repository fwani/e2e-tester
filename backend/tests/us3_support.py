"""US3 (일시정지 → 편집 → 이어서 실행) 테스트 공용 도구.

**정의를 손으로 쓰지 않는다.** 실제 녹화 경로를 지나 만든 테스트로 검증해야, 녹화가
만드는 것과 편집이 고치는 것이 같은 표현임을 매 테스트가 다시 보증한다 (원칙 I).

일시정지 시점을 "몇 번째 Step 이 끝난 뒤" 로 정확히 잡는 것이 이 모듈의 요점이다.
`step_finished` 이벤트를 기다린 뒤 멈추므로, 실행 속도에 따라 시점이 흔들리지 않는다.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import DEFAULT_EMAIL, click_like_a_person, stop_quietly

PRECONDITION_STEPS = 5
"""SC-007 이 요구하는 "사전 Step 5개 이상" 시나리오의 최소 개수."""


def record_login_then_two_menus(
    client: TestClient, fixture_app: str, name: str = "메뉴 이동"
) -> str:
    """quickstart §5 1단계의 흐름을 녹화한다.

    로그인 → 프로젝트 메뉴 → (실수로) 데이터 메뉴. 사전 Step 이 5개 이상이라 SC-007 을
    측정할 수 있고, 마지막 Step 이 "지워야 할 실수" 라는 점도 그 절차와 같다.
    """
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        session = client.app.state.itb.sessions.require(sid)
        page = session.tabs[0].page

        async def act(p: Any = page) -> None:
            await p.fill("#email", DEFAULT_EMAIL)
            await asyncio.sleep(0.25)
            await p.fill("#password", "record-only-not-a-real-secret")
            await asyncio.sleep(0.25)
            await click_like_a_person(p, "[data-testid=login-submit]")
            await p.wait_for_url("**/projects.html")
            await asyncio.sleep(0.5)
            await click_like_a_person(p, "nav a[href='projects.html']")
            await asyncio.sleep(0.5)
            await click_like_a_person(p, "nav a[href='data.html']")
            await p.wait_for_url("**/data.html")
            await asyncio.sleep(0.5)

        client.portal.call(act)  # type: ignore[attr-defined]

        steps = client.get(f"/api/sessions/{sid}").json()["steps"]
        assert len(steps) >= PRECONDITION_STEPS, (
            f"사전 Step 이 {PRECONDITION_STEPS}개 미만이면 SC-007 을 측정할 수 없다: "
            f"{[(s['type'], s['label']) for s in steps]}"
        )
        saved = client.post(f"/api/sessions/{sid}/save", json={"name": name})
        assert saved.status_code == 200, saved.text
        return str(saved.json()["id"])
    finally:
        stop_quietly(client, sid)


def pause_after(
    client: TestClient,
    sid: str,
    finished_steps: int,
    events: list[tuple[str, dict]],
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    """`finished_steps` 개의 Step 이 끝난 직후 일시정지한다.

    **이벤트를 기준으로 기다린다.** 세션 뷰의 `current_step_index` 를 폴링하면 실행이
    빠른 환경에서 목표 지점을 지나쳐 버린다.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        done = sum(1 for kind, _ in events if kind == "step_finished")
        if done >= finished_steps:
            break
        if any(kind == "run_finished" for kind, _ in events):
            pytest.fail(
                f"{finished_steps}개가 끝나기 전에 실행이 종료됐다. "
                f"끝난 Step: {done}"
            )
        time.sleep(0.02)
    else:
        pytest.fail(f"{timeout_s}초 안에 {finished_steps}개 Step 이 끝나지 않았다.")

    resp = client.post(f"/api/sessions/{sid}/pause")
    assert resp.status_code == 200, resp.text
    view = resp.json()
    assert view["state"] == "paused", view
    return dict(view)


def started_ids(events: list[tuple[str, dict]]) -> list[str]:
    """실행이 시작된 Step id 를 순서대로. 재실행 여부 판정의 근거다 (SC-007)."""
    return [payload["step_id"] for kind, payload in events if kind == "step_started"]


def current_url(client: TestClient, sid: str) -> str:
    """브라우저가 지금 보고 있는 주소. 편집이 화면을 되돌리지 않았음을 확인한다 (FR-040a)."""
    session = client.app.state.itb.sessions.require(sid)
    return str(session.tabs[session.active_tab_index].page.url)


def wait_until_terminal(client: TestClient, sid: str, timeout_s: float = 90.0) -> dict[str, Any]:
    from us2_support import wait_for_run

    return wait_for_run(client, sid, timeout_s)
