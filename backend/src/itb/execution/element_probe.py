"""요소 후보 수집·검증의 실행 측 단일 지점. 헌법 원칙 IV (FR-017·FR-019b).

리코더가 녹화 중에 하는 일과, 편집·다시 집기·AI 도구가 하는 일이 **같은 코드**를 지나야
한다. 갈라지면 같은 요소에 대해 녹화된 Step 과 편집으로 만든 Step 이 다른 후보를 갖게
되고, 원칙 IV 의 "단일 지점" 이 우선순위 해석에만 적용되어 수집 규칙에서 무너진다.

수집 규칙 자체(무엇을 후보로 볼 것인가)는 주입 스크립트의 `describe()` 에 있고, 이 모듈은
그것을 불러 `TargetLocator` 로 만들고 **즉시 검증**한다. 검증이 기록 시점에 일어나야
`StepInspector` 표시가 추측이 아니게 되고 SC-008 을 그 자리에서 측정할 수 있다.
"""

from __future__ import annotations

import contextlib
from typing import Any

from playwright.async_api import ElementHandle, Page

from itb.domain.locator import CandidateStatus, TargetLocator
from itb.locator.collector import apply_statuses, build_unverified, candidate_strategies, classify
from itb.locator.strategy import LocatorStrategy, StrategyKind


async def describe_element(page: Page, selector: str) -> dict[str, Any] | None:
    """CSS 셀렉터로 요소 설명을 얻는다. 없으면 None.

    주입 스크립트의 `window.__itbDescribe` 를 호출한다 — 수집 규칙을 Python 에 복제하지
    않기 위해서다. 스크립트가 아직 주입되지 않았거나 페이지가 사라지는 중이면 None.
    """
    try:
        result = await page.evaluate(
            "(sel) => (typeof window.__itbDescribe === 'function'"
            " ? window.__itbDescribe(sel) : null)",
            selector,
        )
    except Exception:  # noqa: BLE001 - 문서가 교체되는 중이면 읽을 수 없다
        return None
    return result if isinstance(result, dict) else None


async def verify_candidate(
    page: Page, strategy: LocatorStrategy, anchor: ElementHandle | None
) -> CandidateStatus:
    """후보 하나를 실제로 찾아 상태를 판정한다 (data-model §6).

    `anchor` 는 "그 요소" 의 기준이다. 없으면 매칭이 1개여도 같은 요소인지 확인할 수 없어
    `UNVERIFIED` 로 남는다 — 확인하지 못한 것을 확인된 것으로 적지 않는다.
    """
    from itb.execution.locator_runtime import to_locator

    try:
        locator = to_locator(page, strategy)
        count = await locator.count()
    except Exception:  # noqa: BLE001 - 잘못된 셀렉터는 미수집으로 본다
        return CandidateStatus.NOT_COLLECTED

    if count != 1:
        return classify(count, same_element=False)
    if anchor is None:
        return CandidateStatus.UNVERIFIED
    try:
        other = await locator.element_handle()
        same = await page.evaluate("([a, b]) => a === b", [anchor, other])
    except Exception:  # noqa: BLE001
        return CandidateStatus.UNVERIFIED
    return classify(1, same_element=bool(same))


async def collect_and_verify(
    page: Page, element: dict[str, Any], test_id_attribute: str = "data-testid"
) -> TargetLocator | None:
    """요소 설명에서 후보를 만들고 즉시 검증한다. 식별 정보가 전혀 없으면 None."""
    try:
        target = build_unverified(element, test_id_attribute)
    except ValueError:
        # CSS 조차 없다. `TargetLocator` 불변식이 거절한 경우이며 기록할 수 없다.
        return None

    anchor = await _anchor(page, element, target.css.value if target.css else None)

    # **동작 시점에 페이지 안에서 잰 결과를 우선한다** (CSS·testId 에 한해).
    # 클릭이 화면 이동을 유발하면 여기서 다시 재는 시점에는 문서가 이미 교체돼 있어 모든
    # 후보가 미수집으로 나온다. 그 결과를 그대로 적으면 저장된 Step 이 재실행 불가가 된다.
    # 주입 스크립트는 동작이 일어난 그 순간에 쟀으므로 그 값이 더 참에 가깝다.
    at_action = _statuses_from_payload(element)

    statuses: dict[StrategyKind, CandidateStatus] = {}
    for kind, strategy in candidate_strategies(target):
        if kind in at_action:
            statuses[kind] = at_action[kind]
            continue
        statuses[kind] = await verify_candidate(page, strategy, anchor)
    return apply_statuses(target, statuses)


async def _anchor(
    page: Page, element: dict[str, Any], css: str | None
) -> ElementHandle | None:
    """후보 검증의 기준 요소. **주입 스크립트가 남긴 참조를 우선한다.**

    CSS 로 다시 찾으면 그 후보가 여러 요소를 매칭할 때 **다른 요소**가 기준이 된다. 그러면
    맞는 `role`·`text` 후보가 "다른 요소를 가리킨다" 로 판정되어 `UNVERIFIED` 로 버려진다.
    실측에서 같은 구조가 두 번 나오는 화면의 버튼이 확보 후보 0개로 기록됐고, 그 Step 은
    재실행에서 반드시 실패했다.

    참조가 없거나(구버전 페이로드, 문서 교체) 이미 회수됐으면 CSS 재조회로 떨어진다 —
    기준이 없으면 검증은 `UNVERIFIED` 로 남지, 확인하지 못한 것을 확인된 것으로 적지 않는다.
    """
    ref = element.get("ref")
    if isinstance(ref, str) and ref:
        with contextlib.suppress(Exception):
            handle = await page.evaluate_handle(
                "(token) => (typeof window.__itbResolveRef === 'function'"
                " ? window.__itbResolveRef(token) : null)",
                ref,
            )
            resolved = handle.as_element()
            if resolved is not None:
                return resolved
    if css:
        with contextlib.suppress(Exception):
            return await page.query_selector(css)
    return None


_PAYLOAD_KINDS: dict[str, StrategyKind] = {
    "css": StrategyKind.CSS,
    "test_id": StrategyKind.TEST_ID,
}
"""주입 스크립트가 스스로 검증하는 후보. `querySelectorAll` 과 Playwright 의 해석이
정확히 같은 둘만이다 — `role`·`label`·`text` 는 Playwright 고유 매칭 규칙을 쓰므로
페이지 안에서 근사하면 다른 요소를 `verified` 로 적을 수 있다."""


def _statuses_from_payload(element: dict[str, Any]) -> dict[StrategyKind, CandidateStatus]:
    """주입 스크립트가 보낸 검증 결과를 읽는다. 값이 없으면 빈 사전."""
    raw = element.get("verified")
    if not isinstance(raw, dict):
        return {}
    out: dict[StrategyKind, CandidateStatus] = {}
    for key, kind in _PAYLOAD_KINDS.items():
        value = raw.get(key)
        if not isinstance(value, str):
            continue
        try:
            out[kind] = CandidateStatus(value)
        except ValueError:  # 알 수 없는 값은 신뢰하지 않는다
            continue
    return out


async def collect_by_selector(
    page: Page, selector: str, test_id_attribute: str = "data-testid"
) -> TargetLocator | None:
    """셀렉터 하나로 후보 묶음을 만든다. 편집·다시 집기·검증 추가의 공통 진입점."""
    element = await describe_element(page, selector)
    if element is None:
        return None
    return await collect_and_verify(page, element, test_id_attribute)
