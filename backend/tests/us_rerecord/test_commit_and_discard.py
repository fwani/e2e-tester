"""US2 — 구간 교체의 두 결말. 016 FR-025~FR-031c (T036~T039·T040b).

이 파일이 고정하는 핵심은 **불변식 9** 다 — 버리면 목록이 시작 전과 완전히 같아진다.
그것이 성립해야 사용자가 「버리기」를 누를 수 있고, 누를 수 있어야 시행착오 루프가
성립한다. 이 기능의 값 전체가 거기 걸려 있다.

새 Step 은 **사람 조작으로** 만든다. AI 대본으로 만들 수도 있지만, 그러면 실패 원인이
둘이 된다(교체 로직 / 대본). 여기서 보는 것은 교체이지 AI 가 아니다 — 그리고 016 은
「이번 세션이 만든 Step」을 작성 주체로 구분하지 않으므로(원칙 I) 사람이 만든 것으로
확인하는 것이 오히려 정확하다.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, replay, stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us_rerecord.support import open_rerecord, wait_for_index, wait_for_state

pytestmark = pytest.mark.browser


def snapshot(client: TestClient, sid: str) -> list[tuple[str, str]]:
    """id 와 내용을 함께 본다. id 만 비교하면 내용이 바뀐 것을 놓친다."""
    steps = client.get(f"/api/sessions/{sid}").json()["steps"]
    return [(s["id"], repr(sorted(s.items()))) for s in steps]


def insert_manual(client: TestClient, sid: str, url: str, at: int) -> str:
    """브라우저 없이 만들 수 있는 Step 을 한 개 넣는다 (009 FR-285).

    주소 이동은 요소를 지목하지 않으므로 화면 상태와 무관하게 만들어진다 — 교체
    트랜잭션만 보려는 이 파일에 알맞다.
    """
    resp = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": url}, "at": at},
    )
    assert resp.status_code == 200, resp.text
    steps = resp.json()["steps"]
    return str(steps[at]["id"])


def rerecord_of(client: TestClient, sid: str) -> dict[str, Any] | None:
    return client.get(f"/api/sessions/{sid}").json().get("rerecord")


# ─── 확정 (T036 · FR-026·FR-028·FR-030) ─────────────────────────────────────


def test_commit_removes_the_old_range_in_one_go(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """옛 구간이 **한 번에** 사라지고 앞뒤가 이어진다 (FR-026)."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    victim = saved[-2:]

    sid = open_rerecord(keyed_client, test_id, victim)
    assert isinstance(sid, str)
    try:
        at = len(saved) - 2
        made = insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)

        before = [s["id"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]]
        assert made in before and all(v in before for v in victim), (
            "확정 전에는 새 Step 과 옛 구간이 **함께** 있어야 한다 (FR-024)"
        )

        resp = keyed_client.post(f"/api/sessions/{sid}/rerecord/commit")
        assert resp.status_code == 200, resp.text

        after = [s["id"] for s in resp.json()["steps"]]
        assert made in after
        for v in victim:
            assert v not in after, f"옛 구간이 남았다: {v}"
        assert after == [*saved[:at], made], "앞 구간 + 새 Step 이어야 한다"
        assert resp.json()["rerecord"] is None, "끝난 교체는 화면에 남지 않는다"
    finally:
        stop_quietly(keyed_client, sid)


