"""Playwright 생성기 단위 테스트. 헌법 품질 게이트 3 (T144·T164).

게이트가 Generator 단위 테스트를 필수로 요구한다. 여기서 고정하는 것은 네 가지다.

1. **후보별 표현** — `choose_strategy` 가 고른 후보가 그대로 코드가 된다 (원칙 IV)
2. **Step 종류 전부** — hover·drag·upload 포함. 종류가 늘면 여기서 실패해야 한다
3. **민감 변수는 변수 참조로만** — 복호화된 값이 코드에 들어갈 경로가 없다 (FR-089d-1)
4. **이스케이프** — 대상 화면에서 온 텍스트가 코드를 깨거나 주입되지 않는다 (헌법 §보안)
"""

from __future__ import annotations

import json

import pytest

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    SelectStep,
    StepType,
    UploadStep,
)
from itb.domain.test_case import AuthoringMode, Test, Variable
from itb.generator.playwright_gen import (
    NoUsableCandidateError,
    ValueRenderer,
    _frame_selector,
    generate_config,
    generate_package_json,
    generate_spec,
    step_lines,
)
from itb.locator.strategy import StrategyKind, choose_strategy

SECRET = "not-a-real-password"


def cand(value: str, status: CandidateStatus = CandidateStatus.VERIFIED) -> Candidate:
    return Candidate(value=value, status=status)


def target(**kwargs: object) -> TargetLocator:
    return TargetLocator(**kwargs)  # type: ignore[arg-type]


def values(*variables: Variable) -> ValueRenderer:
    return ValueRenderer({v.name: v for v in variables})


def line_of(step: object, renderer: ValueRenderer | None = None) -> str:
    return " ".join(step_lines(step, renderer or values()))  # type: ignore[arg-type]


# ─── 1. 후보별 표현 (원칙 IV) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("locator", "expected"),
    [
        (target(test_id=cand("save")), 'page.getByTestId("save")'),
        (
            target(
                role="button",
                accessible_name="저장",
                role_status=CandidateStatus.VERIFIED,
                css=cand(".x"),
            ),
            'page.getByRole("button", { name: "저장", exact: true })',
        ),
        (target(label=cand("이메일")), 'page.getByLabel("이메일", { exact: true })'),
        (target(text=cand("삭제")), 'page.getByText("삭제", { exact: true })'),
        (
            target(
                stable_attr=StableAttr(
                    name="data-qa", value="save", status=CandidateStatus.VERIFIED
                )
            ),
            'page.locator("[data-qa=\\"save\\"]")',
        ),
        (target(css=cand("#id")), 'page.locator("#id")'),
    ],
)
def test_each_candidate_kind_has_a_representation(
    locator: TargetLocator, expected: str
) -> None:
    """확보된 후보마다 대응하는 Playwright 표현이 있다 (contracts/step-dsl §Export 대비)."""
    step = ClickStep(id="step-01", label="클릭", target=locator)
    assert expected in line_of(step)


def test_generator_uses_the_same_candidate_as_the_runner() -> None:
    """**FR-022 의 핵심.** 생성기와 Runner 가 같은 후보를 고른다.

    `choose_strategy` 하나에서 나오므로 갈릴 수 없다는 사실을 테스트로 고정한다 —
    생성기가 자체 우선순위를 갖게 되는 변경을 여기서 잡는다.
    """
    locator = target(
        test_id=cand("save"),
        label=cand("저장"),
        css=cand(".save"),
    )
    chosen = choose_strategy(locator)
    assert chosen is not None and chosen.kind is StrategyKind.TEST_ID

    step = ClickStep(id="step-01", label="클릭", target=locator)
    generated = line_of(step)
    assert "getByTestId" in generated
    assert "getByLabel" not in generated
    assert ".locator(" not in generated


def test_unusable_candidates_are_refused_not_silently_downgraded() -> None:
    """확보된 후보가 없으면 **거절한다.**

    조용히 CSS 로 떨어지면 반드시 깨지는 코드를 내보내게 된다.
    """
    locator = target(css=cand(".x", CandidateStatus.AMBIGUOUS))
    step = ClickStep(id="step-01", label="모호한 클릭", target=locator)
    with pytest.raises(NoUsableCandidateError) as exc:
        line_of(step)
    assert "다시 집으세요" in str(exc.value)


# ─── 2. Step 종류 전부 (T164) ──────────────────────────────────────────────


