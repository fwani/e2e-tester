"""어긋남 표시가 실행과 생성으로 새지 않는다 (020 T012 · FR-012·FR-016).

**이것은 헌법 검사다.** 원칙 I 은 부가 정보가 실행 방식을 바꾸지 않을 것을, 원칙 V 는
내보낸 테스트가 제품 없이도 같은 일을 할 것을 요구한다. 새 필드가 실행기나 생성기로
새면 둘이 **동시에** 깨진다.

## 왜 문장이 아니라 검사인가

이 침식은 조용히 들어온다. 「알려진 결함이면 검증을 건너뛰자」나 「내보낼 때는 빼자」는
어느 시점엔가 합리적으로 들리고, 그 한 줄이 들어오는 순간 정의는 다시 제품 동작의
사본이 된다. 주석은 그것을 막지 못한다.

`tests/unit/test_definition_summary.py` 의 `ALLOWED_VALUE_READS` 가 세운 선례를 따른다 —
소스를 직접 읽어 이름의 부재를 고정한다.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "itb"

FORBIDDEN = "mismatch"

GUARDED = {
    "execution/step_executor.py": (
        "실행기가 어긋남 표시를 읽으면 검증 판정이 표시에 따라 달라진다 — "
        "헌법 원칙 I 이 금지하는 바로 그것이다 (FR-012)."
    ),
    "generator/playwright_gen.py": (
        "생성기가 어긋남 표시를 읽으면 내보낸 테스트가 제품 안과 다르게 동작한다 — "
        "헌법 원칙 V 의 「제품 없이도 쓸 수 있다」가 거짓이 된다 (FR-016)."
    ),
}


@pytest.mark.parametrize(("relative", "why"), sorted(GUARDED.items()))
def test_module_never_mentions_the_mismatch_field(relative: str, why: str) -> None:
    path = SRC / relative
    source = path.read_text(encoding="utf-8")

    # 주석·문자열에 이름이 나오는 것은 막지 않는다 — 막고 싶은 것은 **읽는 것**이다.
    tree = ast.parse(source)
    reads = [
        node
        for node in ast.walk(tree)
        if (isinstance(node, ast.Attribute) and node.attr == FORBIDDEN)
        or (isinstance(node, ast.Name) and node.id == FORBIDDEN)
        or (isinstance(node, ast.Constant) and node.value == FORBIDDEN)
    ]
    assert not reads, (
        f"{relative} 이 `{FORBIDDEN}` 을 읽는다 ({len(reads)}곳). {why}"
    )


def test_the_guarded_list_covers_both_principles() -> None:
    """지킬 모듈을 빠뜨리면 이 검사가 조용히 무력해진다.

    실행과 생성 **둘 다**가 목록에 있어야 한다 — 하나만 지키면 나머지 원칙이 열린다.
    """
    assert any("step_executor" in k for k in GUARDED)
    assert any("playwright_gen" in k for k in GUARDED)


def test_the_guarded_files_exist() -> None:
    """파일이 옮겨지면 이 검사는 아무것도 안 보고 통과한다. 그 상태를 막는다."""
    for relative in GUARDED:
        assert (SRC / relative).is_file(), (
            f"{relative} 이 없다 — 옮겼다면 이 목록도 함께 옮겨야 한다"
        )
