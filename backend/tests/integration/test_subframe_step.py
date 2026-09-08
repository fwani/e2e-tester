"""하위 프레임(iframe) 안의 동작 (001 research 의 iframe 항목).

**결함**: 리코더가 `expose_binding` 의 `source["frame"]` 을 버리고 `source["page"]` 만
썼다. 주입 스크립트는 모든 프레임에서 돌기 때문에, iframe 안의 클릭도 기록되지만 후보는
**그 프레임의 문서 기준**으로 측정된다. 그것을 main frame 기준으로 검증하면

- `role`·`text` 후보는 main frame 에서 찾지 못하므로 전부 미수집으로 깎이고,
- 주입 스크립트가 프레임 안에서 잰 CSS 만 `verified` 로 남는다.

저장된 Step 은 "확보 후보 1개" 로 멀쩡해 보이지만, 실행이 main frame 을 뒤지므로 그 경로는
0개를 매칭한다. 사용자에게는 예산을 다 쓴 **timeout** 으로만 보이고, 녹화 화면에는 아무
이상이 없었으므로 원인을 짚을 단서가 없다.

001 research 는 "Step 에 프레임 URL 을 함께 기록" 으로 정해 두었고 `Step.frame_url` 필드도
있었지만 **채우는 코드도 읽는 코드도 없었다.** 이 검증이 그 결정을 잠근다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, stop_quietly

from tests.step_wait import has_kinds, wait_for_steps


def _record_in_frame(client: TestClient, fixture_app: str) -> tuple[str, list[dict[str, Any]]]:
    """iframe 안에서 입력·클릭을 녹화하고 (test_id, steps) 를 돌려준다."""
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/embedded.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            frame = p.frame_locator("iframe")
            await frame.locator("#inner-name").fill("프레임 안")
            await asyncio.sleep(0.25)
            # 껍데기 span 을 누른다 — 조작 주체(button)까지 올라가는지도 함께 본다.
            await frame.locator("button.btn .lbl").click()
            await asyncio.sleep(0.4)

        client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(client, sid, has_kinds("fill", "click"))
        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "내장 앱"})
        assert saved.status_code == 200, saved.text
        return str(saved.json()["id"]), steps
    finally:
        stop_quietly(client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_subframe_steps_record_the_frame_url(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """하위 프레임에서 온 Step 은 `frame_url` 을 든다.

    이 값이 없으면 실행이 어느 문서를 뒤져야 하는지 알 방법이 없다.
    """
    _, steps = _record_in_frame(keyed_client, fixture_app)
    acted = [s for s in steps if s["type"] in ("fill", "click")]
    assert acted, f"프레임 안의 동작이 기록되지 않았다: {[s['type'] for s in steps]}"

    missing = [s["id"] for s in acted if not s.get("frame_url")]
    assert not missing, (
        f"하위 프레임에서 기록됐는데 frame_url 이 비어 있다: {missing}. "
        "실행은 main frame 을 뒤지게 되고 그 Step 은 반드시 timeout 된다."
    )
    assert all("embedded-inner.html" in s["frame_url"] for s in acted), (
        f"frame_url 이 내장 문서를 가리키지 않는다: {[s.get('frame_url') for s in acted]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_subframe_candidates_are_verified_in_that_frame(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """프레임 안에서 검증하므로 `role`·`label` 후보가 살아남는다.

    후보 개수만 보면 CSS 하나로도 통과한다. 이전 결함에서 남은 후보가 정확히 그 CSS
    하나였으므로, **어느 후보인지**를 본다.
    """
    _, steps = _record_in_frame(keyed_client, fixture_app)

    clicks = [s for s in steps if s["type"] == "click"]
    assert clicks, "프레임 안의 클릭이 기록되지 않았다"
    target = clicks[-1]["target"]
    assert target["tag"] == "button", f"조작 주체가 아니라 {target['tag']!r} 가 기록됐다"
    assert target["role"] == "button" and target["role_status"] == "verified", (
        f"프레임 안에서 검증하지 못해 role 후보를 잃었다: {target}"
    )

    fills = [s for s in steps if s["type"] == "fill"]
    assert fills, "프레임 안의 입력이 기록되지 않았다"
    label = fills[-1]["target"].get("label")
    assert label and label["status"] == "verified", (
        f"프레임 안에서 검증하지 못해 label 후보를 잃었다: {fills[-1]['target']}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_subframe_test_replays(keyed_client: TestClient, fixture_app: str) -> None:
    """iframe 안에서 녹화한 정의가 **끝까지 재실행된다.**

    사용자가 겪은 것은 이 실행이다. 후보 상태만 재면 "적힌 대로 확보됐지만 실행이 다른
    문서를 뒤진다" 는 경우를 놓친다.
    """
    test_id, _ = _record_in_frame(keyed_client, fixture_app)

    view = replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    failed = [s for s in result["steps"] if s["outcome"] != "pass"]
    assert view["state"] == "completed" and result["outcome"] == "pass", (
        "iframe 안의 Step 이 재실행에서 실패했다: "
        f"{[(s['step_id'], s.get('error_code'), s.get('failure')) for s in failed]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_frame_attached_during_recording_also_replays(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**녹화 중에 iframe 이 붙는 경로.** 위의 검증들과 결함이 다르다.

    시작 화면의 iframe 은 `install()` 보다 먼저 로드되므로, 예전에는 주입 스크립트가
    아예 들어가지 않아 **Step 이 하나도 만들어지지 않았다**. 반면 녹화 중에 붙는 iframe
    은 `add_init_script` 가 덮으므로 스크립트가 돈다 — 그때가 더 나쁘다. Step 은 정상으로
    보이지만 후보가 프레임 문서 기준으로만 검증돼 있어서, 실행이 main frame 을 뒤지고
    **timeout** 으로 끝난다. 사용자가 겪은 것이 이쪽이다.
    """
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    try:
        page = keyed_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            # 녹화가 시작된 뒤에 iframe 이 붙는다.
            await p.goto(f"{fixture_app}/embedded.html")
            await asyncio.sleep(0.4)
            await p.frame_locator("iframe").locator("button.btn .lbl").click()
            await asyncio.sleep(0.4)

        keyed_client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(keyed_client, sid, has_kinds("click"))
        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "나중에 붙은 프레임"}
        )
        assert saved.status_code == 200, saved.text
        test_id = str(saved.json()["id"])
    finally:
        stop_quietly(keyed_client, sid)

    clicks = [s for s in steps if s["type"] == "click"]
    assert clicks, "프레임 안의 클릭이 기록되지 않았다"
    assert clicks[-1].get("frame_url"), (
        f"나중에 붙은 프레임의 Step 이 frame_url 을 잃었다: {clicks[-1]}"
    )

    view = replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    failed = [s for s in result["steps"] if s["outcome"] != "pass"]
    assert view["state"] == "completed" and result["outcome"] == "pass", (
        "나중에 붙은 iframe 안의 Step 이 재실행에서 실패했다: "
        f"{[(s['step_id'], s.get('error_code')) for s in failed]}"
    )
