"""미리보기가 정적 화면에서도 보인다 — 진짜 브라우저 (005 T083·T084 · FR-160~FR-162).

`tests/unit/test_mirror_frame_delivery.py` 는 같은 성질을 가짜 페이지로 빠르게 본다.
여기서 다시 보는 이유는 하나다 — **U-24 의 원인이 CDP 스크린캐스트의 실제 성질**이었기
때문이다. "화면이 변할 때만 프레임을 만든다" 는 가짜로 만들어 낸 성질이 아니라 크롬이
그렇게 동작하는 것이고, 그 위에서 고쳤음을 보이려면 크롬이 있어야 한다.

세 가지를 본다.

1. 뒤늦게 붙은 구독이 **3초 안에** 현재 화면을 받는다 (FR-161·FR-162·SC-218)
2. 화면이 **5초 이상 조용해도** 프레임이 계속 온다 (FR-160)
3. 그 보완이 **강등으로 통보되지 않는다** (contracts/websocket.md §1-b)

셋 다 화면을 한 번도 건드리지 않은 채 본다. 건드리면 스크린캐스트가 스스로 프레임을
만들어 검증 대상이 사라진다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from itb.mirror.screencast import IDLE_INTERVAL_S

FIRST_FRAME_BUDGET_S = 3.0
"""SC-218 — 미리보기 첫 화면 3초 이내."""

QUIET_WINDOW_S = 5.0
"""U-24 의 실측 구간. 그때는 이 창에서 0건이었다 (FR-160)."""

FROM_CACHE_S = 0.5
"""이 안에 왔으면 캐시에서 온 것이다.

캐시는 `SessionEventHub.connect()` 안에서 동기적으로 나가므로 사실상 0초다. 무프레임
감시가 채운 것과 구분하려면 **감시 주기보다 충분히 짧은** 상한이어야 한다.
"""

JUST_AFTER_WATCH_TICK_S = IDLE_INTERVAL_S * 1.1
"""감시가 한 장 채운 **직후**에 구독을 붙이도록 맞춘 지연.

이 시점에 붙으면 다음 감시 프레임은 약 `IDLE_INTERVAL_S` 뒤다. 그래서 캐시가 없으면
첫 프레임이 `FROM_CACHE_S` 안에 올 수 없고, 테스트가 FR-162 의 부재를 실제로 잡는다.
구독 지연을 아무 값이나 쓰면 감시 프레임이 우연히 곧바로 도착해 통과해 버린다.
"""


@pytest.mark.usefixtures("fixture_app")
def test_late_subscriber_gets_the_current_screen_within_three_seconds(
    static_page_session: str,
    subscribe_late: Callable[..., Any],
) -> None:
    """구독이 뒤늦게 붙어도 현재 화면이 온다 (FR-161·FR-162·SC-218).

    **이것이 U-24 의 반전이다.** 이전에는 유일한 초기 프레임이 구독자 없는 시점에
    발행되어 버려졌고, 정적 화면에서는 그 뒤로 아무것도 만들어지지 않아 미리보기가
    영원히 비어 있었다 — 실측 0건.
    """
    with subscribe_late(static_page_session, after_s=JUST_AFTER_WATCH_TICK_S) as probe:
        elapsed = probe.seconds_to_first_frame(FIRST_FRAME_BUDGET_S)

    assert elapsed is not None, (
        f"{FIRST_FRAME_BUDGET_S}초 안에 mirror_frame 이 한 건도 오지 않았다 — U-24 재발"
    )
    assert elapsed <= FIRST_FRAME_BUDGET_S, f"첫 화면이 {elapsed:.2f}초 걸렸다 (SC-218)"
    # **캐시에서 왔음을 구분한다.** 무프레임 감시도 3초 예산은 채워 주므로, 예산만
    # 재면 FR-162(구독 시 마지막 프레임 전달)가 빠져도 통과한다.
    assert elapsed < FROM_CACHE_S, (
        f"첫 화면이 {elapsed:.2f}초 걸렸다 — 캐시가 아니라 무프레임 감시가 채운 것으로 "
        "보인다 (FR-162 미이행)"
    )


@pytest.mark.usefixtures("fixture_app")
def test_frames_keep_arriving_while_the_screen_stays_still(
    static_page_session: str,
    subscribe_late: Callable[..., Any],
) -> None:
    """화면이 5초 이상 변하지 않아도 프레임이 계속 온다 (FR-160, T084).

    첫 장만 오고 끊기면 미리보기는 **멈춘 그림**이 된다. 오래 기다리는 Step 에서
    사용자는 그것이 지금 화면인지 아까 화면인지 구분할 수 없다 (U-02 관찰 2).

    무프레임 감시 주기가 2초이므로 5초 창에서 최소 두 장은 더 와야 한다.
    """
    with subscribe_late(static_page_session) as probe:
        first = probe.next_frame(FIRST_FRAME_BUDGET_S)
        assert first is not None, "첫 프레임이 오지 않아 이어지는 것을 볼 수 없다"
        later = probe.collect_for(QUIET_WINDOW_S)

    expected = int(QUIET_WINDOW_S // IDLE_INTERVAL_S) - 1
    assert len(later) >= expected, (
        f"화면이 조용한 {QUIET_WINDOW_S}초 동안 프레임이 {len(later)}건뿐이다 "
        f"(최소 {expected}건 기대) — 무프레임 감시가 동작하지 않는다"
    )


@pytest.mark.usefixtures("fixture_app")
def test_quiet_screen_is_not_reported_as_degradation(
    static_page_session: str,
    subscribe_late: Callable[..., Any],
) -> None:
    """조용한 화면을 메우는 것은 강등이 아니다 (contracts/websocket.md §1-b).

    강등 배너를 띄우면 사용자는 도구가 제대로 못 하고 있다고 읽는다. 스크린캐스트는
    잘 돌고 있고 화면이 조용할 뿐이다.
    """
    with subscribe_late(static_page_session) as probe:
        probe.collect_for(QUIET_WINDOW_S)
        degraded = probe.messages_of_type("mirror_degraded")

    assert degraded == [], (
        f"조용한 화면을 강등으로 통보했다: {degraded} — 정상 동작의 보완이지 강등이 아니다"
    )