def test_commit_is_refused_when_nothing_was_created(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """빈 것으로 교체하는 것은 **구간 삭제**이지 재녹화가 아니다 (FR-028 · 불변식 10).

    재녹화 버튼으로 삭제가 일어나면 사용자는 무엇이 지워질지 예측할 수 없다. 그리고
    구간 삭제는 이미 있는 조작이다 (`step.deleteSelected`).
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        assert rerecord_of(keyed_client, sid)["can_commit"] is False

        resp = keyed_client.post(f"/api/sessions/{sid}/rerecord/commit")
        assert resp.status_code == 409, resp.text
        assert resp.json()["error"].get("next_action")

        after = [s["id"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]]
        assert after == saved, "거절했는데 목록이 바뀌었다"
    finally:
        stop_quietly(keyed_client, sid)


def test_can_commit_turns_true_once_something_is_made(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """`can_commit` 은 **서버가 판정한다** (불변식 10).

    화면이 조건을 복제하면 서버와 갈리고, 갈리면 활성으로 그린 버튼이 눌린 뒤 거절된다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        assert rerecord_of(keyed_client, sid)["can_commit"] is False
        insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", len(saved) - 1)
        view = rerecord_of(keyed_client, sid)
        assert view["can_commit"] is True
        assert len(view["created_step_ids"]) == 1
    finally:
        stop_quietly(keyed_client, sid)


# ─── 버리기 (T037 · FR-027 · 불변식 9 · SC-004) ─────────────────────────────


@pytest.mark.parametrize("round_no", range(20))
def test_discard_restores_the_list_exactly_every_time(
    keyed_client: TestClient, fixture_app: str, round_no: int
) -> None:
    """**불변식 9 — 20회 모두** 시작 전과 id·순서·내용까지 같다 (SC-004).

    반복인 이유는 이것이 신뢰의 기반이기 때문이다. 스무 번 중 한 번이라도 목록이
    달라지면 사용자는 버리기를 누르지 못하고, 누르지 못하면 시행착오 루프가 성립하지
    않는다.

    통합 계층에서 20회를 도는 대가는 시간이다. 그럼에도 여기서 도는 이유는 단위
    계층(`test_rerecord_transaction.py`)이 **순수 함수**만 보기 때문이다 — 실제로
    되돌아가는지는 세션·컴파일러·이벤트가 함께 도는 자리에서만 확인된다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        before = snapshot(keyed_client, sid)
        at = len(saved) - 1
        for i in range(1 + round_no % 3):
            insert_manual(keyed_client, sid, f"{fixture_app}/projects.html?r={i}", at + i)

        assert snapshot(keyed_client, sid) != before, "만들지 않았으면 검사가 헛돈다"

        resp = keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        assert resp.status_code == 200, resp.text
        wait_for_state(keyed_client, sid, {"paused"})

        assert snapshot(keyed_client, sid) == before, (
            f"{round_no}회차에서 목록이 시작 전과 달라졌다 — 불변식 9 위반"
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_discard_with_nothing_created_is_allowed(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """아무것도 만들지 않은 채 그만두는 것은 정상이다. 확정과 다른 점이다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        before = snapshot(keyed_client, sid)
        resp = keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        assert resp.status_code == 200, resp.text
        wait_for_state(keyed_client, sid, {"paused"})
        assert snapshot(keyed_client, sid) == before
    finally:
        stop_quietly(keyed_client, sid)


# ─── 버리기의 되맞춤 (T038 · FR-031·FR-031a) ────────────────────────────────


def test_discard_keeps_the_session_alive_and_realigns(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """버리기는 **세션을 끝내지 않고** 화면을 도착점으로 되맞춘다 (FR-031·FR-031a).

    끝내는 조작은 기존 「중지」다. 둘이 같은 일을 하면 사용자는 누를 때마다 차이를
    확인하느라 멈춘다 — 그리고 이 기능의 값은 시행착오 루프에 있다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    at = len(saved) - 1

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)
        keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        # **상태만 보면 안 된다** — 되맞춤은 `paused` 에서 시작해 `paused` 로 끝나므로
        # 시작하기도 전에 통과한다. 실행 위치가 도착점에 닿는 것을 본다.
        view = wait_for_index(keyed_client, sid, at)

        assert view["state"] == "paused", "세션이 살아 있어야 한다"
        assert view["rerecord"] is None, "끝난 교체는 화면에 남지 않는다"
    finally:
        stop_quietly(keyed_client, sid)


def test_discard_twice_is_refused(keyed_client: TestClient, fixture_app: str) -> None:
    """연타 방지 — 되맞춤이 도는 중에 또 눌리면 실행이 겹친다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        first = keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        assert first.status_code == 200, first.text
        second = keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        assert second.status_code == 409, second.text
    finally:
        stop_quietly(keyed_client, sid)


def test_commit_after_discard_is_refused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """한 트랜잭션에 결말은 하나뿐이다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        resp = keyed_client.post(f"/api/sessions/{sid}/rerecord/commit")
        assert resp.status_code == 409, resp.text
    finally:
        stop_quietly(keyed_client, sid)


# ─── 확정 전 저장 금지 (T039 · FR-029) ──────────────────────────────────────


def test_saving_before_settling_is_refused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**확정되지 않은 교체는 디스크에 닿지 않는다** (FR-029).

    지금 목록은 「옛 구간 + 새 Step」이 함께 있는 중간 상태다. 그대로 저장하면 사용자가
    의도하지 않은 정의가 자산이 되고, 되돌릴 방법은 손편집뿐이다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    at = len(saved) - 1

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)

        resp = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "중간 상태"})
        assert resp.status_code == 409, resp.text
        body = resp.json()["error"]
        assert "확정" in body["next_action"] and "버리기" in body["next_action"], (
            "양쪽 길을 다 말해야 한다 — 확정도 버리기도 사용자의 정당한 선택이다"
        )

        on_disk = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
        assert on_disk == saved, "거절했는데 디스크가 바뀌었다"
    finally:
        stop_quietly(keyed_client, sid)


def test_saving_after_commit_works(keyed_client: TestClient, fixture_app: str) -> None:
    """확정하면 저장이 풀린다. 막는 것은 **중간 상태**이지 재녹화 자체가 아니다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    at = len(saved) - 1

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)
        keyed_client.post(f"/api/sessions/{sid}/rerecord/commit")

        resp = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "교체 완료"})
        assert resp.status_code == 200, resp.text

        on_disk = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
        assert saved[-1] not in on_disk, "옛 구간이 디스크에 남았다"
    finally:
        stop_quietly(keyed_client, sid)


