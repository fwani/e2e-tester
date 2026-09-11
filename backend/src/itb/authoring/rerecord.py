"""구간 교체 트랜잭션. 016 FR-015·FR-016·FR-023~FR-030 (T008, research R7).

## 스냅샷이 없다

되돌리기를 다루는 모듈인데 원본 복사본을 만들지 않는다. **FR-037 이 AI 의 편집 권한을
「이번 세션이 만든 Step」으로 한정했기 때문이다** — 그래서 재녹화가 도는 동안 옛 구간과
구간 밖은 바뀌지 않는다. 바뀌지 않는 것을 복사해 두고 나중에 같은지 비교하는 것은 일이
아니라 의식이다.

남는 것은 id 집합 둘이고, 두 결말이 **같은 함수의 다른 인자**가 된다.

    확정 → delete_steps(steps, range.step_ids)   옛 구간이 사라진다
    버리기 → delete_steps(steps, created(steps)) 새 것이 사라진다 = 시작 전과 같다

「이번에 만든 것」은 기록하지 않고 **도출한다** — 시작 시점 id 집합에 없으면 만든
것이다. 생성 경로가 둘(리코더 sink·손 삽입)이고 하나를 놓치면 조용히 깨지기 때문이다
(`baseline_ids` 주석 참조).

`delete_steps` 는 011 FR-388 의 **전부-또는-전무**를 보장한다. 검증에서 걸리면 아무것도
만들지 않으므로 부분 적용이 남지 않는다 (FR-026·FR-027).

## 구간은 순번이 아니라 id 로 잡는다

재녹화 도중 새 Step 이 구간 시작 위치에 삽입되므로 옛 구간의 **순번은 계속 밀린다.**
순번으로 들면 삽입마다 다시 계산해야 하고, 한 번 어긋나면 확정이 엉뚱한 Step 을 지운다.

## 이 모듈은 세션을 모른다

순수 데이터와 순수 함수다. 어디에 보관할지·언제 이벤트를 낼지는 호출자
(`itb.api.routes.sessions`)의 사정이다 — `StepCompiler` 가 「어디에 넣을지는 세션의
사정」이라고 적은 것과 같은 판단이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from itb.domain.step import Step
from itb.execution.step_edits import EditResult, delete_steps, find_index


class RangeNotContiguousError(Exception):
    """고른 Step 이 목록에서 이어져 있지 않다 (FR-016).

    불연속을 허용하지 않는 이유는 **도착점이 하나여야 하기 때문**이다. 3번과 7번을
    고르면 화면을 3 직전으로 되돌려야 하는지 7 직전으로 되돌려야 하는지 정할 수 없고,
    사이에 낀 4~6 을 새 Step 과 어떻게 이을지도 정의되지 않는다.
    """

    def __init__(self, step_ids: list[str]) -> None:
        self.step_ids = step_ids
        super().__init__(
            "고른 Step 이 이어져 있지 않습니다. 재녹화는 연속한 구간에만 할 수 있습니다."
        )


class EmptyRangeError(Exception):
    """구간이 비어 있다 (FR-015)."""

    def __init__(self) -> None:
        super().__init__("다시 만들 Step 을 하나 이상 고르세요.")


class NothingCreatedError(Exception):
    """만든 Step 이 없는데 확정하려 했다 (FR-028 · 불변식 10).

    옛 구간을 빈 것으로 바꾸는 것은 **구간 삭제**이고, 그것은 이미 있는 조작이다
    (`step.deleteSelected`). 재녹화 버튼으로 삭제가 일어나면 사용자는 무엇이 지워질지
    예측할 수 없다.
    """

    def __init__(self) -> None:
        super().__init__(
            "아직 만들어진 Step 이 없습니다. 지시를 보내 Step 을 먼저 만드세요."
        )


class TransactionSettledError(Exception):
    """이미 끝난 트랜잭션에 확정·버리기를 다시 걸었다.

    연타 방지다. 버리기의 되맞춤 실행이 도는 중에 한 번 더 눌리면 실행이 겹친다.
    """

    def __init__(self) -> None:
        super().__init__("이 재녹화는 이미 끝났습니다.")


@dataclass(frozen=True, slots=True)
class StepRange:
    """교체 대상 구간. **연속**이며 비어 있지 않다."""

    step_ids: tuple[str, ...]

    @property
    def first(self) -> str:
        return self.step_ids[0]

    def __len__(self) -> int:
        return len(self.step_ids)


def validate_range(steps: list[Step], step_ids: list[str]) -> StepRange:
    """구간을 경계에서 검증한다 (FR-015·FR-016).

    **존재 검증은 `find_index` 에 맡긴다** — 없으면 `StepNotFoundError` 가 나간다.
    여기서 또 확인하면 「없는 Step」의 판정이 두 곳에 생긴다.

    받은 순서가 목록 순서와 달라도 된다 (화면의 체크 순서는 사용자가 누른 순서다).
    정렬해서 연속인지만 본다.
    """
    if not step_ids:
        raise EmptyRangeError

    indices = sorted(find_index(steps, sid) for sid in step_ids)
    if len(set(indices)) != len(indices):
        # 같은 Step 을 두 번 고른 것. `delete_steps` 도 이것을 거절하므로 같은 규칙이다.
        raise RangeNotContiguousError(step_ids)
    if indices[-1] - indices[0] != len(indices) - 1:
        raise RangeNotContiguousError(step_ids)

    return StepRange(tuple(steps[i].id for i in indices))


@dataclass(slots=True)
class RerecordTransaction:
    """진행 중인 구간 교체 하나. 세션당 최대 하나.

    「이번 세션이 만든 Step」은 두 가지로 쓰인다:

    1. 버리기의 대상 (FR-027)
    2. AI 편집 도구의 권한 범위 (FR-037 · 불변식 8)

    2번이 1번을 성립시킨다. 권한이 그 집합으로 한정되므로 다른 Step 이 바뀌지 않고,
    바뀌지 않으므로 그것만 지우면 시작 전과 같아진다 (불변식 9).
    """

    range: StepRange
    arrival_index: int
    """도착점. 구간 첫 Step 의 **시작 시점** 순번 (0-based).

    시작 시점 값을 고정해 두는 이유는 되맞춤(FR-031) 때문이다. 버리기 시점에 다시
    계산하면 그 사이 삽입된 Step 때문에 값이 밀려 엉뚱한 곳에 멈춘다.
    """

    baseline_ids: frozenset[str] = frozenset()
    """재녹화 **시작 시점**에 목록에 있던 Step 의 id.

    ## 왜 「만든 것을 기록」이 아니라 「있던 것을 기억」인가

    초안은 생성 지점마다 `record(step_id)` 를 부르는 방식이었다. 구현하다 깨졌다 —
    Step 이 만들어지는 길이 **둘**이었기 때문이다:

      1. `_accept_step` — 리코더 sink 와 AI 컴파일러가 지난다
      2. `itb.api.routes.steps` 의 삽입 — 손으로 넣는 Step (009 FR-285)

    2번을 놓쳤고, 그래서 손으로 넣은 Step 이 권한 범위 밖에 남아 확정이 「만든 것이
    없다」로 거절됐다. **길을 하나 더 놓치면 같은 일이 또 일어난다.**

    시작 시점 id 를 기억하면 길을 셀 필요가 없다 — 지금 목록에 있는데 그때 없었으면
    이번 세션이 만든 것이다. 새 경로가 생겨도 자동으로 덮인다.

    **research R7 의 「스냅샷을 만들지 않는다」와 어긋나지 않는다.** 그 판단이 거절한
    것은 **내용의 복사본**(되돌릴 때 비교하려고 목록을 통째로 떠 두는 것)이고, 이것은
    id 집합이다. 되돌리기는 여전히 `delete_steps` 한 번이다.
    """

    settled: bool = False

    def created(self, steps: list[Step]) -> list[str]:
        """이번 세션이 만든 Step — **목록 순서로** (불변식 8·9).

        순서를 목록에서 가져오는 이유는 `delete_steps` 가 순서를 보지 않기 때문이 아니라,
        사용자에게 보이는 순서와 같아야 하기 때문이다 (화면이 「새로 만든 것 3개」를
        센다).
        """
        return [s.id for s in steps if s.id not in self.baseline_ids]

    def can_commit(self, steps: list[Step]) -> bool:
        """확정할 수 있는가 (불변식 10).

        **서버가 판정한다.** 화면이 조건을 복제하면 서버와 갈리고, 갈리면 활성으로 그린
        버튼이 눌린 뒤 거절된다 (005 U-01 의 형태).
        """
        return not self.settled and bool(self.created(steps))

    def owns(self, step_id: str, steps: list[Step]) -> bool:
        """AI 가 고칠 수 있는 Step 인가 (불변식 8).

        **목록에 있으면서 시작 시점에 없던 것**만 참이다. 목록에 아예 없는 id 는 거짓이다
        — 지워진 Step 을 고치라는 요청은 범위 문제가 아니라 대상 부재다.
        """
        return step_id not in self.baseline_ids and any(s.id == step_id for s in steps)

    def _guard(self) -> None:
        if self.settled:
            raise TransactionSettledError

    def commit(self, steps: list[Step], current_step_index: int) -> EditResult:
        """확정 — 옛 구간을 **한 번에** 지운다 (FR-026).

        트랜잭션을 닫는 것은 호출자가 결과를 반영한 **뒤**다. 여기서 먼저 닫으면 삭제가
        실패했을 때 되돌릴 수도 다시 시도할 수도 없는 상태가 남는다.
        """
        self._guard()
        if not self.created(steps):
            raise NothingCreatedError
        return delete_steps(steps, current_step_index, list(self.range.step_ids))

    def discard(self, steps: list[Step], current_step_index: int) -> EditResult:
        """버리기 — 이번에 만든 것을 **한 번에** 지운다 (FR-027 · 불변식 9).

        **만든 것이 없어도 허용한다.** 아무것도 만들지 않은 채 그만두는 것은 정상이고,
        그때 결과는 목록 그대로다 (`delete_steps` 가 빈 목록에 아무것도 하지 않는다).
        """
        self._guard()
        return delete_steps(steps, current_step_index, self.created(steps))

    def close(self) -> None:
        """끝났음을 표시한다. 호출자가 결과를 반영한 뒤에 부른다."""
        self.settled = True
