"""실행 결말 네 값이 계약에 실렸다 (005 T007 · FR-131·FR-137).

`test_schema_drift.py` 는 **권위 정의 → 스키마 파일**만 본다. 그 한 걸음 뒤가 비어 있었다 —
스키마 파일이 맞아도 프론트 타입 생성물(`frontend/src/types/generated/`)이 낡아 있으면
화면은 여전히 두 값만 아는 상태로 컴파일된다. 헌법 Cross-language schema duty 가 요구하는
것은 **양쪽 끝이 같은 것**이고, 그래서 여기서 두 끝을 맞대어 본다.

값 자체를 하드코딩해 두는 이유는 별개다. 결말을 다시 좁히는 변경(예: `stopped` 제거)은
스키마와 타입을 함께 재생성하면 드리프트 검사를 조용히 통과한다. U-03 과 U-05 는 값이
모자라서 생긴 결함이므로, **몇 개가 있어야 하는지**를 테스트가 직접 들고 있어야 한다.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from itb.domain.run_result import Outcome, RunScope
from itb.schema.export import DEFAULT_OUT

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
GENERATED_TS = REPO_ROOT / "frontend" / "src" / "types" / "generated" / "run-result.d.ts"

EXPECTED_OUTCOMES = ["pass", "fail", "stopped", "partial_pass"]
"""data-model.md §1. **중지와 부분 성공이 각각 자기 이름을 갖는다.**

`stopped` 가 없으면 사용자가 누른 중지가 실패로 기록된다 (U-03).
`partial_pass` 가 없으면 실패를 건너뛴 실행이 통과로 보인다 (U-05).
"""

EXPECTED_SCOPES = ["full", "partial"]
"""결말과 다른 축이다 (data-model.md §2). 섞으면 "부분 구간을 전부 통과한 실행" 을
부를 이름이 없어진다."""

NEW_RUN_RESULT_FIELDS = ["start_index", "scope", "attempted_count", "stopped_step_index"]


def _run_result_schema() -> dict:
    return json.loads((DEFAULT_OUT / "run-result.schema.json").read_text(encoding="utf-8"))


def _ts_union(type_name: str) -> list[str]:
    """생성된 `.d.ts` 에서 유니온 타입의 리터럴을 순서대로 꺼낸다."""
    source = GENERATED_TS.read_text(encoding="utf-8")
    match = re.search(rf"^export type {type_name} = (.+);$", source, re.MULTILINE)
    assert match is not None, f"{GENERATED_TS} 에 {type_name} 유니온이 없다"
    return re.findall(r'"([^"]+)"', match.group(1))


# ─── 권위 정의 ──────────────────────────────────────────────────────────────


def test_domain_outcome_has_exactly_four_values() -> None:
    """도메인이 네 값을 갖는다. 여기가 권위다 (FR-131·FR-137)."""
    assert [o.value for o in Outcome] == EXPECTED_OUTCOMES


def test_domain_run_scope_has_exactly_two_values() -> None:
    assert [s.value for s in RunScope] == EXPECTED_SCOPES


# ─── 스키마 생성물 ──────────────────────────────────────────────────────────


def test_schema_carries_the_four_outcomes() -> None:
    """스키마가 네 값을 싣는다 (FR-131)."""
    schema = _run_result_schema()
    assert schema["$defs"]["Outcome"]["enum"] == EXPECTED_OUTCOMES


def test_schema_carries_run_scope() -> None:
    schema = _run_result_schema()
    assert schema["$defs"]["RunScope"]["enum"] == EXPECTED_SCOPES


@pytest.mark.parametrize("field", NEW_RUN_RESULT_FIELDS)
def test_schema_requires_the_new_run_result_fields(field: str) -> None:
    """네 필드가 **필수**다 (data-model.md §2).

    선택으로 두면 옛 결과 파일과 새 결과 파일이 같은 타입을 갖고, 화면이 `undefined` 를
    분기마다 다시 다뤄야 한다. 기본값은 모델이 준다.
    """
    schema = _run_result_schema()
    assert field in schema["properties"], f"{field} 가 스키마에 없다"
    assert field in schema["required"], f"{field} 가 required 에 없다"


def test_stopped_step_index_is_nullable() -> None:
    """중지가 아닌 실행에서는 비어 있어야 한다 — 0 으로 채우면 첫 Step 에서 멈춘 것과 같아진다."""
    schema = _run_result_schema()
    variants = schema["properties"]["stopped_step_index"]["anyOf"]
    assert {"type": "null"} in variants


# ─── 프론트 타입 생성물 (Cross-language schema duty) ────────────────────────


def test_generated_typescript_carries_the_same_outcomes() -> None:
    """프론트 타입이 같은 네 값을 안다.

    이것이 빠지면 화면은 `outcome === "fail"` 분기를 그대로 둔 채 컴파일된다 — 결말을
    넓힌 변경이 화면에 도달하지 않는다 (plan 위험표 1행).
    """
    assert _ts_union("Outcome") == EXPECTED_OUTCOMES


def test_generated_typescript_carries_run_scope() -> None:
    assert _ts_union("RunScope") == EXPECTED_SCOPES


def test_generated_typescript_keeps_step_outcome_at_four_values() -> None:
    """Step 결말은 **바뀌지 않았다** (헌법 원칙 I).

    005 는 실행 결말만 넓혔다. Step DSL 쪽이 함께 움직였다면 그것은 사고다.
    """
    assert _ts_union("StepOutcome") == ["pass", "fail", "skipped", "not_run"]


@pytest.mark.parametrize("field", NEW_RUN_RESULT_FIELDS)
def test_generated_typescript_carries_the_new_fields(field: str) -> None:
    source = GENERATED_TS.read_text(encoding="utf-8")
    assert re.search(rf"^\s+{field}:", source, re.MULTILINE), (
        f"{field} 가 생성된 타입에 없다 — npm run gen:types 를 돌리지 않았다"
    )
