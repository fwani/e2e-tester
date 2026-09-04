"""프로젝트 디렉터리 입출력. FR-001·FR-088b·FR-088c.

단독 로컬 도구이므로 데이터베이스 서버가 없다. 프로젝트 하나 = 디렉터리 하나다.

    <프로젝트 디렉터리>/
    ├── itb-project.yaml          # 커밋 대상
    ├── tests/TC-001-*.yaml       # 커밋 대상 — 사용자 자산
    ├── secrets.local.yaml        # .gitignore 대상
    ├── .runs/<테스트ID>/          # .gitignore 대상, 최근 1건만
    └── .gitignore                # 생성 시 자동 작성

테스트 정의만 커밋 대상이고 비밀값·실행 산출물은 제외된다. 이 분리가 FR-088b(사용자가
그대로 버전 관리에 넣을 수 있음)와 FR-089c(암호문조차 정의 파일에 넣지 않음)를 동시에
만족시킨다.
"""

from __future__ import annotations

import pathlib
import re
import shutil
from dataclasses import dataclass

from itb.domain.run_result import RunResult
from itb.domain.test_case import Project, Test
from itb.storage import atomic
from itb.storage.yaml_io import DefinitionError, dump_model, load_model

PROJECT_FILE = "itb-project.yaml"
TESTS_DIR = "tests"
RUNS_DIR = ".runs"
SECRETS_FILE = "secrets.local.yaml"
GITIGNORE_FILE = ".gitignore"

TEST_ID_RE = re.compile(r"^TC-\d{3}$")
_SLUG_STRIP = re.compile(r"[^0-9A-Za-z가-힣]+")

GITIGNORE_BODY = """\
# Interactive AI Test Builder — 자동 생성.
# 테스트 정의(tests/)는 커밋 대상이다. 아래는 커밋해서는 안 되는 것들이다.

# 민감 값 암호문 (FR-089c). 암호문 자체는 공개키로 봉인되어 있으나,
# 비밀 파일을 커밋하면 어느 변수가 존재하는지가 드러나고 키 교체 이력이 남는다.
secrets.local.yaml

# 실행 산출물 — 스크린샷·콘솔·네트워크 기록. 재생성 가능하며 민감 값 흔적이 남을 수 있다.
.runs/

# 키 (보통 프로젝트 밖 ~/.config/itb/keys 에 있으나 방어적으로 제외한다)
*.key
"""


class ProjectError(Exception):
    """프로젝트 디렉터리 관련 오류."""


class ResultUnreadableError(ProjectError):
    """결과 파일이 있는데 읽을 수 없다.

    "결과 없음" 과 **반드시 구분해야 한다**. 손상된 파일을 없는 것처럼 보고하면 사용자는
    "먼저 실행하세요" 를 보고 방금 한 실행이 사라진 줄 안다 — 헌법 §보안의 명시적 오류
    처리 요건이 막으려는 조용한 통과다.
    """


def slugify(name: str) -> str:
    """테스트 이름을 파일명 조각으로 만든다.

    경로 구분자와 제어 문자를 제거한다 — 이름이 파일명으로 쓰이므로 검증이 필수다.
    """
    slug = _SLUG_STRIP.sub("-", name).strip("-").lower()
    return slug[:60] or "test"


def validate_project_path(path: pathlib.Path) -> pathlib.Path:
    """프로젝트 경로를 검증한다 (FR-085).

    절대 경로여야 하고, 실제 디렉터리여야 한다. 상대 경로나 경로 탐색 문자를 거절한다.
    """
    if not path.is_absolute():
        msg = f"절대 경로여야 합니다: {path}"
        raise ProjectError(msg)
    if ".." in path.parts:
        msg = f"경로에 '..' 을 쓸 수 없습니다: {path}"
        raise ProjectError(msg)
    resolved = path.resolve()
    if resolved.exists() and not resolved.is_dir():
        msg = f"디렉터리가 아닙니다: {resolved}"
        raise ProjectError(msg)
    return resolved


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: pathlib.Path

    @property
    def project_file(self) -> pathlib.Path:
        return self.root / PROJECT_FILE

    @property
    def tests_dir(self) -> pathlib.Path:
        return self.root / TESTS_DIR

    @property
    def runs_dir(self) -> pathlib.Path:
        return self.root / RUNS_DIR

    @property
    def secrets_file(self) -> pathlib.Path:
        return self.root / SECRETS_FILE

    @property
    def gitignore(self) -> pathlib.Path:
        return self.root / GITIGNORE_FILE

    def run_dir(self, test_id: str) -> pathlib.Path:
        if not TEST_ID_RE.match(test_id):
            msg = f"테스트 ID 형식이 올바르지 않습니다: {test_id}"
            raise ProjectError(msg)
        return self.runs_dir / test_id

    @property
    def draft_run_dir(self) -> pathlib.Path:
        """저장 전 초안 세션의 산출물 위치.

        아직 테스트 ID 가 없는 세션도 실패 시 스크린샷·로그를 남겨야 진단할 수 있다
        (FR-052·FR-053). 테스트 ID 를 가짜로 부여해 `.runs/TC-000/` 을 만들면 목록에
        없는 테스트의 결과가 디스크에 생겨 사용자가 그것을 무엇으로 읽을지 알 수 없다.
        """
        return self.runs_dir / "_draft"


