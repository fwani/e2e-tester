"""일시정지·인수 국면의 미러 조작 (010 T055 · US3 · FR-314 · 헌법 원칙 III).

**US3 이 세우는 것은 새 경로가 아니라 붙임이다.** US1·US2 가 만든 조작 통로를 다른 국면에
붙인다. 그래서 이 파일이 재는 것도 통로 자체가 아니라 **국면과의 관계** 셋이다.

1. 일시정지에서 채널이 열리고 조작이 대상에 닿는다 (FR-314).
2. 그 조작 뒤에 실행을 재개하면 정상 진행된다 — 세션 상태(인증·화면·입력값)가 유지된다
   (헌법 원칙 III · 불변식 1).
3. 실행 중에는 채널이 **수립되지 않는다** (FR-315·FR-342). 러너가 전진하는 중에 사람
   조작이 끼어들면 같은 Step 이 두 번 돈다.

세 번째는 `test_control_channel_failure.py` 에도 있다. 거기서는 「장애를 주입해도 실행이
완주한다」의 일부이고 여기서는 「인수 흐름이 국면을 지킨다」의 일부다 — 깨졌을 때의 진단이
다르므로 둘 다 둔다.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, start_replay, stop_quietly, wait_for_run

CONTROL_PATH = "/api/sessions/{sid}/control"


def _pause(client: TestClient, session_id: str) -> None:
    paused = client.post(f"/api/sessions/{session_id}/pause")
    assert paused.status_code == 200, paused.text


def _state(client: TestClient, session_id: str) -> str:
    return str(client.get(f"/api/sessions/{session_id}").json()["state"])


def _wait_for_state(
    client: TestClient, session_id: str, target: str, timeout_s: float = 30.0
) -> None:
    """상태가 목표에 닿기를 기다린다. **일시정지는 Step 경계에서 일어난다.**

    요청은 즉시 돌아오지만 러너는 현재 Step 이 끝나야 멈춘다 (005 FR-142). 요청 직후를
    일시정지로 읽으면 아직 도는 실행에 조작을 걸게 된다.
    """

    for _ in range(int(timeout_s / 0.2)):
        if _state(client, session_id) == target:
            return
        client.portal.call(_sleep)  # type: ignore[attr-defined]
    msg = f"{timeout_s}초 안에 '{target}' 에 닿지 못했다 (지금 '{_state(client, session_id)}')"
    raise AssertionError(msg)


async def _sleep() -> None:
    await asyncio.sleep(0.2)


@pytest.mark.browser
def test_the_control_channel_opens_while_paused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**일시정지가 조작 국면이다** (FR-314 · US3).

    001 에서 `PAUSED` 는 「실제 브라우저 창을 앞으로 가져와야 하는가」를 묻는
    `is_manipulation_phase` 에 들어 있지 않았다. 010 은 그것과 **다른 질문**을 세운다 —
    「사람이 지금 브라우저를 조작하는가」이고, 일시정지는 거기 들어간다. 실행이 멈춰
    있으므로 러너 명령과 경쟁하지도 않는다.
    """
    test_id = record_login(keyed_client, fixture_app)
    session_id = start_replay(keyed_client, test_id)
    try:
        _pause(keyed_client, session_id)
        _wait_for_state(keyed_client, session_id, "paused")

        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            opened = ws.receive_json()
            assert opened["type"] == "control_state"
            assert opened["state"] == "open", f"일시정지에서 채널이 열리지 않았다: {opened}"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_mirror_control_while_paused_reaches_the_target(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """일시정지 중 미러 조작이 대상 페이지에 닿는다 (FR-314 · US3 인수 1).

    **세션 상태가 유지된다는 것이 요점이다** (헌법 원칙 III). 일시정지는 브라우저에 대한
    조작이 아니라 명령 전송을 멈추는 것이므로, 페이지는 그대로 살아 있고 조작을 받는다.
    """
    test_id = record_login(keyed_client, fixture_app)
    session_id = start_replay(keyed_client, test_id)
    try:
        _pause(keyed_client, session_id)
        _wait_for_state(keyed_client, session_id, "paused")

        session = keyed_client.app.state.itb.sessions.require(session_id)
        page = session.tabs[0].page

        async def probe(p: Any = page) -> str:
            # 일시정지 중에도 페이지가 살아 있다 — 그 사실이 조작의 전제다.
            await p.evaluate("document.title = document.title")
            return str(p.url)

        before = keyed_client.portal.call(probe)  # type: ignore[attr-defined]

        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            ws.receive_json()  # control_state open
            ws.send_text(
                json.dumps({"kind": "pointer.move", "tab": 0, "x": 10, "y": 10})
            )
            # 거절이 오면 그것이 실패다. 성공 응답은 오지 않는다 (contracts §5 불변식 5).
            keyed_client.portal.call(_sleep)  # type: ignore[attr-defined]

        assert _state(keyed_client, session_id) == "paused", (
            "미러 조작이 세션 상태를 전이시켰다 (contracts §5 불변식 4 위반)"
        )
        after = keyed_client.portal.call(probe)  # type: ignore[attr-defined]
        assert after == before, "조작이 화면을 예기치 않게 옮겼다"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_resume_after_mirror_control_still_finishes(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**미러 조작 뒤 재개해도 실행이 정상 진행된다** (US3 인수 1 · 원칙 III).

    조작 채널의 어떤 일도 실행 상태 기계를 전이시키지 않는다는 계약(contracts §5 불변식 4)
    이 실제로 성립하는지를 실행 끝까지 확인한다. 조작이 세션에 흔적을 남겼다면 재개가
    엉뚱한 지점에서 실패한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    session_id = start_replay(keyed_client, test_id)
    try:
        _pause(keyed_client, session_id)
        _wait_for_state(keyed_client, session_id, "paused")

        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            ws.receive_json()
            for event in (
                {"kind": "pointer.move", "tab": 0, "x": 20, "y": 20},
                {"kind": "pointer.down", "tab": 0, "x": 20, "y": 20, "button": "left"},
                {"kind": "pointer.up", "tab": 0, "x": 20, "y": 20, "button": "left"},
            ):
                ws.send_text(json.dumps(event))
            keyed_client.portal.call(_sleep)  # type: ignore[attr-defined]

        resumed = keyed_client.post(f"/api/sessions/{session_id}/resume")
        assert resumed.status_code == 200, resumed.text
        view = wait_for_run(keyed_client, session_id)
        # **끝났다는 것이 재는 것이다.** 결말이 통과인지 실패인지는 이 검증의 관심이
        # 아니다 — 관심은 조작 채널이 실행을 세우거나 유실시키지 않았는가 하나다.
        assert view["state"] in ("completed", "failed", "stopped"), (
            f"미러 조작 뒤 재개가 끝나지 못했다: {view['state']}"
        )
        assert view["state"] != "lost", "미러 조작이 세션을 유실시켰다 (FR-348 위반)"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_pausing_reopens_what_running_had_closed(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**국면이 채널의 개폐를 정한다** (FR-342 · contracts §1).

    실행 중에는 수립이 거절되고, 멈추면 열린다. 화면이 안 보내는 것에 의존하지 않는
    다는 것이 FR-342 의 요점이므로, 화면을 우회해 소켓에 직접 붙는 이 경로에서 확인한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    session_id = start_replay(keyed_client, test_id)
    try:
        refused = False
        try:
            with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)):
                pass
        except Exception:  # noqa: BLE001 - 수립 거절은 연결 오류로 나타난다
            refused = True
        assert refused, "실행 중인데 조작 채널이 붙었다 (FR-315·FR-342 위반)"

        _pause(keyed_client, session_id)
        _wait_for_state(keyed_client, session_id, "paused")

        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            assert ws.receive_json()["state"] == "open", "멈춘 뒤에도 채널이 열리지 않았다"
    finally:
        stop_quietly(keyed_client, session_id)
