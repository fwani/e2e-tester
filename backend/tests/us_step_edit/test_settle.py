"""US2 — Step 수정의 두 결말. 026 FR-021~FR-029 (contracts/api-contract §2·§3).

이 파일이 고정하는 핵심은 **불변식 B** 다 — 버리면 목록이 시작 전과 id·순서·내용까지
같아진다. 016 은 그것을 「스냅샷 없이」 성립시켰고(research R7), 이 기능은 그 전제를
깨므로 **원본을 보관해서** 성립시킨다.

새 Step 은 016 의 검사와 같은 이유로 **사람 조작으로** 만든다 — AI 대본으로 만들면
실패 원인이 둘이 되고(트랜잭션 / 대본), 원칙 I 이 작성 주체를 구분하지 않으므로 사람이
만든 것으로 확인하는 쪽이 오히려 정확하다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us_rerecord.support import wait_for_index
from tests.us_step_edit.support import open_step_edit, snapshot, step_edit_of

pytestmark = pytest.mark.browser


def saved_ids(client: TestClient, test_id: str) -> list[str]:
    return [s["id"] for s in client.get(f"/api/tests/{test_id}").json()["steps"]]


def insert_manual(client: TestClient, sid: str, url: str, at: int) -> str:
    """브라우저 없이 만들 수 있는 Step 을 하나 넣는다 (009 FR-285).

    주소 이동은 요소를 지목하지 않으므로 화면 상태와 무관하게 만들어진다 — 트랜잭션만
    보려는 이 파일에 알맞다 (016 의 같은 헬퍼와 같은 판단).
    """
    resp = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": url}, "at": at},
    )
    assert resp.status_code == 200, resp.text
    return str(resp.json()["steps"][at]["id"])


def relabel(client: TestClient, sid: str, step_id: str, label: str) -> None:
    """사람의 편집으로 대상을 고친다. AI 가 `update_step` 으로 하는 것과 **같은 함수**를
    지난다 (원칙 I) — 그래서 트랜잭션 입장에서 구별되지 않는다."""
    resp = client.patch(
        f"/api/sessions/{sid}/steps/{step_id}",
        json={"label": label},
    )
    assert resp.status_code == 200, resp.text


# ─── 확정 — 016 과 정반대다 (FR-021·FR-023 · research R5) ───────────────────


def test_commit_deletes_nothing(keyed_client: TestClient, fixture_app: str) -> None:
    """확정해도 **아무 Step 도 사라지지 않는다.** 016 과 갈리는 자리다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        relabel(keyed_client, sid, target, "고친 이름")
        before = [s["id"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]]

        resp = keyed_client.post(f"/api/sessions/{sid}/step-edit/commit")
        assert resp.status_code == 200, resp.text

        after = resp.json()["steps"]
        assert [s["id"] for s in after] == before, "확정이 무언가를 지웠다"
        assert next(s for s in after if s["id"] == target)["label"] == "고친 이름"
        assert resp.json()["step_edit"] is None, "끝난 수정은 화면에서 거둔다"
    finally:
        stop_quietly(keyed_client, sid)


