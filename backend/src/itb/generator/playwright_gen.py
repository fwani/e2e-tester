"""Step → Playwright 코드 생성. 헌법 원칙 V (T143·T164).

**Export 명령 자체는 이번 범위가 아니다** (plan.md Complexity Tracking, 릴리스 게이트 RG-1).
여기서 만드는 것은 그 명령이 쓸 생성기이며, 지금 자리를 잡아 두는 이유는 두 가지다.

1. **후보 선택을 `choose_strategy` 한 곳에서 가져온다** (원칙 IV). Runner 가 쓰는 판단과
   생성된 코드가 같은 후보를 고른다. 나중에 붙일 때 우선순위 로직을 다시 짜지 않는다.
2. **DSL↔Playwright 대응이 실제로 성립하는지 지금 확인한다.** 대응표만 문서로 두면
   Step 종류가 늘 때 조용히 빠진다 — hover·drag 가 실제로 그럴 뻔했다 (T164).

**보안 요건 (헌법 §Technology & Security Constraints)**

- 대상 화면에서 온 텍스트는 **모두 JSON 리터럴로 이스케이프**한다. 문자열을 이어 붙여
  코드를 만들지 않는다. `_js` 를 지나지 않고 코드에 들어가는 값이 있으면 그것이 결함이다.
- 민감 변수는 **변수 참조로만** 생성한다 (FR-089d-1). 복호화된 값이 생성 코드에 들어가는
  경로가 없다 — 이 모듈은 값을 볼 수 없다. `VariableResolver` 를 임포트하지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlsplit

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    SelectStep,
    Step,
    UploadStep,
    mime_type_of,
)
from itb.domain.test_case import Test, Variable
from itb.locator.strategy import LocatorStrategy, StrategyKind, choose_strategy

INDENT = "  "


class UnsupportedStepError(Exception):
    """생성할 수 없는 Step.

    **도구 표면·실행기와 달리 생성기는 종류를 열거한다.** 종류가 늘면 여기서 실패해야
    한다 — 조용히 건너뛰면 내보낸 테스트가 원본보다 적게 실행되고, 그 사실이 드러나지
    않는다 (원칙 V 의 증분 의무).
    """


class NoUsableCandidateError(Exception):
    """확보된 후보가 하나도 없다.

    조용히 CSS 로 떨어지지 않는다 — 그 CSS 도 검증에 실패한 것이므로, 생성하면 반드시
    깨지는 코드가 된다.
    """


def _js(value: str) -> str:
    """문자열을 JS 리터럴로 만든다. **대상 화면에서 온 값은 반드시 이것을 지난다.**

    `json.dumps` 를 쓰는 이유는 JSON 문자열 리터럴이 JS 문자열 리터럴의 부분집합이기
    때문이다. 따옴표·역슬래시·제어 문자·유니코드가 모두 안전하게 처리된다.
    """
    return json.dumps(value, ensure_ascii=False)


def _tab_var(tab: int) -> str:
    """탭 참조에 대응하는 변수 이름. 최초 탭은 `page` 다."""
    return "page" if tab == 0 else f"tab{tab}"


# ─── 값과 변수 (FR-089d-1) ─────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ValueRenderer:
    """`{{변수}}` 참조를 JS 식으로 바꾼다.

    민감 변수는 `process.env.NAME` 이 된다 — **값을 코드에 넣지 않는다.** 비민감 변수는
    정의 파일에 값이 있으므로 리터럴로 넣는다. 그 구분이 이 클래스의 전부다.
    """

    variables: dict[str, Variable]

    @classmethod
    def of(cls, test: Test) -> ValueRenderer:
        return cls({v.name: v for v in test.variables})

    def render(self, raw: str) -> str:
        """값 하나를 JS 식으로. 참조가 없으면 단순 리터럴이다."""
        import re

        parts: list[str] = []
        cursor = 0
        for match in re.finditer(r"\{\{([A-Z][A-Z0-9_]*)\}\}", raw):
            if match.start() > cursor:
                parts.append(_js(raw[cursor : match.start()]))
            parts.append(self._reference(match.group(1)))
            cursor = match.end()
        if cursor < len(raw):
            parts.append(_js(raw[cursor:]))
        if not parts:
            return _js("")
        # 각 조각이 이미 리터럴이거나 식이므로 이어 붙여도 주입 경로가 없다.
        return " + ".join(parts) if len(parts) > 1 else parts[0]

    def _reference(self, name: str) -> str:
        variable = self.variables.get(name)
        if variable is None or variable.sensitive or variable.value is None:
            # 민감하거나 값이 없는 변수는 환경에서 받는다 (FR-089g).
            return f"process.env.{name}"
        return _js(variable.value)


# ─── Locator (원칙 IV — `choose_strategy` 공유) ────────────────────────────


def locator_expression(strategy: LocatorStrategy, tab_var: str) -> str:
    """전략 하나를 Playwright locator 식으로. **후보 선택은 하지 않는다.**

    무엇을 고를지는 `choose_strategy` 가 정한다. 이 함수는 고른 것을 표현할 뿐이다 —
    그래서 Runner 와 생성기가 같은 요소를 잡는다 (FR-022).
    """
    args = strategy.args
    match strategy.kind:
        case StrategyKind.TEST_ID:
            return f"{tab_var}.getByTestId({_js(args['test_id'])})"
        case StrategyKind.ROLE:
            return (
                f"{tab_var}.getByRole({_js(args['role'])}, "
                f"{{ name: {_js(args['name'])}, exact: true }})"
            )
        case StrategyKind.LABEL:
            return f"{tab_var}.getByLabel({_js(args['label'])}, {{ exact: true }})"
        case StrategyKind.TEXT:
            return f"{tab_var}.getByText({_js(args['text'])}, {{ exact: true }})"
        case StrategyKind.STABLE_ATTR:
            selector = f"[{args['name']}={json.dumps(args['value'])}]"
            return f"{tab_var}.locator({_js(selector)})"
        case StrategyKind.CSS:
            return f"{tab_var}.locator({_js(args['css'])})"
    msg = f"알 수 없는 후보 종류입니다: {strategy.kind}"  # pragma: no cover
    raise UnsupportedStepError(msg)  # pragma: no cover


def _frame_selector(frame_url: str) -> str:
    """프레임 주소 → 그 `<iframe>` 요소를 가리키는 선택자.

    **내보낸 코드는 주소로 프레임을 찾을 수 없다.** 제품 내 실행은 `page.frames` 를 주소로
    걸러 쓰지만(`itb.execution.frame_resolver`), Playwright 의 `frameLocator` 는 iframe
    **요소**의 선택자를 받는다. 표준 Playwright 에는 주소로 프레임을 잡는 locator 가 없다.

    그래서 주소의 **경로 부분으로 `src` 를 부분 일치**시킨다. `src` 가 상대 주소든 절대
    주소든 걸리게 하려면 앞의 `/` 를 떼야 한다 — `src="inner.html"` 은 `/inner.html` 을
    포함하지 않는다.

    한계: 같은 경로의 iframe 이 둘이면 Playwright 가 strict 위반으로 실패한다. 조용히 첫
    번째를 고르지 않으므로 **잘못된 프레임을 조작하지는 않는다** — 제품 내 실행이 같은
    주소 여러 개를 채택하지 않는 것과 같은 판단이다.
    """
    parts = urlsplit(frame_url)
    token = parts.path.lstrip("/") or parts.netloc or frame_url
    return f'iframe[src*="{token}"]'


def _locator_root(step: Step) -> str:
    """요소를 찾을 대상. 하위 프레임 Step 이면 `frameLocator` 로 감싼다.

    탭 변수 자체(`page`·`tab1`)는 화면 이동·주소 검증·탭 닫기가 계속 쓴다 — 그 셋은
    프레임이 아니라 탭에 대한 동작이다.
    """
    tab = _tab_var(step.tab)
    frame_url = getattr(step, "frame_url", None)
    if not frame_url:
        return tab
    return f"{tab}.frameLocator({_js(_frame_selector(frame_url))})"


def _locator_for(target: object, tab_var: str, label: str) -> str:
    strategy = choose_strategy(target)  # type: ignore[arg-type]
    if strategy is None:
        msg = (
            f"'{label}' 의 확보된 후보가 없어 코드를 만들 수 없습니다. "
            "Step 상세에서 대상을 다시 집으세요 (FR-020)."
        )
        raise NoUsableCandidateError(msg)
    return locator_expression(strategy, tab_var)


# ─── Step → 코드 ───────────────────────────────────────────────────────────


def _timeout(step: Step) -> str:
    return f"{{ timeout: {step.timeout_ms} }}"


def step_lines(step: Step, values: ValueRenderer) -> list[str]:
    """Step 하나를 코드 줄들로. 탭 준비 줄은 호출자가 앞에 붙인다."""
    tab = _tab_var(step.tab)
    root = _locator_root(step)
    match step:
        case NavigateStep():
            return [f"await {tab}.goto({values.render(step.url)});"]
        case ClickStep():
            loc = _locator_for(step.target, root, step.label)
            return [f"await {loc}.click({_timeout(step)});"]
        case HoverStep():
            loc = _locator_for(step.target, root, step.label)
            return [f"await {loc}.hover({_timeout(step)});"]
        case FillStep():
            loc = _locator_for(step.target, root, step.label)
            return [f"await {loc}.fill({values.render(step.value)}, {_timeout(step)});"]
        case SelectStep():
            loc = _locator_for(step.target, root, step.label)
            return [
                f"await {loc}.selectOption({values.render(step.value)}, {_timeout(step)});"
            ]
        case UploadStep():
            loc = _locator_for(step.target, root, step.label)
            """파일 업로드 (2026-09-09).

            **제품의 재실행과 같은 것을 올린다** — 같은 이름·같은 MIME 의 빈 바이트다
            (`step_executor._upload`). 디스크를 만지지 않으므로 내보낸 코드가 다른
            기계에서도 그대로 돈다.
            """
            payload = (
                "{ "
                f"name: {_js(step.file_name)}, "
                f"mimeType: {_js(mime_type_of(step.file_name))}, "
                "buffer: Buffer.alloc(0) "
                "}"
            )
            return [f"await {loc}.setInputFiles({payload}, {_timeout(step)});"]
        case DragStep():
            source = _locator_for(step.target, root, step.label)
            destination = _locator_for(step.drop_target, root, f"{step.label} (놓는 위치)")
            return [f"await {source}.dragTo({destination}, {_timeout(step)});"]
        case CloseTabStep():
            return [f"await {tab}.close();"]
        case AssertionStep():
            return _assertion_lines(step.assertion, tab, root, values, step)
    msg = f"생성할 수 없는 Step 종류입니다: {type(step).__name__}"
    raise UnsupportedStepError(msg)


def _assertion_lines(
    assertion: Assertion, tab: str, root: str, values: ValueRenderer, step: Step
) -> list[str]:
    """검증 4종 (FR-013a). `hidden` 은 없던 요소도 통과한다 — `toBeHidden` 과 같은 의미다.

    **주소 검증만 `tab` 을 쓴다.** 하위 프레임 안의 Step 이라도 사용자가 뜻한 "현재 주소"
    는 주소창의 주소다 — 제품 내 실행도 같은 판단을 한다 (`step_executor._assert`).
    """
    options = f"{{ timeout: {step.timeout_ms} }}"
    match assertion.kind:
        case AssertionKind.VISIBLE:
            loc = _locator_for(assertion.target, root, step.label)
            return [f"await expect({loc}).toBeVisible({options});"]
        case AssertionKind.HIDDEN:
            loc = _locator_for(assertion.target, root, step.label)
            return [f"await expect({loc}).toBeHidden({options});"]
        case AssertionKind.TEXT:
            expected = values.render(assertion.value or "")
            matcher = (
                "toContainText" if assertion.match is MatchMode.CONTAINS else "toHaveText"
            )
            if assertion.target is None:
                # 화면 전체가 대상이다 (data-model §5).
                return [
                    f"await expect({root}.locator({_js('body')}))."
                    f"{matcher}({expected}, {options});"
                ]
            loc = _locator_for(assertion.target, root, step.label)
            return [f"await expect({loc}).{matcher}({expected}, {options});"]
        case AssertionKind.URL:
            expected = values.render(assertion.value or "")
            if assertion.match is MatchMode.CONTAINS:
                # 정규식으로 만들지 않는다 — 화면에서 온 값이 패턴으로 해석되면
                # 의미가 달라진다. 문자열 포함으로 확인한다.
                return [f"expect({tab}.url()).toContain({expected});"]
            return [f"await expect({tab}).toHaveURL({expected}, {options});"]
    msg = f"지원하지 않는 검증 종류입니다: {assertion.kind}"  # pragma: no cover
    raise UnsupportedStepError(msg)  # pragma: no cover


def _tab_open_lines(tab: int, opener_lines: list[str]) -> list[str]:
    """새 탭을 여는 동작을 `waitForEvent('page')` 로 감싼다 (contracts/step-dsl §Export 대비).

    **탭이 열리는 것 자체는 Step 이 아니다** (FR-030b). 새 탭을 참조하는 Step 을 만났을 때,
    그 탭을 열게 한 **직전 동작**을 이 형태로 다시 쓴다.
    """
    var = _tab_var(tab)
    body = "\n".join(f"{INDENT}{INDENT}{line}" for line in opener_lines)
    return [
        f"const [{var}] = await Promise.all([",
        f"{INDENT}context.waitForEvent('page'),",
        f"{INDENT}(async () => {{",
        body,
        f"{INDENT}}})(),",
        "]);",
        f"await {var}.waitForLoadState();",
    ]


def generate_body(test: Test) -> list[str]:
    """테스트 본문 줄들. 탭 준비를 앞당겨 끼워 넣는다."""
    values = ValueRenderer.of(test)
    known_tabs = {0}
    lines: list[str] = [f"await page.goto({_js(test.start_url)});"]

    for index, step in enumerate(test.steps):
        current = step_lines(step, values)

        # 다음 Step 이 아직 없는 탭을 참조하면, 지금 동작이 그 탭을 여는 동작이다.
        next_step = test.steps[index + 1] if index + 1 < len(test.steps) else None
        opens_tab = (
            next_step is not None
            and next_step.tab not in known_tabs
            and step.tab in known_tabs
        )

        if step.tab not in known_tabs:
            # 여는 동작을 앞에서 감싸지 못한 경우 — 정의가 순서를 보장하지 않는다.
            # 조용히 넘기지 않고, 열리기를 기다리는 코드를 만든다.
            var = _tab_var(step.tab)
            lines.append(
                f"const {var} = context.pages()[{step.tab}] "
                f"?? await context.waitForEvent('page');"
            )
            lines.append(f"await {var}.waitForLoadState();")
            known_tabs.add(step.tab)

        if opens_tab and next_step is not None:
            lines.extend(_tab_open_lines(next_step.tab, current))
            known_tabs.add(next_step.tab)
            continue

        lines.extend(current)

    return lines


def generate_spec(test: Test) -> str:
    """테스트 하나를 Playwright spec 파일 내용으로 만든다.

    **생성된 코드는 제품 API 를 호출하지 않는다** (원칙 V). 표준 Playwright 만 쓴다.
    """
    body = generate_body(test)
    indented = "\n".join(f"{INDENT}{INDENT}{line}" for line in body)
    sensitive = [v.name for v in test.variables if v.sensitive]
    env_note = (
        "\n".join(
            f"// 환경 변수 필요: {name} (민감 값은 코드에 담기지 않는다)"
            for name in sensitive
        )
        + "\n"
        if sensitive
        else ""
    )
    intent = (
        f"// 작성 의도: {test.ai_instruction.strip().splitlines()[0]}\n"
        if test.ai_instruction
        else ""
    )
    return (
        "import { test, expect } from '@playwright/test';\n\n"
        f"{env_note}{intent}"
        f"test({_js(test.name)}, async ({{ page, context }}) => {{\n"
        f"{indented}\n"
        "});\n"
    )


def generate_config() -> str:
    """`playwright.config.ts`. 제품 런타임에 의존하지 않는다 (원칙 V)."""
    return (
        "import { defineConfig } from '@playwright/test';\n\n"
        "export default defineConfig({\n"
        f"{INDENT}testDir: './tests',\n"
        f"{INDENT}use: {{ browserName: 'chromium' }},\n"
        "});\n"
    )


def generate_package_json(name: str = "exported-tests") -> str:
    """의존성 매니페스트. 표준 도구 사슬만 요구한다."""
    return json.dumps(
        {
            "name": name,
            "private": True,
            "scripts": {"test": "playwright test"},
            "devDependencies": {"@playwright/test": "^1.49.0"},
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"
