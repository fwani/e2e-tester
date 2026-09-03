"""T070 — 성능 목표 계측 (research R8).

목표를 테스트로 고정한다. 회귀가 생기면 실패한다.

| 항목 | 목표 | 이 파일에서 |
|------|------|-------------|
| 녹화 이벤트 → Step 목록 반영 | p95 < 200 ms | 측정 |
| 세션 시작 준비 시간 | < 2 s (브라우저 실행·첫 화면 로드 제외) | 측정 |
| Step 실행 제품 오버헤드 | p95 < 50 ms | 측정 (T091) |
| 미러 프레임률·지연 | 5~10 fps / p95 < 300 ms | **수동 실측** (T006 에서 확인) |

"""

from __future__ import annotations

import asyncio
import statistics
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

RECORD_LATENCY_P95_MS = 200.0
"""사람이 즉시성으로 느끼는 임계. 이보다 느리면 녹화 중 무엇이 잡혔는지 확신할 수 없다."""

SESSION_READY_MS = 2000.0
STEP_OVERHEAD_P95_MS = 50.0
"""Step 하나를 실행할 때 **제품이 추가하는** 시간의 상한 (research R8).

대상 앱의 응답 시간은 제품이 줄일 수 없다. 그래서 "Step 소요 시간"이 아니라
**Step 소요 시간의 합과 실행 전체 시간의 차이**를 본다 — 그 차이가 제품 몫이다.
"""
STEP_LIST_SIZE = 200
"""spec Assumptions 의 "수십 개 규모" 에 여유를 둔 값."""


def _p95(samples: list[float]) -> float:
    if len(samples) < 2:
        return samples[0] if samples else 0.0
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return ordered[index]


@pytest.mark.usefixtures("fixture_app")
def test_recording_event_to_step_latency(
    project_client: TestClient, fixture_app: str
) -> None:
    """녹화 이벤트가 Step 목록에 반영되기까지의 지연 (research R8).

    후보 수집 + 기록 시점 검증이 이 경로에 들어 있으므로, 검증 비용이 사용자 체감에
    영향을 주는지 여기서 드러난다.
    """
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    samples: list[float] = []
    try:
        manager = project_client.app.state.itb.sessions
        page = manager.require(sid).tabs[0].page

        def step_count() -> int:
            return len(project_client.get(f"/api/sessions/{sid}").json()["steps"])

        for _ in range(12):
            before = step_count()

            async def one_click(p: Any = page) -> None:
                await p.click("[data-testid=login-email]")

            started = time.perf_counter()
            project_client.portal.call(one_click)  # type: ignore[attr-defined]

            # Step 이 반영될 때까지 짧게 폴링한다
            deadline = started + 3.0
            while time.perf_counter() < deadline:
                if step_count() > before:
                    samples.append((time.perf_counter() - started) * 1000)
                    break
                time.sleep(0.01)

        assert samples, "녹화 이벤트가 Step 으로 반영되지 않았다"
        p95 = _p95(samples)
        median = statistics.median(samples)
        assert p95 < RECORD_LATENCY_P95_MS, (
            f"녹화 반영 지연 p95={p95:.0f}ms 가 목표 {RECORD_LATENCY_P95_MS:.0f}ms 를 넘었다 "
            f"(중앙값 {median:.0f}ms, 표본 {len(samples)}건)"
        )
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_session_creation_is_responsive(
    project_client: TestClient, fixture_app: str
) -> None:
    """세션 시작 준비 시간 (research R8).

    브라우저 실행과 첫 화면 로드가 포함된 값이므로 목표보다 넉넉하게 본다 — 제품이
    추가하는 준비 비용이 지배적이 되면 이 테스트가 먼저 실패한다.
    """
    started = time.perf_counter()
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    sid = created.json()["session_id"]
    try:
        assert created.status_code == 201
        # 브라우저 실행(수백 ms)이 포함되므로 목표의 5배를 상한으로 둔다.
        assert elapsed_ms < SESSION_READY_MS * 5, (
            f"세션 시작이 {elapsed_ms:.0f}ms 걸렸다"
        )
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


