"""T026 — DSL 스키마 드리프트 검사. 헌법 Cross-language schema duty.

권위 정의(`itb.domain`)에서 스키마를 새로 생성해 커밋된 파일과 비교한다. 다르면 실패한다.
생성 단계를 잊었을 때 프론트 타입이 조용히 어긋나는 것을 막는 유일한 수단이다.
"""

from __future__ import annotations

import json

import pytest

from itb.schema.export import DEFAULT_OUT, MODELS, check, render


def test_no_schema_drift() -> None:
    drifted = check(DEFAULT_OUT)
    assert not drifted, (
        f"스키마 생성물이 커밋된 내용과 다릅니다: {', '.join(drifted)}. "
        "uv run python -m itb.schema.export 로 재생성 후 커밋하세요."
    )


@pytest.mark.parametrize("name", sorted(MODELS))
def test_schema_file_exists_and_is_valid_json(name: str) -> None:
    p = DEFAULT_OUT / f"{name}.schema.json"
    assert p.exists(), f"{p} 가 없다"
    json.loads(p.read_text(encoding="utf-8"))


def test_render_is_deterministic() -> None:
    """두 번 생성해도 같아야 한다. 아니면 드리프트 검사가 무의미한 diff 로 실패한다."""
    for name in MODELS:
        assert render(name) == render(name)


def test_step_schema_keeps_discriminated_union() -> None:
    """판별 정보가 없으면 TypeScript 가 판별 유니온을 만들 수 없다 (research R6)."""
    schema = json.loads((DEFAULT_OUT / "step.schema.json").read_text(encoding="utf-8"))
    assert "oneOf" in schema
    disc = schema.get("discriminator")
    assert disc is not None
    assert disc["propertyName"] == "type"
    assert set(disc["mapping"]) == {
        "click",
        "fill",
        "select",
        "navigate",
        "assertion",
        "close_tab",
        "hover",
        "drag",
    }


def test_object_definitions_forbid_additional_properties() -> None:
    """extra="forbid" 가 스키마까지 전달되는지 확인한다.

    전달되지 않으면 생성된 TypeScript 에 인덱스 시그니처가 붙어 필드명 오타가
    타입 검사를 통과한다.
    """
    schema = json.loads((DEFAULT_OUT / "step.schema.json").read_text(encoding="utf-8"))
    offenders = [
        name
        for name, definition in schema.get("$defs", {}).items()
        if definition.get("type") == "object"
        and definition.get("additionalProperties") is not False
    ]
    assert not offenders, f"additionalProperties:false 가 빠진 정의: {offenders}"


def test_step_type_is_required_in_serialization_schema() -> None:
    """`type` 이 옵셔널이면 TS 가 판별할 수 없다."""
    schema = json.loads((DEFAULT_OUT / "step.schema.json").read_text(encoding="utf-8"))
    for name, definition in schema["$defs"].items():
        if not name.endswith("Step"):
            continue
        assert "type" in definition.get("required", []), f"{name} 의 type 이 required 가 아니다"
