"""정의 요약 — 에이전트에게 「지금 이 테스트가 무엇인지」를 알려 준다. 016 FR-001~FR-006.

## 이 모듈이 존재하는 이유

작성 에이전트는 지금까지 **지시문 하나만** 받았다. 그래서 "3번부터 다시", "이 구간을
이렇게 바꿔" 같은 말이 원리적으로 성립하지 않았다 — 에이전트가 3번이 무엇인지 모른다.
이 모듈이 그 빈칸을 채운다.

## **값을 거르지 않는다. 새어 나갈 자리를 없앤다** (research R8)

민감값 방어는 이미 두 겹이다 — `SensitiveCapturer` 가 기록 시점에 변수 참조로 바꾸고,
`Scrubber` 가 디스크에 쓰기 직전에 거른다. 요약에 스크러버를 거는 것은 세 번째 겹인데,
**스크러버는 「민감하다고 알려진 값」만 안다.** 사용자가 표시를 깜빡한 사번·주소·전화번호는
그대로 통과한다.

그래서 이 모듈은 **값을 읽는 자리를 `_value_note` 하나로 묶고, 그 함수가 원본을
반환하지 않게 한다.** 「아예 읽지 않는다」가 아니다 — 변수 참조인지 판정하려면 읽어야
한다. 밖으로 나가는 것은 값이 있다는 *사실*과 변수 참조의 *이름*뿐이다.

`tests/unit/test_definition_summary.py` 의 `ALLOWED_VALUE_READS` 가 이 모듈의 `.value`
읽기를 **전수로** 등록해 둔다. 새 읽기가 생기면 검사가 실패하고, 작성자는 그것이 사용자
입력값인지를 그 목록에 적어야 한다.

같은 이유로 `NavigateStep.url` 의 질의 문자열과 조각을 잘라 낸다 — 토큰이 질의 매개변수로
들어오는 것은 흔하고, 요약에 필요한 것은 「어디로 가는가」이지 「어떤 매개변수로」가 아니다.

## 문자열 하나를 돌려준다

중간 구조체를 두지 않는다. 모델에게 가는 것은 결국 텍스트이고, 구조체를 두면 값을 어디서
차단하는지가 두 곳이 된다 — 구조체를 만들 때와 문자열로 펼 때. 차단은 한 곳이어야 한다.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from itb.domain.locator import TargetLocator
from itb.domain.step import (
    AssertionStep,
    DragStep,
    NavigateStep,
    PressStep,
    Step,
    UploadStep,
)

PLAN_BUDGET = 6144
"""작업 계획이 매 턴 차지할 수 있는 바이트 (025 FR-013 · research R6).

**총량을 늘리지 않고 나눈다.** 016 은 16KB 를 정하면서 "그보다 더 키우지 않는다 — 매 턴
붙기 때문이다" 라고 적었고, 그 판단을 뒤집지 않는다. 6KB + 10KB = 16KB 다.

6KB 로 잡은 근거: 항목 40개 × 평균 100바이트 + 제약 열 줄 + 여유. 그보다 긴 계획은
축약이 받는다 — 완료된 항목부터 접고 **생략을 명시한다.**

**확인 필요**: 실제 정제 결과의 항목 길이를 재어 다시 본다. 016 이 8KB 초안을 실측으로
16KB 로 고친 전례가 있고, 잠정값을 실측 없이 두면 「항목 40개까지 괜찮다」가 거짓인 채로
남는다.
"""

DEFAULT_SUMMARY_BUDGET = 16384
"""요약 문자열의 바이트 상한 (016 · T064 에서 **실측으로 정했다**).

**너무 작으면** 평범한 테스트에서 축약이 상시로 일어나 에이전트가 늘 부분만 본다.
**너무 크면** 매 턴의 토큰이 낭비된다 — 요약은 대화마다 다시 붙기 때문이다 (FR-003).

## 실측 (T064)

| 경우 | Step 100개 | 한 줄 |
|---|---|---|
| 짧은 이름 — `동작 12` | 4.6KB | 46바이트 |
| 실제에 가까운 이름 | **13.6KB** | 136바이트 |

