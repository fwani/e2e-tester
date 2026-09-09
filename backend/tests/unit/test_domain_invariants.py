"""T023 — 도메인 불변식 단위 테스트.

`contracts/step-dsl.md` §검증 규칙과 data-model 의 불변식이 실제로 강제되는지 확인한다.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
from itb.domain.step import DEFAULT_TIMEOUT_MS, Author, Step, StepType, target_of
from itb.domain.test_case import Test, Variable

STEP_ADAPTER = TypeAdapter(Step)

VERIFIED_CSS = {"css": {"value": "#save", "status": "verified"}}
CLOSE_TAB_STEP = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]
TEST_BASE = {
    "id": "TC-001",
    "name": "프로젝트 생성",
    "authoring_mode": "record",
    "start_url": "http://127.0.0.1:4300/login.html",
}


# ─── TargetLocator / Candidate (FR-017, FR-019b) ────────────────────────────


def test_locator_requires_at_least_one_candidate() -> None:
    with pytest.raises(ValidationError, match="후보를 최소 1개"):
        TargetLocator(tag="div")


def test_ambiguous_candidate_is_not_usable() -> None:
    """여러 요소를 매칭하는 후보는 확보된 후보로 세지 않는다 (FR-019b)."""
    amb = Candidate(value="저장", status=CandidateStatus.AMBIGUOUS)
    assert amb.usable is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (CandidateStatus.VERIFIED, True),
        (CandidateStatus.AMBIGUOUS, False),
        (CandidateStatus.UNVERIFIED, False),
        (CandidateStatus.NOT_COLLECTED, False),
    ],
)
def test_only_verified_counts_as_usable(status: CandidateStatus, expected: bool) -> None:
    assert Candidate(value="v", status=status).usable is expected


def test_usable_candidate_count_excludes_ambiguous() -> None:
    """SC-008 측정이 부풀려지지 않는지 확인한다."""
    loc = TargetLocator(
        tag="button",
        test_id=Candidate(value="create-project", status=CandidateStatus.VERIFIED),
        role="button",
        accessible_name="프로젝트 생성",
        role_status=CandidateStatus.VERIFIED,
        text=Candidate(value="프로젝트 생성", status=CandidateStatus.AMBIGUOUS),
        css=Candidate(value=".card button", status=CandidateStatus.AMBIGUOUS),
    )
    assert loc.usable_candidate_count() == 2


def test_stable_attr_usable_follows_status() -> None:
    ok = StableAttr(name="data-role", value="save", status=CandidateStatus.VERIFIED)
    bad = StableAttr(name="data-role", value="save", status=CandidateStatus.AMBIGUOUS)
    assert ok.usable and not bad.usable


def test_role_candidate_needs_both_role_and_name() -> None:
    """role 만 있고 accessible_name 이 없으면 확보된 후보가 아니다."""
    loc = TargetLocator(role="button", role_status=CandidateStatus.VERIFIED, **VERIFIED_CSS)
    assert loc.usable_candidate_count() == 1  # css 만


# ─── Assertion (FR-013a) ────────────────────────────────────────────────────


def test_visible_assertion_requires_target() -> None:
    with pytest.raises(ValidationError, match="target 이 필요"):
        Assertion(kind=AssertionKind.VISIBLE)


def test_hidden_assertion_requires_target() -> None:
    with pytest.raises(ValidationError, match="target 이 필요"):
        Assertion(kind=AssertionKind.HIDDEN)


def test_url_assertion_must_not_have_target() -> None:
    with pytest.raises(ValidationError, match="요소 탐색을 하지 않는다"):
        Assertion(
            kind=AssertionKind.URL,
            value="/projects",
            target=TargetLocator(**VERIFIED_CSS),
        )


def test_url_assertion_requires_value() -> None:
    with pytest.raises(ValidationError, match="비교 값이 필요"):
        Assertion(kind=AssertionKind.URL)


def test_text_assertion_requires_value() -> None:
    with pytest.raises(ValidationError, match="비교 값이 필요"):
        Assertion(kind=AssertionKind.TEXT)


def test_text_assertion_works_without_target() -> None:
    """target 이 없으면 화면 전체를 대상으로 한다."""
    a = Assertion(kind=AssertionKind.TEXT, value="TEST", match=MatchMode.CONTAINS)
    assert a.target is None


# ─── Step (FR-010, FR-012, FR-013, FR-030a) ─────────────────────────────────


def test_step_union_covers_every_step_type() -> None:
    """지원하는 동작 종류가 모두 판별 유니온에 있다.

    **이 집합을 늘리는 것은 DSL 변경이다** — 원칙 I 은 스키마를 먼저 바꾸고 소비자가
    따라오게 요구한다. 이 단언이 그 절차를 밟지 않은 추가를 막는다.

    `hover`·`drag` 는 T161(FR-023c)에서 더했다. `upload` 는 2026-09-09 에 더했다 —
    사용자 보고(「파일업로드 녹화가 제대로 안됨」)이며, 그 종류가 없어서 파일 업로드가
    정의에 전혀 남지 않았다.
    """
    assert {t.value for t in StepType} == {
        "click",
        "fill",
        "select",
        "navigate",
        "assertion",
        "close_tab",
        "hover",
        "drag",
        "upload",
    }


def test_step_defaults() -> None:
    s = STEP_ADAPTER.validate_python(
        {"type": "click", "id": "step-01", "label": "저장", "target": VERIFIED_CSS}
    )
    assert s.tab == 0
    assert s.timeout_ms == DEFAULT_TIMEOUT_MS
    assert s.author is Author.HUMAN


def test_author_does_not_change_step_shape() -> None:
    """원칙 I: 작성 주체가 달라도 구조가 같아야 한다 (FR-014)."""
    payload = {"type": "click", "id": "step-01", "label": "저장", "target": VERIFIED_CSS}
    human = STEP_ADAPTER.validate_python({**payload, "author": "human"})
    ai = STEP_ADAPTER.validate_python({**payload, "author": "ai"})
    assert type(human) is type(ai)
    assert human.model_dump(exclude={"author"}) == ai.model_dump(exclude={"author"})


def test_close_tab_step_targets_via_tab_field() -> None:
    s = STEP_ADAPTER.validate_python(
        {"type": "close_tab", "id": "step-03", "label": "약관 창 닫기", "tab": 1}
    )
    assert s.tab == 1
    assert target_of(s) is None


def test_target_of_reads_assertion_target() -> None:
    s = STEP_ADAPTER.validate_python(
        {
            "type": "assertion",
            "id": "step-02",
            "label": "TEST 확인",
            "assertion": {"kind": "visible", "target": VERIFIED_CSS},
        }
    )
    assert target_of(s) is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", "bad-id"), ("tab", -1), ("timeout_ms", 0), ("timeout_ms", 60_001)],
)
def test_step_field_bounds(field: str, value: object) -> None:
    payload = {
        "type": "click",
        "id": "step-01",
        "label": "저장",
        "target": VERIFIED_CSS,
        field: value,
    }
    with pytest.raises(ValidationError):
        STEP_ADAPTER.validate_python(payload)


def test_unknown_field_is_rejected() -> None:
    """extra="forbid" — 미지 필드 거절이 FR-085 경계 검증을 겸한다 (research R6)."""
    with pytest.raises(ValidationError):
        STEP_ADAPTER.validate_python(
            {
                "type": "click",
                "id": "step-01",
                "label": "저장",
                "target": VERIFIED_CSS,
                "typo_field": 1,
            }
        )


# ─── Variable (FR-082) ──────────────────────────────────────────────────────


def test_sensitive_variable_must_not_carry_value() -> None:
    """민감 값이 정의 파일에 들어가는 것을 스키마가 막는다."""
    with pytest.raises(ValidationError, match="value 를 가질 수 없다"):
        Variable(name="LOGIN_PASSWORD", value="hunter2", sensitive=True)


def test_sensitive_variable_without_value_is_valid() -> None:
    v = Variable(name="LOGIN_PASSWORD", sensitive=True)
    assert v.value is None


def test_non_sensitive_variable_may_carry_value() -> None:
    assert Variable(name="PROJECT_NAME", value="TEST").value == "TEST"


@pytest.mark.parametrize("name", ["lower", "1START", "has-dash", "has space", ""])
def test_variable_name_pattern(name: str) -> None:
    with pytest.raises(ValidationError):
        Variable(name=name, value="v")


# ─── Test (FR-029, dsl_version, 변수 참조) ──────────────────────────────────


def test_test_requires_at_least_one_step() -> None:
    with pytest.raises(ValidationError):
        Test(**TEST_BASE, steps=[])


def test_duplicate_step_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="중복"):
        Test(
            **TEST_BASE,
            steps=[
                {"type": "close_tab", "id": "step-01", "label": "a"},
                {"type": "close_tab", "id": "step-01", "label": "b"},
            ],
        )


def test_undefined_variable_reference_rejected() -> None:
    with pytest.raises(ValidationError, match="정의되지 않은 변수"):
        Test(
            **TEST_BASE,
            steps=[
                {
                    "type": "fill",
                    "id": "step-01",
                    "label": "이름",
                    "value": "{{NOPE}}",
                    "target": VERIFIED_CSS,
                }
            ],
        )


def test_declared_variable_reference_accepted() -> None:
    t = Test(
        **TEST_BASE,
        variables=[{"name": "PROJECT_NAME", "value": "TEST"}],
        steps=[
            {
                "type": "fill",
                "id": "step-01",
                "label": "이름",
                "value": "{{PROJECT_NAME}}",
                "target": VERIFIED_CSS,
            }
        ],
    )
    assert t.referenced_variables() == {"PROJECT_NAME"}


def test_duplicate_variable_names_rejected() -> None:
    with pytest.raises(ValidationError, match="변수 이름이 중복"):
        Test(
            **TEST_BASE,
            variables=[{"name": "A", "value": "1"}, {"name": "A", "value": "2"}],
            steps=CLOSE_TAB_STEP,
        )


def test_unsupported_dsl_version_rejected() -> None:
    with pytest.raises(ValidationError, match="지원하지 않는 dsl_version"):
        Test(**TEST_BASE, steps=CLOSE_TAB_STEP, dsl_version=99)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "ftp://x/"])
def test_non_http_start_url_rejected(url: str) -> None:
    """FR-085 경계 검증 — http/https 스킴만 허용한다."""
    with pytest.raises(ValidationError):
        Test(**{**TEST_BASE, "start_url": url}, steps=CLOSE_TAB_STEP)


@pytest.mark.parametrize("test_id", ["TC-1", "TC-0001", "tc-001", "TC001"])
def test_test_id_pattern(test_id: str) -> None:
    with pytest.raises(ValidationError):
        Test(**{**TEST_BASE, "id": test_id}, steps=CLOSE_TAB_STEP)


def test_ai_instruction_is_optional_and_not_executable() -> None:
    """지시문은 보관만 한다. 실행기는 이 필드를 읽지 않는다 (FR-063)."""
    t = Test(**TEST_BASE, steps=CLOSE_TAB_STEP, ai_instruction="로그인한 다음 ...")
    assert t.ai_instruction is not None
    assert t.referenced_variables() == set()


# ─── hover·drag Step (T161·FR-023c) ────────────────────────────────────────


def test_hover_step_requires_a_target() -> None:
    """hover 는 대상 요소가 있어야 한다 — 어디에 올릴지 없으면 실행할 수 없다."""
    with pytest.raises(ValidationError):
        STEP_ADAPTER.validate_python(
            {"id": "step-01", "label": "메뉴", "type": "hover"}
        )


def test_drag_step_requires_both_ends() -> None:
    """drag 는 끄는 대상과 놓는 위치를 모두 요구한다.

    한쪽만 있는 Step 은 재실행할 수 없다. 스키마가 거절해야 절반짜리 정의가 파일에
    들어가지 않는다.
    """
    verified = {"css": {"value": "#a", "status": "verified"}}
    with pytest.raises(ValidationError):
        STEP_ADAPTER.validate_python(
            {"id": "step-01", "label": "끌기", "type": "drag", "target": verified}
        )


def test_drag_step_keeps_source_as_the_primary_target() -> None:
    """`target_of` 가 끄는 대상을 돌려준다 — 다른 Step 과 같은 규칙이다."""
    from itb.domain.step import target_of

    step = STEP_ADAPTER.validate_python(
        {
            "id": "step-01",
            "label": "끌어다 놓기",
            "type": "drag",
            "target": {"css": {"value": "#chip", "status": "verified"}},
            "drop_target": {"css": {"value": "#zone", "status": "verified"}},
        }
    )
    target = target_of(step)
    assert target is not None
    assert target.css is not None
    assert target.css.value == "#chip"


@pytest.mark.parametrize("step_type", ["hover", "drag"])
def test_new_step_types_carry_the_shared_fields(step_type: str) -> None:
    """원칙 I — 새 종류도 공통 필드를 그대로 쓴다. 별도 표현을 만들지 않는다."""
    payload = {
        "id": "step-01",
        "label": "동작",
        "type": step_type,
        "target": {"css": {"value": "#a", "status": "verified"}},
    }
    if step_type == "drag":
        payload["drop_target"] = {"css": {"value": "#b", "status": "verified"}}

    step = STEP_ADAPTER.validate_python(payload)
    assert step.author is Author.HUMAN
    assert step.tab == 0
    assert step.timeout_ms > 0
    # `author` 가 구조를 바꾸지 않는다 (FR-014)
    ai = STEP_ADAPTER.validate_python({**payload, "author": "ai"})
    assert step.model_dump(exclude={"author"}) == ai.model_dump(exclude={"author"})
