"""프레임 해석 규칙 (001 research 의 iframe 항목).

브라우저를 띄우지 않고 규칙만 잠근다 — `Page`·`Frame` 의 자리에 필요한 것만 가진 대역을
둔다. 여기서 고정하는 것은 **어느 프레임을 채택하고 어느 경우에 거절하는가** 이며, 그
판정이 흔들리면 iframe 안의 Step 이 조용히 다른 프레임에서 실행될 수 있다.
"""

from __future__ import annotations

import pytest

from itb.execution.frame_resolver import FrameNotFoundError, resolve_frame

TIMEOUT_MS = 300
"""폴링 예산. 거절 경로를 재는 데만 쓰므로 짧게 둔다."""


class FakeFrame:
    def __init__(self, url: str, detached: bool = False) -> None:
        self.url = url
        self._detached = detached

    def is_detached(self) -> bool:
        return self._detached


class FakePage:
    """`resolve_frame` 이 쓰는 것만 갖춘 대역. `main_frame` 은 첫 프레임이다."""

    def __init__(self, *frames: FakeFrame) -> None:
        self.frames = list(frames)


def page(*urls: str) -> FakePage:
    return FakePage(*[FakeFrame(u) for u in urls])


async def test_no_frame_url_means_main_frame_and_does_not_wait() -> None:
    """`frame_url` 이 없으면 main frame 이며 대기하지 않는다.

    기존 정의는 전부 이 경로를 지나므로, 여기서 대기가 생기면 모든 Step 이 느려진다.
    """
    p = page("https://app.example/main")
    resolved = await resolve_frame(p, None, TIMEOUT_MS)  # type: ignore[arg-type]
    assert resolved.root is p
    assert resolved.waited_ms == 0
    assert resolved.relaxed is False


async def test_exact_url_wins() -> None:
    """주소가 정확히 같은 프레임을 고른다."""
    p = page("https://app.example/main", "https://app.example/inner?tab=1")
    resolved = await resolve_frame(
        p,  # type: ignore[arg-type]
        "https://app.example/inner?tab=1",
        TIMEOUT_MS,
    )
    assert resolved.root is p.frames[1]
    assert resolved.relaxed is False


async def test_query_is_ignored_only_when_nothing_matches_exactly() -> None:
    """쿼리가 달라진 프레임은 **정확히 맞는 것이 없을 때만** 받아들인다.

    캐시 무효화 토큰이 붙는 iframe 은 재실행마다 주소가 달라진다. 그 경우까지 실패로
    두면 iframe 을 쓰는 앱은 재실행 자체가 불가능하다. 다만 완화를 먼저 쓰면
    `/inner?tab=1` 과 `/inner?tab=2` 를 같은 프레임으로 보게 되므로 순서가 중요하다.
    """
    p = page("https://app.example/main", "https://app.example/inner?token=zzz")
    resolved = await resolve_frame(
        p,  # type: ignore[arg-type]
        "https://app.example/inner?token=aaa",
        TIMEOUT_MS,
    )
    assert resolved.root is p.frames[1]
    assert resolved.relaxed is True, "완화 매칭을 썼다는 사실이 진단에 남아야 한다"


async def test_exact_match_is_preferred_over_relaxed_one() -> None:
    """완화 매칭 후보가 여럿이어도 정확히 맞는 하나가 있으면 그것을 쓴다."""
    p = page(
        "https://app.example/main",
        "https://app.example/inner?tab=1",
        "https://app.example/inner?tab=2",
    )
    resolved = await resolve_frame(
        p,  # type: ignore[arg-type]
        "https://app.example/inner?tab=2",
        TIMEOUT_MS,
    )
    assert resolved.root is p.frames[2]
    assert resolved.relaxed is False


async def test_same_url_twice_is_refused() -> None:
    """같은 주소의 프레임이 둘이면 **채택하지 않는다** (FR-019b 와 같은 판단).

    자동으로 첫 번째를 고르면 잘못된 프레임에서 통과할 수 있고, 그것은 실패보다 나쁘다.
    """
    p = page(
        "https://app.example/main",
        "https://app.example/inner",
        "https://app.example/inner",
    )
    with pytest.raises(FrameNotFoundError) as caught:
        await resolve_frame(p, "https://app.example/inner", TIMEOUT_MS)  # type: ignore[arg-type]
    assert caught.value.ambiguous is True
    assert "2개" in str(caught.value)


async def test_missing_frame_lists_what_is_there() -> None:
    """못 찾으면 **현재 열린 프레임 주소를 함께** 말한다.

    "요소를 찾을 수 없습니다" 로 뭉뚱그리면 사용자는 프레임 문제인지 요소 문제인지
    구분할 수 없다. 주소가 바뀐 것이라면 목록이 그것을 바로 보여 준다.
    """
    p = page("https://app.example/main", "https://app.example/other")
    with pytest.raises(FrameNotFoundError) as caught:
        await resolve_frame(p, "https://app.example/inner", TIMEOUT_MS)  # type: ignore[arg-type]
    message = str(caught.value)
    assert caught.value.ambiguous is False
    assert "https://app.example/other" in message
    assert "https://app.example/inner" in message


async def test_detached_frames_are_not_candidates() -> None:
    """떼어진 프레임은 조작할 수 없으므로 후보가 아니다."""
    p = FakePage(
        FakeFrame("https://app.example/main"),
        FakeFrame("https://app.example/inner", detached=True),
    )
    with pytest.raises(FrameNotFoundError):
        await resolve_frame(p, "https://app.example/inner", TIMEOUT_MS)  # type: ignore[arg-type]
