"""YAML 입출력. FR-011·FR-085.

안전 로더만 쓴다 — 임의 객체 역직렬화를 허용하면 테스트 정의 파일이 코드 실행 경로가 된다.

검증 실패 시 **파일 경로와 문제 위치**를 알려 사용자가 직접 고칠 수 있게 한다.
사람이 읽고 편집할 수 있는 평문 형식을 택한 이유가 그것이다.
"""

from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, ValidationError

MAX_FILE_BYTES = 4 * 1024 * 1024
"""테스트 정의 파일 크기 상한. Step 200개 규모를 크게 넘는 파일은 거절한다."""


class DefinitionError(Exception):
    """정의 파일을 읽을 수 없다. 메시지를 그대로 사용자에게 보여준다."""


def _format_validation_error(path: pathlib.Path, exc: ValidationError) -> str:
    lines = [f"{path} 를 읽을 수 없습니다. {exc.error_count()}건의 문제가 있습니다:"]
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(최상위)"
        lines.append(f"  · {loc}: {err['msg']}")
    return "\n".join(lines)


def load_model[M: BaseModel](path: pathlib.Path, model: type[M]) -> M:
    """YAML 파일을 모델로 검증해 읽는다."""
    if not path.exists():
        msg = f"파일이 없습니다: {path}"
        raise DefinitionError(msg)

    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        msg = f"{path} 가 너무 큽니다 ({size:,}B > {MAX_FILE_BYTES:,}B)."
        raise DefinitionError(msg)

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        msg = f"{path} 의 YAML 형식이 올바르지 않습니다:\n  {exc}"
        raise DefinitionError(msg) from exc
    except UnicodeDecodeError as exc:
        msg = f"{path} 를 UTF-8 로 읽을 수 없습니다: {exc}"
        raise DefinitionError(msg) from exc

    if raw is None:
        msg = f"{path} 가 비어 있습니다."
        raise DefinitionError(msg)
    if not isinstance(raw, dict):
        msg = f"{path} 의 최상위가 매핑이 아닙니다 (실제: {type(raw).__name__})."
        raise DefinitionError(msg)

    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        raise DefinitionError(_format_validation_error(path, exc)) from exc


def dump_model(path: pathlib.Path, obj: BaseModel) -> None:
    """모델을 사람이 읽을 수 있는 YAML 로 쓴다.

    ``sort_keys=False`` 로 모델의 필드 순서를 유지한다 — 정렬하면 git diff 가
    의미 없이 흔들리고 사람이 읽기도 어려워진다.
    """
    payload = obj.model_dump(mode="json", exclude_none=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
