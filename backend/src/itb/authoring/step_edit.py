"""Step 수정 트랜잭션. 026 FR-013·FR-020~FR-029 (research R2·R5·R7).

## `rerecord.py` 의 형제이지 확장이 아니다

016 의 `RerecordTransaction` 이 성립하는 근거는 그 docstring 의 한 문장이다.

> 권한이 그 집합으로 한정되므로 다른 Step 이 바뀌지 않고, 바뀌지 않으므로 그것만 지우면
> 시작 전과 같아진다 (불변식 9).

**이 모듈은 「다른 Step 이 바뀌지 않는다」를 깬다.** 사용자가 고른 Step 하나를 AI 가
제자리에서 고치기 때문이다. 같은 클래스에 담으면 위 문장이 「스냅샷이 없으면 … 있으면 …」
두 갈래가 되고, 016 의 불변식 9 증명이 조건부가 된다. 016 의 검사가 증명하는 것과 이쪽의
검사가 증명하는 것이 한 클래스에서 섞이면, 깨졌을 때 어느 쪽인지 검사가 말해 주지 못한다.

형제로 두면 **016 research R7 이 그대로 산다** — 재녹화는 여전히 스냅샷 없이 되돌린다.

## 확정이 016 과 정반대다

|  | 016 재녹화 | 이 모듈 |
|---|---|---|
| 확정 | 옛 구간을 **지운다** | **아무것도 지우지 않는다** |
| 버리기 | 이번에 만든 것을 지운다 | 그것에 더해 **대상을 원본으로 되돌린다** |
| 아무것도 안 했을 때 확정 | 잠긴다 (빈 구간 교체는 삭제다) | **허용한다** |

마지막 줄이 중요하다. 016 이 확정을 잠근 이유는 교체가 조용한 삭제가 되기 때문인데,
이 모듈은 교체하지 않으므로 그 위험이 없다. 같은 규칙을 베끼면 「AI 에게 물어만 보고
그만두기」가 막힌다.

## 이 모듈은 세션을 모른다

순수 데이터와 순수 함수다. 어디에 보관할지·언제 이벤트를 낼지는 호출자
(`itb.api.routes.sessions`)의 사정이다 — `rerecord.py` 와 같은 판단이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from itb.domain.step import Step
from itb.execution.step_edits import EditResult, delete_steps, restore_step


class TransactionSettledError(Exception):
    """이미 끝난 트랜잭션에 확정·버리기를 다시 걸었다.

    연타 방지다. 버리기의 되맞춤 실행이 도는 중에 한 번 더 눌리면 실행이 겹친다.
    """

    def __init__(self) -> None:
        super().__init__("이 Step 수정은 이미 끝났습니다.")


@dataclass(slots=True)
class StepEditTransaction:
    """진행 중인 Step 수정 하나. 세션당 최대 하나.

    「이번 세션이 만든 Step」은 016 과 같은 방식으로 **도출**한다 — 시작 시점 id 집합에
    없으면 이번에 만든 것이다. 생성 경로가 둘(리코더 sink · 손 삽입)이고 하나를 놓치면
    조용히 깨지기 때문이다 (016 `baseline_ids` 주석).

    `origin` 만이 016 에 없는 필드이고, 그것이 이 기능의 전부다.
    """

    target_id: str
    """사용자가 고른 Step 의 **식별자**.

    순번이 아닌 이유는 수정 중 앞에 Step 이 끼워지면 순번이 밀리기 때문이다 (016 이
    구간을 id 로 잡은 것과 같은 근거).
    """

    origin: Step
    """대상의 **시작 시점 사본**. 되돌리기의 근거다 (FR-020).

    016 이 피한 「내용의 복사본」이 바로 이것이지만, 범위가 **Step 하나**이므로 016 이
    걱정한 비용(정의 전체를 떠 두고 나중에 비교하는 일)이 발생하지 않는다. 비교하지도
    않는다 — 되돌릴 때 그대로 놓을 뿐이다.
    """

    arrival_index: int
    """도착점. 대상의 **시작 시점** 순번 (0-based).

    시작 시점 값을 고정해 두는 이유는 016 과 같다 — 버리기 시점에 다시 계산하면 그 사이
    삽입된 Step 때문에 값이 밀려 엉뚱한 곳에 멈춘다. 지워진 대상을 **되끼울 자리**이기도
    하다.
    """

    baseline_ids: frozenset[str] = field(default_factory=frozenset)
    """수정 **시작 시점**에 목록에 있던 Step 의 id."""

    settled: bool = False

    def created(self, steps: list[Step]) -> list[str]:
        """이번 세션이 만든 Step — **목록 순서로**."""
        return [s.id for s in steps if s.id not in self.baseline_ids]

    def can_commit(self, steps: list[Step]) -> bool:
        """확정할 수 있는가.

        **만든 것이 없어도 참이다** (research R5). 016 과 갈리는 자리이며, 인자를 받는
        모양을 유지하는 이유는 화면이 016 과 같은 통로로 판정을 받기 때문이다.
        """
        del steps  # 판정에 쓰지 않는다 — 시그니처는 016 과 맞춘다
        return not self.settled

    def owns(self, step_id: str, steps: list[Step]) -> bool:
        """AI 가 고칠 수 있는 Step 인가 (FR-013 · 불변식 A).

        **목록에 있어야 한다.** 목록에 아예 없는 id 는 대상이든 아니든 거짓이다 —
        지워진 Step 을 고치라는 요청은 범위 문제가 아니라 대상 부재다 (016 과 같다).
        """
        if not any(s.id == step_id for s in steps):
            return False
        return step_id == self.target_id or step_id not in self.baseline_ids

    def _guard(self) -> None:
        if self.settled:
            raise TransactionSettledError

    def commit(self, steps: list[Step], current_step_index: int) -> EditResult:
        """확정 — **아무 Step 도 지우지 않는다** (FR-021 · research R5).

        수정은 일어나는 즉시 목록에 적용돼 있다. 확정이 하는 일은 「이제 되돌릴 수 없다」를
        선언하는 것뿐이고, 그래서 결과는 지금 목록 그대로다.

        트랜잭션을 닫는 것은 호출자가 결과를 반영한 **뒤**다 — 016 과 같은 규칙이다.
        """
        self._guard()
        return EditResult(list(steps), current_step_index, [], at_index=self.arrival_index)

    def discard(self, steps: list[Step], current_step_index: int) -> EditResult:
        """버리기 — 이번에 만든 것을 지우고 대상을 원본으로 되돌린다 (FR-022 · 불변식 B).

        ## 하나의 결과로 돌려준다 (research R7)

        호출자가 `delete_steps` 를 적용하고 이어서 `restore_step` 을 적용하면, 사이에서
        실패했을 때 **새 Step 은 사라졌는데 대상은 고쳐진 채** 남는다. 그 상태는 시작
        전도 아니고 수정 후도 아니다.

        ## 먼저 지우고 나중에 되돌린다

        반대로 하면 복원으로 목록이 밀린 뒤의 인덱스로 삭제해야 하고, 그 계산이 한 군데
        더 생긴다. 지우기가 먼저면 대상의 자리는 시작 시점 기준 그대로다.
        """
        self._guard()
        cleared = delete_steps(steps, current_step_index, self.created(steps))
        restored = restore_step(
            cleared.steps,
            cleared.current_step_index,
            self.origin,
            self.arrival_index,
        )
        # 경고는 두 걸음에서 모두 나올 수 있다. 같은 문장이 겹치지 않게 순서를 지켜 합친다
        # — 011 FR-382 가 「같은 문장이 쌓이면 알림이 그것으로 덮인다」고 적은 것과 같다.
        warnings = list(cleared.warnings)
        for message in restored.warnings:
            if message not in warnings:
                warnings.append(message)
        return EditResult(
            restored.steps,
            restored.current_step_index,
            warnings,
            at_index=restored.at_index,
        )

    def close(self) -> None:
        """끝났음을 표시한다. 호출자가 결과를 반영한 뒤에 부른다."""
        self.settled = True
