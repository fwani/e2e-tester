"""**확정하면 저장되고, 저장하면 디스크에 새 Step 이 있다** (2026-09-11 사용자 보고).

## 보고된 것

> 「ai 로 변경한 내용(추가,변경) 저장도 안돼. 저장되게 해라」

## 무엇이 그렇게 보였나

서버는 확정되지 않은 교체의 저장을 거절한다 (FR-029 · `sessions.py` 의 `save`). 그 자체는
옳다 — 「옛 구간 + 새 Step」이 함께 있는 중간 상태가 자산이 되면 되돌릴 길이 손편집뿐이다.
그런데 화면에서는 둘이 겹쳤다: 확정 버튼이 있는 재녹화 띠가 Step 목록 머리에 짓눌려
보이지 않았고, 저장 버튼은 활성으로 보이다가 눌러야 거절됐다. 사용자에게는 「저장이 안
된다」가 전부였다.

## 이 파일이 재는 것

화면은 프론트 검사가 본다 (`RerecordBandPlacement.test.tsx`). 여기서는 **서버의 길이 실제로
디스크까지 닿는지**를 본다 — 016 의 어느 검사도 확정 뒤 `save` 를 눌러 파일을 읽어 보지
않았다. `test_commit_and_discard` 는 세션 목록까지만 봤다.

1. 확정 전 저장은 거절되고, 거절이 **다음 걸음**(확정·버리기)을 말한다
2. 확정 뒤 저장은 성공한다
3. 저장된 정의에 새 Step 이 있고 옛 구간이 없다 — 세션이 보여 준 목록과 **같다**

새 Step 은 사람 조작(`steps:manual`)으로 만든다 — `test_commit_and_discard` 와 같은 이유로,
여기서 보는 것은 저장이지 AI 가 아니다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us_rerecord.support import open_rerecord, saved_step_ids, step_ids

pytestmark = pytest.mark.browser


def insert_manual(client: TestClient, sid: str, url: str, at: int) -> str:
    resp = client.post(
        f"/api/sessions/{sid}/steps:manual",
        json={"spec": {"kind": "navigate", "url": url}, "at": at},
    )
    assert resp.status_code == 200, resp.text
    return str(resp.json()["steps"][at]["id"])


def test_commit_then_save_writes_the_new_steps_to_disk(
    keyed_client: TestClient, fixture_app: str
) -> None:
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    before = saved_step_ids(keyed_client, test_id)
    victim = before[-2:]
    name = keyed_client.get(f"/api/tests/{test_id}").json()["name"]

    sid = open_rerecord(keyed_client, test_id, victim)
    assert isinstance(sid, str)
    try:
        at = len(before) - 2
        made = insert_manual(keyed_client, sid, f"{fixture_app}/projects.html", at)

        # (1) 확정 전 — 거절하고 **다음 걸음을 말한다.** 거절만 하면 사용자는 갇힌다.
        refused = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": name})
        assert refused.status_code == 409, refused.text
        next_action = refused.json()["error"].get("next_action", "")
        assert "확정" in next_action and "버리기" in next_action, refused.json()
        assert saved_step_ids(keyed_client, test_id) == before, (
            "거절했는데 디스크가 바뀌었다 — FR-029 위반"
        )

        # (2) 확정 → 저장.
        committed = keyed_client.post(f"/api/sessions/{sid}/rerecord/commit")
        assert committed.status_code == 200, committed.text
        saved = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": name})
        assert saved.status_code == 200, saved.text

        # (3) 디스크의 정의 == 세션이 보여 준 목록. 새 Step 이 있고 옛 구간이 없다.
        on_disk = saved_step_ids(keyed_client, test_id)
        assert on_disk == step_ids(keyed_client, sid), "저장된 것과 화면의 목록이 다르다"
        assert made in on_disk, "새로 만든 Step 이 저장되지 않았다"
        for old in victim:
            assert old not in on_disk, f"옛 구간이 저장에 남았다: {old}"
        assert on_disk == [*before[:at], made]

        # 저장 뒤 세션은 「저장하지 않은 변경 없음」이다 — 다시 저장을 재촉하지 않는다.
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["has_unsaved_changes"] is False, view
    finally:
        stop_quietly(keyed_client, sid)
