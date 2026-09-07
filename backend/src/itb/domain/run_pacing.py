"""실행 속도. 004 FR-101~FR-110.

**Step DSL 이 아니다.** 속도는 한 실행이 얼마나 쉬어 가는지를 정할 뿐이며, 무엇을
수행하는지는 바꾸지 않는다. 그래서 세션에 속하고 테스트 자산에는 기록되지 않는다
(FR-110, 헌법 원칙 V).

**간격 대응표가 여기 한 곳에만 있다.** 러너와 화면이 각자 숫자를 들고 있으면 두 판단이
갈린다 — 화면이 "1.5초 쉽니다" 라고 말하는 동안 러너가 0.5초를 쉬는 상태가 만들어진다.
그래서 화면에도 값을 계산해 주지 않고 **서버가 계산한 값을 실어 보낸다**
(contracts/websocket.md §1).

이 모듈은 순수하다. `.importlinter` 의 `domain-is-pure` 계약이 이를 강제한다.
"""

from __future__ import annotations

from enum import StrEnum


class RunPacing(StrEnum):
    """실행이 Step 사이에 얼마나 쉬는가.

    **자유 입력이 아니라 단계다.** 임의의 밀리초를 받으면 "0으로 뒀는데 왜 안 보이냐" 는
    질문이 돌아온다. 목적은 사람이 따라갈 수 있는 속도를 고르게 하는 것이지 시간을
    조율하게 하는 것이 아니다.
    """

    FAST = "fast"
    """간격 없음. **004 이전의 동작이 이것이다.**"""

    NORMAL = "normal"
    """기본값. 20 Step 테스트에 10초를 더한다 (research R8)."""

    SLOW = "slow"
    """사람이 각 Step 의 화면 변화를 확인할 수 있는 속도 (SC-004)."""

    STEP = "step"
    """한 스텝씩. 간격 대신 매 Step 경계에서 자동 일시정지한다.

    **새 상태를 만들지 않는다.** 기존 `PAUSED` 에 들어가므로 편집·조작 허용 규칙이
    이미 검증된 경로를 그대로 쓴다 (research R7, FR-108).
    """


DEFAULT_PACING = RunPacing.NORMAL
"""취향 파일이 없거나 읽지 못했을 때 쓰는 값.

`FAST` 가 004 이전 동작이지만 기본으로 삼지 않는다. 이 기능의 존재 이유가 "기본이 너무
빠르다" 이므로, 기본이 현재 동작이면 아무것도 달라지지 않는다. `FAST` 는 한 번의 선택으로
유지된다 (FR-109). 무인 실행은 `FAST` 를 명시한다.
"""

_DELAY_MS: dict[RunPacing, int] = {
    RunPacing.FAST: 0,
    RunPacing.NORMAL: 500,
    RunPacing.SLOW: 1500,
    RunPacing.STEP: 0,
}

_LABEL: dict[RunPacing, str] = {
    RunPacing.FAST: "빠름",
    RunPacing.NORMAL: "보통",
    RunPacing.SLOW: "느림",
    RunPacing.STEP: "한 스텝씩",
}

MIN_PERCEPTIBLE_DELAY_MS = 1000
"""`SLOW` 가 만족해야 하는 하한 (SC-004).

사람이 화면 변화를 "확인했다" 고 느끼려면 이 정도는 필요하다. `_DELAY_MS[SLOW]` 를
줄이려는 변경은 이 상수와 함께 검토되어야 한다 — 단위 테스트가 두 값을 대조한다.
"""


def delay_ms(pacing: RunPacing) -> int:
    """이 속도의 Step 간 간격(ms).

    **`STEP` 이 0인 것은 간격이 없어서가 아니라 다른 방식으로 멈추기 때문이다.**
    자동 일시정지는 시간이 아니라 사용자 지시로 풀린다.
    """
    return _DELAY_MS[pacing]


def auto_pause(pacing: RunPacing) -> bool:
    """매 Step 경계에서 자동으로 일시정지하는가."""
    return pacing is RunPacing.STEP


def label(pacing: RunPacing) -> str:
    """사람이 읽는 이름. 화면 표기에 쓴다."""
    return _LABEL[pacing]
