"""부정 검증이 거짓으로 통과하지 않는다 (021 T010 · US1 · FR-001~FR-007).

## 이 파일이 재는 것 — 하나가 나머지 전부보다 중요하다

부정 검증의 기본 상태는 **참**이다. 「`오류` 가 없다」를 클릭 직후 화면이 비어 있는
찰나에 평가하면 통과한다. 그 통과는 아무것도 검증하지 않았다는 뜻인데 결과 화면에는
초록색으로 찍힌다 — 검증 도구가 낼 수 있는 가장 나쁜 출력이다.

`fixtures/sample-app/locked-controls.html` 의 저장 버튼은 **0.8초 뒤에** 오류 문구를
띄운다. `test_a_late_message_is_caught` 가 이 화면을 쓴다. **그 하나가 실패하면 이
기능은 동작하지 않는 것이다.**

실행기를 실제 브라우저에 직접 댄다 (`test_lazy_loading.py` 와 같은 구조). 녹화·저장
왕복을 거치지 않는 이유는, 재려는 것이 **판정의 시점**이라서 그 지점을 직접 겨눠야
실패가 무엇을 뜻하는지 분명하기 때문이다.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import AssertionStep, ClickStep
from itb.execution.step_executor import StepExecutor, StepFailure
from itb.secrets.resolver import VariableResolver

PAGE = "locked-controls.html"

LATE_MESSAGE_DELAY_MS = 800
"""`locked-controls.html` 이 오류 문구를 띄우기까지의 시간. 픽스처와 같아야 한다."""

BUDGET_MS = 5000
"""검증 하나의 예산. 지연(800ms)보다 크고, 넉넉하지 않을 만큼."""


def _resolver() -> VariableResolver:
    return VariableResolver(SimpleNamespace(variables=[]))


def _css(value: str) -> TargetLocator:
    return TargetLocator(css=Candidate(value=value, status=CandidateStatus.VERIFIED))


def _open(client: TestClient, fixture_app: str) -> tuple[str, Any]:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/{PAGE}"},
    )
    assert created.status_code == 201, created.text
    sid = str(created.json()["session_id"])
    return sid, client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]


def _call(client: TestClient, factory: Any) -> Any:
    return client.portal.call(factory)  # type: ignore[attr-defined]


def _assert_step(assertion: Assertion, timeout_ms: int = BUDGET_MS) -> AssertionStep:
    return AssertionStep(
        id="step-01", label="검증", assertion=assertion, timeout_ms=timeout_ms
    )


# ─── FR-003 — 부정 검증은 기다린다. **이 파일의 핵심** ──────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_a_late_message_is_caught(project_client: TestClient, fixture_app: str) -> None:
    """**이 하나가 통과하지 못하면 기능 전체가 무의미하다.**

    저장 버튼을 누르면 0.8초 뒤에 오류가 뜬다. 그 직후 「`오류` 를 포함하지 않는다」를
    평가하면 화면이 아직 비어 있어 통과한다 — 021 이전 텍스트 검증의 동작이 정확히
    그랬다. 대기가 들어갔으므로 이제 **실패해야** 한다.
    """
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        click = ClickStep(
            id="step-00",
            label="저장 누르기",
            target=_css("[data-testid='save-changes']"),
            timeout_ms=BUDGET_MS,
        )
        _call(project_client, lambda: executor.execute(click))

        step = _assert_step(
            Assertion(kind=AssertionKind.TEXT, value="오류", match=MatchMode.NOT_CONTAINS)
        )
        with pytest.raises(StepFailure) as caught:
            _call(project_client, lambda: executor.execute(step))

        message = str(caught.value)
        assert "오류" in message, "기대한 값이 사유에 있어야 한다 (FR-005)"
        assert "오류가 발생했습니다" in message, "실제 화면 텍스트가 사유에 있어야 한다"
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_a_negated_check_watches_for_the_whole_window(
    project_client: TestClient, fixture_app: str
) -> None:
    """부정 검증은 제한 시간을 **끝까지 지켜본다** (FR-003a).

    ## 이것은 비효율이 아니다

    앞선 검증(`test_a_late_message_is_caught`)이 통과하려면 이 성질이 필요하다 —
    「지금 없다」로 끝내면 0.8초 뒤에 뜨는 오류를 영영 놓친다. 「없다」는 언제까지
    없어야 하는지를 정해야 답이 나오는 질문이고, 그 기간이 `timeout_ms` 다.

    긍정 검증은 반대다. 한 번 나타나면 그 사실은 변하지 않으므로 즉시 끝난다 —
    `test_a_positive_check_returns_as_soon_as_it_holds` 가 그쪽을 본다.
    """
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        window_ms = 1200
        step = _assert_step(
            Assertion(kind=AssertionKind.TEXT, value="여기에는 없는 문구", match=MatchMode.NOT_CONTAINS),
            timeout_ms=window_ms,
        )
        started = time.monotonic()
        _call(project_client, lambda: executor.execute(step))
        elapsed_ms = (time.monotonic() - started) * 1000

        assert elapsed_ms >= window_ms * 0.8, (
            f"부정 검증이 관찰 기간을 채우지 않았다. 실제 {elapsed_ms:.0f}ms / "
            f"기간 {window_ms}ms — 이러면 늦게 나타나는 것을 놓친다"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_a_positive_check_returns_as_soon_as_it_holds(
    project_client: TestClient, fixture_app: str
) -> None:
    """긍정 검증은 참이 되는 즉시 끝난다 (FR-004).

    여기까지 제한 시간을 꽉 채우면, 020 이 만든 「실패해도 끝까지 돈다」와 겹쳐 실행
    시간이 감당할 수 없게 늘어난다.
    """
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        step = _assert_step(
            Assertion(kind=AssertionKind.TEXT, value="연관 리소스", match=MatchMode.CONTAINS)
        )
        started = time.monotonic()
        _call(project_client, lambda: executor.execute(step))
        elapsed_ms = (time.monotonic() - started) * 1000

        assert elapsed_ms < BUDGET_MS / 2, (
            f"조건이 참인데 기다렸다. 실제 {elapsed_ms:.0f}ms / 예산 {BUDGET_MS}ms"
        )
    finally:
        stop_quietly(project_client, sid)


# ─── FR-001 — 값 비교의 부정형 ──────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
@pytest.mark.parametrize(
    ("match", "value", "should_pass"),
    [
        (MatchMode.NOT_CONTAINS, "여기에는 없는 문구", True),
        (MatchMode.NOT_CONTAINS, "연관 리소스", False),
        (MatchMode.NOT_EQUALS, "화면 전체와 다른 값", True),
    ],
)
def test_negated_text_on_the_whole_screen(
    project_client: TestClient,
    fixture_app: str,
    match: MatchMode,
    value: str,
    should_pass: bool,
) -> None:
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        step = _assert_step(
            Assertion(kind=AssertionKind.TEXT, value=value, match=match), timeout_ms=1500
        )
        if should_pass:
            _call(project_client, lambda: executor.execute(step))
        else:
            with pytest.raises(StepFailure):
                _call(project_client, lambda: executor.execute(step))
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_negated_url(project_client: TestClient, fixture_app: str) -> None:
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        passing = _assert_step(
            Assertion(kind=AssertionKind.URL, value="/login.html", match=MatchMode.NOT_EQUALS)
        )
        _call(project_client, lambda: executor.execute(passing))

        failing = _assert_step(
            Assertion(kind=AssertionKind.URL, value=PAGE, match=MatchMode.NOT_CONTAINS),
            timeout_ms=1500,
        )
        with pytest.raises(StepFailure) as caught:
            _call(project_client, lambda: executor.execute(failing))
        assert PAGE in str(caught.value)
    finally:
        stop_quietly(project_client, sid)


# ─── FR-006 — 대상을 찾지 못하면 긍정·부정 **모두** 실패 ────────────────────


@pytest.mark.usefixtures("fixture_app")
@pytest.mark.parametrize("match", [MatchMode.CONTAINS, MatchMode.NOT_CONTAINS])
def test_a_missing_target_fails_even_for_a_negated_check(
    project_client: TestClient, fixture_app: str, match: MatchMode
) -> None:
    """통과시키면 「요소가 사라져서 통과」와 「텍스트가 달라서 통과」를 구별할 수 없다.

    요소가 없을 수도 있는 상황은 `hidden` 이 담당한다.
    """
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        step = _assert_step(
            Assertion(
                kind=AssertionKind.TEXT,
                target=_css("[data-testid='there-is-no-such-element']"),
                value="무엇이든",
                match=match,
            ),
            timeout_ms=1200,
        )
        with pytest.raises(StepFailure):
            _call(project_client, lambda: executor.execute(step))
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_negated_text_scoped_to_an_element(
    project_client: TestClient, fixture_app: str
) -> None:
    """대상이 있는 부정 검증 — 그 요소의 텍스트만 본다."""
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        passing = _assert_step(
            Assertion(
                kind=AssertionKind.TEXT,
                target=_css("[data-testid='auto-resource-name']"),
                value="배송",
                match=MatchMode.NOT_CONTAINS,
            )
        )
        _call(project_client, lambda: executor.execute(passing))

        failing = _assert_step(
            Assertion(
                kind=AssertionKind.TEXT,
                target=_css("[data-testid='auto-resource-name']"),
                value="주문",
                match=MatchMode.NOT_CONTAINS,
            ),
            timeout_ms=1200,
        )
        with pytest.raises(StepFailure):
            _call(project_client, lambda: executor.execute(failing))
    finally:
        stop_quietly(project_client, sid)
