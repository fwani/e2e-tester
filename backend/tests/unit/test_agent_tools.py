"""도구 표면과 Step 종류의 1:1 대응. FR-086·research R5 (T106).

**이 테스트가 원칙 I 의 에이전트 쪽 증거다.** 도구가 Step 종류와 1:1 이면 "AI 결과를
결정적 Step 으로 컴파일"(FR-061)이 별도 변환이 아니라 기록의 부산물이 되고, 컴파일 단계에서
표현 불가능한 동작을 만나 실패하는 경우가 원리적으로 없다.

대응이 깨지는 방향은 둘이다.

1. **Step 종류가 늘었는데 도구가 없다** — 사람은 만들 수 있는데 AI 는 못 만든다.
   Step 종류가 8종이 된 뒤(T161) 실제로 이 상태였고 T163 이 회복했다.
2. **도구가 늘었는데 Step 이 없다** — 성공한 동작을 저장할 수 없다. `execute_javascript`
   가 그 예이며, 그래서 두지 않는다 (FR-086).

두 방향을 모두 고정한다. 자격 증명이 필요하지 않다 — 표면을 검사할 뿐이다.
"""

from __future__ import annotations

import inspect

from itb.authoring import tools as tools_mod
from itb.authoring.tools import STEP_PRODUCING_TOOLS, TOOL_NAMES, BrowserToolbox
from itb.domain.step import StepType

FORBIDDEN_TOOL_HINTS = (
    "execute_javascript",
    "eval",
    "evaluate",
    "shell",
    "exec",
    "screenshot_click",
    "request",
)
"""두어서는 안 되는 도구의 이름 조각.

`execute_javascript` 는 표현할 수 있는 Step 이 없고 FR-086(브라우저 조작 범위를 넘는 동작
금지)에도 걸린다. 셸 실행은 헌법 §보안이 금지한다.
"""


def test_step_producing_tools_match_step_types_one_to_one() -> None:
    """Step 을 만드는 도구와 Step 종류가 정확히 대응한다 (T163).

    `assert_condition` 만 이름이 다르다 — Step 종류는 `assertion` 이다. 그 외에는
    도구 이름이 곧 Step 종류다.
    """
    step_types = {t.value for t in StepType}
    tool_targets = {
        "assertion" if name == "assert_condition" else name
        for name in STEP_PRODUCING_TOOLS
    }
    assert tool_targets == step_types, (
        f"도구 표면과 Step 종류가 1:1 이 아니다. "
        f"도구만 있는 것: {tool_targets - step_types}, "
        f"Step 만 있는 것: {step_types - tool_targets}"
    )


def test_hover_and_drag_are_covered() -> None:
    """T163 — hover·drag 가 도구 표면에 있다.

    이 둘이 없으면 plan.md 원칙 I 게이트의 PASS 근거("도구 표면이 Step 종류와 1:1")가
    참이 아니고, T113 컴파일러가 그 근거에 의존한다.
    """
    assert "hover" in STEP_PRODUCING_TOOLS
    assert "drag" in STEP_PRODUCING_TOOLS


def test_toolbox_implements_every_declared_tool() -> None:
    """선언한 도구 이름마다 실제 메서드가 있다.

    목록과 구현이 갈리면 SDK 에 넘긴 스키마와 실행되는 코드가 달라진다.
    """
    for name in TOOL_NAMES:
        method = getattr(BrowserToolbox, name, None)
        assert method is not None, f"도구 {name} 의 구현이 없다"
        assert inspect.iscoroutinefunction(method), f"{name} 은 async 여야 한다"


def test_no_arbitrary_execution_tool_exists() -> None:
    """FR-086 — 임의 실행 도구가 없다. **부재를 테스트로 고정한다.**"""
    for name in TOOL_NAMES:
        for hint in FORBIDDEN_TOOL_HINTS:
            assert hint not in name, f"금지된 도구가 표면에 있다: {name}"

    surface = {
        name
        for name, value in vars(BrowserToolbox).items()
        if inspect.iscoroutinefunction(value) and not name.startswith("_")
    }
    assert surface == set(TOOL_NAMES), (
        f"선언되지 않은 공개 도구가 있다: {surface - set(TOOL_NAMES)}"
    )


def test_tools_that_do_not_produce_steps_are_all_accounted_for() -> None:
    """Step 을 만들지 않는 도구가 **전부 어느 분류엔가 들어 있다**.

    ## 016 이 이 검사를 다시 적었다

    이전 문장은 「`list_tabs`·`observe_page`·`report_blocked` 셋」이었다. 016 이 편집
    도구 넷을 더하면서 그 셋이 일곱이 됐고, 검사가 실패했다 — **검사가 제 일을 한
    것이다.** 목록을 늘리는 대신 분류로 답한다.

    읽기 전용·제어·편집 도구가 Step 을 만들면 정의에 실행할 것이 없는 Step 이 들어간다.
    분류의 정합성 자체는 `test_tool_surface.py` 가 본다.
    """
    from itb.authoring.tools import CONTROL_TOOLS, READ_ONLY_TOOLS, STEP_EDITING_TOOLS

    non_producing = set(TOOL_NAMES) - set(STEP_PRODUCING_TOOLS)
    classified = set(READ_ONLY_TOOLS) | set(CONTROL_TOOLS) | set(STEP_EDITING_TOOLS)
    assert non_producing == classified, (
        f"어느 분류에도 없는 도구가 있다: {sorted(non_producing - classified)}"
    )


def test_module_does_not_import_sdk_at_module_level() -> None:
    """`BrowserToolbox` 는 SDK 를 알지 못한다.

    안다면 자격 증명 없이 도구 동작을 테스트할 수 없고, 원칙 II 의 동적 검증(SC-006)도
    이 지점을 쓸 수 없다.
    """
    source = inspect.getsource(tools_mod)
    module_level = [
        line
        for line in source.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    assert all("anthropic" not in line for line in module_level), module_level
