"""Step 모델. 헌법 원칙 I (Unified Step Model, NON-NEGOTIABLE).

**사람이 만든 Step 과 AI 가 만든 Step 은 같은 타입이다.** ``author`` 는 부가 정보이며
실행 방식을 바꾸지 않는다 (FR-014). 컴포넌트별 별도 표현을 두지 않는다.
"""

from __future__ import annotations

import mimetypes
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from itb.domain.assertion import Assertion
from itb.domain.locator import TargetLocator

STEP_ID_PATTERN = r"^step-\d{2,}$"
DEFAULT_TIMEOUT_MS = 10_000
"""Step 하나가 쓸 수 있는 총 시간의 기본값 (004 FR-115, research R5).

001 의 5000ms 에서 올렸다. **결함 수정이 아니라 여유 확보다** — 004 가 고친 로딩 오탐의
원인은 예산 부족이 아니라 예산을 쓰는 방식이었다(research R1). 다만 실제 앱의 목록·표는
API 왕복과 렌더에 3~5초가 드물지 않고, 5초는 그 경계에 걸쳐 있어 환경 속도에 따라 통과와
실패가 갈린다 — 재실행 성공률 ≥95% 목표(PRD §18)를 직접 위협한다.

15초 이상으로 두지 않는 이유: 실패를 확인하는 시간이 그만큼 늘어난다. `느림` 으로 돌리며
디버깅할 때 한 Step 이 15초씩 매달리면 속도 조절의 이득이 상쇄된다.

**이 값은 여기 한 곳에만 있다.** 생성기가 `step.timeout_ms` 를 그대로 읽으므로 내보낸
Playwright 코드에도 자동으로 반영된다 (FR-118). `locator.strategy` 로 옮기지 않는 이유는
`.importlinter` 의 `domain-is-pure` 계약이 `itb.domain` → `itb.locator` 임포트를 금지하기
때문이다 (data-model §8).
"""


class Author(StrEnum):
    HUMAN = "human"
    AI = "ai"


class StepType(StrEnum):
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    NAVIGATE = "navigate"
    ASSERTION = "assertion"
    CLOSE_TAB = "close_tab"
    HOVER = "hover"
    """마우스를 올리는 동작 (FR-023c). hover 로만 열리는 메뉴가 있는 화면에 필요하다."""

    DRAG = "drag"
    """끌어다 놓는 동작 (FR-023c)."""

    UPLOAD = "upload"
    """파일을 올리는 동작 (2026-09-09 사용자 보고 — 「파일 업로드 녹화가 제대로 안됨」).

    **이 종류가 없어서 업로드가 기록되지 않았다.** 리코더는 파일 입력을 감지하고도
    ``파일 입력이 감지됐습니다 … Step 편집에서 파일 경로를 직접 지정해야 합니다`` 라는
    경고만 남겼는데, 그 「Step 편집」에는 파일을 지정할 칸도 Step 종류도 없었다. 001
    research 가 「감지해 Step 을 만들되 경로는 사용자가 지정한다」로 정했지만(research.md)
    구현이 비어 있었고 문구만 남아 있었다.
    """


class _StepBase(BaseModel):
    """모든 Step 이 공유하는 필드.

    ``json_schema_serialization_defaults_required=True`` 는 직렬화 스키마에서 기본값이
    있는 필드도 required 로 표기하게 한다. 직렬화된 Step 에는 기본값이 항상 채워져 있고,
    ``type`` 이 옵셔널이면 생성된 TypeScript 가 판별 유니온으로 좁힐 수 없다 (research R6).
    """

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    id: str = Field(pattern=STEP_ID_PATTERN)
    label: str = Field(min_length=1, max_length=200)
    """사람이 읽는 표시 이름. 목록·결과 화면에 나온다."""

    author: Author = Author.HUMAN
    """작성 주체. **실행 방식을 바꾸지 않는다** (FR-014)."""

    tab: int = Field(default=0, ge=0)
    """탭 참조. 열린 순서이며 최초 탭이 0이다 (FR-030a). 번호는 재사용하지 않는다."""

    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1, le=60_000)
    frame_url: str | None = Field(default=None, max_length=2000)
    """하위 프레임에서 기록된 경우. MVP 실행은 main frame 만 대상으로 한다."""


class ClickStep(_StepBase):
    type: Literal[StepType.CLICK] = StepType.CLICK
    target: TargetLocator


class FillStep(_StepBase):
    type: Literal[StepType.FILL] = StepType.FILL
    target: TargetLocator
    value: str = Field(max_length=4000)
    """``{{변수명}}`` 참조를 쓸 수 있다. 민감 값은 반드시 참조로만 저장한다 (FR-082)."""


class SelectStep(_StepBase):
    type: Literal[StepType.SELECT] = StepType.SELECT
    target: TargetLocator
    value: str = Field(max_length=2000)


class NavigateStep(_StepBase):
    type: Literal[StepType.NAVIGATE] = StepType.NAVIGATE
    url: str = Field(min_length=1, max_length=2000)


class AssertionStep(_StepBase):
    type: Literal[StepType.ASSERTION] = StepType.ASSERTION
    assertion: Assertion


class HoverStep(_StepBase):
    """마우스를 올리는 동작 (FR-023c).

    **화면을 바꾼 hover 만 기록한다.** 포인터가 지나간 모든 요소를 Step 으로 만들면 정의가
    쓸모없이 길어지고, 어느 hover 가 의미 있었는지 사람이 다시 판단해야 한다. 리코더는
    hover 직후 문서 변화가 관측된 경우만 이 Step 을 만든다 (contracts/step-dsl.md).
    """

    type: Literal[StepType.HOVER] = StepType.HOVER
    target: TargetLocator


