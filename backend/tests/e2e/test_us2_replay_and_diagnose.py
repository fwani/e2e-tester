"""T077 — US2 종단 테스트: 실행 → 실패 → 진단 → 실패 Step부터 재실행.

US2 의 Independent Test 를 그대로 따라간다. 각 단계가 개별 테스트로 나뉘어 있으면
"각각은 되는데 이어 붙이면 안 되는" 상태를 못 잡는다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import (
    break_first_click,
    record_login,
    replay,
    result_of,
    start_replay,
    stop_quietly,
    wait_for_run,
)


@pytest.mark.usefixtures("fixture_app")
def test_replay_then_diagnose_then_rerun_from_failed_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """녹화한 테스트가 통과하고, 대상이 어긋나면 진단 정보와 함께 실패하며,
    고친 뒤 실패한 Step부터 다시 실행할 수 있다."""
    client = keyed_client

    # ── 1. 저장한 테스트를 실행하면 통과한다 ──────────────────────────────
    test_id = record_login(client, fixture_app)
    assert replay(client, test_id)["state"] == "completed"

    baseline = result_of(client, test_id)
    assert baseline["outcome"] == "pass"
    original_steps = client.get(f"/api/tests/{test_id}").json()["steps"]

    # ── 2. 대상이 어긋나면 그 Step 에서 멈춘다 ────────────────────────────
    broken_index = break_first_click(client, test_id)
    view = replay(client, test_id)
    assert view["state"] == "failed", f"어긋난 정의인데 통과했다: {view['state']}"

    failed = result_of(client, test_id)
    assert failed["outcome"] == "fail"
    assert failed["failed_step_index"] == broken_index

    # ── 3. 진단 정보 (FR-050·FR-051·FR-054·FR-021·FR-052·FR-053) ──────────
    assert failed["total_ms"] > 0
    assert failed["total_count"] == len(original_steps)
    assert failed["passed_count"] == broken_index, (
        f"실패 이전 Step 수와 통과 수가 다르다: {failed['passed_count']} vs {broken_index}"
    )

    detail = failed["steps"][broken_index]
    assert detail["outcome"] == "fail"
    assert detail["error_message"], "FR-054 — 사람이 읽을 수 있는 실패 이유가 없다"
    attempts = detail["locator_attempts"]
    assert attempts, "FR-021 — 시도한 후보 목록이 비어 있다"
    assert all(not a["matched"] for a in attempts), (
        f"매칭된 후보가 있는데 실패했다: {attempts}"
    )
    assert any(a["waited_ms"] > 0 for a in attempts), (
        f"어느 후보에도 대기 예산을 쓰지 않았다: {attempts}"
    )

    artifacts = failed["artifacts"]
    assert artifacts["failure_screenshot"], "FR-052 — 실패 시점 스크린샷이 없다"
    assert artifacts["console_log"], "FR-053 — 콘솔 기록이 없다"
    assert artifacts["network_log"], "FR-053 — 네트워크 기록이 없다"
    assert artifacts["trace"] is None, "MVP 는 실행 추적을 지원하지 않는다"

    for kind in ("screenshot", "console", "network"):
        resp = client.get(f"/api/tests/{test_id}/result/artifacts/{kind}")
        assert resp.status_code == 200, f"{kind} 산출물을 받을 수 없다: {resp.text}"
    trace = client.get(f"/api/tests/{test_id}/result/artifacts/trace")
    assert trace.status_code == 501, "TRACE 는 501 이어야 한다 (spec 디자인 차이 1)"

    # 목록 화면에도 실패 요약이 노출된다 (FR-005)
    row = next(
        r for r in client.get("/api/tests").json()["tests"] if r["id"] == test_id
    )
    assert row["outcome"] == "fail"
    assert row["failure_summary"]["step_index"] == broken_index

    # ── 4. 정의를 되돌리고 실패한 Step 부터 다시 실행한다 (FR-055) ────────
    repaired = client.get(f"/api/tests/{test_id}").json()
    repaired["steps"] = original_steps
    _write_definition(client, test_id, repaired)

    sid = start_replay(client, test_id)
    try:
        resumed = client.post(
            f"/api/sessions/{sid}/run-from", json={"step_index": broken_index}
        )
        assert resumed.status_code == 200, resumed.text
        final = wait_for_run(client, sid)
    finally:
        stop_quietly(client, sid)

    assert final["state"] == "completed", (
        f"실패한 Step 부터 재실행이 통과하지 않았다: {final['state']}"
    )
    rerun = result_of(client, test_id)
    assert rerun["outcome"] == "pass"
    assert rerun["failed_step_index"] is None


@pytest.mark.usefixtures("fixture_app")
def test_run_from_rejects_out_of_range_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-039 — 없는 Step 번호로는 이어서 실행할 수 없다."""
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/run-from", json={"step_index": 999}
        )
        assert resp.status_code == 400, resp.text
        assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_only_one_replay_session_per_test(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-043 — 한 테스트에 동시 실행 세션은 하나뿐이다."""
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        second = keyed_client.post(
            "/api/sessions", json={"mode": "replay", "test_id": test_id}
        )
        assert second.status_code == 409, second.text
        assert second.json()["error"]["code"] == "SESSION_ALREADY_ACTIVE"
    finally:
        stop_quietly(keyed_client, sid)


def _write_definition(client: TestClient, test_id: str, definition: dict) -> None:
    """정의를 파일에 그대로 다시 쓴다. 화면의 "Step 고치기" 를 대신한다."""
    import yaml

    repo = client.app.state.itb.repository
    path = repo.find_test_path(test_id)
    assert path is not None
    path.write_text(
        yaml.safe_dump(definition, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


# ─── 004 US1: 속도가 판정을 바꾸지 않는다 (SC-005·FR-104) ───────────────────


@pytest.mark.usefixtures("fixture_app")
def test_all_pacing_levels_judge_identically(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """SC-005 — 네 속도로 각각 실행해 통과/실패 판정과 실패 Step 위치가 모두 같다.

    **이것이 속도 조절의 전제다.** 사람이 보려고 느리게 돌린 실행이 다른 결과를 내면,
    빠르게 돌린 결과를 믿을 수 없어진다 — 느린 실행으로 확인한 것이 무의미해진다.

    `한 스텝씩` 은 사용자 지시로만 진행하므로 매 경계에서 이어하기를 눌러 준다.
    """
    import time

    from itb.domain.run_pacing import RunPacing, auto_pause

    test_id = record_login(keyed_client, fixture_app)
    verdicts: dict[str, tuple[str, object, int]] = {}

    for pacing in RunPacing:
        created = keyed_client.post(
            "/api/sessions",
            json={"mode": "replay", "test_id": test_id, "pacing": pacing.value},
        )
        assert created.status_code == 201, created.text
        sid = str(created.json()["session_id"])
        try:
            deadline = time.monotonic() + 90.0
            state = ""
            while time.monotonic() < deadline:
                state = keyed_client.get(f"/api/sessions/{sid}").json()["state"]
                if state in ("completed", "failed"):
                    break
                if state == "paused" and auto_pause(pacing):
                    # 한 스텝씩 — 사용자가 진행을 지시할 때까지 기다리는 것이 정상이다.
                    keyed_client.post(f"/api/sessions/{sid}/resume")
                time.sleep(0.03)
            assert state in ("completed", "failed"), (
                f"{pacing.value} 실행이 끝나지 않았다 (state={state})"
            )
        finally:
            stop_quietly(keyed_client, sid)

        result = result_of(keyed_client, test_id)
        verdicts[pacing.value] = (
            state,
            result["failed_step_index"],
            result["passed_count"],
        )

    distinct = set(verdicts.values())
    assert len(distinct) == 1, f"속도에 따라 판정이 갈렸다: {verdicts}"
