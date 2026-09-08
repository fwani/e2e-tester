"""중첩 구조 요소의 후보 수집 (SC-008 회귀).

**결함**: 리코더가 이벤트의 `target` — 사람이 누른 **가장 깊은 노드** — 를 그대로
기록했다. 앱은 버튼을 `div > div > button > span` 이나 `button > svg > path` 처럼
여러 겹으로 만들기 때문에, 기록된 요소는 `span`·`svg`·`path` 였다.

그 결과 두 가지를 동시에 잃었다.

1. **최우선 후보인 `role`+접근 이름이 사라진다** (FR-018). `span`·`path` 에는 암시적
   role 이 없다. 아이콘만 있는 버튼은 텍스트도 없으므로 남는 후보가 CSS 하나뿐이었다.
2. **그 CSS 가 깊이 상한(6)에 걸려 상대 경로가 됐다.** `main > section > div > div >
   button > span` 은 문서 어디에나 맞으므로 여러 요소를 매칭하고 `ambiguous` 로 버려졌다.

둘이 겹치면 **확보 후보가 0개인 Step** 이 저장된다. 녹화 중에는 클릭이 정상으로 보이므로
사용자는 재실행에서 "요소를 찾지 못했다" 를 볼 때까지 알 수 없었다.

그래서 이 검증은 **녹화만 하지 않는다.** 녹화한 정의를 그대로 재실행해서 모든 Step 이
통과하는지 본다 — 사용자가 실제로 겪은 것이 그 실행이기 때문이다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, stop_quietly

from tests.step_wait import wait_for_steps

CASES: tuple[tuple[str, str], ...] = (
    ("[data-case=span-in-button] .lbl", "button"),
    ("[data-case=svg-in-button] svg path", "button"),
    ("[data-case=span-in-anchor] span", "a"),
    ("[data-case=span-in-role-button] span", "div"),
    ("[data-case=icon-only] svg path:nth-of-type(1)", "button"),
)
"""(클릭이 닿는 깊은 노드, 기록돼야 하는 조작 주체의 태그)."""


def _usable(candidate: dict[str, Any] | None) -> bool:
    """실행이 쓸 수 있는 후보인가. `verified` 만 쓸 수 있다 (원칙 IV)."""
    return bool(candidate) and candidate.get("status") == "verified"


def _usable_count(target: dict[str, Any]) -> int:
    count = sum(
        1 for key in ("test_id", "label", "text", "css") if _usable(target.get(key))
    )
    if target.get("role") and target.get("accessible_name"):
        count += target.get("role_status") == "verified"
    count += _usable(target.get("stable_attr"))
    return count


@pytest.mark.usefixtures("fixture_app")
def test_click_on_nested_node_records_the_actionable_element(
    project_client: TestClient, fixture_app: str
) -> None:
    """깊은 노드를 눌러도 조작 주체(button·a·[role=button])가 기록된다."""
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/nested.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            for selector, _ in CASES:
                await p.click(selector)
                await asyncio.sleep(0.25)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(
            project_client,
            sid,
            lambda s: len([x for x in s if x["type"] == "click"]) >= len(CASES),
        )
    finally:
        stop_quietly(project_client, sid)

    clicks = [s for s in steps if s["type"] == "click"]
    assert len(clicks) >= len(CASES), f"클릭 Step 이 부족하다: {[s['label'] for s in steps]}"

    weak: list[str] = []
    for step, (selector, expected_tag) in zip(clicks, CASES, strict=False):
        target = step["target"]
        if target.get("tag") != expected_tag:
            weak.append(
                f"{selector}: 조작 주체가 아니라 {target.get('tag')!r} 가 기록됐다"
            )
        if _usable_count(target) < 1:
            weak.append(f"{selector}: 확보 후보 0개 — 재실행이 반드시 실패한다 ({target})")
    assert not weak, "중첩 구조에서 잘못된 요소가 기록됐다: " + "; ".join(weak)


@pytest.mark.usefixtures("fixture_app")
def test_nested_targets_keep_the_role_candidate(
    project_client: TestClient, fixture_app: str
) -> None:
    """중첩 구조에서도 `role`+접근 이름 후보를 확보한다 (FR-018 최우선 후보).

    후보 개수만 보면 CSS 하나로도 통과한다. 그 CSS 는 위치 경로이므로 화면 구조가
    바뀌면 깨진다 — 결함이 다시 들어와도 개수만으로는 드러나지 않는다. 그래서 **어느
    후보인지**를 본다.
    """
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/nested.html"},
    )
    sid = created.json()["session_id"]
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            # 아이콘만 있는 버튼. 이전 코드에서는 `path` 가 기록되어 role·text 가 모두
            # 없었고, 같은 구조가 두 벌이라 CSS 도 모호해져 후보가 0개였다.
            await p.click("[data-case=icon-only] svg path:nth-of-type(1)")

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(
            project_client, sid, lambda s: any(x["type"] == "click" for x in s)
        )
    finally:
        stop_quietly(project_client, sid)

    target = [s for s in steps if s["type"] == "click"][-1]["target"]
    assert target["role"] == "button" and target["role_status"] == "verified", (
        f"아이콘 버튼의 role 후보를 확보하지 못했다: {target}"
    )
    assert target["accessible_name"] == "첫 닫기", (
        f"접근 이름이 조작 주체의 것이 아니다: {target}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_nested_targets_replay_without_element_not_found(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """중첩 구조를 녹화한 정의가 **끝까지 재실행된다.**

    사용자가 겪은 것은 녹화 화면이 아니라 이 실행이다. 후보 개수만 재면 "확보했다고 적힌
    후보가 실제로는 다른 요소를 잡는" 경우를 놓치므로, 실행 결과로 확인한다.
    """
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/nested.html"},
    )
    sid = created.json()["session_id"]
    try:
        page = keyed_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            for selector, _ in CASES:
                await p.click(selector)
                await asyncio.sleep(0.25)

        keyed_client.portal.call(act)  # type: ignore[attr-defined]
        wait_for_steps(
            keyed_client,
            sid,
            lambda s: len([x for x in s if x["type"] == "click"]) >= len(CASES),
        )
        saved = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "중첩 구조"})
        assert saved.status_code == 200, saved.text
        test_id = str(saved.json()["id"])
    finally:
        stop_quietly(keyed_client, sid)

    view = replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    failed = [s for s in result["steps"] if s["outcome"] != "pass"]
    assert view["state"] == "completed" and result["outcome"] == "pass", (
        "중첩 구조로 만든 버튼의 Step 이 재실행에서 실패했다: "
        f"{[(s['step_id'], s.get('failure', {}).get('message')) for s in failed]}"
    )
