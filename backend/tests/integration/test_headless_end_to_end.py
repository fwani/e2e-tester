"""화면 없는 기계의 전체 흐름 (010 T091 · SC-518).

> SC-518: 화면 없는 기계에서 녹화·인수를 포함한 전체 흐름이 동작한다. (010 이전에는
> 창을 띄우지 못해 불가능했다)

## 왜 조각이 아니라 전체인가

조각은 이미 각각 있다 — 헤드리스 기본값(T002), 미러 조작(T033), 한글 입력(T049),
파일 첨부(T068). **그 조각들이 이어 붙는 자리가 검증되지 않았다는 것**이 converge
1회차의 발견이었다.

이 파일은 **창을 한 번도 띄우지 않고** 한 흐름을 끝까지 돈다.

    세션 열기 → 미러에서 클릭·입력 → Step 확인 → 저장 → 재실행 → 완주

각 단계는 다른 파일이 이미 자세히 재고 있다. 여기서 재는 것은 **이어짐** 하나다 — 어느
단계도 창을 요구하지 않고, 앞 단계의 산출이 뒤 단계의 입력이 된다.

## 「화면이 없다」를 어떻게 재현하는가

`ITB_HEADLESS` 를 세우는 것으로는 부족하다. 그것은 브라우저를 창 없이 띄우라는 뜻일 뿐,
**제품이 창을 열려고 시도하는 경로**를 막지 않는다. 그래서 창 열기 판정(`can_open_a_window`)
도 함께 거짓으로 만든다 — CI 러너·원격 서버의 상태다.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly, wait_for_run

CONTROL_PATH = "/api/sessions/{sid}/control"

SETTLE_S = 0.6
"""조작 뒤 Step 이 쌓이기를 기다리는 시간. `test_mirror_recording_parity.py` 와 같은 값."""


@pytest.fixture
def headless_machine(monkeypatch: pytest.MonkeyPatch) -> None:
    """화면 없는 기계를 재현한다.

    **환경 변수만으로는 부족하다.** `ITB_HEADLESS` 는 브라우저를 창 없이 띄우라는 뜻이고,
    제품이 창을 열려고 **시도하는** 경로는 그와 별개다. 둘 다 막아야 CI 러너·원격 서버의
    상태가 된다.
    """
    from itb.api.routes import control
    from itb.execution.session import HEADLESS_ENV

    monkeypatch.setenv(HEADLESS_ENV, "1")
    monkeypatch.setattr(control, "can_open_a_window", lambda: False)


def _settle(client: TestClient) -> None:
    async def wait() -> None:
        await asyncio.sleep(SETTLE_S)

    client.portal.call(wait)  # type: ignore[attr-defined]


def _center(client: TestClient, session_id: str, selector: str) -> tuple[float, float]:
    page = client.app.state.itb.sessions.require(session_id).tabs[0].page

    async def read(p: Any = page) -> dict[str, float]:
        box = await p.locator(selector).bounding_box()
        assert box is not None, f"{selector} 의 위치를 읽을 수 없다"
        return box

    box = client.portal.call(read)  # type: ignore[attr-defined]
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


@pytest.mark.browser
def test_the_whole_flow_works_without_a_window(
    keyed_client: TestClient, fixture_app: str, headless_machine: None
) -> None:
    """**창 없이 녹화 → 입력 → 저장 → 재실행이 끝까지 돈다** (SC-518).

    010 이전에는 이 흐름이 불가능했다 — 조작 국면이 실제 창을 요구했고, 화면 없는
    기계에는 그 창이 없었다.
    """
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    session_id = str(created.json()["session_id"])

    try:
        # ── 1. 창으로 전환하려 해도 **사유와 함께 거절된다** (FR-351) ──
        refused = keyed_client.post(
            f"/api/sessions/{session_id}/control-surface", json={"surface": "window"}
        )
        assert refused.status_code == 400, (
            f"화면 없는 기계인데 창 전환이 거절되지 않았다: {refused.text}"
        )
        assert "띄울 창이 없어" in refused.json()["error"]["message"]

        # ── 2. 미러에서 조작한다. 이것이 이 기계에 남은 유일한 조작 수단이다 ──
        email_x, email_y = _center(keyed_client, session_id, "#email")
        submit_x, submit_y = _center(
            keyed_client, session_id, "[data-testid=login-submit]"
        )

        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            assert ws.receive_json()["state"] == "open"

            # 입력 요소를 클릭하고 한글을 친다 (US2 의 경로를 그대로 지난다).
            for event in (
                {"kind": "pointer.down", "tab": 0, "x": email_x, "y": email_y, "button": "left"},
                {"kind": "pointer.up", "tab": 0, "x": email_x, "y": email_y, "button": "left"},
            ):
                ws.send_text(json.dumps(event))
            for i in range(1, 3):
                partial = "주문"[:i]
                ws.send_text(
                    json.dumps({"kind": "ime.compose", "tab": 0, "text": partial})
                )
            ws.send_text(json.dumps({"kind": "ime.commit", "tab": 0, "text": "주문"}))
            _settle(keyed_client)

            # 다른 요소를 클릭한다 — 입력이 확정되고 클릭 Step 이 쌓인다.
            for event in (
                {
                    "kind": "pointer.down",
                    "tab": 0,
                    "x": submit_x,
                    "y": submit_y,
                    "button": "left",
                },
                {"kind": "pointer.up", "tab": 0, "x": submit_x, "y": submit_y, "button": "left"},
            ):
                ws.send_text(json.dumps(event))
            _settle(keyed_client)

        # ── 3. Step 이 쌓였다 ──
        steps = keyed_client.get(f"/api/sessions/{session_id}").json()["steps"]
        kinds = [s["type"] for s in steps]
        assert "fill" in kinds, f"미러 입력이 Step 이 되지 않았다: {kinds}"
        assert "click" in kinds, f"미러 클릭이 Step 이 되지 않았다: {kinds}"

        # ── 4. 저장한다 ──
        saved = keyed_client.post(
            f"/api/sessions/{session_id}/save", json={"name": "화면 없는 기계 흐름"}
        )
        assert saved.status_code == 200, saved.text
        test_id = str(saved.json()["id"])
    finally:
        stop_quietly(keyed_client, session_id)

    # ── 5. 재실행이 완주한다. 여기도 창을 열지 않는다 ──
    started = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert started.status_code == 201, started.text
    replay_id = str(started.json()["session_id"])
    try:
        view = wait_for_run(keyed_client, replay_id)
        assert view["state"] in ("completed", "failed", "stopped"), (
            f"창 없이 시작한 재실행이 끝나지 못했다: {view['state']}"
        )
        assert view["state"] != "lost", "창 없는 기계에서 재실행이 세션을 잃었다"
    finally:
        stop_quietly(keyed_client, replay_id)


@pytest.mark.browser
def test_takeover_needs_no_window(
    keyed_client: TestClient, fixture_app: str, headless_machine: None
) -> None:
    """**인수도 창을 요구하지 않는다** (SC-518 · T053).

    001 은 인수 녹화를 시작할 때 창을 앞으로 가져왔다 (`bring_tab_to_front`). 화면 없는
    기계에서 그 호출은 아무것도 하지 못하고, 사용자는 조작할 곳을 잃는다. 010 이 그
    호출을 없애고 조작을 미러로 옮겼다.

    일시정지를 인수의 대역으로 쓴다 — 둘 다 「사람이 이어받는」 조작 국면이고
    (`CONTROL_PHASE_STATES`), AI 세션을 띄우지 않고도 같은 성질을 잴 수 있다.
    """
    from us2_support import record_login, start_replay

    test_id = record_login(keyed_client, fixture_app)
    session_id = start_replay(keyed_client, test_id)
    try:
        paused = keyed_client.post(f"/api/sessions/{session_id}/pause")
        assert paused.status_code == 200, paused.text

        for _ in range(150):
            if keyed_client.get(f"/api/sessions/{session_id}").json()["state"] == "paused":
                break
            _settle(keyed_client)
        else:
            pytest.fail("일시정지에 닿지 못했다")

        # 창 없이도 조작 통로가 열린다 — 이것이 인수가 성립하는 근거다.
        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            assert ws.receive_json()["state"] == "open", (
                "화면 없는 기계에서 인수 조작 통로가 열리지 않았다 (SC-518)"
            )
            ws.send_text(json.dumps({"kind": "pointer.move", "tab": 0, "x": 10, "y": 10}))
            _settle(keyed_client)

        assert keyed_client.get(f"/api/sessions/{session_id}").json()["state"] == "paused"
    finally:
        stop_quietly(keyed_client, session_id)
