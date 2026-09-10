"""T032 — 프로젝트 저장 계층 단위 테스트 (FR-001·FR-007·FR-029·FR-085·FR-088b)."""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import pytest

from itb.domain.run_result import Outcome, RunResult
from itb.domain.test_case import Project, Test
from itb.storage.repository import (
    ProjectError,
    ProjectRepository,
    ResultUnreadableError,
    slugify,
    validate_project_path,
)
from itb.storage.yaml_io import MAX_FILE_BYTES, DefinitionError

CLOSE_TAB = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]


def make_project(**overrides: object) -> Project:
    payload: dict[str, object] = {
        "name": "데이터 플랫폼",
        "default_start_url": "http://127.0.0.1:4300/login.html",
    }
    payload.update(overrides)
    return Project(**payload)  # type: ignore[arg-type]


def make_test(test_id: str = "TC-001", name: str = "프로젝트 생성", **kw: object) -> Test:
    payload: dict[str, object] = {
        "id": test_id,
        "name": name,
        "authoring_mode": "record",
        "start_url": "http://127.0.0.1:4300/login.html",
        "steps": CLOSE_TAB,
    }
    payload.update(kw)
    return Test(**payload)  # type: ignore[arg-type]


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> ProjectRepository:
    return ProjectRepository.create(tmp_path / "proj", make_project())


# ─── 경로 검증 (FR-085) ─────────────────────────────────────────────────────


def test_relative_path_rejected() -> None:
    with pytest.raises(ProjectError, match="절대 경로"):
        validate_project_path(pathlib.Path("relative/dir"))


def test_parent_traversal_rejected(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ProjectError, match=r"\.\."):
        validate_project_path(tmp_path / ".." / "escaped")


def test_file_path_rejected(tmp_path: pathlib.Path) -> None:
    f = tmp_path / "a-file"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(ProjectError, match="디렉터리가 아닙니다"):
        validate_project_path(f)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("프로젝트 생성", "프로젝트-생성"),
        ("a/b/../c", "a-b-c"),
        ("with\x00null", "with-null"),
        ("!!!", "test"),
        ("", "test"),
    ],
)
def test_slugify_strips_path_and_control_chars(name: str, expected: str) -> None:
    """이름이 파일명으로 쓰이므로 경로 구분자·제어 문자를 제거해야 한다."""
    assert slugify(name) == expected


def test_slugify_caps_length() -> None:
    assert len(slugify("가" * 200)) <= 60


# ─── 생성·열기 (FR-001) ─────────────────────────────────────────────────────


def test_create_writes_layout(repo: ProjectRepository) -> None:
    assert repo.paths.project_file.exists()
    assert repo.paths.tests_dir.is_dir()
    assert repo.paths.gitignore.exists()


