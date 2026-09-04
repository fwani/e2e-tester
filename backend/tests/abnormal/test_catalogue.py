"""T009 — 시나리오 목록 자체를 검증한다.

두 가지를 본다.

1. **커버리지** (SC-206) — 고장 유형 4종 × 조작 면 3종의 12개 조합이 각각 3건 이상
2. **수단 등록 전수성** (RG-106·SC-211) — 목록의 모든 시나리오에 실행 수단이 등록돼 있다

2번이 이 파일의 핵심이다. 등록되지 않은 시나리오를 **건너뛰면** "전건 통과"(SC-201)가 거짓이
된다. 건너뛰기는 통과가 아니다.
"""

from __future__ import annotations

import collections

import pytest
from tests.abnormal.catalogue import (
    CATALOGUE_PATH,
    DRIVERS,
    FAULTS,
    SURFACES,
    load_catalogue,
    scenarios,
)

MIN_PER_COMBINATION = 3


def test_catalogue_exists_in_one_place() -> None:
    """목록은 specs 아래 한 곳뿐이다. 복사본을 만들면 조합 커버리지가 갈라진다."""
    assert CATALOGUE_PATH.exists(), f"목록이 없다: {CATALOGUE_PATH}"


def test_every_combination_has_enough_scenarios() -> None:
    """12개 조합이 각각 3건 이상이어야 한다 (SC-206)."""
    counts = collections.Counter((s.fault, s.surface) for s in scenarios())

    thin = {
        f"{fault}/{surface}": counts[(fault, surface)]
        for fault in FAULTS
        for surface in SURFACES
        if counts[(fault, surface)] < MIN_PER_COMBINATION
    }
    assert not thin, f"조합별 최소 {MIN_PER_COMBINATION}건을 채우지 못했다: {thin}"


def test_ids_are_unique() -> None:
    ids = [s.id for s in scenarios()]
    duplicated = [i for i, n in collections.Counter(ids).items() if n > 1]
    assert not duplicated, f"식별자가 중복됐다: {duplicated}"


def test_fields_are_within_the_declared_vocabulary() -> None:
    for s in scenarios():
        assert s.fault in FAULTS, f"{s.id}: 알 수 없는 고장 유형 {s.fault!r}"
        assert s.surface in SURFACES, f"{s.id}: 알 수 없는 조작 면 {s.surface!r}"
        assert s.operation.strip(), f"{s.id}: 조작 설명이 비어 있다"
        assert s.target.strip(), f"{s.id}: 조작 대상이 비어 있다"


def test_catalogue_carries_no_expected_responses() -> None:
    """시나리오에 기대 응답을 적지 않는다는 결정을 목록이 지키는지 본다.

    기대 코드·메시지를 적으면 구현이 틀렸을 때 기대값도 같이 틀린다 (명세의 판정 규칙).
    """
    forbidden = {"expect", "expected", "expected_code", "expected_status", "expected_message"}
    for raw in load_catalogue()["scenarios"]:
        leaked = forbidden & set(raw)
        assert not leaked, f"{raw['id']}: 기대 응답을 적었다 {sorted(leaked)}"


@pytest.mark.parametrize("surface", SURFACES)
def test_every_scenario_has_a_registered_driver(surface: str) -> None:
    """RG-106 — 실행 수단이 없는 시나리오는 **실패**다. 건너뛰기가 아니다.

    수단을 등록하는 모듈을 여기서 임포트한다. 임포트하지 않으면 레지스트리가 비어 있어
    이 검증 자체가 무의미해진다.
    """
    import tests.abnormal.drivers  # noqa: F401  (등록 부작용을 위해 임포트한다)

    missing = [str(s) for s in scenarios(surface) if s.id not in DRIVERS]
    assert not missing, (
        f"{surface} 면에서 실행 수단이 등록되지 않은 시나리오 {len(missing)}건:\n  "
        + "\n  ".join(missing)
        + "\n\n건너뛰기는 통과가 아니다 (RG-106). 수단을 등록하거나 목록에서 빼야 한다."
    )
