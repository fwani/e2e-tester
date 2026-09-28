"""세 작성 경로가 같은 검증을 만든다 (021 T029 · US3 · 원칙 I).

헌법 원칙 I 이 요구하는 것은 「작성 경로가 Step 의 의미를 바꾸지 않는다」다. 021 이
어휘를 늘렸으므로, 늘어난 어휘에서도 그것이 성립하는지 확인한다.

**비교 대상은 조건(`Assertion`) 자체다.** 표시 이름과 식별자는 경로마다 다를 수 있고
달라도 된다 — 같아야 하는 것은 「무엇을 검증하는가」다.

브라우저를 띄우지 않는다. 세 경로가 갈릴 수 있는 지점은 **조건을 만드는 코드**이고,
대상 요소 수집은 세 경로가 이미 같은 함수를 지난다 (`collect_by_selector`).
"""

from __future__ import annotations

import pytest

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.manual_step import AssertTextSpec, AssertUrlSpec, build_step
from itb.domain.step import AssertionStep
from itb.execution.assertion_builder import build_step as build_from_condition


def _condition(step: AssertionStep) -> Assertion:
    return step.assertion


# ─── 화면 폼 경로 ↔ 수동 삽입 경로 ──────────────────────────────────────────


@pytest.mark.parametrize("match", [MatchMode.NOT_CONTAINS, MatchMode.NOT_EQUALS])
def test_manual_text_insert_matches_the_form_path(match: MatchMode) -> None:
    """같은 부정 텍스트 검증을 두 경로로 만들면 조건이 같다."""
    manual = build_step(AssertTextSpec(value="오류", match=match), "step-01")
    form = build_from_condition(
        Assertion(kind=AssertionKind.TEXT, value="오류", match=match), "step-02"
    )
    assert _condition(manual) == _condition(form)


@pytest.mark.parametrize("match", [MatchMode.NOT_CONTAINS, MatchMode.NOT_EQUALS])
def test_manual_url_insert_matches_the_form_path(match: MatchMode) -> None:
    manual = build_step(AssertUrlSpec(url="/login", match=match), "step-01")
    form = build_from_condition(
        Assertion(kind=AssertionKind.URL, value="/login", match=match), "step-02"
    )
    assert _condition(manual) == _condition(form)


def test_the_two_paths_differ_only_in_the_label() -> None:
    """**이름만 다르다.** 이름이 다른 것은 의도다 — 경로마다 붙이는 접두가 있다.

    이름까지 같아야 한다고 요구하면 두 경로 중 하나의 이름 규칙을 버려야 하고,
    사용자는 목록에서 어디서 만든 Step 인지 알 수 없게 된다.
    """
    manual = build_step(AssertTextSpec(value="오류", match=MatchMode.NOT_CONTAINS), "step-01")
    form = build_from_condition(
        Assertion(kind=AssertionKind.TEXT, value="오류", match=MatchMode.NOT_CONTAINS),
        "step-01",
    )
    assert manual.label != form.label
    assert manual.model_dump(exclude={"label"}) == form.model_dump(exclude={"label"})


# ─── 작성 도구 경로 — 구조로 확인한다 ───────────────────────────────────────


def test_the_authoring_tool_builds_the_condition_from_the_domain_model() -> None:
    """도구도 같은 `Assertion` 을 만든다.

    브라우저 없이 확인할 수 있는 것은 **도구가 자기 조건 형태를 따로 갖지 않는다**는
    구조다. 도구 코드가 `Assertion(...)` 을 그대로 부르므로 형태 규칙이 도메인 한 곳에
    강제되고, 세 경로가 같은 거절을 받는다.
    """
    import inspect

    from itb.authoring import tools

    source = inspect.getsource(tools.BrowserToolbox.assert_condition)
    assert "Assertion(" in source, "도구가 도메인 모델을 쓰지 않는다"
    assert "AssertionKind(kind)" in source and "MatchMode(match)" in source, (
        "도구가 자기 열거 목록을 따로 들고 있으면 도메인과 갈린다"
    )


@pytest.mark.parametrize(
    ("kind", "extra", "reason"),
    [
        (AssertionKind.VISIBLE, {"match": MatchMode.NOT_CONTAINS}, "값 없는 종류의 부정"),
        (AssertionKind.TEXT, {"value": "", "match": MatchMode.NOT_EQUALS}, "빈 값의 부정"),
    ],
)
def test_every_path_gets_the_same_refusal(
    kind: AssertionKind, extra: dict, reason: str
) -> None:
    """형태 규칙이 도메인 한 곳에 있으므로 **경로와 무관하게 같은 것이 거절된다.**

    경로마다 자기 검사를 가지면 화면에서는 막히는데 도구로는 통과하는 자리가 생기고,
    그렇게 만들어진 정의가 파일에 남는다.
    """
    from pydantic import ValidationError

    from itb.domain.locator import Candidate, CandidateStatus, TargetLocator

    target = TargetLocator(css=Candidate(value="#x", status=CandidateStatus.VERIFIED))
    payload = dict(extra)
    if kind in (AssertionKind.VISIBLE, AssertionKind.HIDDEN):
        payload["target"] = target
    with pytest.raises(ValidationError):
        Assertion(kind=kind, **payload)
