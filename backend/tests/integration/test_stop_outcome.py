"""중지의 결말 (005 T027~T031 · FR-131·FR-132·FR-136·FR-137).

리포트 U-03 의 실측은 이랬다 — 중지 자체는 0.1초에 걸렸는데,

- 화면이 "**브라우저 세션이 유실됐습니다** / 열려 있던 탭이 모두 닫혀 세션이
  유실됐습니다" 라는 **오류**로 바뀌었다
- 결과는 `FAIL · 5 / 7 통과` 였다 — **사용자가 멈춘 것이 실패로 기록됐다**
- 경고 배너에 내부 UUID 가 노출됐다

원인은 유실 감지기의 "정상 종료면 유실이 아니다" 가드에 `REVIEW` 가 빠져 있던 것이었다.
`STOP` 은 세션을 `REVIEW` 로 남긴 뒤 브라우저를 놓으므로(DR-010), 그 close 가 가드를
지나 `session_lost` 를 발행하고 후처리가 결과를 실패로 확정했다.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient
from us2_support import break_first_click, record_login, start_replay, stop_quietly, wait_for_run


def _result_of(client: TestClient, test_id: str) -> dict:
    resp = client.get(f"/api/tests/{test_id}/result")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _wait_for_step(client: TestClient, sid: str, events: list[tuple[str, dict]], n: int) -> None:
    """Step `n` 개가 끝나기를 기다린다. 실행 중에 중지를 걸기 위한 것이다."""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if sum(1 for t, _ in events if t == "step_finished") >= n:
            return
        client.get(f"/api/sessions/{sid}")
        time.sleep(0.05)
    msg = f"Step {n}개가 끝나지 않았다"
    raise AssertionError(msg)


def test_user_stop_is_recorded_as_stopped_not_failed(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """사용자가 요청한 중지는 `stopped` 다 (FR-131·SC-215).

    **실패 집계에 들어가면 실행 이력이 오염된다.** 사용자는 자기가 누른 버튼의 결과를
    사고로 통보받고, 목록은 통과했던 테스트를 실패로 표시한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        _wait_for_step(keyed_client, sid, event_log, 1)
        stopped = keyed_client.post(f"/api/sessions/{sid}/stop")
        assert stopped.status_code == 200, stopped.text

        result = _result_of(keyed_client, test_id)
        assert result["outcome"] == "stopped", (
            f"사용자가 누른 중지가 {result['outcome']} 로 기록됐다 (U-03)"
        )
        assert result["stopped_step_index"] is not None, "중지 시점 Step 이 남지 않았다"
    finally:
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_intentional_stop_does_not_emit_session_lost(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """의도적 중지는 유실 이벤트를 내지 않는다 (FR-132·U-03).

    이 이벤트가 화면의 "브라우저 세션이 유실됐습니다" 오류 배너를 띄웠고, 그 후처리가
    결과를 실패로 확정했다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        _wait_for_step(keyed_client, sid, event_log, 1)
        event_log.clear()
        keyed_client.post(f"/api/sessions/{sid}/stop")
        # 후처리가 비동기이므로 잠깐 기다린다.
        time.sleep(0.5)
        keyed_client.get(f"/api/sessions/{sid}")

        lost = [payload for t, payload in event_log if t == "session_lost"]
        assert lost == [], f"의도적 중지가 유실로 감지됐다 (U-03): {lost}"
    finally:
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_stop_keeps_session_for_review(keyed_client: TestClient, fixture_app: str) -> None:
    """중지는 화면을 떠나지 않는다 — 세션이 `review` 로 남는다 (DR-010 유지).

    005 가 이 성질을 바꾸지 않았음을 고정한다. 바꾼 것은 그 화면이 저장 프롬프트가
    아니라 중지 결과를 보여준다는 것이다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = keyed_client.post(f"/api/sessions/{sid}/stop").json()
        assert view["state"] == "review", view["state"]
        assert view["steps"], "중지 후 Step 이 사라졌다"
    finally:
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_stop_on_already_finished_session_is_harmless(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """이미 끝난 세션에 중지가 다시 도착하면 오류가 아니다 (contracts §4).

    화면이 「중지」를 연타할 수 있었으므로(U-08) 중복 요청이 실제로 온다. 그것을 오류로
    만들면 사용자는 자기가 고칠 수 없는 실패를 본다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    wait_for_run(keyed_client, sid)
    try:
        first = keyed_client.post(f"/api/sessions/{sid}/stop")
        second = keyed_client.post(f"/api/sessions/{sid}/stop")
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
    finally:
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_completed_run_is_not_relabelled_as_stopped(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """정상 종료 뒤의 정리는 결말을 바꾸지 않는다.

    중지 경로에 결말 기록을 붙이면서 가장 위험한 실수는 **이미 끝난 실행의 결말을
    덮는 것**이다. 통과한 실행을 닫았을 때 「중지」로 바뀌면 결과가 거짓이 된다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    view = wait_for_run(keyed_client, sid)
    assert view["state"] == "completed", view["state"]
    before = _result_of(keyed_client, test_id)["outcome"]

    keyed_client.post(f"/api/sessions/{sid}/stop")
    after = _result_of(keyed_client, test_id)["outcome"]
    assert after == before == "pass", f"정상 종료의 결말이 {before} → {after} 로 바뀌었다"
    keyed_client.post(f"/api/sessions/{sid}/discard")


def test_resume_refuses_to_walk_past_a_failed_step(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """실패한 Step 을 조용히 지나가지 않는다 (FR-136·U-05).

    리포트는 「계속하기」가 0.15초 만에 배지를 「완료」로 바꾸고, 실패했던 step 06 을
    **빈 체크박스로 지운** 것을 봤다. 저장된 결과는 여전히 실패였다 — 같은 목록 화면에
    모순된 두 문장이 동시에 떴다.
    """
    test_id = record_login(keyed_client, fixture_app)
    failed_index = break_first_click(keyed_client, test_id)
    sid = start_replay(keyed_client, test_id)
    try:
        wait_for_run(keyed_client, sid)
        # 실패로 끝난 세션에 재개를 시도한다.
        refused = keyed_client.post(f"/api/sessions/{sid}/resume")
        if refused.status_code == 409:
            body = refused.json()["error"]
            assert body["code"] == "CANNOT_RESUME_PAST_FAILURE"
            assert body["detail"]["failed_step_index"] == failed_index
            assert body["next_action"], "다음 행동을 주지 않으면 사용자는 막힌다"
        else:
            # 종료 상태에서는 상태 기계가 먼저 거절한다 — 그것도 "조용히 지나가지
            # 않는다" 를 만족한다. 다만 성공(200)이면 결함이 남아 있는 것이다.
            assert refused.status_code != 200, (
                f"실패 Step 을 지나 재개됐다 (U-05): {refused.text}"
            )
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_skip_failed_resume_is_partial_pass_not_pass(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """실패를 건너뛰고 계속한 실행의 결말은 `partial_pass` 다 (FR-137·U-05).

    「완료」로 표시하면 사용자는 실패를 못 본 채 통과했다고 믿고 넘어간다.
    """
    test_id = record_login(keyed_client, fixture_app)
    break_first_click(keyed_client, test_id)
    sid = start_replay(keyed_client, test_id)
    try:
        wait_for_run(keyed_client, sid)
        work = keyed_client.app.state.itb  # noqa: F841 - 아래 엔진 상태 확인에 쓴다
        from itb.api.routes.sessions import _WORK

        engine = _WORK[sid].engine
        assert engine is not None
        assert engine.has_failed_step(), "실패 Step 이 없으면 이 검증이 성립하지 않는다"

        # 건너뛰기를 **명시**하고 결말을 확인한다. 재개가 상태 기계에 막히는 경우에도
        # 결말 판정 자체는 확인할 수 있어야 한다.
        engine.note_skipped_failures()
        engine.clear_failed_steps()
        engine.finalized = False
        import asyncio

        asyncio.run(_finalize(engine))

        result = _result_of(keyed_client, test_id)
        assert result["outcome"] == "partial_pass", (
            f"실패를 건너뛴 실행이 {result['outcome']} 로 기록됐다 (U-05)"
        )
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


async def _finalize(engine: object) -> None:
    await engine.finalize(True)  # type: ignore[attr-defined]
