"""어긋난 검증의 도구 계약 (020 T011·T061·T039).

`contracts/tool-surface.md` 가 약속한 입출력을 고정한다. 세 가지다.

1. **검증이 어긋나면 Step 은 남고, 모델은 「다시 하라」로 읽지 않는다** (FR-005·FR-010)
2. **동작 Step 은 현행대로 실패하면 기록되지 않는다** (FR-006) — 같은 `_execute` 를
   지나므로 기본값이 새면 실패한 클릭이 조용히 기록된다
3. **막힘의 종류가 질문의 유무를 정한다** (FR-023·FR-024)
"""

from __future__ import annotations

from typing import Any

import pytest

from itb.authoring.tools import (
    MAX_CONSECUTIVE_ELEMENT_FAILURES,
    BlockedKind,
    BrowserToolbox,
)
from itb.domain.assertion import MAX_OBSERVED_CHARS
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    SelectStep,
    Step,
    UploadStep,
)
from itb.execution.step_executor import StepFailure
from itb.secrets.scrubber import Scrubber


def _target(name: str = "save") -> TargetLocator:
    return TargetLocator(
        role="button",
        accessible_name=name,
        css=Candidate(value=f"button.{name}", status=CandidateStatus.VERIFIED),
    )


class _FailingExecutor:
    """항상 같은 사유로 실패하는 실행기. 실패 사유가 흔들리면 판정을 못 한다."""

    def __init__(self, message: str) -> None:
        self.message = message

    async def execute(self, _step: Step) -> None:
        raise StepFailure(self.message)


class _StubSession:
    """탭 하나만 있는 세션. `_execute` 가 새 탭 열림을 감지하려고 수를 읽는다."""

    tabs: list[object] = []
    active_tab_index = 0


class Harness:
    """Step 기록과 진행 보고를 받는 툴박스."""

    def __init__(self, message: str = "기대: '저장되었습니다' / 실제: '처리 완료'") -> None:
        self.kept: list[Step] = []
        self.said: list[str] = []
        self.box = BrowserToolbox(
            session=_StubSession(),  # type: ignore[arg-type]
            executor=_FailingExecutor(message),  # type: ignore[arg-type]
            allocate_step_id=lambda: f"step-{len(self.kept) + 1:02d}",
            on_step=self._keep,
            on_progress=self._say,
        )

    async def _keep(self, step: Step) -> None:
        self.kept.append(step)

    async def _say(self, message: str) -> None:
        self.said.append(message)


def _assertion_step() -> AssertionStep:
    from itb.domain.assertion import Assertion, AssertionKind

    return AssertionStep(
        id="step-01",
        label="문구 확인",
        assertion=Assertion(kind=AssertionKind.TEXT, value="저장되었습니다"),
    )


# ─── 1. 어긋난 검증 ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_mismatch_keeps_the_step_with_the_expected_value_intact() -> None:
    """기대값은 **지시문의 것** 그대로 남는다 — 관찰값으로 대체되지 않는다."""
    h = Harness()
    result = await h.box._execute(_assertion_step(), "assert:text", keep_on_failure=True)

    assert result["ok"] is True
    assert result["assertion_failed"] is True
    assert len(h.kept) == 1
    kept = h.kept[0]
    assert isinstance(kept, AssertionStep)
    assert kept.assertion.value == "저장되었습니다", "기대값이 관찰값으로 바뀌었다"
    assert kept.mismatch is not None
    assert "처리 완료" in kept.mismatch.observed


@pytest.mark.anyio
async def test_the_model_is_told_not_to_change_the_value() -> None:
    """`ok` 와 `assertion_failed` 를 **함께** 싣는 이유가 여기 있다 (FR-010).

    도구 호출로서는 성공했고 검증 결과로서는 어긋났다. 한 축으로 뭉치면 모델이
    「실패했으니 다시」로 읽고, 그 재시도가 곧 버그값을 정답으로 만든다.
    """
    h = Harness()
    result = await h.box._execute(_assertion_step(), "assert:text", keep_on_failure=True)
    assert "바꾸어 다시 시도하지 마세요" in result["note"]


@pytest.mark.anyio
async def test_mismatch_does_not_move_the_failure_streak() -> None:
    """상한에 대해 중립이다 (FR-009). 상한만큼 어긋나도 막히지 않는다."""
    h = Harness()
    for _ in range(MAX_CONSECUTIVE_ELEMENT_FAILURES + 1):
        await h.box._execute(_assertion_step(), "assert:text", keep_on_failure=True)
    assert not h.box.limits.exceeded


@pytest.mark.anyio
async def test_long_observations_are_truncated_and_say_so() -> None:
    """관찰값은 화면 전체 텍스트일 수 있다. 잘랐다는 사실이 드러나야 한다 (FR-008)."""
    h = Harness(message="가" * (MAX_OBSERVED_CHARS + 500))
    await h.box._execute(_assertion_step(), "assert:text", keep_on_failure=True)
    kept = h.kept[0]
    assert isinstance(kept, AssertionStep)
    assert kept.mismatch is not None
    assert len(kept.mismatch.observed) == MAX_OBSERVED_CHARS
    assert kept.mismatch.truncated is True


