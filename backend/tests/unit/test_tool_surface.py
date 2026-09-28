"""도구 표면 계약. 016 T052 (contracts/agent-tools.md §1).

**이 파일이 계약이다.** 도구를 더하거나 빼면 여기가 먼저 실패하고, 작성자는 그것이
어느 분류에 속하는지 답해야 한다.

## 016 이 무엇을 바꿨는가

옛 `TOOL_NAMES` 주석은 「이 목록이 계약이다 — 늘리면 Step 종류와의 1:1 이 깨진다」였다.
그 문장은 정확히는 `STEP_PRODUCING_TOOLS` 에 대한 것이었다 — 실제로 `observe_page`·
`list_tabs`·`report_blocked` 셋이 Step 을 만들지 않으면서 목록에 있었고, 그 사실을 적을
자리가 없었다.

016 은 계약을 **넓힌 것이 아니라 정확히 적었다.** 네 분류로 갈라 전수를 검사한다.
"""

from __future__ import annotations

import inspect

import pytest

from itb.authoring import tools as tools_mod
from itb.authoring.tools import (
    CONTROL_TOOLS,
    READ_ONLY_TOOLS,
    STEP_EDITING_TOOLS,
    STEP_PRODUCING_TOOLS,
    TOOL_NAMES,
    TOOL_SCHEMAS,
    BrowserToolbox,
)
from itb.domain.step import StepType

CLASSES = {
    "READ_ONLY_TOOLS": READ_ONLY_TOOLS,
    "STEP_PRODUCING_TOOLS": STEP_PRODUCING_TOOLS,
    "STEP_EDITING_TOOLS": STEP_EDITING_TOOLS,
    "CONTROL_TOOLS": CONTROL_TOOLS,
}


# ─── 검사 1 — 네 분류가 표면을 정확히 덮는다 ────────────────────────────────


def test_the_four_classes_cover_the_surface_exactly() -> None:
    """합집합이 `TOOL_NAMES` 와 같고 **교집합이 없다**.

    빠진 도구가 있으면 그것은 「어느 분류인지 아무도 답하지 않은 도구」다. 두 분류에
    든 도구가 있으면 「Step 을 만들면서 동시에 고치는 도구」이며, 그런 것이 생기면
    되돌리기의 대상이 불분명해진다.
    """
    union: list[str] = []
    for group in CLASSES.values():
        union.extend(group)

    assert set(union) == set(TOOL_NAMES), (
        f"분류에서 빠진 도구: {sorted(set(TOOL_NAMES) - set(union))} / "
        f"표면에 없는데 분류된 도구: {sorted(set(union) - set(TOOL_NAMES))}"
    )
    assert len(union) == len(set(union)), "두 분류에 든 도구가 있다"
    # 023 이 `press` 를 더해 17종이 됐다. **Step 종류가 늘어서 늘어난 것**이며,
    # 아래 1:1 대응 검사가 그 사실을 강제한다 — 종류 없이 도구만 늘면 거기서 깨진다.
    assert len(TOOL_NAMES) == 17, f"023 이후 표면은 17종이다 (지금 {len(TOOL_NAMES)})"


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_every_tool_has_a_method_on_the_toolbox(name: str) -> None:
    """모든 도구가 `BrowserToolbox` 의 메서드를 부른다.

    도구가 툴박스 밖에서 일을 하면 자격 증명 없이 검증할 수 없고, 그것이 이 클래스가
    SDK 를 알지 못하게 둔 이유다.
    """
    assert hasattr(BrowserToolbox, name), f"툴박스에 {name} 메서드가 없다"


# ─── 검사 2 — Step 종류와 1:1 (기존, 016 이 건드리지 않는다) ────────────────


def test_step_producing_tools_map_one_to_one_with_step_types() -> None:
    """**016 은 이 대응을 건드리지 않는다** (FR-040).

    편집 도구가 넷 늘었지만 새 Step 종류를 만들지 않는다. 종류를 더하고 도구를 빼면
    「사람은 만들 수 있는데 AI 는 만들 수 없는 Step 종류」가 생긴다.
    """
    # `assert_condition` 이 `assertion` 종류를 만든다 — 이름만 다르고 대응은 1:1 이다.
    expected = {t.value for t in StepType} - {"assertion"} | {"assert_condition"}
    assert set(STEP_PRODUCING_TOOLS) == expected, (
        f"Step 종류와 어긋났다. 도구에만 있는 것: "
        f"{sorted(set(STEP_PRODUCING_TOOLS) - expected)} / "
        f"종류에만 있는 것: {sorted(expected - set(STEP_PRODUCING_TOOLS))}"
    )
    assert len(STEP_PRODUCING_TOOLS) == 10


