"""지시문 정제 — 거친 글을 작업 계획으로 바꾼다. 025 FR-014~FR-022.

## 사람이 쓰는 지시문은 정제되어 있지 않다

실제 지시문은 이렇게 생겼다.

```
관리자 계정 (아이디/비밀번호)로 로그인한 후 운영 관리 > 메뉴관리로 이동한다.
중요!: 기존 등록된 데이터는 검증으로 사용하지 않는다.

[등록] … 연결 URL은 (주소 A) 값을 입력한다 …
[목록] 관리자 계정 (아이디/비밀번호)로 로그인한 후 운영 관리 > 메뉴관리로 이동한다 …
[수정] … 연결 URL((주소 B))을 변경하고 …
```

같은 전제가 구획마다 반복되고, 전역 제약이 본문 중간에 섞여 있고, 구체값이 자리마다
다르고, 자격 증명이 평문으로 들어 있다.

이 글이 매 턴 다시 실리면 반복된 전제와 산문이 함께 실려 분량이 크고, 정작 「어디까지
했는가」는 어디에도 없다.

## **줄이고 정리하는 일이지 해석하는 일이 아니다** (FR-015·FR-016)

이 모듈에서 가장 위험한 실패는 **구체값을 뭉개는 것**이다. 등록의 연결 주소와 수정의
연결 주소가 다르다면 그 둘은 다른 값으로 남아야 한다 — 「같은 사이트니까 하나로」는 이
테스트를 무의미하게 만든다.

그래서 프롬프트가 「해석하지 말 것」을 반복해 말하고, **사용자가 확인하고 고친 뒤에야**
작성이 시작된다 (FR-018). 확인 없이 진행되는 경로를 만들지 않는다.

## **정제는 관문이 아니다** (FR-020)

실패하면 원문으로 진행한다. 모델이 도구를 부르지 않거나, 부른 인자가 스키마를 통과하지
못하거나, 호출 자체가 실패한 경우 — 셋 다 「정제하지 못했다」 하나로 수렴한다.

정제가 작성을 막는 순간 이 기능은 값이 아니라 비용이 된다.

## 도구 호출로 구조를 강제한다 (research R8)

JSON 을 텍스트로 받아 파싱하면 파싱 실패 처리를 새로 만들어야 하고, 그것은 이미 있는
것의 두 번째 사본이 된다. 이 저장소는 도구 호출로 구조를 강제하는 경로를 이미 갖고 있다.

`response_format` 을 쓰지 않는 이유는 실측이 없기 때문이다 — `llm/client.py` 의 주석은
이 모델에서 **쓸 수 없는 파라미터 목록**을 실측으로 적어 두고 있고, 확인 없이 새
파라미터를 더하지 않는다는 뜻이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from itb.authoring.plan import (
    MAX_PLAN_ITEMS,
    Constraint,
    ConstraintScope,
    PlanItem,
    PlanSource,
    WorkPlan,
)
from itb.llm.client import LlmConfig, LlmUnavailableError, RefusalError, check_stop_reason

SUBMIT_TOOL = "submit_plan"
"""모델이 계획을 제출하는 도구. **이것 하나만 준다.**

다른 도구를 주지 않으므로 모델이 할 수 있는 일이 하나뿐이고, 구조가 스키마로 강제된다.
"""

REFINE_SYSTEM = """\
당신은 사람이 쓴 E2E 테스트 지시문을 **정리하는** 도구입니다.

당신이 하는 일은 **줄이고 정리하는 것**이지 **해석하는 것이 아닙니다.**

## 반드시 지킬 것

- **지시문이 준 구체값을 글자 그대로 남기세요.** 주소·계정·기대 문구·숫자를 바꾸거나
  줄이지 마세요.
- **같은 성격의 값이 자리마다 다르면 각각 남기세요.** 등록의 주소와 수정의 주소가
  다르다면 그것이 이 테스트의 요점입니다. 하나로 합치지 마세요.
- **금지사항을 남기세요.** 「~하지 않는다」, 「~를 쓰지 않는다」 같은 문장은 제약입니다.
- 지시문에 없는 단계를 **만들어 내지 마세요.** 당신이 보기에 빠진 것 같아도 더하지
  않습니다.
- 지시문에 있는 단계를 **빼지 마세요.** 사소해 보여도 사용자가 적은 것입니다.

## 어떻게 나누는가

