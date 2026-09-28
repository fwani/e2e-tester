"""023 계약 — 입력값 검증의 대상 성질 판정 (T063).

`contracts/assertion-surface.md` §2·§3 의 표를 고정한다.

## 이 파일의 요점 — **두 작성 경로가 같은 판정을 하는가**

`research.md` R3 이 찾은 것: AI 작성 경로는 `build_assertion` 을 지나지 않고 `Assertion`
을 직접 만든다. 그래서 021 의 `stateless_target_warning` 이 **그 경로에 닿지 않고 있다.**

023 이 같은 구조로 규칙을 넣었다면 AI 가 만드는 검증만 새 규칙 밖에 남았을 것이다. 그래서
판정을 공용 함수에 두었고, **이 파일이 그 단일화를 고정한다** — 한쪽만 거절하면 깨진다.
"""

from __future__ import annotations

import pytest

from itb.domain.assertion import AssertionKind
from itb.execution.assertion_builder import (
    select_value_note,
    text_on_input_note,
    value_target_refusal,
)
from itb.execution.element_probe import ProbedTarget


def probed(tag: str, input_type: str | None = None) -> ProbedTarget:
    attrs = {"type": input_type} if input_type else {}
    return ProbedTarget(locator=None, descriptor={"tag": tag, "attributes": attrs})  # type: ignore[arg-type]


# ── §2 대상 성질의 세 갈래 ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "target",
    [
        probed("input"),
        probed("input", "text"),
        probed("input", "email"),
        probed("input", "number"),
        probed("input", "search"),
        probed("input", "date"),
        probed("textarea"),
        probed("select"),
    ],
)
def test_value_bearing_targets_are_accepted(target: ProbedTarget) -> None:
    """값을 갖는 대상은 받는다 (FR-001)."""
    assert value_target_refusal(AssertionKind.VALUE, target, "E2E") is None


@pytest.mark.parametrize("input_type", ["checkbox", "radio"])
def test_checkbox_and_radio_are_refused(input_type: str) -> None:
    """체크 여부와 무관한 고정 문자열이므로 **늘 같은 결과를 내는 검증**이 된다 (FR-032).

    실측으로 확인했다 — 체크하든 말든 `'on'` 이 나온다 (research R8a).

    거절 문구는 **체크 상태 검증이 아직 없다는 사실**도 담아야 한다. 그것이 없으면
    사용자는 「그럼 어떻게 하나」에서 막힌다.
    """
    message = value_target_refusal(AssertionKind.VALUE, probed("input", input_type), "on")
    assert message is not None
    assert "체크" in message, message


@pytest.mark.parametrize("tag", ["button", "div", "a", "span", "p", "h1"])
def test_valueless_targets_are_refused_and_point_at_text(tag: str) -> None:
    """값이 없는 대상은 거절하고 **텍스트 검증을 가리킨다** (FR-031).

    이것이 이 기능이 고치려는 실수의 **반대 방향**이다. 가리키지 않으면 사용자는 두
    종류 사이를 오가며 헤맨다.
    """
    message = value_target_refusal(AssertionKind.VALUE, probed(tag), "x")
    assert message is not None
    assert "텍스트 검증" in message, message


def test_unknown_tag_is_not_refused() -> None:
    """판정하지 못한 것을 거절로 바꾸지 않는다.

    태그를 읽지 못한 경우다. 거절로 바꾸면 정당한 대상이 막히고, 그때 사용자는 왜
    막혔는지 알 수 없다 — 실행 시점 오류로 드러나는 편이 낫다.
    """
    assert value_target_refusal(AssertionKind.VALUE, probed(""), "x") is None


def test_other_kinds_are_untouched() -> None:
    """입력값 검증이 아니면 이 규칙은 아무것도 하지 않는다.

    **기존 여섯 종류의 허용 범위를 넓히지도 좁히지도 않는다** (023 data-model §2).
    """
    for kind in AssertionKind:
        if kind is AssertionKind.VALUE:
            continue
        assert value_target_refusal(kind, probed("button"), "x") is None


# ── §3 비밀번호 칸 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "why"),
    [
        ("hunter2", "평문"),
        ("", "빈 값"),
        ("{{USERNAME}}", "민감하지 않은 변수 — 정의 파일에 값이 남는다"),
        ("{{SECRET_PW}} 그리고 평문", "참조와 평문이 섞였다"),
        ("prefix{{SECRET_PW}}", "앞에 평문이 붙었다"),
    ],
)
def test_password_target_refuses_anything_that_leaves_plaintext(
    value: str, why: str
) -> None:
    """**참조라는 형식이 아니라 민감한지가 기준이다** (FR-015).

    셋째 줄이 판단이 필요한 칸이다. 민감하지 않은 변수는 정의 파일에 값을 가지므로,
    그것으로 비교하면 평문을 적은 것과 결과가 같다.
    """
    message = value_target_refusal(AssertionKind.VALUE, probed("input", "password"), value)
    assert message is not None, f"{why} 인데 통과했다"
    assert "SECRET_" in message, f"이름 규약을 알려 주지 않는다: {message}"


@pytest.mark.parametrize("value", ["{{SECRET_PW}}", "{{SECRET_A}}{{SECRET_B}}"])
def test_password_target_accepts_sensitive_references(value: str) -> None:
    """막는 것은 대상이 아니라 *평문 값*이다."""
    assert value_target_refusal(AssertionKind.VALUE, probed("input", "password"), value) is None


# ── 안내 (거절이 아니다) ────────────────────────────────────────────────────


def test_select_gets_a_note_not_a_refusal() -> None:
    """선택 목록은 **만들되 알린다** (FR-033).

    실측: 화면에 `분석` 이 보여도 값은 `analysis` 다 (research R8a).
    """
    target = probed("select")
    assert value_target_refusal(AssertionKind.VALUE, target, "analysis") is None
    note = select_value_note(AssertionKind.VALUE, target)
    assert note is not None and "내부 식별자" in note, note


def test_text_assertion_on_an_input_gets_a_note() -> None:
    """입력 칸에 텍스트 검증을 고르면 알린다 — **막지 않는다** (FR-030)."""
    note = text_on_input_note(AssertionKind.TEXT, probed("input", "text"))
    assert note is not None and "입력값" in note, note


def test_text_assertion_on_a_select_gets_no_note() -> None:
    """선택 목록은 자식 `option` 의 글자를 텍스트로 가지므로 관찰값이 비지 않는다."""
    assert text_on_input_note(AssertionKind.TEXT, probed("select")) is None