# ─── 확정 후 전체 실행 (T040b · SC-005) ─────────────────────────────────────


def test_the_test_still_runs_end_to_end_after_a_commit(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**확정·저장 후 처음부터 끝까지 실행해 성공한다** (SC-005).

    이 기능의 최종 판정 기준이다. 새 Step 이 이어 붙은 자리에서 깨지면 재녹화는
    쓸모가 없다 — 사용자는 고치려다 테스트를 망가뜨린 것이 된다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    at = len(saved) - 1

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)
        assert keyed_client.post(f"/api/sessions/{sid}/rerecord/commit").status_code == 200
        assert (
            keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "교체됨"}).status_code
            == 200
        )
    finally:
        stop_quietly(keyed_client, sid)

    result = replay(keyed_client, test_id)
    assert result["state"] == "completed", (
        f"교체한 테스트가 처음부터 돌지 않는다: {result.get('state')} — SC-005 위반"
    )


# ─── 되맞춤 실패 (T073 · FR-031c · 불변식 11) ──────────────────────────────


def test_a_failed_realign_says_both_facts(
    keyed_client: TestClient,
    fixture_app: str,
    monkeypatch: pytest.MonkeyPatch,
    event_log: list[tuple[str, dict[str, Any]]],
) -> None:
    """되맞춤이 실패하면 **두 사실을 함께** 말한다 (불변식 11).

    정의는 이미 원본으로 돌아갔고, 화면은 그것과 어긋나 있다. 둘 중 하나만 말하면
    사용자는 무엇을 믿어야 할지 모른다 — 목록을 보고 「되돌아갔구나」 하면서 화면은
    엉뚱한 자리에 있거나, 「실패했구나」 하면서 목록이 이미 바뀐 것을 모른다.

    실패를 **유도한다.** 되맞춤은 시작 주소로 돌아간 뒤 앞 구간을 다시 도는데, 그
    첫 걸음(`_return_to_start`)을 터뜨린다 — 실제로도 대상 앱이 내려가면 그렇게 된다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    at = len(saved) - 1

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)

        # 되맞춤의 첫 걸음을 터뜨린다.
        from itb.api.routes import sessions as routes

        async def boom(_w: Any) -> None:
            msg = "대상 앱에 닿을 수 없습니다"
            raise RuntimeError(msg)

        monkeypatch.setattr(routes, "_return_to_start", boom)

        resp = keyed_client.post(f"/api/sessions/{sid}/rerecord/discard")
        assert resp.status_code == 200, resp.text

        failed = [p for name, p in event_log if name == "rerecord_realign_failed"]
        assert failed, (
            f"되맞춤 실패가 알려지지 않았다. 받은 이벤트: {sorted({n for n, _ in event_log})}"
        )

        payload = failed[0]
        # **사실 1** — 정의는 이미 되돌아갔다.
        assert payload["definition_reverted"] is True
        # **사실 2** — 왜 화면을 맞추지 못했는가.
        assert "대상 앱에 닿을 수 없습니다" in payload["reason"]

        # 그리고 실제로 정의는 되돌아가 있다 — 말과 상태가 같아야 한다.
        after = [s["id"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]]
        assert after == saved, "되돌아갔다고 말했는데 목록이 다르다"
    finally:
        stop_quietly(keyed_client, sid)


# ─── 도착점에 닿지 못하면 재녹화를 시작하지 않는다 (T071 · FR-020) ─────────


def test_a_broken_prefix_closes_the_transaction(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """앞 구간이 깨지면 **교체가 시작되지 않는다** (FR-020 · 수렴 T071).

    트랜잭션은 러너를 띄우기 전에 만들어진다 — 도착점 순번을 그 시점에만 알 수 있기
    때문이다. 그래서 닫아 주지 않으면 「교체가 시작된 채 세션은 실패」인 상태가 남고,
    사용자는 재녹화 띠를 보면서 확정도 버리기도 할 수 없다 (둘 다 `paused` 를 요구하고
    세션은 `failed` 다).
    """
    from tests.us2_support import break_first_click

    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    broken = break_first_click(keyed_client, test_id)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    assert broken < len(saved) - 1, "깨진 Step 이 앞 구간에 있어야 한다"

    resp = keyed_client.post(
        "/api/sessions",
        json={"mode": "rerecord", "test_id": test_id, "rerecord_step_ids": [saved[-1]]},
    )
    assert resp.status_code == 201, resp.text
    sid = resp.json()["session_id"]
    try:
        view = wait_for_state(keyed_client, sid, {"failed", "review"})
        assert view["rerecord"] is None, (
            "도착점에 닿지 못했는데 교체가 시작된 채로 남았다 — FR-020 위반"
        )
        # 어느 Step 에서 실패했는지 결과에 남아 있어야 한다.
        results = view.get("step_results") or []
        assert any(r["outcome"] == "fail" for r in results), (
            "실패한 Step 이 결과에 드러나지 않는다"
        )
    finally:
        stop_quietly(keyed_client, sid)


# ─── 세션 유실 (T074 · FR-044) ─────────────────────────────────────────────


def test_a_lost_session_keeps_what_was_made_and_says_so(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """세션이 유실되면 만든 Step 을 **보존**하고 중간 상태임을 알린다 (FR-044).

    기존 유실 처리가 「그때까지의 결과를 보존」하는 것과 같은 판단이다 — 사용자가
    버리기를 고르지 않았는데 제품이 버리지 않는다. 다만 목록은 「옛 구간 + 새 Step」이
    함께 있는 중간 상태이므로, 그것을 말하지 않으면 사용자는 저장하고 나서야 안다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    at = len(saved) - 1

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        made = insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)

        # 브라우저를 사용자가 닫은 것처럼 만든다.
        #
        # **실제로 창을 닫지 않는다.** 유실 처리(`_loss_handler`)를 직접 부르는 것이
        # 이 검사가 보려는 것이다 — 창을 닫는 경로는 010 이 이미 검증했고, 여기서
        # 재현하면 실패 원인이 둘이 된다 (감지 / 처리).
        from itb.api.routes import sessions as routes

        handler = routes._loss_handler(
            keyed_client.app.state.itb,  # type: ignore[attr-defined]
            sid,
        )
        keyed_client.portal.call(  # type: ignore[attr-defined]
            lambda: handler("사용자가 창을 닫았습니다")
        )

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        steps_now = [s["id"] for s in view["steps"]]
        assert made in steps_now, "유실되면서 만든 Step 이 사라졌다 — FR-044 위반"
        for old in saved:
            assert old in steps_now, "옛 구간도 남아 있어야 한다 (중간 상태)"
        assert view["rerecord"] is None, (
            "브라우저가 없으면 확정도 버리기도 할 수 없다 — 트랜잭션을 닫아야 한다"
        )
    finally:
        stop_quietly(keyed_client, sid)
