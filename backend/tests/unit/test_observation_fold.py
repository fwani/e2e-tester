"""턴 내부의 낡은 화면 관찰 접기 (025 T072·T073 · US6).

## 이 파일이 지키는 성질

접기는 **무엇을 접는가**보다 **무엇을 접지 않는가**가 중요하다. 조작 결과·검증 결과·
막힘 신고가 접히면 이 기능이 고치려는 문제(무엇을 했는지 모른다)가 턴 안에서 다시
생긴다.

그리고 접힌 자리가 **사라지면 안 된다.** 관찰이 애초에 없었던 것처럼 보이면 모델은
관찰 없이 조작하려 든다.
"""

from __future__ import annotations

import json
from typing import Any

from itb.authoring.fold import (
    FOLDED_NOTE,
    KEEP_LATEST_OBSERVATIONS,
    fold_stale_observations,
)


def _result(tool_use_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": json.dumps(payload, ensure_ascii=False),
            }
        ],
    }


def _observation(tool_use_id: str, ref: str) -> dict[str, Any]:
    return _result(
        tool_use_id,
        {"tab": 0, "elements": [{"element_ref": ref, "tag": "button"}], "text": "x" * 3000},
    )


def _conversation() -> list[dict[str, Any]]:
    return [
        {"role": "user", "content": "로그인한다"},
        _observation("a", "e1"),
        _result("b", {"ok": True, "step": "로그인 클릭"}),
        _observation("c", "e9"),
        _result("d", {"ok": True, "assertion_failed": True, "observed": "다름"}),
        _observation("e", "e17"),
    ]


def _contents(messages: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            out.extend(str(b.get("content")) for b in content)
        else:
            out.append(str(content))
    return out


def test_only_the_latest_observation_survives() -> None:
    """가장 최근 관찰만 온전히 남는다 (FR-030)."""
    folded = _contents(fold_stale_observations(_conversation()))

    assert sum(1 for c in folded if '"element_ref"' in c) == KEEP_LATEST_OBSERVATIONS
    assert any("e17" in c for c in folded), "가장 최근 관찰이 남아야 한다"
    assert not any("e1\"" in c for c in folded), "지난 관찰이 온전히 남았다"


def test_folded_places_say_they_are_stale() -> None:
    """**사라지지 않고 접힌다** (FR-031).

    관찰이 애초에 없었던 것처럼 보이면 모델은 관찰 없이 조작하려 든다. 「낡았다」는
    말이 남아야 다시 관찰할지를 스스로 정한다.
    """
    folded = _contents(fold_stale_observations(_conversation()))

    assert sum(1 for c in folded if FOLDED_NOTE in c) == 2
    assert any('"folded": true' in c for c in folded)


def test_actions_and_assertions_are_not_folded() -> None:
    """**관찰만 접는다** (FR-034).

    조작 결과·검증 결과는 「무엇을 했는가」의 기록이고, 사라지면 이 기능이 고치려는
    문제가 턴 안에서 다시 생긴다.
    """
    folded = _contents(fold_stale_observations(_conversation()))

    assert any("로그인 클릭" in c for c in folded)
    assert any("assertion_failed" in c for c in folded)


def test_user_messages_are_untouched() -> None:
    """사용자가 한 말은 접지 않는다 — 거기에 지시문이 있다."""
    folded = _contents(fold_stale_observations(_conversation()))

    assert "로그인한다" in folded


def test_the_original_list_is_not_modified() -> None:
    """**모델에게 보내는 사본에만 적용된다** (FR-033).

    제품이 든 기록과 사용자에게 보이는 대화가 접히면, 사용자는 제품이 무엇을 했는지
    볼 수 없다.
    """
    original = _conversation()
    before = json.dumps(original, ensure_ascii=False)

    fold_stale_observations(original)

    assert json.dumps(original, ensure_ascii=False) == before


def test_folding_is_a_no_op_with_one_observation() -> None:
    """관찰이 하나뿐이면 접을 것이 없다."""
    messages = [{"role": "user", "content": "지시"}, _observation("a", "e1")]

    folded = _contents(fold_stale_observations(messages))

    assert any("e1" in c for c in folded)
    assert not any(FOLDED_NOTE in c for c in folded)


def test_find_by_text_results_are_not_folded() -> None:
    """`find_by_text` 의 결과는 접지 않는다.

    「사람이 말한 낱말이 화면 어디에 있는가」는 화면이 바뀌어도 대체로 유효하고, 크기도
    작다. 그 결과에는 `elements` 가 없으므로 판정에서 자연히 걸러진다.
    """
    messages = [
        {"role": "user", "content": "지시"},
        _result("f", {"matches": [{"text_element": {"tag": "span"}}]}),
        _observation("a", "e1"),
        _observation("b", "e2"),
    ]

    folded = _contents(fold_stale_observations(messages))

    assert any("text_element" in c for c in folded), "낱말 찾기 결과가 접혔다"
    assert sum(1 for c in folded if FOLDED_NOTE in c) == 1
