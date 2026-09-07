"""006 T093 — 편집한 정의로 실제 실행이 돈다 (SC-308 · quickstart §4).

**계약 테스트가 덮지 않는 자리다.** `tests/contract/test_definition_edit_api.py` 는 편집이
정의 파일에 반영되는 것까지 본다. 그 다음 한 걸음 — **저장한 정의로 러너가 실제로 도는가** —
는 아무도 단정하지 않고 있었다 (converge F1).

그 한 걸음이 이 기능의 값 전체를 지탱한다. 편집이 실행에 반영되지 않으면 사용자는 고쳤다고
믿고 같은 실패를 다시 본다 — 006 이 없애려던 것보다 나쁜 상태다.

**여기서만 브라우저를 쓴다.** 편집 자체는 브라우저 없이 되지만(FR-182), "편집이 실행에
반영된다" 는 주장은 실행 없이 검증할 수 없다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, result_of


def _definition(client: TestClient, test_id: str) -> dict:
    resp = client.get(f"/api/tests/{test_id}/definition")
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def _save(client: TestClient, test_id: str, edits: list[dict]) -> dict:
    view = _definition(client, test_id)
    resp = client.put(
        f"/api/tests/{test_id}/definition",
        json={"revision": view["revision"], "edits": edits},
    )
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


@pytest.mark.usefixtures("fixture_app")
def test_edited_value_is_used_by_the_next_run(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-183 · SC-308 — 브라우저 없이 고친 값이 다음 실행에 쓰인다.

    이메일 칸의 값을 바꿔 저장하고 재실행한 뒤, **실행이 끝난 브라우저 화면**이 아니라
    저장된 정의와 실행 결과 양쪽이 새 값을 가리키는지 본다.
    """
    test_id = record_login(keyed_client, fixture_app)

    # 녹화된 Step 중 이메일을 채우는 것을 찾는다.
    steps = _definition(keyed_client, test_id)["test"]["steps"]
    email_step = next(
        (s for s in steps if s["type"] == "fill" and "@" in str(s.get("value", ""))),
        None,
    )
    assert email_step is not None, f"이메일 fill Step 을 찾지 못했다: {steps}"

    edited = "edited@example.internal"
    saved = _save(
        keyed_client,
        test_id,
        [{"op": "update", "step_id": email_step["id"], "value": edited}],
    )
    assert any(s.get("value") == edited for s in saved["test"]["steps"])

    view = replay(keyed_client, test_id)
    assert view["state"] in ("completed", "failed"), view["state"]

    # 실행이 읽은 정의가 편집본이다 — 세션 뷰의 Step 이 그 증거다.
    assert any(s.get("value") == edited for s in view["steps"]), (
        "실행이 편집 전 값을 쓰고 있다 — 편집이 실행에 반영되지 않았다"
    )


@pytest.mark.usefixtures("fixture_app")
def test_edited_timeout_is_used_by_the_next_run(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-183 · SC-308 — 대기 시간 편집이 실행에 반영된다.

    quickstart §4 가 사람에게 걸라고 적은 것과 같은 확인이다 — 대기 예산을 줄이면 실패까지
    걸리는 시간이 줄어야 한다. 여기서는 시간을 재지 않고 **러너가 읽은 값**을 본다.
    시간을 재면 기계 속도에 따라 흔들리는 테스트가 된다.
    """
    test_id = record_login(keyed_client, fixture_app)
    steps = _definition(keyed_client, test_id)["test"]["steps"]
    target = steps[0]
    assert target["timeout_ms"] != 3000, "픽스처 기본값과 겹쳐 검증이 무의미하다"

    _save(
        keyed_client,
        test_id,
        [{"op": "update", "step_id": target["id"], "timeout_ms": 3000}],
    )

    view = replay(keyed_client, test_id)
    ran = next(s for s in view["steps"] if s["id"] == target["id"])
    assert ran["timeout_ms"] == 3000, (
        f"실행이 옛 대기 시간을 쓰고 있다: {ran['timeout_ms']}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_deleted_step_is_not_executed(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-184 · SC-308 — 지운 Step 은 실행되지 않는다.

    삭제가 정의에서만 사라지고 실행에는 남아 있으면, 사용자는 지웠다고 믿는데 그 동작이
    계속 일어난다. 그것은 조용한 오작동이다.
    """
    test_id = record_login(keyed_client, fixture_app)
    steps = _definition(keyed_client, test_id)["test"]["steps"]
    assert len(steps) >= 2, f"삭제를 검증할 Step 이 부족하다: {len(steps)}"
    removed = steps[-1]["id"]
    before = len(steps)

    _save(keyed_client, test_id, [{"op": "delete", "step_id": removed}])

    view = replay(keyed_client, test_id)
    executed_ids = {s["id"] for s in view["steps"]}
    assert removed not in executed_ids, "지운 Step 이 아직 실행 목록에 있다"

    result = result_of(keyed_client, test_id)
    assert result["total_count"] == before - 1, (
        f"결과가 옛 Step 수를 쓰고 있다: {result['total_count']} (기대 {before - 1})"
    )


@pytest.mark.usefixtures("fixture_app")
def test_editing_does_not_break_the_secret_reference(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-214 · SC-308 — 편집 뒤에도 민감 값이 실행에서 채워진다.

    변수 파생이 두 벌이면 여기서 깨진다 — 민감 표시가 강등되면 재실행이 빈 값을 채우고,
    로그인이 조용히 실패한다 (research R5 가 막으려던 것). 그것을 실행으로 확인한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    view0 = _definition(keyed_client, test_id)
    sensitive = [v for v in view0["test"]["variables"] if v["sensitive"]]
    assert sensitive, "민감 변수가 없어 이 검증이 성립하지 않는다"

    # 민감 값과 **무관한** Step 을 고친다. 그것이 변수 정의를 흔들면 안 된다.
    other = next(
        s for s in view0["test"]["steps"] if str(s.get("value", "")) != ""
        and not str(s.get("value", "")).startswith("{{")
    )
    saved = _save(
        keyed_client,
        test_id,
        [{"op": "update", "step_id": other["id"], "label": "편집한 라벨"}],
    )
    after = {v["name"]: v for v in saved["test"]["variables"]}
    for v in sensitive:
        assert after[v["name"]]["sensitive"] is True, (
            f"{v['name']} 의 민감 표시가 강등됐다 — 재실행이 빈 값을 채운다"
        )
        assert after[v["name"]]["value"] is None

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", (
        f"편집 뒤 재실행이 통과하지 못했다: {view['state']} — 민감 값이 채워지지 않았을 수 있다"
    )
