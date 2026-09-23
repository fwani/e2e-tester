"""019 T008 — 가져오기 출처 표시의 하위 호환과 무해성.

`Test.imported_from` 은 헌법 원칙 I 이 허용하는 **메타데이터**다. 두 가지를 확인한다.

1. 019 이전에 저장된 정의 파일이 그대로 읽힌다 (키가 없다)
2. 표시가 있든 없든 **Step 의 실행 의미가 달라지지 않는다**

두 번째가 이 파일의 존재 이유다. provenance 가 실행에 영향을 주기 시작하면 그것은
메타데이터가 아니라 Step 모델의 일부가 되고, 원칙 I 위반이다.
"""

from __future__ import annotations

import datetime as dt

import pytest
import yaml
from pydantic import ValidationError

from itb.domain.test_case import DSL_VERSION, ImportProvenance, Test

LEGACY_YAML = """\
dsl_version: 1
id: TC-001
name: 운영 관리 메뉴 진입
description: null
actor: null
authoring_mode: ai
start_url: https://example.test
browser: chromium
variables:
- name: SECRET_INPUT_LOGIN_PW
  value: null
  sensitive: true
steps:
- id: step-01
  label: 비밀번호 입력
  author: ai
  tab: 0
  timeout_ms: 10000
  frame_url: null
  type: fill
  target:
    tag: input
    test_id: null
    role: textbox
    accessible_name: 비밀번호
    role_status: verified
    label: null
    text: null
    stable_attr: null
    css:
      value: input#login-pw
      status: verified
  value: '{{SECRET_INPUT_LOGIN_PW}}'
"""


def _legacy() -> Test:
    return Test.model_validate(yaml.safe_load(LEGACY_YAML))


# ─── 하위 호환 (data-model §5) ──────────────────────────────────────────────


def test_legacy_definition_still_loads() -> None:
    """019 이전 파일에는 `imported_from` 키가 없다. 기본값으로 읽혀야 한다."""
    test = _legacy()
    assert test.imported_from is None
    assert test.dsl_version == DSL_VERSION


def test_dsl_version_is_not_bumped() -> None:
    """`dsl_version` 을 올렸다면 기존 파일이 전부 거절된다.

    이 단언이 깨지는 날은 `_check_refs` 가 사용자 자산을 못 읽게 되는 날이다.
    """
    assert DSL_VERSION == 1


# ─── 실행 의미에 관여하지 않는다 (헌법 원칙 I) ─────────────────────────────


def test_provenance_does_not_change_step_semantics() -> None:
    """표시를 붙인 테스트와 안 붙인 테스트의 **Step 이 완전히 같다**."""
    plain = _legacy()
    marked = _legacy().model_copy(
        update={
            "imported_from": ImportProvenance(
                source_file="team-bundle.itbshare.yaml",
                imported_at=dt.datetime(2026, 9, 23, tzinfo=dt.UTC),
                original_id="TC-009",
            )
        }
    )

    assert marked.imported_from is not None
    plain_steps = [s.model_dump(mode="json") for s in plain.steps]
    marked_steps = [s.model_dump(mode="json") for s in marked.steps]
    assert plain_steps == marked_steps
    assert marked.referenced_variables() == plain.referenced_variables()
    assert marked.sensitive_variable_names() == plain.sensitive_variable_names()


def test_provenance_round_trips_through_yaml() -> None:
    """저장했다 읽어도 같아야 한다 — 정의 파일이 정본이다."""
    marked = _legacy().model_copy(
        update={
            "imported_from": ImportProvenance(
                source_file="team-bundle.itbshare.yaml",
                imported_at=dt.datetime(2026, 9, 23, tzinfo=dt.UTC),
                original_id="TC-009",
            )
        }
    )
    reloaded = Test.model_validate(yaml.safe_load(yaml.safe_dump(marked.model_dump(mode="json"))))
    assert reloaded.imported_from == marked.imported_from


# ─── 표시 자체의 검증 ───────────────────────────────────────────────────────


def test_original_id_must_look_like_a_test_id() -> None:
    with pytest.raises(ValidationError):
        ImportProvenance(
            source_file="b.itbshare.yaml",
            imported_at=dt.datetime(2026, 9, 23, tzinfo=dt.UTC),
            original_id="not-an-id",
        )


def test_source_file_is_not_empty() -> None:
    """빈 이름은 「출처를 모른다」와 구별되지 않는다. 그 경우는 `imported_from=None` 이다."""
    with pytest.raises(ValidationError):
        ImportProvenance(
            source_file="",
            imported_at=dt.datetime(2026, 9, 23, tzinfo=dt.UTC),
            original_id="TC-001",
        )


def test_provenance_rejects_unknown_fields() -> None:
    """`extra="forbid"` — 모르는 키가 조용히 실리지 않는다."""
    with pytest.raises(ValidationError):
        ImportProvenance.model_validate(
            {
                "source_file": "b.itbshare.yaml",
                "imported_at": "2026-09-23T00:00:00Z",
                "original_id": "TC-001",
                "source_path": "/Users/someone/secret/path",
            }
        )
