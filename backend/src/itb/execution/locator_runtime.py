"""`LocatorStrategy` → Playwright `Locator`. 헌법 원칙 IV (FR-018·FR-021·FR-022).

`itb.locator.strategy` 가 **무엇으로 찾을지**를 정하고, 이 모듈이 **그것을 Playwright 로
어떻게 표현할지**만 담당한다. 우선순위 로직은 여기 없다 — 있으면 Generator 와 갈라진다.

**실측 반영 (research R4, T007)**: `get_by_role(name=...)` 과 `get_by_text` 의 기본 매칭은
**부분 일치**다. `exact=True` 를 붙이지 않으면 대체 후보가 조용히 다른 요소를 잡아 테스트가
잘못된 대상에 대해 통과할 수 있다 — 실패보다 나쁜 결과다.

**004 재작성**: 요소를 **폴링으로** 찾는다. 이전에는 후보 전체를 대기 없이 한 번 확인한 뒤
최상위 후보 하나에만 남은 예산 전체를 걸었다. 그 결과 하위 후보로만 늦게 나타나는 요소는
한 번도 다시 확인되지 않았고, 사용자에게는 "데이터가 로딩 중인데 요소가 없다는 에러" 로
보였다 (004 research R1 실측: 5004ms 실패 → 폴링 시 2089ms 통과).

함께 제거한 것이 `locator.first.wait_for(state="attached")` 폴백이다. 후보가 여러 요소를
매칭하면 `.first` 는 이미 붙어 있으므로 즉시 반환했고, 로딩 중 스켈레톤을 채택했다
(research R2 실측: 28ms 통과). 1~2단계의 `count()==1` 엄격 검사가 3단계에서 무효화되는
구조적 모순이었다.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from playwright.async_api import Locator, Page

from itb.domain.locator import TargetLocator
from itb.domain.run_result import LocatorAttempt
from itb.locator.strategy import (
    POLL_INTERVAL_MS,
    LocatorStrategy,
    StrategyKind,
    ordered_strategies,
)

MIN_ACTION_TIMEOUT_MS = 250
"""동작 자체에 항상 남겨 두는 최소 시간.

두 곳에서 같은 뜻으로 쓴다.

- `step_executor` 는 남은 예산이 이 값 아래로 내려가도 동작에 이만큼은 준다. 0 을
  Playwright 에 넘기면 "무한 대기" 로 해석되어 상한이 사라진다 (FR-057).
- `resolve()` 는 예산이 이만큼밖에 안 남으면 **보이지 않는 매칭도 채택한다.** 더 기다려 봐야
  동작할 시간이 없고, 그때는 Playwright 의 actionability 오류가 우리 문구보다 정확하게
  원인을 말한다 (004 FR-119).

