"""T015 — 오류 계약을 우회해 응답을 만드는 곳이 없는지 원본을 훑는다 (RG-104-3).

개별 경로를 하나씩 보지 않는다. `itb/api` 아래 **모든 파일**을 구문 트리로 읽어, 계약을
거치지 않고 오류를 내는 표현을 찾는다. 새 파일이 추가돼도 자동으로 포함된다.

우회가 왜 문제인가: `HTTPException(400, "안 됩니다")` 는 `{"detail": "안 됩니다"}` 를 내보낸다.
분류도 다음 행동도 없고, 화면의 오류 추출기는 `error.message` 를 찾다 실패해 "요청이
실패했습니다"라는 한 문장만 남긴다 — 사용자는 무엇이 잘못됐는지 알 수 없다.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

API_DIR = pathlib.Path(__file__).resolve().parents[2] / "src" / "itb" / "api"

# 계약 자체를 정의하는 파일. 여기서는 HTTPException 을 상속해 쓰는 것이 정상이다.
CONTRACT_OWNER = "errors.py"


def _api_sources() -> list[pathlib.Path]:
    return sorted(p for p in API_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def _bypasses(tree: ast.AST) -> list[tuple[int, str]]:
    """계약을 거치지 않는 오류 생성을 찾는다."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = (
            fn.attr
            if isinstance(fn, ast.Attribute)
            else fn.id
            if isinstance(fn, ast.Name)
            else None
        )
        if name == "HTTPException":
            found.append((node.lineno, "HTTPException 을 직접 만든다"))
    return found


def test_api_layer_does_not_bypass_the_error_contract() -> None:
    offenders: list[str] = []
    for path in _api_sources():
        if path.name == CONTRACT_OWNER:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, why in _bypasses(tree):
            offenders.append(f"{path.relative_to(API_DIR.parents[2])}:{line} — {why}")

    assert not offenders, (
        "오류 계약을 우회하는 지점이 있다 (RG-104-3):\n  "
        + "\n  ".join(offenders)
        + "\n\n`itb.api.errors` 의 생성자(bad_request/not_found/conflict/…)를 쓰세요. "
        "계약을 거치지 않으면 분류와 다음 행동이 빠진 채 나갑니다."
    )


def test_the_contract_owner_still_exists() -> None:
    """위 검사가 통과했다는 것이 '계약이 사라졌다'는 뜻이 되지 않게 한다."""
    owner = API_DIR / CONTRACT_OWNER
    assert owner.exists(), f"오류 계약 결합부가 사라졌다: {owner}"
    source = owner.read_text(encoding="utf-8")
    for helper in ("bad_request", "not_found", "conflict", "not_implemented"):
        assert f"def {helper}(" in source, f"{helper}() 가 없다"


@pytest.mark.parametrize("path", _api_sources(), ids=lambda p: p.name)
def test_each_api_file_parses(path: pathlib.Path) -> None:
    """훑기가 조용히 아무것도 못 읽는 상태로 통과하지 않게 한다."""
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