(긴 쪽의 예: `주문 관리 화면에서 12번째 항목의 상세 보기 버튼 클릭`)

**초안은 8KB 였고 모자랐다.** 짧은 이름으로만 재면 넉넉해 보이지만, 실제 표시 이름은
요소의 접근가능한 이름에서 파생되므로 서너 배 길다 — 8KB 에서는 긴 이름의 Step 100개가
이미 축약에 걸렸다. 잠정값을 실측 없이 두었다면 「Step 100개까지 괜찮다」는 말이 거짓인
채로 남았을 것이다.

16KB 는 긴 이름 기준 100개에 약 20% 여유다.

**그보다 더 키우지 않는다.** 이 값은 **매 턴** 붙는다 (FR-003) — 16KB 는 대략 4천
토큰이고, 열 차례 주고받으면 요약만 4만 토큰이다. 그 이상이 필요한 테스트는 축약
(FR-006)이 받는다: 교체 구간을 중심으로 남기고 생략을 **명시**하므로, 잘리더라도
에이전트가 「여기 더 있다」를 안다.
"""

VALUE_PRESENT = "값 있음"
"""값이 있다는 **사실**만 알리는 문구.

값을 아예 적지 않으면 에이전트는 빈 칸으로 오해하고 「값을 넣으세요」를 다시 시킨다.
"""

RANGE_MARK = "◀ 교체 구간"

STEP_EDIT_MARK = "◀ 고쳐 달라고 요구받은 Step"
"""026 FR-011 — 016 의 표시와 **뜻이 다르므로 문구도 다르다.**

「교체 구간」은 사용자가 확정하면 사라지는 Step 이고, 이것은 **남아서 고쳐지는** Step
이다. 같은 문구를 쓰면 모델이 016 의 지침(「당신이 지우지 마세요」)을 이쪽에도 적용해
고치기를 주저하거나, 반대로 지워도 되는 것으로 읽는다.
"""

_VARIABLE_REFERENCE = re.compile(r"^\s*\{\{[^{}]+\}\}\s*$")
"""값 **전체**가 변수 참조 하나인 경우만 참조로 본다.

부분 참조(`prefix-{{x}}`)를 참조로 다루면 접두어가 그대로 요약에 실린다 — 그 접두어가
사번일 수 있다. 전체가 참조일 때만 이름을 그대로 보이는 것이 안전한 쪽이다.
"""


def _describe_target(target: TargetLocator | None) -> str:
    """대상을 **읽는 사람이 알아볼 만큼만** 적는다.

    후보 묶음 전체를 적지 않는 이유는 둘이다. 첫째, 길다 — 후보 6종이 Step 마다 붙으면
    요약이 예산을 금방 넘는다. 둘째, 에이전트가 후보를 알 필요가 없다. 에이전트가 대상을
    지목할 때 쓰는 것은 `observe_page` 가 주는 `element_ref` 이지 저장된 후보가 아니다
    (헌법 원칙 IV).
    """
    if target is None:
        return ""
    role = target.role or target.tag or ""
    name = target.accessible_name or ""
    if role and name:
        return f'{role} "{name}"'
    if name:
        return f'"{name}"'
    if role:
        return role
    # 이름도 역할도 없으면 무엇이라도 있어야 사용자가 그 줄을 지목할 수 있다.
    if target.label is not None:
        return f'label "{target.label.value}"'
    if target.test_id is not None:
        return f"testid {target.test_id.value}"
    return "(이름 없는 요소)"


def _safe_url(url: str) -> str:
    """질의 문자열과 조각을 잘라 낸다. 토큰이 거기 실려 오기 때문이다 (R8)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")) or url


def _value_note(step: Step) -> str:
    """값에 대해 **말할 수 있는 것**만 돌려준다.

    `value` 를 읽기는 한다 — 참조인지 판정하려면 읽어야 한다. 읽은 값은 **밖으로 나가지
    않는다**: 참조면 참조 문자열을, 아니면 고정 문구를 돌려준다. 반환 경로에 원본 값이
    실리는 가지가 없다는 것이 이 함수가 작은 이유다.
    """
    raw = getattr(step, "value", None)
    if raw is None:
        return ""
    if _VARIABLE_REFERENCE.match(raw):
        return raw.strip()
    if raw == "":
        return "빈 값"
    return VALUE_PRESENT