class ProjectRepository:
    """열린 프로젝트 하나에 대한 파일 입출력."""

    def __init__(self, root: pathlib.Path) -> None:
        self.paths = ProjectPaths(validate_project_path(root))

    # ─── 생성·열기 (FR-001) ─────────────────────────────────────────────────

    @classmethod
    def create(cls, root: pathlib.Path, project: Project) -> ProjectRepository:
        """새 프로젝트를 만든다. 이미 있으면 거절한다."""
        repo = cls(root)
        if repo.paths.project_file.exists():
            msg = f"이미 프로젝트가 있습니다: {repo.paths.project_file}"
            raise ProjectError(msg)
        repo.paths.root.mkdir(parents=True, exist_ok=True)
        repo.paths.tests_dir.mkdir(exist_ok=True)
        repo.write_project(project)
        repo.ensure_gitignore()
        return repo

    @classmethod
    def open(cls, root: pathlib.Path) -> ProjectRepository:
        repo = cls(root)
        if not repo.paths.project_file.exists():
            msg = (
                f"프로젝트를 찾을 수 없습니다: {repo.paths.project_file}\n"
                "이 디렉터리에 프로젝트를 새로 만들 수 있습니다."
            )
            raise ProjectError(msg)
        repo.read_project()  # 검증 목적
        return repo

    def ensure_gitignore(self) -> bool:
        """`.gitignore` 를 만들거나 빠진 항목을 덧붙인다 (FR-088b).

        이미 있는 파일을 덮어쓰지 않는다 — 사용자가 쓴 규칙을 지운다.
        """
        required = ("secrets.local.yaml", ".runs/", "*.key")
        if not self.paths.gitignore.exists():
            atomic.write_text(self.paths.gitignore, GITIGNORE_BODY)
            return True

        current = self.paths.gitignore.read_text(encoding="utf-8")
        missing = [p for p in required if p not in current]
        if not missing:
            return False
        addition = "\n# Interactive AI Test Builder — 아래 항목이 빠져 있어 덧붙였다.\n"
        addition += "".join(f"{p}\n" for p in missing)
        atomic.write_text(self.paths.gitignore, current.rstrip("\n") + "\n" + addition)
        return True

    # ─── 프로젝트 메타 ─────────────────────────────────────────────────────

    def read_project(self) -> Project:
        return load_model(self.paths.project_file, Project)

    def write_project(self, project: Project) -> None:
        dump_model(self.paths.project_file, project)

    # ─── 테스트 정의 ───────────────────────────────────────────────────────

    def test_path(self, test: Test) -> pathlib.Path:
        return self.paths.tests_dir / f"{test.id}-{slugify(test.name)}.yaml"

    def find_test_path(self, test_id: str) -> pathlib.Path | None:
        if not TEST_ID_RE.match(test_id):
            msg = f"테스트 ID 형식이 올바르지 않습니다: {test_id}"
            raise ProjectError(msg)
        matches = sorted(self.paths.tests_dir.glob(f"{test_id}-*.yaml"))
        return matches[0] if matches else None

    def list_test_paths(self) -> list[pathlib.Path]:
        if not self.paths.tests_dir.exists():
            return []
        return sorted(self.paths.tests_dir.glob("TC-*.yaml"))

    def list_tests(self) -> tuple[list[Test], list[str]]:
        """읽을 수 있는 테스트 목록과, 읽을 수 없는 파일의 사유 목록.

        깨진 파일 하나가 목록 전체를 못 보게 만들면 안 된다. 사유를 함께 돌려주어
        사용자가 그 파일만 고칠 수 있게 한다.
        """
        tests: list[Test] = []
        problems: list[str] = []
        for p in self.list_test_paths():
            try:
                tests.append(load_model(p, Test))
            except DefinitionError as exc:
                problems.append(str(exc))
        tests.sort(key=lambda t: t.id)
        return tests, problems

    def read_test(self, test_id: str) -> Test:
        p = self.find_test_path(test_id)
        if p is None:
            msg = f"테스트를 찾을 수 없습니다: {test_id}"
            raise ProjectError(msg)
        return load_model(p, Test)

    def write_test(self, test: Test) -> pathlib.Path:
        """테스트를 저장한다. 이름이 바뀌어 파일명이 달라지면 이전 파일을 지운다."""
        if not test.steps:
            msg = "Step 이 없는 테스트는 저장할 수 없습니다 (FR-029)."
            raise ProjectError(msg)
        target = self.test_path(test)
        previous = self.find_test_path(test.id)
        self.paths.tests_dir.mkdir(parents=True, exist_ok=True)
        dump_model(target, test)
        if previous is not None and previous != target:
            previous.unlink()
        return target

    def delete_test(self, test_id: str) -> bool:
        p = self.find_test_path(test_id)
        if p is None:
            return False
        p.unlink()
        run_dir = self.paths.run_dir(test_id)
        if run_dir.exists():
            shutil.rmtree(run_dir)
        return True

    # ─── 테스트 ID 부여 ───────────────────────────────────────────────────

    def allocate_test_id(self) -> str:
        """다음 테스트 ID 를 부여하고 카운터를 저장한다.

        카운터와 실제 파일을 함께 본다 — 카운터만 믿으면 파일을 손으로 옮긴 뒤 충돌한다.
        """
        project = self.read_project()
        used = {
            m.group(0)
            for p in self.list_test_paths()
            if (m := re.match(r"TC-\d{3}", p.name)) is not None
        }
        number = project.next_test_number
        while f"TC-{number:03d}" in used:
            number += 1
        if number > 999:
            msg = "테스트 ID 가 999 를 넘었습니다. 프로젝트를 나누세요."
            raise ProjectError(msg)
        test_id = f"TC-{number:03d}"
        project.next_test_number = number + 1
        self.write_project(project)
        return test_id

    # ─── 실행 결과 (테스트당 최근 1건) ────────────────────────────────────

    def result_path(self, test_id: str) -> pathlib.Path:
        return self.paths.run_dir(test_id) / "result.json"

    def read_result(self, test_id: str) -> RunResult | None:
        """실행 결과 하나를 읽는다.

        파일이 없으면 `None`. **있는데 읽을 수 없으면 `ResultUnreadableError`** 를 던진다.
        단건 조회는 손상 사실을 사용자에게 전달해야 한다 (FR-087).
        """
        p = self.result_path(test_id)
        if not p.exists():
            return None
        try:
            return RunResult.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception as exc:
            msg = (
                f"{test_id} 의 실행 결과 파일을 읽을 수 없습니다: {p.name} "
                f"({type(exc).__name__}). 다시 실행하면 새 결과로 덮어씁니다."
            )
            raise ResultUnreadableError(msg) from exc

    def try_read_result(self, test_id: str) -> tuple[RunResult | None, str | None]:
        """목록 경로용. (결과, 문제 사유) 를 돌려주고 예외를 던지지 않는다.

        깨진 결과 파일 하나가 목록 전체를 못 보게 만들면 안 된다. 대신 사유를 함께
        돌려주어 목록이 그 사실을 표시할 수 있게 한다 — `list_tests` 와 같은 방식이다.
        """
        try:
            return self.read_result(test_id), None
        except ResultUnreadableError as exc:
            return None, str(exc)

    def write_result(self, result: RunResult) -> pathlib.Path:
        """실행 결과를 저장한다. 이전 결과를 덮어쓴다 — 최근 1건만 보관한다."""
        run_dir = self.paths.run_dir(result.test_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        p = run_dir / "result.json"
        # 원자적으로 쓴다 (003 AP-042). 결과를 쓰다 끊기면 목록이 반쪽 JSON 을 만나
        # "결과를 읽을 수 없다"로 표시된다 — 이전 결과까지 함께 사라진다.
        atomic.write_text(p, result.model_dump_json(indent=2, exclude_none=False))
        return p
