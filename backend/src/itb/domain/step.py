"""Step 모델. 헌법 원칙 I (Unified Step Model, NON-NEGOTIABLE).

**사람이 만든 Step 과 AI 가 만든 Step 은 같은 타입이다.** ``author`` 는 부가 정보이며
실행 방식을 바꾸지 않는다 (FR-014). 컴포넌트별 별도 표현을 두지 않는다.
"""

from __future__ import annotations

import mimetypes
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from itb.domain.assertion import Assertion, AuthoringMismatch
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


class PressKey(StrEnum):
    """키 입력 Step 이 누를 수 있는 키 (023 FR-052·FR-053).

    ## 왜 자유 문자열이 아닌가

    | | 자유 문자열 | 열거형 |
    |---|---|---|
    | 오타 (`enter` 대 `Enter`) | **실행 시점까지 숨는다** | 정의 시점에 거절 |
    | AI 가 없는 키를 지어내면 | 실행 시점 오류 | 도구 호출이 즉시 거절 |
    | 생성된 코드 | **검증 안 된 문자열이 그대로 나간다** | 목록에 있는 값만 |

    세 번째 줄에서 갈렸다. 헌법의 보안 제약이 「생성된 Playwright 코드는 생성 중
    **데이터로 다루어야** 하며 페이지에서 온 문자열의 이스케이프되지 않은 결합으로
    만들어서는 안 된다」고 못박는다. 검증되지 않은 키 이름이 생성기로 들어가는 경로를
    열지 않는다 (023 research R12).

    ## 왜 넷뿐인가

    ``ENTER``·``SPACE`` 는 사용자가 요구한 것이고, ``TAB``·``ESCAPE`` 는 같은
    「확정·이동·취소」 계열이면서 클릭으로 대신할 수 없다. 화살표는 선택 Step 이,
    Backspace 는 입력 Step 이 담당한다. 문자 키는 입력 Step 이 담당하며, 키로 쪼개면
    녹화가 피해 온 IME 조합 문제가 되돌아온다.

    **넓히는 것은 값을 더하는 일이다.** 좁게 시작하는 것이 나중을 막지 않는다.

    ## 값이 표준 도구의 키 이름과 같은 철자다

    변환표를 두지 않기 위해서다. 표가 있으면 어느 쪽이 권위인지 매번 판단해야 하고 값을
    더할 때마다 두 곳을 고쳐야 한다 (023 contracts/export-mapping.md §6).
    """

    ENTER = "Enter"
    SPACE = "Space"
    TAB = "Tab"
    ESCAPE = "Escape"


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


    PRESS = "press"
    """키를 누르는 동작 (023 — 사용자 보고 「엔터·스페이스를 인식하지 못해 스텝 생성이 실패」).

    **이 종류가 없어서 태그 칸을 다룰 수 없었다.** 「태그를 입력한 뒤 Enter 또는 Space를
    눌러 추가하세요」 같은 위젯은 키가 확정 동작이라, 값을 넣는 것만으로는 아무 일도
    일어나지 않는다. 우회로도 없다 — 그런 칸 옆에는 「추가」 버튼이 없다.

    **사람도 AI 도 만들 수 없었다.** 녹화는 키를 듣지 않았고 AI 도구는 Step 종류와 1:1 로
    대응하므로 그쪽에도 없었다. 원칙 I 의 관점에서 대칭적으로 비어 있었고, 이 종류가 그
    간극을 메운다.
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

    mismatch: AuthoringMismatch | None = None
    """작성 시점에 이 검증이 통과하지 않았다는 기록 (020 FR-005).

    ``None`` 이면 작성 시점에 통과했다. **020 이전에 저장된 모든 정의가 여기 해당한다** —
    그 정의들은 통과할 때만 기록됐기 때문이다. 그래서 마이그레이션이 필요 없다.

    ## 왜 `_StepBase` 가 아니라 여기인가

    「어긋난 클릭 Step」은 **원리적으로 존재할 수 없다.** 동작 Step 은 실패하면 기록되지
    않는다 (020 FR-006). 공통 필드로 올리면 나머지 8종에 **영원히 ``None`` 인 칸**이
    생기고, 읽는 쪽은 그 칸이 왜 비어 있는지를 매번 판단해야 한다.

    ## 왜 `assertion` 안이 아닌가

    :class:`~itb.domain.assertion.Assertion` 은 **조건**이다. 「그때 어땠는가」는 조건이
    아니라 이력이고, Playwright 생성기가 `Assertion` 만 읽으므로 거기 섞으면 내보낸
    코드에 새어 나간다.

    ## 실행을 바꾸지 않는다 (헌법 원칙 I · FR-012)

    ``author`` 와 같은 성질의 **부가 정보**다. 실행기는 이 필드를 읽지 않으며, 사람이
    만든 검증도 같은 필드를 갖는다 (FR-011). 원칙이 허용하는 「MAY be recorded as
    metadata, MUST NOT change how the Step executes」에 정확히 해당한다.

    그 불변식은 문장이 아니라 검사가 지킨다 —
    ``tests/unit/test_mismatch_isolation.py`` 가 실행기와 생성기의 소스에 이 이름이
    나타나지 않음을 고정한다.
    """


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


class PressStep(_StepBase):
    """키를 누르는 동작 (023 FR-050).

    ## ``target`` 이 필수인 이유 — 포커스에 기대지 않는다

    「지금 포커스된 곳에 Enter」는 **앞 Step 의 부작용에 결과가 좌우된다.** 정의만 보고
    무엇을 했는지 알 수 없고, 화면이 조금 바뀌면 엉뚱한 요소가 키를 받는다. 원칙 II 가
    요구하는 「같은 화면이면 같은 결과」가 성립하지 않는다.

    그래서 실행도 내보내기도 **대상 요소에 포커스를 준 뒤** 키를 보낸다 (FR-051).

    ## ``value`` 가 아니라 ``key`` 인 이유

    :class:`FillStep` 의 ``value`` 는 **사람이 친 글자**이고 민감할 수 있어 변수 참조로
    저장된다. 여기의 ``key`` 는 **어느 키를 눌렀는가**이고 열거값이며 비밀이 될 수 없다.
    이름을 같게 하면 민감값 처리 코드가 이 필드도 훑어야 하는지 매번 판단하게 된다.

    ## 이 Step 은 결과를 판정하지 않는다

    「Enter 를 눌렀더니 태그가 생겼다」를 확인하려면 **검증 Step 을 따로** 둔다. 키를
    눌렀는데 화면이 안 바뀌어도 이 Step 은 성공이다 — 동작과 판정을 한 Step 에 뭉치면
    실패했을 때 어느 쪽이 틀렸는지 알 수 없다.
    """

    type: Literal[StepType.PRESS] = StepType.PRESS
    target: TargetLocator
    key: PressKey
    """누를 키. **열거형이라 임의 문자열이 실행기·생성기에 도달할 수 없다.**"""


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
    | UploadStep
    | PressStep,
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


def press_label(key: PressKey) -> str:
    """키 입력 Step 의 표시 이름 (023 FR-059).

    ## 왜 도메인에 있는가

    **녹화 경로와 AI 경로가 같은 문구를 써야 한다.** 각자 만들면 같은 동작이 목록에서
    다르게 불리고, 사용자는 두 Step 이 다른 일을 한다고 읽는다 — 원칙 I 이 금지하는
    「작성 주체가 Step 의 의미를 바꾸는」 상태의 표시 판이다.

    입력 Step 의 이름은 지금 녹화기와 AI 도구가 각자 만들고 있다. 그것을 이번에 고치지는
    않되, **새로 생기는 종류에서 같은 갈래를 만들지는 않는다.**

    ## 어느 키인지가 반드시 들어간다

    「키 입력」만 있으면 목록에서 Enter 와 Escape 를 구별할 수 없고, 그 둘은 정반대
    동작이다 — 021 이 긍정·부정 검증의 이름에 대해 정한 것과 같은 규칙이다.

    대상 요소는 넣지 않는다. 다른 동작 Step 과 같은 방식이며 대상은 상세에서 본다.
    """
    return f"{key.value} 키 입력"