def test_every_step_type_is_generated() -> None:
    """**Step 종류 전부에 대응이 있다.**

    종류가 늘었는데 생성기가 따라오지 않으면 내보낸 테스트가 원본보다 적게 실행된다.
    hover·drag 가 실제로 그럴 뻔했다 (T164) — 그래서 열거를 테스트로 고정한다.
    """
    loc = target(test_id=cand("a"))
    drop = target(test_id=cand("b"))
    samples = {
        StepType.CLICK: ClickStep(id="step-01", label="클릭", target=loc),
        StepType.FILL: FillStep(id="step-02", label="입력", target=loc, value="v"),
        StepType.SELECT: SelectStep(id="step-03", label="선택", target=loc, value="v"),
        StepType.NAVIGATE: NavigateStep(
            id="step-04", label="이동", url="https://example.com"
        ),
        StepType.ASSERTION: AssertionStep(
            id="step-05",
            label="확인",
            assertion=Assertion(kind=AssertionKind.VISIBLE, target=loc),
        ),
        StepType.CLOSE_TAB: CloseTabStep(id="step-06", label="닫기", tab=1),
        StepType.HOVER: HoverStep(id="step-07", label="올리기", target=loc),
        StepType.DRAG: DragStep(
            id="step-08", label="끌기", target=loc, drop_target=drop
        ),
        # 2026-09-09 — 파일 업로드 (사용자 보고). 이 줄이 없으면 아래 열거 단언이 잡는다.
        StepType.UPLOAD: UploadStep(
            id="step-09", label="올리기", target=loc, file_name="보고서.xlsx"
        ),
    }
    assert set(samples) == set(StepType), "Step 종류가 늘었는데 표본이 없다"

    for kind, step in samples.items():
        generated = line_of(step)
        assert generated.strip(), f"{kind} 의 코드가 비어 있다"


def test_hover_and_drag_match_the_documented_mapping() -> None:
    """T164 — 대응표(`contracts/step-dsl.md`)가 실제 생성 결과와 같다."""
    loc = target(test_id=cand("tools-menu"))
    hover = HoverStep(id="step-01", label="도구", target=loc)
    assert 'page.getByTestId("tools-menu").hover(' in line_of(hover)

    drag = DragStep(
        id="step-02",
        label="끌기",
        target=target(test_id=cand("chip-events")),
        drop_target=target(label=cand("보관함")),
    )
    generated = line_of(drag)
    assert 'page.getByTestId("chip-events").dragTo(' in generated
    assert 'page.getByLabel("보관함", { exact: true })' in generated


def test_upload_carries_the_file_name_and_its_mime_type() -> None:
    """파일 업로드 (2026-09-09 사용자 보고).

    **확장자가 코드에 그대로 남아야 한다.** 사용자가 요구한 것이 그것이다 — 「실제
    서비스에서는 확장자를 보는경우가 있기 때문」. 이름을 통째로 실으므로 확장자는 그
    안에 있고, MIME 은 이름에서 유추한 값이다 (`mime_type_of`).

    **디스크를 만지지 않는다.** `Buffer.alloc(0)` 으로 내용을 넘기므로 내보낸 코드가
    다른 기계에서도 그대로 돈다 — 제품의 재실행(`step_executor._upload`)과 같은 방식이다.
    """
    step = UploadStep(
        id="step-01",
        label="첨부",
        target=target(test_id=cand("attach")),
        file_name="보고서.xlsx",
    )
    generated = line_of(step)
    assert 'page.getByTestId("attach").setInputFiles(' in generated
    assert '"보고서.xlsx"' in generated
    assert "spreadsheetml.sheet" in generated, "확장자에서 유추한 MIME 이 실려야 한다"
    assert "Buffer.alloc(0)" in generated


def test_upload_without_extension_still_generates() -> None:
    """확장자 없는 파일도 올릴 수 있다 — 오류가 아니다.

    그때 MIME 은 `application/octet-stream` 이다. 지어내면 서버가 다른 이유로 거절한다.
    """
    step = UploadStep(
        id="step-01",
        label="첨부",
        target=target(test_id=cand("attach")),
        file_name="README",
    )
    generated = line_of(step)
    assert '"README"' in generated
    assert "application/octet-stream" in generated


