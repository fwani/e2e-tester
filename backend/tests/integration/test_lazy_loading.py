"""004 US2 — 로딩 중인 데이터를 기다린다. FR-111~FR-119, SC-001~SC-003.

**이 파일이 고정하는 것은 사용자가 보고한 결함이다.** 004 이전 코드는 아래 절반이
실패한다. 그 실패를 Phase 0 에서 실측으로 확인했다 (research R1: 5004ms 실패).

`resolve()` 와 `StepExecutor` 를 실제 브라우저와 실제 픽스처 화면에 대고 부른다. 녹화·저장
왕복을 거치지 않는 이유는, 결함이 **요소를 찾는 순간**에 있어서 그 지점을 직접 겨눠야
실패가 무엇을 뜻하는지 분명하기 때문이다.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from itb.domain.error import ErrorCode
from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
from itb.domain.step import ClickStep
from itb.execution.locator_runtime import ElementNotFoundError, resolve
from itb.secrets.resolver import VariableResolver

VERIFIED = CandidateStatus.VERIFIED


def _resolver() -> VariableResolver:
    """변수를 쓰지 않는 해석기. 이 파일은 요소 탐색만 보므로 변수가 필요 없다."""
    return VariableResolver(SimpleNamespace(variables=[]))

LAZY_DELAY_MS = 2000
"""`lazy.html` 이 목록을 그리기까지의 시간. 픽스처의 기본값과 같아야 한다."""

LATE_VISIBLE_DELAY_MS = 1000
"""`late-visible.html` 이 버튼을 보이게 하기까지의 시간."""

BUDGET_MS = 5000
"""이 파일의 기본 대기 예산. 지연(2000ms)보다 크고 넉넉하지 않을 만큼 잡는다."""

IMMEDIATE_COST_LIMIT_MS = 100
"""SC-003 — 요소가 즉시 존재할 때 허용되는 총 소요."""


# ─── 도우미 ────────────────────────────────────────────────────────────────


def _open(client: TestClient, fixture_app: str, path: str) -> tuple[str, Any]:
    """세션을 열고 그 세션의 첫 탭 `Page` 를 돌려준다."""
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/{path}"},
    )
    assert created.status_code == 201, created.text
    sid = str(created.json()["session_id"])
    page = client.app.state.itb.sessions.require(sid).tabs[0].page  # type: ignore[attr-defined]
    return sid, page


def _call(client: TestClient, coro_factory: Any) -> Any:
    """세션의 이벤트 루프에서 코루틴을 돌린다."""
    return client.portal.call(coro_factory)  # type: ignore[attr-defined]


def _target(**kwargs: Any) -> TargetLocator:
    """검증된 후보만 가진 `TargetLocator` 를 짧게 만든다."""
    out: dict[str, Any] = {}
    if "test_id" in kwargs:
        out["test_id"] = Candidate(value=kwargs["test_id"], status=VERIFIED)
    if "role" in kwargs:
        out["role"] = kwargs["role"]
        out["accessible_name"] = kwargs["name"]
        out["role_status"] = VERIFIED
    if "text" in kwargs:
        out["text"] = Candidate(value=kwargs["text"], status=VERIFIED)
    if "css" in kwargs:
        out["css"] = Candidate(value=kwargs["css"], status=VERIFIED)
    if "attr" in kwargs:
        name, value = kwargs["attr"]
        out["stable_attr"] = StableAttr(name=name, value=value, status=VERIFIED)
    return TargetLocator(**out)


# ─── FR-111 — 모든 후보를 계속 다시 확인한다 ───────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_element_appears_after_delay(
    project_client: TestClient, fixture_app: str
) -> None:
    """SC-001 — 2초 뒤 나타나는 요소로 Step 이 통과한다.

    최상위 후보(testId)가 결국 맞는 경우다. 004 이전에도 통과했지만, 폴링으로 바꾼 뒤에도
    통과해야 한다 — 알고리즘을 바꾸면서 되던 것을 깨뜨리지 않았음을 본다.
    """
    sid, page = _open(project_client, fixture_app, "lazy.html")
    try:
        started = time.monotonic()
        found = _call(
            project_client,
            lambda: resolve(page, _target(test_id="order-detail"), BUDGET_MS),
        )
        elapsed_ms = (time.monotonic() - started) * 1000

        assert found.strategy.kind.value == "test_id"
        assert LAZY_DELAY_MS * 0.5 < elapsed_ms < BUDGET_MS, (
            f"지연({LAZY_DELAY_MS}ms)만큼 기다린 뒤 찾아야 한다. 실제 {elapsed_ms:.0f}ms"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_lower_candidate_appears_late(
    project_client: TestClient, fixture_app: str
) -> None:
    """SC-002 — **004 이전 코드가 실패하는 지점.**

    최상위 후보(testId)는 끝내 맞지 않고, 하위 후보(role+이름)만 2초 뒤에 맞는다.
    004 이전에는 예산 전체를 최상위 후보에만 걸어 5004ms 만에 실패했다 (research R1).
    """
    sid, page = _open(project_client, fixture_app, "lazy.html")
    try:
        target = _target(
            test_id="stale-testid-that-never-matches",
            role="button",
            name="주문 상세",
        )
        started = time.monotonic()
        found = _call(project_client, lambda: resolve(page, target, BUDGET_MS))
        elapsed_ms = (time.monotonic() - started) * 1000

        assert found.strategy.kind.value == "role", (
            "최상위 후보가 안 맞으면 다음 후보로 내려가야 한다"
        )
        assert elapsed_ms < BUDGET_MS, (
            f"예산을 다 쓰기 전에 찾아야 한다. 실제 {elapsed_ms:.0f}ms"
        )
    finally:
        stop_quietly(project_client, sid)


# ─── FR-112 — 보이고 조작 가능해진 뒤에 동작한다 ───────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_attached_but_invisible_waits(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-112 — DOM 에 붙어 있지만 1초 뒤 보이는 요소를 기다린 뒤 조작한다.

    `count()` 는 처음부터 1이다. DOM 존재만으로 "찾음" 을 판정하면 아직 조작할 수 없는
    요소에 동작이 수행된다.
    """
    sid, page = _open(project_client, fixture_app, "late-visible.html")
    try:
        found = _call(
            project_client,
            lambda: resolve(page, _target(test_id="send-report"), BUDGET_MS),
        )
        visible = _call(project_client, found.locator.is_visible)
        assert visible, "채택 시점에 요소가 보이는 상태여야 한다"
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_invisible_target_is_still_adopted_before_the_budget_ends(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-119 를 위한 안전장치 — 끝내 보이지 않아도 실패시키지 않는다.

    보이지 않는 것이 **정상인** 대상이 있다. `hidden` 검증이 그렇고, 화면 밖 입력란이
    그렇다. 보임을 필수 조건으로 만들면 그런 Step 이 전부 깨진다.

    예산이 거의 끝나면 `count()==1` 인 매칭을 채택한다. 남은 시간은 거의 없지만, 그 뒤
    Playwright 의 actionability 오류가 우리 문구보다 정확하게 원인을 말한다.
    """
    sid, page = _open(
        project_client, fixture_app, "late-visible.html?ms=30000"
    )
    try:
        found = _call(
            project_client,
            lambda: resolve(page, _target(test_id="send-report"), 1500),
        )
        assert found.strategy.kind.value == "test_id"
        visible = _call(project_client, found.locator.is_visible)
        assert not visible, "이 시나리오는 끝내 보이지 않는 상태를 본다"
    finally:
        stop_quietly(project_client, sid)


# ─── research R2 — 모호한 매칭을 조용히 통과시키지 않는다 ──────────────────


@pytest.mark.usefixtures("fixture_app")
def test_ambiguous_does_not_silently_pick_first(
    project_client: TestClient, fixture_app: str
) -> None:
    """**004 이전 코드가 잘못 통과하던 지점** (research R2 실측: 28ms 통과).

    로딩 중 스켈레톤 2개가 같은 텍스트를 갖는다. 004 이전에는
    `locator.first.wait_for(attached)` 가 4ms 만에 반환하며 스켈레톤을 채택했다 —
    잘못된 요소에 대해 테스트가 통과하는 것은 실패보다 나쁘다.
    """
    sid, page = _open(project_client, fixture_app, "lazy.html?ms=30000")
    try:
        with pytest.raises(ElementNotFoundError) as caught:
            _call(
                project_client,
                lambda: resolve(page, _target(text="불러오는 중"), 1200),
            )
        assert caught.value.ambiguous, (
            "여러 개를 매칭한 것과 아무것도 못 찾은 것은 다른 실패다"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_candidate_disagreement_still_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """spec 엣지 케이스 — `resolve()` 재작성이 불일치 기록을 떨어뜨리지 않았다.

    두 후보가 각각 하나씩, 그러나 **서로 다른 요소**를 가리키게 만든다. 최상위 후보로
    진행하되 불일치를 기록해야 한다. 이것이 사라지면 나중에 테스트가 엉뚱한 요소에 대해
    통과했을 때 원인을 찾을 단서가 없다.
    """
    sid, page = _open(project_client, fixture_app, "lazy.html")
    try:
        # **두 후보가 동시에 존재해야** 불일치가 관측된다. 한쪽만 있으면 그것을 채택하고
        # 끝이므로 비교할 상대가 없다. 둘 다 즉시 존재하되 서로 다른 요소를 가리킨다.
        found = _call(
            project_client,
            lambda: resolve(
                page, _target(test_id="lazy-status", css="h1"), BUDGET_MS
            ),
        )
        assert found.strategy.kind.value == "test_id", "채택은 우선순위 순이다"
        assert found.disagreement, "후보가 다른 요소를 가리키면 기록이 남아야 한다"
    finally:
        stop_quietly(project_client, sid)


# ─── FR-120·FR-121 — 예산을 넘긴 실패는 정의 문제와 구별된다 ───────────────


@pytest.mark.usefixtures("fixture_app")
def test_budget_exhausted_reports_not_ready(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-121 — 기다렸으나 나타나지 않은 실패는 시간 초과로 보고된다."""
    sid, page = _open(project_client, fixture_app, "lazy.html?ms=30000")
    try:
        with pytest.raises(ElementNotFoundError) as caught:
            _call(
                project_client,
                lambda: resolve(page, _target(test_id="order-detail"), 1000),
            )
        exc = caught.value
        assert exc.timed_out, "예산을 다 쓴 실패임이 드러나야 한다"
        assert exc.waited_ms >= 500, f"실제 기다린 시간이 남아야 한다: {exc.waited_ms}"
        assert not exc.ambiguous
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_timeout_failure_maps_to_element_not_ready(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-120·FR-123 — `StepExecutor` 가 시간 초과를 `ELEMENT_NOT_READY` 로 낸다.

    화면이 문구를 해석하지 않고 분류만으로 갈라야 한다.
    """
    from itb.execution.step_executor import StepExecutor, StepFailure

    sid, _ = _open(project_client, fixture_app, "lazy.html?ms=30000")
    session = project_client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
    try:
        step = ClickStep(
            id="step-01",
            label="주문 상세 누르기",
            target=_target(test_id="order-detail"),
            timeout_ms=1000,
        )
        executor = StepExecutor(session, _resolver())
        with pytest.raises(StepFailure) as caught:
            _call(project_client, lambda: executor.execute(step))
        assert caught.value.code is ErrorCode.ELEMENT_NOT_READY
        assert "1000" in str(caught.value) or "ms" in str(caught.value), (
            "얼마나 기다렸는지가 사유에 있어야 한다 (FR-121)"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_no_usable_candidate_is_step_failed(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-120 — 후보가 애초에 없는 실패는 `STEP_FAILED` 로 남는다.

    이것은 기다려도 달라지지 않는 **정의 문제**이므로 시간 문제와 갈려야 한다.
    """
    from itb.execution.step_executor import StepExecutor, StepFailure

    sid, _ = _open(project_client, fixture_app, "lazy.html")
    session = project_client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
    try:
        unusable = TargetLocator(
            css=Candidate(value="#nope", status=CandidateStatus.NOT_COLLECTED)
        )
        step = ClickStep(
            id="step-01", label="쓸 수 없는 대상", target=unusable, timeout_ms=1000
        )
        executor = StepExecutor(session, _resolver())
        started = time.monotonic()
        with pytest.raises(StepFailure) as caught:
            _call(project_client, lambda: executor.execute(step))
        elapsed_ms = (time.monotonic() - started) * 1000

        assert caught.value.code is ErrorCode.STEP_FAILED
        assert elapsed_ms < 500, (
            "시도할 후보가 없으면 기다리지 않고 즉시 실패해야 한다"
        )
    finally:
        stop_quietly(project_client, sid)


# ─── FR-113·FR-117 — 정상 경로와 예산 상한 ─────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_immediate_element_does_not_poll(
    project_client: TestClient, fixture_app: str
) -> None:
    """SC-003·FR-113 — 요소가 즉시 존재하면 폴링 루프에 들어가지 않는다.

    대기 정책이 정상 경로를 느리게 만들면 안 된다. 폴링 주기(100ms)보다 빨리 끝나는 것이
    루프에 들어가지 않았다는 관측 가능한 증거다.
    """
    sid, page = _open(project_client, fixture_app, "lazy.html")
    try:
        started = time.monotonic()
        found = _call(
            project_client,
            lambda: resolve(page, _target(test_id="lazy-status"), BUDGET_MS),
        )
        elapsed_ms = (time.monotonic() - started) * 1000

        assert found.strategy.kind.value == "test_id"
        assert elapsed_ms < IMMEDIATE_COST_LIMIT_MS, (
            f"즉시 존재하는 요소에 {elapsed_ms:.0f}ms 가 들었다 (상한 "
            f"{IMMEDIATE_COST_LIMIT_MS}ms)"
        )
        assert all(a.waited_ms == 0 for a in found.attempts), (
            "1라운드에서 끝났다면 어느 후보도 기다리지 않았어야 한다"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_step_never_exceeds_budget(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-117 — 한 Step 의 총 소요가 그 Step 의 대기 예산을 넘지 않는다.

    탭 대기·요소 탐색·조작 가능 대기·동작 수행이 **하나의** 예산을 나눠 쓴다. 각자 상한을
    갖게 두면 한 Step 이 예산의 두 배 이상 걸린다.

    폴링은 대기 시간을 늘릴 수 있는 변경이므로 이 불변식을 명시적으로 고정한다.
    """
    from itb.execution.step_executor import StepExecutor, StepFailure

    budget_ms = 1500
    sid, _ = _open(project_client, fixture_app, "lazy.html?ms=30000")
    session = project_client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
    try:
        step = ClickStep(
            id="step-01",
            label="나타나지 않는 요소",
            target=_target(test_id="order-detail"),
            timeout_ms=budget_ms,
        )
        executor = StepExecutor(session, _resolver())
        started = time.monotonic()
        with pytest.raises(StepFailure):
            _call(project_client, lambda: executor.execute(step))
        elapsed_ms = (time.monotonic() - started) * 1000

        # 예산 + 한 폴링 주기 + 여유. 두 배가 되면 예산이 나뉘지 않은 것이다.
        assert elapsed_ms < budget_ms * 1.6, (
            f"예산 {budget_ms}ms 인 Step 이 {elapsed_ms:.0f}ms 걸렸다"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_element_wait_is_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-114 — 실제로 기다린 시간이 실행 기록에 남는다.

    **성공한 Step 에도 남아야 한다.** 실패했을 때만 남기면 "왜 이 Step 만 느린가" 를
    볼 수 없고, 예산을 얼마로 잡아야 할지 판단할 근거가 사라진다.
    """
    from itb.execution.step_executor import StepExecutor

    sid, _ = _open(project_client, fixture_app, "lazy.html")
    session = project_client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
    try:
        step = ClickStep(
            id="step-01",
            label="주문 상세 누르기",
            target=_target(test_id="order-detail"),
            timeout_ms=BUDGET_MS,
        )
        executor = StepExecutor(session, _resolver())
        record = _call(project_client, lambda: executor.execute(step))
        assert record.element_wait_ms >= LAZY_DELAY_MS * 0.5, (
            f"2초를 기다렸는데 기록이 {record.element_wait_ms}ms 다"
        )
    finally:
        stop_quietly(project_client, sid)


# ─── FR-119 — `hidden` 검증은 그대로다 ─────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_hidden_assertion_still_passes_when_absent(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-119 — 처음부터 없는 요소에 대한 `hidden` 검증은 통과한다.

    이 Step 의 목표는 "대상이 보이지 않는 상태" 이고 그 상태는 이미 충족돼 있다.
    대기 정책이 이 판정을 실패로 바꾸면 정상 흐름이 깨진다.
    """
    from itb.domain.assertion import Assertion, AssertionKind
    from itb.domain.step import AssertionStep
    from itb.execution.step_executor import StepExecutor

    sid, _ = _open(project_client, fixture_app, "lazy.html")
    session = project_client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
    try:
        step = AssertionStep(
            id="step-01",
            label="없는 요소가 보이지 않는다",
            assertion=Assertion(
                kind=AssertionKind.HIDDEN,
                target=_target(test_id="never-exists-anywhere"),
            ),
            timeout_ms=1000,
        )
        executor = StepExecutor(session, _resolver())
        started = time.monotonic()
        _call(project_client, lambda: executor.execute(step))
        elapsed_ms = (time.monotonic() - started) * 1000
        assert elapsed_ms < 2000, (
            f"`hidden` 검증이 {elapsed_ms:.0f}ms 걸렸다 — 예산을 다 쓰고 있다"
        )
    finally:
        stop_quietly(project_client, sid)
