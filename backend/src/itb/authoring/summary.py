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
    Step,
    UploadStep,
)

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
    return _value_note(step)


def _line(index: int, step: Step, in_range: bool) -> str:
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
        cells.append(RANGE_MARK)
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


def build_definition_summary(
    steps: list[Step],
    range_ids: list[str] | None = None,
    budget: int = DEFAULT_SUMMARY_BUDGET,
) -> str:
    """에이전트 컨텍스트에 실을 정의 요약을 만든다.

    ``range_ids`` 는 교체 대상 구간의 Step id 다 (016 의 구간 재녹화). 목록에 없는 id 가
    와도 **거절하지 않는다** — 요약은 보고이지 검증이 아니고, 구간 검증은 경계
    (`itb.authoring.rerecord.validate_range`)가 한다. 같은 규칙을 두 곳에 두지 않는다.
    """
    marked = set(range_ids or ())

    if not steps:
        return "[지금 테스트]\n(Step 이 없습니다)"

    lines = [_line(i + 1, s, s.id in marked) for i, s in enumerate(steps)]
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