- **할 일**: 화면을 조작하거나 확인하는 동작 하나. 지시문의 문장 하나 또는 몇 문장이
  한 항목이 됩니다.
- **제약**: 모든 항목에 걸리는 규칙(`global`), 또는 특정 항목에서 써야 할 구체값(`item`).
  「기존 데이터는 검증에 쓰지 않는다」는 전역이고, 「이 칸에 (주소 A) 를 넣는다」는
  그 항목에 걸립니다.

## 반복된 전제는 한 번으로

같은 로그인·화면 이동이 구획마다 반복되면 **첫 번째만** 항목으로 남기세요. 뒤의 것들은
이미 그 상태이므로 다시 하지 않습니다.

## 자격 증명

비밀번호처럼 보이는 값은 **`{{이름}}` 형태의 변수 참조로 바꾸고**, 무엇을 바꿨는지
`notes` 에 적으세요. 아이디·계정명은 그대로 둡니다 — 그것은 어느 계정인지를 말하는
정보이고, 사용자가 확인해야 하는 값입니다.

## 결과

`submit_plan` 도구를 **한 번** 부르세요. 다른 말은 하지 마세요.
"""

_LABELED_PASSWORD = re.compile(
    r"(비밀번호|패스워드|password|pw)\s*[:：/]?\s*([^\s,、/]{4,})", re.IGNORECASE
)
"""「비밀번호: 값」처럼 **이름표가 붙은** 자리."""

_URL_LIKE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")
"""주소처럼 보이는 조각. **자격 증명 판정에서 제외한다.**

이 지시문에는 `연결 URL은 https://mobigen.com` 같은 문장이 실제로 있고, 그것을 치환하면
사용자가 요구한 값이 사라진다 — 이 기능에서 가장 해로운 실패다 (FR-015).
"""

_SLASH_CREDENTIAL = re.compile(
    r"(?:계정|아이디|계정명|로그인|ID)([^/\n]{0,20}?)/\s*([!-~]{6,})"
    r"|(\S{2,})\s*/\s*([!-~]{6,})(?=[^\n]{0,12}(?:로그인|접속))",
    re.IGNORECASE,
)
"""`계정 <아이디> / <비밀번호>` 처럼 **이름표 없이 슬래시로 나열한** 자리.

**2026-09-29 사용자 지시문에서 찾았다.** 실제로 쓰이는 형식이 이것이었고, 이름표만
보던 규칙은 **하나도 잡지 못했다.**

    관리자 계정 platform1 / <비밀번호>로 로그인한 후 …

두 갈래로 본다 — 계정 낱말이 **앞**에 오는 경우와, 「로그인」이 **뒤**에 오는 경우.
실제 지시문은 둘 중 하나로 쓰인다.

**끝의 한글 조사는 남긴다.** 대상을 ASCII 출력 문자(`[!-~]`)로 한정했으므로
`<비밀번호>로` 에서 조사 `로` 는 잡히지 않는다 — 조사까지 치환하면 문장이 깨진다.

**URL 을 잡지 않는다.** `(?<!/)` 가 `https://…` 의 두 번째 슬래시를 막고, 뒤쪽 갈래는
「로그인」이 가까이 있을 때만 본다. `연결 URL은 https://mobigen.com` 같은 문장이 이
지시문에 실제로 있으므로, 그것을 잡으면 사용자가 요구한 값이 사라진다 — **이 기능에서
가장 해로운 실패**다 (FR-015).
"""

_PASSWORD_PATTERNS = (_LABELED_PASSWORD, _SLASH_CREDENTIAL)
"""지시문에서 자격 증명으로 보이는 자리 (FR-010 · research R10).

**모델의 치환을 믿고 끝내지 않는다.** 모델이 규칙을 어겼을 때 막을 것이 없으면 평문이
매 턴 다시 실린다 — `report_blocked` 가 종류에 따라 질문을 버리는 것과 같은 판단이다
(지침에만 적어 두지 않고 제품이 한 번 더 본다).

**완벽하지 않다.** 기존 포착기는 입력 필드의 유형(password)을 근거로 판정하는데 지시문에는
그런 근거가 없다. 하한은 **지금보다 나빠지지 않는 것**이고, 못 잡은 것이 그대로 실리는
것은 025 이전과 같은 수준이다.

