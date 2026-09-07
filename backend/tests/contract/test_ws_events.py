"""T076 — WebSocket 이벤트 계약 (contracts/websocket.md).

세 가지를 본다.

1. **형태** — 모든 이벤트에 `type` 과 `seq` 가 있고, 실행 이벤트의 페이로드 키가 계약과 같다.
2. **`seq` 단조 증가** — 클라이언트가 재연결·서버 재시작을 구분하는 유일한 근거다.
3. **`mirror_*` 유실 허용** — 미러 전송 실패가 `step_*` 흐름이나 실행에 영향을 주지 않는다.

1·3은 소켓 계층만 있으면 검증할 수 있으므로 브라우저 없이 본다. 2는 실제 재실행에서도
확인한다 — 발행 지점이 여러 곳이라 한 곳만 보면 부족하다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from itb.api.ws.session_events import MIRROR_EVENTS, SessionEventHub

WS_PATH = "/api/sessions/{sid}/events"
"""T160 에서 확정한 경로. 계약 문서와 구현이 같은 값을 쓴다."""

STATE_EVENT_KEYS = {"state", "current_step_index", "active_tab"}
"""contracts/websocket.md §상태 이벤트."""

TAB_OPENED_KEYS = {"tab", "url", "title"}

EXECUTION_EVENT_KEYS = {
    "step_started": {"step_id", "index", "tab"},
    "step_finished": {
        "step_id",
        "index",
        "outcome",
        "duration_ms",
        "resolved_candidate",
        # 004 FR-114 — 실행 중에도 "이 Step 이 왜 오래 걸렸는지" 가 보인다.
        "element_wait_ms",
    },
    "step_failed": {
        "step_id",
        "index",
        "error_message",
        "locator_attempts",
        "tab_wait_ms",
        "element_wait_ms",
    },
    "run_finished": {
        "outcome",
        "total_ms",
        "passed_count",
        "total_count",
        "failed_step_index",
    },
}
"""contracts/websocket.md §실행 이벤트 의 페이로드."""


class _FakeSocket:
    """전송을 기록하는 가짜 소켓. 필요하면 전송에 실패한다."""

    def __init__(self, fail_on: set[str] | None = None) -> None:
        self.sent: list[dict] = []
        self.fail_on = fail_on or set()
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        if message["type"] in self.fail_on:
            msg = "전송 실패 (연결 끊김 모사)"
            raise RuntimeError(msg)
        self.sent.append(message)

    async def close(self) -> None:
        pass


async def test_every_event_carries_type_and_monotonic_seq() -> None:
    """모든 이벤트에 `type` 과 단조 증가하는 `seq` 가 있다."""
    hub = SessionEventHub()
    socket = _FakeSocket()
    await hub.connect(socket)  # type: ignore[arg-type]

    for index in range(5):
        await hub.publish("step_started", {"step_id": f"step-{index:02d}", "index": index})

    assert len(socket.sent) == 5
    seqs = [m["seq"] for m in socket.sent]
    assert seqs == sorted(seqs), f"seq 가 단조 증가하지 않는다: {seqs}"
    assert len(set(seqs)) == len(seqs), f"seq 가 중복됐다: {seqs}"
    assert all(m["type"] == "step_started" for m in socket.sent)


async def test_mirror_frame_failure_does_not_break_execution_events() -> None:
    """FR-047b — 미러 전송 실패가 `step_*` 흐름을 막지 않는다.

    미러 전송이 예외를 던져도 `publish` 는 호출자에게 전파하지 않는다. 실행 태스크가
    미러 때문에 멈추면 안 된다.
    """
    hub = SessionEventHub()
    healthy = _FakeSocket()
    broken = _FakeSocket(fail_on=set(MIRROR_EVENTS))
    await hub.connect(healthy)  # type: ignore[arg-type]
    await hub.connect(broken)  # type: ignore[arg-type]

    await hub.publish("mirror_frame", {"tab": 0, "data": "AAA", "width": 8, "height": 8})
    await hub.publish("step_finished", {"step_id": "step-01", "index": 0})

    # 실패한 소켓은 조용히 정리되고, 살아 있는 소켓은 계속 받는다.
    assert [m["type"] for m in healthy.sent] == ["mirror_frame", "step_finished"]
    assert broken.sent == []
    assert hub.subscriber_count == 1


async def test_publish_succeeds_without_any_subscriber() -> None:
    """구독자가 없어도 발행은 성공한다 — 실행이 UI 연결 여부에 의존하면 안 된다."""
    hub = SessionEventHub()
    await hub.publish("run_finished", {"outcome": "pass"})  # 예외가 없으면 통과


def test_websocket_endpoint_delivers_events(client: TestClient) -> None:
    """실제 엔드포인트로 붙어 이벤트를 받는다. 서버 → 클라이언트 단방향이다."""
    state = client.app.state.itb
    session_id = "contract-test-session"

    with client.websocket_connect(WS_PATH.format(sid=session_id)) as ws:
        sink = state.broker.sink(session_id)
        client.portal.call(sink, "state_changed", {"state": "replaying"})  # type: ignore[attr-defined]
        client.portal.call(  # type: ignore[attr-defined]
            sink, "run_finished", {"outcome": "pass", "total_ms": 10}
        )

        first = ws.receive_json()
        second = ws.receive_json()

    assert first["type"] == "state_changed"
    assert second["type"] == "run_finished"
    assert second["seq"] > first["seq"], f"seq 가 증가하지 않았다: {first} → {second}"


@pytest.mark.usefixtures("fixture_app")
def test_replay_emits_the_contracted_execution_events(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """실제 재실행이 계약대로 된 실행 이벤트를 낸다."""
    from us2_support import record_login, replay

    test_id = record_login(keyed_client, fixture_app)
    event_log.clear()

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", f"재실행이 실패했다: {view['state']}"

    by_type: dict[str, list[dict]] = {}
    for name, payload in event_log:
        by_type.setdefault(name, []).append(payload)

    for required in ("step_started", "step_finished", "run_finished"):
        assert required in by_type, (
            f"{required} 이벤트가 없다. 관측된 이벤트: {sorted(by_type)}"
        )

    for name, expected_keys in EXECUTION_EVENT_KEYS.items():
        for payload in by_type.get(name, []):
            missing = expected_keys - set(payload)
            assert not missing, f"{name} 페이로드에 계약 키가 빠졌다: {sorted(missing)}"

    assert len(by_type["step_started"]) == len(by_type["step_finished"])
    assert len(by_type["run_finished"]) == 1
    summary = by_type["run_finished"][0]
    assert summary["outcome"] == "pass"
    assert summary["passed_count"] == summary["total_count"]


# ─── T160: 계약과 구현의 일치 ───────────────────────────────────────────────


def test_contract_document_declares_the_implemented_path() -> None:
    """계약 문서의 경로가 구현 경로와 같아야 한다.

    문서만 읽고 프론트를 만들었을 때 연결되지 않는 상황을 막는다. 이 테스트가 없으면
    둘의 불일치는 사람이 두 파일을 나란히 놓고 볼 때만 드러난다.
    """
    import pathlib

    contract = (
        pathlib.Path(__file__).resolve().parents[3]
        / "specs/001-interactive-ai-test-builder/contracts/websocket.md"
    )
    assert contract.exists(), f"계약 문서를 찾을 수 없다: {contract}"
    body = contract.read_text(encoding="utf-8")
    assert "/api/sessions/{session_id}/events" in body, (
        "계약 문서의 경로가 구현과 다르다"
    )
    assert "/ws/sessions/{session_id}" not in body, (
        "옛 경로 표기가 계약 문서에 남아 있다"
    )


@pytest.mark.usefixtures("fixture_app")
def test_state_changed_carries_the_contracted_payload(
    project_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """`state_changed` 는 `state`·`current_step_index`·`active_tab` 을 담는다."""
    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    try:
        payloads = [p for name, p in event_log if name == "state_changed"]
        assert payloads, f"state_changed 가 없다: {sorted({n for n, _ in event_log})}"
        for payload in payloads:
            missing = STATE_EVENT_KEYS - set(payload)
            assert not missing, f"계약 키가 빠졌다: {sorted(missing)}"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_tab_opened_carries_title(
    project_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """`tab_opened` 는 `title` 을 담는다. 막 열린 탭이면 빈 문자열일 수 있다.

    **최초 탭(0)은 대상이 아니다.** 세션이 만들어지는 도중에 열리므로 이벤트 통로가 아직
    붙지 않았고, 클라이언트는 세션 조회로 그 탭을 알게 된다. 이벤트가 의미를 갖는 것은
    녹화 중 새로 열리는 탭이다 (FR-030a).
    """
    import asyncio
    from typing import Any

    created = project_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    sid = created.json()["session_id"]
    try:
        session = project_client.app.state.itb.sessions.require(sid)
        page = session.tabs[0].page

        async def act(p: Any = page) -> None:
            await p.fill("#email", "tester@example.com")
            await asyncio.sleep(0.2)
            await p.fill("#password", "record-only-not-a-real-secret")
            await asyncio.sleep(0.2)
            await p.click("[data-testid=login-submit]")
            await p.wait_for_url("**/projects.html")
            await asyncio.sleep(0.4)
            await p.click("[data-testid=terms-link]")
            await asyncio.sleep(0.9)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        payloads = [p for name, p in event_log if name == "tab_opened"]
        assert payloads, "새 탭을 열었는데 tab_opened 이벤트가 없다"
        for payload in payloads:
            missing = TAB_OPENED_KEYS - set(payload)
            assert not missing, f"계약 키가 빠졌다: {sorted(missing)}"
            assert isinstance(payload["title"], str)
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_edit_warning_is_published_as_an_event(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """FR-040b — 편집 경고는 REST 응답만이 아니라 이벤트로도 나간다.

    편집을 요청한 클라이언트가 아닌 화면도 경고를 알아야 한다. 이벤트가 없으면 같은
    세션을 보고 있는 다른 화면은 편집이 반영되지 않았다는 사실을 모른다.
    """
    from us2_support import record_login, start_replay, stop_quietly

    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        # 실행이 진행된 뒤 일시정지해 "이미 실행된 Step" 편집 상황을 만든다.
        from us2_support import wait_for_run

        wait_for_run(keyed_client, sid)
        steps = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert steps

        event_log.clear()
        # 종료된 세션은 편집을 받지 않는다 — 경고 이벤트 경로만 직접 확인한다.
        session = keyed_client.app.state.itb.sessions.require(sid)
        session.add_edit_warning("step 01 은 이미 실행된 Step입니다.")
        keyed_client.portal.call(session.publish_edit_warnings)  # type: ignore[attr-defined]

        warnings = [p for name, p in event_log if name == "edit_warning"]
        assert warnings, f"edit_warning 이 발행되지 않았다: {[n for n, _ in event_log]}"
        assert warnings[0]["messages"], "경고 메시지가 비어 있다"
    finally:
        stop_quietly(keyed_client, sid)


# ─── 004: 실행 속도 변경 이벤트 (contracts/websocket.md §1) ─────────────────

PACING_CHANGED_KEYS = {"pacing", "delay_ms", "auto_pause", "preference_saved"}


def test_pacing_changed_carries_the_contracted_payload(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """속도 변경이 **계산된 값까지** 실어 보낸다 (004).

    화면이 간격 대응표를 따로 들고 있으면 서버와 갈린다 — 화면이 "1.5초 쉽니다" 라고
    말하는 동안 러너가 0.5초를 쉬는 상태가 만들어진다. 값을 함께 보내면 대응표가 서버
    한 곳에만 남는다.
    """
    from us2_support import record_login, start_replay, stop_quietly

    from itb.domain.run_pacing import RunPacing, auto_pause, delay_ms

    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    event_log.clear()
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/pacing", json={"pacing": RunPacing.SLOW.value}
        )
        assert resp.status_code == 200, resp.text
    finally:
        stop_quietly(keyed_client, sid)

    events = [p for name, p in event_log if name == "pacing_changed"]
    assert events, f"pacing_changed 가 없다. 관측: {sorted({n for n, _ in event_log})}"

    payload = events[0]
    missing = PACING_CHANGED_KEYS - set(payload)
    assert not missing, f"계약 키가 빠졌다: {sorted(missing)}"
    assert payload["pacing"] == RunPacing.SLOW.value
    assert payload["delay_ms"] == delay_ms(RunPacing.SLOW)
    assert payload["auto_pause"] is auto_pause(RunPacing.SLOW)