def test_step_list_handles_large_test(tmp_path: Any) -> None:
    """Step 200개 규모의 정의를 적재·직렬화할 수 있다 (research R8).

    브라우저를 쓰지 않는다 — 도메인·저장 계층의 규모 처리만 본다.
    """
    from itb.domain.test_case import Test
    from itb.storage.yaml_io import dump_model, load_model

    steps = [
        {
            "id": f"step-{i + 1:03d}",
            "type": "click",
            "label": f"동작 {i + 1}",
            "tab": 0,
            "target": {"css": {"value": f"#el{i}", "status": "verified"}},
        }
        for i in range(STEP_LIST_SIZE)
    ]
    test = Test(
        id="TC-001",
        name="대규모 테스트",
        authoring_mode="record",
        start_url="http://127.0.0.1:4300/login.html",
        steps=steps,  # type: ignore[arg-type]
    )
    assert len(test.steps) == STEP_LIST_SIZE

    out = tmp_path / "big.yaml"
    started = time.perf_counter()
    dump_model(out, test)
    reloaded = load_model(out, Test)
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert len(reloaded.steps) == STEP_LIST_SIZE
    assert elapsed_ms < 2000, f"Step {STEP_LIST_SIZE}개 왕복이 {elapsed_ms:.0f}ms 걸렸다"


def test_locator_resolution_candidate_probe_is_cheap() -> None:
    """후보 전략 생성이 저렴해야 한다 (research R4 실측 5.1ms 의 순수 계산 부분).

    실제 `count()` 왕복은 브라우저가 필요하므로 여기서는 전략 계산만 본다.
    """
    from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
    from itb.locator.strategy import ordered_strategies

    target = TargetLocator(
        tag="button",
        test_id=Candidate(value="create-project", status=CandidateStatus.VERIFIED),
        role="button",
        accessible_name="프로젝트 생성",
        role_status=CandidateStatus.VERIFIED,
        label=Candidate(value="프로젝트명", status=CandidateStatus.VERIFIED),
        text=Candidate(value="프로젝트 생성", status=CandidateStatus.VERIFIED),
        stable_attr=StableAttr(
            name="data-role", value="create", status=CandidateStatus.VERIFIED
        ),
        css=Candidate(value=".card button", status=CandidateStatus.VERIFIED),
    )

    started = time.perf_counter()
    for _ in range(10_000):
        ordered_strategies(target)
    per_call_us = (time.perf_counter() - started) / 10_000 * 1_000_000
    assert per_call_us < 200, f"전략 계산이 호출당 {per_call_us:.0f}µs 걸렸다"


@pytest.mark.usefixtures("fixture_app")
def test_mirror_disconnect_does_not_affect_recording(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-047b — 이벤트 통로가 끊겨도 녹화가 계속된다.

    성능 목표가 아니라 요구사항이다. 통로를 제거해도 Step 이 계속 쌓이는지 본다.
    """
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        # 이벤트 통로를 끊는다 (WebSocket 연결 상실을 모사)
        session.attach_sink(None)

        async def act() -> None:
            await page.click("[data-testid=login-email]")
            await asyncio.sleep(0.3)
            await page.click("[data-testid=login-submit]")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = project_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert steps, "이벤트 통로가 끊기자 녹화가 멈췄다 — FR-047b 위반"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_step_execution_overhead(keyed_client: TestClient, fixture_app: str) -> None:
    """T091 — Step 실행에서 제품이 추가하는 오버헤드 (research R8, p95 < 50ms).

    측정 방법: 실행 전체 시간에서 Step 별 소요 시간 합을 뺀다. 남는 것이 후보 해석·탭 해석·
    결과 집계·이벤트 발행 등 **제품이 넣은 비용**이다. Step 소요 시간 자체를 재면 대상 앱의
    응답 시간이 섞여 목표를 판정할 수 없다.
    """
    from us2_support import record_login, replay, result_of

    test_id = record_login(keyed_client, fixture_app)

    overheads: list[float] = []
    for _ in range(5):
        view = replay(keyed_client, test_id)
        assert view["state"] == "completed", f"측정용 실행이 실패했다: {view['state']}"
        result = result_of(keyed_client, test_id)
        step_ms = sum(s["duration_ms"] for s in result["steps"])
        step_count = max(len(result["steps"]), 1)
        overheads.append(max(result["total_ms"] - step_ms, 0) / step_count)

    p95 = _p95(overheads)
    assert p95 < STEP_OVERHEAD_P95_MS, (
        f"Step 실행 오버헤드 p95={p95:.1f}ms 가 목표 "
        f"{STEP_OVERHEAD_P95_MS:.0f}ms 를 넘었다 (표본 {[round(o, 1) for o in overheads]})"
    )
