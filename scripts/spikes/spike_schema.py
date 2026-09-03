"""T009 — Pydantic v2 판별 유니온 → JSON Schema 왕복 확인 (research R6).

판별 유니온이 JSON Schema 에서 discriminator/oneOf 로 떨어지는지 본다.
떨어지지 않으면 json-schema-to-typescript 가 판별 유니온을 만들지 못하므로
스키마 후처리 단계가 필요하다.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ClickStep(BaseModel):
    model_config = ConfigDict(extra="forbid")   # → additionalProperties: false
    type: Literal["click"]
    id: str
    tab: int = 0


class FillStep(BaseModel):
    model_config = ConfigDict(extra="forbid")   # → additionalProperties: false
    type: Literal["fill"]
    id: str
    tab: int = 0
    value: str


class CloseTabStep(BaseModel):
    model_config = ConfigDict(extra="forbid")   # → additionalProperties: false
    type: Literal["close_tab"]
    id: str
    tab: int = 0


Step = Annotated[ClickStep | FillStep | CloseTabStep, Field(discriminator="type")]


class StepEnvelope(RootModel[Step]):
    pass


def main() -> int:
    schema = StepEnvelope.model_json_schema()
    out = pathlib.Path("scripts/spikes/out")
    out.mkdir(parents=True, exist_ok=True)
    p = out / "step-union.schema.json"
    p.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")

    has_oneof = "oneOf" in schema
    has_disc = "discriminator" in schema
    print(f"  oneOf 존재: {has_oneof}")
    print(f"  discriminator 존재: {has_disc}")
    if has_disc:
        print(f"  discriminator 내용: {json.dumps(schema['discriminator'], ensure_ascii=False)}")
    print(f"  스키마 저장: {p}")

    if not (has_oneof and has_disc):
        print("  ✗ 판별 정보가 스키마에 없다 → 후처리 단계가 필요하다")
        return 1
    print("  ✓ 판별 유니온 정보가 스키마에 보존됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
