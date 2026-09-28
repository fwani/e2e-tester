"""이어갈 때 AI 가 받는 지시 (022 US1 · FR-006·FR-007 · **SC-001**).

## 무엇이 문제였나 (2026-09-28 사용자 보고)

예산이 떨어져 멈춘 뒤 「다시」를 누르면 「같은 동작을 다시 시도하세요」가 갔다. 예산
소진은 특정 동작에서 막힌 것이 아니므로 **마지막 동작은 성공했을 수 있고**, 그러면
이어가기가 이미 한 일을 반복한다 — 같은 항목이 두 번 등록된다.

문구 문제가 아니라 동작 문제다. 그래서 여기서 못 박는다.
"""

from __future__ import annotations

import copy
import dataclasses

import pytest

from itb.api.routes.sessions import _resume_note
from itb.authoring.agent import AgentOutcome, AgentStatus
from itb.authoring.blocked import AiChoice
from itb.authoring.tools import BlockedKind


class _Work:
    """`_resume_note` 가 읽는 것은 `last_blocked` 하나뿐이다."""

    def __init__(self, kind: BlockedKind | None) -> None:
        self.last_blocked = (
            None
            if kind is None
            else AgentOutcome(AgentStatus.BLOCKED, reason="멈췄다", blocked_kind=kind)
        )


def test_budget_exhaustion_is_told_to_continue_not_repeat() -> None:
    """예산 소진에서 이어가면 **남은 지시**를 한다 (FR-006 · SC-001)."""
    note = _resume_note(_Work(BlockedKind.BUDGET_EXHAUSTED), AiChoice.RETRY)  # type: ignore[arg-type]

    assert "이어서" in note
    assert "이미 끝낸 동작은 다시 하지 마세요" in note
    assert "같은 동작을" not in note, "이미 한 일을 반복시키는 지시가 가면 안 된다"


@pytest.mark.parametrize(
    "kind",
    [BlockedKind.NEEDS_INPUT, BlockedKind.PRODUCT_MISMATCH, None],
)
def test_other_blocks_keep_the_retry_instruction(kind: BlockedKind | None) -> None:
    """**예산 소진이 아니면 지금 그대로다** (FR-007 · US1 시나리오 3).

    요소를 못 찾아 막힌 경우에는 「같은 동작을 다시」가 맞는 지시다. 사유를 모르는
    경우(`None`, 서버 재시작 뒤 등)도 기존 동작을 따른다.
    """
    note = _resume_note(_Work(kind), AiChoice.RETRY)  # type: ignore[arg-type]
    assert note == "같은 동작을 지금 화면 상태에서 다시 시도하세요."


@pytest.mark.parametrize(
    "kind",
    [BlockedKind.BUDGET_EXHAUSTED, BlockedKind.NEEDS_INPUT],
)
def test_skip_is_unchanged_whatever_the_kind(kind: BlockedKind) -> None:
    """건너뛰기는 막힘의 종류와 무관하게 그대로다 — 이 기능이 건드리는 것은 이어가기다."""
    note = _resume_note(_Work(kind), AiChoice.SKIP)  # type: ignore[arg-type]
    assert note.startswith("그 동작은 건너뜁니다.")


# ─── 이어가기가 Step 을 잃지 않는다 (FR-009 · SC-003) ──────────────────────


def test_fresh_budget_does_not_touch_steps() -> None:
    """**예산을 새로 주는 것이 Step 을 건드리지 않는다.**

    자명해 보이지만 `reset()` → `reset_attempt()` 개명이 지나간 자리라 회귀 위험이
    실재한다 (analyze E1). Step 은 컴파일러가 소유하고 `AttemptLimits` 는 그것을 세지도
    않는데, 「전부 되돌린다」로 읽히던 이름이 누군가에게 그렇게 하라고 말할 수 있다.
    """
    from itb.authoring.tools import AttemptLimits

    limits = AttemptLimits()
    limits.record_call()
    limits.steps_at_attempt_start = 2

    # `slots=True` 라 `__dict__` 가 없다 — 필드를 이름으로 훑는다.
    names = [f.name for f in dataclasses.fields(limits)]
    before = {n: copy.deepcopy(getattr(limits, n)) for n in names}
    limits.reset_attempt(step_count=7)

    changed = {n for n in names if getattr(limits, n) != before[n]}
    allowed = {"calls", "steps_at_attempt_start"}
    assert changed <= allowed, f"예상 밖의 상태가 바뀌었다: {changed - allowed}"
    assert limits.total_calls == 1, "누적은 남는다 (FR-018)"


# ─── 방향을 적어 이어가는 길은 남는다 (FR-011) ─────────────────────────────


def test_the_answer_path_is_open_whatever_the_kind() -> None:
    """**화면이 칸을 열지 않을 뿐, 서버가 답변을 거절하지는 않는다** (022 FR-011).

    예산 소진에서도 사용자가 「목록 화면부터 다시 봐」처럼 방향을 줄 수 있어야 한다.
    화면이 칸을 닫는 것은 「적지 않아도 된다」는 뜻이지 「적을 수 없다」가 아니다.

    `ai_choice` 가 답변을 거절하는 조건이 **막힘의 종류를 보지 않는지**를 못 박는다 —
    나중에 누가 「예산 소진에는 답변을 받지 않는다」를 넣으면 여기서 걸린다.
    """
    import inspect

    from itb.api.routes import sessions

    src = inspect.getsource(sessions.ai_choice)
    body = src.split("if choice is AiChoice.ANSWER")[1].split("command = command_for")[0]
    assert "BUDGET" not in body.upper(), "답변 경로가 막힘의 종류로 갈리면 안 된다"
    assert "blocked_kind" not in body
