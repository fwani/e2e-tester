"""다시 집기. FR-020 (T138).

깨진 Step 의 대상 요소를 사용자가 **브라우저에서 다시 지정**하면 후보를 새로 수집·검증해
그 Step 을 갱신한다. 저장된 후보를 손으로 고치게 하지 않는 것이 이 기능의 요점이다 —
CSS 경로를 사람이 쓰기 시작하면 원칙 IV 의 후보 묶음이 단일 셀렉터로 퇴화한다.

**대기 상태를 리코더 안에 두지 않는다.** 리코더는 "동작을 Step 으로 만드는 것" 이고,
다시 집기는 "다음 클릭 한 번을 Step 으로 만들지 않고 대상 지정으로 쓰는 것" 이다.
반대 동작이므로 분리해 두면 리코더의 판정에 예외가 섞이지 않는다.

`drag` 는 대상 요소를 둘 가진다 (`target` 과 `drop_target`). 어느 쪽을 다시 집는지
`slot` 으로 지정한다 — 지정하지 않으면 놓는 위치를 고칠 방법이 없다 (T166).
"""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from itb.domain.locator import TargetLocator


class RepickSlot(StrEnum):
    """다시 집을 대상. `drag` 만 두 번째 값을 쓴다."""

    TARGET = "target"
    DROP_TARGET = "drop_target"


@dataclass(frozen=True, slots=True)
class PendingRepick:
    """다시 집기 대기 하나."""

    step_id: str
    slot: RepickSlot = RepickSlot.TARGET


RepickSink = Callable[[PendingRepick, TargetLocator], Awaitable[None]]
"""재지정 결과를 받는 통로. Step 갱신과 이벤트 발행은 호출자가 한다."""


@dataclass(slots=True)
class RepickController:
    """다시 집기 대기 상태.

    한 번에 하나만 대기한다. 두 개를 동시에 걸면 사용자의 다음 클릭이 어느 Step 을
    고치는지 알 수 없다.
    """

    sink: RepickSink | None = None
    pending: PendingRepick | None = None

    @property
    def armed(self) -> bool:
        return self.pending is not None

    def arm(self, step_id: str, slot: RepickSlot = RepickSlot.TARGET) -> PendingRepick:
        self.pending = PendingRepick(step_id=step_id, slot=slot)
        return self.pending

    def clear(self) -> PendingRepick | None:
        pending, self.pending = self.pending, None
        return pending

    async def deliver(self, target: TargetLocator) -> bool:
        """대기 중이던 Step 에 새 후보를 전달한다. 전달했으면 True.

        **대기를 먼저 해제한다.** `pointerdown` 과 `click` 이 같은 클릭에 대해 둘 다
        도착하므로, 해제가 늦으면 한 번의 클릭이 두 번 전달된다.
        """
        pending = self.clear()
        if pending is None or self.sink is None:
            return False
        with contextlib.suppress(Exception):
            await self.sink(pending, target)
        return True


def apply_repick(step: object, slot: RepickSlot, target: TargetLocator) -> object:
    """Step 의 지정된 슬롯을 새 후보로 바꾼 사본을 돌려준다.

    Step 종류를 바꾸지 않는다. 대상이 없는 종류(`navigate`·`close_tab`)나 없는 슬롯을
    지정하면 거절한다 — 조용히 무시하면 사용자는 갱신됐다고 오해한다.
    """
    if not hasattr(step, slot.value):
        kind = getattr(step, "type", type(step).__name__)
        msg = f"{kind} Step 에는 '{slot.value}' 대상이 없어 다시 집을 수 없습니다."
        raise ValueError(msg)
    return step.model_copy(update={slot.value: target})  # type: ignore[attr-defined]
