"""도착점의 경계. 016 FR-018·FR-020·FR-021 (T013a).

재녹화는 **화면을 구간 직전 상태로 만드는 것**에서 시작한다. 그 자리가 어디인지를
경계값에서 확인한다 — 목록의 처음·끝·깨진 앞 구간.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import break_first_click, record_login, stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us_rerecord.support import open_rerecord, step_ids

pytestmark = pytest.mark.browser


def test_a_range_starting_at_step_one_runs_nothing(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """구간이 첫 Step 부터면 **아무것도 실행하지 않는다** (FR-021).

    도착점이 「시작 주소를 연 상태」다. 앞 구간이 없으므로 실행할 것도 없다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[0]])
    assert isinstance(sid, str)
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "paused"
        assert view["current_step_index"] == 0, "첫 Step 앞에 멈춰야 한다"
        # 실행 결과가 하나도 없어야 한다 — 앞 구간을 돌지 않았다는 뜻이다.
        assert not view.get("step_results"), (
            f"아무것도 실행하지 않아야 하는데 결과가 있다: {view.get('step_results')}"
        )
        assert view["rerecord"]["range_step_ids"] == [saved[0]]
    finally:
        stop_quietly(keyed_client, sid)


def test_a_range_ending_at_the_last_step_is_allowed(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """구간 끝이 목록 끝이어도 된다. 「이 뒤 전부 지우기」와 결과가 같은 경우다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "paused"
        assert view["rerecord"]["range_step_ids"] == [saved[-1]]
        # 앞 구간은 전부 실행됐다.
        assert view["current_step_index"] == len(saved) - 1
    finally:
        stop_quietly(keyed_client, sid)


def test_the_whole_list_can_be_a_range(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """전체를 구간으로 잡으면 도착점은 시작 주소다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, saved)
    assert isinstance(sid, str)
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "paused"
        assert view["current_step_index"] == 0
        assert len(view["rerecord"]["range_step_ids"]) == len(saved)
    finally:
        stop_quietly(keyed_client, sid)


def test_the_old_range_is_still_in_the_list_at_the_start(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**옛 구간은 확정 전까지 목록에 남아 있다** (FR-024).

    먼저 지우면 실패했을 때 아무것도 없는 상태가 남는다 — 「넣고 지우기」 순서의 근거다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        assert step_ids(keyed_client, sid) == saved, "시작 시점 목록이 저장본과 같아야 한다"
        assert keyed_client.get(f"/api/sessions/{sid}").json()["rerecord"][
            "created_step_ids"
        ] == []
    finally:
        stop_quietly(keyed_client, sid)


def test_a_broken_prefix_says_which_step_failed(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """앞 구간이 깨져 도착점에 닿지 못하면 **어느 Step 에서 왜인지** 말한다 (FR-020).

    세션은 남는다 — 어디서 왜 실패했는지 보려면 세션이 필요하다. 그러나 트랜잭션은
    만들어지지 않는다: 교체를 시작하지 못했기 때문이다.
    """
    # **로그인만으로는 이 상황을 만들 수 없다** — 그 녹화는 클릭이 마지막이라 깨진
    # Step 을 앞 구간에 둘 자리가 없다. 메뉴까지 녹화해 뒤를 만든다.
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    broken_index = break_first_click(keyed_client, test_id)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    assert broken_index < len(saved) - 1, (
        "깨진 Step 이 마지막이면 앞 구간에 두는 검사가 성립하지 않는다"
    )

    resp = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "rerecord",
            "test_id": test_id,
            "rerecord_step_ids": [saved[-1]],
        },
    )
    assert resp.status_code == 201, resp.text
    sid = resp.json()["session_id"]
    try:
        from tests.us_rerecord.support import wait_for_state

        view = wait_for_state(keyed_client, sid, {"failed", "review"})
        results = {r["step_id"]: r for r in view.get("step_results") or []}
        failed = [sid_ for sid_, r in results.items() if r["outcome"] == "fail"]
        assert failed, "실패한 Step 이 결과에 드러나야 한다"
    finally:
        stop_quietly(keyed_client, sid)