def test_drag_requires_both_ends_to_be_resolvable() -> None:
    """놓는 위치의 후보가 없으면 만들지 않는다.

    끄는 대상만 만들면 요소가 엉뚱한 곳에 떨어지고, 그 결과는 통과로 보일 수 있다.
    """
    drag = DragStep(
        id="step-01",
        label="끌기",
        target=target(test_id=cand("a")),
        drop_target=target(css=cand(".b", CandidateStatus.NOT_COLLECTED)),
    )
    with pytest.raises(NoUsableCandidateError) as exc:
        line_of(drag)
    assert "놓는 위치" in str(exc.value)


@pytest.mark.parametrize(
    ("assertion", "expected"),
    [
        (
            Assertion(kind=AssertionKind.VISIBLE, target=target(test_id=cand("a"))),
            "toBeVisible",
        ),
        (
            Assertion(kind=AssertionKind.HIDDEN, target=target(test_id=cand("a"))),
            "toBeHidden",
        ),
        (
            Assertion(kind=AssertionKind.TEXT, value="TEST", match=MatchMode.CONTAINS),
            "toContainText",
        ),
        (
            Assertion(kind=AssertionKind.URL, value="https://x/", match=MatchMode.EQUALS),
            "toHaveURL",
        ),
    ],
)
def test_four_assertion_kinds(assertion: Assertion, expected: str) -> None:
    """FR-013a 의 4종 전부 (T144 필수 항목)."""
    step = AssertionStep(id="step-01", label="확인", assertion=assertion)
    assert expected in line_of(step)


def test_url_contains_does_not_become_a_regex() -> None:
    """`contains` 를 정규식으로 만들지 않는다.

    화면에서 온 값이 패턴으로 해석되면 의미가 달라진다 — `.` 하나가 임의 문자가 된다.
    """
    step = AssertionStep(
        id="step-01",
        label="주소",
        assertion=Assertion(
            kind=AssertionKind.URL, value="a.b/c", match=MatchMode.CONTAINS
        ),
    )
    generated = line_of(step)
    assert "toContain(" in generated
    assert "RegExp" not in generated


# ─── 3. 멀티 탭 ────────────────────────────────────────────────────────────


def test_multi_tab_uses_wait_for_event_pattern() -> None:
    """`tab: 1` 은 `waitForEvent('page')` 로 잡는다 (contracts/step-dsl §Export 대비)."""
    test = Test(
        id="TC-005",
        name="약관 새 창",
        authoring_mode=AuthoringMode.RECORD,
        start_url="https://example.internal/signup",
        steps=[
            ClickStep(id="step-01", label="약관", tab=0, target=target(test_id=cand("t"))),
            AssertionStep(
                id="step-02",
                label="제목",
                tab=1,
                assertion=Assertion(
                    kind=AssertionKind.VISIBLE, target=target(text=cand("약관"))
                ),
            ),
            CloseTabStep(id="step-03", label="닫기", tab=1),
        ],
    )
    code = generate_spec(test)
    assert "const [tab1] = await Promise.all([" in code
    assert "context.waitForEvent('page')" in code
    assert "await tab1.close();" in code
    # 새 탭 참조는 그 탭의 변수로 만들어진다 — `page` 로 새지 않는다.
    assert 'tab1.getByText("약관"' in code


# ─── 4. 민감 변수와 이스케이프 (헌법 §보안) ───────────────────────────────


def test_sensitive_variable_becomes_an_env_reference_only() -> None:
    """FR-089d-1 — 민감 값이 코드에 들어갈 경로가 없다."""
    renderer = values(Variable(name="LOGIN_PASSWORD", value=None, sensitive=True))
    step = FillStep(
        id="step-01",
        label="비밀번호",
        target=target(label=cand("비밀번호")),
        value="{{LOGIN_PASSWORD}}",
    )
    generated = line_of(step, renderer)
    assert "process.env.LOGIN_PASSWORD" in generated
    assert SECRET not in generated


def test_generated_spec_never_contains_a_decrypted_value() -> None:
    """생성기는 값을 볼 수 없다 — 해석기를 임포트하지 않는다.

    "실수로 넣지 않는다" 가 아니라 **넣을 수 없다**는 것이 요점이다.
    """
    import inspect

    from itb.generator import playwright_gen

    # 문서가 아니라 **실제 임포트**를 본다. 주석은 규칙을 지키게 하지 못한다.
    imported = {
        line.strip()
        for line in inspect.getsource(playwright_gen).splitlines()
        if line.startswith(("import ", "from "))
    }
    joined = " ".join(imported)
    assert "secrets" not in joined, joined
    assert "resolver" not in joined, joined
    # 값을 다루는 이름이 모듈 표면에도 없다.
    assert not [n for n in vars(playwright_gen) if "resolver" in n.lower()]


