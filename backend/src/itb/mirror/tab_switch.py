"""미러 표시 탭 관리. FR-030f·FR-047c~e (research R3).

**한 번에 한 탭만 스트리밍한다.** 모든 탭을 동시에 밀면 프레임률 목표를 탭 수로 나누게
되고, 관찰 목적에 쓰이지 않는 대역폭을 쓴다.

**모든 활성 상태에서 미러를 유지한다** (FR-047d). 종료·유실 시에는 중단하고 그 사실을
표시한다 (FR-047e).

**010 이후 미러는 조작 국면에서 조작을 받는다** (FR-314). 그래서 이 컨트롤러가 하나를 더
갖는다 — **지금 보고 있는 탭에 붙은 조작 통로**다. 조작은 활성 탭이 아니라 **보고 있는
탭**에 가야 한다 (FR-317). 활성 탭에 보내면 사용자가 보지 않는 화면이 조작되고, 무엇이
눌렸는지는 어디에도 나타나지 않는다.

표시 탭과 조작 대상이 **같은 곳에서 갈아 끼워지는 것**이 그 요구의 구현이다. 두 곳에서
따로 관리하면 탭을 바꾸는 순간 둘이 갈리고, 갈린 상태에서 한 번의 조작이 다른 탭에 간다.
"""

from __future__ import annotations

import contextlib

from itb.execution.session import BrowserSession
from itb.execution.state_machine import mirror_should_run
from itb.mirror.input import TabInput
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
        self._input: TabInput | None = None
        """보고 있는 탭의 조작 통로 (010 FR-317).

        `None` 이면 조작을 받을 수 없다 — 표시 중인 탭이 없거나 조작 채널이 아직 열리지
        않았다. 프레임과 **같은 탭**을 가리킨다는 것이 이 필드가 여기 있는 이유다.
        """
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

        was_controlling = self._input is not None
        # 탭을 바꾸면 `TabScreencast` 가 새로 만들어진다. 국면을 이어 주지 않으면 탭을
        # 바꾼 순간부터 조작 국면인데 관찰 국면의 주기로 돈다.
        control_phase = self._current is not None and self._current.control_phase
        await self._stop_current()
        screencast = TabScreencast(handle.page, tab_index, self._session.emit)
        self._current = screencast
        self._session.mirrored_tab_index = tab_index
        # FR-317 — 조작 통로가 열려 있었다면 **새 표시 탭으로 함께 옮긴다.** 옮기지 않으면
        # 다음 조작이 사용자가 더 이상 보고 있지 않은 탭에 간다.
        if was_controlling:
            await self.attach_input()
        screencast.set_control_phase(control_phase or was_controlling)
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
        """미러를 중단하고 사유를 표시한다 (FR-047e).

        조작 통로도 함께 닫는다 — 세션이 끝난 뒤 마지막 프레임이 남아 있어도 조작을
        전달해서는 안 된다 (FR-347).
        """
        await self.detach_input()
        if self._current is None:
            return
        await self._current.stop(reason)
        self._current = None

    async def _stop_current(self) -> None:
        await self.detach_input()
        if self._current is None:
            return
        with contextlib.suppress(Exception):
            await self._current.stop()
        self._current = None

    # ─── 조작 통로 (010 FR-314·FR-317) ─────────────────────────────────────

    @property
    def input(self) -> TabInput | None:
        """보고 있는 탭의 조작 통로. 열려 있지 않으면 `None`."""
        return self._input

    def set_control_phase(self, active: bool) -> None:
        """지금이 조작 국면인지 미러에 알린다 (010 FR-335 · research R8).

        **미러가 스스로 국면을 판정하지 않는다.** 상태 기계가 알고 통보한다 — 프론트의
        `MirrorView` 가 국면을 보지 않는 것(FR-316)과 같은 이유다. 판정이 두 곳에 있으면
        한 곳이 빠지고, 빠진 자리에서 조작 국면인데 2초 주기로 도는 미러가 남는다.
        """
        if self._current is not None:
            self._current.set_control_phase(active)

    async def attach_input(self) -> TabInput | None:
        """지금 보고 있는 탭에 조작 통로를 연다 (FR-317).

        **국면 판정은 하지 않는다.** 언제 열고 닫을지는 조작 채널이 정하고
        (`api/ws/control_channel.py`), 여기는 「어느 탭인가」만 안다. 판정이 두 곳에 있으면
        한 곳이 빠지고, 빠진 자리에서 관찰 국면에 열린 통로가 남는다 (FR-342).

        열 수 없으면 `None` 을 돌려준다 — 미러 실패는 실행 실패가 아니다 (FR-047b).
        """
        await self.detach_input()
        if self._current is None:
            return None
        handle = self._session.find_tab(self._current.tab_index)
        if handle is None or handle.closed:
            return None
        controller = TabInput(handle.page, self._current.tab_index)
        try:
            await controller.attach()
        except Exception:  # noqa: BLE001 - CDP 를 못 쓰는 환경도 있다 (FR-348)
            return None
        self._input = controller
        return controller

    async def detach_input(self) -> None:
        """조작 통로를 닫는다. **누른 채로 남은 포인터를 먼저 놓는다** (FR-318).

        `TabInput.detach` 가 그 순서를 지킨다 — 여기서 다시 하지 않는다.
        """
        if self._input is None:
            return
        controller, self._input = self._input, None
        with contextlib.suppress(Exception):
            await controller.detach()
