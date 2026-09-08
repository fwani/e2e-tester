"""손으로 만드는 Step 서술 (009 T014 · FR-286·FR-287).

**이 파일이 지키는 것은 셋이다.**

1. 넷이 각각 올바른 도메인 Step 이 된다 — 새 Step 종류를 만들지 않았다 (원칙 I).
2. 요소를 요구하는 종류가 **모델 단계에서** 성립하지 않는다 (원칙 IV).
3. 라벨을 서버가 만든다 — 만든 경로에 따라 이름이 갈리지 않는다.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from itb.domain.assertion import AssertionKind, MatchMode
from itb.domain.manual_step import (
    LABEL_MAX,
    InsertableKind,
    ManualStepSpec,
    build_step,
    derive_label,
)
from itb.domain.step import (
    DEFAULT_TIMEOUT_MS,
    AssertionStep,
    Author,
    CloseTabStep,
    NavigateStep,
    StepType,
)

SPEC = TypeAdapter(ManualStepSpec)


# ─── 1. 넷이 각각 올바른 Step 이 된다 ───────────────────────────────────────


def test_navigate_로_주소_이동_step_이_된다() -> None:
    step = build_step(SPEC.validate_python({"kind": "navigate", "url": "/orders"}), "step-07")

    assert isinstance(step, NavigateStep)
    assert step.type is StepType.NAVIGATE
    assert step.url == "/orders"
    assert step.id == "step-07"
    # 손으로 넣은 것은 사람이 만든 것이다. 실행 방식은 바뀌지 않는다 (원칙 I · FR-014).
    assert step.author is Author.HUMAN


def test_close_tab_은_공통_tab_이_대상을_가리킨다() -> None:
    step = build_step(SPEC.validate_python({"kind": "close_tab", "tab": 2}), "step-03")

    assert isinstance(step, CloseTabStep)
    assert step.tab == 2


def test_assert_url_은_target_없는_url_검증이_된다() -> None:
    step = build_step(
        SPEC.validate_python({"kind": "assert_url", "url": "/done", "match": "contains"}),
        "step-09",
    )

    assert isinstance(step, AssertionStep)
    assert step.assertion.kind is AssertionKind.URL
    assert step.assertion.match is MatchMode.CONTAINS
    assert step.assertion.value == "/done"
    # url 검증은 요소 탐색을 하지 않는다 (assertion.py 의 규칙).
    assert step.assertion.target is None


def test_assert_text_은_target_없이_화면_전체를_본다() -> None:
    step = build_step(
        SPEC.validate_python({"kind": "assert_text", "value": "주문 완료"}), "step-11"
    )

    assert isinstance(step, AssertionStep)
    assert step.assertion.kind is AssertionKind.TEXT
    assert step.assertion.target is None
    # 화면 전체 텍스트에는 contains 가 기본이다.
    assert step.assertion.match is MatchMode.CONTAINS


def test_새_step_종류를_만들지_않는다() -> None:
    """만들어지는 type 은 기존 셋뿐이다 (원칙 I · 원칙 V).

    이것이 참이면 실행·생성기·내보내기를 고칠 것이 없다 — 생성기는 이미 셋을 다룬다.
    """
    made = {
        build_step(SPEC.validate_python(body), "step-01").type
        for body in (
            {"kind": "navigate", "url": "/a"},
            {"kind": "close_tab"},
            {"kind": "assert_url", "url": "/b"},
            {"kind": "assert_text", "value": "c"},
        )
    }

    assert made == {StepType.NAVIGATE, StepType.CLOSE_TAB, StepType.ASSERTION}


# ─── 2. 요소를 요구하는 종류는 성립하지 않는다 (원칙 IV) ────────────────────


@pytest.mark.parametrize("kind", ["click", "fill", "select", "hover", "drag"])
def test_요소를_요구하는_종류는_모델_단계에서_거절된다(kind: str) -> None:
    """**런타임 검사가 아니라 타입이다.** 판별 유니온에 그 종류가 없다 (FR-287)."""
    with pytest.raises(ValidationError):
        SPEC.validate_python({"kind": kind, "url": "/x"})


def test_target_을_실어_보낼_수_없다() -> None:
    """``extra="forbid"`` 가 막는다. 손으로 넣은 후보는 검증 상태를 얻을 수 없다."""
    with pytest.raises(ValidationError):
        SPEC.validate_python(
            {
                "kind": "assert_url",
                "url": "/done",
                "target": {"css": {"value": "a", "status": "verified"}},
            }
        )


def test_삽입_가능한_종류는_넷이다() -> None:
    """목록이 늘거나 줄면 이 검사가 먼저 말한다 (FR-286).

    프론트엔드는 생성 타입으로 이 목록을 받으므로 여기가 유일한 정본이다.
    """
    assert {k.value for k in InsertableKind} == {
        "navigate",
        "close_tab",
        "assert_url",
        "assert_text",
    }


# ─── 3. 라벨은 서버가 만든다 ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"kind": "navigate", "url": "/orders"}, "주소로 이동 — /orders"),
        ({"kind": "close_tab", "tab": 1}, "탭 1 닫기"),
        ({"kind": "assert_url", "url": "/done"}, "주소 검증 — /done"),
        ({"kind": "assert_text", "value": "완료"}, "화면 텍스트 검증 — 완료"),
    ],
)
def test_라벨을_서술에서_파생한다(body: dict[str, object], expected: str) -> None:
    assert derive_label(SPEC.validate_python(body)) == expected


def test_라벨을_주면_그것을_쓴다() -> None:
    step = build_step(
        SPEC.validate_python({"kind": "navigate", "url": "/orders", "label": "주문 목록 열기"}),
        "step-02",
    )

    assert step.label == "주문 목록 열기"


def test_긴_값은_라벨_한도_안으로_자른다() -> None:
    """자르지 않으면 **만드는 순간** Step 검증이 터진다 (label 은 200자 한도).

    그때 사용자는 자기가 넣은 주소가 길다는 것 말고는 알 수 없다.
    """
    long_url = "/x" + "y" * 500
    step = build_step(SPEC.validate_python({"kind": "navigate", "url": long_url}), "step-04")

    assert len(step.label) <= LABEL_MAX
    assert step.label.endswith("…")
    # 값 자체는 자르지 않는다 — 라벨만 줄인다.
    assert isinstance(step, NavigateStep)
    assert step.url == long_url


# ─── 그 밖의 규칙 ───────────────────────────────────────────────────────────


def test_타임아웃을_생략하면_step_의_기본값을_쓴다() -> None:
    step = build_step(SPEC.validate_python({"kind": "navigate", "url": "/a"}), "step-01")

    assert step.timeout_ms == DEFAULT_TIMEOUT_MS


def test_타임아웃을_주면_그것을_쓴다() -> None:
    step = build_step(
        SPEC.validate_python({"kind": "navigate", "url": "/a", "timeout_ms": 3000}), "step-01"
    )

    assert step.timeout_ms == 3000


def test_id_와_author_를_요청으로_받지_않는다() -> None:
    """id 는 서버가 매기고(allocate_step_id) author 는 항상 human 이다 (research R6)."""
    with pytest.raises(ValidationError):
        SPEC.validate_python({"kind": "navigate", "url": "/a", "id": "step-99"})
    with pytest.raises(ValidationError):
        SPEC.validate_python({"kind": "navigate", "url": "/a", "author": "ai"})
