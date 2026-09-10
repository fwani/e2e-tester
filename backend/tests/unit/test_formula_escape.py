"""수식 주입 방어와 셀 자르기 (014 T023 · FR-009·FR-010 · research R13)."""

from __future__ import annotations

from itb.portability.limits import MAX_CELL_CHARS
from itb.portability.workbook import clamp_cell, escape_cell


class EscapeTests:
    def test_등호로_시작하면_고정한다(self) -> None:
        assert escape_cell("=1+1") == "'=1+1"

    def test_더하기로_시작하면_고정한다(self) -> None:
        assert escape_cell("+A1") == "'+A1"

    def test_빼기로_시작하면_고정한다(self) -> None:
        assert escape_cell("-1") == "'-1"

    def test_골뱅이로_시작하면_고정한다(self) -> None:
        assert escape_cell("@SUM(A1)") == "'@SUM(A1)"

    def test_탭과_캐리지리턴도_고정한다(self) -> None:
        assert escape_cell("\tfoo") == "'\tfoo"
        assert escape_cell("\rbar") == "'\rbar"

    def test_명령_실행형_문자열을_고정한다(self) -> None:
        payload = '=cmd|\' /C calc\'!A1'
        assert escape_cell(payload).startswith("'=")

    def test_평범한_문자열은_그대로다(self) -> None:
        assert escape_cell("로그인 버튼을 누른다") == "로그인 버튼을 누른다"

    def test_변수_참조는_그대로다(self) -> None:
        assert escape_cell("{{SECRET_LOGIN_PW}}") == "{{SECRET_LOGIN_PW}}"

    def test_빈_문자열은_그대로다(self) -> None:
        assert escape_cell("") == ""

    def test_가운데_등호는_건드리지_않는다(self) -> None:
        assert escape_cell("a=b") == "a=b"

    def test_번호매긴_절차는_그대로다(self) -> None:
        # "1. ..." 은 수식 선두 문자가 아니다.
        assert escape_cell("1. 로그인 화면을 연다") == "1. 로그인 화면을 연다"


class ClampTests:
    def test_짧으면_그대로다(self) -> None:
        assert clamp_cell("짧다") == "짧다"

    def test_한도_경계에서_그대로다(self) -> None:
        value = "가" * MAX_CELL_CHARS
        assert clamp_cell(value) == value

    def test_넘으면_한도_안으로_들어온다(self) -> None:
        value = "\n".join(f"{i}. 줄" for i in range(20000))
        assert len(value) > MAX_CELL_CHARS
        assert len(clamp_cell(value)) <= MAX_CELL_CHARS

    def test_잘렸음을_칸_안에_남긴다(self) -> None:
        # 경고는 화면에만 있고 파일은 남에게 전달된다.
        value = "\n".join(f"{i}. 줄" for i in range(20000))
        assert "생략" in clamp_cell(value)

    def test_생략한_줄_수를_말한다(self) -> None:
        value = "\n".join(f"{i}. 줄" for i in range(20000))
        result = clamp_cell(value)
        kept = len(result.splitlines()) - 1  # 표시 문구 한 줄 제외
        assert f"이하 {20000 - kept}줄 생략" in result

    def test_실패시키지_않는다(self) -> None:
        # 한 줄이 통째로 한도를 넘어도 예외가 아니다.
        assert len(clamp_cell("가" * (MAX_CELL_CHARS * 2))) <= MAX_CELL_CHARS
