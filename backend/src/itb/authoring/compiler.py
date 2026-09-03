"""성공한 도구 호출을 Step 으로 확정한다. FR-061·FR-062 (T113).

**변환이 없다.** 도구 표면이 Step 과 1:1 이므로(research R5, T163) 도구가 성공했다는 것은
곧 그 Step 이 실행됐다는 뜻이고, 컴파일러가 하는 일은 그것을 목록에 넣는 것뿐이다.
표현 불가능한 동작을 만나 실패하는 경우가 원리적으로 없다 — 그것이 도구 표면을 Step 에
묶어 둔 이유다.

이 모듈이 별도로 존재하는 이유는 **어디에 넣을지**가 세션의 사정이기 때문이다. 목록 끝에
붙일지 일시정지 위치에 삽입할지는 도구가 알 필요가 없다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from itb.domain.step import Step

StepPlacer = Callable[[Step, int], Awaitable[None]]
"""(step, insert_index) 를 받아 세션의 작업 중 목록에 넣고 이벤트를 발행한다.

리코더의 `sink` 와 **같은 통로다.** 사람 녹화·AI 작성·자연어 추가가 모두 같은
`step_added` 이벤트로 나가야 프론트에 작성 주체별 분기가 생기지 않는다 (원칙 I).
"""


@dataclass(slots=True)
class StepCompiler:
    """한 작성 세션에서 확정된 Step 들.

    ``insert_at`` 이 None 이면 목록 끝에 붙인다. 일시정지 중 자연어 추가(FR-079)는
    그 위치를 지정한다.
    """

    place: StepPlacer
    insert_at: int | None = None
    compiled: list[Step] = field(default_factory=list)

    async def accept(self, step: Step) -> None:
        """성공한 동작 하나를 Step 으로 확정한다."""
        index = self.insert_at if self.insert_at is not None else -1
        self.compiled.append(step)
        await self.place(step, index)
        if self.insert_at is not None:
            self.insert_at += 1

    @property
    def count(self) -> int:
        return len(self.compiled)

    def step_ids(self) -> list[str]:
        """이 지시문에서 나온 Step id 목록 (data-model §10 `produced_step_ids`)."""
        return [s.id for s in self.compiled]
