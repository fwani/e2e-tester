"""T050 — 녹화 통합 테스트 (US1). 실제 브라우저와 픽스처 앱을 쓴다.

확인 항목:
- 4종 동작 기록 (클릭·입력·선택·화면 이동) — FR-024
- 같은 요소 연속 입력이 최종 값 하나로 병합 — FR-025
- 한글 입력이 조합 완료 값으로 기록 — research R2
- 후보 수집과 기록 시점 검증 — FR-017·FR-019b
- Step 0개 저장 거절 — FR-029
- 민감 값이 변수 참조로만 저장 — FR-082·FR-083
"""

from __future__ import annotations

import asyncio
import pathlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from itb.domain.locator import CandidateStatus
from tests.step_wait import has_any, has_kinds, wait_for_steps


def _session(client: TestClient, fixture_app: str, page: str = "login.html") -> dict[str, Any]:
    resp = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/{page}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _steps(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["steps"]


def _stop(client: TestClient, session_id: str) -> None:
    client.post(f"/api/sessions/{session_id}/stop")


async def _drive(client: TestClient, session_id: str, script: str) -> None:
    """세션의 브라우저에서 스크립트를 수행한다.

    TestClient 는 앱과 같은 프로세스에서 돌므로 SessionManager 의 실제 Page 에 접근할 수 있다.
    """
    manager = client.app.state.itb.sessions
    session = manager.require(session_id)
    page = session.tabs[0].page
    await page.evaluate(script)
    await asyncio.sleep(0.4)


@pytest.mark.usefixtures("fixture_app")
def test_records_click_fill_select_and_navigation(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-024 — 4종 동작이 각각 Step 으로 기록된다.

    **화면 이동은 뒤로 가기로 유발한다.** 클릭이 유발한 이동은 의도적으로 억제된다 —
    클릭 Step 이 재실행 시 같은 이동을 만들므로 별도 Step 으로 두면 중복이다 (FR-030b).
    뒤로 가기는 클릭에서 나오지 않으므로 Step 으로 기록되어야 한다 (spec 엣지 케이스).
    """
    view = _session(project_client, fixture_app)
    sid = view["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await page.fill("#email", "tester@example.com")
            await page.click("#password")  # blur 로 email 확정
            await page.fill("#password", "pw-not-a-real-secret")
            await page.click("[data-testid=login-submit]")
            await page.wait_for_url("**/projects.html")
            await asyncio.sleep(0.5)
            await page.click("[data-testid=create-project]")
            await page.select_option("[data-testid=project-type]", "pipeline")
            await asyncio.sleep(0.4)
            # 클릭에서 나오지 않은 이동 — 화면 이동 Step 으로 기록되어야 한다
            await page.go_back()
            await asyncio.sleep(0.8)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        # 읽기를 고정 시간 뒤로 미루지 않는다 — 4종이 다 도달하면 즉시, 아니면 마감까지
        # 기다린 뒤 마지막으로 읽은 것으로 아래 단언이 사유를 낸다 (`tests/step_wait.py`).
        steps = wait_for_steps(
            project_client, sid, has_kinds("fill", "click", "select", "navigate")
        )
        kinds = [s["type"] for s in steps]
        assert "fill" in kinds, f"입력 Step 이 없다: {kinds}"
        assert "click" in kinds, f"클릭 Step 이 없다: {kinds}"
        assert "select" in kinds, f"선택 Step 이 없다: {kinds}"
        assert "navigate" in kinds, f"화면 이동 Step 이 없다: {kinds}"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_repeated_input_merges_into_final_value(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-025 — change 와 blur 가 모두 발생하므로 중복 제거가 필요하다 (research R2)."""
    view = _session(project_client, fixture_app)
    sid = view["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        page = manager.require(sid).tabs[0].page

        async def act() -> None:
            for value in ("first@example.com", "second@example.com", "final@example.com"):
                await page.fill("#email", value)
                await page.dispatch_event("#email", "change")
                await asyncio.sleep(0.15)
            await page.click("#password")
            await asyncio.sleep(0.4)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        # 병합 결과를 세려면 먼저 도달해야 한다. **개수를 조건으로 걸지 않는다** —
        # 그러면 "1개가 될 때까지" 기다리다 병합 실패를 마감으로 덮는다. 도달 여부만
        # 기다리고 개수는 아래 단언이 판정한다.
        steps = wait_for_steps(project_client, sid, has_kinds("fill"))
        fills = [s for s in steps if s["type"] == "fill"]
        assert len(fills) == 1, f"입력 Step 이 {len(fills)}개다. 병합되지 않았다: {fills}"
        assert fills[0]["value"] == "final@example.com"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_korean_input_records_composed_value(
    project_client: TestClient, fixture_app: str
) -> None:
    """research R2 — 조합 중인 자모가 아니라 완성된 문자열이 기록된다."""
    view = _session(project_client, fixture_app)
    sid = view["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        page = manager.require(sid).tabs[0].page

        async def act() -> None:
            # 픽스처 앱은 로그인 없이 projects.html 에 들어가면 login.html 로 되돌린다.
            # 정상 로그인 경로를 거쳐야 프로젝트 화면에 머문다.
            await page.fill("#email", "tester@example.com")
            await page.fill("#password", "pw-not-a-real-secret")
            await page.click("[data-testid=login-submit]")
            await page.wait_for_url("**/projects.html")
            await asyncio.sleep(0.4)
            await page.click("#open-create")
            await page.fill("#pname", "한글프로젝트")
            await page.dispatch_event("#pname", "change")
            await asyncio.sleep(0.4)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        # 대상 요소를 특정한다 — 마지막 fill 은 다른 필드일 수 있다.
        def is_pname(step: dict[str, Any]) -> bool:
            # navigate·close_tab Step 에는 target 이 없다 (판별 유니온).
            target = step.get("target") or {}
            css = (target.get("css") or {}).get("value", "")
            return step["type"] == "fill" and css.endswith("#pname")

        steps = wait_for_steps(project_client, sid, has_any(is_pname))
        pname_fills = [s for s in steps if is_pname(s)]
        assert pname_fills, "프로젝트명 입력 Step 이 없다"
        assert pname_fills[-1]["value"] == "한글프로젝트"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_candidates_are_collected_and_verified(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-017·FR-019b — 후보를 여러 개 수집하고 기록 시점에 검증한다."""
    view = _session(project_client, fixture_app)
    sid = view["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        page = manager.require(sid).tabs[0].page

        async def act() -> None:
            await page.click("[data-testid=login-submit]")
            await asyncio.sleep(0.4)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(project_client, sid, has_kinds("click"))
        clicks = [s for s in steps if s["type"] == "click"]
        assert clicks, "클릭 Step 이 없다"
        target = clicks[0]["target"]  # click Step 은 target 을 항상 갖는다

        # testId 가 있는 버튼이므로 test_id 후보가 검증을 통과해야 한다
        assert target["test_id"] is not None
        assert target["test_id"]["status"] == CandidateStatus.VERIFIED.value
        # 상태가 4종 중 하나로 채워져 있어야 한다 — 미검증 그대로 남아 있으면 안 된다
        collected = [
            target[key]["status"]
            for key in ("test_id", "label", "text", "css")
            if target.get(key) is not None
        ]
        assert collected
        assert all(s in {c.value for c in CandidateStatus} for s in collected)
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_saving_with_no_steps_is_rejected(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-029 — Step 이 없는 테스트는 저장할 수 없다."""
    view = _session(project_client, fixture_app)
    sid = view["session_id"]
    try:
        resp = project_client.post(f"/api/sessions/{sid}/save", json={"name": "빈 테스트"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "STEP_LIST_EMPTY"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_password_is_stored_as_variable_reference_not_plaintext(
    project_client: TestClient, fixture_app: str, tmp_path: pathlib.Path
) -> None:
    """FR-082·FR-083·T157 — 평문이 Step·이벤트·정의 파일 어디에도 남지 않는다."""
    secret = "not-a-real-password-1234"
    project_client.post("/api/keys/generate", json={})
    view = _session(project_client, fixture_app)
    sid = view["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        page = manager.require(sid).tabs[0].page

        async def act() -> None:
            await page.fill("#email", "tester@example.com")
            await page.fill("#password", secret)
            await page.click("[data-testid=login-submit]")
            await asyncio.sleep(0.6)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(project_client, sid, has_kinds("fill", "click"))
        blob = str(steps)
        assert secret not in blob, "평문 비밀번호가 Step 에 남았다"

        password_fills = [
            s for s in steps if s["type"] == "fill" and "민감" in s["label"]
        ]
        assert password_fills, f"민감 입력 Step 이 없다: {[s['label'] for s in steps]}"
        assert password_fills[0]["value"].startswith("{{")

        saved = project_client.post(f"/api/sessions/{sid}/save", json={"name": "로그인"})
        assert saved.status_code == 200, saved.text
        assert secret not in saved.text, "평문이 저장 응답에 남았다"

        # 디스크의 정의 파일에도 평문이 없어야 한다
        for path in (tmp_path / "proj" / "tests").glob("*.yaml"):
            assert secret not in path.read_text(encoding="utf-8")
    finally:
        _stop(project_client, sid)
