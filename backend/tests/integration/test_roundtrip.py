"""T072 — 녹화 → 저장 → 재실행 왕복과 결정성 (헌법 품질 게이트 2, SC-003).

**한 번 통과하는 것으로는 부족하다.** 대상 앱이 바뀌지 않았는데 결과가 흔들리면 그 테스트는
회귀 신호로 쓸 수 없다. 그래서 같은 정의를 연속으로 여러 번 돌려 매번 같은 결과가 나오는지 본다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, result_of

DETERMINISM_RUNS = 10
"""헌법 품질 게이트 2 — 10회 연속 동일 결과."""


@pytest.mark.usefixtures("fixture_app")
def test_recorded_test_replays_and_matches_definition(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """녹화한 Step 목록과 실행 결과의 Step 목록이 1:1로 대응한다."""
    test_id = record_login(keyed_client, fixture_app)
    definition = keyed_client.get(f"/api/tests/{test_id}").json()

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", f"재실행이 실패했다: {view['state']}"

    result = result_of(keyed_client, test_id)
    assert result["outcome"] == "pass"
    assert result["total_count"] == len(definition["steps"])
    assert result["passed_count"] == result["total_count"]
    assert result["failed_step_index"] is None
    assert result["browser"], "FR-058 — 어떤 브라우저로 실행했는지가 결과에 있어야 한다"

    assert [s["step_id"] for s in result["steps"]] == [
        s["id"] for s in definition["steps"]
    ], "결과의 Step 순서가 정의와 다르다"
    assert all(s["outcome"] == "pass" for s in result["steps"])
    assert all(s["duration_ms"] >= 0 for s in result["steps"])


@pytest.mark.usefixtures("fixture_app")
def test_repeated_replay_is_deterministic(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """SC-003 — 대상 앱을 바꾸지 않으면 10회 연속 같은 결과가 나온다."""
    test_id = record_login(keyed_client, fixture_app)

    outcomes: list[str] = []
    step_outcomes: list[tuple[str, ...]] = []
    for _ in range(DETERMINISM_RUNS):
        view = replay(keyed_client, test_id)
        outcomes.append(view["state"])
        result = result_of(keyed_client, test_id)
        step_outcomes.append(tuple(s["outcome"] for s in result["steps"]))

    assert set(outcomes) == {"completed"}, (
        f"{DETERMINISM_RUNS}회 중 통과하지 않은 실행이 있다: {outcomes}"
    )
    assert len(set(step_outcomes)) == 1, (
        f"Step별 결과가 실행마다 달랐다 — 결정적이지 않다: {set(step_outcomes)}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_replay_reuses_the_saved_definition_only(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-045 — 실행은 저장된 정의만 근거로 한다.

    정의 파일을 지운 뒤 재실행을 요청하면 `404` 여야 한다. 세션이 어딘가에 사본을 들고
    있으면 이 요청이 성공해 버린다.

    **삭제는 `204` 가 아니다** (013 FR-437). 옮겨진 자리를 돌려주지 않으면 사용자가
    되돌릴 수 없어, 「파괴하지 않는다」는 결정이 사용자에게는 삭제와 구별되지 않는다.
    이 검사가 재는 것은 삭제의 응답 형태가 아니라 **정의가 실제로 사라졌는가**이므로,
    옮겨진 자리가 실렸는지까지만 확인하고 넘어간다.
    """
    test_id = record_login(keyed_client, fixture_app)
    assert replay(keyed_client, test_id)["state"] == "completed"

    removed = keyed_client.delete(f"/api/tests/{test_id}")
    assert removed.status_code == 200, removed.text
    assert removed.json()["trashed_to"], "옮겨진 자리가 없으면 되돌릴 방법이 없다"

    resp = keyed_client.post(
        "/api/sessions", json={"mode": "replay", "test_id": test_id}
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"
