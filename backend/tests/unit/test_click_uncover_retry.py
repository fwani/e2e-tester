"""가려진 클릭을 한 번 더 시도한다 (2026-09-09 사용자 보고).

보고 문장: 「step9번으로 클릭한 다음에 메뉴에 마우스가 그대로 있어서 확장된 형태라서 메뉴
뒤에 가려진 원천데이터를 클릭하지 못한다. 측정은 잘되었으나, 재실행시 클릭한 위치에 마우스가
가게되면서 발생한 문제로 보인다.」

## 진단

맞다. Playwright 의 ``click()`` 은 포인터를 요소 위로 옮기고 **그대로 둔다.** 녹화 때는
사람이 곧 마우스를 움직여 hover 메뉴가 접히지만, 재생 때는 포인터가 머문다. 다음 Step 의
대상이 그 메뉴 뒤에 있으면 클릭이 통하지 않는다.

그리고 그것이 **교착이 된다**: Playwright 는 클릭 전에 히트 검사를 하고, 그 검사는 포인터를
옮기기 **전에** 한다. 「메뉴가 덮고 있다 → 검사 실패 → 재시도 → 포인터는 그대로」가 예산이
끝날 때까지 돈다.

## 첫 판은 실패한 뒤에 고치려 했다 — 사용자가 「안 됨」이라고 답했다

이유가 둘이다. ① 재시도에 남는 예산이 250ms 뿐이다 (`MIN_ACTION_TIMEOUT_MS` — 첫 시도가
Step 예산을 통째로 쓰고 실패한다). ② 막힌 Step 마다 예산을 통째로 버려 재실행이 Step 당
10초씩 느려진다.

그래서 **실패를 기다리지 않고 미리 확인한다.**

## 이 파일이 고정하는 성질

1. **가려지지 않은 클릭은 바뀌지 않는다** — 포인터를 옮기지 않는다.
2. **가려진 클릭은 포인터를 먼저 비운다** — 실패를 기다리지 않는다.
3. **모르면 옮기지 않는다** — 확인이 실패했을 때 화면을 건드리지 않는다.
4. **그래도 실패하면 한 번 더 시도한다** — 가림 확인이 놓치는 경우의 마지막 기회.
5. **재시도는 한 번뿐이다** — 무한히 돌면 Step 예산(FR-057)이 뜻을 잃는다.

브라우저를 띄우지 않는다. 재는 것은 **호출 순서**이고, 그것은 대역으로 정확히 볼 수 있다.
"""

from __future__ import annotations

import time

import pytest
from playwright.async_api import Error as PlaywrightError

from itb.execution import pointer
from itb.execution.step_executor import StepExecutor


class _Mouse:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def move(self, x: float, y: float) -> None:
        self._log.append(f"move({int(x)},{int(y)})")


class _Page:
    """`viewport_size` 와 `mouse` 만 갖는 최소 페이지."""

    def __init__(self, log: list[str], size: dict[str, int] | None) -> None:
        self.viewport_size = size
        self.mouse = _Mouse(log)


class _Locator:
    """정해진 횟수만큼 실패하는 클릭 + 가림 여부를 답하는 평가."""

    def __init__(
        self,
        log: list[str],
        fail_times: int = 0,
        occluded: bool | PlaywrightError = False,
    ) -> None:
        self._log = log
        self._left = fail_times
        self._occluded = occluded

    async def evaluate(self, _script: str) -> bool:
        self._log.append("probe")
        if isinstance(self._occluded, PlaywrightError):
            raise self._occluded
        return self._occluded

    async def click(self, timeout: int) -> None:  # noqa: ARG002 - 예산은 여기서 재지 않는다
        self._log.append("click")
        if self._left > 0:
            self._left -= 1
            msg = "<div class=\"menu\"> intercepts pointer events"
            raise PlaywrightError(msg)


def _executor() -> StepExecutor:
    """생성자를 지나지 않고 메서드만 쓴다.

    `StepExecutor` 는 세션·해석기를 요구하지만 `_click`·`_park_pointer` 는 그 어느 것도
    보지 않는다. 실물을 조립하면 브라우저가 필요해지고, 그러면 이 검증이 재려는 것(호출
    순서)이 무거운 픽스처 뒤로 숨는다.
    """
    return StepExecutor.__new__(StepExecutor)


DEADLINE_AHEAD = 5.0


