"""미러 프레임 도달을 재는 통합 하니스 (005 T002 · FR-160·FR-161·FR-162·SC-218).

U-24 의 실측은 **구독 후 정적 화면 5초에 0건**이었다. 그 실측을 그대로 재현하려면 두
조건이 필요하다.

1. **화면이 변하지 않는 세션** — 스크린캐스트는 화면이 변할 때만 프레임을 만든다.
2. **뒤늦게 붙는 구독** — 유일한 초기 프레임은 `POST /api/sessions` 안에서 발행되고,
   프론트의 WebSocket 은 그 응답을 받은 뒤에 붙는다. 구독자가 없는 동안 허브는 조용히
   버린다.

그래서 이 하니스는 세션을 만든 뒤 **일부러 기다렸다가** 구독을 붙인다. 기다리지 않으면
결함을 재현하지 못하고, 재현하지 못하는 테스트는 회귀를 잡지 못한다.

`backend/tests/unit/test_mirror_frame_delivery.py` 는 같은 성질을 가짜 페이지로 본다.
그쪽이 빠르고, 이쪽은 **진짜 브라우저에서도 그런지**를 본다 — CDP 스크린캐스트의
"화면이 변할 때만" 성질은 가짜로 만들 수 없다.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

WS_PATH = "/api/sessions/{sid}/events"

LATE_SUBSCRIBE_DELAY_S = 1.5
"""구독을 붙이기 전에 기다리는 시간.

세션 생성이 돌려준 뒤에도 초기 프레임 발행이 조금 늦을 수 있으므로, 그 시점을 확실히
지나도록 잡는다. 무프레임 감시 주기(`IDLE_INTERVAL_S`=2초)보다는 짧게 둔다 — 감시가
채워 준 프레임을 받고 "캐시가 동작했다" 고 잘못 읽지 않기 위해서다.
"""


@dataclass
class MirrorProbe:
    """붙어 있는 구독에서 `mirror_frame` 을 꺼내 본다.

    `TestClient` 의 WebSocket 은 `receive_json()` 이 무기한 막힌다. 프레임이 **오지 않는
    것**을 재려는 하니스가 오지 않을 때 영원히 매달리면 쓸 수 없으므로, 읽기를 별도
    스레드에 두고 본 스레드는 마감 시각을 들고 큐를 본다.
    """

    subscribed_at: float
    _frames: queue.Queue[dict[str, Any]] = field(default_factory=queue.Queue)
    _all: list[dict[str, Any]] = field(default_factory=list)
    _errors: list[BaseException] = field(default_factory=list)

    def messages_of_type(self, event_type: str) -> list[dict[str, Any]]:
        """구독 이후 도착한 특정 이벤트 전부. `mirror_degraded` 부재 검증에 쓴다."""
        return [m for m in list(self._all) if m.get("type") == event_type]

    def next_frame(self, timeout_s: float) -> dict[str, Any] | None:
        """다음 `mirror_frame` 하나. 시간 안에 오지 않으면 `None`."""
        try:
            return self._frames.get(timeout=timeout_s)
        except queue.Empty:
            return None

    def seconds_to_first_frame(self, timeout_s: float) -> float | None:
        """구독을 붙인 시점부터 첫 프레임까지의 초. 오지 않으면 `None` (SC-218)."""
        frame = self.next_frame(timeout_s)
        if frame is None:
            return None
        return time.monotonic() - self.subscribed_at

    def collect_for(self, seconds: float) -> list[dict[str, Any]]:
        """주어진 시간 동안 도착한 프레임을 모은다 (FR-160 의 "계속 온다" 검증용)."""
        deadline = time.monotonic() + seconds
        got: list[dict[str, Any]] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return got
            frame = self.next_frame(remaining)
            if frame is not None:
                got.append(frame)


@pytest.fixture
def static_page_session(keyed_client: TestClient, fixture_app: str) -> Iterator[str]:
    """정적 페이지를 연 녹화 세션. 화면을 **건드리지 않는다**.

    건드리는 순간 스크린캐스트가 프레임을 만들어 U-24 의 국면이 사라진다.
    """
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    session_id = str(created.json()["session_id"])
    try:
        yield session_id
    finally:
        from us2_support import stop_quietly

        stop_quietly(keyed_client, session_id)


@pytest.fixture
def subscribe_late(
    keyed_client: TestClient,
) -> Iterator[Callable[..., Any]]:
    """세션에 **뒤늦게** 구독을 붙이고 `MirrorProbe` 를 준다.

    ```python
    with subscribe_late(session_id) as probe:
        assert probe.seconds_to_first_frame(3.0) is not None
    ```
    """

    @contextmanager
    def _subscribe(
        session_id: str, *, after_s: float = LATE_SUBSCRIBE_DELAY_S
    ) -> Iterator[MirrorProbe]:
        time.sleep(after_s)
        with keyed_client.websocket_connect(WS_PATH.format(sid=session_id)) as ws:
            probe = MirrorProbe(subscribed_at=time.monotonic())
            stop = threading.Event()

            def pump() -> None:
                while not stop.is_set():
                    try:
                        message = ws.receive_json()
                    except Exception as exc:  # noqa: BLE001 - 닫히면 여기로 온다
                        if not stop.is_set():
                            probe._errors.append(exc)
                        return
                    probe._all.append(message)
                    if message.get("type") == "mirror_frame":
                        probe._frames.put(message)

            reader = threading.Thread(target=pump, name="mirror-probe", daemon=True)
            reader.start()
            try:
                yield probe
            finally:
                # 먼저 정지 신호를 세우고 소켓을 닫는다. 순서가 반대면 닫힘 예외를
                # 진짜 오류로 기록한다.
                stop.set()
                ws.close()
                reader.join(timeout=5.0)

    yield _subscribe
