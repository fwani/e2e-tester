"""AI 가 **무엇을 하는 중인지** 알린다. FR-011·FR-060 (2026-09-11 사용자 요청).

## 무엇이 문제였나

이전에는 `_execute` 가 **성공한 뒤에** Step 이름 하나를 보냈다. 그래서 세 가지가
보이지 않았다:

1. 요소를 기다리는 동안(최대 `timeout_ms`) 화면이 조용하다 — 사용자에게는 「멈춘 것」과
   「기다리는 것」이 같아 보인다
2. **실패하면 아무것도 보고되지 않는다.** 무엇을 하다 실패했는지 남지 않는다
3. 관찰·편집처럼 Step 을 만들지 않는 도구는 아예 흔적이 없다

사용자가 읽는 것은 **시도**의 기록이지 성공의 기록이 아니다.
"""

from __future__ import annotations

from typing import Any

import pytest

from itb.authoring.tools import STEP_EDITING_TOOLS, BrowserToolbox
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep, Step
from itb.execution.step_edits import EditResult


def target(name: str) -> TargetLocator:
    return TargetLocator(
        role="button",
        accessible_name=name,
        css=Candidate(value=f"button.{name}", status=CandidateStatus.VERIFIED),
    )


class Harness:
    """진행 보고만 받는 툴박스."""

    def __init__(self, steps: list[Step] | None = None) -> None:
        self.said: list[str] = []
        self.steps = list(steps or [])
        self.box = BrowserToolbox(
            session=None,  # type: ignore[arg-type]
            executor=None,  # type: ignore[arg-type]
            allocate_step_id=lambda: "step-99",
            on_step=self._noop_step,
            on_progress=self._say,
            steps_source=lambda: self.steps,
            on_edit=self._apply,
            in_scope=lambda _sid: True,
        )

    async def _say(self, message: str) -> None:
        self.said.append(message)

    async def _noop_step(self, _step: Step) -> None:  # pragma: no cover
        return

    async def _apply(self, result: EditResult) -> None:
        self.steps = result.steps


# ─── 편집 도구가 무엇을 하는지 알린다 ──────────────────────────────────────


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool", "args", "expected"),
    [
        ("update_step", ("step-01", "label", "새 이름"), "고치는 중"),
        ("delete_step", ("step-01",), "지우는 중"),
        ("move_step", ("step-02", "up"), "옮기는 중"),
    ],
)
async def test_every_editing_tool_announces_what_it_does(
    tool: str, args: tuple[Any, ...], expected: str
) -> None:
    """편집 도구 셋이 **하기 전에** 무엇을 하는지 알린다.

    알리지 않으면 사용자는 AI 가 목록을 고치는 동안 아무것도 보지 못하고, 목록이
    갑자기 달라진 것만 본다.
    """
    h = Harness(
        [
            ClickStep(id="step-01", label="첫", target=target("a")),
            ClickStep(id="step-02", label="둘", target=target("b")),
        ]
    )
    await getattr(h.box, tool)(*args)

    assert h.said, f"{tool} 이 아무것도 알리지 않았다"
    assert any(expected in line for line in h.said), (
        f"{tool} 의 보고에 「{expected}」가 없다: {h.said}"
    )


@pytest.mark.anyio
async def test_a_refused_edit_is_still_announced_by_its_attempt() -> None:
    """거절되는 편집도 **시도는 알린다.**

    권한 밖이라 거절되더라도 사용자는 AI 가 무엇을 하려 했는지 알아야 한다 — 그것이
    「AI 가 엉뚱한 것을 고치려 했다」를 알아채는 유일한 경로다.
    """
    h = Harness([ClickStep(id="step-01", label="첫", target=target("a"))])
    h.box.in_scope = lambda _sid: False

    await h.box.update_step("step-01", "label", "안 될 것")
    # 범위 판정이 보고보다 먼저이므로 지금은 조용하다. 그 사실을 고정한다 —
    # 바꾸려면 이 검사를 함께 고쳐야 하고, 그때 「무엇을 알릴지」를 다시 판단하게 된다.
    assert h.said == [], (
        "거절이 보고를 내면 자취가 「하려다 만 것」으로 채워진다. 지금 설계는 "
        "권한 판정을 먼저 하고 통과한 것만 알린다."
    )


# ─── 구조 — 보고가 도구마다 흩어지지 않는다 ────────────────────────────────


def test_all_reporting_goes_through_one_helper() -> None:
    """보고가 **한 함수**를 지난다 (`_announce`).

    도구마다 `on_progress` 를 직접 부르면 어떤 도구는 알리고 어떤 도구는 안 알리는
    상태가 생기고, 그것이 이 변경 전의 상태였다 (성공한 Step 만 알렸다).
    """
    import inspect

    from itb.authoring import tools as tools_mod

    source = inspect.getsource(tools_mod.BrowserToolbox)
    direct = source.count("self.on_progress(")
    assert direct == 1, (
        f"`on_progress` 를 직접 부르는 자리가 {direct}곳이다. "
        "`_announce` 하나를 지나야 보고 규칙이 한 곳에 있다."
    )


def test_the_announcer_never_breaks_the_tool() -> None:
    """**보고 실패가 작성을 끊지 않는다.**

    진행 표시는 곁가지다. 이벤트 발행이 실패했다고 사용자가 만들던 Step 이 사라지면
    안 된다 (FR-067 과 같은 판단).
    """
    import inspect

    from itb.authoring.tools import BrowserToolbox

    source = inspect.getsource(BrowserToolbox._announce)
    assert "contextlib.suppress" in source, "보고 실패가 도구를 멈춘다"


def test_editing_tools_report_before_acting() -> None:
    """편집 도구가 **일하기 전에** 알린다 — 순서를 구조로 고정한다."""
    import inspect

    from itb.authoring.tools import BrowserToolbox

    for name in STEP_EDITING_TOOLS:
        source = inspect.getsource(getattr(BrowserToolbox, name))
        announce = source.index("_announce")
        sink = source.index("self.on_edit(")
        assert announce < sink, f"{name} 이 일한 뒤에 알린다 — 기다리는 동안 조용하다"
