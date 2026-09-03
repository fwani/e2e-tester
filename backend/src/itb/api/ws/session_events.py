"""세션 이벤트 송신. contracts/websocket.md.

**서버 → 클라이언트 단방향.** 클라이언트가 WebSocket 으로 명령을 보내는 경로를 두지 않는다 —
같은 명령이 두 경로로 들어오면 검증과 권한 처리가 두 벌이 되고 어느 쪽이 진실인지 모호해진다.

**재전송하지 않는다.** 연결이 끊기면 클라이언트가 `GET /api/sessions/{sid}` 로 전체 상태를
다시 받는다. 단독 로컬 도구이므로 그게 싸고, 재전송 버퍼는 유실 시 조용히 어긋나는 상태를 만든다.

민감 값은 이 계층에 도달하기 전에 마스킹되어 있어야 한다 (FR-089d). 여기서는 받은 것을
그대로 보낸다 — 마스킹 책임을 두 곳에 두면 어느 쪽이 빠졌는지 알 수 없다.
"""

from __future__ import annotations

import contextlib
import itertools
from typing import Any

from fastapi import WebSocket

MIRROR_EVENTS = frozenset(
    {"mirror_frame", "mirror_tab_changed", "mirror_degraded", "mirror_stopped"}
)
"""유실 가능한 이벤트. 프론트는 마지막 프레임만 그리면 되고, 전송 실패가 실행에 영향을
주어서는 안 된다 (FR-047b)."""


class SessionEventHub:
    """한 세션의 WebSocket 구독자들.

    구독자가 없어도 이벤트 발행은 성공한다 — 실행이 UI 연결 여부에 의존해서는 안 된다.
    """

    def __init__(self) -> None:
        self._sockets: list[WebSocket] = []
        self._seq = itertools.count(1)

    @property
    def subscriber_count(self) -> int:
        return len(self._sockets)

    async def connect(self, socket: WebSocket) -> None:
        await socket.accept()
        self._sockets.append(socket)

    def disconnect(self, socket: WebSocket) -> None:
        with contextlib.suppress(ValueError):
            self._sockets.remove(socket)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """이벤트를 모든 구독자에게 보낸다.

        전송에 실패한 소켓은 목록에서 제거하고 계속 진행한다. **어떤 실패도 호출자에게
        전파하지 않는다** — 미러가 끊겨도 `step_*` 이벤트가 계속 흘러야 하고, 실행 자체는
        영향을 받지 않아야 한다 (FR-047b).
        """
        if not self._sockets:
            return
        message = {"type": event_type, "seq": next(self._seq), **payload}
        dead: list[WebSocket] = []
        for socket in list(self._sockets):
            try:
                await socket.send_json(message)
            except Exception:  # noqa: BLE001 - 끊긴 소켓은 조용히 정리한다
                dead.append(socket)
        for socket in dead:
            self.disconnect(socket)

    async def close_all(self) -> None:
        for socket in list(self._sockets):
            with contextlib.suppress(Exception):
                await socket.close()
        self._sockets.clear()


class EventBroker:
    """세션 ID 별 허브 모음."""

    def __init__(self) -> None:
        self._hubs: dict[str, SessionEventHub] = {}

    def hub(self, session_id: str) -> SessionEventHub:
        hub = self._hubs.get(session_id)
        if hub is None:
            hub = SessionEventHub()
            self._hubs[session_id] = hub
        return hub

    def sink(self, session_id: str):  # noqa: ANN201 - EventSink 시그니처를 만든다
        """`BrowserSession.attach_sink` 에 넘길 통로를 만든다."""
        hub = self.hub(session_id)

        async def send(event_type: str, payload: dict[str, Any]) -> None:
            await hub.publish(event_type, payload)

        return send

    async def drop(self, session_id: str) -> None:
        hub = self._hubs.pop(session_id, None)
        if hub is not None:
            await hub.close_all()

    async def close_all(self) -> None:
        for sid in list(self._hubs):
            await self.drop(sid)
