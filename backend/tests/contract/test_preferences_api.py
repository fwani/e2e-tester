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
