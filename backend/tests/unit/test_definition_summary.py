"""정의 요약. 016 FR-001~FR-006 (T003, research R8).

에이전트에게 「지금 이 테스트가 무엇인지」를 알려 주는 문자열을 만든다. 이 파일이
고정하는 것은 **무엇을 적는가**가 아니라 **값이 어디로도 새지 않는가**다.

## 왜 거르지 않고 읽지 않는가

민감값 방어는 지금 두 겹이다 — `SensitiveCapturer` 가 기록 시점에 변수 참조로 바꾸고,
`Scrubber` 가 디스크에 쓰기 직전에 거른다. 요약에 스크러버를 거는 것은 세 번째 겹인데,
스크러버는 **민감하다고 알려진 값**만 안다. 사용자가 표시를 깜빡한 사번·주소·카드번호는
그대로 통과한다.

그래서 **값을 읽는 자리를 한 곳(`_value_note`)으로 묶고, 그 한 곳이 원본을 내보내지
않게 한다.** 「아예 읽지 않는다」가 아니다 — 변수 참조인지 판정하려면 읽어야 한다.
아래 세 검사가 함께 그 보장을 이룬다:

- `test_no_step_value_ever_appears` — 값 100종이 새지 않는다 (결과)
- `test_value_is_read_in_exactly_one_place` — 읽는 자리가 하나뿐이다 (구조)
- `test_the_one_reader_never_returns_the_raw_value` — 그 하나가 내보내지 않는다 (구조)

결과 검사만 두면 다음 사람이 다른 자리에서 값을 읽었을 때 목록에 없는 값으로 샌다.

`NavigateStep.url` 도 같은 이유로 **질의 문자열과 조각을 잘라 낸다** — 토큰이 질의
매개변수로 들어오는 것은 흔한 일이고, 요약에 필요한 것은 「어디로 가는가」이지 「어떤
매개변수로 가는가」가 아니다.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from itb.authoring import summary
from itb.authoring.summary import DEFAULT_SUMMARY_BUDGET, build_definition_summary
from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    FillStep,
    NavigateStep,
    SelectStep,
    Step,
    UploadStep,
)


def cand(value: str) -> Candidate:
    return Candidate(value=value, status=CandidateStatus.VERIFIED)


def target(name: str = "저장") -> TargetLocator:
    return TargetLocator(role="button", accessible_name=name, css=cand(f"button.{name}"))


def sample_steps() -> list[Step]:
    """여섯 종류가 섞인 목록. 값을 가진 Step 셋을 일부러 넣는다."""
    return [
        NavigateStep(id="step-01", label="시작 주소 열기", url="https://app.example/login"),
        FillStep(id="step-02", label="아이디 입력", target=target("아이디"), value="admin1234"),
        FillStep(
            id="step-03",
            label="비밀번호 입력",
            target=target("비밀번호"),
            value="{{로그인_비밀번호}}",
        ),
        ClickStep(id="step-04", label="로그인 클릭", target=target("로그인")),
        SelectStep(id="step-05", label="부서 고르기", target=target("부서"), value="영업2팀"),
        AssertionStep(
            id="step-06",
            label="환영 문구 확인",
            assertion=Assertion(kind=AssertionKind.TEXT, target=target("환영"), value="반갑습니다"),
        ),
        UploadStep(
            id="step-07", label="첨부 올리기", target=target("첨부"), file_name="보고서.xlsx"
        ),
        CloseTabStep(id="step-08", label="탭 닫기", tab=1),
    ]


# ─── (a) 무엇을 적는가 ──────────────────────────────────────────────────────


def test_summary_carries_the_facts_the_agent_needs() -> None:
    """순번·id·표시 이름·종류·대상 요약·탭이 들어간다 (FR-001)."""
    text = build_definition_summary(sample_steps(), range_ids=[])

    assert "step-02" in text
    assert "아이디 입력" in text
    assert "fill" in text
    assert "아이디" in text, "대상의 접근가능한 이름이 있어야 한다"
    # 순번은 1부터. 에이전트와 사용자가 같은 번호로 말해야 한다.
    assert "1." in text and "8." in text
    # 탭이 0이 아닌 Step 은 그 사실이 보여야 한다.
    assert "tab 1" in text


def test_navigate_keeps_the_destination_without_the_query() -> None:
    """주소는 남기되 **질의 문자열과 조각은 자른다** (R8).

    토큰이 질의 매개변수로 들어오는 것은 흔하다. 요약에 필요한 것은 어디로 가는가이지
    어떤 매개변수로 가는가가 아니다.
    """
    steps: list[Step] = [
        NavigateStep(
            id="step-01",
            label="콜백",
            url="https://app.example/callback?token=SECRET-TOKEN-9f3&next=/home#frag",
        )
    ]
    text = build_definition_summary(steps, range_ids=[])

    assert "https://app.example/callback" in text
    assert "SECRET-TOKEN-9f3" not in text
    assert "token=" not in text
    assert "#frag" not in text


# ─── (b) 값이 새지 않는가 — 이 파일의 핵심 ──────────────────────────────────


VALUE_SAMPLES = [
    # 흔한 비밀
    "hunter2",
    "P@ssw0rd!",
    "correct horse battery staple",
    # 민감으로 표시되지 않을 법한 개인 정보 — 스크러버가 모르는 것들
    "20230417",
    "사번-A10293",
    "서울특별시 강남구 테헤란로 152",
    "010-1234-5678",
    "4111-1111-1111-1111",
    "hong@example.com",
    "900101-1234567",
    # 경계
    "a",
    "0",
    " ",
    "값 있음",  # 대체 문구와 같은 글자가 실제 값이어도 구별되어야 한다
]
"""요약에 절대 나타나면 안 되는 값들. 100종은 아래 `_expand` 로 만든다."""


def _expand() -> list[str]:
    """샘플을 100종 이상으로 늘린다. 접미사만 바꿔 충돌 없는 고유 값을 만든다."""
    out: list[str] = []
    for i in range(8):
        out.extend(f"{v}~{i}" for v in VALUE_SAMPLES)
    return out


@pytest.mark.parametrize("secret", _expand())
def test_no_step_value_ever_appears(secret: str) -> None:
    """**어떤 Step 의 `value` 도 요약에 나타나지 않는다** (FR-002 · SC-008).

    값이 무엇이든 상관없이 나타나지 않아야 하므로, 「민감하다고 알려진 값」 목록에
    의존하지 않는 검사다 — 스크러버를 거는 것과 다른 점이 이것이다.
    """
    steps: list[Step] = [
        FillStep(id="step-01", label="입력", target=target("칸"), value=secret),
        SelectStep(id="step-02", label="고르기", target=target("목록"), value=secret),
        AssertionStep(
            id="step-03",
            label="확인",
            assertion=Assertion(kind=AssertionKind.TEXT, target=target("문구"), value=secret),
        ),
    ]
    text = build_definition_summary(steps, range_ids=[])
    assert secret not in text, f"값이 요약에 샜다: {secret!r}"


def test_a_step_with_a_value_says_so_without_the_value() -> None:
    """값이 있다는 **사실**은 알린다. 없으면 에이전트가 빈 칸으로 오해한다."""
    steps: list[Step] = [
        FillStep(id="step-01", label="입력", target=target("칸"), value="hunter2"),
    ]
    text = build_definition_summary(steps, range_ids=[])
    assert "값 있음" in text


def test_a_variable_reference_is_shown_as_a_reference() -> None:
    """변수 참조는 **이름 그대로** 보인다 (FR-002).

    참조는 값이 아니다. 에이전트가 `{{로그인_비밀번호}}` 를 다시 쓸 수 있어야 재녹화에서
    같은 계정으로 로그인한다.
    """
    steps: list[Step] = [
        FillStep(id="step-01", label="입력", target=target("칸"), value="{{로그인_비밀번호}}"),
    ]
    text = build_definition_summary(steps, range_ids=[])
    assert "{{로그인_비밀번호}}" in text
    assert "값 있음" not in text, "참조가 있으면 대체 문구 대신 참조를 보인다"


ALLOWED_VALUE_READS = {
    # ── 사용자 입력값을 읽는 유일한 자리 ────────────────────────────────────
    #
    # `_value_note` 안에 있다. 변수 참조인지 판정하려면 읽어야 하고, 그 함수의 반환
    # 가지 어디에도 원본이 실리지 않는다 (아래 검사가 그것을 고정한다).
    "getattr(step, 'value', None)",  # ast.unparse 는 작은따옴표로 정규화한다
    #
    # ── 사용자 입력값이 **아닌** 읽기 ───────────────────────────────────────
    #
    # 로케이터 후보의 값 — CSS 셀렉터와 test id 다. 사용자가 친 것이 아니라 화면에서
    # 수집한 것이며, Step 목록 화면이 이미 그대로 보여 준다.
    "target.label.value",
    "target.test_id.value",
    # 열거형의 값 — Step 종류 이름("fill")과 검증 종류 이름("text").
    "step.type.value",
    "step.assertion.kind.value",
    # 검증의 기댓값 — **있는지만 본다.** `is None` 비교이며 내용은 읽지 않는다.
    # 위 `_extra` 가 이 값을 그대로 쓰면 기댓값(사용자가 적은 문자열)이 샌다.
    "step.assertion.value",
}
"""`summary.py` 안에서 `.value` 로 끝나는 **모든** 읽기와 그 이유.

