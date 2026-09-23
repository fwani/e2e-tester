"""계획 확정 → 결과 (기능 019 · research R5).

**전부 성공하거나 아무것도 만들지 않는다** (FR-024). 두 경로가 원자성을 얻는 방법이 다르다.

- **새 프로젝트**: 임시 디렉터리에 완성한 뒤 :func:`os.replace` 로 최종 자리에 옮긴다.
  같은 파일 시스템 안에서 원자적이다. 레지스트리 등록은 **옮기기가 성공한 뒤**에 한다 —
  순서가 반대면 목록에 있는데 없는 프로젝트가 생긴다.
- **기존 프로젝트**: :func:`itb.storage.test_moves.run_all` 로 쓰고, 실패하면 되돌린다.
  013 의 테스트 이동이 같은 문제를 풀며 만든 것이고, 되돌리지 못한 경우를 별도 예외로
  구분하는 부분까지 우리가 필요로 하는 모양이다.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import os
import pathlib
import shutil
from dataclasses import dataclass, field

from pydantic import ValidationError

from itb.domain.test_case import ImportProvenance, Project, Test, TestGroup
from itb.sharing.planner import PlannedValue, SharePlan
from itb.storage import registry
from itb.storage.paths import allocate_workspace_path
from itb.storage.repository import ProjectError, ProjectRepository
from itb.storage.test_moves import AllOrNothingError, PartialFailureError, run_all


@dataclass(slots=True)
class CreatedTest:
    target_id: str
    source_id: str
    name: str
    group_prefix: str


@dataclass(slots=True)
class Renumbered:
    from_id: str
    to_id: str


@dataclass(slots=True)
class Skipped:
    source_id: str
    reason: str


@dataclass(slots=True)
class ShareReport:
    """확정 뒤 한 번 만들어져 응답으로만 나간다. 저장하지 않는다."""

    project_root: str
    project_name: str
    project_renamed_from: str | None = None
    created_tests: list[CreatedTest] = field(default_factory=list)
    renumbered: list[Renumbered] = field(default_factory=list)
    created_groups: list[TestGroup] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)
    required_values: list[PlannedValue] = field(default_factory=list)
    notices: list[object] = field(default_factory=list)
    repaired_variables: list[object] = field(default_factory=list)


class ApplyError(Exception):
    """확정에 실패했고 **되돌렸다.** 대상 프로젝트는 요청 전과 같다."""


class ApplyPartialError(ApplyError):
    """확정에 실패했고 **되돌리지도 못했다.** 무엇이 남았는지 ``stranded`` 가 말한다."""

    def __init__(self, message: str, stranded: list[str]) -> None:
        super().__init__(message)
        self.stranded = stranded


def _prepared_tests(
    plan: SharePlan,
    *,
    variable_values: dict[str, str] | None,
) -> list[tuple[Test, str]]:
    """저장할 테스트와 그 소속 접두어.

    세 가지를 바꾼다.

    1. **식별자** — 계획이 정한 대상 번호
    2. **출처 표시** — 어느 묶음에서 언제 왔는지, 원래 번호는 무엇이었는지 (FR-028)
    3. **비민감 변수 값** — 사용자가 확정 화면에서 채운 것 (FR-048)

    민감 값은 여기서 다루지 않는다. 그것은 `secrets.local.yaml` 로 가고 봉인 경로는
    `PUT /api/secrets/{name}` 하나뿐이다.
    """
    by_source = {t.source_id: t for t in plan.tests if t.status == "create"}
    fillable = {v.name for v in plan.required_values if not v.sensitive}
    filled = {
        name: value for name, value in (variable_values or {}).items() if name in fillable
    }
    """**채울 목록에 오른 비민감 변수만** 받는다.

    두 가지를 막는다. ① 클라이언트가 임의의 이름을 보내 값이 있던 변수를 갈아 끼우는 것
    ② 민감 변수가 평문으로 정의에 들어가는 것 — 라우터가 앞에서 거절하지만, 여기서도
    자리를 막아 두 곳 중 하나만 고쳐지는 날을 없앤다.
    """

    stamp = dt.datetime.now(dt.UTC)

    out: list[tuple[Test, str]] = []
    for test in plan.bundle.tests:
        entry = by_source.get(test.id)
        if entry is None:
            continue

        # **값이 비어 있는 변수에만 채운다.** 같은 이름이 다른 테스트에서 값을 갖고 있을 수
        # 있고(그래서 채울 목록에는 올랐다), 그 값을 이 입력으로 갈아 끼우면 사용자가 손댄
        # 적 없는 테스트가 조용히 바뀐다.
        variables = [
            var.model_copy(update={"value": filled[var.name]})
            if not var.sensitive and not var.value and var.name in filled
            else var
            for var in test.variables
        ]
        prepared = test.model_copy(
            update={
                "id": entry.target_id,
                "variables": variables,
                "imported_from": ImportProvenance(
                    source_file=plan.file_name,
                    imported_at=stamp,
                    original_id=test.id,
                ),
                "updated_at": stamp,
            }
        )
        # `model_copy` 는 검증을 다시 돌리지 않는다. 검증 없이 저장하면 **읽을 수 없는
        # 정의 파일**이 만들어지고(예: 상한을 넘는 값), 가져오기는 성공을 보고한다.
        try:
            prepared = Test.model_validate(prepared.model_dump(mode="json"))
        except ValidationError as exc:
            msg = f"{test.id} 의 값을 저장할 수 없습니다: {_first_message(exc)}"
            raise ApplyError(msg) from exc
        out.append((prepared, entry.group_prefix))
    return out


def _first_message(exc: ValidationError) -> str:
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first.get("loc", ()))
    return f"{where}: {first.get('msg', '')}" if where else str(first.get("msg", ""))


def _report(
    plan: SharePlan,
    repo: ProjectRepository,
    prepared: list[tuple[Test, str]],
    created_groups: list[TestGroup],
) -> ShareReport:
    by_target = {t.target_id: t for t in plan.tests if t.status == "create"}
    project = repo.read_project()
    return ShareReport(
        project_root=str(repo.paths.root),
        project_name=project.name,
        project_renamed_from=plan.project_renamed_from,
        created_tests=[
            CreatedTest(
                target_id=test.id,
                source_id=by_target[test.id].source_id,
                name=test.name,
                group_prefix=prefix,
            )
            for test, prefix in prepared
        ],
        renumbered=[
            Renumbered(from_id=t.source_id, to_id=t.target_id)
            for t in plan.tests
            if t.renumbered
        ],
        created_groups=created_groups,
        skipped=[
            Skipped(source_id=t.source_id, reason=t.reason or "건너뛰었습니다.")
            for t in plan.tests
            if t.status == "skip"
        ],
        required_values=plan.required_values,
        notices=list(plan.notices),
        repaired_variables=list(plan.repaired),
    )


def _groups_to_create(plan: SharePlan, existing: list[TestGroup]) -> list[TestGroup]:
    have = {g.prefix for g in existing}
    return [
        TestGroup(prefix=g.target_prefix, name=g.target_name)
        for g in plan.groups
        if g.action in ("create", "create_renamed_prefix") and g.target_prefix not in have
    ]


# ─── 새 프로젝트 (US2) ──────────────────────────────────────────────────────


def apply_new_project(
    plan: SharePlan,
    *,
    project_name: str,
    default_start_url: str | None = None,
    variable_values: dict[str, str] | None = None,
    workspace: pathlib.Path | None = None,
) -> ShareReport:
    """새 프로젝트를 만들어 묶음을 복원한다 (FR-020).

    **임시 디렉터리에 완성한 뒤 옮긴다** (research R5). 바로 최종 자리에 쓰면, 쓰는 도중
    서버가 죽었을 때 반쯤 만들어진 프로젝트가 목록에 남는다.

    레지스트리 등록은 **마지막**이다. 먼저 등록하면 옮기기가 실패했을 때 목록에 있는데
    없는 프로젝트가 생긴다.
    """
    final = allocate_workspace_path(project_name, workspace)
    staging = final.with_name(f".{final.name}.importing")
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)

    incoming = plan.bundle.bundle.project
    project = Project(
        name=project_name,
        default_start_url=default_start_url or incoming.default_start_url,
        browser=incoming.browser,
        test_id_attribute=incoming.test_id_attribute,
        max_tabs=incoming.max_tabs,
        groups=[
            TestGroup(prefix=g.target_prefix, name=g.target_name)
            for g in plan.groups
            if g.action != "skip"
        ],
    )

    try:
        repo = ProjectRepository.create(staging, project)
        prepared = _prepared_tests(plan, variable_values=variable_values)
        for test, _prefix in prepared:
            repo.write_test(test)
    except Exception as exc:  # noqa: BLE001 — 무엇이든 임시 자리를 치우고 사유를 나른다
        # **무엇이 터지든 임시 자리를 치운다.** 좁게 잡으면 예상 못 한 예외에서
        # `.<이름>.importing` 이 남고, 다음 가져오기의 이름 충돌 계산에까지 끼어든다.
        shutil.rmtree(staging, ignore_errors=True)
        if isinstance(exc, ApplyError):
            raise
        msg = f"프로젝트를 만들지 못했습니다: {exc}. 아무것도 만들어지지 않았습니다."
        raise ApplyError(msg) from exc

    try:
        os.replace(staging, final)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        msg = f"프로젝트를 제자리에 놓지 못했습니다: {exc}. 아무것도 만들어지지 않았습니다."
        raise ApplyError(msg) from exc

    # **여기서 등록한다.** 옮기기가 끝난 뒤여야 목록과 디스크가 어긋나지 않는다.
    with contextlib.suppress(OSError):
        registry.remember(final, project_name, origin="managed")

    try:
        moved = ProjectRepository.open(final)
        return _report(plan, moved, prepared, project.groups)
    except Exception as exc:  # noqa: BLE001 — 자산은 이미 제자리에 있다
        # **여기서는 되돌리지 않는다.** `os.replace` 가 끝났으므로 프로젝트는 완성된 채
        # 제자리에 있고, 지우면 방금 만든 사용자 자산을 파괴하는 것이 된다. 「만들어졌지만
        # 결과를 읽지 못했다」를 그대로 말한다 — 사용자는 목록에서 그것을 열면 된다.
        msg = (
            f"프로젝트를 만들었지만 결과를 읽지 못했습니다: {exc} "
            "목록에서 확인하세요."
        )
        raise ApplyPartialError(msg, [str(final)]) from exc


# ─── 기존 프로젝트 (US5) ────────────────────────────────────────────────────


def apply_current_project(
    plan: SharePlan,
    repo: ProjectRepository,
    *,
    variable_values: dict[str, str] | None = None,
) -> ShareReport:
    """열린 프로젝트에 테스트를 더한다 (FR-021).

    **그룹을 테스트보다 먼저 쓴다.** 반대 순서면 그룹 없는 접두어를 가진 테스트가 잠시
    존재한다. 실패하면 프로젝트 파일도 되돌린다.
    """
    project = repo.read_project()
    new_groups = _groups_to_create(plan, project.groups)
    prepared = _prepared_tests(plan, variable_values=variable_values)

    if new_groups:
        try:
            merged = [*project.groups, *new_groups]
            repo.write_project(project.model_copy(update={"groups": merged}))
        except (ProjectError, OSError, ValueError) as exc:
            msg = f"그룹을 만들지 못했습니다: {exc}. 아무것도 만들어지지 않았습니다."
            raise ApplyError(msg) from exc

    def validate(item: tuple[Test, str]) -> None:
        test, _prefix = item
        if repo.find_test_path(test.id) is not None:
            msg = f"이미 있는 식별자입니다: {test.id}"
            raise ProjectError(msg)

    def do(item: tuple[Test, str]) -> pathlib.Path:
        test, _prefix = item
        return repo.write_test(test)

    def undo(_item: tuple[Test, str], written: pathlib.Path) -> None:
        written.unlink(missing_ok=True)

    try:
        run_all(prepared, validate=validate, do=do, undo=undo)
    except PartialFailureError as exc:
        _restore_groups(repo, project, new_groups)
        raise ApplyPartialError(str(exc), [str(p) for p in exc.stranded]) from exc
    except (AllOrNothingError, ProjectError, OSError) as exc:
        _restore_groups(repo, project, new_groups)
        msg = f"{exc} 아무것도 만들어지지 않았습니다."
        raise ApplyError(msg) from exc

    return _report(plan, repo, prepared, new_groups)


def _restore_groups(
    repo: ProjectRepository, before: Project, added: list[TestGroup]
) -> None:
    """테스트 쓰기가 실패했으면 그룹도 되돌린다.

    되돌리지 못해도 **여기서 터지지 않는다.** 호출자는 이미 실패를 나르는 중이고, 여기서
    새 예외를 올리면 원래 사유가 사라진다. 남은 빈 그룹은 사용자가 지울 수 있다.
    """
    if not added:
        return
    with contextlib.suppress(Exception):
        repo.write_project(before)
