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
from pydantic import BaseModel, ConfigDict

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
