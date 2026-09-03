"""`LocatorStrategy` → Playwright `Locator`. 헌법 원칙 IV (FR-018·FR-021·FR-022).

`itb.locator.strategy` 가 **무엇으로 찾을지**를 정하고, 이 모듈이 **그것을 Playwright 로
어떻게 표현할지**만 담당한다. 우선순위 로직은 여기 없다 — 있으면 Generator 와 갈라진다.

**실측 반영 (research R4, T007)**: `get_by_role(name=...)` 과 `get_by_text` 의 기본 매칭은
**부분 일치**다. `exact=True` 를 붙이지 않으면 대체 후보가 조용히 다른 요소를 잡아 테스트가
잘못된 대상에 대해 통과할 수 있다 — 실패보다 나쁜 결과다.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from playwright.async_api import Locator, Page

from itb.domain.locator import TargetLocator
from itb.domain.run_result import LocatorAttempt
from itb.locator.strategy import LocatorStrategy, StrategyKind, ordered_strategies


class ElementNotFoundError(Exception):
    """모든 후보로 요소를 찾지 못했다. 시도 내역을 함께 들고 있다 (FR-021)."""

    def __init__(self, message: str, attempts: list[LocatorAttempt]) -> None:
        super().__init__(message)
        self.attempts = attempts


@dataclass(slots=True)
class Resolution:
    """요소 탐색 결과."""

    locator: Locator
    strategy: LocatorStrategy
    attempts: list[LocatorAttempt]
    disagreement: list[str]
    """후보들이 서로 다른 요소를 가리킨 경우의 기록 (spec 엣지 케이스)."""


def to_locator(page: Page, strategy: LocatorStrategy) -> Locator:
    """전략을 Playwright `Locator` 로 바꾼다. 순수 변환이며 대기하지 않는다."""
    args = strategy.args
    match strategy.kind:
        case StrategyKind.TEST_ID:
            return page.get_by_test_id(args["test_id"])
        case StrategyKind.ROLE:
            return page.get_by_role(
                args["role"],  # type: ignore[arg-type]
                name=args["name"],
                exact=strategy.exact,
            )
        case StrategyKind.LABEL:
            return page.get_by_label(args["label"], exact=strategy.exact)
        case StrategyKind.TEXT:
            return page.get_by_text(args["text"], exact=strategy.exact)
        case StrategyKind.STABLE_ATTR:
            name = args["name"].replace('"', '\\"')
            value = args["value"].replace('"', '\\"')
            return page.locator(f'[{name}="{value}"]')
        case StrategyKind.CSS:
            return page.locator(args["css"])


async def resolve(
    page: Page, target: TargetLocator, timeout_ms: int
) -> Resolution:
    """우선순위대로 요소를 찾는다.

    알고리즘 (research R4):

    1. 각 후보에 대해 **대기 없이** `count()` 를 확인한다 (실측 5종 총 5.1ms).
    2. 정확히 1개를 매칭하는 첫 후보를 채택한다.
    3. 어느 후보도 즉시 매칭되지 않으면 — 요소가 늦게 나타날 수 있다 — 최상위 후보에
       **남은 예산 전체**를 걸고 기다린다. 후보마다 예산을 나누면 모두 함께 실패한다.
    4. 후보들이 서로 다른 요소를 가리키면 불일치를 기록한다.
    """
    strategies = ordered_strategies(target)
    if not strategies:
        msg = (
            "이 Step 에 사용할 수 있는 요소 식별 후보가 없습니다. "
            "모든 후보가 미수집·모호·검증 실패 상태입니다. Step 상세에서 다시 집으세요."
        )
        raise ElementNotFoundError(msg, [])

    started = time.monotonic()
    attempts: list[LocatorAttempt] = []
    matched: list[tuple[LocatorStrategy, Locator]] = []

    # 1~2단계: 즉시 확인
    for strategy in strategies:
        locator = to_locator(page, strategy)
        try:
            count = await locator.count()
        except Exception:  # noqa: BLE001 - 잘못된 셀렉터
            count = 0
        attempts.append(
            LocatorAttempt(
                candidate=strategy.kind.value,
                expression=strategy.describe(),
                matched=count == 1,
                match_count=count,
                waited_ms=0,
            )
        )
        if count == 1:
            matched.append((strategy, locator))

    disagreement = await _detect_disagreement(page, matched)

    if matched:
        strategy, locator = matched[0]
        return Resolution(
            locator=locator,
            strategy=strategy,
            attempts=attempts,
            disagreement=disagreement,
        )

    # 3단계: 최상위 후보에 남은 예산을 집중한다
    elapsed_ms = int((time.monotonic() - started) * 1000)
    remaining = max(timeout_ms - elapsed_ms, 0)
    top = strategies[0]
    locator = to_locator(page, top)
    if remaining > 0:
        try:
            await locator.first.wait_for(state="attached", timeout=remaining)
            attempts[0] = LocatorAttempt(
                candidate=top.kind.value,
                expression=top.describe(),
                matched=True,
                match_count=await locator.count(),
                waited_ms=remaining,
            )
            return Resolution(
                locator=locator.first,
                strategy=top,
                attempts=attempts,
                disagreement=disagreement,
            )
        except Exception:  # noqa: BLE001 - 대기 시간 초과
            attempts[0] = LocatorAttempt(
                candidate=top.kind.value,
                expression=top.describe(),
                matched=False,
                match_count=0,
                waited_ms=remaining,
            )

    tried = ", ".join(a.expression for a in attempts)
    msg = f"요소를 찾을 수 없습니다. 시도한 식별 정보: {tried}"
    raise ElementNotFoundError(msg, attempts)


async def _detect_disagreement(
    page: Page, matched: list[tuple[LocatorStrategy, Locator]]
) -> list[str]:
    """후보들이 서로 다른 요소를 가리키는지 확인한다.

    실행은 최상위 후보 결과로 진행하되, 불일치를 실행 로그에 남긴다 — 나중에 테스트가
    엉뚱한 요소에 대해 통과했을 때 원인을 찾을 수 있는 유일한 단서다.
    """
    if len(matched) < 2:
        return []
    try:
        handles = await asyncio.gather(
            *(locator.element_handle() for _, locator in matched)
        )
    except Exception:  # noqa: BLE001
        return []

    first = handles[0]
    notes: list[str] = []
    for (strategy, _), handle in zip(matched[1:], handles[1:], strict=False):
        try:
            same = await page.evaluate("([a, b]) => a === b", [first, handle])
        except Exception as exc:  # noqa: BLE001 - 비교 실패도 기록으로 남긴다
            # 헌법 보안 요건: 예외를 조용히 삼키지 않는다. 비교하지 못했다는 사실 자체가
            # 진단 정보다 — 조용히 넘기면 불일치가 없었던 것처럼 보인다.
            notes.append(
                f"{strategy.kind.value} 후보를 최상위 후보와 비교하지 못했습니다: "
                f"{type(exc).__name__}"
            )
            continue
        if not same:
            notes.append(
                f"{matched[0][0].kind.value} 와 {strategy.kind.value} 후보가 "
                "서로 다른 요소를 가리킵니다."
            )
    return notes