이 목록이 검사의 실체다. 새 읽기가 생기면 검사가 실패하고, 작성자는 그것이 사용자
입력값인지 아닌지를 **여기에 적어야** 한다. 목록 없이 「한 함수에서만 읽는다」로 검사하면
`Candidate.value`(셀렉터)와 `StepType.value`(열거형)까지 걸려 검사가 헛돈다.
"""


def test_value_is_read_in_exactly_one_place() -> None:
    """`value` 로 끝나는 읽기가 **전부 등록되어 있다** (R8).

    위 검사들은 「새지 않았다」를 본다 — 지금 구현에 대해서는 참이지만, 다음 사람이
    요약을 늘리다 다른 자리에서 값을 읽으면 그 검사는 **새 코드 경로를 보지 못한다**
    (값 100종 목록에 없는 값으로 새면 통과한다).

    그래서 결과가 아니라 **구조**를 고정한다. 값을 읽는 자리가 하나뿐이면, 그 하나가
    값을 내보내지 않는지만 확인하면 된다 (`_value_note` 는 반환 가지가 셋이고 어느
    쪽도 원본을 싣지 않는다).

    **읽지 않는 것이 아니라 한 곳에서만 읽는다** — 변수 참조인지 판정하려면 읽어야
    하기 때문이다. 그 사실을 여기에 적어 둔다.
    """
    tree = ast.parse(inspect.getsource(summary))

    reads: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "value":
            reads.add(ast.unparse(node))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "value"
        ):
            reads.add(ast.unparse(node))

    assert reads == ALLOWED_VALUE_READS, (
        "`value` 로 끝나는 읽기가 바뀌었다.\n"
        f"  새로 생긴 것: {sorted(reads - ALLOWED_VALUE_READS)}\n"
        f"  사라진 것:   {sorted(ALLOWED_VALUE_READS - reads)}\n"
        "사용자 입력값을 읽는 자리가 늘어난 것이라면 R8 위반이다. "
        "안전한 읽기라면 이 목록에 **이유와 함께** 등록하라."
    )


def test_the_one_reader_never_returns_the_raw_value() -> None:
    """`_value_note` 의 반환 가지 어디에도 원본 값이 실리지 않는다 (R8).

    위 검사가 「한 곳에서만 읽는다」를 지키고, 이것이 「그 한 곳이 내보내지 않는다」를
    지킨다. 둘이 함께여야 보장이 된다.
    """
    tree = ast.parse(inspect.getsource(summary._value_note))
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)

    for node in ast.walk(fn):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        returned = node.value
        # 허용: 상수 · 상수 이름(VALUE_PRESENT) · 참조 문자열의 strip 호출
        if isinstance(returned, ast.Constant):
            continue
        if isinstance(returned, ast.Name) and returned.id.isupper():
            continue
        if (
            isinstance(returned, ast.Call)
            and isinstance(returned.func, ast.Attribute)
            and returned.func.attr == "strip"
        ):
            # `raw.strip()` — 이 가지는 값 전체가 `{{이름}}` 일 때만 닿는다.
            continue
        msg = f"원본 값이 반환될 수 있는 가지가 생겼다: {ast.dump(returned)[:120]}"
        raise AssertionError(msg)


# ─── (c) 교체 구간 표시 ─────────────────────────────────────────────────────


def test_the_replacement_range_is_marked() -> None:
    """교체 대상 구간이 드러난다 (FR-004).

    표시가 없으면 에이전트는 「어디를 다시 만드는지」를 지시문에서만 알게 되고,
    사용자가 "여기" 라고 말할 때 가리킬 것이 없다.
    """
    steps = sample_steps()
    text = build_definition_summary(steps, range_ids=["step-04", "step-05"])

    lines = [ln for ln in text.splitlines() if "step-04" in ln or "step-05" in ln]
    assert len(lines) == 2
    assert all("교체 구간" in ln for ln in lines)

    untouched = [ln for ln in text.splitlines() if "step-02" in ln]
    assert untouched and "교체 구간" not in untouched[0]


def test_no_range_means_no_marks() -> None:
    """구간이 없으면 표시도 없다 — 일반 AI 작성·자연어 Step 추가 경로 (FR-005)."""
    text = build_definition_summary(sample_steps(), range_ids=[])
    assert "교체 구간" not in text


# ─── (d) 축약 ───────────────────────────────────────────────────────────────


def many_steps(n: int) -> list[Step]:
    return [
        ClickStep(id=f"step-{i + 1:02d}", label=f"동작 {i + 1}", target=target(f"버튼{i + 1}"))
        for i in range(n)
    ]


def test_a_long_definition_is_shortened_within_budget() -> None:
    """예산을 넘으면 줄인다 (FR-006)."""
    text = build_definition_summary(many_steps(400), range_ids=[], budget=2000)
    assert len(text.encode()) <= 2000


def test_shortening_says_what_it_dropped() -> None:
    """**조용히 자르지 않는다** (FR-006).

    생략을 말하지 않으면 에이전트는 목록이 그게 전부라고 믿고, 없는 Step 을 만들거나
    있는 Step 을 다시 만든다.
    """
    text = build_definition_summary(many_steps(400), range_ids=[], budget=2000)
    assert "생략" in text
    # 생략 구간의 번호를 말한다 — 몇 개가 사라졌는지 알 수 있어야 한다.
    assert any(ch.isdigit() for ch in text.split("생략")[0][-40:])


def test_shortening_keeps_the_range_and_its_neighbours() -> None:
    """줄일 때 **교체 구간에서 먼 것부터** 버린다 (FR-006).

    구간을 버리면 요약이 있으나 마나다 — 에이전트가 다시 만들 자리를 못 본다.
    """
    steps = many_steps(400)
    text = build_definition_summary(steps, range_ids=["step-200", "step-201"], budget=2000)

    assert "step-200" in text
    assert "step-201" in text
    assert "step-199" in text, "구간의 앞 이웃은 맥락이다"
    assert "step-202" in text, "구간의 뒤 이웃도 맥락이다"


def test_a_short_definition_is_not_shortened() -> None:
    """예산 안에 들면 전부 적는다. 정상 경로에서 축약이 끼어들지 않는다."""
    steps = sample_steps()
    text = build_definition_summary(steps, range_ids=[])
    assert "생략" not in text
    for step in steps:
        assert step.id in text


def test_the_default_budget_fits_a_hundred_steps() -> None:
    """Step 100개가 기본 예산 안에 들어간다 (T064 의 실측 대상).

    이 값이 너무 작으면 평범한 테스트에서 축약이 상시로 일어나고, 너무 크면 매 턴의
    토큰이 낭비된다. 실측으로 정한다.
    """
    text = build_definition_summary(many_steps(100), range_ids=[])
    assert "생략" not in text, (
        f"Step 100개가 기본 예산({DEFAULT_SUMMARY_BUDGET})을 넘었다: {len(text.encode())} bytes"
    )


# ─── 경계 ───────────────────────────────────────────────────────────────────


def test_an_empty_definition_is_stated_not_blank() -> None:
    """Step 이 없으면 그 사실을 말한다. 빈 문자열은 「모른다」와 구별되지 않는다."""
    text = build_definition_summary([], range_ids=[])
    assert text.strip()
    assert "없" in text


def test_range_ids_that_are_not_in_the_list_are_ignored() -> None:
    """목록에 없는 id 가 구간으로 와도 터지지 않는다.

    요약은 **보고**이지 검증이 아니다. 구간 검증은 경계(`validate_range`)가 한다 —
    여기서 또 거절하면 같은 규칙이 두 곳에 생긴다.
    """
    text = build_definition_summary(sample_steps(), range_ids=["step-99"])
    assert "교체 구간" not in text


# ─── FR-005 — 모든 AI 경로가 같은 요약을 받는다 (T006b) ─────────────────────


def test_every_ai_path_shares_one_injection_point() -> None:
    """US4·US6·016 이 **같은 한 곳**에서 요약을 받는다 (FR-005).

    경로마다 AI 가 아는 것이 다르면 사용자는 어느 경로에서 무엇을 말할 수 있는지
    예측하지 못한다. 배선이 한 곳(`_build_agent` 의 `summary_source`)임을 구조로
    고정한다 — 두 곳이 되는 순간 한쪽이 빠지고, 빠진 경로에서 AI 는 정의를 모른다.
    """
    from itb.api.routes import sessions as routes

    source = inspect.getsource(routes)
    tree = ast.parse(source)

    wired = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg == "summary_source"
    ]
    assert len(wired) == 1, (
        f"`summary_source` 배선이 {len(wired)}곳이다. 한 곳이어야 한다 (FR-005) — "
        "두 곳이 되면 한쪽이 빠지고, 빠진 경로에서 AI 는 정의를 모른다."
    )

    builders = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(k, ast.keyword) and k.arg == "summary_source"
            for inner in ast.walk(node)
            if isinstance(inner, ast.Call)
            for k in inner.keywords
        )
    ]
    assert builders == ["_build_agent"], (
        f"요약 배선이 예상 밖의 함수에 있다: {builders}. "
        "`_build_agent` 하나가 모든 AI 경로의 조립 지점이다."
    )


def test_the_agent_prepends_the_summary_to_every_turn() -> None:
    """요약이 **매 턴** 붙는다 (FR-003).

    첫 메시지에만 붙이면 대화가 길어질수록 에이전트가 보는 목록이 낡는다 — 자기가
    방금 만든 Step 도 모르는 상태가 된다.
    """
    from itb.authoring.agent import AuthoringAgent

    tree = ast.parse(inspect.getsource(AuthoringAgent))
    appenders = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and any(
            isinstance(inner, ast.Attribute) and inner.attr == "append"
            for inner in ast.walk(node)
        )
    ]
    wrapped = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and any(
            isinstance(inner, ast.Attribute) and inner.attr == "_with_summary"
            for inner in ast.walk(node)
        )
    ]
    assert set(appenders) == set(wrapped), (
        f"이력에 사용자 메시지를 붙이면서 요약을 빠뜨린 입구가 있다: "
        f"{sorted(set(appenders) - set(wrapped))}"
    )
    assert len(appenders) >= 4, (
        f"입구가 {len(appenders)}개다 — run·chat·resume_with_answer·"
        f"resume_after_takeover 넷 이상이어야 한다"
    )