그러나 **실제로 쓰이는 형식은 잡아야 한다.** 초안은 이름표(`비밀번호:`)만 보았고, 사용자의
실제 지시문은 슬래시 나열이라 하나도 잡지 못했다. 새 형식을 만나면 여기 더한다.
"""

SUBMIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "maxItems": MAX_PLAN_ITEMS,
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        "constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "scope": {"type": "string", "enum": ["global", "item"]},
                    "item_index": {"type": "integer", "minimum": 1},
                },
                "required": ["text"],
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["items"],
}
"""제출 스키마.

**항목을 `item_index`(1부터)로 가리킨다.** 모델에게 id 를 만들게 하면 중복과 오타가
생기고, 그것을 검증하는 코드가 또 필요해진다. 순번은 모델이 이미 알고 있는 값이다.
"""


@dataclass(slots=True)
class RefineResult:
    """정제 결과. **실패도 결과다** (FR-020).

    예외로 올리지 않는 이유는 실패가 예외적인 사건이 아니기 때문이다 — 원문으로 진행하는
    것이 정상 경로의 하나다.
    """

    refined: bool
    plan: WorkPlan | None = None
    notes: list[str] = field(default_factory=list)


def _scrub_credentials(text: str) -> tuple[str, list[str]]:
    """평문 자격 증명을 변수 참조로 바꾼다 (FR-010).

    바꾼 사실을 함께 돌려준다 — **사용자가 확인할 때 무엇이 바뀌었는지 보여야** 한다.
    조용히 바꾸면 사용자는 자기가 적은 값이 쓰이는 줄 안다.
    """
    notes: list[str] = []
    out = text

    def replace_labeled(match: re.Match[str]) -> str:
        label = match.group(1)
        notes.append(f"「{label}」 값을 변수 참조로 바꿨습니다.")
        return f"{label}: {{{{password}}}}"

    def replace_slash(match: re.Match[str]) -> str:
        # 어느 갈래가 맞았는지에 따라 잡힌 조각이 다르다. **원문의 앞부분은 그대로
        # 두고 비밀번호 자리만 바꾼다** — 계정명은 어느 계정인지를 말하는 정보이고,
        # 사용자가 확인해야 하는 값이다.
        whole = match.group(0)
        secret = match.group(2) or match.group(4)
        if not secret:  # pragma: no cover - 두 갈래 중 하나는 반드시 맞는다
            return whole
        notes.append("계정 표기의 비밀번호를 변수 참조로 바꿨습니다.")
        return whole.replace(secret, "{{password}}")

    out = _LABELED_PASSWORD.sub(replace_labeled, out)

    # **주소를 먼저 빼 둔다.** 정규식에 부정 전방탐색을 겹치는 대신 이렇게 하는 이유는
    # 읽을 수 있기 때문이다 — 「주소는 건드리지 않는다」가 규칙이고, 그 규칙이 정규식
    # 안에 숨으면 다음 사람이 왜 그런지 알 수 없다.
    #
    # 자리표시자에 공백이 없으므로 아래 패턴의 `\S{2,}` 갈래에 걸릴 수 있지만, 그
    # 갈래는 뒤에 「로그인」이 가까이 있을 때만 맞고 자리표시자에는 슬래시가 없다.
    urls: list[str] = []

    def stash(match: re.Match[str]) -> str:
        urls.append(match.group(0))
        return f"\x00URL{len(urls) - 1}\x00"

    out = _URL_LIKE.sub(stash, out)
    out = _SLASH_CREDENTIAL.sub(replace_slash, out)
    for index, url in enumerate(urls):
        out = out.replace(f"\x00URL{index}\x00", url)
    return out, notes


def _plan_from_payload(payload: dict[str, Any]) -> WorkPlan:
    """모델이 제출한 것을 계획으로 옮긴다.

    **여기서 한 번 더 자격 증명을 본다.** 모델이 규칙을 어겼을 때 막을 것이 없으면
    평문이 매 턴 다시 실린다.
    """
    items: list[PlanItem] = []
    extra_notes: list[str] = []
    for index, raw in enumerate(payload.get("items") or [], start=1):
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        cleaned, notes = _scrub_credentials(text)
        extra_notes.extend(notes)
        items.append(PlanItem(id=f"i{index}", order=index, text=cleaned))

    constraints: list[Constraint] = []
    for raw in payload.get("constraints") or []:
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        cleaned, notes = _scrub_credentials(text)
        extra_notes.extend(notes)
        scope = ConstraintScope(str(raw.get("scope") or "global"))
        item_id: str | None = None
        if scope is ConstraintScope.ITEM:
            index = raw.get("item_index")
            # 없는 항목을 가리키면 **전역으로 떨어뜨린다.** 버리지 않는 이유는 제약을
            # 잃는 것이 이 기능에서 가장 해로운 실패이기 때문이다 — 어느 항목인지
            # 몰라도 「어기면 안 되는 것」이라는 사실은 남는다.
            if isinstance(index, int) and 1 <= index <= len(items):
                item_id = items[index - 1].id
            else:
                scope = ConstraintScope.GLOBAL
        constraints.append(Constraint(text=cleaned, scope=scope, item_id=item_id))

    plan = WorkPlan(items=items, constraints=constraints, source=PlanSource.REFINED)
    plan.renumber()
    return plan


async def refine_instruction(
    instruction: str, config: LlmConfig | None = None
) -> RefineResult:
    """지시문을 작업 계획으로 정제한다 (FR-014).

    **실패는 예외가 아니다.** 어떤 이유로 실패하든 `refined=False` 로 돌아오고, 호출자는
    원문으로 진행한다 (FR-020).

    **작성 시점에만 불린다.** 저장된 테스트의 실행 경로에서 이 함수에 닿을 수 없다 —
    `.importlinter` 의 `execution-no-llm` 계약이 그것을 구조로 막는다 (헌법 원칙 II).
    """
    text = (instruction or "").strip()
    if not text:
        return RefineResult(refined=False, notes=["지시문이 비어 있습니다."])

    try:
        # **비동기 도구여야 한다** (2026-09-29 사용자 보고).
        #
        # 동기 `beta_tool` 로 만든 도구를 `AsyncAnthropic` 의 tool_runner 에 넘기면
        # 요청 본문을 만들 때 터진다:
        #
        #     TypeError: Object of type BetaFunctionTool is not JSON serializable
        #
        # 이 저장소의 작성 도구가 전부 `beta_async_tool` 인 것과 같은 이유다
        # (`tools.build_tools`). 클라이언트가 비동기면 도구도 비동기여야 한다.
        from anthropic import beta_async_tool  # noqa: PLC0415 - SDK 경계를 이 함수 안에

        from itb.llm.client import create_client  # noqa: PLC0415
    except ImportError:
        return RefineResult(refined=False, notes=["정제를 준비할 수 없습니다."])

    submitted: dict[str, Any] = {}

    @beta_async_tool(name=SUBMIT_TOOL, input_schema=SUBMIT_SCHEMA)
    async def submit_plan(**payload: Any) -> str:
        submitted.update(payload)
        return "접수했습니다."

    try:
        client = create_client()
        runner = client.beta.messages.tool_runner(
            messages=[{"role": "user", "content": text}],
            tools=[submit_plan],
            system=REFINE_SYSTEM,
            # 한 번 부르고 끝난다. 상한을 낮게 두는 것이 「도구를 부르지 않고 계속
            # 말하는」 경우의 방어선이다 (`agent.py` 의 `max_iterations` 와 같은 판단).
            max_iterations=3,
            **(config or LlmConfig()).request_kwargs(),
        )
        async for message in runner:
            check_stop_reason(getattr(message, "stop_reason", None))
    except (LlmUnavailableError, RefusalError) as exc:
        return RefineResult(refined=False, notes=[str(exc)])
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 원문 진행으로 수렴한다
        return RefineResult(
            refined=False,
            notes=[f"지시문을 정제하지 못했습니다: {type(exc).__name__}"],
        )

    if not submitted.get("items"):
        return RefineResult(
            refined=False, notes=["지시문을 정제하지 못했습니다. 원문으로 진행합니다."]
        )

    plan = _plan_from_payload(submitted)
    if plan.empty:
        return RefineResult(
            refined=False, notes=["정제 결과가 비어 있습니다. 원문으로 진행합니다."]
        )

    notes = [str(n) for n in (submitted.get("notes") or [])]
    # 제품이 바꾼 것도 함께 알린다 — 모델이 말하지 않은 치환이 있을 수 있다.
    _, product_notes = _scrub_credentials(text)
    seen = set(notes)
    notes.extend(n for n in product_notes if n not in seen)
    return RefineResult(refined=True, plan=plan, notes=notes)
