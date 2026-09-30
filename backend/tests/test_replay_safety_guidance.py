"""작성한 정의가 **재실행에서도 통과하도록** 지침이 말하는가 (2026-09-30 사용자 보고).

## 무엇이 문제였나

보고 문장: 「ai 가 생성한 스텝이 재실행하면 에러가난다. ai 는 현상황에서 성공하는
스텝을 생성하는 것이 목적인데, 잘못된 데이터를 생성해두어서 그런지 모르겠다.」

TC-005 를 봤다. 로케이터는 멀쩡했다 — 세 Step 모두 `match_count: 1` 로 정확히 찾았다.
깨진 것은 **무엇을 성공으로 볼지**와 **기다림을 어디에 적을지**였다.

| Step | 기록 | 화면에서 실제로 일어난 일 |
|---|---|---|
| 저장 클릭 | pass (32ms) | 거부됨. 「연결 테스트를 하세요」만 떴다 |
| 연결 테스트 클릭 | pass (39ms) | 서버 ping 시작 — **비동기** |
| 저장 클릭 | pass (37ms) | 확인 중이라 또 거부됨 |

`network.log` 에 등록 요청이 하나도 없다. 저장을 두 번 눌렀는데 두 번 다 아무 일도
일어나지 않았고, 제품은 두 번 다 통과로 적었다.

## 제품이 보장할 수 있는 것과 없는 것

`_execute` 는 조작이 예외를 던지지 않으면 Step 을 확정한다. 「화면이 의도대로 바뀌었다」를
제품이 판정하게 만들지 않은 이유는 `delete_step` 의 docstring 에 적었다 — 그 기준을
제품이 정하면 오탐이 조용히 Step 을 버린다.

그래서 방어는 지침 한 줄이고, **약한 방어다.** 모델이 어기면 막을 것이 없다
(`test_no_alternate_route` 의 머리말이 같은 한계를 적어 두었다). 이 파일이 하는 일은
그 한 줄이 **조용히 사라지지 않게** 붙잡는 것뿐이다.

`TOOL_SCHEMAS` 를 함께 보는 이유는 `test_tool_descriptions_scope` 에 적혀 있다 —
모델이 실제로 받는 것은 그쪽이고, 거기 옛 문장이 남으면 지침만 고쳐도 행동은 안 바뀐다.
"""

from __future__ import annotations

import pytest

from itb.authoring.agent import SYSTEM_PROMPT
from itb.authoring.tools import TOOL_SCHEMAS

# ─── 1. 지침이 두 원인을 모두 말한다 ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("fragment", "why"),
    [
        (
            "재실행에서도 통과",
            "작성한 정의가 재실행 대상이라는 것을 말하지 않는다",
        ),
        (
            "요소를 눌렀다",
            "`ok` 가 「제품이 그 일을 했다」는 뜻이 아님을 말하지 않는다",
        ),
        (
            "delete_step 으로 지우세요",
            "효과가 없던 조작을 어떻게 처리할지 말하지 않는다",
        ),
        (
            "assert_condition 으로 남기세요",
            "비동기 완료를 무엇으로 적을지 말하지 않는다",
        ),
        (
            "정의에 없는 기다림은 재실행에 없습니다",
            "작성 때의 턴 간격이 재실행에 없다는 것을 말하지 않는다",
        ),
    ],
)
def test_the_system_prompt_states_the_rule(fragment: str, why: str) -> None:
    """지침이 사라지면 제품은 다시 헛클릭을 정의에 남긴다."""
    assert fragment in SYSTEM_PROMPT, why


def test_the_deletion_rule_does_not_collide_with_the_older_one() -> None:
    """「만들고 지우기를 반복하지 마세요」와 **상충해 보이면 안 된다**.

    한쪽은 지우라 하고 한쪽은 지우지 말라 하는 두 규칙을 함께 받으면 모델은 둘 중
    아무 쪽이나 고른다. 020 이 「성공한 것만 남는다」를 조작으로 한정한 것과 같은 이유다
    (`test_no_alternate_route.test_the_action_rule_is_scoped_to_actions_only`).
    """
    assert "만들고 지우기를 반복하지 마세요" in SYSTEM_PROMPT, (
        "옛 규칙이 사라졌다면 이 검사의 전제가 바뀐 것이다"
    )
    assert "되지 않은 것을 남기지 말라" in SYSTEM_PROMPT, (
        "두 규칙이 어떻게 다른지 말하지 않는다 — 모델이 상충하는 지시를 받는다"
    )


# ─── 2. 모델이 실제로 받는 도구 설명문도 같은 말을 한다 ──────────────────────


def test_the_assertion_tool_is_offered_as_the_way_to_wait() -> None:
    """검증이 대기 수단이라는 것을 **도구 설명문이** 말해야 한다.

    지침에만 있으면 모델은 검증을 「확인」으로만 읽고, 기다려야 하는 자리에서 쓰지 않는다.
    """
    description = TOOL_SCHEMAS["assert_condition"][0]
    assert "기다" in description, "검증이 기다린다는 사실을 말하지 않는다"
    assert "enabled" in description


def test_the_delete_tool_says_what_it_is_for_here() -> None:
    """헛클릭을 걷어내는 용도가 설명문에 있어야 한다."""
    description = TOOL_SCHEMAS["delete_step"][0]
    assert "화면이 바뀌지 않아" in description, (
        "효과 없는 조작을 지우는 용도를 말하지 않는다"
    )


def test_the_boundary_survives() -> None:
    """용도를 넓혀도 **지울 수 있는 범위는 그대로다.**

    `test_tool_descriptions_scope` 가 보는 것과 같은 경계다. 여기서 한 번 더 보는 이유는
    이 변경이 바로 그 설명문에 문장을 덧붙였기 때문이다 — 덧붙이다 경계를 밀어내면
    사람의 Step 이 에이전트에게 열린다.
    """
    description = TOOL_SCHEMAS["delete_step"][0]
    assert "지목한 Step" in description
    assert "그 밖의 Step 은 지울 수 없다" in description
