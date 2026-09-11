"""AI 편집 도구의 권한 범위. 016 FR-037·FR-038 · 불변식 8 (T054).

**이 파일이 지키는 것은 신뢰다.** AI 가 사용자의 멀쩡한 Step 을 건드릴 수 있으면
사용자는 재녹화를 켤 수 없고, 켜지 않으면 이 기능은 없는 것과 같다.

그리고 이 한정이 **되돌리기를 성립시킨다** — 옛 구간과 구간 밖이 바뀌지 않으므로
버리기가 「이번에 만든 것」만 지우면 시작 전과 같아진다 (불변식 9 · research R7).

브라우저 없이 돈다. 툴박스는 sink 로만 세션과 이어져 있으므로, sink 를 가짜로 끼우면
권한 판정을 그 자리에서 확인할 수 있다.
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


def steps_of(n: int) -> list[Step]:
    return [
        ClickStep(id=f"step-{i + 1:02d}", label=f"동작 {i + 1}", target=target(f"b{i + 1}"))
        for i in range(n)
    ]


class Harness:
    """sink 만 갖춘 툴박스. 브라우저·실행기는 쓰지 않는다."""

    def __init__(self, steps: list[Step], owned: set[str]) -> None:
        self.steps = list(steps)
        self.applied: list[EditResult] = []
        self.box = BrowserToolbox(
            session=None,  # type: ignore[arg-type] - 편집 도구는 세션을 쓰지 않는다
            executor=None,  # type: ignore[arg-type]
            allocate_step_id=lambda: "step-99",
            on_step=self._never,
            steps_source=lambda: self.steps,
            on_edit=self._apply,
            in_scope=lambda step_id: step_id in owned,
        )

    async def _never(self, _step: Step) -> None:  # pragma: no cover - 불려선 안 된다
        msg = "편집 도구가 Step 을 만들었다"
        raise AssertionError(msg)

    async def _apply(self, result: EditResult) -> None:
        self.applied.append(result)
        self.steps = result.steps


# ─── 거절 — 범위 밖 (불변식 8) ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_a_step_outside_the_scope_is_refused() -> None:
    """구간 밖 Step 은 고칠 수 없다 (FR-037)."""
    h = Harness(steps_of(5), owned={"step-05"})
    result = await h.box.update_step("step-02", "label", "내 맘대로")

    assert "error" in result, "범위 밖인데 통과했다"
    assert "step-02" in result["error"]
    assert h.applied == [], "거절했는데 편집이 반영됐다"
    assert h.steps[1].label == "동작 2", "목록이 바뀌었다"


@pytest.mark.anyio
async def test_the_refusal_is_a_return_value_not_an_exception() -> None:
    """**거절은 예외가 아니라 반환값이다** (FR-038).

    SDK 는 도구가 던진 예외를 잡아 모델에게 돌려주므로 예외로는 루프를 끊을 수 없고,
    무엇보다 이 거절들은 오류가 아니라 **정상적인 답**이다 — 「그건 내 권한 밖입니다」.
    에이전트가 읽고 사람에게 전할 수 있어야 한다.
    """
    h = Harness(steps_of(4), owned=set())
    for tool, args in (
        ("update_step", ("step-01", "label", "x")),
        ("delete_step", ("step-01",)),
        ("move_step", ("step-01", "down")),
    ):
        got = await getattr(h.box, tool)(*args)
        assert isinstance(got, dict) and "error" in got, f"{tool} 이 거절을 반환하지 않았다"
        assert got["error"].strip(), f"{tool} 의 거절에 사유가 없다"


@pytest.mark.anyio
async def test_the_refusal_tells_the_agent_what_to_do() -> None:
    """조용히 무시하지 않고 **사람에게 말하라**고 한다 (FR-038)."""
    h = Harness(steps_of(4), owned=set())
    got = await h.box.update_step("step-01", "label", "x")
    assert "사람" in got["error"], "무엇을 해야 하는지 말해야 한다"


@pytest.mark.anyio
async def test_a_missing_step_is_refused_as_absent_not_as_scope() -> None:
    """목록에 없는 id 는 **대상 부재**다. 범위 문제와 구별해 말한다."""
    h = Harness(steps_of(3), owned={"step-99"})
    got = await h.box.delete_step("step-99")
    assert "error" in got
    assert "step-99" in got["error"]


@pytest.mark.anyio
async def test_without_wiring_nothing_can_be_edited() -> None:
    """**모르는 것을 참으로 보지 않는다.**

    sink 가 없으면 전부 거절한다. 기본값이 「전부 허용」이면, 배선을 빠뜨린 경로에서
    AI 가 사용자의 Step 을 건드린다.
    """
    box = BrowserToolbox(
        session=None,  # type: ignore[arg-type]
        executor=None,  # type: ignore[arg-type]
        allocate_step_id=lambda: "step-99",
        on_step=_unused,
    )
    got = await box.update_step("step-01", "label", "x")
    assert "error" in got


async def _unused(_step: Step) -> None:  # pragma: no cover
    raise AssertionError


# ─── 허용 — 범위 안 ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_a_step_in_the_scope_can_be_updated() -> None:
    h = Harness(steps_of(4), owned={"step-03"})
    got = await h.box.update_step("step-03", "label", "주문 저장")

    assert got.get("ok") is True, got
    assert got["label"] == "주문 저장"
    assert h.steps[2].label == "주문 저장"
    # 나머지는 그대로다 — 이것이 불변식 9 의 전제다.
    assert [s.label for s in h.steps] == ["동작 1", "동작 2", "주문 저장", "동작 4"]


@pytest.mark.anyio
async def test_a_step_in_the_scope_can_be_deleted() -> None:
    h = Harness(steps_of(4), owned={"step-02"})
    got = await h.box.delete_step("step-02")

    assert got.get("ok") is True, got
    assert [s.id for s in h.steps] == ["step-01", "step-03", "step-04"]


@pytest.mark.anyio
async def test_moving_inside_the_scope_works() -> None:
    h = Harness(steps_of(4), owned={"step-02", "step-03"})
    got = await h.box.move_step("step-03", "up")

    assert got.get("ok") is True, got
    assert [s.id for s in h.steps] == ["step-01", "step-03", "step-02", "step-04"]


@pytest.mark.anyio
async def test_moving_onto_a_step_outside_the_scope_is_refused() -> None:
    """**옮길 자리도 권한 범위 안이어야 한다.**

    허용하면 AI 가 만든 Step 이 옛 구간 위로 올라가고, 확정이 지울 구간과 남길 것의
    경계가 흐려진다.
    """
    h = Harness(steps_of(4), owned={"step-03"})
    got = await h.box.move_step("step-03", "up")

    assert "error" in got, "구간 밖으로 올라가는 것이 통과했다"
    assert "step-02" in got["error"]
    assert [s.id for s in h.steps] == ["step-01", "step-02", "step-03", "step-04"]


@pytest.mark.anyio
async def test_moving_past_the_edge_is_refused_clearly() -> None:
    h = Harness(steps_of(3), owned={"step-01"})
    got = await h.box.move_step("step-01", "up")
    assert "error" in got
    assert "처음" in got["error"]


@pytest.mark.anyio
async def test_a_bad_direction_is_refused() -> None:
    h = Harness(steps_of(3), owned={"step-02"})
    got = await h.box.move_step("step-02", "sideways")
    assert "error" in got
    assert "up" in got["error"]


@pytest.mark.anyio
async def test_an_unsupported_field_is_refused_by_the_shared_function() -> None:
    """고칠 수 없는 필드는 **편집 연산이 판정한다** (원칙 I).

    도구가 목록을 복제하면 사람이 고칠 수 있는 것과 AI 가 고칠 수 있는 것이 갈린다.
    """
    h = Harness(steps_of(3), owned={"step-02"})
    got = await h.box.update_step("step-02", "url", "https://example.com")
    assert "error" in got, "click Step 에 url 은 없다"


# ─── 상한 (FR-042) ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_editing_counts_against_the_call_budget() -> None:
    """편집도 도구 호출 1회로 센다 (FR-042).

    세지 않으면 「만들고 지우기」를 반복하며 예산을 우회할 수 있다.
    """
    h = Harness(steps_of(4), owned={"step-02"})
    before = h.box.limits.calls
    await h.box.update_step("step-02", "label", "가")
    await h.box.delete_step("step-02")
    assert h.box.limits.calls == before + 2


@pytest.mark.anyio
async def test_every_editing_tool_respects_the_budget() -> None:
    """상한에 닿으면 넷 다 멈춘다 — 하나라도 새면 상한이 뜻을 잃는다."""
    h = Harness(steps_of(4), owned={"step-02"})
    h.box.limits.calls = h.box.limits.max_calls
    for tool, args in (
        ("update_step", ("step-02", "label", "x")),
        ("delete_step", ("step-02",)),
        ("move_step", ("step-02", "down")),
        ("repick_target", ("step-02", "e1")),
    ):
        got: dict[str, Any] = await getattr(h.box, tool)(*args)
        assert got.get("stop") or "error" in got or "중단" in str(got), (
            f"{tool} 이 상한을 넘겼다: {got}"
        )
    assert len(STEP_EDITING_TOOLS) == 4
