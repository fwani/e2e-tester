"""그룹 이름 → 시트 이름 변환 (014 T021 · FR-008 · research R6)."""

from __future__ import annotations

from itb.portability.limits import MAX_SHEET_NAME_CHARS
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME, assign, sanitize


class SanitizeTests:
    def test_평범한_이름은_그대로다(self) -> None:
        assert sanitize("사용자관리") == ("사용자관리", None)

    def test_금지문자를_밑줄로_바꾼다(self) -> None:
        name, reason = sanitize("사용자/권한:관리")
        assert name == "사용자_권한_관리"
        assert reason == "forbidden_char"

    def test_금지문자_여섯가지를_모두_바꾼다(self) -> None:
        name, _ = sanitize(r"a:b\c/d?e*f[g]h")
        assert name == "a_b_c_d_e_f_g_h"

    def test_양끝_작은따옴표를_뗀다(self) -> None:
        # 엑셀이 양 끝의 작은따옴표를 거부한다.
        name, reason = sanitize("'회원'")
        assert name == "회원"
        assert reason == "forbidden_char"

    def test_31자를_넘으면_자른다(self) -> None:
        name, reason = sanitize("가" * 40)
        assert len(name) == MAX_SHEET_NAME_CHARS
        assert reason == "too_long"

    def test_빈_이름은_대체된다(self) -> None:
        assert sanitize("   ") == ("시트", "empty")

    def test_금지문자만_있으면_빈_이름이_되지_않는다(self) -> None:
        name, _ = sanitize("///")
        # 밑줄로 바뀌므로 빈 문자열이 아니다 — 대체 이름으로 떨어지지 않는다.
        assert name == "___"

    def test_예약어는_뒤에_밑줄을_붙인다(self) -> None:
        assert sanitize("History")[0] == "History_"

    def test_예약어_판정은_대소문자를_무시한다(self) -> None:
        assert sanitize("history")[0] == "history_"


class AssignTests:
    def test_순서를_유지한다(self) -> None:
        names, _ = assign(["다", "가", "나"])
        assert names == ["다", "가", "나"]

    def test_겹치면_접미를_붙인다(self) -> None:
        names, renames = assign(["회원", "회원"])
        assert names == ["회원", "회원~2"]
        assert [r.reason for r in renames] == ["collision"]

    def test_셋_이상_겹쳐도_각각_다르다(self) -> None:
        names, _ = assign(["x", "x", "x", "x"])
        assert names == ["x", "x~2", "x~3", "x~4"]
        assert len(set(names)) == 4

    def test_겹침_대조는_대소문자를_무시한다(self) -> None:
        # 엑셀은 Sheet 와 sheet 를 같은 이름으로 본다.
        names, _ = assign(["Sheet", "sheet"])
        assert names[0] != names[1]
        assert names[1] == "sheet~2"

    def test_잘린_이름이_겹쳐도_구분된다(self) -> None:
        long_a = "가" * 40
        names, _ = assign([long_a, long_a])
        assert names[0] != names[1]
        assert all(len(n) <= MAX_SHEET_NAME_CHARS for n in names)

    def test_충돌_접미가_31자를_넘지_않는다(self) -> None:
        # 접미를 자르면 겹침이 되살아나므로 앞을 자른다.
        names, _ = assign(["나" * 31] * 3)
        assert all(len(n) <= MAX_SHEET_NAME_CHARS for n in names)
        assert names[1].endswith("~2")
        assert names[2].endswith("~3")

    def test_바뀐_것만_기록에_남는다(self) -> None:
        _, renames = assign(["정상", "사용자/권한"])
        assert [r.group_name for r in renames] == ["사용자/권한"]

    def test_그룹없음_시트_이름은_그대로_통과한다(self) -> None:
        names, renames = assign([UNGROUPED_SHEET_NAME])
        assert names == [UNGROUPED_SHEET_NAME]
        assert renames == []