def test_commit_is_allowed_when_nothing_was_made(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**만든 것이 없어도 확정된다** (research R5).

    016 은 빈 구간 교체가 조용한 삭제이므로 잠갔다. 이쪽은 교체하지 않으므로 그 위험이
    없고, 같은 규칙을 베끼면 「AI 에게 물어만 보고 그만두기」가 막힌다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(sid, str)
    try:
        view = step_edit_of(keyed_client, sid)
        assert view is not None and view["can_commit"] is True
        assert keyed_client.post(f"/api/sessions/{sid}/step-edit/commit").status_code == 200
    finally:
        stop_quietly(keyed_client, sid)


def test_settling_twice_is_refused(keyed_client: TestClient, fixture_app: str) -> None:
    """연타 방지 — 되맞춤이 도는 중에 또 눌리면 실행이 겹친다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(sid, str)
    try:
        assert keyed_client.post(f"/api/sessions/{sid}/step-edit/commit").status_code == 200
        assert keyed_client.post(f"/api/sessions/{sid}/step-edit/commit").status_code == 409
        assert keyed_client.post(f"/api/sessions/{sid}/step-edit/discard").status_code == 409
    finally:
        stop_quietly(keyed_client, sid)


def test_settling_without_an_open_edit_is_refused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    test_id = record_login(keyed_client, fixture_app)
    created = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    sid = created.json()["session_id"]
    try:
        assert keyed_client.post(f"/api/sessions/{sid}/step-edit/commit").status_code == 409
    finally:
        stop_quietly(keyed_client, sid)


# ─── 버리기 — 불변식 B (FR-022·FR-029) ──────────────────────────────────────


def test_discard_restores_the_modified_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """고쳐진 Step 이 **시작 전 모습 그대로** 돌아온다. 식별자까지 같다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        before = snapshot(keyed_client, sid)
        relabel(keyed_client, sid, target, "고친 이름")
        assert snapshot(keyed_client, sid) != before, "고쳐지지 않았으면 검사가 뜻이 없다"

        resp = keyed_client.post(f"/api/sessions/{sid}/step-edit/discard")
        assert resp.status_code == 200, resp.text
        wait_for_index(keyed_client, sid, len(saved) - 1)

        assert snapshot(keyed_client, sid) == before
    finally:
        stop_quietly(keyed_client, sid)


def test_discard_also_removes_what_was_made(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """새로 만든 Step 과 고쳐진 대상이 **함께** 되돌아온다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        before = snapshot(keyed_client, sid)
        made = insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", len(saved) - 1)
        relabel(keyed_client, sid, target, "고친 이름")

        resp = keyed_client.post(f"/api/sessions/{sid}/step-edit/discard")
        assert resp.status_code == 200, resp.text
        wait_for_index(keyed_client, sid, len(saved) - 1)

        after = snapshot(keyed_client, sid)
        assert after == before
        assert made not in [sid_ for sid_, _ in after]
    finally:
        stop_quietly(keyed_client, sid)


def test_discard_puts_back_a_step_that_was_deleted(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**`restore_step` 의 둘째 경우가 실제 경로에서 쓰이는 자리다.**

    "이 Step 은 필요 없다" 는 정당한 수정이고, 지워진 Step 은 교체로 돌아오지 않는다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        before = snapshot(keyed_client, sid)
        assert keyed_client.delete(f"/api/sessions/{sid}/steps/{target}").status_code == 200
        assert target not in [s for s, _ in snapshot(keyed_client, sid)]

        resp = keyed_client.post(f"/api/sessions/{sid}/step-edit/discard")
        assert resp.status_code == 200, resp.text

        assert snapshot(keyed_client, sid) == before, "지워진 대상이 원래 자리로 돌아와야 한다"
    finally:
        stop_quietly(keyed_client, sid)


def test_discard_does_not_end_the_session(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """버리기는 세션을 끝내지 않는다 (FR-026). 끝내는 조작은 기존 「중지」다.

    이 기능의 값은 시행착오 루프에 있고, 버릴 때마다 세션이 사라지면 그 루프가
    성립하지 않는다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[-1])
    assert isinstance(sid, str)
    try:
        assert keyed_client.post(f"/api/sessions/{sid}/step-edit/discard").status_code == 200
        view = wait_for_index(keyed_client, sid, len(saved) - 1)
        assert view["state"] == "paused", "세션이 살아 있어야 한다"
        assert view["step_edit"] is None
    finally:
        stop_quietly(keyed_client, sid)


# ─── 확정되지 않은 수정은 디스크에 닿지 않는다 (FR-024) ─────────────────────


def test_an_unsettled_edit_never_reaches_the_disk(
    keyed_client: TestClient, fixture_app: str
) -> None:
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]
    before = keyed_client.get(f"/api/tests/{test_id}").json()["steps"]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        relabel(keyed_client, sid, target, "고친 이름")
        assert keyed_client.get(f"/api/tests/{test_id}").json()["steps"] == before, (
            "확정하지 않은 수정이 디스크에 내려갔다"
        )
    finally:
        stop_quietly(keyed_client, sid)