def _extra(step: Step) -> str:
    """Step 종류마다 다른 한 조각. **값은 여기로 오지 않는다.**"""
    if isinstance(step, NavigateStep):
        return _safe_url(step.url)
    if isinstance(step, UploadStep):
        # 파일 **이름**이다. 내용은 애초에 기록되지 않는다 (UploadStep 의 설계).
        return step.file_name
    if isinstance(step, AssertionStep):
        kind = step.assertion.kind.value
        note = "" if step.assertion.value is None else VALUE_PRESENT
        return f"{kind} {note}".strip()
    if isinstance(step, DragStep):
        return f"→ {_describe_target(step.drop_target)}"
    if isinstance(step, PressStep):
        # **어느 키인지가 이 Step 의 전부다** (023). 없으면 모델은 요약을 읽고도 Enter 와
        # Escape 를 구별하지 못한다 — 그 둘은 정반대 동작이다.
        return step.key.value
    return _value_note(step)


def _line(index: int, step: Step, in_range: bool, mark: str = RANGE_MARK) -> str:
    """Step 하나를 한 줄로. 순번은 **1부터** — 사용자가 보는 번호와 같아야 한다."""
    target = getattr(step, "target", None)
    cells = [
        f"{index:>3}.",
        step.id,
        step.label,
        step.type.value,
        _describe_target(target),
        _extra(step),
    ]
    if step.tab:
        cells.append(f"tab {step.tab}")
    if in_range:
        cells.append(mark)
    return "  ".join(c for c in cells if c)


def _anchor(steps: list[Step], range_ids: set[str]) -> int:
    """축약할 때 **무엇을 중심으로 남길 것인가**.

    교체 구간이 있으면 그 한가운데다. 없으면 목록의 끝이다 — 새 Step 은 끝에 붙으므로
    (`StepCompiler` 의 기본 동작) 에이전트가 가장 자주 참조하는 곳이 그쪽이다.
    """
    marked = [i for i, s in enumerate(steps) if s.id in range_ids]
    if marked:
        return (marked[0] + marked[-1]) // 2
    return len(steps) - 1


STEPS_BUDGET_WITH_PLAN = DEFAULT_SUMMARY_BUDGET - PLAN_BUDGET
"""**계획이 함께 붙을 때** Step 목록의 몫 (10KB · 025 research R6).

## 기본값이 아니다

`build_definition_summary` 의 기본 예산은 016 이 정한 16KB 그대로다. 계획이 있는 세션에서만
호출자가 이 값을 넘긴다.

**그렇게 가른 이유**: 016 은 실측으로 「긴 이름 기준 Step 100개가 13.6KB」를 확인하고 16KB 를
정했다. 그것을 무조건 10KB 로 줄이면 **계획이 없는 세션에서도** 100개 근처에서 축약이 걸린다 —
016 이 피하려던 상황이 025 와 아무 상관 없는 경로에서 되살아난다.

계획이 있는 세션에서는 Step 목록이 10KB 로 좁아진다. 그 대가를 받아들이는 이유는, 016 의
축약이 **조용히 자르지 않기** 때문이다 — 교체 구간을 중심으로 남기고 생략을 명시하므로
모델이 「여기 더 있다」를 안다. 반면 계획이 없으면 모델은 **무엇을 요구받았는지 자체를
모른다.** 둘 중 하나가 좁아져야 한다면 잘려도 덜 해로운 쪽이 Step 목록이다.

**확인 필요**: 실제 세션에서 어느 쪽이 먼저 축약에 걸리는지 재어 배분을 다시 본다.
"""


