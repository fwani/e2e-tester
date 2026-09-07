"""미러 프레임 전달 (005 T083~T086 · FR-160~FR-165).

리포트 U-24 의 실측은 이랬다 — **구독 후 정적 화면 5초에 0건.** 원인은 스크린캐스트가
화면이 변할 때만 프레임을 만들고, 그 유일한 초기 프레임이 구독자 없는 시점에 발행되어
버려지는 것이었다.

이 테스트가 지키는 것은 그 반전이다. 그리고 반전시키면서 **깨서는 안 되는 두 성질**을
함께 고정한다 — 미러가 입력을 전달하지 않는 것(FR-047a)과 미러 실패가 실행에 영향을
주지 않는 것(FR-047b).
"""

from __future__ import annotations

import asyncio

import pytest

from itb.mirror import screencast as sc
from itb.mirror.screencast import (
    IDLE_INTERVAL_S,
    MirrorInputForbiddenError,
    TabScreencast,
    _ALLOWED_COMMANDS,
    _send,
)


class FakePage:
    """스크린샷만 찍히는 화면. **화면은 절대 변하지 않는다** — 정적 화면 재현이다."""

    def __init__(self, *, fail: bool = False) -> None:
        self.shots = 0
        self.fail = fail
        self.context = None

    async def screenshot(self, **_kw: object) -> bytes:
        self.shots += 1
        if self.fail:
            msg = "화면을 찍을 수 없다"
            raise RuntimeError(msg)
        return b"\xff\xd8jpeg-bytes"


def collector() -> tuple[list[tuple[str, dict]], object]:
    events: list[tuple[str, dict]] = []

    async def emit(event_type: str, **payload: object) -> None:
        events.append((event_type, dict(payload)))

    return events, emit


# ─── FR-047a: 입력 전달 경로가 없다 ─────────────────────────────────────────


def test_allowed_commands_are_exactly_three() -> None:
    """허용 CDP 명령이 늘지 않았다 (FR-047a·FR-165).

    005 는 **송신 쪽만** 만졌다. 무프레임 감시는 CDP 가 아니라 Playwright
    `page.screenshot` 을 쓰므로 이 목록에 아무것도 추가되지 않아야 한다.
    """
    assert _ALLOWED_COMMANDS == {
        "Page.startScreencast",
        "Page.stopScreencast",
        "Page.screencastFrameAck",
    }


def test_mirror_module_does_not_import_input_domain() -> None:
    """`Input` 도메인을 임포트하지도 언급하지도 않는다 (FR-047a)."""
    source = (sc.__file__ or "")
    assert source
    with open(source, encoding="utf-8") as fh:
        text = fh.read()
    # 문서 문자열에서 "Input.*" 을 금지 사실로 적는 것은 허용한다.
    forbidden = [
        line
        for line in text.splitlines()
        if "Input." in line and not line.lstrip().startswith(("#", '"', "'", "*"))
        and "FR-047a" not in line
        and "_ALLOWED_COMMANDS" not in line
    ]
    assert forbidden == [], f"미러가 Input 도메인을 다루는 줄이 있다: {forbidden}"


@pytest.mark.asyncio
async def test_send_rejects_commands_outside_whitelist() -> None:
    """목록을 벗어난 전송은 함수 자체가 거절한다 (FR-047a)."""
    with pytest.raises(MirrorInputForbiddenError):
        await _send(None, "Input.dispatchMouseEvent", {})  # type: ignore[arg-type]


# ─── FR-162: 구독이 뒤늦게 붙어도 현재 화면을 받는다 ────────────────────────