값이 한 곳에만 있어야 두 판단이 어긋나지 않는다.
"""


class ElementNotFoundError(Exception):
    """모든 후보로 요소를 찾지 못했다. 시도 내역을 함께 들고 있다 (FR-021).

    **실패의 종류를 함께 든다** (004 FR-120·FR-123). 호출부가 문구를 해석하지 않고
    분류할 수 있어야 한다 — 세 경우는 사용자가 할 일이 서로 다르다.

    - 시도할 후보가 애초에 없다 → 정의 문제. 기다려도 달라지지 않는다
    - 예산 안에 아무도 하나를 가리키지 못했다 (`timed_out`) → 화면이 느린 문제
    - 예산 안에 여러 개만 매칭됐다 (`ambiguous`) → 정의가 낡은 문제
    """

    def __init__(
        self,
        message: str,
        attempts: list[LocatorAttempt],
        *,
        timed_out: bool = False,
        waited_ms: int = 0,
        ambiguous: bool = False,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.timed_out = timed_out
        self.waited_ms = waited_ms
        self.ambiguous = ambiguous


@dataclass(slots=True)
class Resolution:
    """요소 탐색 결과."""

    locator: Locator
    strategy: LocatorStrategy
    attempts: list[LocatorAttempt]
    disagreement: list[str]
    """후보들이 서로 다른 요소를 가리킨 경우의 기록 (spec 엣지 케이스)."""

    waited_ms: int = 0
    """요소가 나타나기를 **기다린** 시간 (004 FR-114). 즉시 찾았으면 0.

    후보를 확인하는 왕복 비용은 포함하지 않는다. 이 값이 답해야 하는 질문은 "이 Step 이
    화면을 얼마나 기다렸는가" 이고, 그 답으로 사용자는 예산을 얼마로 잡을지 정한다.
    탐색 자체의 비용(후보 5종 왕복 ~15ms)을 섞으면 즉시 찾은 Step 도 0이 아닌 값을 갖게
    되어, "기다림이 있었다" 와 "없었다" 를 구별할 수 없다.
    """


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


async def resolve(page: Page, target: TargetLocator, timeout_ms: int) -> Resolution:
    """우선순위대로 요소를 찾는다. 나타날 때까지 예산 안에서 기다린다.

    알고리즘 (004 research R1~R4):

    1. 후보 **전체**를 대기 없이 확인한다 (실측 5종 14.8ms). 정확히 1개를 매칭하는 후보 중
       우선순위가 가장 높은 것을 채택 후보로 삼는다.
    2. 채택 후보가 **보이면** 즉시 반환한다. 요소가 이미 있는 정상 경로는 여기서 끝난다 —
       폴링 루프에 들어가지 않으므로 이번 변경의 비용이 0 이다 (FR-113, SC-003).
    3. 아니면 `POLL_INTERVAL_MS` 주기로 **후보 전체를 다시 확인한다.** 최상위 후보 하나에만
       예산을 걸지 않는 것이 004 가 고친 결함이다 (FR-111).
    4. 예산이 `MIN_ACTION_TIMEOUT_MS` 만큼밖에 안 남으면 보이지 않는 매칭도 채택한다.
       보이지 않는 것이 정상인 대상이 있기 때문이다 (`hidden` 검증, 화면 밖 입력란 — FR-119).
    5. 끝내 못 찾으면 **왜 못 찾았는지 구별해서** 던진다 (FR-120).

    **채택은 언제나 우선순위 순이다.** 보임 여부는 *언제 채택할지*만 정하고 *무엇을 채택할지*
    는 정하지 않는다. 보이는 하위 후보를 보이지 않는 상위 후보보다 먼저 잡으면, 기록된
    식별 정보가 가리키는 것과 다른 요소를 조작하게 된다 — 원칙 IV 가 막으려는 것이 그것이다.
    """
    strategies = ordered_strategies(target)
    if not strategies:
        msg = (
            "이 Step 에 사용할 수 있는 요소 식별 후보가 없습니다. "
            "모든 후보가 미수집·모호·검증 실패 상태입니다. Step 상세에서 다시 집으세요."
        )
        # `timed_out` 이 아니다 — 기다려도 달라지지 않는 정의 문제다 (FR-120).
        raise ElementNotFoundError(msg, [])

    started = time.monotonic()
    deadline = started + max(timeout_ms, 0) / 1000
    grace = MIN_ACTION_TIMEOUT_MS / 1000

    attempts: list[LocatorAttempt] = []
    saw_ambiguous = False

    while True:
        round_started = time.monotonic()
        waited_ms = int((round_started - started) * 1000)
        attempts, matched, round_ambiguous = await _probe_round(
            page, strategies, waited_ms
        )
        saw_ambiguous = saw_ambiguous or round_ambiguous

        if matched:
            # 우선순위가 가장 높은 매칭. 보임은 *언제* 채택할지만 정한다.
            strategy, locator = matched[0]
            out_of_time = time.monotonic() >= deadline - grace
            if out_of_time or await _is_visible(locator):
                disagreement = await _detect_disagreement(page, matched)
                return Resolution(
                    locator=locator,
                    strategy=strategy,
                    attempts=attempts,
                    disagreement=disagreement,
                    # 이 라운드를 **시작하기까지** 기다린 시간. 1라운드는 0 이다.
                    waited_ms=waited_ms,
                )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(POLL_INTERVAL_MS / 1000, remaining))

    waited_ms = int((time.monotonic() - started) * 1000)
    tried = ", ".join(a.expression for a in attempts)
    if saw_ambiguous and not any(a.matched for a in attempts):
        counts = ", ".join(
            f"{a.expression} → {a.match_count}개" for a in attempts if a.match_count > 1
        )
        msg = (
            "요소가 여러 개 매칭되어 어느 것을 조작할지 결정할 수 없습니다. "
            f"{waited_ms}ms 동안 기다렸지만 하나로 좁혀지지 않았습니다. {counts}"
        )
        raise ElementNotFoundError(
            msg, attempts, timed_out=True, waited_ms=waited_ms, ambiguous=True
        )

    msg = (
        f"요소를 찾을 수 없습니다. {waited_ms}ms 동안 모든 식별 후보를 다시 "
        f"확인했습니다. 시도한 식별 정보: {tried}"
    )
    raise ElementNotFoundError(msg, attempts, timed_out=True, waited_ms=waited_ms)


async def _probe_round(
    page: Page, strategies: list[LocatorStrategy], waited_ms: int
) -> tuple[list[LocatorAttempt], list[tuple[LocatorStrategy, Locator]], bool]:
    """후보 전체를 한 번 확인한다. (시도 내역, 우선순위 순 매칭, 모호함 있었는가).

    `waited_ms` 는 **이 라운드를 시작하기까지 기다린 시간**이다. 1라운드는 0 이며, 그것이
    "즉시 찾았다" 를 결과에서 읽을 수 있게 한다.
    """
    attempts: list[LocatorAttempt] = []
    matched: list[tuple[LocatorStrategy, Locator]] = []
    ambiguous = False

    for strategy in strategies:
        locator = to_locator(page, strategy)
        try:
            count = await locator.count()
        except Exception:  # noqa: BLE001 - 잘못된 셀렉터. 시도 내역에 0개로 남긴다
            count = 0
        attempts.append(
            LocatorAttempt(
                candidate=strategy.kind.value,
                expression=strategy.describe(),
                matched=count == 1,
                match_count=count,
                waited_ms=waited_ms,
            )
        )
        if count == 1:
            matched.append((strategy, locator))
        elif count > 1:
            ambiguous = True

    return attempts, matched, ambiguous


async def _is_visible(locator: Locator) -> bool:
    """지금 보이는가. **기다리지 않는다** — 기다림은 폴링 루프가 담당한다.

    실측 비용 4.7ms (research R7). 매칭이 있을 때만 부르므로 정상 경로에 얹히는 비용이
    SC-003 의 100ms 상한에 여유가 크다.
    """
    try:
        return await locator.is_visible()
    except Exception:  # noqa: BLE001 - 판정하지 못하면 아직 아니라고 본다
        # 조용히 삼키지 않는다: False 는 "보인다고 확인하지 못했다" 는 뜻이며, 폴링이
        # 계속되고 예산이 끝나면 어차피 채택된다. 잘못된 요소를 잡는 쪽으로 기울지 않는다.
        return False


async def _detect_disagreement(
    page: Page, matched: list[tuple[LocatorStrategy, Locator]]
) -> list[str]:
    """후보들이 서로 다른 요소를 가리키는지 확인한다.

    실행은 최상위 후보 결과로 진행하되, 불일치를 실행 로그에 남긴다 — 나중에 테스트가
    엉뚱한 요소에 대해 통과했을 때 원인을 찾을 수 있는 유일한 단서다.

    **004 재작성에서 보존해야 하는 기능이다.** 폴링으로 바꾸면서 이것이 조용히 빠지면
    회귀가 드러나지 않는다 (spec 엣지 케이스, tasks T020a).
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
