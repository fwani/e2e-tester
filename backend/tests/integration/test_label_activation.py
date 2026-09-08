"""레이블 활성화가 만드는 중복 (FR-025 계열, TC-009 step 20·21 회귀).

`<label for>` 을 누르면 브라우저가 연결된 컨트롤에 **클릭을 한 번 더 합성해 보낸다.** 두
이벤트의 대상이 다르므로 요소별 중복 제거로는 접히지 않고, 한 번의 클릭이 Step 두 개가
된다.

**정의가 길어지는 문제가 아니다.** 실측(TC-009)에서 그 두 Step 은 재실행에서 체크박스를
켰다가 **다시 껐다** — 뜻이 뒤집힌다. 게다가 두 번째 Step 의 대상인 실제
`<input class="checkbox-input">` 은 `<button class="accordion-head">` 에 덮여 있어 요소를
찾고도 10초를 쓰고 실패했다.

그래서 남겨야 하는 쪽은 **포인터가 실제로 닿은 쪽**이다. "레이블 대신 컨트롤을 기록" 으로
접으면 가려진 쪽을 골라 매번 실패한다 — 이 검증의 픽스처가 그 조건을 갖추고 있다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, stop_quietly

from tests.step_wait import has_kinds, wait_for_steps


def _record_two_filters(client: TestClient, fixture_app: str) -> tuple[str, list[dict[str, Any]]]:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/label-checkbox.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.click("label[for=filter-druid]")
            await asyncio.sleep(0.9)  # CLICK_DEDUPE_MS(700) 보다 길게 — 다음 클릭이 접히지 않게
            await p.click("label[for=filter-elastic]")
            await asyncio.sleep(0.5)

        client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(client, sid, has_kinds("click"))
        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "필터 두 개"})
        assert saved.status_code == 200, saved.text
        return str(saved.json()["id"]), steps
    finally:
        stop_quietly(client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_one_click_on_a_label_makes_one_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """레이블 클릭 한 번이 Step 한 개가 된다."""
    _, steps = _record_two_filters(keyed_client, fixture_app)
    clicks = [s for s in steps if s["type"] == "click"]
    assert len(clicks) == 2, (
        "클릭 두 번이 Step 두 개가 아니다 — 레이블 활성화의 합성 클릭이 접히지 않았다: "
        f"{[(s['label'], (s['target'].get('css') or {}).get('value')) for s in clicks]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_the_step_targets_what_the_pointer_touched(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """남는 것은 **보이는 쪽**(레이블)이다.

    가려진 `<input>` 을 골라 접으면 개수는 맞지만 재실행이 매번 실패한다. 개수만 재는
    검증으로는 그 해법을 걸러 내지 못하므로 어느 요소인지 본다.
    """
    _, steps = _record_two_filters(keyed_client, fixture_app)
    clicks = [s for s in steps if s["type"] == "click"]
    tags = [s["target"].get("tag") for s in clicks]
    assert tags == ["label", "label"], (
        f"포인터가 닿지 않은 요소가 기록됐다: {tags}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_replay_leaves_both_filters_on(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """재실행이 두 필터를 **켠 상태로** 끝낸다.

    중복이 남아 있으면 같은 체크박스를 두 번 눌러 원래대로 돌아가거나(뜻이 뒤집힘), 가려진
    `<input>` 을 누르려다 시간 초과로 실패한다. 화면의 결과 문구로 그것을 잡는다.
    """
    test_id, _ = _record_two_filters(keyed_client, fixture_app)

    view = replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    failed = [s for s in result["steps"] if s["outcome"] != "pass"]
    detail = [
        (s["step_id"], s.get("error_code"), (s.get("error_message") or "")[:120])
        for s in failed
    ]
    assert view["state"] == "completed" and result["outcome"] == "pass", (
        f"재실행이 실패했다: {detail}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_a_click_is_not_followed_by_a_hover_step_on_the_same_element(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """클릭 뒤에 같은 요소의 hover Step 이 붙지 않는다 (TC-011 step-14 회귀).

    **순서가 뒤집힌 같은 문제다.** `hover → click` 은 클릭이 hover 를 갈아 끼워 접히지만
    (`test_hover_then_click_on_the_same_element_is_one_step`), 실제 앱에서는 반대 순서가
    나온다 — 필터를 고르면 화면이 다시 그려지고, 포인터 밑 노드가 교체되면서 **새
    `pointerover`** 가 발생한다. 그 직후의 화면 변화가 hover 의 효과로 오인돼 Step 이 된다.

    실측(TC-011): `클릭 즐겨찾기(label)` 뒤에 `hover 즐겨찾기(input)` 가 붙었고, 재실행은
    `<button class="accordion-head">` 에 덮인 그 input 을 hover 하려다 10초를 쓰고 실패했다.

    `click()` 이 이미 포인터를 그 자리로 옮기므로 hover Step 이 더할 것이 없다.
    """
    _, steps = _record_two_filters(keyed_client, fixture_app)

    kinds = [(s["type"], s["target"].get("accessible_name")) for s in steps]
    hovers = [name for kind, name in kinds if kind == "hover"]
    clicked = {name for kind, name in kinds if kind == "click"}
    overlap = [name for name in hovers if name in clicked]
    assert not overlap, (
        f"클릭한 요소의 hover 가 Step 으로 남았다: {overlap} (전체 {kinds})"
    )


@pytest.mark.usefixtures("fixture_app")
def test_clicking_the_box_and_the_name_record_the_same_element(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """체크박스는 **네모를 눌러도 이름을 눌러도 같게 기록된다** (TC-013 회귀).

    둘은 같은 조작이다. 그런데 눌린 요소를 그대로 기록하면 누른 자리에 따라 정의가
    달라진다 — 실측(TC-013)에서 `즐겨찾기` 를 이름으로 누른 Step 12 는 `label` 로, 네모로
    누른 Step 16 은 `input` 으로 기록됐고 **16 만 재실행에서 실패했다**(실제 `input` 이
    `<button class="accordion-head">` 에 덮여 있었다).

    그래서 짝 중 **그 자리를 실제로 받을 수 있는 쪽**으로 통일한다.
    """
    tags: dict[str, str | None] = {}
    for what, selector in (("네모", "#filter-druid"), ("이름", "label[for=filter-druid]")):
        created = keyed_client.post(
            "/api/sessions",
            json={"mode": "record", "start_url": f"{fixture_app}/label-checkbox.html"},
        )
        sid = created.json()["session_id"]
        try:
            page = keyed_client.app.state.itb.sessions.require(sid).tabs[0].page

            async def act(p: Any = page, sel: str = selector) -> None:
                await p.click(sel)
                await asyncio.sleep(0.5)

            keyed_client.portal.call(act)  # type: ignore[attr-defined]
            steps = wait_for_steps(keyed_client, sid, has_kinds("click"))
        finally:
            stop_quietly(keyed_client, sid)
        clicks = [s for s in steps if s["type"] == "click"]
        assert clicks, f"{what} 클릭이 기록되지 않았다"
        tags[what] = clicks[-1]["target"].get("tag")

    assert tags["네모"] == tags["이름"] == "label", (
        f"누른 자리에 따라 다르게 기록됐다: {tags}"
    )
