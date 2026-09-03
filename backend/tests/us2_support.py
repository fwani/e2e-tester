"""US2 (재실행) 테스트 공용 도구.

`tests/` 에는 `__init__.py` 가 없으므로 pytest 가 이 디렉터리를 sys.path 에 넣는다.
테스트 모듈에서 ``from us2_support import ...`` 로 쓴다.

여기 있는 함수들은 **정의를 손으로 쓰지 않고 실제 녹화 경로를 지나게** 하는 데 목적이 있다.
녹화가 만든 것과 실행이 읽는 것이 같은 표현임을 매 테스트가 다시 보증한다 (헌법 원칙 I).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

TERMINAL_STATES = frozenset({"completed", "failed", "stopped", "lost"})

DEFAULT_EMAIL = "tester@example.com"

HOVER_SETTLE_S = 0.3
"""클릭 전 마우스를 올려 두고 기다리는 시간.

리코더는 **포인터가 요소에 올라간 시점에** 후보를 수집·검증한다. 클릭 시점 수집은 앱의
클릭 핸들러가 유발하는 화면 이동과 경쟁해서 진다 — 문서가 교체되면 후보를 확인할 수 없다.
사람은 클릭 전에 수백 ms 마우스를 올려 두므로 실제 사용에서는 문제가 되지 않지만,
`page.click()` 은 마우스 이동과 클릭을 한 호출에 몰아넣어 그 간격을 없앤다.
그래서 테스트는 사람과 같은 순서(올려놓기 → 누르기)로 조작한다.
"""


async def click_like_a_person(page: Any, selector: str) -> None:
    """마우스를 올려 두고 잠깐 기다린 뒤 누른다. `HOVER_SETTLE_S` 의 설명을 참고한다."""
    await page.hover(selector)
    await asyncio.sleep(HOVER_SETTLE_S)
    await page.click(selector)


def record_login(
    client: TestClient,
    fixture_app: str,
    password: str = "record-only-not-a-real-secret",
    name: str = "로그인",
) -> str:
    """픽스처 앱 로그인 흐름을 녹화해 저장하고 테스트 ID 를 돌려준다."""
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
            await p.fill("#password", password)
            await asyncio.sleep(0.25)
            await click_like_a_person(p, "[data-testid=login-submit]")
            await p.wait_for_url("**/projects.html")
            await asyncio.sleep(0.5)

        client.portal.call(act)  # type: ignore[attr-defined]

        steps = client.get(f"/api/sessions/{sid}").json()["steps"]
        assert steps, "녹화된 Step 이 없다 — 이후 재실행 테스트가 성립하지 않는다"

        saved = client.post(f"/api/sessions/{sid}/save", json={"name": name})
        assert saved.status_code == 200, saved.text
        return str(saved.json()["id"])
    finally:
        stop_quietly(client, sid)


def record_new_tab_flow(client: TestClient, fixture_app: str) -> str:
    """로그인 후 새 탭(약관)을 여는 흐름을 녹화해 저장한다. 탭 참조가 있는 정의를 만든다."""
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
            await asyncio.sleep(0.2)
            await p.fill("#password", "record-only-not-a-real-secret")
            await asyncio.sleep(0.2)
            await click_like_a_person(p, "[data-testid=login-submit]")
            await p.wait_for_url("**/projects.html")
            await asyncio.sleep(0.4)
            await click_like_a_person(p, "[data-testid=terms-link]")
            await asyncio.sleep(0.9)
            tab1 = session.tabs[1].page
            await tab1.wait_for_load_state()
            await click_like_a_person(tab1, "[data-testid=close-terms]")
            await asyncio.sleep(0.6)

        client.portal.call(act)  # type: ignore[attr-defined]

        steps = client.get(f"/api/sessions/{sid}").json()["steps"]
        assert any(s["tab"] == 1 for s in steps), (
            f"새 탭 Step 이 녹화되지 않았다: {[(s['type'], s['tab']) for s in steps]}"
        )
        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "약관 확인"})
        assert saved.status_code == 200, saved.text
        return str(saved.json()["id"])
    finally:
        stop_quietly(client, sid)


def start_replay(client: TestClient, test_id: str) -> str:
    """재실행 세션을 시작하고 세션 ID 를 돌려준다."""
    created = client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])


def wait_for_run(client: TestClient, sid: str, timeout_s: float = 90.0) -> dict[str, Any]:
    """세션이 종료 상태에 도달할 때까지 기다리고 세션 뷰를 돌려준다."""
    deadline = time.monotonic() + timeout_s
    view: dict[str, Any] = {}
    while time.monotonic() < deadline:
        resp = client.get(f"/api/sessions/{sid}")
        if resp.status_code != 200:
            pytest.fail(f"세션 조회가 실패했다: {resp.status_code} {resp.text[:200]}")
        view = resp.json()
        if view["state"] in TERMINAL_STATES:
            return view
        time.sleep(0.05)
    pytest.fail(f"실행이 {timeout_s}초 안에 끝나지 않았다. 마지막 상태: {view.get('state')}")
    raise AssertionError  # pragma: no cover - pytest.fail 이 먼저 던진다


def replay(client: TestClient, test_id: str, timeout_s: float = 90.0) -> dict[str, Any]:
    """재실행을 끝까지 돌리고 세션 뷰를 돌려준다. 세션은 정리한다."""
    sid = start_replay(client, test_id)
    try:
        return wait_for_run(client, sid, timeout_s)
    finally:
        stop_quietly(client, sid)


def result_of(client: TestClient, test_id: str) -> dict[str, Any]:
    resp = client.get(f"/api/tests/{test_id}/result")
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def stop_quietly(client: TestClient, sid: str) -> None:
    """세션을 정리한다. 이미 끝난 세션이면 조용히 넘어간다.

    정리 실패가 본 검증의 실패 메시지를 가리면 안 된다.
    """
    try:
        client.post(f"/api/sessions/{sid}/stop")
    except Exception:  # noqa: BLE001, S110 - 사유를 남길 로거가 없고, 정리 실패는 무해하다
        pass


def break_first_click(client: TestClient, test_id: str) -> int:
    """저장된 정의의 첫 click Step 후보를 존재하지 않는 것으로 바꿔 실패를 유도한다.

    픽스처 앱은 정적 파일이라 "버튼 이름이 바뀐 상황"을 앱 쪽에서 만들 수 없다.
    정의 쪽 후보를 어긋나게 해서 같은 국면(요소를 못 찾음)을 만든다.

    실패시킨 Step 의 위치를 돌려준다.
    """
    import yaml

    repo = client.app.state.itb.repository
    path = repo.find_test_path(test_id)
    assert path is not None, f"정의 파일을 찾을 수 없다: {test_id}"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    for index, step in enumerate(raw["steps"]):
        if step["type"] != "click":
            continue
        target = step["target"]
        for key in ("test_id", "label", "text", "css"):
            if target.get(key):
                target[key]["value"] = "존재하지-않는-요소-9999"
        if target.get("role"):
            target["accessible_name"] = "존재하지 않는 버튼 9999"
        if target.get("stable_attr"):
            target["stable_attr"]["value"] = "존재하지-않는-값-9999"
        step["timeout_ms"] = 1500  # 테스트를 빠르게 끝낸다
        path.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        return index

    pytest.fail("click Step 이 없어 실패를 유도할 수 없다")
    raise AssertionError  # pragma: no cover
