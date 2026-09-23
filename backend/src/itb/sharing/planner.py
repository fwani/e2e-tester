"""묶음 + 대상 프로젝트 → 가져오기 계획 (기능 019 · data-model §3).

**계획은 확정의 입력이 아니라 예고다.** 무엇이 생길지 사용자에게 보여 주기 위한 것이며,
확정은 이 계획을 **다시 세운다** — 그 사이 대상 프로젝트가 바뀌었을 수 있기 때문이다.

**디스크를 건드리지 않는다.** 읽기만 한다. 확정 전에는 아무것도 만들지 않아야 하는데,
계획을 세우며 무언가 만들면 그 자체가 "만든 것" 이 된다.

**`itb.secrets` 를 임포트하지 않는다** (`.importlinter`). 「이 변수에 이미 값이 있는가」는
:attr:`PlannedValue.already_stored` 를 ``None`` 으로 둔 채 만들고, 라우터가 채운다 (R3).
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Literal

from itb.domain.test_case import (
    GROUP_PREFIX_PATTERN,
    MAX_TEST_NUMBER,
    RESERVED_PREFIX,
    Project,
    Test,
    TestGroup,
)
from itb.sharing.bundle import RequiredValue, ValueUsage
from itb.sharing.limits import SHARE_PLAN_TTL_SECONDS
from itb.sharing.reader import ReadBundle, RepairedVariable

Target = Literal["new", "current"]
GroupAction = Literal["reuse", "create", "create_renamed_prefix", "skip"]
TestStatus = Literal["create", "skip"]

_PREFIX_MAX = 8
"""그룹 접두어 길이 상한. :data:`itb.domain.test_case.GROUP_PREFIX_PATTERN` 이 정한 값이다."""


@dataclass(slots=True)
class GroupPlan:
    source_prefix: str
    source_name: str
    target_prefix: str
    target_name: str
    action: GroupAction
    reason: str | None = None


@dataclass(slots=True)
class TestPlan:
    source_id: str
    target_id: str
    name: str
    group_prefix: str
    status: TestStatus
    reason: str | None = None

    @property
    def renumbered(self) -> bool:
        return self.status == "create" and self.source_id != self.target_id


@dataclass(slots=True)
class GroupCapacity:
    prefix: str
    needed: int
    available: int

    @property
    def ok(self) -> bool:
        return self.needed <= self.available


@dataclass(slots=True)
class PlannedValue:
    """`RequiredValue` + 대상 쪽 사정 (data-model §3.3)."""

    name: str
    sensitive: bool
    declared: bool
    usages: list[ValueUsage]
    already_stored: bool | None = None
    """민감 변수일 때만 뜻이 있다. **라우터가 채운다** — 이 모듈은 암호문에 닿지 않는다."""

    env_provided: bool | None = None
    """같은 이름 환경 변수가 있는가. 있으면 값을 채우지 않아도 실행된다 (R10)."""

    @property
    def blocks_run(self) -> bool:
        """값이 없을 때 실행이 막히는가. **민감 변수만 참이다** (FR-044).

        빈 비민감 값은 막지 않는다 — 빈 문자열이 유효한 입력일 수 있고, 이것은 제품이 이미
        쓰는 판정이다 (`undefined_variable_references`).
        """
        return self.sensitive


@dataclass(slots=True)
class Notice:
    code: str
    message: str
    detail: dict[str, object] | None = None


@dataclass(slots=True)
class SharePlan:
    """확정 전에 사용자에게 보이는 예고 전체."""

    plan_id: str
    created_at: dt.datetime
    expires_at: dt.datetime
    file_name: str
    target: Target
    bundle: ReadBundle
    target_project_name: str | None = None
    project_renamed_from: str | None = None
    groups: list[GroupPlan] = field(default_factory=list)
    tests: list[TestPlan] = field(default_factory=list)
    required_values: list[PlannedValue] = field(default_factory=list)
    capacity: list[GroupCapacity] = field(default_factory=list)
    repaired: list[RepairedVariable] = field(default_factory=list)
    notices: list[Notice] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)

    @property
    def expired(self) -> bool:
        return dt.datetime.now(dt.UTC) >= self.expires_at


# ─── 그룹 대응 (research R6) ────────────────────────────────────────────────


def _alternative_prefix(base: str, taken: set[str]) -> str | None:
    """접두어가 다른 이름에 쓰이고 있을 때의 대체 이름 (`USER` → `USER2` → …).

    8자 상한 안에서 찾는다. 찾지 못하면 ``None`` — 그 그룹은 건너뛰고 사유를 보고한다.
    억지로 잘라 넣으면 서로 다른 그룹이 같은 접두어를 갖게 된다.
    """
    import re

    for suffix in range(2, 100):
        tail = str(suffix)
        stem = base[: _PREFIX_MAX - len(tail)]
        candidate = f"{stem}{tail}"
        if candidate not in taken and re.fullmatch(GROUP_PREFIX_PATTERN, candidate):
            return candidate
    return None


def _plan_groups(
    incoming: list[TestGroup], existing: list[TestGroup]
) -> tuple[list[GroupPlan], dict[str, str]]:
    """묶음의 그룹을 대상 프로젝트에 대응시킨다 (FR-027 · research R6 표).

    **이름이 정체성이다.** 두 사람이 같은 그룹을 각자 `USER`·`USR` 로 만들었을 때, 이름이
    같으면 같은 그룹으로 보는 것이 사용자의 기대에 맞는다. 반대로 접두어만 같고 이름이
    다르면 다른 그룹이고, 접두어를 양보하는 쪽은 **들어오는 쪽**이다.

    돌려주는 사전은 ``묶음 접두어 → 대상 접두어`` 다. 건너뛴 그룹은 들어 있지 않다.
    """
    by_name = {g.name: g for g in existing}
    taken = {g.prefix for g in existing} | {RESERVED_PREFIX}

    plans: list[GroupPlan] = []
    mapping: dict[str, str] = {}

    for group in incoming:
        same_name = by_name.get(group.name)
        if same_name is not None:
            plans.append(
                GroupPlan(
                    source_prefix=group.prefix,
                    source_name=group.name,
                    target_prefix=same_name.prefix,
                    target_name=same_name.name,
                    action="reuse",
                )
            )
            mapping[group.prefix] = same_name.prefix
            continue

        if group.prefix not in taken:
            taken.add(group.prefix)
            plans.append(
                GroupPlan(
                    source_prefix=group.prefix,
                    source_name=group.name,
                    target_prefix=group.prefix,
                    target_name=group.name,
                    action="create",
                )
            )
            mapping[group.prefix] = group.prefix
            continue

        alternative = _alternative_prefix(group.prefix, taken)
        if alternative is None:
            plans.append(
                GroupPlan(
                    source_prefix=group.prefix,
                    source_name=group.name,
                    target_prefix=group.prefix,
                    target_name=group.name,
                    action="skip",
                    reason=(
                        f"접두어 {group.prefix} 가 이미 다른 그룹의 것이고, "
                        "대체 접두어를 만들지 못했습니다."
                    ),
                )
            )
            continue

        taken.add(alternative)
        plans.append(
            GroupPlan(
                source_prefix=group.prefix,
                source_name=group.name,
                target_prefix=alternative,
                target_name=group.name,
                action="create_renamed_prefix",
                reason=(
                    f"접두어 {group.prefix} 가 이미 다른 그룹의 것이라 "
                    f"{alternative} 로 만듭니다."
                ),
            )
        )
        mapping[group.prefix] = alternative

    return plans, mapping


# ─── 식별자 재부여 (research R6) ────────────────────────────────────────────


def _group_prefix(test_id: str) -> str:
    return test_id.split("-", 1)[0]


def _number(test_id: str) -> int:
    try:
        return int(test_id.split("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _plan_tests(
    tests: list[Test],
    *,
    group_map: dict[str, str],
    used: dict[str, set[int]],
) -> tuple[list[TestPlan], list[GroupCapacity]]:
    """들어오는 테스트에 대상 식별자를 준다.

    **겹치면 들어오는 쪽이 양보한다** (FR-025). 기존 테스트는 손대지 않는다 — 덮어쓰기는
    되돌릴 수 없는 손실이다.

    번호는 :meth:`itb.storage.repository.ProjectRepository.allocate_test_id` 와 같은
    규칙을 쓴다 — 그룹마다 1번부터, 빈 번호를 채운다. 저장소를 부르지 않는 이유는 **계획
    단계가 디스크를 건드리지 않아야** 하고, 여러 건을 한꺼번에 배치하려면 이미 배치한
    번호까지 세어야 하기 때문이다.
    """
    taken = {prefix: set(numbers) for prefix, numbers in used.items()}
    needed: dict[str, int] = {}
    plans: list[TestPlan] = []

    for test in tests:
        source_prefix = _group_prefix(test.id)
        if source_prefix == RESERVED_PREFIX:
            target_prefix: str | None = RESERVED_PREFIX
        else:
            target_prefix = group_map.get(source_prefix)

        if target_prefix is None:
            plans.append(
                TestPlan(
                    source_id=test.id,
                    target_id=test.id,
                    name=test.name,
                    group_prefix=source_prefix,
                    status="skip",
                    reason=f"그룹 {source_prefix} 를 만들지 못해 건너뜁니다.",
                )
            )
            continue

        needed[target_prefix] = needed.get(target_prefix, 0) + 1
        pool = taken.setdefault(target_prefix, set())

        wanted = _number(test.id)
        number = wanted if wanted and wanted not in pool else 1
        while number in pool:
            number += 1

        if number > MAX_TEST_NUMBER:
            plans.append(
                TestPlan(
                    source_id=test.id,
                    target_id=test.id,
                    name=test.name,
                    group_prefix=target_prefix,
                    status="skip",
                    reason=f"「{target_prefix}」 그룹의 번호가 모두 찼습니다.",
                )
            )
            continue

        pool.add(number)
        plans.append(
            TestPlan(
                source_id=test.id,
                target_id=f"{target_prefix}-{number:03d}",
                name=test.name,
                group_prefix=target_prefix,
                status="create",
            )
        )

    capacity = [
        GroupCapacity(
            prefix=prefix,
            needed=count,
            available=MAX_TEST_NUMBER - len(used.get(prefix, set())),
        )
        for prefix, count in sorted(needed.items())
    ]
    return plans, capacity


# ─── 필요 값 (FR-040) ───────────────────────────────────────────────────────


def _plan_values(
    required: list[RequiredValue], id_map: dict[str, str]
) -> list[PlannedValue]:
    """쓰이는 자리를 **대상 식별자 기준**으로 고쳐 쓴다.

    재부여된 번호로 보여 주지 않으면 사용자가 그 테스트를 찾지 못한다. 목록에는
    `TC-001` 이라고 적혀 있는데 화면에는 `TC-007` 만 있는 상태가 된다.

    건너뛴 테스트에서만 쓰이던 값은 목록에서 빠진다 — 채워도 쓰일 데가 없다.
    """
    out: list[PlannedValue] = []
    for value in required:
        usages = [
            ValueUsage(
                test_id=id_map[u.test_id],
                step_id=u.step_id,
                step_label=u.step_label,
                field=u.field,
            )
            for u in value.usages
            if u.test_id in id_map
        ]
        if not usages:
            continue
        out.append(
            PlannedValue(
                name=value.name,
                sensitive=value.sensitive,
                declared=value.declared,
                usages=usages,
            )
        )
    return out


# ─── 계획 세우기 ───────────────────────────────────────────────────────────


def plan_import(
    read: ReadBundle,
    *,
    target: Target,
    file_name: str,
    existing_project: Project | None = None,
    existing_groups: list[TestGroup] | None = None,
    used_numbers: dict[str, set[int]] | None = None,
    reserved_project_name: str | None = None,
    reimported_tests: int = 0,
    now: dt.datetime | None = None,
) -> SharePlan:
    """무엇이 생길지 예고한다. **디스크를 건드리지 않는다.**

    ``reserved_project_name`` 은 `new` 일 때 호출자가 미리 확보한 이름이다 — 실제 디렉터리
    이름 충돌 회피는 :func:`itb.storage.paths.allocate_workspace_path` 가 알고 있고, 그것은
    파일 시스템을 본다. 이 모듈이 그것을 부르지 않는 이유는 계획 단계를 순수하게 두기
    위해서다.
    """
    stamp = now or dt.datetime.now(dt.UTC)

    groups, group_map = _plan_groups(
        list(read.bundle.project.groups),
        list(existing_groups or []),
    )
    tests, capacity = _plan_tests(
        read.tests,
        group_map=group_map,
        used=used_numbers or {},
    )

    id_map = {t.source_id: t.target_id for t in tests if t.status == "create"}
    values = _plan_values(read.required_values, id_map)

    incoming_name = read.bundle.project.name
    final_name = reserved_project_name or incoming_name

    notices: list[Notice] = []
    start_url = (
        existing_project.default_start_url
        if target == "current" and existing_project is not None
        else read.bundle.project.default_start_url
    )
    notices.append(
        Notice(
            code="START_URL_CHECK",
            message=(
                f"시작 주소가 {start_url} 입니다. 이 환경에 접근할 수 있는지 확인하세요."
            ),
            detail={"url": start_url},
        )
    )
    if target == "new" and final_name != incoming_name:
        notices.append(
            Notice(
                code="PROJECT_RENAMED",
                message=(
                    f"같은 이름의 프로젝트가 이미 있어 「{final_name}」 으로 만듭니다. "
                    "기존 프로젝트는 그대로 둡니다."
                ),
                detail={"from": incoming_name, "to": final_name},
            )
        )
    if reimported_tests:
        notices.append(
            Notice(
                code="REIMPORT",
                message="같은 묶음을 이미 가져온 적이 있습니다. 그대로 진행하면 또 만들어집니다.",
                detail={"matched_tests": reimported_tests},
            )
        )
    if read.repaired:
        notices.append(
            Notice(
                code="VARIABLES_REPAIRED",
                message=(
                    f"변수 선언이 없어 {len(read.repaired)}건을 보충했습니다. "
                    "채워야 할 값 목록에서 확인하세요."
                ),
                detail={"count": len(read.repaired)},
            )
        )

    blocking: list[str] = []
    blocking += [f"{c.prefix} 그룹에 자리가 부족합니다." for c in capacity if not c.ok]
    if not id_map:
        blocking.append("만들 수 있는 테스트가 하나도 없습니다.")

    return SharePlan(
        plan_id=uuid.uuid4().hex,
        created_at=stamp,
        expires_at=stamp + dt.timedelta(seconds=SHARE_PLAN_TTL_SECONDS),
        file_name=file_name,
        target=target,
        bundle=read,
        target_project_name=final_name if target == "new" else None,
        project_renamed_from=(
            incoming_name if target == "new" and final_name != incoming_name else None
        ),
        groups=groups,
        tests=tests,
        required_values=values,
        capacity=capacity,
        repaired=list(read.repaired),
        notices=notices,
        blocking=blocking,
    )