class ClickRetryTests:
    async def test_an_unobstructed_click_does_not_move_the_pointer(self) -> None:
        """**지금 통하는 흐름은 하나도 바뀌지 않는다.**

        이것이 「가림을 실제로 확인한다」를 고른 이유다. 항상 비우면 hover 로 열려 포인터가
        안에 있어야 유지되는 메뉴가 접히고, 그 안을 누르는 클릭이 실패한다. 그 경우 대상은
        가려져 있지 않다 — 메뉴 **안**에 있다.
        """
        log: list[str] = []
        page = _Page(log, {"width": 1280, "height": 800})
        locator = _Locator(log, occluded=False)

        await _executor()._click(page, locator, time.monotonic() + DEADLINE_AHEAD)  # type: ignore[arg-type]

        assert log == ["probe", "click"], f"가려지지 않았는데 포인터를 건드렸다: {log}"

    async def test_an_occluded_click_parks_the_pointer_first(self) -> None:
        """**가려졌으면 실패를 기다리지 않는다.**

        기다렸다 고치는 것이 첫 판이었고 안 됐다 — 재시도에 250ms 밖에 남지 않고, 막힌
        Step 마다 예산을 통째로 버린다.
        """
        log: list[str] = []
        page = _Page(log, {"width": 1280, "height": 800})
        locator = _Locator(log, occluded=True)

        await _executor()._click(page, locator, time.monotonic() + DEADLINE_AHEAD)  # type: ignore[arg-type]

        assert log == ["probe", "move(1279,799)", "click"], log

    async def test_a_failing_probe_does_not_move_the_pointer(self) -> None:
        """**모르면 화면을 건드리지 않는다.**

        확인이 실패하는 경우(요소가 방금 사라졌다, 프레임이 옮겨졌다)는 클릭 쪽이 곧 같은
        사실을 더 정확한 문장으로 말한다. 여기서 「가려졌다」고 답하면 포인터를 옮겨 hover
        로 유지되는 메뉴를 접을 수 있다.
        """
        log: list[str] = []
        page = _Page(log, {"width": 1280, "height": 800})
        locator = _Locator(log, occluded=PlaywrightError("요소가 사라졌습니다"))

        await _executor()._click(page, locator, time.monotonic() + DEADLINE_AHEAD)  # type: ignore[arg-type]

        assert log == ["probe", "click"], log

    async def test_a_blocked_click_still_retries_once(self) -> None:
        """가림 확인이 놓쳐도 마지막 한 번의 기회가 있다 (전환 중 등)."""
        log: list[str] = []
        page = _Page(log, {"width": 1280, "height": 800})
        locator = _Locator(log, fail_times=1, occluded=False)

        await _executor()._click(page, locator, time.monotonic() + DEADLINE_AHEAD)  # type: ignore[arg-type]

        assert log == ["probe", "click", "move(1279,799)", "click"], log

    async def test_the_pointer_goes_to_the_far_corner(self) -> None:
        """**오른쪽 아래 끝이다.**

        화면 메뉴는 위·왼쪽에 몰려 있으므로 그 반대 끝이 무언가를 hover 할 확률이 가장
        낮다. `(0, 0)` 은 로고나 첫 메뉴가 있는 자리라 다른 것을 열 수 있다.
        """
        log: list[str] = []
        page = _Page(log, {"width": 640, "height": 480})
        await pointer.park(page)  # type: ignore[arg-type]
        assert log == ["move(639,479)"]

    async def test_an_unknown_viewport_moves_nothing(self) -> None:
        """크기를 모르면 좌표를 지어내지 않는다 — 엉뚱한 곳을 hover 하는 것보다 낫다."""
        log: list[str] = []
        page = _Page(log, None)
        await pointer.park(page)  # type: ignore[arg-type]
        assert log == []

    async def test_a_second_failure_keeps_the_original_kind_of_error(self) -> None:
        """두 번째도 실패하면 **그 사유를 그대로 올린다.**

        여기서 다른 예외로 바꾸면 사용자는 「가려서 못 눌렀다」는 사실을 잃는다.
        """
        log: list[str] = []
        page = _Page(log, {"width": 1280, "height": 800})
        locator = _Locator(log, fail_times=2, occluded=False)

        with pytest.raises(PlaywrightError, match="intercepts pointer events"):
            await _executor()._click(page, locator, time.monotonic() + DEADLINE_AHEAD)  # type: ignore[arg-type]

        # 시도는 **두 번뿐이다.** 무한히 돌면 Step 예산(FR-057)이 뜻을 잃는다.
        assert log.count("click") == 2, log
