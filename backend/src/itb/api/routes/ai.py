"""언어모델 사용 가능 여부. DR-021. contracts/rest-api-delta.md §8.

**작성 경로 전용이다.** 저장된 테스트의 재실행 경로는 이 모듈을 읽지 않는다.
`itb.api` 계층에 있으므로 `.importlinter` 의 `execution-no-llm` 계약을 위반하지 않는다 —
그 계약의 `source_modules` 는 `itb.execution` 등이고 `itb.api` 는 거기 없다 (원칙 II).

**언어모델을 호출하지 않는다.** 자격 증명을 해석할 수 있는지만 본다. 호출하면 비용과
지연이 생기고, 화면에 들어올 때마다 그것을 치를 이유가 없다.

**자격 증명의 어떤 조각도 반환하지 않는다** (헌법 보안 요구). 가능 여부와 안내 문구뿐이다.
"""

from __future__ import annotations

import importlib.util
import os
import shutil

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from itb.domain.test_case import MAX_INSTRUCTION_CHARS

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    reason: str | None
    """쓸 수 없을 때 **무엇이 준비되지 않았고 무엇을 하면 되는지.** 사용자가 그대로
    읽고 조치할 수 있어야 한다."""


def _claude_code_availability() -> AvailabilityResponse:
    """개발용 드라이버가 쓸 준비가 되었는가 (`ITB_AI_DRIVER=claude-code`).

    **`claude` 를 실행하지 않는다.** 화면에 들어올 때마다 프로세스를 띄울 이유가 없고,
    이 모듈의 규칙(언어모델을 호출하지 않는다)과도 어긋난다. 그래서 값싸게 확인할 수 있는
    두 가지만 본다 — 선택 의존성과 실행 파일.

    **로그인 여부는 확인하지 못한다.** 이 경로는 개발자가 자기 머신에서 켜는 것이고,
    로그인이 안 되어 있으면 첫 「AI 실행」에서 사유와 함께 실패한다. 제품 기본 경로는
    이 한계를 갖지 않는다 (아래 `availability` 본문이 자격 증명을 실제로 해석한다).
    """
    if importlib.util.find_spec("claude_agent_sdk") is None:
        return AvailabilityResponse(
            available=False,
            reason=(
                "개발용 드라이버(ITB_AI_DRIVER=claude-code)가 켜져 있지만 "
                "claude-agent-sdk 가 설치되지 않았습니다. "
                "`uv sync --extra claude-code` 를 실행하세요."
            ),
        )
    if shutil.which("claude") is None:
        return AvailabilityResponse(
            available=False,
            reason=(
                "개발용 드라이버(ITB_AI_DRIVER=claude-code)가 켜져 있지만 "
                "`claude` 실행 파일을 찾을 수 없습니다. Claude Code 를 설치하고 "
                "로그인한 뒤 백엔드를 다시 시작하세요."
            ),
        )
    return AvailabilityResponse(available=True, reason=None)


@router.get("/availability")
async def availability() -> AvailabilityResponse:
    """자격 증명을 해석할 수 있는가.

    **실패해도 200 이다.** 점검 자체가 오류로 끝나면 화면이 또 조용해진다 — 그것이
    이 라운드가 고치는 결함이다 (DR-016).
    """
    # 지연 임포트. 재실행만 쓰는 경로에서 언어모델 경계 모듈을 적재하지 않는다.
    from itb.authoring.agent import DRIVER_CLAUDE_CODE, DRIVER_ENV  # noqa: PLC0415
    from itb.llm.client import LlmUnavailableError, create_client  # noqa: PLC0415

    # 개발용 드라이버를 켜 두었으면 **자격 증명이 아니라 `claude` 를 본다.** 이것을
    # 갈라 두지 않으면 Claude Code 로 돌려도 화면은 "자격 증명 없음" 을 계속 보여주고
    # 버튼이 잠긴 채로 남는다 — 백엔드가 되는데 화면에서 안 되는 상태다.
    if os.environ.get(DRIVER_ENV, "").strip() == DRIVER_CLAUDE_CODE:
        return _claude_code_availability()

    try:
        client = create_client()
    except LlmUnavailableError as exc:
        return AvailabilityResponse(available=False, reason=str(exc))
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 사용자에게 알린다
        return AvailabilityResponse(
            available=False,
            reason=(
                "언어모델을 준비할 수 없습니다. "
                f"({type(exc).__name__}) 직접 녹화로 테스트를 만들 수 있습니다."
            ),
        )
    # SDK 는 자격 증명이 하나도 없어도 **만들어진다** — 실패는 첫 요청에서 난다. 그래서
    # 생성 성공만 보면 자격 증명 없는 환경에서 `available: true` 를 돌려주고, 사용자는
    # 「AI 실행」을 눌러야 실패를 알게 된다 (UX U-07 에서 실제로 그랬다). 생성자가 해석한
    # 세 갈래(정적 키·토큰·프로필/연합 자격 증명)가 전부 비어 있으면 없는 것이다.
    if (
        getattr(client, "api_key", None) is None
        and getattr(client, "auth_token", None) is None
        and getattr(client, "credentials", None) is None
    ):
        return AvailabilityResponse(
            available=False,
            reason=(
                "언어모델 자격 증명을 찾을 수 없습니다. `ANTHROPIC_API_KEY` 를 환경 변수로 "
                "주거나 `ant auth login` 으로 로그인하세요. 직접 녹화로 테스트를 만들 수 있습니다."
            ),
        )
    return AvailabilityResponse(available=True, reason=None)


