"""004 US1 — Step 간 간격과 그 중단. FR-101·FR-103·FR-105·FR-106, SC-005·SC-007.

**간격이 사용자를 기다리게 만들면 안 된다.** 사람이 따라갈 시간을 주는 것이 목적인데,
그 때문에 멈추라는 지시가 늦게 먹으면 이 기능은 편의가 아니라 방해가 된다.

간격은 `asyncio.wait_for(session.wait_pause_requested(), timeout=간격)` 으로 잔다.
일시정지는 이벤트가 set 되는 즉시, 중지는 태스크 취소로 반영되므로 설계상 지연이 0에
가깝다 (research R6). 아래 상한 1초는 여유를 크게 둔 값이다.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, result_of, start_replay, stop_quietly

from itb.domain.run_pacing import RunPacing, delay_ms

INTERRUPT_LIMIT_S = 1.0
"""SC-007 — 간격 도중에 들어온 일시정지·중지가 반영되어야 하는 상한."""

SLOW_DELAY_MS = delay_ms(RunPacing.SLOW)


def _view(client: TestClient, sid: str) -> dict[str, Any]:
    resp = client.get(f"/api/sessions/{sid}")
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def _wait_for(client: TestClient, sid: str, states: set[str], timeout_s: float) -> str:
    deadline = time.monotonic() + timeout_s
    state = ""
    while time.monotonic() < deadline:
        state = _view(client, sid)["state"]
        if state in states:
            return state
        time.sleep(0.02)
    return state


def _start_slow_replay(client: TestClient, test_id: str) -> str:
    created = client.post(
        "/api/sessions",
        json={"mode": "replay", "test_id": test_id, "pacing": RunPacing.SLOW.value},
    )
    assert created.status_code == 201, created.text
    view = created.json()
    assert view["pacing"] == RunPacing.SLOW.value
    return str(view["session_id"])


# ─── FR-106 · SC-007 — 간격 도중 일시정지·중지 ─────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_pause_during_the_gap_is_immediate(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """SC-007 — `느림` 간격 도중 일시정지가 1초 안에 반영된다.

    `_resume` 이벤트만으로는 불가능한 일이다. 그 이벤트는 일시정지에서 `clear()` 되는데
    `asyncio.Event` 는 clear 를 기다릴 수 없다 (research R6). 이 테스트가 지키는 것은
    `_pause_requested` 라는 반대 방향 이벤트가 있어야 한다는 사실이다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = _start_slow_replay(keyed_client, test_id)
    try:
        # 첫 Step 이 끝나 간격에 들어갈 시간을 준다.
        time.sleep(SLOW_DELAY_MS / 1000 * 0.4)

        started = time.monotonic()
        resp = keyed_client.post(f"/api/sessions/{sid}/pause")
        assert resp.status_code == 200, resp.text
        state = _wait_for(keyed_client, sid, {"paused"}, INTERRUPT_LIMIT_S)
        elapsed = time.monotonic() - started

        assert state == "paused", f"{INTERRUPT_LIMIT_S}초 안에 멈추지 않았다 (state={state})"
        assert elapsed < INTERRUPT_LIMIT_S, f"{elapsed:.2f}초 걸렸다"
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_stop_during_the_gap_is_immediate(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """SC-007 — 중지도 간격이 끝나기를 기다리지 않는다.

    중지는 태스크 취소이고 `asyncio.wait_for` 는 취소 가능하다. 만약 간격을
    `asyncio.sleep` 으로 잤다면 그것도 취소되므로 이 테스트만으로는 설계가 갈리지
    않지만, 일시정지 쪽과 함께 두어 두 경로가 모두 막히지 않음을 고정한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = _start_slow_replay(keyed_client, test_id)
    try:
        time.sleep(SLOW_DELAY_MS / 1000 * 0.4)

        started = time.monotonic()
        resp = keyed_client.post(f"/api/sessions/{sid}/stop")
        assert resp.status_code == 200, resp.text
        elapsed = time.monotonic() - started
        assert elapsed < INTERRUPT_LIMIT_S, f"중지에 {elapsed:.2f}초 걸렸다"
    finally:
        stop_quietly(keyed_client, sid)


# ─── FR-103 — 실행 중 속도 변경 ────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_pacing_change_does_not_interrupt_running_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-103 — 속도 변경은 진행 중인 Step 을 끊지 않는다.

    변경 요청이 브라우저에 아무 명령도 보내지 않아야 하고, 실행이 계속되어야 한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = _start_slow_replay(keyed_client, test_id)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": RunPacing.FAST.value}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["pacing"] == RunPacing.FAST.value

        # 실행이 계속되어 끝난다 — 변경이 실행을 깨뜨리지 않았다.
        state = _wait_for(keyed_client, sid, {"completed", "failed"}, 60.0)
        assert state == "completed", f"속도 변경 후 실행이 {state} 로 끝났다"
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_pacing_survives_reconnect(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """세션 뷰가 속도를 싣는다 (contracts/rest-api.md §4).

    재연결 시 화면이 속도 표시를 복원하지 못하면, 사용자는 자기가 고른 속도가 아직
    적용 중인지 알 수 없다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = _start_slow_replay(keyed_client, test_id)
    try:
        assert _view(keyed_client, sid)["pacing"] == RunPacing.SLOW.value
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_unknown_pacing_is_rejected(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """열거형 밖 값은 받지 않는다. 임의의 밀리초 입력을 허용하지 않는다."""
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": "turtle"}
        )
        assert resp.status_code == 422, resp.text
    finally:
        stop_quietly(keyed_client, sid)


# ─── FR-101 · FR-105 — 간격이 생기되 예산 밖이다 ───────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_slow_run_takes_longer_but_judges_the_same(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-101·FR-104 — `느림` 은 더 오래 걸리되 판정을 바꾸지 않는다."""
    test_id = record_login(keyed_client, fixture_app)

    # **두 실행을 같은 기준으로 잰다.** 세션 생성에는 브라우저 실행이 들어 있어 1초 이상
    # 걸린다. 한쪽만 그것을 포함하면 간격 때문에 늘어난 시간이 그 안에 묻힌다.
    sid = start_replay(keyed_client, test_id)
    started = time.monotonic()
    try:
        fast_state = _wait_for(keyed_client, sid, {"completed", "failed"}, 90.0)
        fast_s = time.monotonic() - started
    finally:
        stop_quietly(keyed_client, sid)
    fast_result = result_of(keyed_client, test_id)

    sid = _start_slow_replay(keyed_client, test_id)
    started = time.monotonic()
    try:
        state = _wait_for(keyed_client, sid, {"completed", "failed"}, 90.0)
        slow_s = time.monotonic() - started
    finally:
        stop_quietly(keyed_client, sid)
    slow_result = result_of(keyed_client, test_id)

    assert state == fast_state, "속도가 판정을 바꿨다"
    assert slow_result["outcome"] == fast_result["outcome"]
    assert slow_result["failed_step_index"] == fast_result["failed_step_index"]

    step_count = len(fast_result["steps"])
    expected_extra_s = SLOW_DELAY_MS / 1000 * max(step_count - 1, 0)
    assert slow_s > fast_s + expected_extra_s * 0.5, (
        f"간격이 실제로 생기지 않았다. 빠름 {fast_s:.1f}s / 느림 {slow_s:.1f}s "
        f"(Step {step_count}개, 기대 추가 {expected_extra_s:.1f}s)"
    )


@pytest.mark.usefixtures("fixture_app")
def test_delay_excluded_from_step_budget(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-105 — 간격은 어느 Step 의 소요에도 들어가지 않는다.

    간격이 `duration_ms` 에 섞이면 시간 초과 판정이 속도에 따라 달라진다 — `느림` 으로
    돌렸다는 이유로 멀쩡한 Step 이 실패하게 된다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = _start_slow_replay(keyed_client, test_id)
    try:
        _wait_for(keyed_client, sid, {"completed", "failed"}, 90.0)
    finally:
        stop_quietly(keyed_client, sid)

    result = result_of(keyed_client, test_id)
    for step in result["steps"]:
        if step["outcome"] != "pass":
            continue
        assert step["duration_ms"] < SLOW_DELAY_MS, (
            f"{step['label']} 의 소요 {step['duration_ms']}ms 에 간격"
            f"({SLOW_DELAY_MS}ms)이 섞였다"
        )


@pytest.mark.usefixtures("fixture_app")
def test_no_delay_after_last_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """spec 엣지 케이스 — 마지막 Step 뒤에는 쉬지 않는다.

    끝난 실행이 끝나지 않은 것처럼 보이면 안 된다. 종료 상태 도달까지의 시간이 간격보다
    짧게 남는 것으로 확인한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = _start_slow_replay(keyed_client, test_id)
    try:
        state = _wait_for(keyed_client, sid, {"completed", "failed"}, 90.0)
        assert state == "completed"

        # 종료 직후 다시 조회해도 여전히 종료 상태다 — 뒤늦게 간격을 자고 있지 않다.
        started = time.monotonic()
        again = _view(keyed_client, sid)["state"]
        assert again == "completed"
        assert time.monotonic() - started < INTERRUPT_LIMIT_S
    finally:
        stop_quietly(keyed_client, sid)


# ─── FR-108 — 한 스텝씩 ────────────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_step_pacing_pauses_at_every_boundary(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-108 — `한 스텝씩` 은 매 Step 경계에서 멈추고, 기존 일시정지와 같은 조작을 받는다.

    **새 상태를 만들지 않는다** (research R7). `PAUSED` 에 들어가므로 편집·이어하기·중지
    규칙이 이미 검증된 경로를 그대로 쓴다.
    """
    test_id = record_login(keyed_client, fixture_app)
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "replay", "test_id": test_id, "pacing": RunPacing.STEP.value},
    )
    assert created.status_code == 201, created.text
    sid = str(created.json()["session_id"])
    try:
        state = _wait_for(keyed_client, sid, {"paused"}, 30.0)
        assert state == "paused", "한 스텝씩인데 Step 경계에서 멈추지 않았다"

        view = _view(keyed_client, sid)
        assert view["pacing"] == RunPacing.STEP.value, (
            "화면이 자동 일시정지와 사용자 일시정지를 구별할 근거가 필요하다"
        )
        # 자동 일시정지도 `PAUSED` 이므로 편집이 허용된다 (FR-108).
        assert "edit_steps" in view["allowed_commands"]

        index_before = view["current_step_index"]
        resumed = keyed_client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 200, resumed.text

        state = _wait_for(keyed_client, sid, {"paused", "completed"}, 30.0)
        assert state in {"paused", "completed"}
        if state == "paused":
            assert _view(keyed_client, sid)["current_step_index"] > index_before, (
                "이어하기가 한 Step 만 진행하고 다시 멈춰야 한다"
            )
    finally:
        stop_quietly(keyed_client, sid)
