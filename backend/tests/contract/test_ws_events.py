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

EXECUTION_EVENT_KEYS = {
    "step_started": {"step_id", "index", "tab"},
    "step_finished": {"step_id", "index", "outcome", "duration_ms", "resolved_candidate"},
    "step_failed": {"step_id", "index", "error_message", "locator_attempts", "tab_wait_ms"},
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

    with client.websocket_connect(f"/api/sessions/{session_id}/events") as ws:
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
