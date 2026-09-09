"""조작 채널 장애 주입 (010 T023 · FR-348 · SC-519 · contracts §5 불변식 4).

**재는 것 하나** — 조작 채널이 어떻게 망가져도 **진행 중인 실행은 완주한다.** 미러
프레임이 끊겨도 실행이 영향받지 않는다는 성질(FR-047b)을 조작 쪽에서 유지하는 것이
FR-348 이고, SC-519 가 그것을 10회 중 10회로 정한다.

장애를 세 가지로 나눈다 — 붙었다 갑자기 끊기, 폭주(쓰레기 사건을 쏟아붓기), 그리고
붙지 못하기. 셋 다 클라이언트 쪽에서 실제로 일어나는 형태다.

**실행 완주를 재는 것이 요점이다.** 조작이 성공했는지는 여기서 재지 않는다 — 그것은
`test_mirror_recording_parity.py` 의 일이다. 여기서 재는 것은 "조작 채널의 사정이 실행을
건드리지 않는다" 하나다.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, stop_quietly

CONTROL_PATH = "/api/sessions/{sid}/control"

FAILURE_RUNS = 10
"""SC-519 가 정한 횟수. **10회 중 10회 완주**해야 한다.

한 번의 성공은 우연일 수 있고, 채널 장애가 실행에 번지는 경로는 대개 경합이라 매번
나타나지 않는다.
"""


GARBAGE = [
    {"kind": "script.eval", "text": "alert(1)"},
    {"kind": "pointer.down", "x": 10**9, "y": -10**9, "button": "left"},
    {"kind": "text.insert", "text": "가" * 100_000},
    {"kind": "pointer.move"},
    {"not": "an event"},
    "문자열",
    42,
]
"""채널이 받아서는 안 되는 것들. **하나도 실행을 건드려서는 안 된다.**

목록에 형이 아예 다른 것(문자열·정수)을 섞은 이유는 검증을 우회하는 경로가 대개 형
가정에서 생기기 때문이다.
"""


def _open_control(client: TestClient, session_id: str):  # noqa: ANN202
    return client.websocket_connect(CONTROL_PATH.format(sid=session_id))


@pytest.mark.browser
def test_a_flooded_control_channel_does_not_break_the_run(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """쓰레기 사건을 쏟아부어도 실행이 완주한다 (FR-348 · SC-519).

    폭주가 프레임 전달을 막거나 실행을 세우면 FR-336·FR-348 위반이다. 채널이 사건을
    **버리고 사유를 돌려주는** 것으로 끝나야 한다.
    """
    test_id = record_login(keyed_client, fixture_app)

    for attempt in range(FAILURE_RUNS):
        session_id = _start_recording(keyed_client, fixture_app)
        try:
            with _open_control(keyed_client, session_id) as ws:
                for event in GARBAGE * 5:
                    ws.send_text(json.dumps(event))
                # 거절이 돌아오는지까지는 여기서 재지 않는다. 재는 것은 실행이 산다는 것이다.
        finally:
            stop_quietly(keyed_client, session_id)

        view = replay(keyed_client, test_id)
        # **끝났다는 것이 재는 것이다** — 결말이 통과인지 실패인지는 이 검증의 관심이
        # 아니다. 관심은 조작 채널의 사정이 실행을 세우거나 유실시키지 않았는가 하나다
        # (FR-348). `replay` 는 세션 뷰를 돌려주므로 `state` 를 본다.
        assert view["state"] in ("completed", "failed", "stopped"), (
            f"{attempt + 1}회차: 조작 채널 폭주 뒤 실행이 완주하지 못했다 — {view['state']}"
        )
        assert view["state"] != "lost", (
            f"{attempt + 1}회차: 조작 채널 폭주가 세션을 유실시켰다 (FR-348 위반)"
        )


@pytest.mark.browser
def test_an_abruptly_dropped_control_channel_does_not_break_the_run(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """조작 도중 채널이 끊겨도 실행이 완주한다 (FR-348 · FR-318).

    **누른 채로 끊는다** — 끌어놓기 중간에 연결이 사라지는 형태다. 서버가 `pointer.up` 을
    보내지 않으면 대상 페이지가 누른 상태로 남고, 그 상태에서 다음 실행이 엉뚱하게
    실패한다 (contracts §2).
    """
    test_id = record_login(keyed_client, fixture_app)

    for attempt in range(FAILURE_RUNS):
        session_id = _start_recording(keyed_client, fixture_app)
        try:
            with _open_control(keyed_client, session_id) as ws:
                ws.send_text(
                    json.dumps(
                        {"kind": "pointer.down", "x": 5, "y": 5, "button": "left", "tab": 0}
                    )
                )
                # 놓지 않고 끊는다. 컨텍스트를 나가며 소켓이 닫힌다.
        finally:
            stop_quietly(keyed_client, session_id)

        view = replay(keyed_client, test_id)
        assert view["state"] in ("completed", "failed", "stopped"), (
            f"{attempt + 1}회차: 채널이 끊긴 뒤 실행이 완주하지 못했다 — {view['state']}"
        )
        assert view["state"] != "lost", (
            f"{attempt + 1}회차: 끊긴 채널이 세션을 유실시켰다 (FR-348 위반)"
        )


@pytest.mark.browser
def test_the_control_channel_is_refused_during_a_run(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """실행 중에는 채널이 **수립되지 않는다** (FR-315·FR-342).

    화면 단에서 막는 것으로 충분하지 않다는 것이 FR-342 다. 화면을 우회해 소켓에 직접
    붙는 경로에서도 거절되어야 한다.
    """
    from us2_support import start_replay, wait_for_run

    test_id = record_login(keyed_client, fixture_app)
    session_id = start_replay(keyed_client, test_id)
    try:
        refused = False
        try:
            with _open_control(keyed_client, session_id):
                pass
        except Exception:  # noqa: BLE001 - 수립 거절은 연결 오류로 나타난다
            refused = True
        assert refused, "실행 중인 세션에 조작 채널이 붙었다 (FR-342 위반)"
    finally:
        wait_for_run(keyed_client, session_id)
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_only_one_controller_per_session(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """세션당 조작자는 하나다 (명세 Out of Scope · contracts §2).

    둘이 붙으면 같은 화면에 두 사람의 조작이 섞이고, 어느 조작이 어느 Step 이 되었는지
    아무도 답할 수 없다.
    """
    session_id = _start_recording(keyed_client, fixture_app)
    try:
        with _open_control(keyed_client, session_id):
            refused = False
            try:
                with _open_control(keyed_client, session_id):
                    pass
            except Exception:  # noqa: BLE001
                refused = True
            assert refused, "같은 세션에 조작 채널이 둘 붙었다"
    finally:
        stop_quietly(keyed_client, session_id)


def _start_recording(client: TestClient, fixture_app: str) -> str:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])