def build_definition_summary(
    steps: list[Step],
    range_ids: list[str] | None = None,
    budget: int = DEFAULT_SUMMARY_BUDGET,
    mark: str = RANGE_MARK,
) -> str:
    """에이전트 컨텍스트에 실을 정의 요약을 만든다.

    ``range_ids`` 는 **표시할 Step 의 id** 다. 016 에서는 교체 대상 구간이고, 026 에서는
    사용자가 고쳐 달라고 지목한 Step 하나다 — 두 경로가 **같은 통로**를 쓰므로 경로마다
    AI 가 아는 것이 달라지지 않는다 (016 FR-005 가 세운 규칙).

    ``mark`` 가 그 표시 문구다. 뜻이 다르므로 문구가 달라야 한다 (:data:`STEP_EDIT_MARK`).

    목록에 없는 id 가 와도 **거절하지 않는다** — 요약은 보고이지 검증이 아니고, 대상
    검증은 경계가 한다. 같은 규칙을 두 곳에 두지 않는다.
    """
    marked = set(range_ids or ())

    if not steps:
        return "[지금 테스트]\n(Step 이 없습니다)"

    lines = [_line(i + 1, s, s.id in marked, mark) for i, s in enumerate(steps)]
    head = "[지금 테스트]"
    full = "\n".join([head, *lines])
    if len(full.encode()) <= budget:
        return full

    return _shorten(head, lines, steps, marked, budget)


def _shorten(
    head: str,
    lines: list[str],
    steps: list[Step],
    marked: set[str],
    budget: int,
) -> str:
    """예산에 맞게 줄인다. **조용히 자르지 않는다** (FR-006).

    중심(`_anchor`)에서 바깥으로 넓혀 가며 담고, 담지 못한 구간은 생략 표시로 남긴다.
    생략을 말하지 않으면 에이전트는 목록이 그게 전부라고 믿고, 없는 Step 을 지목하거나
    이미 있는 Step 을 다시 만든다.
    """
    center = _anchor(steps, marked)
    lo = hi = center
    used = len(head.encode()) + len(lines[center].encode()) + 1
    # 생략 표시 두 줄의 자리를 미리 빼 둔다 — 다 담고 나서 자리가 없으면 표시를 못 한다.
    reserve = 80
    chosen = {center}

    while True:
        grew = False
        for nxt in (lo - 1, hi + 1):
            if nxt < 0 or nxt >= len(lines) or nxt in chosen:
                continue
            cost = len(lines[nxt].encode()) + 1
            if used + cost + reserve > budget:
                continue
            used += cost
            chosen.add(nxt)
            lo, hi = min(lo, nxt), max(hi, nxt)
            grew = True
        if not grew:
            break

    out = [head]
    if lo > 0:
        out.append(f"    … (Step 1~{lo} 생략) …")
    out.extend(lines[lo : hi + 1])
    if hi < len(lines) - 1:
        out.append(f"    … (Step {hi + 2}~{len(lines)} 생략) …")
    return "\n".join(out)


# ─── 작업 계획 주입 (025 FR-008~FR-013) ────────────────────────────────────
#
# **여기에 두는 이유는 규칙을 한 곳에 모으기 위해서다.** 016 이 정한 예산·축약·민감값
# 규칙이 이 모듈에 있고, 계획 주입도 같은 규칙을 지켜야 한다. 별도 모듈로 만들면 「생략을
# 명시한다」 같은 판단이 두 곳에 생기고, 한쪽만 고쳐진다.

MARK_DONE = "✓"
MARK_NEXT = "▶"
MARK_SKIPPED = "—"
"""할 일 목록의 표시 (contracts/agent-context.md §1).

`▶` 가 있는 이유: 목록만 주면 모델이 어디서 이어야 하는지를 스스로 판정해야 하고, 그
판정이 「되풀이」와 「건너뜀」이 생기는 자리다. **다음 할 일을 제품이 지목한다.**
"""

PLAN_OMITTED = "    … ({done}개 완료 항목 생략) …"
"""접힌 구간 표시. **조용히 자르지 않는다** (FR-013 · 016 과 같은 규칙)."""


