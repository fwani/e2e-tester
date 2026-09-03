"""T052 — US1 종단 테스트: 녹화 → 저장 → 목록 (헌법 품질 게이트 3).

quickstart §2 의 절차를 자동화한다. 실제 브라우저와 픽스처 앱을 쓴다.

**독립 검증 기준** (spec US1): 재실행 기능 없이도 이 스토리가 검증된다 — 녹화해서 Step
목록을 얻고 저장하는 것까지가 US1의 가치다.
"""

from __future__ import annotations

import asyncio
import pathlib
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient


@pytest.mark.usefixtures("fixture_app")
def test_record_save_and_appear_in_list(
    project_client: TestClient, fixture_app: str, tmp_path: pathlib.Path
) -> None:
    """quickstart §2 — 프로젝트 생성부터 목록 표시까지."""
    # 1. 프로젝트가 열려 있고 .gitignore 가 만들어졌다
    project = project_client.get("/api/project").json()
    assert project["gitignore_present"] is True
    gitignore = (tmp_path / "proj" / ".gitignore").read_text(encoding="utf-8")
    assert "secrets.local.yaml" in gitignore
    assert ".runs/" in gitignore

    # 2. 녹화 세션 시작 — 실제 브라우저가 시작 URL 로 열린다
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    assert created.json()["state"] == "recording"

    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        # 3. 사용자가 브라우저를 조작한다
        async def act() -> None:
            await page.fill("#email", "tester@example.com")
            await page.fill("#password", "pw-not-a-real-secret")
            await page.click("[data-testid=login-submit]")
            await page.wait_for_url("**/projects.html")
            await asyncio.sleep(0.5)
            await page.click("[data-testid=create-project]")
            await page.fill("#pname", "TEST")
            await page.select_option("[data-testid=project-type]", "pipeline")
            await asyncio.sleep(0.3)
            await page.click("[data-testid=save-project]")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        # 4. Step 목록이 조작을 반영한다
        steps: list[dict[str, Any]] = project_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert len(steps) >= 5, f"Step 이 너무 적다: {[s['label'] for s in steps]}"
        kinds = {s["type"] for s in steps}
        assert {"click", "fill", "select"} <= kinds, f"동작 종류가 부족하다: {kinds}"

        # 각 Step 에 사람이 읽을 수 있는 표시 이름과 탭 참조가 있다 (FR-012·FR-027)
        for step in steps:
            assert step["label"], f"표시 이름이 없다: {step}"
            assert step["tab"] == 0
            assert step["author"] == "human"

        # 5. 저장
        saved = project_client.post(f"/api/sessions/{sid}/save", json={"name": "프로젝트 생성"})
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
        assert test_id == "TC-001"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")

    # 6. 목록에 나타난다 (FR-002)
    listing = project_client.get("/api/tests").json()
    assert listing["counts"]["total"] == 1
    row = listing["tests"][0]
    assert row["id"] == "TC-001"
    assert row["name"] == "프로젝트 생성"
    assert row["authoring_mode"] == "record"
    assert row["step_count"] == len(steps)
    assert row["outcome"] is None  # 아직 실행하지 않았다

    # 7. 정의 파일이 사람이 읽을 수 있는 형태로 저장됐다 (FR-011·FR-088b)
    files = list((tmp_path / "proj" / "tests").glob("TC-001-*.yaml"))
    assert len(files) == 1, f"정의 파일이 하나여야 한다: {files}"
    raw = files[0].read_text(encoding="utf-8")
    assert "프로젝트 생성" in raw
    parsed = yaml.safe_load(raw)
    assert parsed["dsl_version"] == 1
    assert len(parsed["steps"]) == len(steps)

    # 8. 다시 열 수 있다 (FR-016)
    reopened = project_client.get("/api/tests/TC-001").json()
    assert reopened["name"] == "프로젝트 생성"
    assert len(reopened["steps"]) == len(steps)


@pytest.mark.usefixtures("fixture_app")
def test_second_test_gets_next_id(project_client: TestClient, fixture_app: str) -> None:
    """FR-002 — 테스트 ID 는 프로젝트 안에서 자동으로 부여된다."""
    ids: list[str] = []
    for name in ("첫 번째", "두 번째"):
        created = project_client.post(
            "/api/sessions",
            json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
        )
        sid = created.json()["session_id"]
        try:
            manager = project_client.app.state.itb.sessions
            page = manager.require(sid).tabs[0].page

            async def act(p: Any = page) -> None:
                await p.click("[data-testid=login-submit]")
                await asyncio.sleep(0.4)

            project_client.portal.call(act)  # type: ignore[attr-defined]
            saved = project_client.post(f"/api/sessions/{sid}/save", json={"name": name})
            assert saved.status_code == 200, saved.text
            ids.append(saved.json()["id"])
        finally:
            project_client.post(f"/api/sessions/{sid}/stop")

    assert ids == ["TC-001", "TC-002"]


@pytest.mark.usefixtures("fixture_app")
def test_multitab_flow_saves_tab_references(
    project_client: TestClient, fixture_app: str, tmp_path: pathlib.Path
) -> None:
    """quickstart §3 — 새 탭을 거치는 흐름이 탭 참조와 함께 저장된다 (FR-030)."""
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await page.fill("#email", "tester@example.com")
            await page.fill("#password", "pw-not-a-real-secret")
            await page.click("[data-testid=login-submit]")
            await page.wait_for_url("**/projects.html")
            await asyncio.sleep(0.5)
            await page.click("[data-testid=terms-link]")
            await asyncio.sleep(0.9)
            tab1 = session.tabs[1].page
            await tab1.wait_for_load_state()
            await tab1.click("[data-testid=close-terms]")
            await asyncio.sleep(0.6)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        saved = project_client.post(
            f"/api/sessions/{sid}/save", json={"name": "약관 새 창 확인"}
        )
        assert saved.status_code == 200, saved.text
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")

    files = list((tmp_path / "proj" / "tests").glob("*.yaml"))
    parsed = yaml.safe_load(files[0].read_text(encoding="utf-8"))
    tabs_used = {s["tab"] for s in parsed["steps"]}
    assert 0 in tabs_used
    assert 1 in tabs_used, f"새 탭 Step 이 저장되지 않았다: {parsed['steps']}"
