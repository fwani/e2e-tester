"""에이전트가 **지금이 언제인지** 알고 돈다 (`itb.authoring.clock`).

## 보고된 것

> 「ai 생성기가 현재시간을 인식하는 방법을 넣어줘. 사람이 현재시간을 요청할때가있어」

지시문에 「게시일은 오늘 날짜로 입력한다」 같은 문장이 있으면 모델은 시점을 알아야 한다.
알려 주지 않으면 화면에 적힌 날짜를 가져다 쓰거나 지어낸다 — 둘 다 사용자가 요구한 값이
아니다.

## 이 파일이 재는 것

**말이 모델에게 실제로 가는가.** 안내문을 만드는 함수가 있는 것과 그것이 시스템 프롬프트에
실리는 것은 다른 일이고, 이 저장소는 그 차이로 한 번 헛돈 적이 있다 — 그래서 두 드라이버가
`SYSTEM_PROMPT` 상수가 아니라 `build_system_prompt()` 를 넘기는지까지 본다.

언어모델도 브라우저도 쓰지 않는다. 순수한 문자열 조립이다.
"""

from __future__ import annotations

import inspect
import re
from datetime import UTC, datetime

from itb.authoring.agent import SYSTEM_PROMPT, build_system_prompt
from itb.authoring.clock import current_time_note, describe_now

_SAMPLE = datetime(2026, 9, 30, 14, 23, 5)
"""시간대가 없는 값 — 서버의 지역 시각으로 읽힌다. 시·분·날짜는 그대로 남는다."""


def test_안내문이_주어진_시각을_그대로_말한다() -> None:
    note = current_time_note(_SAMPLE)

    assert "2026-09-30" in note
    assert "14:23" in note
    assert "(수)" in note, "요일이 없으면 「이번 주 금요일」 같은 지시를 계산할 수 없다"


def test_안내문이_ISO_표기를_함께_준다() -> None:
    """날짜 칸이 요구하는 형식은 제품마다 다르다. 기준이 되는 표기가 하나 있어야 한다."""
    assert "2026-09-30T14:23:05" in current_time_note(_SAMPLE)


def test_표기에_시간대가_드러난다() -> None:
    """서버가 사람과 다른 지역에 있으면 **그 사실이 보여야** 한다.

    어느 지역인지는 단언하지 않는다 — 기기마다 다르고, 재려는 것은 시간대가 표기에
    들어 있는가이지 그 값이 무엇인가가 아니다.
    """
    assert re.search(r"UTC[+-]\d{2}:\d{2}", describe_now(_SAMPLE))


def test_시간대가_있는_값은_서버_지역_시각으로_옮긴다() -> None:
    """같은 순간이라도 사람이 보는 시계는 서버의 것이다. 자정 근처에서 「오늘」이
    하루 어긋나지 않게 하려면 한 시계로 모아야 한다."""
    utc_noon = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    expected = utc_noon.astimezone()

    assert expected.strftime("%H:%M") in describe_now(utc_noon)


def test_시각을_주지_않으면_지금을_쓴다() -> None:
    note = current_time_note()

    assert datetime.now().astimezone().strftime("%Y-%m-%d") in note  # noqa: DTZ005


def test_시스템_프롬프트에_시각이_실린다() -> None:
    """**이것이 요점이다.** 안내문이 있는 것과 모델이 받는 것은 다른 일이다."""
    prompt = build_system_prompt(_SAMPLE)

    assert SYSTEM_PROMPT in prompt, "기존 지침을 잃으면 안 된다"
    assert "2026-09-30" in prompt
    assert "## 지금 시각" in prompt


def test_지시문의_값이_지금_시각보다_우선한다고_말한다() -> None:
    """정제된 계획의 구체값을 지금 시각으로 덮으면 사용자가 적은 값이 사라진다."""
    note = current_time_note(_SAMPLE)

    assert "그 값을 그대로 쓰세요" in note
    assert "화면에 이미 적혀 있는 날짜를 기준으로 삼지 마세요" in note


def test_두_드라이버가_상수가_아니라_함수를_넘긴다() -> None:
    """상수를 그대로 넘기는 경로가 하나라도 남으면 **그 경로에서만** 시각이 빠진다.

    `claude_code_driver` 는 선택 의존성(`claude_agent_sdk`)을 요구하므로 불러서 재지
    않는다. 재려는 것은 호출 결과가 아니라 **무엇을 넘기는가**이고, 그것은 소스에 있다.
    """
    from itb.authoring import agent, claude_code_driver

    for source in (
        inspect.getsource(agent._sdk_driver),
        inspect.getsource(claude_code_driver.claude_code_driver),
    ):
        assert "build_system_prompt()" in source
        assert "=SYSTEM_PROMPT" not in source
