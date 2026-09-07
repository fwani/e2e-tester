"""미러 표시 탭 관리. FR-030f·FR-047c~e (research R3).

**한 번에 한 탭만 스트리밍한다.** 모든 탭을 동시에 밀면 프레임률 목표를 탭 수로 나누게
되고, 관찰 목적에 쓰이지 않는 대역폭을 쓴다.

**모든 활성 상태에서 미러를 유지한다** (FR-047d). 조작 국면에서도 읽기 전용으로 계속 보여
준다 — 브라우저 세션이 살아 있다는 것을 사용자가 눈으로 확인하는 수단이기 때문이다.
종료·유실 시에는 중단하고 그 사실을 표시한다 (FR-047e).
"""

from __future__ import annotations

import contextlib

from itb.execution.session import BrowserSession
from itb.execution.state_machine import mirror_should_run
from itb.mirror.screencast import TabScreencast


class MirrorController:
    """세션 하나의 미러. 표시 탭을 갈아 끼운다.

    실행 중에는 현재 Step 의 대상 탭을 따라간다 — `follow` 를 러너가 부른다. 사용자가
    직접 고른 탭이 있으면 그 선택이 우선한다. 자동 추적이 사용자의 선택을 덮으면,
    사용자는 보려던 탭을 계속 놓친다.
    """

    def __init__(self, session: BrowserSession) -> None:
        self._session = session
        self._current: TabScreencast | None = None
        self._pinned = False
        """사용자가 탭을 직접 골랐는가. 골랐다면 자동 추적을 하지 않는다."""

    @property
    def current_tab(self) -> int | None:
        return self._current.tab_index if self._current is not None else None

    @property
    def pinned(self) -> bool:
        return self._pinned

    # ─── 표시 탭 전환 ──────────────────────────────────────────────────────

    async def show(self, tab_index: int, *, pinned: bool = False) -> bool:
        """`tab_index` 를 표시한다. 이전 탭은 정지한다.

        돌려주는 값은 강등 없이 시작했는지 여부다. 대상 탭이 없거나 닫혀 있으면 아무것도
        하지 않고 `False` 를 돌려준다 — 미러 실패는 실행 실패가 아니다 (FR-047b).
        """
        if pinned:
            self._pinned = True

        if not mirror_should_run(self._session.state):
            await self.stop("세션이 종료되어 미러를 중단했습니다.")
            return False

        if self._current is not None and self._current.tab_index == tab_index:
            return self._current.running and not self._current.degraded

        handle = self._session.find_tab(tab_index)
        if handle is None or handle.closed:
            return False

        await self._stop_current()
        screencast = TabScreencast(handle.page, tab_index, self._session.emit)
        self._current = screencast
        self._session.mirrored_tab_index = tab_index
        await self._session.emit("mirror_tab_changed", tab=tab_index)
        return await screencast.start()

    async def follow(self, tab_index: int) -> None:
        """실행이 옮겨간 탭을 따라간다. 사용자가 탭을 고정했으면 따라가지 않는다."""
        if self._pinned:
            return
        await self.show(tab_index)

    def unpin(self) -> None:
        """자동 추적을 다시 켠다."""
        self._pinned = False

    # ─── 정지 ──────────────────────────────────────────────────────────────

    def last_frame(self) -> dict[str, object] | None:
        """지금 표시 중인 탭의 마지막 프레임 (005 FR-162).

        새 구독자에게 현재 화면을 주기 위한 것이다. 표시 중인 탭이 없으면 `None`.
        """
        if self._current is None:
            return None
        return self._current.last_frame()

    async def on_transport_lost(self) -> None:
        """이벤트 통로가 끊겼다. ack 를 멈춰 프레임 밀기를 자연히 세운다 (FR-047b)."""
        if self._current is not None:
            self._current.pause_acking()

    async def stop(self, reason: str) -> None:
        """미러를 중단하고 사유를 표시한다 (FR-047e)."""
        if self._current is None:
            return
        await self._current.stop(reason)
        self._current = None

    async def _stop_current(self) -> None:
        if self._current is None:
            return
        with contextlib.suppress(Exception):
            await self._current.stop()
        self._current = None
