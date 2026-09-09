"""조작 위치 전환과 브라우저 요구 응답 (010 T061·T072·T073 · contracts §3).

**명령은 REST 로 남는다.** 조작 사건은 WebSocket 을 타지만(그것은 명령이 아니라 대상
브라우저로 흘려보내는 입력이다), 조작 위치를 바꾸는 것과 브라우저 요구에 답하는 것은
명령이다 — 상태를 바꾸고, 한 번만 일어나야 하며, 결과를 응답으로 확인해야 한다
(research R4).

**전환은 사용자 요청으로만 일어난다** (FR-353). 서버가 상황을 판단해 스스로 창을 열지
않는다 — 요청하지 않은 창은 그 자체로 조작 위치를 잃게 만들고, 화면 없는 기계에서는
자동 전환이 실패한다. 이 파일에 「강등을 감지하면 창을 연다」 같은 경로가 없는 것이
그 요구의 구현이다.
"""

from __future__ import annotations

import contextlib
import os
import sys
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from itb.api.errors import ErrorCode, bad_request, not_found
from itb.api.state import AppState, get_state
from itb.execution.session import HEADLESS_ENV

router = APIRouter(prefix="/api/sessions", tags=["control"])

State = Annotated[AppState, Depends(get_state)]

SESSION_GONE = "세션이 이미 끝났습니다."
"""`sessions.py`·`tabs.py` 와 **같은 문장**을 쓴다 (005 FR-135·FR-141).

같은 사실을 세 엔드포인트가 다른 말로 부르면 사용자는 다른 일이 일어난 줄 안다.
"""

ControlSurface = Literal["mirror", "window"]


class ControlSurfaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: ControlSurface


class ControlSurfaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: ControlSurface


class PromptResponseRequest(BaseModel):
    """브라우저 요구에 대한 사용자의 응답 (contracts §3 · data-model §4)."""

    model_config = ConfigDict(extra="forbid")

    accept: bool = True
    text: str | None = None
    """`prompt` 대화상자의 입력값. 다른 종류에서는 무시된다."""

    file_ids: list[str] = []
    """파일 선택 응답. 업로드로 얻은 식별자다 (FR-337)."""


def can_open_a_window() -> bool:
    """이 기계에서 창을 띄울 수 있는가 (FR-351).

    **화면 없는 기계에서 전환을 요청하면 열 창이 없다.** 조용히 실패하면 사용자는 창이
    어딘가 열렸는데 못 찾는 것으로 읽고 찾아 헤맨다 — 그것이 FR-339 가 금지하는 형태다.

    판정은 보수적이지 않고 **사실에 가깝게** 한다.

    - macOS·Windows 는 창 서버가 항상 있다.
    - 리눅스는 `DISPLAY`(X11) 또는 `WAYLAND_DISPLAY` 가 있어야 한다. CI 러너·원격 서버
      에는 둘 다 없다.

    이 판정이 틀리는 경우(원격 X 전달 등)에도 손해는 「열 수 있는데 못 연다고 말하는 것」
    이며, 반대 방향(열 수 없는데 열겠다고 하고 실패하는 것)보다 낫다 — 사용자가 사유를
    읽고 미러로 계속 갈 수 있다.
    """
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