def test_non_sensitive_variable_is_inlined() -> None:
    """비민감 변수는 정의 파일에 값이 있으므로 리터럴로 넣는다."""
    renderer = values(Variable(name="PROJECT_NAME", value="TEST", sensitive=False))
    step = FillStep(
        id="step-01", label="이름", target=target(label=cand("이름")), value="{{PROJECT_NAME}}"
    )
    assert '"TEST"' in line_of(step, renderer)


def test_page_derived_text_is_escaped() -> None:
    """헌법 §보안 — 화면에서 온 텍스트로 코드를 깨거나 주입할 수 없다."""
    hostile = '"); await page.evaluate("alert(1)"); //'
    step = ClickStep(id="step-01", label="위험", target=target(text=cand(hostile)))
    generated = line_of(step)

    # 원문이 리터럴 밖으로 새지 않는다 — JSON 리터럴로 감싸여 있다.
    assert json.dumps(hostile, ensure_ascii=False) in generated
    assert "await page.evaluate" not in generated.replace(
        json.dumps(hostile, ensure_ascii=False), ""
    )


def test_newlines_and_quotes_survive_escaping() -> None:
    tricky = 'line1\nline2 "quoted" \\ backslash'
    step = AssertionStep(
        id="step-01",
        label="텍스트",
        assertion=Assertion(kind=AssertionKind.TEXT, value=tricky),
    )
    generated = line_of(step)
    assert "\n" not in generated.replace("\\n", "")
    assert json.dumps(tricky, ensure_ascii=False) in generated


def test_mixed_text_and_reference_is_composed_safely() -> None:
    """참조와 리터럴이 섞이면 각 조각을 이스케이프해 잇는다."""
    renderer = values(Variable(name="NAME", value=None, sensitive=True))
    step = FillStep(
        id="step-01",
        label="인사",
        target=target(label=cand("인사")),
        value='안녕 {{NAME}} "님"',
    )
    generated = line_of(step, renderer)
    assert "process.env.NAME" in generated
    assert '"안녕 "' in generated
    assert json.dumps(' "님"', ensure_ascii=False) in generated


# ─── 이식성 (원칙 V) ───────────────────────────────────────────────────────


def test_generated_project_does_not_depend_on_the_product() -> None:
    """원칙 V — 내보낸 자산이 제품 없이 돌아간다.

    생성물에 제품 모듈·API·런타임 심이 들어가면 이식성 약속이 깨진다.
    """
    test = Test(
        id="TC-001",
        name="로그인",
        authoring_mode=AuthoringMode.RECORD,
        start_url="https://example.internal/login",
        steps=[ClickStep(id="step-01", label="클릭", target=target(test_id=cand("a")))],
    )
    artifacts = [generate_spec(test), generate_config(), generate_package_json()]
    for artifact in artifacts:
        for forbidden in ("itb", "127.0.0.1:4320", "/api/", "localhost:4320"):
            assert forbidden not in artifact, f"제품 의존이 생성물에 있다: {forbidden}"

    assert "@playwright/test" in artifacts[0]
    assert "defineConfig" in artifacts[1]
    assert json.loads(artifacts[2])["devDependencies"]["@playwright/test"]


def test_ai_instruction_is_a_comment_not_an_instruction() -> None:
    """FR-063 — 지시문은 생성 코드에서도 주석이다. 실행되지 않는다."""
    test = Test(
        id="TC-002",
        name="AI 작성",
        authoring_mode=AuthoringMode.AI,
        start_url="https://example.internal/login",
        ai_instruction="로그인해서 프로젝트를 삭제해",
        steps=[ClickStep(id="step-01", label="클릭", target=target(test_id=cand("a")))],
    )
    code = generate_spec(test)
    assert "// 작성 의도: 로그인해서 프로젝트를 삭제해" in code
    for line in code.splitlines():
        if "로그인해서 프로젝트를 삭제해" in line:
            assert line.strip().startswith("//")


# ─── 004: 대기 예산이 생성 코드에 그대로 반영된다 (FR-118, SC-008) ───────────


