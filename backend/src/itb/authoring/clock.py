"""지금이 언제인지를 에이전트에게 알려 준다.

## 왜 필요한가

사람이 쓴 지시문에는 시점을 가리키는 말이 섞여 있다 — 「게시일은 오늘 날짜로 입력한다」,
「종료일을 내일로 준다」. 모델은 **자기가 언제 도는지 모른다.** 알려 주지 않으면 셋 중
하나가 일어난다.

1. 학습 시점의 날짜를 쓴다 — 과거 날짜가 들어가 제품이 거절하거나, 조용히 틀린 값이 남는다.
2. 화면에 이미 적혀 있는 날짜를 가져다 쓴다 — 그것은 제품이 만든 값이지 사용자가 요구한
   값이 아니다. `SYSTEM_PROMPT` 가 「화면에서 읽은 값으로 바꾸지 마세요」라고 반복해
   말하는 바로 그 실패다.
3. 막혔다고 보고한다 — 물어볼 필요가 없는 것을 묻는다.

## **서버의 지역 시각으로 준다**

UTC 로 주고 환산을 모델에게 맡기면, 자정 근처에서 「오늘」이 하루 어긋난다. 사람과 테스트
대상 제품이 같은 자리에 있다고 보는 편이 오해가 적다. 대신 시간대를 표기에 함께 적어,
서버가 다른 지역에 있으면 **그 사실이 드러나게** 한다.

## 이것은 「이번 시도를 시작한 시각」이다

시스템 프롬프트에 한 번 실리고 그 시도 동안 바뀌지 않는다. 도구로 만들어 매번 물어보게
할 수도 있지만, 그러면 도구 호출 예산(`MAX_TOOL_CALLS`)을 쓰고 모델이 그 도구를 부를지도
확실하지 않다 — 시점은 **묻지 않아도 알고 있어야 하는 것**에 가깝다.

**한계를 알고 쓴다**: 여기서 만든 값은 작성 시점에 Step 의 값으로 굳는다. 저장된 테스트를
다른 날 실행하면 그 값은 그날의 「오늘」이 아니다. 실행 시점에 다시 계산되는 값이
필요하다면 그것은 이 모듈이 아니라 변수 기능이 할 일이다.
"""

from __future__ import annotations

from datetime import datetime

_WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")
"""요일 이름을 직접 갖는다 — `%A` 는 서버의 locale 을 따라가서, 개발자 기기와 배포
환경이 다른 말을 한다."""


def describe_now(now: datetime | None = None) -> str:
    """사람이 읽는 한 줄 표기. 예: `2026-09-30 (수) 14:23 KST (UTC+09:00)`."""
    moment = _localized(now)
    stamp = f"{moment:%Y-%m-%d} ({_WEEKDAYS[moment.weekday()]}) {moment:%H:%M}"
    return f"{stamp} {_zone(moment)}".strip()


def current_time_note(now: datetime | None = None) -> str:
    """시스템 프롬프트에 붙일 절. `build_system_prompt` 가 쓴다.

    ISO 8601 을 함께 준다 — 입력 칸이 요구하는 형식은 제품마다 다르고, 모델이 형식을
    바꿔 쓸 때 기준이 되는 표기가 하나 있어야 한다.
    """
    moment = _localized(now)
    return f"""\
## 지금 시각

지금은 **{describe_now(moment)}** 입니다 (ISO 8601: `{moment.isoformat(timespec="seconds")}`).

- 지시문이 「오늘」·「지금」·「현재 시각」처럼 시점을 말하면 **이 값을 기준으로** 값을
  만드세요. 「내일」·「3일 뒤」처럼 상대적인 시점도 이 값에서 계산하세요.
- **화면에 이미 적혀 있는 날짜를 기준으로 삼지 마세요.** 그것은 제품이 만든 값이지
  사용자가 요구한 값이 아닙니다.
- 지시문이 구체적인 날짜·시각을 적어 두었으면 **그 값을 그대로 쓰세요.** 지시문의 값이
  지금 시각보다 우선합니다.
- 날짜 칸이 요구하는 형식은 제품마다 다릅니다. 칸의 `placeholder` 나 이미 들어 있는
  값의 모양을 보고 맞추세요.
- 이 값은 **이번 시도를 시작한 시각**입니다. 초 단위로 정확하지 않으니 시간 자체를
  기대값으로 삼는 검증에는 쓰지 마세요.
"""


def _localized(now: datetime | None) -> datetime:
    """시간대를 붙인다. 시간대가 없는 값은 **서버의 지역 시각으로 읽는다** —
    `astimezone()` 이 naive 를 그렇게 다루고, 그것이 여기서 원하는 해석이다."""
    return (now or datetime.now()).astimezone()  # noqa: DTZ005 - 지역 시각이 목적이다


def _zone(moment: datetime) -> str:
    """`KST (UTC+09:00)` 또는 offset 만. 이름과 offset 이 같은 말이면 하나만 남긴다."""
    raw = moment.strftime("%z")
    offset = f"UTC{raw[:3]}:{raw[3:]}" if raw else ""
    name = moment.tzname() or ""
    if not name or name.replace(" ", "") == offset.replace("UTC", ""):
        return offset
    return f"{name} ({offset})".strip() if offset else name