@pytest.mark.asyncio
async def test_first_frame_is_cached_without_screen_change() -> None:
    """정적 화면에서도 마지막 프레임이 생긴다 (FR-161·FR-162·SC-218).

    **이것이 U-24 의 반전이다.** 이전에는 화면이 변하지 않으면 캐시할 프레임 자체가
    없었고, 구독이 붙어도 줄 것이 없었다.
    """
    page = FakePage()
    events, emit = collector()
    cast = TabScreencast(page, 0, emit)

    # CDP 를 못 쓰는 환경을 흉내 낸다 — 강등 경로로 들어간다.
    page.context = None
    started = await cast.start()

    assert started is False, "CDP 세션을 못 만들었으므로 강등이어야 한다"
    assert cast.last_frame() is not None, "강등 경로에서도 첫 프레임이 캐시돼야 한다"
    frame = cast.last_frame()
    assert frame is not None
    assert frame["tab"] == 0
    assert frame["data"], "빈 프레임을 캐시하면 화면이 검은 화면을 그린다"
    await cast.stop()


@pytest.mark.asyncio
async def test_idle_watch_keeps_sending_on_static_screen() -> None:
    """화면이 조용해도 프레임이 계속 온다 (FR-160).

    오래 기다리는 Step 에서 미러가 비던 것이 이것으로 잡힌다. 리포트는 20초 대기 구간
    내내 "미러 프레임을 기다리고 있습니다" 만 봤다 (U-02 관찰 2).
    """
    page = FakePage()
    events, emit = collector()
    cast = TabScreencast(page, 0, emit)
    page.context = None
    await cast.start()

    before = page.shots
    # 감시 주기를 두 번 이상 지나도록 기다린다.
    await asyncio.sleep(IDLE_INTERVAL_S * 1.2)
    await cast.stop()

    assert page.shots > before, "정적 화면에서 프레임이 더 오지 않았다"
    assert [e for e in events if e[0] == "mirror_frame"], "mirror_frame 이 발행되지 않았다"


@pytest.mark.asyncio
async def test_idle_watch_does_not_announce_degradation() -> None:
    """무프레임 감시는 강등이 아니다 (contracts/websocket.md §1-b).

    강등 배너를 띄우면 사용자는 문제가 있다고 읽는다. 이것은 정상 동작의 보완이다.
    """
    page = FakePage()
    events, emit = collector()
    cast = TabScreencast(page, 0, emit)
    page.context = None
    await cast.start()
    degraded_at_start = [e for e in events if e[0] == "mirror_degraded"]
    events.clear()
    await asyncio.sleep(IDLE_INTERVAL_S * 1.2)
    await cast.stop()

    # 시작 시점의 강등 통보는 CDP 를 못 쓴 것이므로 정당하다. 그 뒤로는 없어야 한다.
    assert degraded_at_start, "CDP 실패는 강등으로 알려야 한다"
    assert [e for e in events if e[0] == "mirror_degraded"] == []


# ─── FR-047b·FR-164: 미러 실패가 실행에 영향을 주지 않는다 ──────────────────


@pytest.mark.asyncio
async def test_screenshot_failure_does_not_raise() -> None:
    """찍을 수 없는 화면에서도 예외가 새지 않는다 (FR-164·FR-047b).

    미러 감시 태스크의 예외가 실행 경로로 전파되면, 미리보기를 고치려던 변경이 실행을
    깨뜨린다.
    """
    page = FakePage(fail=True)
    events, emit = collector()
    cast = TabScreencast(page, 0, emit)
    page.context = None
    await cast.start()
    await asyncio.sleep(IDLE_INTERVAL_S * 0.8)
    await cast.stop()

    assert cast.last_frame() is None, "찍지 못한 프레임을 캐시해서는 안 된다"


@pytest.mark.asyncio
async def test_stop_cancels_idle_watch() -> None:
    """정지하면 감시도 멈춘다. 남으면 종료된 세션의 화면을 계속 찍는다."""
    page = FakePage()
    _events, emit = collector()
    cast = TabScreencast(page, 0, emit)
    page.context = None
    await cast.start()
    await cast.stop()

    settled = page.shots
    await asyncio.sleep(IDLE_INTERVAL_S * 1.2)
    assert page.shots == settled, "정지 후에도 화면을 찍고 있다"
