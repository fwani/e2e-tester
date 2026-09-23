"""019 T034 — 가져오기 계획.

계획은 **예고**다. 무엇이 생길지 사용자가 확정 전에 알아야 하고, 그 예고가 실제와 달라지면
사용자는 본 적 없는 결과를 받는다.

**디스크를 건드리지 않는다.** 이 파일의 모든 검증이 파일 시스템 없이 돈다는 것 자체가
그 성질의 증거다.
"""

from __future__ import annotations

from sharing_support import make_test

from itb.domain.test_case import Project, TestGroup
from itb.sharing.builder import build_bundle, dump_bundle
from itb.sharing.planner import plan_import
from itb.sharing.reader import read_bundle


def _read(tests: list[str] | None = None, groups: list[TestGroup] | None = None):
    project = Project(
        name="dev-graphio",
        default_start_url="https://example.internal",
        groups=groups or [],
    )
    made = [make_test(tid, f"{tid} 테스트") for tid in (tests or ["TC-001"])]
    return read_bundle(dump_bundle(build_bundle(project, made)))


def _plan(**kwargs):
    read = kwargs.pop("read", None) or _read()
    kwargs.setdefault("target", "new")
    kwargs.setdefault("file_name", "team.itbshare.yaml")
    return plan_import(read, **kwargs)


# ─── 새 프로젝트 ───────────────────────────────────────────────────────────


def test_plan_names_every_incoming_test() -> None:
    plan = _plan(read=_read(["TC-001", "TC-002"]))
    assert [t.source_id for t in plan.tests] == ["TC-001", "TC-002"]
    assert all(t.status == "create" for t in plan.tests)


def test_empty_target_keeps_the_original_numbers() -> None:
    """빈 프로젝트로 들어가면 번호를 바꿀 이유가 없다."""
    plan = _plan(read=_read(["TC-003"]))
    assert plan.tests[0].target_id == "TC-003"
    assert plan.tests[0].renumbered is False


def test_reserved_name_is_reported_not_silent() -> None:
    """이름이 바뀌었다는 사실을 사용자가 알아야 한다 (US2 AS3)."""
    plan = _plan(reserved_project_name="dev-graphio-2")
    assert plan.target_project_name == "dev-graphio-2"
    assert plan.project_renamed_from == "dev-graphio"
    assert any(n.code == "PROJECT_RENAMED" for n in plan.notices)


def test_start_url_is_always_flagged_for_the_reader() -> None:
    """받는 쪽 환경이 다를 수 있다. 확인할 거리를 먼저 보여 준다."""
    plan = _plan()
    (notice,) = [n for n in plan.notices if n.code == "START_URL_CHECK"]
    assert "example.internal" in notice.message


def test_reimport_is_flagged() -> None:
    plan = _plan(reimported_tests=3)
    (notice,) = [n for n in plan.notices if n.code == "REIMPORT"]
    assert notice.detail == {"matched_tests": 3}


# ─── 식별자 충돌 (FR-025) ──────────────────────────────────────────────────


def test_conflicting_id_yields_to_the_incoming_test() -> None:
    """기존 테스트는 손대지 않는다. 덮어쓰기는 되돌릴 수 없는 손실이다."""
    plan = _plan(read=_read(["TC-001"]), used_numbers={"TC": {1}})
    (entry,) = plan.tests
    assert entry.source_id == "TC-001"
    assert entry.target_id == "TC-002"
    assert entry.renumbered is True


def test_renumbering_fills_the_first_free_slot() -> None:
    plan = _plan(read=_read(["TC-001"]), used_numbers={"TC": {1, 2, 4}})
    assert plan.tests[0].target_id == "TC-003"


def test_incoming_tests_do_not_collide_with_each_other() -> None:
    """한 번에 여러 건이 들어와도 같은 번호를 두 번 주지 않는다."""
    plan = _plan(read=_read(["TC-001", "TC-002"]), used_numbers={"TC": {1, 2}})
    assert sorted(t.target_id for t in plan.tests) == ["TC-003", "TC-004"]


def test_full_group_is_blocking_before_commit() -> None:
    """확정 도중 번호가 바닥나는 상태를 만들지 않는다 (research R6)."""
    plan = _plan(read=_read(["TC-001"]), used_numbers={"TC": set(range(1, 1000))})
    assert plan.blocking
    assert plan.tests[0].status == "skip"


