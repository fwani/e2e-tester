"""실패 문장이 **무엇이 잘못됐는지** 를 갈라 말하는가 (FR-054, 003 AP-031).

한 문장으로 뭉뚱그린 실패 사유는 사용자를 없는 문제로 보낸다. 실측(TC-007 step-16)에서
후보는 요소를 정확히 1개 매칭했는데(`matched: true`, `element_wait_ms: 0`) 메시지는
"대상 요소가 나타나지 않았거나 동작이 막혔습니다" 라고 말했다. 사용자는 요소가 안 나타나는
문제를 찾아 헤맸지만 실제 원인은 **로딩 표시가 포인터를 가로막은 것**이었다.
"""

from __future__ import annotations

from playwright.async_api import Error as PlaywrightError

from itb.domain.step import HoverStep
from itb.execution.step_executor import _blocker, _humanize

CALL_LOG = (
    "Locator.hover: Timeout 9977ms exceeded.\n"
    "Call log:\n"
    '  - waiting for locator("main#app-main > div > div:nth-of-type(1)")\n'
    '  - locator resolved to <div class="overlay"></div>\n'
    "  - attempting hover action\n"
    "  - waiting for element to be visible and stable\n"
    "  - element is visible and stable\n"
    "  - scrolling into view if needed\n"
    "  - done scrolling\n"
    '  - <div class="loader-spinner"></div> from <div class="loader-group">…</div>'
    " subtree intercepts pointer events"
)


def _step() -> HoverStep:
    from itb.domain.locator import Candidate, CandidateStatus, TargetLocator

    return HoverStep(
        id="step-16",
        label="div 에 마우스 올리기",
        target=TargetLocator(
            css=Candidate(value="main#app-main > div", status=CandidateStatus.VERIFIED)
        ),
    )


def test_blocked_action_is_not_reported_as_a_missing_element() -> None:
    """가로막힌 동작을 "요소가 나타나지 않았다" 로 말하지 않는다."""
    message = _humanize(PlaywrightError(CALL_LOG), _step())
    assert "대상 요소는 찾았지만" in message, message
    assert "나타나지 않았거나" not in message, message


def test_the_blocking_element_is_named() -> None:
    """**무엇이** 막았는지 말한다. 그것이 사용자가 다음에 할 일을 정한다."""
    message = _humanize(PlaywrightError(CALL_LOG), _step())
    assert 'loader-spinner' in message, message


def test_blocker_is_the_first_tag_not_the_ancestor() -> None:
    """`<blocker> from <ancestor> subtree ...` 에서 앞의 것을 잡는다.

    뒤의 조상을 잡으면 사용자에게 엉뚱한 요소를 지목해 보여 준다.
    """
    assert _blocker(" ".join(CALL_LOG.split())) == '<div class="loader-spinner">'


def test_detection_survives_the_raw_text_clipping() -> None:
    """**판정은 잘리지 않은 원문으로 한다.**

    사용자에게 붙이는 원문은 400자로 자른다. 실측에서 그 절단이 `subtree` 를 `su` 로
    끊어 `intercepts pointer events` 자체를 잘라 냈다. 잘린 문자열로 판정하면 **호출
    기록이 길 때만** 판정이 실패한다 — 그리고 가로막힘은 호출 기록이 긴 실패다.
    """
    padded = CALL_LOG.replace("Call log:", "Call log:\n  - " + "x" * 500)
    message = _humanize(PlaywrightError(padded), _step())
    assert "대상 요소는 찾았지만" in message, message


def test_plain_timeout_keeps_the_old_wording() -> None:
    """가로막힘이 아닌 시간 초과는 문장이 바뀌지 않는다."""
    message = _humanize(
        PlaywrightError("Locator.click: Timeout 10000ms exceeded."), _step()
    )
    assert "대상 요소가 나타나지 않았거나" in message, message
