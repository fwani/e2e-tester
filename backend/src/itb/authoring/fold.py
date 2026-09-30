"""턴 내부의 낡은 화면 관찰을 접는다. 025 FR-030~FR-034.

## 왜 턴 **내부**인가

턴 **사이**에는 이력이 통째로 사라진다 (research R1 · `journal.py` 가 그것을 메운다).
그런데 턴 **안**에서는 정반대다 — 화면 관찰이 하나도 버려지지 않고 쌓인다.

실측(`specs/025-ai-instruction-context/baseline.md` T002): 상한 근처에서 관찰 한 번이
**66.7KB, 약 22,000 토큰**이다. 스무 번 관찰하면 **1.3MB** 가 한 턴 안에 쌓인다.

한 지시에 허용된 도구 호출은 `MAX_TOOL_CALLS` 이며 2026-09-30 에 40 에서 300 이 됐다.
**이 접기가 없으면 쌓이는 양은 회차에 비례한다** — 상한을 올리는 변경은 언제나 이
함수의 몫을 키운다.

모델은 지금 화면과 지나간 화면을 구별해야 하고, 뒤로 갈수록 그 구별이 흐려진다.

## **사라지게 하지 않고 접는다** (FR-031)

관찰이 애초에 없었던 것처럼 보이면 모델은 관찰 없이 조작하려 든다. 접힌 자리에는
「낡았다, 필요하면 다시 관찰하라」가 남는다.

## 관찰만 접는다 (FR-034)

조작 결과·검증 결과·막힘 신고·할 일 표시는 접지 않는다. 그것들은 「무엇을 했는가」의
기록이고, 사라지면 이 기능이 고치려는 문제가 턴 안에서 다시 생긴다.

## **SDK 를 알지 못한다**

순수 함수다. 메시지 목록을 받아 새 목록을 돌려준다. runner 를 다루는 것은
`agent.py` 의 드라이버이고, 그쪽이 이 함수를 부른다 — 접는 규칙과 SDK 를 다루는 방법이
한 파일에 섞이면 어느 쪽이 바뀌어도 둘 다 읽어야 한다.
"""

from __future__ import annotations

import json
from typing import Any

KEEP_LATEST_OBSERVATIONS = 1
"""온전히 남길 관찰의 개수 (FR-032).

**1 로 둔 근거**: 모델이 조작에 쓰는 것은 `element_ref` 이고, 그 참조는 화면이 바뀌면
낡는다 — 이미 시스템 프롬프트가 「화면이 바뀌었을 수 있으면 다시 관찰하라」고 말한다.
두 장을 남겨도 낡은 쪽을 쓰는 것은 여전히 거절되므로, 남겨서 얻는 것이 없고 66.7KB 를
더 실을 뿐이다.

**탭을 가르지 않는다.** 여러 탭을 오가는 작성에서는 탭마다 최신 하나를 남기는 편이
나아 보이지만, 그러면 「지금 화면」이 여럿이 되고 모델이 어느 것이 지금인지 판단해야
한다. 다시 관찰하는 비용은 한 번의 도구 호출이고, 판단이 틀리는 비용은 조작이 엉뚱한
화면에 가는 것이다.

**확인 필요**: 실제 세션에서 탭 전환이 잦은 경우 다시 관찰하는 횟수를 재어 이 값을
다시 본다.
"""

FOLDED_NOTE = (
    "이 화면 관찰은 낡았습니다. 지금 화면이 필요하면 observe_page 를 다시 부르세요."
)
"""접힌 자리에 남기는 말 (FR-031).

**「없음」이 아니라 「낡음」이다.** 없다고 하면 모델은 관찰한 적이 없다고 읽고, 그러면
같은 화면을 또 관찰한다. 낡았다고 하면 다시 관찰할지를 스스로 정한다.
"""

_OBSERVE_MARKS = ('"element_ref"', '"elements"')
"""관찰 결과임을 알아보는 표식.

**도구 이름으로 거슬러 찾지 않는다.** `tool_use` 블록에서 이름을 읽어 짝을 맞추는
방법이 더 정확해 보이지만, 그러려면 이 함수가 메시지의 앞뒤 관계를 알아야 하고 SDK 가
그 구조를 바꾸면 조용히 멈춘다. 결과 자체의 모양을 보는 것이 더 단단하다 —
`observe_page` 의 응답에는 `elements` 가 반드시 있고, 다른 도구의 응답에는 없다.

**`find_by_text` 는 접지 않는다.** 그 결과에는 `matches` 가 있고 `elements` 가 없다.
접지 않는 것이 맞다 — 「사람이 말한 낱말이 화면 어디에 있는가」는 화면이 바뀌어도
대체로 유효하고, 크기도 작다.
"""


def _is_observation(content: Any) -> bool:
    """이 tool_result 가 화면 관찰의 결과인가."""
    if isinstance(content, str):
        return any(mark in content for mark in _OBSERVE_MARKS)
    if isinstance(content, (dict, list)):
        try:
            text = json.dumps(content, ensure_ascii=False)
        except (TypeError, ValueError):
            return False
        return any(mark in text for mark in _OBSERVE_MARKS)
    return False


def _fold_block(block: dict[str, Any]) -> dict[str, Any]:
    folded = json.dumps({"folded": True, "note": FOLDED_NOTE}, ensure_ascii=False)
    return {**block, "content": folded}


def fold_stale_observations(
    messages: list[dict[str, Any]], keep: int = KEEP_LATEST_OBSERVATIONS
) -> list[dict[str, Any]]:
    """지난 화면 관찰을 접는다. **원본을 바꾸지 않는다** (FR-033).

    제품이 든 기록과 모델에게 보내는 사본을 가르는 것은 이 기능 전체의 규칙이다 —
    사용자에게 보이는 대화가 접히면 사용자는 제품이 무엇을 했는지 볼 수 없다.

    뒤에서부터 세어 `keep` 개를 남기고 나머지를 접는다. 접을 것이 없으면 **원본과 같은
    내용의 새 리스트**를 돌려준다.
    """
    seen = 0
    out: list[dict[str, Any]] = []
    # 뒤에서부터 — 최근 것이 남아야 한다.
    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, list):
            out.append(message)
            continue

        blocks: list[Any] = []
        changed = False
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_result"
                and _is_observation(block.get("content"))
            ):
                seen += 1
                if seen > keep:
                    blocks.append(_fold_block(block))
                    changed = True
                    continue
            blocks.append(block)
        out.append({**message, "content": blocks} if changed else message)

    return list(reversed(out))