def test_editing_tools_create_no_step_type() -> None:
    """편집 도구는 Step **종류**를 만들지 않는다 (FR-040)."""
    kinds = {t.value for t in StepType}
    for name in STEP_EDITING_TOOLS:
        assert name not in kinds, f"{name} 이 Step 종류 이름과 겹친다"


# ─── 검사 3 — 편집 도구가 사람 편집과 같은 함수를 지난다 (원칙 I) ───────────


EXPECTED_SHARED_FUNCTIONS = {
    "update_step": "update_step",
    "delete_step": "delete_step",
    "move_step": "reorder_steps",
    # `repick_target` 은 순수 편집 함수를 지나지 않는다 — 목록을 손대지 않고 Step
    # 하나를 바꿔 끼운다. 대신 `collect_by_selector`(사람의 다시 집기와 같은 수집기)를
    # 지나는 것이 그쪽의 같음이다.
    "repick_target": "collect_by_selector",
}
"""편집 도구가 **사람 편집 경로와 공유하는 함수**.

원칙 I 이 문서의 약속이 아니라 코드의 성질이 되는 지점이다 — 같은 함수를 지나면 결과가
다를 수가 없다. 목록에서 이름이 빠지면 그 도구가 자기만의 길을 냈다는 뜻이다.
"""


@pytest.mark.parametrize(("tool", "shared"), sorted(EXPECTED_SHARED_FUNCTIONS.items()))
def test_editing_tools_go_through_the_same_functions_humans_do(
    tool: str, shared: str
) -> None:
    """**원칙 I 의 증거** (FR-036 · SC-006).

    `itb.api.routes.steps`(사람)와 `itb.authoring.tools`(AI)가 같은 함수를 부른다.
    """
    ai_source = inspect.getsource(getattr(BrowserToolbox, tool))
    assert shared in ai_source, f"{tool} 이 {shared} 을 지나지 않는다 — 원칙 I 위반"

    from itb.api.routes import steps as human_routes

    human_source = inspect.getsource(human_routes)
    assert shared in human_source, (
        f"사람 경로가 {shared} 을 쓰지 않는다 — 공유 함수 목록이 낡았다"
    )


def test_editing_tools_never_build_their_own_step_list() -> None:
    """편집 도구가 목록을 **직접 만들지 않는다**.

    `w.steps = [...]` 같은 코드가 도구 안에 생기면 편집 규칙이 두 벌이 된다. 도구는
    편집 연산이 돌려준 `EditResult` 를 sink 로 넘기기만 한다.
    """
    for tool in STEP_EDITING_TOOLS:
        source = inspect.getsource(getattr(BrowserToolbox, tool))
        assert "self.on_edit(" in source, f"{tool} 이 편집 sink 를 지나지 않는다"


# ─── 검사 4 — 스키마 키가 표면과 같다 (개발용 드라이버) ─────────────────────


def test_tool_schemas_match_the_surface() -> None:
    """`TOOL_SCHEMAS` 의 키가 `TOOL_NAMES` 와 같다.

    빠뜨리면 **기본 드라이버에서는 되고 개발용에서는 안 되는 도구**가 생긴다 —
    `QUALIFIED_TOOL_NAMES` 가 이 사전에서 파생되기 때문이다.
    """
    assert set(TOOL_SCHEMAS) == set(TOOL_NAMES), (
        f"스키마에 없는 도구: {sorted(set(TOOL_NAMES) - set(TOOL_SCHEMAS))} / "
        f"표면에 없는 스키마: {sorted(set(TOOL_SCHEMAS) - set(TOOL_NAMES))}"
    )


@pytest.mark.parametrize("name", sorted(TOOL_SCHEMAS))
def test_every_schema_has_a_description_and_a_shape(name: str) -> None:
    description, schema = TOOL_SCHEMAS[name]
    assert description.strip(), f"{name} 에 설명이 없다"
    assert schema.get("type") == "object", f"{name} 의 스키마가 object 가 아니다"


