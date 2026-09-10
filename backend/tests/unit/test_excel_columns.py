"""워크북 컬럼 대조 (014 T022 · FR-003·FR-017)."""

from __future__ import annotations

import unicodedata

from itb.portability.columns import ORDER, REQUIRED, Column, map_headers, normalize_header


class OrderTests:
    def test_일곱개가_정해진_순서로_있다(self) -> None:
        assert [c.value for c in ORDER] == [
            "TC ID",
            "대상기능",
            "테스트항목",
            "수행자",
            "수행 절차",
            "기대 결과",
            "결과",
        ]

    def test_필수는_둘뿐이다(self) -> None:
        assert REQUIRED == {Column.TC_ID, Column.NAME}


class NormalizeTests:
    def test_앞뒤_공백을_뗀다(self) -> None:
        assert normalize_header("  TC ID  ") == "tc id"

    def test_대소문자를_무시한다(self) -> None:
        assert normalize_header("TC Id") == normalize_header("tc id")

    def test_가운데_연속_공백을_줄인다(self) -> None:
        assert normalize_header("수행   절차") == "수행 절차"

    def test_자모분리된_한글도_같게_본다(self) -> None:
        # NFD 로 저장된 파일이 있다. 눈으로 같은 글자가 대조에 실패하면 안 된다.
        nfd = unicodedata.normalize("NFD", "대상기능")
        assert nfd != "대상기능"
        assert normalize_header(nfd) == normalize_header("대상기능")

    def test_None_은_빈_문자열이다(self) -> None:
        assert normalize_header(None) == ""


class MapHeadersTests:
    def test_정확한_머리글을_찾는다(self) -> None:
        m = map_headers(
            ["TC ID", "대상기능", "테스트항목", "수행자", "수행 절차", "기대 결과", "결과"]
        )
        assert m.usable
        assert m.index[Column.TC_ID] == 0
        assert m.index[Column.OUTCOME] == 6

    def test_열_순서가_달라도_찾는다(self) -> None:
        m = map_headers(["대상기능", "결과", "TC ID"])
        assert m.usable
        assert m.index[Column.NAME] == 0
        assert m.index[Column.TC_ID] == 2

    def test_표기가_달라도_찾는다(self) -> None:
        m = map_headers(["TC_ID", "대상 기능", "설명", "역할", "수행절차", "기대결과", "P/F"])
        assert m.usable
        assert set(m.index) == set(ORDER)

    def test_필수_컬럼이_없으면_쓸_수_없다(self) -> None:
        m = map_headers(["설명", "결과"])
        assert not m.usable
        assert m.missing_required == {Column.TC_ID, Column.NAME}

    def test_선택_컬럼은_없어도_된다(self) -> None:
        m = map_headers(["TC ID", "대상기능"])
        assert m.usable
        assert Column.ACTOR not in m.index

    def test_모르는_머리글은_무시한다(self) -> None:
        # 비슷해 보인다고 추측하지 않는다.
        m = map_headers(["TC ID", "대상기능", "담당부서", "비고"])
        assert m.usable
        assert set(m.index) == {Column.TC_ID, Column.NAME}

    def test_같은_컬럼이_둘이면_왼쪽이_이긴다(self) -> None:
        m = map_headers(["TC ID", "대상기능", "tc id"])
        assert m.index[Column.TC_ID] == 0

    def test_빈_머리글_칸을_건너뛴다(self) -> None:
        m = map_headers([None, "TC ID", "", "대상기능"])
        assert m.usable
        assert m.index[Column.TC_ID] == 1
        assert m.index[Column.NAME] == 3


class ValueTests:
    def test_행에서_값을_꺼낸다(self) -> None:
        m = map_headers(["TC ID", "대상기능"])
        assert m.value(["TC-001", "로그인"], Column.NAME) == "로그인"

    def test_없는_컬럼은_None(self) -> None:
        m = map_headers(["TC ID", "대상기능"])
        assert m.value(["TC-001", "로그인"], Column.ACTOR) is None

    def test_행이_짧으면_None(self) -> None:
        # 뒤쪽 빈 칸이 통째로 잘려 오는 파일이 있다.
        m = map_headers(["TC ID", "대상기능", "수행자"])
        assert m.value(["TC-001", "로그인"], Column.ACTOR) is None
