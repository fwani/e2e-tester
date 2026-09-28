"""상태 검증의 작성 시점 경고 (021 T027 · FR-014).

## 왜 이 경고가 필요한가 — 방향이 비대칭이다

브라우저는 `<div>` 같은 요소에 대해 「조작할 수 있다」를 참으로 준다.

| 검증 | 이런 대상에서 | 위험 |
|---|---|---|
| 「조작할 수 없다」 | 항상 실패 | 낮다 — 사람이 알아차린다 |
| 「조작할 수 있다」 | **항상 통과** | **높다 — 아무것도 검증하지 않은 초록색** |

020 이 「통과가 정보를 담고 있지 않다」를 문제로 규정한 것과 같은 종류의 실패다.

**막지 않고 알린다.** 막으면 `contenteditable` 이나 ARIA 로 잠금을 표현하는 정당한
위젯까지 막히고, 그런 화면에서 사용자가 할 수 있는 일이 없어진다.
"""

from __future__ import annotations

import pytest

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.execution.assertion_builder import STATEFUL_TAGS, stateless_target_warning


def _target(tag: str | None) -> TargetLocator:
    return TargetLocator(
        css=Candidate(value="#x", status=CandidateStatus.VERIFIED), tag=tag
    )


@pytest.mark.parametrize("tag", sorted(STATEFUL_TAGS))
@pytest.mark.parametrize("kind", [AssertionKind.ENABLED, AssertionKind.DISABLED])
def test_no_warning_for_elements_that_can_be_disabled(
    tag: str, kind: AssertionKind
) -> None:
    assert stateless_target_warning(Assertion(kind=kind, target=_target(tag))) is None


@pytest.mark.parametrize("tag", ["div", "span", "p", "a", "li"])
@pytest.mark.parametrize("kind", [AssertionKind.ENABLED, AssertionKind.DISABLED])
def test_warning_for_elements_that_cannot(tag: str, kind: AssertionKind) -> None:
    warning = stateless_target_warning(Assertion(kind=kind, target=_target(tag)))
    assert warning is not None
    assert tag in warning, "어느 요소가 문제인지 말해야 한다"


@pytest.mark.parametrize("tag", ["div", "span"])
def test_the_step_is_still_made(tag: str) -> None:
    """**경고는 거절이 아니다.**

    `stateless_target_warning` 이 문구를 돌려주는 것과 별개로 조건 자체는 유효하다 —
    도메인 검사를 통과한다. 거절로 바꾸면 ARIA 로 잠금을 표현하는 위젯을 검증할 수
    없게 된다.
    """
    assertion = Assertion(kind=AssertionKind.DISABLED, target=_target(tag))
    assert assertion.kind is AssertionKind.DISABLED
    assert stateless_target_warning(assertion) is not None


def test_no_warning_when_the_tag_is_unknown() -> None:
    """태그를 수집하지 못한 대상에는 경고하지 않는다.

    모르는 것을 문제라고 말하면 경고가 소음이 되고, 소음이 된 경고는 읽히지 않는다.
    """
    assert stateless_target_warning(
        Assertion(kind=AssertionKind.DISABLED, target=_target(None))
    ) is None


@pytest.mark.parametrize(
    "assertion",
    [
        Assertion(kind=AssertionKind.VISIBLE, target=_target("div")),
        Assertion(kind=AssertionKind.HIDDEN, target=_target("div")),
        Assertion(kind=AssertionKind.TEXT, value="x", match=MatchMode.CONTAINS),
        Assertion(kind=AssertionKind.URL, value="/x"),
    ],
)
def test_other_kinds_are_untouched(assertion: Assertion) -> None:
    """상태 검증이 아닌 종류에는 해당 없다 — `<div>` 가 보이는지 묻는 것은 정상이다."""
    assert stateless_target_warning(assertion) is None
