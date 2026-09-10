"""Pydantic 모델 → JSON Schema 내보내기. 헌법 Cross-language schema duty.

`itb.domain` 이 **유일한 권위 정의**다. 여기서 JSON Schema 를 내보내고, 프론트엔드는
그것으로 TypeScript 타입을 생성한다. 두 개의 손으로 관리하는 스키마 복사본은 원칙 I 위반이다.

    uv run python -m itb.schema.export

CI 의 schema-drift 잡이 재생성 결과를 커밋된 파일과 비교한다 (research R6).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from pydantic import TypeAdapter

from itb.domain.draft import Draft
from itb.domain.error import ErrorResponse
from itb.domain.manual_step import ManualStepSpec
from itb.domain.run_result import RunResult
from itb.domain.step import Step
from itb.domain.test_case import Project, Test

# backend/schema/ — pyproject 와 같은 층
DEFAULT_OUT = pathlib.Path(__file__).resolve().parents[3] / "schema"

MODELS: dict[str, TypeAdapter] = {
    "step-dsl": TypeAdapter(Test),
    "step": TypeAdapter(Step),
    "project": TypeAdapter(Project),
    "run-result": TypeAdapter(RunResult),
    # 오류 계약. 프론트엔드가 ErrorCode 목록을 손으로 복제하던 것을 대체한다 (003 EC-006).
    "error-response": TypeAdapter(ErrorResponse),
    # 손으로 넣을 수 있는 Step 종류. 화면이 이 목록을 상수로 복제하지 않게 한다 (009 FR-286).
    "manual-step": TypeAdapter(ManualStepSpec),
    # 아직 녹화되지 않은 테스트의 의도 (014). Test 와 **다른 모양**이어야 하며, 그 사실이
    # 스키마에도 드러난다 — steps 필드가 없다.
    "draft": TypeAdapter(Draft),
}


def render(name: str) -> str:
    """스키마 하나를 결정적인 문자열로 만든다.

    키 정렬과 개행을 고정한다 — 그렇지 않으면 드리프트 검사가 무의미한 diff 로 실패한다.
    """
    schema = MODELS[name].json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = schema.get("title", name)
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_all(out_dir: pathlib.Path) -> list[pathlib.Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []
    for name in MODELS:
        p = out_dir / f"{name}.schema.json"
        p.write_text(render(name), encoding="utf-8")
        written.append(p)
    return written


def check(out_dir: pathlib.Path) -> list[str]:
    """커밋된 파일이 새로 생성한 내용과 같은지 확인한다. 다른 항목 이름을 돌려준다."""
    drifted: list[str] = []
    for name in MODELS:
        p = out_dir / f"{name}.schema.json"
        if not p.exists() or p.read_text(encoding="utf-8") != render(name):
            drifted.append(name)
    return drifted


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="쓰지 않고 드리프트만 확인한다")
    args = ap.parse_args(argv)

    if args.check:
        drifted = check(args.out)
        if drifted:
            print("드리프트 발생:", ", ".join(drifted), file=sys.stderr)
            print("uv run python -m itb.schema.export 로 재생성 후 커밋하세요.", file=sys.stderr)
            return 1
        print("스키마 드리프트 없음")
        return 0

    for p in write_all(args.out):
        print(f"생성: {p.relative_to(p.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
