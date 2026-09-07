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

    async def connect(
        self, socket: WebSocket, current_frame: dict[str, Any] | None = None
    ) -> None:
        """구독을 받는다. **현재 화면 한 장을 함께 준다** (005 FR-162).

        스크린캐스트는 화면이 변할 때만 프레임을 만들고, 그 초기 한 장은 이 구독이 붙기
        전에 발행된다. `publish` 는 구독자가 없으면 조용히 버리므로, 정적 화면에서는
        미리보기에 한 장도 도달하지 않았다 — 실측 0건 (U-24).

        **이것은 재전송이 아니라 현재 상태 전달이다.** 이 모듈이 "재전송하지 않는다" 로
        정한 것은 순서 있는 상태 이벤트를 두고 한 말이고, `mirror_frame` 은 이미
        "유실 가능 · 마지막 프레임만 그리면 된다" 로 정의돼 있다.

        보낼 프레임이 없으면 아무것도 보내지 않는다. 없는 것을 빈 프레임으로 채우면
        화면이 검은 화면을 대상 앱의 모습으로 그린다.
        """
        await socket.accept()
        self._sockets.append(socket)
        if current_frame is None:
            return
        message = {"type": "mirror_frame", "seq": next(self._seq), **current_frame}
        try:
            await socket.send_json(message)
        except Exception:  # noqa: BLE001 - 첫 프레임 실패가 구독을 막지 않는다
            # 미러 실패는 실행에 영향을 주지 않는다 (FR-047b). 구독은 살려 둔다 —
            # `step_*` 이벤트는 계속 흘러야 한다.
            return

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