def test_capacity_reports_room_per_group() -> None:
    plan = _plan(read=_read(["TC-001", "TC-002"]), used_numbers={"TC": {1}})
    (capacity,) = plan.capacity
    assert capacity.prefix == "TC"
    assert capacity.needed == 2
    assert capacity.available == 998
    assert capacity.ok is True


# ─── 그룹 대응 (FR-027 · research R6 표) ───────────────────────────────────


def test_same_group_name_is_reused_even_with_a_different_prefix() -> None:
    """이름이 정체성이다. 두 사람이 각자 USER·USR 로 만들었어도 같은 그룹이다."""
    read = _read(["USER-001"], groups=[TestGroup(prefix="USER", name="사용자관리")])
    plan = _plan(read=read, existing_groups=[TestGroup(prefix="USR", name="사용자관리")])
    (group,) = plan.groups
    assert group.action == "reuse"
    assert group.target_prefix == "USR"
    assert plan.tests[0].target_id.startswith("USR-")


def test_new_group_is_created_with_its_own_prefix() -> None:
    read = _read(["USER-001"], groups=[TestGroup(prefix="USER", name="사용자관리")])
    plan = _plan(read=read, existing_groups=[])
    (group,) = plan.groups
    assert group.action == "create"
    assert group.target_prefix == "USER"


def test_prefix_taken_by_another_name_gets_an_alternative() -> None:
    """접두어만 같고 이름이 다르면 다른 그룹이다. 양보하는 쪽은 들어오는 쪽이다."""
    read = _read(["USER-001"], groups=[TestGroup(prefix="USER", name="사용자관리")])
    plan = _plan(read=read, existing_groups=[TestGroup(prefix="USER", name="회원")])
    (group,) = plan.groups
    assert group.action == "create_renamed_prefix"
    assert group.target_prefix == "USER2"
    assert group.reason
    assert plan.tests[0].target_id.startswith("USER2-")


def test_ungrouped_tests_go_to_the_reserved_space() -> None:
    """`TC` 는 예약 접두어이며 그룹이 아니다."""
    plan = _plan(read=_read(["TC-001"]))
    assert plan.groups == []
    assert plan.tests[0].target_id.startswith("TC-")


# ─── 필요 값 (FR-040) ───────────────────────────────────────────────────────


def test_required_values_point_at_the_target_id() -> None:
    """재부여된 번호로 보여 주지 않으면 사용자가 그 테스트를 찾지 못한다."""
    from sharing_support import make_secret_test

    project = Project(name="p", default_start_url="https://x.test")
    read = read_bundle(dump_bundle(build_bundle(project, [make_secret_test("TC-001")])))
    plan = _plan(read=read, used_numbers={"TC": {1}})
    (value,) = plan.required_values
    assert plan.tests[0].target_id == "TC-002"
    assert [u.test_id for u in value.usages] == ["TC-002"]


def test_only_sensitive_values_block_the_run() -> None:
    """빈 비민감 값은 막지 않는다 — 빈 문자열이 유효한 입력일 수 있다 (FR-044)."""
    from sharing_support import make_secret_test

    project = Project(name="p", default_start_url="https://x.test")
    read = read_bundle(
        dump_bundle(build_bundle(project, [make_secret_test("TC-001", plain_name="LOGIN_ID")]))
    )
    plan = _plan(read=read)
    by_name = {v.name: v for v in plan.required_values}
    assert by_name["SECRET_LOGIN_PW"].blocks_run is True
    assert by_name["LOGIN_ID"].blocks_run is False


def test_secret_state_is_left_for_the_router_to_fill() -> None:
    """`itb.sharing` 은 암호문에 닿을 수 없다 (research R3)."""
    from sharing_support import make_secret_test

    project = Project(name="p", default_start_url="https://x.test")
    read = read_bundle(dump_bundle(build_bundle(project, [make_secret_test("TC-001")])))
    (value,) = _plan(read=read).required_values
    assert value.already_stored is None
    assert value.env_provided is None


# ─── 수명 ──────────────────────────────────────────────────────────────────


def test_plan_carries_an_expiry() -> None:
    plan = _plan()
    assert plan.expires_at > plan.created_at
    assert plan.expired is False