def test_create_refuses_existing_project(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "proj"
    ProjectRepository.create(root, make_project())
    with pytest.raises(ProjectError, match="이미 프로젝트가 있습니다"):
        ProjectRepository.create(root, make_project())


def test_open_missing_project(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ProjectError, match="찾을 수 없습니다"):
        ProjectRepository.open(tmp_path)


def test_open_roundtrip(repo: ProjectRepository) -> None:
    reopened = ProjectRepository.open(repo.paths.root)
    assert reopened.read_project().name == "데이터 플랫폼"


# ─── .gitignore (FR-088b) ───────────────────────────────────────────────────


def test_gitignore_excludes_secrets_and_runs(repo: ProjectRepository) -> None:
    body = repo.paths.gitignore.read_text(encoding="utf-8")
    assert "secrets.local.yaml" in body
    assert ".runs/" in body
    assert "*.key" in body


def test_gitignore_does_not_exclude_test_definitions(repo: ProjectRepository) -> None:
    """테스트 정의는 커밋 대상이다 — 제외되면 자산 이식성이 무너진다.

    주석에는 `tests/` 가 설명으로 등장하므로 **규칙 줄만** 검사한다.
    """
    rules = [
        line.strip()
        for line in repo.paths.gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert rules  # 규칙이 아예 없으면 검사가 무의미하다
    assert not any("tests" in rule for rule in rules)


def test_ensure_gitignore_preserves_user_rules(repo: ProjectRepository) -> None:
    repo.paths.gitignore.write_text("# 사용자 규칙\nmy-notes.txt\n", encoding="utf-8")
    changed = repo.ensure_gitignore()
    body = repo.paths.gitignore.read_text(encoding="utf-8")
    assert changed is True
    assert "my-notes.txt" in body
    assert "secrets.local.yaml" in body


def test_ensure_gitignore_is_idempotent(repo: ProjectRepository) -> None:
    assert repo.ensure_gitignore() is False


# ─── 테스트 정의 저장 (FR-007·FR-029) ──────────────────────────────────────


def test_write_and_read_test(repo: ProjectRepository) -> None:
    p = repo.write_test(make_test())
    assert p.name == "TC-001-프로젝트-생성.yaml"
    assert repo.read_test("TC-001").name == "프로젝트 생성"


def test_rename_removes_previous_file(repo: ProjectRepository) -> None:
    repo.write_test(make_test())
    repo.write_test(make_test(name="프로젝트 삭제"))
    names = [p.name for p in repo.list_test_paths()]
    assert names == ["TC-001-프로젝트-삭제.yaml"]


def test_read_unknown_test(repo: ProjectRepository) -> None:
    with pytest.raises(ProjectError, match="찾을 수 없습니다"):
        repo.read_test("TC-404")


def test_malformed_test_id_rejected(repo: ProjectRepository) -> None:
    with pytest.raises(ProjectError, match="테스트 ID 형식"):
        repo.find_test_path("../../etc/passwd")


def test_delete_test_removes_definition_and_artifacts(repo: ProjectRepository) -> None:
    repo.write_test(make_test())
    repo.write_result(
        RunResult(
            test_id="TC-001",
            outcome=Outcome.PASS,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            total_ms=10,
            passed_count=1,
            total_count=1,
            browser="chromium",
        )
    )
    assert repo.paths.run_dir("TC-001").exists()
    assert repo.delete_test("TC-001") is True
    assert repo.find_test_path("TC-001") is None
    assert not repo.paths.run_dir("TC-001").exists()


def test_delete_unknown_test_returns_false(repo: ProjectRepository) -> None:
    assert repo.delete_test("TC-999") is False


def test_list_tests_reports_broken_file_without_hiding_others(
    repo: ProjectRepository,
) -> None:
    """깨진 파일 하나가 목록 전체를 못 보게 만들면 안 된다."""
    repo.write_test(make_test("TC-001", "정상"))
    (repo.paths.tests_dir / "TC-002-broken.yaml").write_text("steps: []\n", encoding="utf-8")
    tests, problems = repo.list_tests()
    assert [t.id for t in tests] == ["TC-001"]
    assert len(problems) == 1
    assert "TC-002-broken.yaml" in problems[0]


def test_list_tests_is_sorted_by_id(repo: ProjectRepository) -> None:
    repo.write_test(make_test("TC-003", "셋"))
    repo.write_test(make_test("TC-001", "하나"))
    tests, _ = repo.list_tests()
    assert [t.id for t in tests] == ["TC-001", "TC-003"]


# ─── ID 부여 ────────────────────────────────────────────────────────────────


def test_allocate_test_id_increments(repo: ProjectRepository) -> None:
    assert repo.allocate_test_id() == "TC-001"
    assert repo.allocate_test_id() == "TC-002"


def test_allocate_test_id_skips_ids_taken_by_files(repo: ProjectRepository) -> None:
    """파일을 손으로 옮긴 뒤에도 충돌하지 않아야 한다."""
    repo.write_test(make_test("TC-001"))
    assert repo.allocate_test_id() == "TC-002"


def test_allocate_test_id_respects_existing_counter(tmp_path: pathlib.Path) -> None:
    repo = ProjectRepository.create(tmp_path / "p", make_project(next_test_number=42))
    assert repo.allocate_test_id() == "TC-042"


# ─── 실행 결과 (최근 1건) ───────────────────────────────────────────────────


def _result(outcome: Outcome, total_ms: int) -> RunResult:
    return RunResult(
        test_id="TC-001",
        outcome=outcome,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        total_ms=total_ms,
        passed_count=1,
        total_count=1,
        browser="chromium",
    )


def test_write_result_overwrites_previous(repo: ProjectRepository) -> None:
    """테스트당 최근 1건만 보관한다 (spec Assumptions)."""
    repo.write_result(_result(Outcome.PASS, 100))
    repo.write_result(_result(Outcome.FAIL, 200))
    got = repo.read_result("TC-001")
    assert got is not None
    assert got.outcome is Outcome.FAIL
    assert got.total_ms == 200


def test_read_result_missing_returns_none(repo: ProjectRepository) -> None:
    assert repo.read_result("TC-001") is None


def test_read_result_corrupted_raises_with_reason(repo: ProjectRepository) -> None:
    """T162 — 손상된 결과 파일을 "결과 없음" 으로 보고하지 않는다 (FR-087).

    없는 것처럼 돌려주면 화면이 "먼저 실행하세요" 를 띄우고, 사용자는 방금 한 실행이
    사라진 줄 안다. 파일이 있다는 사실과 읽을 수 없다는 사실을 모두 전달해야 한다.
    """
    p = repo.result_path("TC-001")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ResultUnreadableError, match="읽을 수 없습니다"):
        repo.read_result("TC-001")


def test_try_read_result_tolerates_corruption_for_listing(
    repo: ProjectRepository,
) -> None:
    """목록 경로는 깨진 파일 하나가 전체를 막지 않게 사유만 돌려준다."""
    p = repo.result_path("TC-001")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not json", encoding="utf-8")

    result, problem = repo.try_read_result("TC-001")
    assert result is None
    assert problem is not None
    assert "TC-001" in problem


def test_try_read_result_reports_no_problem_when_missing(
    repo: ProjectRepository,
) -> None:
    """파일이 없는 것은 문제가 아니다 — 아직 실행하지 않은 정상 상태다."""
    assert repo.try_read_result("TC-001") == (None, None)


def test_run_dir_rejects_bad_test_id(repo: ProjectRepository) -> None:
    with pytest.raises(ProjectError, match="테스트 ID 형식"):
        repo.paths.run_dir("../escape")


# ─── YAML 입출력 경계 (FR-085) ──────────────────────────────────────────────


def test_load_rejects_non_mapping_root(repo: ProjectRepository) -> None:
    p = repo.paths.tests_dir / "TC-005-list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    _, problems = repo.list_tests()
    assert any("최상위가 매핑이 아닙니다" in x for x in problems)


def test_load_rejects_empty_file(repo: ProjectRepository) -> None:
    (repo.paths.tests_dir / "TC-006-empty.yaml").write_text("", encoding="utf-8")
    _, problems = repo.list_tests()
    assert any("비어 있습니다" in x for x in problems)


def test_load_rejects_invalid_yaml(repo: ProjectRepository) -> None:
    (repo.paths.tests_dir / "TC-007-bad.yaml").write_text("a: [1,\n", encoding="utf-8")
    _, problems = repo.list_tests()
    assert any("YAML 형식이 올바르지 않습니다" in x for x in problems)


def test_load_rejects_oversized_file(repo: ProjectRepository) -> None:
    p = repo.paths.tests_dir / "TC-008-huge.yaml"
    p.write_text("x: " + "a" * (MAX_FILE_BYTES + 10), encoding="utf-8")
    _, problems = repo.list_tests()
    assert any("너무 큽니다" in x for x in problems)


def test_definition_error_names_the_file_and_field(repo: ProjectRepository) -> None:
    """사용자가 직접 고칠 수 있도록 파일 경로와 문제 위치를 알려야 한다."""
    p = repo.paths.tests_dir / "TC-009-nosteps.yaml"
    p.write_text(
        "id: TC-009\nname: x\nauthoring_mode: record\n"
        "start_url: http://127.0.0.1:4300/\nsteps: []\n",
        encoding="utf-8",
    )
    _, problems = repo.list_tests()
    assert len(problems) == 1
    assert "TC-009-nosteps.yaml" in problems[0]
    assert "steps" in problems[0]


def test_yaml_safe_loader_does_not_execute_python_tags(repo: ProjectRepository) -> None:
    """임의 객체 역직렬화를 허용하면 정의 파일이 코드 실행 경로가 된다."""
    p = repo.paths.tests_dir / "TC-010-unsafe.yaml"
    p.write_text("!!python/object/apply:os.system ['echo pwned']\n", encoding="utf-8")
    _, problems = repo.list_tests()
    assert len(problems) == 1
    assert isinstance(problems[0], str)


def test_dump_preserves_field_order(repo: ProjectRepository) -> None:
    """키를 정렬하면 git diff 가 의미 없이 흔들린다."""
    repo.write_test(make_test())
    body = repo.read_test("TC-001")
    text = repo.find_test_path("TC-001")
    assert text is not None
    raw = text.read_text(encoding="utf-8")
    assert raw.index("dsl_version") < raw.index("name")
    assert raw.index("id") < raw.index("steps")
    assert body.id == "TC-001"


def test_missing_file_raises_definition_error(tmp_path: pathlib.Path) -> None:
    from itb.storage.yaml_io import load_model

    with pytest.raises(DefinitionError, match="파일이 없습니다"):
        load_model(tmp_path / "nope.yaml", Project)


# ─── 013 식별자 형식 확장 (FR-444 · research R1·R3) ─────────────────────────


def test_a_grouped_test_shows_up_in_the_listing(repo: ProjectRepository) -> None:
    """**013 에서 가장 조용한 함정이었다** (research R1).

    `list_test_paths()` 가 `glob("TC-*.yaml")` 이면 새 접두어 테스트는 **저장은 되는데
    목록에 아예 안 나온다.** 쓰기도 읽기도 성공하므로 어디가 잘못됐는지 보이지 않는다.
    """
    repo.write_test(make_test("USER-001", "로그인"))
    repo.write_test(make_test("TC-002", "옛 테스트"))

    ids = [t.id for t in repo.list_tests()[0]]

    assert set(ids) == {"USER-001", "TC-002"}


def test_the_listing_ignores_yaml_that_is_not_a_test(repo: ProjectRepository) -> None:
    """`tests/` 에 사용자가 다른 `.yaml` 을 두었을 때 그것을 테스트로 읽지 않는다."""
    repo.write_test(make_test("USER-001", "로그인"))
    (repo.paths.tests_dir / "메모.yaml").write_text("아무 내용", encoding="utf-8")
    (repo.paths.tests_dir / "TC-002.yaml").write_text("이름 조각이 없다", encoding="utf-8")

    tests, problems = repo.list_tests()

    assert [t.id for t in tests] == ["USER-001"]
    assert problems == []


def test_numbers_are_unique_across_prefixes(repo: ProjectRepository) -> None:
    """**번호는 접두어를 넘어 고유하다** (research R3).

    그래야 그룹을 옮길 때 번호를 다시 뽑지 않는다 — `USER-003` → `DATA-003` 이 언제나
    빈자리다. FR-444c(식별자 고유)를 규칙이 아니라 구조로 만족시킨다.
    """
    repo.write_test(make_test("USER-001", "로그인"))
    repo.write_test(make_test("DATA-002", "적재"))

    assert repo.allocate_test_id() == "TC-003"
    assert repo.allocate_test_id("USER") == "USER-004"


def test_allocate_skips_numbers_taken_by_another_prefix(repo: ProjectRepository) -> None:
    """카운터만 믿지 않는 기존 성질이 접두어를 넘어서도 유지된다."""
    project = repo.read_project()
    project.next_test_number = 1
    repo.write_project(project)
    repo.write_test(make_test("USER-001", "로그인"))

    assert repo.allocate_test_id("DATA") == "DATA-002"


@pytest.mark.parametrize(
    "bad", ["tc-001", "TC-1", "TC-0001", "../TC-001", "TC/001", "ABCDEFGHI-001", "-001"]
)
def test_paths_still_reject_malformed_identifiers(repo: ProjectRepository, bad: str) -> None:
    """넓혔지만 **없애지 않았다** (헌법 §보안).

    식별자는 파일 이름과 디렉터리 이름이 된다. 검증을 빼면 경로 구분자와 상위 이동이
    그대로 경로가 된다.
    """
    with pytest.raises(ProjectError):
        repo.paths.run_dir(bad)
    with pytest.raises(ProjectError):
        repo.find_test_path(bad)


def test_lowercase_is_refused_so_two_ids_cannot_share_one_slot(repo: ProjectRepository) -> None:
    """대소문자를 섞어 허용하면 macOS 기본 파일 시스템에서 한 자리를 둘이 다툰다 (research R1)."""
    with pytest.raises(ProjectError):
        repo.paths.run_dir("user-001")