def _constraint_lines(plan: object) -> list[str]:
    """지켜야 할 것. **맨 앞에 온다** — 가장 자주 어겨지고, 앞머리가 가장 잘 읽힌다."""
    constraints = getattr(plan, "constraints", None) or []
    if not constraints:
        return []
    return ["[반드시 지킬 것]", *(f"- {c.text}" for c in constraints)]


def _item_line(item: object, is_next: bool) -> str:
    status = getattr(item, "status", None)
    value = getattr(status, "value", status)
    if value == "done":
        mark = MARK_DONE
    elif value == "skipped":
        mark = MARK_SKIPPED
    elif is_next:
        mark = MARK_NEXT
    else:
        mark = " "
    line = f"{getattr(item, 'order', 0):>3}. {mark} {getattr(item, 'text', '')}"
    reason = getattr(item, "skip_reason", None)
    if value == "skipped" and reason:
        line = f"{line}  (건너뜀: {reason})"
    return line


def build_plan_summary(plan: object | None, budget: int = PLAN_BUDGET) -> str:
    """작업 계획을 매 턴 붙일 문자열로 편다 (025 FR-008·FR-009).

    ## 계획이 없으면 빈 문자열이다

    정제에 실패했거나 사용자가 거절한 세션이 그렇다. 그때 붙는 것은 016 이전과 정확히
    같이 정의 요약뿐이다 (FR-012) — **기존 경로가 그대로 돌아야 한다**는 것이 이 기능의
    경계다.

    ## 축약은 **완료된 항목부터**

    남은 일이 무엇인지가 끝난 일보다 중요하다. 다만 접힌 구간에 완료가 몇 개였는지는
    남긴다 — 「1~6 완료, 생략」. 조용히 사라지면 모델은 그것들을 다시 하려 든다.

    ## 값을 다루지 않는다

    계획의 항목과 제약은 **정제 단계에서 이미 자격 증명이 변수 참조로 바뀐** 문자열이다
    (`refine.py` · FR-010). 여기서 다시 거르지 않는다 — 거르는 곳이 둘이면 어느 쪽이
    기준인지 말할 수 없다 (016 `_keep_mismatch` 와 같은 판단).
    """
    if plan is None or getattr(plan, "empty", True):
        return ""

    items = list(getattr(plan, "items", None) or [])
    next_item = getattr(plan, "next_item", None)
    next_id = getattr(next_item, "id", None)

    head = _constraint_lines(plan)
    lines = [_item_line(i, getattr(i, "id", None) == next_id) for i in items]
    parts = [*head, "", "[할 일]", *lines] if head else ["[할 일]", *lines]
    full = "\n".join(parts).strip()
    if len(full.encode()) <= budget:
        return full

    return _shorten_plan(head, items, lines, next_id, budget)


def _shorten_plan(
    head: list[str],
    items: list[object],
    lines: list[str],
    next_id: object,
    budget: int,
) -> str:
    """예산에 맞게 줄인다. **완료된 앞쪽부터 접고 생략을 명시한다.**

    제약은 접지 않는다 — 그것을 잃으면 이 기능이 고치려는 문제(값을 바꾸고 금지를
    어긴다)가 그대로 돌아온다. 제약만으로 예산을 넘는 계획은 애초에 성립하지 않는
    지시문이고, 그때는 항목이 전부 접힌 채로 나간다.
    """
    kept: list[str] = []
    used = sum(len(line.encode()) + 1 for line in head) + len("[할 일]".encode())
    reserve = 80
    folded = 0

    for index in range(len(lines) - 1, -1, -1):
        cost = len(lines[index].encode()) + 1
        status = getattr(getattr(items[index], "status", None), "value", None)
        if used + cost + reserve > budget and status == "done":
            folded += 1
            continue
        if used + cost + reserve > budget:
            # 미완료를 접어야 할 만큼 좁으면 더 담지 않는다 — 남은 일이 먼저다.
            folded += 1
            continue
        kept.append(lines[index])
        used += cost

    body = list(reversed(kept))
    out = [*head, ""] if head else []
    out.append("[할 일]")
    if folded:
        out.append(PLAN_OMITTED.format(done=folded))
    out.extend(body)
    return "\n".join(out).strip()
