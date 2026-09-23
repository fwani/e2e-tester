"""019 T090 — 공유 왕복 종단 테스트 (헌법 품질 게이트 2).

이 기능이 **새 왕복을 만들었다** — `record → store → export → import → replay`.
게이트 2 는 그 왕복이 일관된 결과를 내라고 요구한다.

**실제 녹화에서 출발한다.** 정의를 손으로 쓰면 「녹화가 만든 것」이 아니라 「우리가 옮겨
쓸 수 있다고 믿는 것」을 옮기게 된다. 로케이터 후보의 모양, 검증 스텝의 구성, 민감 값의
변수화 — 전부 녹화 경로가 만든 그대로여야 한다 (헌법 원칙 I).

**두 프로젝트를 쓴다.** 보내는 쪽과 받는 쪽이 같은 프로젝트면 「가져왔다」와 「원래
있었다」를 구별할 수 없다. 키는 같은 장비의 것이므로 민감 값 인계는 quickstart 의
작업 공간 분리 절차가 맡는다 (§0) — 여기서는 **값이 따라오지 않는다**는 사실만 본다.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from fastapi.testclient import TestClient
from us2_support import record_login, replay, result_of

SECRET_PASSWORD = "roundtrip-not-a-real-secret"


def _root(client: TestClient) -> pathlib.Path:
    return pathlib.Path(client.get("/api/project").json()["root"])


def _definition(client: TestClient, test_id: str) -> dict:
    root = _root(client)
    (path,) = [p for p in (root / "tests").iterdir() if p.name.startswith(f"{test_id}-")]
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.usefixtures("fixture_app")
def test_record_export_import_and_replay(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """quickstart §2~§4 — 녹화한 것이 묶음을 건너 그대로 복원되고 실행된다."""
    # ── 1. 녹화해서 저장한다. 민감 값은 녹화 중에 변수로 바뀐다 (FR-082a) ──────
    test_id = record_login(keyed_client, fixture_app, password=SECRET_PASSWORD)
    original = _definition(keyed_client, test_id)

    sensitive = [v for v in original["variables"] if v["sensitive"]]
    assert sensitive, "녹화가 민감 변수를 만들지 않았다 — 이 왕복이 확인할 것이 없어진다"
    secret_name = sensitive[0]["name"]

    # ── 2. 내보낸다. 민감 값이 바이트 어디에도 없어야 한다 (SC-004) ───────────
    exported = keyed_client.post("/api/share/export", json={})
    assert exported.status_code == 200, exported.text
    data = exported.content
    assert SECRET_PASSWORD.encode("utf-8") not in data

    secrets_file = _root(keyed_client) / "secrets.local.yaml"
    sealed = (yaml.safe_load(secrets_file.read_text(encoding="utf-8")) or {}).get("values") or {}
    assert sealed, "봉인된 값이 없으면 유출 검사가 아무것도 확인하지 않는다"
    text = data.decode("utf-8")
    assert [c for c in sealed.values() if c in text] == []

    # ── 3. 새 프로젝트로 가져온다 ────────────────────────────────────────────
    plan = keyed_client.post(
        "/api/share/import/plan?target=new",
        files={"file": ("동료-묶음.itbshare.yaml", data, "application/yaml")},
    )
    assert plan.status_code == 201, plan.text
    assert any(v["name"] == secret_name for v in plan.json()["required_values"])

    report = keyed_client.post(
        "/api/share/import/commit", json={"plan_id": plan.json()["plan_id"]}
    )
    assert report.status_code == 201, report.text
    restored_id = report.json()["created_tests"][0]["target_id"]

    # ── 4. 스텝이 로케이터 후보까지 그대로다 (헌법 원칙 IV) ──────────────────
    restored = _definition(keyed_client, restored_id)
    assert restored["steps"] == original["steps"], "스텝이 왕복에서 달라졌다"
    assert restored["variables"] == original["variables"]
    assert restored["start_url"] == original["start_url"]

    # 출처가 남고, 민감 값은 따라오지 않았다.
    assert restored["imported_from"]["original_id"] == test_id
    assert not (_root(keyed_client) / "secrets.local.yaml").exists()

    # ── 5. 값을 채우기 전에는 실행이 막힌다 (FR-044) ─────────────────────────
    #
    # **세션이 하나도 늘지 않았다는 것**을 본다. 「세션이 하나도 없다」로 재면 1단계 녹화가
    # 남긴 것에 걸리고, 「그 테스트의 세션이 없다」로 재도 마찬가지다 — 새 프로젝트의
    # 복원본이 원본과 같은 번호를 받았으므로 둘의 test_id 가 같다.
    before = {s["session_id"] for s in keyed_client.get("/api/sessions").json()["sessions"]}

    blocked = keyed_client.post(
        "/api/sessions", json={"mode": "replay", "test_id": restored_id}
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "SECRET_VALUE_MISSING"

    after = keyed_client.get("/api/sessions").json()["sessions"]
    assert {s["session_id"] for s in after} == before, "막혔는데 세션이 만들어졌다"

    # ── 6. 값을 채우면 실행되고, 원본과 같은 결과가 나온다 (SC-003) ──────────
    put = keyed_client.put(f"/api/secrets/{secret_name}", json={"value": SECRET_PASSWORD})
    assert put.status_code == 204, put.text
    assert keyed_client.get(f"/api/tests/{restored_id}/readiness").json()["runnable"] is True

    session = replay(keyed_client, restored_id)
    assert session["state"] == "completed", session

    result = result_of(keyed_client, restored_id)
    assert result["outcome"] == "pass", result
    assert result["total_count"] == len(original["steps"])
