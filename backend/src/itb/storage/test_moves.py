"""여러 자산을 옮기면서 「전부 되거나 전부 안 되거나」를 지킨다. 013 FR-432·FR-444b.

**삭제와 그룹 이동이 같은 규약을 쓴다.** 라우트마다 따로 두면 두 벌이 되고, 한쪽만 고치면
다른 쪽에서 되돌림이 빠진다 — 그리고 되돌림이 빠진 쪽은 사고가 나야 드러난다.

## 왜 여기서 원자성을 흉내 낼 수 있는가

파일 시스템에는 여러 경로에 걸친 원자적 연산이 없다. 011 의 Step 복수 삭제는 판정이 **메모리
안**에서 끝나 원자성이 공짜였지만 (`api/routes/steps.py` 의 `remove_many`), 여기서는 그렇지
않다.

**삭제를 휴지통 이동으로 정한 결정이 이것을 가능하게 했다** (013 research R4). 삭제가
파괴가 아니라 **이동**이므로 되돌릴 수 있다. 영구 삭제였다면 「셋 중 둘만 지워진 채 오류」가
구조적으로 피할 수 없는 상태였다.

## 세 걸음

1. **먼저 전부 검증한다.** 하나라도 걸리면 아무것도 건드리지 않고 예외를 그대로 올린다.
   실패의 대부분이 여기서 걸린다 — 존재하지 않음, 실행 중.
2. **하나씩 실행한다.** 한 것을 기억한다.
3. **도중에 실패하면 이미 한 것을 되돌린다.** 되돌리기도 실패하면 **그 사실을 삼키지 않고**
   :class:`PartialFailureError` 로 알린다.

3번이 갈라져 있는 이유는 **사용자가 할 일이 다르기 때문**이다. 되돌렸으면 요청 전과 같으니
다시 시도하면 되고, 되돌리지 못했으면 어디에 무엇이 있는지 확인해야 한다.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Stranded:
    """되돌리지 못한 것 하나. 사용자에게 **어디 있는지** 알리기 위한 것이다."""

    target: str
    where: str


class AllOrNothingError(Exception):
    """도중에 실패했고 **이미 한 것을 전부 되돌렸다.**

    디스크는 요청 전과 같다. 호출자는 이것을 「아무 일도 일어나지 않았다」로 다뤄야 한다.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PartialFailureError(Exception):
    """도중에 실패했고 **되돌리지도 못했다.**

    파괴는 일어나지 않았다 — 모든 자산은 새 자리 아니면 원래 자리에 있다. 어느 쪽인지를
    :attr:`stranded` 가 말한다. 이것을 :class:`AllOrNothingError` 와 뭉치면 사용자는
    「다시 시도하면 되는가」에 답할 수 없다.
    """

    def __init__(self, reason: str, stranded: list[Stranded]) -> None:
        super().__init__(reason)
        self.reason = reason
        self.stranded = stranded


@dataclass(slots=True)
class _Applied:
    target: object
    result: object = field(default=None)


def run_all[T, R](
    targets: Sequence[T],
    *,
    validate: Callable[[T], None],
    do: Callable[[T], R],
    undo: Callable[[T, R], None],
) -> list[R]:
    """세 걸음을 실행하고 결과 목록을 돌려준다.

    `validate` 가 올린 예외는 **그대로 올라간다** — 무엇이 막았는지는 호출자가 안다
    (없는 테스트인지 실행 중인지). 이 단계에서는 아무것도 건드리지 않았으므로 되돌릴 것도
    없다.

    `do` 가 실패하면 `undo` 로 되돌리고 :class:`AllOrNothingError` 를 올린다. `undo` 까지
    실패하면 :class:`PartialFailureError` 다.
    """
    for target in targets:
        validate(target)

    applied: list[_Applied] = []
    for target in targets:
        try:
            applied.append(_Applied(target, do(target)))
        except Exception as exc:  # noqa: BLE001 — 무엇이든 되돌리고 사유를 나른다
            stranded = _rollback(applied, undo)
            if stranded:
                msg = f"{exc}. 이미 옮긴 것을 되돌리지 못했습니다."
                raise PartialFailureError(msg, stranded) from exc
            raise AllOrNothingError(str(exc)) from exc

    return [a.result for a in applied]  # type: ignore[misc]


def _rollback[T, R](applied: list[_Applied], undo: Callable[[T, R], None]) -> list[Stranded]:
    """되돌린다. **역순으로** 한다 — 나중에 한 것이 앞의 것에 기대고 있을 수 있다.

    되돌리기가 실패해도 **멈추지 않는다.** 남은 것들은 되돌릴 수 있을지 모르고, 하나가
    막혔다고 나머지를 포기하면 되돌릴 수 있었던 것까지 새 자리에 남는다.
    """
    stranded: list[Stranded] = []
    for item in reversed(applied):
        try:
            undo(item.target, item.result)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001, PERF203 — 되돌리기 실패도 결과의 일부다
            stranded.append(Stranded(target=str(item.target), where=str(item.result)))
    return stranded