def test_default_budget_reaches_the_generated_code() -> None:
    """제품 안과 내보낸 테스트가 **같은 시간을 기다린다** (004 FR-118).

    지연 로딩 화면에서 제품은 통과하는데 내보낸 테스트는 실패하는 상황을 막는 것이
    목적이다. 생성기가 `step.timeout_ms` 를 그대로 읽으므로 기본값 상향이 자동으로
    반영되는데, 그 "자동" 이 유지되는지는 확인해 둬야 한다 — 누군가 생성기에 상수를
    적어 넣으면 두 값이 갈린다.
    """
    from itb.domain.step import DEFAULT_TIMEOUT_MS

    step = ClickStep(id="step-01", label="클릭", target=target(test_id=cand("a")))
    assert step.timeout_ms == DEFAULT_TIMEOUT_MS
    assert f"timeout: {DEFAULT_TIMEOUT_MS}" in line_of(step), (
        "생성 코드가 Step 의 대기 예산을 쓰지 않는다"
    )


def test_per_step_budget_is_honoured_by_the_generator() -> None:
    """Step 별로 조정한 예산도 생성 코드에 실린다 (FR-115).

    느린 화면 하나 때문에 예산을 올린 사용자가, 내보낸 테스트에서는 기본값으로
    돌아가는 것을 보면 안 된다.
    """
    step = ClickStep(
        id="step-01", label="클릭", target=target(test_id=cand("a")), timeout_ms=30_000
    )
    assert "timeout: 30000" in line_of(step)


def test_generator_does_not_hardcode_a_timeout() -> None:
    """생성기 소스에 대기 시간 상수가 박혀 있지 않다.

    값이 두 곳에 있으면 한쪽만 바뀌는 날이 온다. 004 가 기본값을 5000 → 10000 으로
    올릴 때 생성기를 건드리지 않아도 됐던 것이 이 성질 덕이다.
    """
    import pathlib

    source = pathlib.Path("src/itb/generator/playwright_gen.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("timeout: 5000", "timeout: 10000", "= 5000", "= 10000"):
        assert forbidden not in source, (
            f"생성기에 대기 시간이 박혀 있다: {forbidden!r}"
        )


# ─── 5. 하위 프레임 (001 research 의 iframe 항목) ──────────────────────────


def test_subframe_step_wraps_the_locator_in_a_frame_locator() -> None:
    """`frame_url` 이 있는 Step 은 `frameLocator` 를 지난다.

    감싸지 않으면 내보낸 코드가 main frame 에서 요소를 찾아 반드시 실패한다 — 제품 내
    실행이 프레임을 해석하는 것과 **같은 문서**를 봐야 한다 (FR-022).
    """
    step = ClickStep(
        id="step-01",
        label="내장 저장 클릭",
        target=target(
            role="button",
            accessible_name="저장",
            role_status=CandidateStatus.VERIFIED,
            css=cand("button.btn"),
        ),
        frame_url="http://127.0.0.1:4300/embedded-inner.html",
    )
    line = line_of(step)
    assert 'page.frameLocator("iframe[src*=\\"embedded-inner.html\\"]")' in line, line
    assert '.getByRole("button", { name: "저장", exact: true })' in line, line


def test_frame_selector_drops_the_leading_slash() -> None:
    """`src` 가 상대 주소여도 걸리게 앞의 `/` 를 뗀다.

    `src="inner.html"` 은 `/inner.html` 을 포함하지 않는다. 떼지 않으면 상대 주소로 쓴
    iframe 을 하나도 찾지 못한다.
    """
    assert _frame_selector("https://app.example/a/b/inner.html?v=2") == (
        'iframe[src*="a/b/inner.html"]'
    )


def test_main_frame_step_is_not_wrapped() -> None:
    """`frame_url` 이 없으면 감싸지 않는다. 기존 정의의 출력이 바뀌면 안 된다."""
    step = ClickStep(id="step-01", label="저장 클릭", target=target(test_id=cand("save")))
    assert line_of(step) == 'await page.getByTestId("save").click({ timeout: 10000 });'


def test_url_assertion_in_a_subframe_still_checks_the_tab() -> None:
    """주소 검증은 프레임이 아니라 **탭**을 본다.

    iframe 안에서 기록됐다고 프레임의 주소를 재면 사용자가 뜻한 "현재 주소"(주소창)와
    달라진다. 제품 내 실행도 같은 판단을 한다 (`step_executor._assert`).
    """
    step = AssertionStep(
        id="step-01",
        label="주소 확인",
        assertion=Assertion(kind=AssertionKind.URL, value="https://app.example/done"),
        frame_url="http://127.0.0.1:4300/embedded-inner.html",
    )
    line = line_of(step)
    assert "frameLocator" not in line, line
    assert "await expect(page).toHaveURL" in line, line
