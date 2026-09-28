"""요소의 조작 가능 여부를 검증한다 (021 T020 · US2 · FR-010~FR-014).

## 이 파일이 재는 것

「삭제 버튼이 비활성화되어 직접 제거할 수 없는지 확인한다」 — 사용자 시나리오에
반복해서 나오는 문장인데, 021 이전에는 어느 어휘로도 표현할 수 없었다.

| 화면이 이렇게 동작하면 | `visible` | `hidden` |
|---|---|---|
| 버튼이 DOM 에서 빠진다 | 실패 (원하는 결과) | 통과 (원하는 결과) |
| 버튼이 남고 `disabled` 만 붙는다 | **통과** — 잘못 통과 | **실패** — 잘못 실패 |

아래 줄이 이 기능이 채우는 빈칸이다.

**`hidden` 과 갈리는 지점은 대상이 없을 때다** — `hidden` 은 통과하지만 상태 검증은
실패한다. 「없다」와 「있는데 잠겼다」는 다른 사실이고, 한 검증이 둘을 함께 통과시키면
결과를 보고 어느 쪽이었는지 알 수 없다.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import AssertionStep
from itb.execution.step_executor import StepExecutor, StepFailure
from itb.secrets.resolver import VariableResolver

PAGE = "locked-controls.html"
BUDGET_MS = 3000

LOCKED = "[data-testid='delete-auto']"
"""자동 포함된 리소스의 삭제 버튼 — `disabled` 다."""

UNLOCKED = "[data-testid='delete-manual']"
"""직접 추가한 리소스의 삭제 버튼 — 누를 수 있다."""


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


def _step(kind: AssertionKind, selector: str, timeout_ms: int = BUDGET_MS) -> AssertionStep:
    return AssertionStep(
        id="step-01",
        label="상태 검증",
        assertion=Assertion(kind=kind, target=_css(selector)),
        timeout_ms=timeout_ms,
    )


# ─── FR-010 — 통과와 실패가 대상에 따라 갈린다 ──────────────────────────────


@pytest.mark.usefixtures("fixture_app")
@pytest.mark.parametrize(
    ("kind", "selector", "should_pass"),
    [
        (AssertionKind.DISABLED, LOCKED, True),
        (AssertionKind.DISABLED, UNLOCKED, False),
        (AssertionKind.ENABLED, UNLOCKED, True),
        (AssertionKind.ENABLED, LOCKED, False),
    ],
)
def test_state_matches_the_element(
    project_client: TestClient,
    fixture_app: str,
    kind: AssertionKind,
    selector: str,
    should_pass: bool,
) -> None:
    """**네 조합이 다 필요하다.** 통과만 재면 「항상 통과하는 검증」이 통과한다."""
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        step = _step(kind, selector, timeout_ms=1200)
        if should_pass:
            _call(project_client, lambda: executor.execute(step))
        else:
            with pytest.raises(StepFailure):
                _call(project_client, lambda: executor.execute(step))
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_the_failure_says_what_was_expected_and_what_happened(
    project_client: TestClient, fixture_app: str
) -> None:
    """020 이 이 문자열을 그대로 어긋남 기록에 싣는다 — 기대와 실제가 둘 다 있어야 한다."""
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        with pytest.raises(StepFailure) as caught:
            _call(
                project_client,
                lambda: executor.execute(_step(AssertionKind.DISABLED, UNLOCKED, 1200)),
            )
        message = str(caught.value)
        assert "조작할 수 없어야" in message
        assert "조작할 수 있었" in message
    finally:
        stop_quietly(project_client, sid)


# ─── FR-012 — 대상이 없으면 실패한다. **`hidden` 과 갈리는 지점** ───────────


@pytest.mark.usefixtures("fixture_app")
@pytest.mark.parametrize("kind", [AssertionKind.ENABLED, AssertionKind.DISABLED])
def test_a_missing_target_fails_unlike_hidden(
    project_client: TestClient, fixture_app: str, kind: AssertionKind
) -> None:
    """없는 것은 비활성이 아니다.

    통과시키면 「버튼이 사라져서 통과」와 「버튼이 잠겨서 통과」를 결과에서 구별할 수
    없다. 요소가 없을 수도 있는 상황은 `hidden` 이 담당한다.
    """
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        with pytest.raises(StepFailure):
            _call(
                project_client,
                lambda: executor.execute(
                    _step(kind, "[data-testid='there-is-no-such-button']", 1200)
                ),
            )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_hidden_still_passes_on_a_missing_target(
    project_client: TestClient, fixture_app: str
) -> None:
    """**대조군이다.** `hidden` 의 기존 동작이 021 로 바뀌지 않았음을 함께 세운다."""
    sid, session = _open(project_client, fixture_app)
    executor = StepExecutor(session, _resolver())
    try:
        _call(
            project_client,
            lambda: executor.execute(
                _step(AssertionKind.HIDDEN, "[data-testid='there-is-no-such-button']", 1200)
            ),
        )
    finally:
        stop_quietly(project_client, sid)
