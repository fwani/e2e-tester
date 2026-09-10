"""워크북의 7개 컬럼 — 내보내기와 가져오기의 단일 출처 (기능 014 · FR-003·FR-017).

**두 방향이 같은 정의를 본다.** 내보내기가 쓰는 머리글과 가져오기가 찾는 머리글이 따로
있으면, 우리가 내보낸 파일을 우리가 못 읽는 날이 온다.

컬럼 순서는 고정이다 (FR-003). 사용자가 설계서에서 열을 옮겨 두었을 수 있으므로, 가져오기는
**위치가 아니라 머리글 이름으로** 찾는다 (FR-017).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class Column(StrEnum):
    """컬럼 하나. 값이 곧 머리글 텍스트다."""

    TC_ID = "TC ID"
    NAME = "대상기능"
    DESCRIPTION = "테스트항목"
    ACTOR = "수행자"
    PROCEDURE = "수행 절차"
    EXPECTATION = "기대 결과"
    OUTCOME = "결과"


ORDER: tuple[Column, ...] = (
    Column.TC_ID,
    Column.NAME,
    Column.DESCRIPTION,
    Column.ACTOR,
    Column.PROCEDURE,
    Column.EXPECTATION,
    Column.OUTCOME,
)
"""머리글 행에 나가는 순서. **고정이다** (FR-003)."""

REQUIRED: frozenset[Column] = frozenset({Column.TC_ID, Column.NAME})
"""이 둘을 찾지 못한 시트는 통째로 건너뛴다 (FR-017).

`TC ID` 없이는 그룹 접두어를 읽을 수 없고, `대상기능` 없이는 초안의 제목이 없다. 나머지
다섯은 비어 있어도 초안이 성립한다.
"""

ALIASES: dict[Column, frozenset[str]] = {
    Column.TC_ID: frozenset({"tc id", "tcid", "tc_id", "테스트 id", "id"}),
    Column.NAME: frozenset({"대상기능", "대상 기능", "제목", "테스트명", "기능"}),
    Column.DESCRIPTION: frozenset({"테스트항목", "테스트 항목", "설명", "description"}),
    Column.ACTOR: frozenset({"수행자", "수행 자", "actor", "역할"}),
    Column.PROCEDURE: frozenset({"수행 절차", "수행절차", "테스트 스텝", "절차"}),
    Column.EXPECTATION: frozenset({"기대 결과", "기대결과", "검증 스텝", "예상 결과"}),
    Column.OUTCOME: frozenset({"결과", "result", "p/f", "pass/fail"}),
}
"""머리글로 인정하는 표기들 (정규화된 형태).

사람이 쓴 설계서의 머리글은 우리가 내보낸 것과 정확히 같지 않다 — 「대상 기능」에 공백이
있거나 「TC_ID」로 적혀 있다. **넉넉히 받되 만들어내지는 않는다**: 목록에 없는 머리글은
그 컬럼이 아니라고 판단하고, 비슷해 보인다고 추측하지 않는다.
"""


def normalize_header(raw: object) -> str:
    """머리글 셀 값을 대조용 형태로 만든다.

    앞뒤 공백을 떼고 대소문자를 무시한다 (FR-017). 유니코드는 NFC 로 정규화한다 — 한글이
    자모 분리(NFD)된 채 들어오는 파일이 있고, 그러면 눈으로 같은 글자가 대조에 실패한다.
    가운데 연속 공백은 하나로 줄인다.
    """
    if raw is None:
        return ""
    text = unicodedata.normalize("NFC", str(raw)).strip().lower()
    return " ".join(text.split())


@dataclass(frozen=True, slots=True)
class HeaderMap:
    """한 시트의 머리글 → 열 번호 (0부터).

    :attr:`missing_required` 가 비어 있지 않으면 그 시트는 건너뛴다.
    """

    index: dict[Column, int]
    missing_required: frozenset[Column]

    @property
    def usable(self) -> bool:
        return not self.missing_required

    def value(self, row: list[object], column: Column) -> object | None:
        """행에서 그 컬럼의 값을 꺼낸다. 없는 컬럼이거나 행이 짧으면 ``None``."""
        pos = self.index.get(column)
        if pos is None or pos >= len(row):
            return None
        return row[pos]


def header_labels(header_row: list[object]) -> list[str]:
    """머리글 행을 사람이 고를 수 있는 목록으로 만든다 (FR-020f).

    사용자가 컬럼을 짝지으려면 **그 시트에 어떤 열이 있는지** 봐야 한다. 빈 칸은 자리를
    지키되 이름이 없으므로 ``"(N번째 열)"`` 로 부른다 — 위치를 잃으면 짝지을 수 없다.
    """
    labels: list[str] = []
    for pos, cell in enumerate(header_row):
        text = "" if cell is None else str(cell).strip()
        labels.append(text or f"({pos + 1}번째 열)")
    return labels


def map_headers(
    header_row: list[object],
    *,
    overrides: dict[Column, int] | None = None,
) -> HeaderMap:
    """머리글 행을 읽어 컬럼 위치를 정한다.

    **먼저 나온 것이 이긴다.** 같은 컬럼으로 해석되는 머리글이 둘이면 왼쪽을 쓴다 — 어느
    쪽인지 정하지 않으면 파일마다 결과가 달라진다.

    `overrides` 는 사용자가 미리보기에서 직접 짝지은 것이며 **자동 판정을 이긴다**
    (FR-020e). 별칭 목록은 우리가 아는 표기만 담고 있어서, 사용자가 화면에서 보고 있는
    열을 우리가 못 알아보는 경우가 반드시 생긴다. 그때 시트를 통째로 버리는 대신
    사람이 짝지을 수 있어야 한다.
    """
    index: dict[Column, int] = {}
    for pos, cell in enumerate(header_row):
        key = normalize_header(cell)
        if not key:
            continue
        for column in ORDER:
            if column in index:
                continue
            if key == normalize_header(column.value) or key in ALIASES[column]:
                index[column] = pos
                break

    if overrides:
        # 사용자가 정한 것이 이긴다. 같은 열을 두 컬럼에 겹쳐 주는 것은 호출자가
        # 확정 전에 거절한다 (FR-020h) — 여기서는 정해진 것을 그대로 반영한다.
        for column, pos in overrides.items():
            if pos < 0:
                index.pop(column, None)  # 「쓰지 않음」
                continue
            index[column] = pos

    return HeaderMap(
        index=index,
        missing_required=frozenset(c for c in REQUIRED if c not in index),
    )


def conflicting_overrides(overrides: dict[Column, int]) -> list[int]:
    """두 컬럼이 같은 열을 가리키는 경우의 열 번호들 (FR-020h).

    겹치면 한 열의 값이 두 자리에 들어가고, 사용자는 자기가 무엇을 지정했는지 화면에서
    확인할 수 없다. 확정 전에 거절한다.
    """
    seen: dict[int, int] = {}
    for pos in overrides.values():
        if pos < 0:
            continue
        seen[pos] = seen.get(pos, 0) + 1
    return sorted(pos for pos, n in seen.items() if n > 1)
