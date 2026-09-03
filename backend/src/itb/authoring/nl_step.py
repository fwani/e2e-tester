"""일시정지 중 자연어로 Step 추가. FR-078~FR-081 (T130).

US4 와 다른 점은 **범위**다. 여기서는 지시 하나가 Step 하나를 만든다. 지금 화면을 분석해
그 한 동작만 수행하고, 성공하면 일시정지 위치에 삽입한다.

**대상을 찾지 못하면 Step 을 만들지 않는다** (FR-081). 알리고 일시정지 상태를 유지한다 —
만들어 두면 재실행에서 반드시 실패하는 Step 이 정의에 들어간다. 실패할 것을 미리 아는데
넣어 두는 것은 사용자에게 더 나쁘다.

만들어진 Step 은 **수동으로 만든 Step 과 구조가 완전히 같다** (FR-080, 원칙 I). 같은
`BrowserToolbox` 를 지나므로 다를 수가 없다 — 그것이 이 설계의 요점이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from itb.authoring.agent import AgentOutcome, AgentStatus, AuthoringAgent, validate_instruction
from itb.authoring.compiler import StepCompiler

NL_STEP_SYSTEM_HINT = """\
지금은 실행이 일시정지된 상태이고, 사용자가 **Step 하나**를 추가하려 합니다.

- observe_page 로 지금 화면을 확인한 뒤 요청된 동작 또는 검증을 **한 번만** 수행하세요.
- 여러 동작으로 나누지 마세요. 하나를 넘기면 사용자가 의도한 것보다 많이 바뀝니다.
- 요청한 대상을 화면에서 찾을 수 없으면 report_blocked 로 알리세요.
  추측으로 비슷한 요소를 누르지 마세요.
"""

MAX_TOOL_CALLS_FOR_ONE_STEP = 8
"""Step 하나를 만드는 데 허용할 도구 호출 수.

관찰 몇 번과 동작 한 번이면 끝난다. 넉넉히 두면 "하나만" 이라는 제약이 사라져 화면이
사용자가 의도한 것보다 많이 바뀐다.
"""


@dataclass(slots=True)
class NlStepResult:
    """자연어 Step 추가 결과."""

    created: bool
    message: str
    step_id: str | None = None

    @property
    def kept_paused(self) -> bool:
        """일시정지 상태를 유지했는가. 실패해도 항상 유지한다 (FR-081)."""
        return True


def _describe_failure(outcome: AgentOutcome) -> str:
    if outcome.status is AgentStatus.BLOCKED:
        return (
            f"요청한 대상을 화면에서 찾지 못해 Step 을 만들지 않았습니다. "
            f"{outcome.reason or ''}".strip()
        )
    if outcome.status is AgentStatus.ERROR:
        return f"Step 을 만들지 못했습니다. {outcome.reason or ''}".strip()
    return "Step 이 만들어지지 않았습니다. 지시를 더 구체적으로 적어 보세요."


async def add_step(
    agent: AuthoringAgent, compiler: StepCompiler, instruction: str
) -> NlStepResult:
    """자연어 지시 하나로 Step 하나를 만든다.

    **성공 판정은 컴파일러가 센 Step 수다.** 에이전트가 "했다" 고 말하는 것이 아니라
    도구가 실제로 성공해 Step 이 확정된 것만 성공으로 본다 (FR-061 과 같은 규칙).
    """
    text = validate_instruction(instruction)
    before = compiler.count

    agent.toolbox.limits.max_calls = MAX_TOOL_CALLS_FOR_ONE_STEP
    agent.toolbox.limits.calls = 0
    outcome = await agent.run(f"{NL_STEP_SYSTEM_HINT}\n요청: {text}")

    created = compiler.count - before
    if created <= 0:
        return NlStepResult(created=False, message=_describe_failure(outcome))

    step = compiler.compiled[-1]
    if created > 1:
        # 하나만 만들라고 했는데 여러 개가 됐다. 지운다면 브라우저 상태와 어긋나므로
        # **남기고 사실을 알린다** — 이미 화면에 적용된 동작을 정의에서만 지우면 그 편집이
        # 화면에 반영되지 않는 것과 같은 상황이 된다 (FR-040a).
        return NlStepResult(
            created=True,
            step_id=step.id,
            message=(
                f"요청 하나에 Step {created}개가 만들어졌습니다. 브라우저에는 이미 적용된 "
                "동작이므로 그대로 남겼습니다. 필요 없는 Step 은 지우고 화면을 정리하세요."
            ),
        )
    return NlStepResult(
        created=True,
        step_id=step.id,
        message=f"Step 을 추가했습니다: {step.label}",
    )
