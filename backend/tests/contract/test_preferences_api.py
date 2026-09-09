"""사용자 취향 엔드포인트 계약. 004 contracts/rest-api.md §3.

**프로젝트를 열지 않아도 동작해야 한다.** 취향은 사람에 속하고 프로젝트에 속하지 않는다.
첫 화면이 속도 기본값을 물어볼 수 있어야 하므로 `PROJECT_NOT_OPEN` 을 내면 안 된다.
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, start_replay, stop_quietly

from itb.domain.run_pacing import DEFAULT_PACING, RunPacing
from itb.storage import preferences


def test_get_returns_default_without_a_file(client: TestClient) -> None:
    resp = client.get("/api/preferences")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["run_pacing"] == DEFAULT_PACING.value
    assert body["warning"] is None


def test_put_then_get_round_trip(client: TestClient) -> None:
    put = client.put("/api/preferences", json={"run_pacing": RunPacing.SLOW.value})
    assert put.status_code == 200, put.text
    assert put.json()["run_pacing"] == RunPacing.SLOW.value

    got = client.get("/api/preferences")
    assert got.json()["run_pacing"] == RunPacing.SLOW.value


def test_unknown_value_is_rejected(client: TestClient) -> None:
    """열거형 밖 값은 422. 임의의 밀리초를 받지 않는다."""
    resp = client.put("/api/preferences", json={"run_pacing": "turtle"})
    assert resp.status_code == 422, resp.text


def test_extra_fields_are_rejected(client: TestClient) -> None:
    """**취향만 받는다** (조직 보안 요건).

    자격 증명·경로 같은 것이 이 엔드포인트로 흘러 들어가는 경로를 구조로 막는다.
    """
    resp = client.put(
        "/api/preferences",
        json={"run_pacing": RunPacing.FAST.value, "passphrase": "not-a-real-secret"},
    )
    assert resp.status_code == 422, resp.text


def test_broken_file_warns_but_does_not_fail(
    client: TestClient, isolated_home: pathlib.Path
) -> None:
    """읽기 실패는 경고로만 알린다 — 조회 자체는 성공한다.

    취향을 못 읽었다고 첫 화면이 안 열리면 사용자는 아무것도 할 수 없다.
    """
    path = preferences.preferences_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ 깨진 파일", encoding="utf-8")

    resp = client.get("/api/preferences")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["run_pacing"] == DEFAULT_PACING.value
    assert body["warning"], "읽지 못한 사유를 알려야 한다"


def test_write_failure_is_reported(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """저장 실패를 성공으로 보고하지 않는다.

    저장했다고 말한 뒤 다음 실행에서 사라지면 사용자는 무엇이 잘못됐는지 알 수 없다.
    """

    def _boom(_pacing: object) -> None:
        msg = "디스크 가득 참"
        raise preferences.PreferencesWriteError(msg)

    monkeypatch.setattr(preferences, "save", _boom)
    resp = client.put("/api/preferences", json={"run_pacing": RunPacing.FAST.value})
    assert resp.status_code == 500, resp.text
    assert resp.json()["error"]["code"] == "STORAGE_WRITE_FAILED"


# ─── 세션 속도 변경의 계약 (contracts/rest-api.md §2) ──────────────────────


def test_session_pacing_change_persists_the_preference(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-109 — 실행 중 변경도 취향에 남는다.

    "다음 실행에서 마지막 선택이 기본값" 은 실행 중 변경까지 반영되어야 성립한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": RunPacing.SLOW.value}
        )
        assert resp.status_code == 200, resp.text
        assert keyed_client.get("/api/preferences").json()["run_pacing"] == (
            RunPacing.SLOW.value
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_pacing_change_survives_preference_write_failure(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """취향 쓰기 실패로 **이 호출이 실패하지는 않는다.**

    속도는 이미 바뀌었다. 취향을 못 남긴 것 때문에 실행을 방해할 이유가 없다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)

    def _boom(_pacing: object) -> None:
        msg = "쓰기 실패"
        raise preferences.PreferencesWriteError(msg)

    monkeypatch.setattr(preferences, "save", _boom)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": RunPacing.SLOW.value}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["pacing"] == RunPacing.SLOW.value
    finally:
        stop_quietly(keyed_client, sid)


def test_unknown_session_is_not_found(client: TestClient) -> None:
    resp = client.post("/api/sessions/does-not-exist/pacing", json={"pacing": "slow"})
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_lost_session_accepts_pacing_change(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """유실된 세션에서도 속도를 바꿀 수 있다 (2026-09-09 사용자 결정).

    ## 이전 단언과 그 근거

    이전에는 409 `SESSION_LOST` 를 요구했고 근거는 이렇게 적혀 있었다 — 「속도를 받아 주면
    사용자는 다음 실행에 반영될 것으로 믿지만, 그 세션에는 다음 실행이 없다」.

    **그 전제가 사실이 아니었다.** 속도는 세션의 값이면서 **취향 파일에 남는 값**이고
    (FR-109 — 다음 실행에서 마지막 선택이 기본값), 유실 화면에 남는 길이 바로 「저장하고
    처음부터 다시 실행」이다. 사용자가 다음 실행을 준비하는 것을 막고 있었다.

    사용자 결정: 「속도 선택은 실행중이든 아니든 바꿀수있어야함」.
    """
    from itb.execution.state_machine import Command

    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        session = keyed_client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
        keyed_client.portal.call(  # type: ignore[attr-defined]
            lambda: session.apply(Command.SESSION_LOST)
        )
        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": RunPacing.SLOW.value}
        )
        assert resp.status_code == 200, resp.text
        # 세션의 값이 실제로 바뀐다 — 화면이 무엇을 골랐는지 되읽을 수 있어야 한다.
        assert resp.json()["pacing"] == RunPacing.SLOW.value
    finally:
        stop_quietly(keyed_client, sid)


def test_finished_session_accepts_pacing_change(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """끝난 세션의 속도도 바꿀 수 있다 (2026-09-09 사용자 결정).

    이 자리가 **가장 쓸모 있는 자리**다. 실행이 끝난 화면에는 「처음부터 실행」이 활성으로
    있고(국면 `finished`), 여기서 고른 값이 그 실행의 속도가 된다 (004 FR-109).

    거절이 있던 동안 화면 쪽도 함께 굳어 있었다 — 권한표가 그 거절을 비활성으로 옮겨
    그리느라, 실행 종료 화면의 속도 컨트롤 넷이 「실행이 이미 끝났습니다」를 달고 눌리지
    않는 채 서 있었다. 사용자가 지목한 것이 그 화면이다.
    """
    import time

    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        deadline = time.monotonic() + 90.0
        while time.monotonic() < deadline:
            state = keyed_client.get(f"/api/sessions/{sid}").json()["state"]
            if state in ("completed", "failed"):
                break
            time.sleep(0.05)
        else:
            pytest.fail("측정용 실행이 끝나지 않았다")

        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": RunPacing.SLOW.value}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["pacing"] == RunPacing.SLOW.value
        # 상태는 그대로다 — 속도 변경이 끝난 세션을 되살리지 않는다.
        assert resp.json()["state"] in ("completed", "failed")
    finally:
        stop_quietly(keyed_client, sid)
