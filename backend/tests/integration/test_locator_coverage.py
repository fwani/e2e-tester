"""T073 — 요소 식별 후보 수집률 (SC-008).

픽스처 앱은 `data-testid` 가 있는 요소와 없는 요소를 의도적으로 섞어 두었다
(fixtures/sample-app/README.md). 그래서 이 측정이 자동으로 통과하지 않는다 — 실제 수집
품질을 본다.

**측정 대상은 `verified` 후보다.** 수집만 되고 검증되지 않은 후보는 실행 시 다른 요소를
잡을 수 있으므로 후보로 세지 않는다 (원칙 IV).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

MIN_VERIFIED_CANDIDATES = 2
COVERAGE_TARGET = 0.90
"""SC-008 — 후보 2개 이상인 Step 이 90% 이상."""


def _verified_count(step: dict[str, Any]) -> int:
    """이 Step 이 실행 시 쓸 수 있는 `verified` 후보 개수."""
    if step["type"] in ("navigate", "close_tab"):
        return MIN_VERIFIED_CANDIDATES  # 요소 탐색을 하지 않는 종류는 측정 대상이 아니다

    target = step.get("target") or (step.get("assertion") or {}).get("target")
    if target is None:
        return MIN_VERIFIED_CANDIDATES

    count = 0
    for key in ("test_id", "label", "text", "css"):
        candidate = target.get(key)
        if candidate and candidate.get("status") == "verified":
            count += 1
    if target.get("role") and target.get("accessible_name") and (
        target.get("role_status") == "verified"
    ):
        count += 1
    stable = target.get("stable_attr")
    if stable and stable.get("status") == "verified":
        count += 1
    return count


@pytest.mark.usefixtures("fixture_app")
def test_recorded_steps_have_at_least_two_verified_candidates(
    project_client: TestClient, fixture_app: str
) -> None:
    """SC-008 — 픽스처 앱 녹화 결과에서 후보 2개 이상 Step 비율 90% 이상."""
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        session = project_client.app.state.itb.sessions.require(sid)
        page = session.tabs[0].page

        async def act(p: Any = page) -> None:
            # testId 있는 요소와 없는 요소를 고루 지난다 (픽스처 README 의 표).
            await p.fill("#email", "tester@example.com")
            await asyncio.sleep(0.2)
            await p.fill("#password", "record-only-not-a-real-secret")
            await asyncio.sleep(0.2)
            await p.click("[data-testid=login-submit]")
            await p.wait_for_url("**/projects.html")
            await asyncio.sleep(0.4)
            await p.click("[data-testid=create-project]")
            await asyncio.sleep(0.3)
            await p.fill("#pname", "분석 프로젝트")  # testId 없음 — label 로 잡혀야 한다
            await asyncio.sleep(0.2)
            await p.select_option("#ptype", "pipeline")
            await asyncio.sleep(0.2)
            await p.click("[data-testid=save-project]")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = project_client.get(f"/api/sessions/{sid}").json()["steps"]
    finally:
        stop_quietly(project_client, sid)

    assert len(steps) >= 6, f"측정에 필요한 Step 이 부족하다: {len(steps)}개"

    counts = [_verified_count(s) for s in steps]
    covered = sum(1 for c in counts if c >= MIN_VERIFIED_CANDIDATES)
    ratio = covered / len(steps)

    weak = [
        (s["id"], s["label"], c)
        for s, c in zip(steps, counts, strict=True)
        if c < MIN_VERIFIED_CANDIDATES
    ]
    assert ratio >= COVERAGE_TARGET, (
        f"후보 2개 이상 Step 비율이 {ratio:.0%} 로 목표 {COVERAGE_TARGET:.0%} 에 못 미친다. "
        f"부족한 Step: {weak}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_element_without_test_id_still_gets_candidates(
    project_client: TestClient, fixture_app: str
) -> None:
    """testId 가 없는 요소(비밀번호 입력)도 label·css 후보를 확보한다."""
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.fill("#password", "record-only-not-a-real-secret")
            await asyncio.sleep(0.4)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = project_client.get(f"/api/sessions/{sid}").json()["steps"]
    finally:
        stop_quietly(project_client, sid)

    assert steps, "비밀번호 입력이 기록되지 않았다"
    target = steps[-1]["target"]
    assert target.get("test_id") is None or target["test_id"]["status"] != "verified", (
        "픽스처의 비밀번호 입력에는 data-testid 가 없어야 한다 — 측정 설계가 무너졌다"
    )
    assert _verified_count(steps[-1]) >= MIN_VERIFIED_CANDIDATES, (
        f"testId 없는 요소의 후보가 부족하다: {target}"
    )
