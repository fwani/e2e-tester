"""그룹 이름 ↔ 시트 이름 (기능 014 · FR-008 · research R6).

엑셀은 시트 이름에 규칙을 건다 — 31자 이내, ``: \\ / ? * [ ]`` 금지, 양 끝 작은따옴표 금지,
``History`` 예약. 우리 그룹 이름은 100자까지 어떤 글자든 받으므로 변환이 필요하다.

**변환이 일어나면 사용자에게 알린다** (FR-008). 조용히 바꾸면 사용자는 자기가 쓴 그룹 이름을
파일에서 찾지 못한다.

시트 이름은 그룹 **이름**만 담는다. 접두어는 각 행의 TC ID 에 실린다 — 시트 이름을
``USER 사용자관리`` 처럼 만들면 왕복은 쉬워지지만, 남이 쓰던 설계서에 우리 내부 접두어를
강요하게 된다. 이 기능의 목적은 남의 설계서를 받는 것이다.

이 모듈은 순수 함수만 담는다. openpyxl 을 임포트하지 않으므로 테스트가 파일 없이 돈다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from itb.portability.limits import MAX_SHEET_NAME_CHARS

UNGROUPED_SHEET_NAME = "그룹 없음"
"""그룹 없는 테스트를 담는 시트의 이름.

화면에서 이미 쓰는 말이다 (`TestGroupBar.tsx`). 같은 것을 두 이름으로 부르지 않는다.
"""

_FORBIDDEN = re.compile(r"[:\\/?*\[\]]")
"""엑셀이 시트 이름에 허용하지 않는 문자."""

_RESERVED_LOWER = {"history"}
"""엑셀이 예약한 시트 이름 (대소문자 무관)."""


@dataclass(frozen=True, slots=True)
class SheetRename:
    """그룹 이름이 시트 이름으로 바뀌었다는 기록."""

    group_name: str
    sheet_name: str
    reason: str
    """``forbidden_char`` · ``too_long`` · ``empty`` · ``reserved`` · ``collision``"""


def sanitize(name: str) -> tuple[str, str | None]:
    """그룹 이름 하나를 시트 이름으로 만든다.

    돌려주는 둘째 값은 바뀐 이유이며, 바뀌지 않았으면 ``None`` 이다.
    충돌 회피는 :func:`assign` 이 맡는다 — 여기서는 이름 하나만 본다.
    """
    reason: str | None = None
    result = name

    if _FORBIDDEN.search(result):
        result = _FORBIDDEN.sub("_", result)
        reason = "forbidden_char"

    # 엑셀은 양 끝의 작은따옴표를 거부한다.
    stripped = result.strip("'")
    if stripped != result:
        result = stripped
        reason = reason or "forbidden_char"

    if len(result) > MAX_SHEET_NAME_CHARS:
        result = result[:MAX_SHEET_NAME_CHARS]
        reason = reason or "too_long"

    result = result.strip()
    if not result:
        result = "시트"
        reason = "empty"

    if result.lower() in _RESERVED_LOWER:
        result = f"{result}_"
        reason = reason or "reserved"

    return result, reason


def assign(names: list[str]) -> tuple[list[str], list[SheetRename]]:
    """그룹 이름들에 서로 겹치지 않는 시트 이름을 준다 (FR-008).

    순서를 유지한다. 겹치면 뒤에 ``~2``, ``~3`` … 을 붙이되, 31자를 넘지 않도록 **앞을**
    자른다 — 접미를 자르면 겹침이 되살아나므로 자를 수 있는 것은 앞부분뿐이다.

    대조는 대소문자를 무시한다. 엑셀은 ``Sheet`` 와 ``sheet`` 를 같은 이름으로 본다.
    """
    assigned: list[str] = []
    renames: list[SheetRename] = []
    used: set[str] = set()

    for original in names:
        base, reason = sanitize(original)
        candidate = base
        suffix = 1
        while candidate.lower() in used:
            suffix += 1
            tail = f"~{suffix}"
            head_len = MAX_SHEET_NAME_CHARS - len(tail)
            candidate = f"{base[:head_len]}{tail}"
            reason = "collision"

        used.add(candidate.lower())
        assigned.append(candidate)
        if candidate != original:
            renames.append(
                SheetRename(
                    group_name=original,
                    sheet_name=candidate,
                    reason=reason or "collision",
                )
            )

    return assigned, renames
