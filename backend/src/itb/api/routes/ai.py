"""언어모델 사용 가능 여부. DR-021. contracts/rest-api-delta.md §8.

**작성 경로 전용이다.** 저장된 테스트의 재실행 경로는 이 모듈을 읽지 않는다.
`itb.api` 계층에 있으므로 `.importlinter` 의 `execution-no-llm` 계약을 위반하지 않는다 —
그 계약의 `source_modules` 는 `itb.execution` 등이고 `itb.api` 는 거기 없다 (원칙 II).

**언어모델을 호출하지 않는다.** 자격 증명을 해석할 수 있는지만 본다. 호출하면 비용과
지연이 생기고, 화면에 들어올 때마다 그것을 치를 이유가 없다.

**자격 증명의 어떤 조각도 반환하지 않는다** (헌법 보안 요구). 가능 여부와 안내 문구뿐이다.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    reason: str | None
    """쓸 수 없을 때 **무엇이 준비되지 않았고 무엇을 하면 되는지.** 사용자가 그대로
    읽고 조치할 수 있어야 한다."""


@router.get("/availability")
async def availability() -> AvailabilityResponse:
    """자격 증명을 해석할 수 있는가.

    **실패해도 200 이다.** 점검 자체가 오류로 끝나면 화면이 또 조용해진다 — 그것이
    이 라운드가 고치는 결함이다 (DR-016).
    """
    # 지연 임포트. 재실행만 쓰는 경로에서 언어모델 경계 모듈을 적재하지 않는다.
    from itb.llm.client import LlmUnavailableError, create_client  # noqa: PLC0415

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
