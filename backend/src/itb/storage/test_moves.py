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

import contextlib
import pathlib
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from itb.storage.repository import TEST_ID_RE

if TYPE_CHECKING:  # pragma: no cover — 순환 임포트를 피한다
    from itb.storage.repository import ProjectRepository


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


# ─── 그룹 이동 (013 FR-444a·FR-444b) ───────────────────────────────────────


class MoveError(OSError):
    """테스트를 다른 그룹으로 옮기지 못했다. 원래 자리 그대로다."""


@dataclass(frozen=True, slots=True)
class MovedTest:
    """옮겨진 테스트 하나."""

    from_id: str
    to_id: str
    name: str


def target_id(test_id: str, to_prefix: str) -> str:
    """접두어만 바꾼다. **번호는 그대로다** (013 research R3).

    번호가 프로젝트 전체에서 고유하므로 `USER-003` → `DATA-003` 은 언제나 빈자리다.
    그룹마다 번호를 매겼다면 여기서 새 번호를 뽑아야 하고 그 자리가 차 있을 수 있다 —
    FR-444c(식별자 고유)를 규칙이 아니라 **구조로** 만족시킨다.
    """
    number = test_id.split("-", 1)[1]
    return f"{to_prefix}-{number}"


def move_test_to_group(repo: ProjectRepository, test_id: str, to_prefix: str) -> MovedTest:
    """테스트 하나의 그룹을 바꾼다 (013 contracts/api-contract.md §4).

    **순서가 계약이다.**

    1. `.runs/<옛ID>/` → `.runs/<새ID>/` (있을 때만)
    2. 새 정의 파일 쓰기 (원자적, 내용의 ``id`` 도 새 값)
    3. 옛 정의 파일 지우기
    4. 2·3 이 실패하면 1을 되돌리고 새로 쓴 파일이 있으면 치운다

    **산출물이 먼저인 이유**: 반대로 하면 「테스트는 새 자리, 결과는 옛 자리」가 되어
    사용자에게는 **결과가 사라진 것**으로 보인다. 이 순서의 실패는 새 식별자 자리에
    산출물만 남기고, 그것은 목록에 나타나지 않는다 — 목록은 정의 파일에서 나온다.
    **눈에 보이지 않는 흔적이 눈에 보이는 손실보다 낫다** (013 research R5).

    **알려진 창**: 2와 3 사이에 정의 파일이 두 자리에 있다. 이 도구는 로컬 단독 실행이고
    그 사이에 목록을 읽는 다른 요청이 사실상 없다. 그래도 없는 것처럼 적지 않는다.
    """
    new_id = target_id(test_id, to_prefix)
    if not TEST_ID_RE.match(new_id):
        msg = f"만들 수 없는 식별자입니다: {new_id}"
        raise MoveError(msg)
    if repo.find_test_path(new_id) is not None:
        msg = f"이미 쓰는 식별자입니다: {new_id}"
        raise MoveError(msg)

    old_path = repo.find_test_path(test_id)
    if old_path is None:
        msg = f"테스트 정의를 찾을 수 없습니다: {test_id}"
        raise MoveError(msg)

    test = repo.read_test(test_id)
    old_runs = repo.paths.run_dir(test_id)
    new_runs = repo.paths.run_dir(new_id)
    runs_moved = False
    new_path: pathlib.Path | None = None

    try:
        if old_runs.is_dir():
            new_runs.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_runs), str(new_runs))
            runs_moved = True
        new_path = repo.write_test(test.model_copy(update={"id": new_id}))
        old_path.unlink()
    except OSError as exc:
        with contextlib.suppress(OSError):
            if new_path is not None and new_path.exists() and new_path != old_path:
                new_path.unlink()
            if runs_moved and new_runs.is_dir():
                shutil.move(str(new_runs), str(old_runs))
        msg = f"그룹을 옮기지 못했습니다: {exc.strerror or exc}"
        raise MoveError(msg) from exc

    return MovedTest(from_id=test_id, to_id=new_id, name=test.name)


def move_test_back(repo: ProjectRepository, moved: MovedTest) -> None:
    """되돌린다 — 복수 이동이 도중에 실패했을 때 쓴다 (`run_all` 의 3번 걸음)."""
    move_test_to_group(repo, moved.to_id, moved.from_id.split("-", 1)[0])
