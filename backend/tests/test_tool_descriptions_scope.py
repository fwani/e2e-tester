"""AI 가 **실제로 받는 설명문**이 넓어진 권한을 말하는가. 026 FR-016 (research R8).

## 왜 docstring 이 아니라 `TOOL_SCHEMAS` 를 보는가

이 저장소에서 모델의 행동을 바꾸려면 세 자리를 같이 고쳐야 한다 — `TOOL_SCHEMAS` ·
메서드 docstring · `SYSTEM_PROMPT`. 그중 **모델이 실제로 받는 것은 `TOOL_SCHEMAS`** 이고,
거기 옛 문장이 남아 있으면 코드가 아무리 넓어져도 모델은 시도하지 않는다.

같은 형태의 누락이 이 저장소에서 이미 한 번 있었다 (025 `find_by_text` 순환: 도구가
참조를 주도록 고치고 docstring 과 SYSTEM_PROMPT 까지 고쳤는데 `TOOL_SCHEMAS` 가 남아
모델이 옛 안내를 따를 상태였다).

`TOOL_SCHEMAS` 는 순수 데이터이므로 선택 의존성(`claude_agent_sdk`) 없이 검사할 수 있다.
"""

from __future__ import annotations

import pytest

from itb.authoring.agent import SYSTEM_PROMPT
from itb.authoring.summary import STEP_EDIT_MARK
from itb.authoring.tools import STEP_EDITING_TOOLS, TOOL_SCHEMAS


@pytest.mark.parametrize("name", STEP_EDITING_TOOLS)
def test_every_editing_tool_tells_the_model_about_the_chosen_step(name: str) -> None:
    """넷 다 「사용자가 고쳐 달라고 지목한 Step」을 말해야 한다.

    하나라도 빠지면 그 도구만 옛 범위로 동작한다 — 모델이 대상을 고칠 수는 있는데
    대상 요소는 못 바꾸는, 설명하기 어려운 상태가 된다.
    """
    description = TOOL_SCHEMAS[name][0]
    assert "지목한 Step" in description, (
        f"{name} 의 설명문이 넓어진 권한을 말하지 않는다. "
        "이것이 모델이 실제로 받는 문장이며, 코드만 고치면 행동은 바뀌지 않는다."
    )


@pytest.mark.parametrize("name", STEP_EDITING_TOOLS)
def test_the_old_sentence_is_gone(name: str) -> None:
    """옛 문장이 남아 있으면 모델은 지목받은 Step 조차 시도하지 않는다."""
    description = TOOL_SCHEMAS[name][0]
    assert "다른 Step 은 고칠 수 없다" not in description
    assert "다른 Step 은 지울 수 없다" not in description


@pytest.mark.parametrize("name", ["update_step", "delete_step"])
def test_the_boundary_is_still_stated(name: str) -> None:
    """넓어졌다고 경계가 없어진 것이 아니다. 밖은 여전히 사람의 일이다.

    넷 중 둘만 보는 이유는 016 이 그렇게 써 두었기 때문이다 — `move_step` 과
    `repick_target` 은 범위 한정을 문장 앞머리로만 말한다. 그 한정은 위 검사가 본다.
    """
    description = TOOL_SCHEMAS[name][0]
    assert "그 밖의 Step 은" in description, f"{name} 의 설명문이 경계를 말하지 않는다"


def test_the_refusal_tells_the_model_what_to_do_instead() -> None:
    """거절만 받으면 모델은 같은 요청을 반복한다 (FR-016).

    **사람에게 무엇을 부탁하라는 것인지**가 문장에 있어야 한다.
    """
    assert "어느 Step 을 고르면 되는지" in TOOL_SCHEMAS["update_step"][0]


def test_the_system_prompt_names_the_mark_the_summary_actually_writes() -> None:
    """지침이 가리키는 표시와 요약이 쓰는 표시가 **같은 문자열**이어야 한다.

    둘이 갈리면 모델은 지침에 적힌 표시를 찾다 못 찾고, 지목받은 Step 을 알아보지
    못한다. 상수를 직접 비교해 고정한다.
    """
    assert STEP_EDIT_MARK in SYSTEM_PROMPT


def test_the_system_prompt_separates_the_two_marks() -> None:
    """「교체 구간」과 「고쳐 달라고 요구받은 Step」은 **뜻이 정반대**다.

    앞은 확정하면 사라지고 뒤는 남아서 고쳐진다. 지침이 둘을 구분하지 않으면 모델이
    016 의 「당신이 지우지 마세요」를 이쪽에도 적용해 고치기를 주저한다.
    """
    assert "◀ 교체 구간" in SYSTEM_PROMPT
    assert "다릅니다" in SYSTEM_PROMPT


def test_the_tool_surface_did_not_grow() -> None:
    """**도구가 하나도 늘지 않았다** (026 contracts/agent-tools §4).

    이 기능이 바꾼 것은 도구가 아니라 도구가 무엇에 쓸 수 있는가이다.
    """
    assert len(STEP_EDITING_TOOLS) == 4
    assert set(STEP_EDITING_TOOLS) == {
        "update_step",
        "delete_step",
        "move_step",
        "repick_target",
    }
