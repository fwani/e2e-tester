"""Step 의 `frame_url` → 요소를 찾을 문서. 001 research (iframe 항목).

`tab_resolver` 가 "어느 탭인가" 를 정하듯 이 모듈은 **"어느 문서인가"** 를 정한다. 둘을
갈라 두는 이유는 실패가 서로 다른 것을 말하기 때문이다 — 탭이 없는 것과, 탭은 열렸는데 그
안의 프레임이 아직 없는 것은 사용자가 할 일이 다르다.

**왜 필요한가 (실측으로 드러난 결함).** 주입 스크립트는 모든 프레임에서 돈다. iframe 안을
클릭하면 후보가 **그 프레임의 문서 기준**으로 측정되므로 `main#app-main > div` 같은 경로가
`verified` 로 적힌다. 그런데 실행이 main frame 만 뒤지면 그 경로는 0개를 매칭하고, 사용자는
예산을 다 쓴 "요소를 찾을 수 없습니다" 만 본다. 녹화 화면에서는 클릭이 정상으로 보였으므로
원인을 짚을 단서가 없다. **측정과 실행이 서로 다른 문서를 본 것**이 원인이었다.

**식별은 URL 로 한다.** 프레임에는 재실행 사이에 유지되는 식별자가 없다 — 순서는 로딩 상황에
따라 바뀌고, `name` 은 대부분 비어 있다. 001 research 가 "Step 에 프레임 URL 을 함께
기록" 으로 정한 근거이며, 이 모듈이 그 결정의 실행 측이다.

**여러 개에 맞으면 채택하지 않는다.** 같은 URL 의 iframe 이 둘이면 어느 쪽을 조작할지
결정할 수 없다. 자동으로 첫 번째를 고르면 잘못된 프레임에서 통과할 수 있고, 그것은 실패보다
나쁘다 — 요소 후보에 `ambiguous` 를 둔 것과 같은 판단이다 (FR-019b).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from playwright.async_api import Frame, Page

from itb.locator.strategy import POLL_INTERVAL_MS

SearchRoot = Page | Frame
"""요소를 찾을 문서. main frame 은 `Page`, 하위 프레임은 `Frame` 이다.

두 타입은 요소 탐색에 필요한 API(`locator`·`get_by_*`·`evaluate`)를 같은 이름으로
가지므로, 탐색 코드는 어느 쪽인지 알 필요가 없다.
"""

MAX_LISTED_FRAMES = 8
"""실패 메시지에 담을 프레임 URL 개수 상한. 프레임이 수십 개인 화면에서 메시지가
읽을 수 없게 길어지는 것을 막는다."""


class FrameNotFoundError(Exception):
    """`frame_url` 이 가리키는 프레임을 하나로 좁히지 못했다.

    **실패의 종류를 함께 든다.** 호출부가 문구를 해석하지 않고 분류할 수 있어야 한다 —
    아직 안 열린 것(기다리거나 예산을 늘린다)과 같은 URL 이 여러 개인 것(정의를 고친다)은
    사용자가 할 일이 다르다.
    """

    def __init__(
        self, message: str, *, waited_ms: int = 0, ambiguous: bool = False
    ) -> None:
        super().__init__(message)
        self.waited_ms = waited_ms
        self.ambiguous = ambiguous


@dataclass(slots=True)
class FrameResolution:
    """프레임 해석 결과."""

    root: SearchRoot
    waited_ms: int
    """프레임이 나타나기를 기다린 시간. 요소 대기 시간에 합산된다."""

    relaxed: bool = False
    """쿼리·프래그먼트를 뗀 주소로 맞춘 경우. 진단에 남긴다.

    캐시 무효화 토큰이나 세션 파라미터가 붙는 iframe 은 재실행마다 URL 이 달라진다.
    그 경우까지 실패로 두면 iframe 을 쓰는 앱은 재실행 자체가 불가능하다.
    """


def _bare(url: str) -> str:
    """쿼리·프래그먼트를 뗀 주소. 완화 매칭의 기준이다."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def _live_frames(page: Page) -> list[Frame]:
    """지금 붙어 있는 프레임. 떼어진 프레임은 조작할 수 없으므로 뺀다."""
    return [f for f in page.frames if not f.is_detached()]


def _candidates(page: Page, frame_url: str) -> tuple[list[Frame], bool]:
    """`frame_url` 에 맞는 프레임과, 완화 매칭을 썼는지.

    **정확히 같은 URL 을 먼저 본다.** 완화 매칭을 먼저 쓰면 `/app?tab=1` 과 `/app?tab=2`
    를 같은 프레임으로 보게 되고, 그때 잘못된 프레임을 조작할 수 있다.
    """
    frames = _live_frames(page)
    exact = [f for f in frames if f.url == frame_url]
    if exact:
        return exact, False
    target = _bare(frame_url)
    return [f for f in frames if _bare(f.url) == target], True


async def resolve_frame(
    page: Page, frame_url: str | None, timeout_ms: int
) -> FrameResolution:
    """Step 의 `frame_url` 을 요소를 찾을 문서로 바꾼다.

    `frame_url` 이 없으면 main frame 이며 **대기하지 않는다** — 기존 정의는 모두 이 경로를
    지나므로 이번 변경의 비용이 0 이다.

    하위 프레임은 예산 안에서 폴링한다. iframe 은 대상 앱이 늦게 붙일 수 있고, 그것은
    요소가 늦게 나타나는 것과 같은 성질의 대기다 (004 FR-111 과 같은 판단).
    """
    if frame_url is None:
        return FrameResolution(root=page, waited_ms=0)

    started = time.monotonic()
    deadline = started + max(timeout_ms, 0) / 1000
    matched: list[Frame] = []
    relaxed = False

    while True:
        matched, relaxed = _candidates(page, frame_url)
        if len(matched) == 1:
            return FrameResolution(
                root=matched[0],
                waited_ms=int((time.monotonic() - started) * 1000),
                relaxed=relaxed,
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        # 여러 개에 맞는 상태는 기다려도 좁혀지지 않는 것이 보통이지만, 로딩 중 같은
        # 자리표시자 프레임이 잠시 둘인 경우가 있으므로 예산 안에서는 다시 확인한다.
        await asyncio.sleep(min(POLL_INTERVAL_MS / 1000, remaining))

    waited_ms = int((time.monotonic() - started) * 1000)
    if len(matched) > 1:
        msg = (
            f"같은 주소의 프레임이 {len(matched)}개 있어 어느 것을 조작할지 결정할 수 "
            f"없습니다. {waited_ms}ms 동안 기다렸지만 하나로 좁혀지지 않았습니다. "
            f"프레임 주소: {frame_url}"
        )
        raise FrameNotFoundError(msg, waited_ms=waited_ms, ambiguous=True)

    present = [f.url for f in _live_frames(page)][:MAX_LISTED_FRAMES]
    msg = (
        f"이 Step 은 하위 프레임(iframe) 안에서 기록됐지만 그 프레임을 찾지 못했습니다. "
        f"{waited_ms}ms 동안 기다렸습니다. 기록된 프레임 주소: {frame_url} / "
        f"현재 열린 프레임: {', '.join(present) if present else '없음'}"
    )
    raise FrameNotFoundError(msg, waited_ms=waited_ms)