# ─── 지시문 정제 (025 US4 · contracts/api-contract.md §1) ──────────────────
#
# **세션 생성과 갈라 둔다** (research R7). 세션 생성 안에서 정제하면 사용자는 브라우저가
# 뜬 뒤에 결과를 보게 되고, 고치려면 이미 시작된 일을 되돌려야 한다. 두 호출로 나누면
# 「시작했다가 취소한 세션」이라는 상태 자체가 생기지 않는다.
#
# 이 자리에 두는 이유는 `ai.py` 가 이미 **작성 경로 전용**이기 때문이다. 재실행 경로는
# 이 모듈을 읽지 않는다 (헌법 원칙 II).


class RefineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(min_length=1, max_length=MAX_INSTRUCTION_CHARS)
    """정제할 지시문. 길이 상한의 출처는 `itb.domain.test_case` 하나다 — 세션 생성이
    쓰는 것과 같아야, 정제를 지난 지시문이 세션 생성에서 거절되는 자리가 생기지 않는다."""


class RefinedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    order: int
    text: str
    status: str
    skip_reason: str | None = None


class RefinedConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    scope: str
    item_id: str | None = None


class RefinedPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[RefinedItem]
    constraints: list[RefinedConstraint]
    source: str


class RefineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refined: bool
    """정제가 성공했는가. **실패해도 200 이다** — 아래 설명을 보라."""

    plan: RefinedPlan | None
    notes: list[str]
    """사용자에게 알릴 것. **뜻이 바뀐 자리를 반드시 싣는다** — 자격 증명을 변수 참조로
    바꾼 것 같은. 조용히 바꾸면 사용자는 자기가 적은 값이 쓰이는 줄 안다."""


@router.post("/refine")
async def refine(body: RefineRequest) -> RefineResponse:
    """지시문을 작업 계획으로 정제한다 (025 FR-014 · FR-020).

    ## **실패도 200 이다**

    정제 실패는 작성을 막는 사건이 아니다. 400 으로 돌려주면 화면이 그것을 오류로 다루고,
    그러면 정제가 작성의 관문이 된다 — 이 기능의 경계가 정확히 그 반대다 (FR-020).

    요청 검증 실패(빈 지시문·길이 초과)만 422 다. 그것은 Pydantic 이 돌려준다.

    ## 세션을 만들지 않는다

    화면이 결과를 보여 주고 사용자가 확정한 뒤에, 그 계획을 실어 세션 생성을 부른다
    (FR-018 · contracts/api-contract.md §2).
    """
    from itb.authoring.refine import refine_instruction  # noqa: PLC0415

    result = await refine_instruction(body.instruction)
    if not result.refined or result.plan is None:
        return RefineResponse(refined=False, plan=None, notes=result.notes)

    plan = result.plan
    return RefineResponse(
        refined=True,
        plan=RefinedPlan(
            items=[
                RefinedItem(
                    id=i.id,
                    order=i.order,
                    text=i.text,
                    status=i.status.value,
                    skip_reason=i.skip_reason,
                )
                for i in plan.items
            ],
            constraints=[
                RefinedConstraint(text=c.text, scope=c.scope.value, item_id=c.item_id)
                for c in plan.constraints
            ],
            source=plan.source.value,
        ),
        notes=result.notes,
    )