def test_build_tools_returns_the_whole_surface() -> None:
    """`build_tools` 가 도구를 빠뜨리지 않는다.

    **정적으로 본다** — 툴박스를 만들려면 브라우저 세션이 필요하고, 이 검사는 단위
    계층에 있어야 한다 (도구 표면은 브라우저와 무관한 계약이다).
    """
    source = inspect.getsource(tools_mod.build_tools)
    for name in TOOL_NAMES:
        assert f"async def {name}(" in source, f"build_tools 에 {name} 이 없다"


# ─── 021 — 어휘가 늘어도 도구 표면은 그대로다 ──────────────────────────────


def test_new_assertion_vocabulary_did_not_grow_the_surface() -> None:
    """**검증 종류가 늘었다고 도구가 늘면 안 된다** (021 contracts/assertion-surface §3).

    도구 표면은 계약이고 Step 종류와 1:1 이다. 새 검증 어휘는 기존 검증 도구의 **인자
    값**으로 들어간다. 여기서 그 경계를 따로 말하는 이유는 **어휘 추가와 도구 추가를
    가르는 선**을 이 파일에 남겨 두기 위해서다.

    ## 023 에서 이 검사를 숫자에서 규칙으로 바꿨다

    원래는 `len(TOOL_NAMES) == 16` 과 `len(STEP_PRODUCING_TOOLS) == 9` 로 적혀 있었다.
    023 이 검증 종류(`value`)와 Step 종류(`press`)를 **함께** 더하자 두 숫자가 모두
    깨졌는데, **깨진 방식이 이 검사가 막으려던 것과 무관했다** — `value` 는 도구를
    늘리지 않았고, 늘어난 하나는 `press` 라는 Step 종류 때문이었다.

    숫자로 적으면 종류가 늘 때마다 이 검사를 고쳐야 하고, 고치는 사람은 **무엇을 확인하던
    검사였는지 모른 채** 숫자만 바꾸게 된다. 그래서 뜻을 그대로 적는다: 검증 종류가 몇
    개든 그것을 다루는 도구는 `assert_condition` **하나**이고, 일곱 종류가 모두 그
    하나를 지난다.
    """
    from itb.domain.assertion import AssertionKind

    assertion_tools = [n for n in TOOL_NAMES if n.startswith("assert")]
    assert assertion_tools == ["assert_condition"], (
        f"검증 도구는 하나여야 한다. 지금: {assertion_tools}"
    )

    # 일곱 종류가 모두 그 하나의 인자로 들어간다 — 종류마다 도구를 만들지 않는다.
    _, schema = TOOL_SCHEMAS["assert_condition"]
    kinds = set(schema["properties"]["kind"]["enum"])
    assert kinds == {k.value for k in AssertionKind}, (
        "검증 종류가 도구 인자와 어긋났다 — 모델이 쓸 수 있는 어휘를 모른 채 작성한다"
    )


def test_the_assertion_tool_enum_matches_the_domain() -> None:
    """도구 스키마의 종류·비교 목록이 도메인 열거형과 같다.

    손으로 옮겨 적으면 도메인에 값을 더했을 때 도구만 뒤처지고, 모델은 쓸 수 있는
    어휘를 모른 채 작성한다. **목록을 베끼지 않고 도메인에서 읽는지**를 본다.
    """
    from itb.authoring.tools import TOOL_SCHEMAS
    from itb.domain.assertion import AssertionKind, MatchMode

    _, schema = TOOL_SCHEMAS["assert_condition"]
    props = schema["properties"]
    assert set(props["kind"]["enum"]) == {k.value for k in AssertionKind}
    assert set(props["match"]["enum"]) == {m.value for m in MatchMode}


def test_the_authoring_guidance_tells_the_model_not_to_flip_a_negated_check() -> None:
    """020 이 「값을 바꾸지 마라」를 넣은 자리에 부정형 판이 있어야 한다.

    없으면 020 이 막은 일이 부정형에서 되풀이된다 — 모델에게는 조건을 뒤집어
    통과시키는 것이 가장 쉬운 길이다.
    """
    from itb.authoring.agent import SYSTEM_PROMPT

    assert "뒤집지 마세요" in SYSTEM_PROMPT
    assert "not_contains" in SYSTEM_PROMPT
    assert "눌러 보고" in SYSTEM_PROMPT, "비활성 버튼을 눌러 확인하지 말라는 말이 없다"
