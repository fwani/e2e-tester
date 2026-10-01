"""028 — 그룹 접두어 규칙과 식별자 읽기.

028 이 접두어에 하이픈을 허용한다 (`IT-PM`). 규칙만 넓히면 끝나는 일이 아니다 —
식별자에서 접두어를 뽑는 코드가 전부 **앞에서** 자르고 있어서 `IT-PM-001` 의 접두어를
`IT` 로 읽는다. 이 파일이 지키는 것은 둘이다.

1. **규칙이 옛 규칙의 상위집합이다.** 저장된 자산에 손대지 않는 근거가 이것뿐이다
   (spec FR-011 · research R7-1). 이 단언이 깨지면 마이그레이션 없이 넘어간 결정 전체가
   무너진다.
2. **읽는 법이 한 곳에 있고, 옛 식별자에서 옛 결과와 같다** (FR-008 · R7-2).

**접두어의 각 마디가 영문으로 시작한다**는 규칙이 이 설계의 핵심이다 (FR-001). 그래서
접두어 안에 숫자만의 마디가 올 수 없고, 식별자의 접두어·번호 경계가 모호해지지 않는다
(FR-004) — `A-001-001` 같은 값이 애초에 만들어질 수 없다.
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from itb.domain.test_case import (
    GROUP_PREFIX_MAX_LENGTH,
    GROUP_PREFIX_PATTERN,
    TEST_ID_PATTERN,
    TestGroup,
    id_from_filename,
    number_of,
    prefix_of,
)

PREFIX_RE = re.compile(GROUP_PREFIX_PATTERN)
TEST_ID_RE = re.compile(TEST_ID_PATTERN)

OLD_PREFIX_PATTERN = r"^[A-Z][A-Z0-9]{0,7}$"
"""028 이전의 규칙. **여기 적어 두는 것이 상위집합 단언의 근거다.**"""


def prefix_ok(value: str) -> bool:
    """규칙 전체 — 패턴과 길이를 함께 본다.

    길이가 패턴 밖에 있는 이유는 Pydantic 의 `pattern` 이 Rust regex 로 컴파일되어
    선읽기를 쓸 수 없기 때문이다 (research R1). 그래서 검증도 두 조각을 함께 봐야 한다.
    """
    return PREFIX_RE.match(value) is not None and len(value) <= GROUP_PREFIX_MAX_LENGTH


# ─── 규칙 (FR-001 ~ FR-005) ─────────────────────────────────────────────────


@pytest.mark.parametrize("prefix", ["IT-PM", "IT-DM", "A-B-C", "IT-PM2", "X1-Y2"])
def test_hyphenated_prefix_is_allowed(prefix: str) -> None:
    """사용자가 문서에서 쓰던 식별 체계를 그대로 옮길 수 있어야 한다 (FR-001)."""
    assert prefix_ok(prefix)


@pytest.mark.parametrize(
    ("prefix", "why"),
    [
        ("IT-", "하이픈으로 끝난다"),
        ("-PM", "하이픈으로 시작한다"),
        ("IT--PM", "하이픈이 연달아 온다"),
        ("it-pm", "소문자다"),
        ("IT_PM", "밑줄은 마디 구분자가 아니다"),
        ("IT PM", "공백"),
        ("1T", "첫 글자가 숫자다"),
        ("IT-001", "숫자만의 마디 — 식별자의 번호와 구분되지 않는다"),
        ("A-001-B", "가운데가 숫자만의 마디"),
        ("IT-PM-DMX-YZW", "13자 — 상한을 넘는다"),
    ],
)
def test_bad_prefix_is_rejected(prefix: str, why: str) -> None:
    assert not prefix_ok(prefix), why


def test_prefix_length_limit_is_twelve() -> None:
    """식별자가 파일 이름에 들어가므로 무한정 늘릴 수 없다 (FR-003)."""
    assert GROUP_PREFIX_MAX_LENGTH == 12
    assert prefix_ok("A" * 12)
    assert not prefix_ok("A" * 13)


@pytest.mark.parametrize(
    "old",
    ["A", "TC", "USER", "DATA9", "Z0000000", "AB12CD34", "X", "Q7"],
)
def test_new_rule_is_a_superset_of_the_old_one(old: str) -> None:
    """**마이그레이션이 없는 이유가 이것이다** (FR-011 · R7-1).

    옛 규칙을 만족하던 값이 하나라도 새 규칙에서 떨어지면, 저장된 프로젝트가 열리지
    않는다. 그 순간 「변환 단계를 두지 않는다」는 결정이 사고가 된다.
    """
    assert re.match(OLD_PREFIX_PATTERN, old), "표본이 옛 규칙을 만족해야 한다"
    assert prefix_ok(old)


def test_reserved_prefix_is_still_rejected_by_the_model() -> None:
    """`TC` 는 그룹 없는 테스트가 쓴다 (FR-005).

    패턴 자체는 `TC` 를 통과시킨다 — 예약 판정은 라우트가 한다. 여기서는 패턴이
    그것을 막지 **않는다**는 사실을 고정한다. 옛 테스트 식별자가 전부 `TC-###` 이고
    그것들이 읽혀야 하기 때문이다.
    """
    assert prefix_ok("TC")


def test_group_model_enforces_the_rule() -> None:
    """경계에서 검증된다 (헌법 §보안 — 모든 외부 입력은 경계에서)."""
    assert TestGroup(prefix="IT-PM", name="프로젝트 관리").prefix == "IT-PM"
    for bad in ["IT-", "IT--PM", "it-pm", "IT-001", "A" * 13]:
        with pytest.raises(ValidationError):
            TestGroup(prefix=bad, name="아무개")


# ─── 식별자 (FR-008) ────────────────────────────────────────────────────────


@pytest.mark.parametrize("test_id", ["TC-001", "USER-001", "IT-PM-001", "IT-PM-DM-999"])
def test_test_id_pattern_accepts(test_id: str) -> None:
    assert TEST_ID_RE.match(test_id)


@pytest.mark.parametrize("bad", ["IT-PM-1", "IT-PM-0001", "IT-PM", "001", "IT--PM-001"])
def test_test_id_pattern_rejects(bad: str) -> None:
    assert not TEST_ID_RE.match(bad)


# ─── 읽기 함수 (FR-008 ~ FR-010) ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("test_id", "prefix", "number"),
    [
        ("TC-014", "TC", 14),
        ("USER-001", "USER", 1),
        ("IT-PM-001", "IT-PM", 1),
        ("IT-PM-DM-999", "IT-PM-DM", 999),
    ],
)
def test_reading_splits_at_the_last_hyphen(test_id: str, prefix: str, number: int) -> None:
    """**경계는 마지막 하이픈이다** (FR-008)."""
    assert prefix_of(test_id) == prefix
    assert number_of(test_id) == number


@pytest.mark.parametrize("old_id", ["TC-001", "TC-999", "USER-001", "DATA9-042"])
def test_reading_matches_the_old_behaviour_for_old_ids(old_id: str) -> None:
    """옛 식별자에서 옛 `split("-", 1)` 과 **같은 값**을 낸다 (R7-2).

    하이픈이 하나뿐인 식별자에서는 앞에서 자르나 뒤에서 자르나 결과가 같다. 그것이
    옛 자산을 건드리지 않아도 되는 두 번째 근거다.
    """
    assert prefix_of(old_id) == old_id.split("-", 1)[0]
    assert number_of(old_id) == int(old_id.split("-", 1)[1])


@pytest.mark.parametrize("bad", ["", "TC", "TC-1", "tc-001", "TC-001-", "-001"])
def test_reading_raises_on_malformed_ids(bad: str) -> None:
    """**조용히 답하지 않는다.**

    옛 `split("-", 1)[0]` 은 하이픈이 없는 문자열을 통째로 접두어라고 답했다. 그래서
    잘못된 값이 그룹 집계에 섞여도 드러나지 않았다.
    """
    with pytest.raises(ValueError, match="식별자"):
        prefix_of(bad)
    with pytest.raises(ValueError, match="식별자"):
        number_of(bad)


# ─── 파일 이름 (FR-010) ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("filename", "test_id"),
    [
        ("USER-001-로그인.yaml", "USER-001"),
        ("TC-999-a.yaml", "TC-999"),
        ("IT-PM-001-로그인.yaml", "IT-PM-001"),
        ("IT-PM-DM-003-x.yaml", "IT-PM-DM-003"),
    ],
)
def test_filename_reading(filename: str, test_id: str) -> None:
    assert id_from_filename(filename) == test_id


@pytest.mark.parametrize(
    ("filename", "test_id"),
    [
        ("IT-PM-001-단계-002-확인.yaml", "IT-PM-001"),
        ("IT-PM-001-ABC-002.yaml", "IT-PM-001"),
        ("IT-001-ABC-002.yaml", "IT-001"),
    ],
)
def test_filename_reading_is_not_fooled_by_the_name_part(filename: str, test_id: str) -> None:
    """**이름 부분에도 하이픈과 숫자가 들어간다** (R4).

    접두어를 욕심내어 길게 읽으면 `IT-PM-001-ABC-002` 를 식별자로 삼는다. 접두어의 모든
    마디가 영문으로 시작하므로, 왼쪽에서 처음 만나는 「하이픈 + 3자리」가 언제나 진짜
    번호다 — 최소 일치가 안전한 이유가 그것이다.
    """
    assert id_from_filename(filename) == test_id


@pytest.mark.parametrize(
    "filename",
    ["README.md", "USER-001.yaml", "user-001-a.yaml", "USER-1-a.yaml", ".gitignore"],
)
def test_filename_reading_returns_none_for_non_test_files(filename: str) -> None:
    """테스트 디렉터리에는 정의 파일이 아닌 것도 있다. 예외가 아니라 `None` 이다 —
    「이 파일은 테스트가 아니다」는 오류가 아니라 판정이기 때문이다."""
    assert id_from_filename(filename) is None
