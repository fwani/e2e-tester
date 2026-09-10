"""014 이전에 만든 자산이 그대로 읽히는가 (014 T025 · quickstart §3 회귀 1).

`Test` 에 `description` 과 `actor` 를 더했다. 두 필드는 **기본값이 None** 이라 옛 파일에
없어도 읽혀야 한다 — 그 사실을 확인하는 유일한 검사가 여기다.

`dsl_version` 을 올리지 않은 이유도 함께 못박는다. 올렸다면 `Test._check_refs` 가
"지원하지 않는 dsl_version" 으로 **기존 파일을 전부 거절한다**. 필드를 더하는 것은
판올림이 아니다.

이 파일은 손으로 쓴 YAML 을 읽는다. 모델로 만들어 저장한 뒤 다시 읽으면 새 필드가 이미
들어 있어, 정작 확인하려는 것(그 키가 **없는** 파일)을 확인하지 못한다.
"""

from __future__ import annotations

import pathlib

import pytest

from itb.domain.test_case import DSL_VERSION, Project, Test
from itb.storage.repository import ProjectRepository
from itb.storage.yaml_io import load_model

LEGACY_TEST_YAML = """\
dsl_version: 1
id: TC-001
name: 프로젝트 생성
authoring_mode: record
start_url: https://example.internal/login
browser: chromium
variables:
  - name: PROJECT_NAME
    value: TEST
    sensitive: false
steps:
  - id: step-01
    type: fill
    label: 이름 입력
    author: human
    tab: 0
    timeout_ms: 5000
    value: "{{PROJECT_NAME}}"
    target:
      tag: input
      label: {value: 이름, status: verified}
  - id: step-02
    type: assertion
    label: '"TEST" 표시 확인'
    author: human
    tab: 0
    timeout_ms: 5000
    assertion:
      kind: visible
      value: "{{PROJECT_NAME}}"
      target:
        text: {value: TEST, status: verified}
created_at: 2026-09-01T10:00:00Z
updated_at: 2026-09-01T10:00:00Z
"""

LEGACY_PROJECT_YAML = """\
name: 옛 프로젝트
default_start_url: https://example.internal
browser: chromium
test_id_attribute: data-testid
next_test_number: 2
max_tabs: 10
"""


@pytest.fixture
def legacy_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """014 이전 모양의 프로젝트 디렉터리."""
    root = tmp_path / "legacy"
    (root / "tests").mkdir(parents=True)
    (root / "itb-project.yaml").write_text(LEGACY_PROJECT_YAML, encoding="utf-8")
    (root / "tests" / "TC-001-프로젝트-생성.yaml").write_text(LEGACY_TEST_YAML, encoding="utf-8")
    return root


class LegacyReadTests:
    def test_옛_테스트_정의가_읽힌다(self, legacy_root: pathlib.Path) -> None:
        test = load_model(legacy_root / "tests" / "TC-001-프로젝트-생성.yaml", Test)
        assert test.id == "TC-001"
        assert test.name == "프로젝트 생성"
        assert len(test.steps) == 2

    def test_없는_필드는_None_이_된다(self, legacy_root: pathlib.Path) -> None:
        test = load_model(legacy_root / "tests" / "TC-001-프로젝트-생성.yaml", Test)
        assert test.description is None
        assert test.actor is None

    def test_옛_프로젝트_파일이_읽힌다(self, legacy_root: pathlib.Path) -> None:
        project = load_model(legacy_root / "itb-project.yaml", Project)
        assert project.name == "옛 프로젝트"
        assert project.groups == []

    def test_dsl_version_은_그대로_1이다(self) -> None:
        # 올렸다면 위 정의들이 전부 거절됐을 것이다.
        assert DSL_VERSION == 1

    def test_저장소가_옛_프로젝트를_연다(self, legacy_root: pathlib.Path) -> None:
        repo = ProjectRepository.open(legacy_root)
        tests, problems = repo.list_tests()
        assert [t.id for t in tests] == ["TC-001"]
        assert problems == []

    def test_초안_디렉터리가_없어도_동작한다(self, legacy_root: pathlib.Path) -> None:
        # 초안을 한 번도 만들지 않은 프로젝트가 정상이다.
        repo = ProjectRepository.open(legacy_root)
        assert repo.drafts.list_paths() == []
        assert repo.drafts.count() == 0
        assert repo.drafts.list_all() == ([], [])

    def test_옛_테스트를_다시_저장해도_읽힌다(self, legacy_root: pathlib.Path) -> None:
        # 새 필드가 None 으로 직렬화돼도 다시 읽혀야 한다.
        repo = ProjectRepository.open(legacy_root)
        test = repo.list_tests()[0][0]
        repo.write_test(test)
        again = repo.list_tests()[0][0]
        assert again.description is None
        assert again.actor is None
        assert again.id == "TC-001"

    def test_새_필드를_채워_저장하면_보존된다(self, legacy_root: pathlib.Path) -> None:
        repo = ProjectRepository.open(legacy_root)
        test = repo.list_tests()[0][0]
        updated = test.model_copy(update={"description": "설명", "actor": "관리자"})
        repo.write_test(updated)
        again = repo.list_tests()[0][0]
        assert again.description == "설명"
        assert again.actor == "관리자"


class DraftsAreSeparateTests:
    def test_초안_파일이_테스트_목록에_섞이지_않는다(self, legacy_root: pathlib.Path) -> None:
        # 벽이 정규식이 아니라 파일시스템이라는 것을 못박는다 (research R7).
        repo = ProjectRepository.open(legacy_root)
        (legacy_root / "drafts").mkdir()
        (legacy_root / "drafts" / "D-0001-로그인.yaml").write_text(
            "draft_id: D-0001\n", encoding="utf-8"
        )
        assert [t.id for t in repo.list_tests()[0]] == ["TC-001"]
        assert len(repo.drafts.list_paths()) == 1
