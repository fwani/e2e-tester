"""부분 실행의 결과 (005 T061·T062 · FR-152).

리포트 U-02 의 실측은 이랬다 — 「실패한 Step부터 실행」을 걸었더니,

- 결과가 **「통과 / 전체 = 0 / 7」** 이 됐다. 직전 실행의 5 / 7 이 사라졌다
- 부분 실행이라는 표시가 어디에도 없었다
- 건너뛴 01~05 와 도달 못한 07 이 똑같이 "—" + 빈 체크박스였다

사용자는 `5 / 7` → `0 / 7` 을 보고 "고치다 더 망가뜨렸다" 고 읽는다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from us2_support import record_login, start_replay, stop_quietly, wait_for_run


def _result(client: TestClient, test_id: str) -> dict:
    resp = client.get(f"/api/tests/{test_id}/result")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_full_run_records_full_scope(keyed_client: TestClient, fixture_app: str) -> None:
    """전체 실행은 `scope=full` 이고 시작 지점이 0 이다."""
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        wait_for_run(keyed_client, sid)
        result = _result(keyed_client, test_id)
        assert result["scope"] == "full"
        assert result["start_index"] == 0
        # 전체 실행에서는 보조 표시를 주지 않는다 — 같은 것을 두 번 보여줄 이유가 없다.
        assert result["last_full_run"] is None
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_partial_run_does_not_erase_the_last_full_run(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """부분 실행이 최근 전체 실행 결과를 덮지 않는다 (FR-152·U-02).

    **이것이 "고치다 더 망가뜨렸다" 는 오해를 없애는 장치다.**
    """
    test_id = record_login(keyed_client, fixture_app)

    # 1) 전체 실행으로 기준 결과를 만든다.
    first = start_replay(keyed_client, test_id)
    wait_for_run(keyed_client, first)
    baseline = _result(keyed_client, test_id)
    assert baseline["scope"] == "full"
    baseline_passed = baseline["passed_count"]
    keyed_client.post(f"/api/sessions/{first}/stop")
    keyed_client.post(f"/api/sessions/{first}/discard")

    # 2) 마지막 Step 부터 부분 실행한다.
    steps = keyed_client.get(f"/api/tests/{test_id}").json()["steps"]
    last_index = len(steps) - 1
    second = start_replay(keyed_client, test_id)
    try:
        moved = keyed_client.post(
            f"/api/sessions/{second}/run-from", json={"step_index": last_index}
        )
        assert moved.status_code == 200, moved.text
        wait_for_run(keyed_client, second)

        result = _result(keyed_client, test_id)
        assert result["scope"] == "partial", result["scope"]
        assert result["start_index"] == last_index

        # 최근 전체 실행이 보조로 남아 있다.
        full = result["last_full_run"]
        assert full is not None, (
            "부분 실행이 전체 실행 결과를 지웠다 (U-02) — 사용자는 나빠진 줄 안다"
        )
        assert full["scope"] == "full"
        assert full["passed_count"] == baseline_passed
    finally:
        stop_quietly(keyed_client, second)
        keyed_client.post(f"/api/sessions/{second}/discard")


def test_partial_run_denominator_excludes_skipped(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """분모는 실행 대상 수다 — `0 / 7` 이 아니다 (FR-152·U-02).

    건너뛴 Step 을 분모에 남기면 부분 실행이 항상 나빠 보인다.
    """
    test_id = record_login(keyed_client, fixture_app)
    steps = keyed_client.get(f"/api/tests/{test_id}").json()["steps"]
    last_index = len(steps) - 1

    sid = start_replay(keyed_client, test_id)
    try:
        keyed_client.post(f"/api/sessions/{sid}/run-from", json={"step_index": last_index})
        wait_for_run(keyed_client, sid)
        result = _result(keyed_client, test_id)

        skipped = [s for s in result["steps"] if s["outcome"] == "skipped"]
        assert len(skipped) == last_index, (
            f"앞선 {last_index}개가 건너뜀으로 기록되지 않았다: {[s['outcome'] for s in result['steps']]}"
        )
        assert result["attempted_count"] == result["total_count"] - len(skipped)
        assert result["attempted_count"] < result["total_count"], (
            "부분 실행인데 실행 대상 수가 전체와 같다"
        )
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_skipped_and_not_run_are_distinct_in_the_result(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """건너뜀과 미실행이 결과에서 구분된다 (FR-151·U-21).

    백엔드는 이미 두 값을 구분해 저장하고 있었다 — 화면이 그것을 읽지 않은 것이
    U-21 이었다. 이 테스트는 **그 구분이 계속 저장된다**는 것을 지킨다.
    """
    from itb.domain.run_result import StepOutcome

    assert {StepOutcome.SKIPPED, StepOutcome.NOT_RUN} <= set(StepOutcome), (
        "건너뜀·미실행 구분이 도메인에서 사라졌다"
    )
    assert StepOutcome.SKIPPED != StepOutcome.NOT_RUN