@pytest.mark.anyio
async def test_sensitive_values_never_reach_the_stored_observation() -> None:
    """어긋남 기록은 **디스크에 남는다** (FR-015).

    진행 알림과 달리 흘러가지 않으므로 여기가 거르는 유일한 자리다.
    """
    secret = "Hunter2Hunter2"
    h = Harness(message=f"기대: '환영' / 실제: '{secret} 님 환영'")
    h.box.scrubber_source = lambda: Scrubber([secret])

    await h.box._execute(_assertion_step(), "assert:text", keep_on_failure=True)
    kept = h.kept[0]
    assert isinstance(kept, AssertionStep)
    assert kept.mismatch is not None
    assert secret not in kept.mismatch.observed


@pytest.mark.anyio
async def test_the_progress_message_says_mismatch_not_failure() -> None:
    """사용자가 읽는 말도 달라야 한다 — 어긋남은 도구의 실패가 아니다."""
    h = Harness()
    await h.box._execute(_assertion_step(), "assert:text", keep_on_failure=True)
    assert any("기대와 다름" in m for m in h.said)


# ─── 2. 동작 Step 은 그대로다 (FR-006) ───────────────────────────────────────


def _action_steps() -> list[tuple[str, Step]]:
    """검증을 뺀 Step 생성 도구 여덟이 만드는 Step 전부."""
    return [
        ("click", ClickStep(id="step-01", label="클릭", target=_target())),
        ("fill", FillStep(id="step-01", label="입력", target=_target(), value="가")),
        ("select", SelectStep(id="step-01", label="선택", target=_target(), value="가")),
        ("navigate", NavigateStep(id="step-01", label="이동", url="https://example.test/")),
        ("hover", HoverStep(id="step-01", label="올리기", target=_target())),
        (
            "drag",
            DragStep(id="step-01", label="끌기", target=_target(), drop_target=_target("drop")),
        ),
        (
            "upload",
            UploadStep(id="step-01", label="올리기", target=_target(), file_name="a.csv"),
        ),
        ("close_tab", CloseTabStep(id="step-01", label="탭 닫기", tab=1)),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(("name", "step"), _action_steps())
async def test_action_steps_are_still_dropped_on_failure(name: str, step: Step) -> None:
    """**기본값이 새면 실패한 클릭이 조용히 기록된다.**

    `_execute` 는 Step 생성 도구 아홉이 함께 지나는 곳이다. 020 이 그 함수를 고쳤으므로,
    나머지 여덟이 그대로인지를 전수로 확인한다 (정합성 점검 F3).
    """
    h = Harness()
    result = await h.box._execute(step, f"{name}:target")

    assert "error" in result, f"{name} 이 실패했는데 오류를 돌려주지 않았다"
    assert h.kept == [], f"{name} 이 실패했는데 Step 으로 기록됐다 (FR-006)"


@pytest.mark.anyio
async def test_action_failure_still_counts_toward_the_streak() -> None:
    """동작 실패는 여전히 연속 실패로 세어진다 — 막힘 판정이 살아 있어야 한다."""
    h = Harness()
    for _ in range(MAX_CONSECUTIVE_ELEMENT_FAILURES):
        await h.box._execute(
            ClickStep(id="step-01", label="클릭", target=_target()), "click:save"
        )
    assert h.box.limits.exceeded


# ─── 3. 막힘의 종류 (FR-023~FR-025) ──────────────────────────────────────────


@pytest.mark.anyio
async def test_product_mismatch_discards_the_question() -> None:
    """제품 동작 불일치에는 사람이 알려 줄 것이 없다 (FR-024).

    **도구 쪽에서 버린다.** 지침에만 적어 두면 모델이 규칙을 어겼을 때 막을 것이 없고,
    그러면 답할 수 없는 질문 앞에서 사용자가 시간을 쓴다.
    """
    h = Harness()
    await h.box.report_blocked(
        "저장 후 목록으로 돌아가지 않습니다.",
        question="어느 목록을 말하는 건가요?",
        kind="product_mismatch",
    )
    assert h.box.blocked_kind is BlockedKind.PRODUCT_MISMATCH
    assert h.box.blocked_question is None


@pytest.mark.anyio
async def test_needs_input_keeps_the_question() -> None:
    """기존 동작은 그대로다 (FR-025)."""
    h = Harness()
    await h.box.report_blocked("어느 계정인지 모릅니다.", question="어느 계정으로 로그인할까요?")
    assert h.box.blocked_kind is BlockedKind.NEEDS_INPUT
    assert h.box.blocked_question == "어느 계정으로 로그인할까요?"


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["", None, "produkt_mismatch", "unknown"])
async def test_unrecognized_kind_falls_back_to_needs_input(kind: Any) -> None:
    """오타가 조용히 답변 칸을 막으면 사용자는 이유를 모른 채 이어갈 방법을 잃는다.

    반대 방향의 오작동(질문이 필요 없는데 칸이 열림)이 덜 해롭다.
    """
    h = Harness()
    await h.box.report_blocked("이유", question="물어볼 것", kind=kind)
    assert h.box.blocked_kind is BlockedKind.NEEDS_INPUT
    assert h.box.blocked_question == "물어볼 것"