class DragStep(_StepBase):
    """끌어다 놓는 동작 (FR-023c).

    ``target`` 이 끄는 대상이고 ``drop_target`` 이 놓는 위치다. 다른 Step 과 마찬가지로
    ``target`` 이 주된 대상이므로 `target_of` 가 그대로 동작한다.
    """

    type: Literal[StepType.DRAG] = StepType.DRAG
    target: TargetLocator
    drop_target: TargetLocator


class UploadStep(_StepBase):
    """파일을 올리는 동작 (2026-09-09 사용자 보고).

    ## 무엇을 기록하는가 — **파일 이름 하나다**

    사용자가 요구한 것은 확장자다: 「파일업로드 녹화의 경우, 파일의 확장자 기록되 되어야함.
    실제 서비스에서는 확장자를 보는경우가 있기 때문」.

    그래서 이 Step 은 ``file_name`` 을 갖고, **확장자는 그 이름의 일부다.** 확장자를 별도
    필드로 두지 않는 이유는 진실이 둘이 되기 때문이다 — 이름이 ``보고서.xlsx`` 인데
    확장자 필드가 ``csv`` 인 Step 이 만들어질 수 있고, 그때 어느 쪽이 맞는지 아무도 모른다.
    확장자가 필요한 곳은 `extension_of` 로 꺼낸다.

    **파일 내용은 기록하지 않는다.** 녹화 시점에 브라우저가 주는 것은 이름뿐이고
    (``File.name``), 내용을 정의 파일에 담으면 테스트가 옮겨 다닐 수 없게 된다. 재실행은
    같은 이름의 빈 파일을 만들어 올린다 — 확장자를 보는 검증은 통과하고, 내용을 파싱하는
    검증은 통과하지 못한다. 그 한계는 실행기 쪽에 적어 두었다.
    """

    type: Literal[StepType.UPLOAD] = StepType.UPLOAD
    target: TargetLocator
    file_name: str = Field(min_length=1, max_length=255)
    """녹화 때 고른 파일의 이름. **확장자를 포함한다** — 그것이 이 Step 의 핵심 정보다."""


class CloseTabStep(_StepBase):
    """탭 닫기 (FR-030c). 대상은 공통 ``tab`` 필드가 가리킨다."""

    type: Literal[StepType.CLOSE_TAB] = StepType.CLOSE_TAB


Step = Annotated[
    ClickStep
    | FillStep
    | SelectStep
    | NavigateStep
    | AssertionStep
    | CloseTabStep
    | HoverStep
    | DragStep
    | UploadStep,
    Field(discriminator="type"),
]
"""판별 유니온. 이 하나가 제품 전체의 유일한 테스트 표현이다 (원칙 I)."""


def extension_of(file_name: str) -> str:
    """파일 이름에서 확장자를 꺼낸다 — **점 없이, 소문자로** (2026-09-09).

    판정을 한 곳에 두는 이유는 이 값이 두 곳에서 쓰이기 때문이다: 화면이 행에 표시하고,
    실행기가 올릴 임시 파일의 이름을 만든다. 각자 잘라 쓰면 ``.tar.gz`` 같은 이름에서
    답이 갈린다 (여기서는 마지막 조각만 본다 — ``gz``).

    확장자가 없으면 빈 문자열이다. 확장자 없는 파일도 올릴 수 있으므로 오류가 아니다.

    **숨김 파일은 확장자가 없다** (``.gitignore`` → ``""``). 검사가 이것을 잡았다 —
    첫 판은 마지막 점 뒤를 그대로 돌려줘 ``gitignore`` 를 확장자로 봤고, 화면 쪽
    (`uploadExtension`)은 처음부터 점이 맨 앞이면 확장자가 없다고 봤다. 같은 파일에 대해
    두 곳이 다른 답을 내는 상태이며, 이 함수의 주석이 경계한 바로 그 갈림이었다.
    """
    stem, dot, tail = file_name.rpartition(".")
    if not dot or not tail or not stem:
        return ""
    return tail.strip().lower()


def mime_type_of(file_name: str) -> str:
    """파일 이름에서 MIME 유형을 정한다 (2026-09-09).

    업로드를 받는 서버가 확장자 대신 ``Content-Type`` 을 보는 경우가 있다. 이름에서
    유추할 수 있는 것은 여기서 유추하고, 모르면 ``application/octet-stream`` 이다 —
    그것이 「모르는 바이트 묶음」의 표준 표기이며, 지어내면 서버가 다른 이유로 거절한다.

    **판정을 여기 두는 이유**는 두 곳이 같은 답을 써야 하기 때문이다: 제품의 재실행
    (`step_executor`)과 생성된 Playwright 코드(`playwright_gen`). 갈리면 「제품에서는
    되는데 내보낸 코드에서는 안 되는」 테스트가 만들어진다 (FR-118 이 막으려는 것).
    """
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


def target_of(step: object) -> TargetLocator | None:
    """Step 의 대상 요소를 꺼낸다. 대상이 없는 종류면 None.

    호출자가 ``isinstance`` 분기를 반복하지 않게 하는 편의 함수다.
    """
    tgt = getattr(step, "target", None)
    if tgt is not None:
        return tgt
    assertion = getattr(step, "assertion", None)
    if assertion is not None:
        return assertion.target
    return None