@router.post("/{session_id}/control-surface")
async def set_control_surface(
    session_id: str, body: ControlSurfaceRequest, state: State
) -> ControlSurfaceResponse:
    """조작 위치를 옮긴다 (FR-349·FR-351·FR-353 · contracts §3).

    **세션 상태와 녹화는 유지된다.** 창을 여는 것은 `BrowserContext` 를 새로 만드는 것이
    아니라 이미 살아 있는 탭을 앞으로 가져오는 것이다 — 인증·화면·입력값이 그대로 남는
    이유가 그것이고, 원칙 III 이 요구하는 성질이다.

    창을 띄울 수 없는 환경이면 **사유와 함께 거절한다** (FR-351).
    """
    from itb.api.routes.sessions import surface_of, work_of

    w = work_of(session_id)

    if body.surface == "window":
        if not can_open_a_window():
            raise bad_request(
                ErrorCode.INVALID_REQUEST,
                "이 기계에는 띄울 창이 없어 실제 창으로 전환할 수 없습니다. "
                "미러에서 계속 조작하세요.",
                detail={"reason": "headless_environment", "env": HEADLESS_ENV},
            )
        # 이미 살아 있는 탭을 앞으로 가져온다. 실패해도 전환 자체는 성립한다 —
        # 창이 뒤에 있는 것과 창이 없는 것은 다르다.
        with contextlib.suppress(Exception):
            await w.session.bring_tab_to_front(w.session.mirrored_tab_index)
        # 조작 위치가 창으로 옮겨갔으므로 미러의 조작 통로를 닫는다. 두 위치에서 동시에
        # 조작이 들어오면 같은 화면에 두 벌의 입력이 섞인다.
        await state.control.close(
            session_id, "실제 브라우저 창으로 조작 위치를 옮겼습니다."
        )

    surface = surface_of(w, body.surface)
    await w.session.emit("control_surface", surface=surface)
    return ControlSurfaceResponse(surface=surface)


@router.post("/{session_id}/prompts/{prompt_id}", status_code=204)
async def answer_prompt(
    session_id: str, prompt_id: str, body: PromptResponseRequest, state: State
) -> None:
    """브라우저 요구에 답한다 (FR-338·FR-340 · contracts §3).

    **이미 해소된 요구와 다른 세션의 `prompt_id` 는 거절한다** (FR-340). 세션 식별자만으로
    임의의 다른 세션을 조작할 수 없어야 하고, `prompt_id` 는 그 세션 안에서만 뜻을 갖는다 —
    요구 사전이 세션마다 따로 있으므로 그 격리가 **검사가 아니라 구조로** 성립한다.
    """
    from itb.api.routes.sessions import work_of

    w = work_of(session_id)
    prompts = w.prompts
    if prompts is None:
        raise not_found(
            ErrorCode.PROMPT_NOT_FOUND,
            "이 세션은 브라우저 요구를 받고 있지 않습니다.",
            prompt_id=prompt_id,
        )

    paths = _resolve_files(state, session_id, body.file_ids)
    answered = await prompts.answer(
        prompt_id, accept=body.accept, text=body.text, paths=paths
    )
    if not answered:
        raise not_found(
            ErrorCode.PROMPT_NOT_FOUND,
            "그 요구는 이미 처리되었거나 이 세션의 것이 아닙니다.",
            prompt_id=prompt_id,
        )


def _resolve_files(state: AppState, session_id: str, file_ids: list[str]) -> list[str]:
    """업로드 식별자를 실제 경로로 바꾼다 (FR-340).

    **다른 세션의 파일은 찾을 수 없다.** 저장소가 세션 단위로 나뉘어 있으므로 그 격리가
    조회 자체에서 성립한다 — 검사로 막는 것이 아니라 구조로 막는다. 여기서 사용자가 보낸
    값으로 경로를 만들지 않는 것도 같은 성질이다 (FR-337c): 경로는 업로드 시점에 서버가
    발급한 식별자로 이미 만들어져 있고, 여기서는 사전 조회만 한다.
    """
    if not file_ids:
        return []
    store = state.session_files.get(session_id)
    if store is None:
        raise not_found(
            ErrorCode.UPLOAD_NOT_FOUND,
            "이 세션에 올린 파일이 없습니다.",
            file_ids=file_ids,
        )
    paths: list[str] = []
    for file_id in file_ids:
        path = store.path_of(file_id)
        if path is None:
            raise not_found(
                ErrorCode.UPLOAD_NOT_FOUND,
                "그 파일을 찾을 수 없습니다. 다시 올려 주세요.",
                file_id=file_id,
            )
        paths.append(str(path))
    return paths
