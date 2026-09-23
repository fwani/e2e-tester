"""019 T081 — 그룹 대응 규칙 (research R6 표 · FR-027).

표의 네 행을 각각 확인한다. **이름이 정체성이고 접두어는 식별자용 짧은 값이다** —
두 사람이 같은 그룹을 각자 `USER`·`USR` 로 만들었을 때 이름이 같으면 같은 그룹이다.
"""

from __future__ import annotations

from sharing_support import make_test

from itb.domain.test_case import Project, TestGroup
from itb.sharing.builder import build_bundle, dump_bundle
from itb.sharing.planner import plan_import
from itb.sharing.reader import read_bundle


def _plan(incoming: list[TestGroup], existing: list[TestGroup], test_id: str = "USER-001"):
    project = Project(
        name="p", default_start_url="https://x.test", groups=incoming
    )
    read = read_bundle(dump_bundle(build_bundle(project, [make_test(test_id, "가")])))
    return plan_import(
        read, target="current", file_name="b.itbshare.yaml", existing_groups=existing
    )


USER = TestGroup(prefix="USER", name="사용자관리")


# ─── 표 1행: 같은 **이름**의 그룹이 있다 ───────────────────────────────────


def test_same_name_reuses_the_existing_prefix() -> None:
    plan = _plan([USER], [TestGroup(prefix="USR", name="사용자관리")])
    (group,) = plan.groups
    assert group.action == "reuse"
    assert group.target_prefix == "USR"
    assert plan.tests[0].target_id.startswith("USR-")


def test_same_name_and_same_prefix_is_still_reuse() -> None:
    plan = _plan([USER], [USER])
    (group,) = plan.groups
    assert group.action == "reuse"
    assert group.target_prefix == "USER"


# ─── 표 2행: 이름도 접두어도 비어 있다 ─────────────────────────────────────


def test_free_prefix_creates_the_group_as_is() -> None:
    plan = _plan([USER], [])
    (group,) = plan.groups
    assert group.action == "create"
    assert (group.target_prefix, group.target_name) == ("USER", "사용자관리")


def test_other_groups_do_not_interfere() -> None:
    plan = _plan([USER], [TestGroup(prefix="DATA", name="데이터")])
    (group,) = plan.groups
    assert group.action == "create"
    assert group.target_prefix == "USER"


# ─── 표 3행: 접두어가 **다른 이름**에 쓰이고 있다 ──────────────────────────


def test_taken_prefix_yields_an_alternative() -> None:
    plan = _plan([USER], [TestGroup(prefix="USER", name="회원")])
    (group,) = plan.groups
    assert group.action == "create_renamed_prefix"
    assert group.target_prefix == "USER2"
    assert group.reason, "왜 바뀌었는지 말해야 한다"


def test_alternative_keeps_walking_until_free() -> None:
    existing = [
        TestGroup(prefix="USER", name="회원"),
        TestGroup(prefix="USER2", name="회원2"),
        TestGroup(prefix="USER3", name="회원3"),
    ]
    plan = _plan([USER], existing)
    assert plan.groups[0].target_prefix == "USER4"


def test_alternative_respects_the_prefix_length_limit() -> None:
    """접두어는 8자까지다. 억지로 잘라 넣으면 두 그룹이 같은 접두어를 갖는다."""
    long_group = TestGroup(prefix="ABCDEFGH", name="긴 접두어")
    plan = _plan([long_group], [TestGroup(prefix="ABCDEFGH", name="다른 이름")])
    (group,) = plan.groups
    assert group.action == "create_renamed_prefix"
    assert len(group.target_prefix) <= 8


# ─── 표 4행: 그룹 없는 테스트 ──────────────────────────────────────────────


def test_reserved_prefix_is_not_a_group() -> None:
    """`TC` 는 예약 접두어이며 그룹이 아니다 (013 FR-445a)."""
    plan = _plan([], [], test_id="TC-001")
    assert plan.groups == []
    assert plan.tests[0].target_id.startswith("TC-")


def test_incoming_cannot_take_the_reserved_prefix() -> None:
    """묶음이 `TC` 를 그룹으로 들고 와도 예약 접두어를 빼앗지 못한다."""
    plan = _plan([TestGroup(prefix="TCX", name="그룹")], [], test_id="TCX-001")
    (group,) = plan.groups
    assert group.target_prefix == "TCX"


# ─── 건너뛴 그룹의 테스트 ──────────────────────────────────────────────────


def test_tests_of_a_skipped_group_are_skipped_with_a_reason() -> None:
    """접두어를 확보하지 못하면 그 그룹의 테스트도 들어갈 수 없다. **조용히 빠지지 않는다.**"""
    existing = [TestGroup(prefix="USER", name="회원")]
    existing += [TestGroup(prefix=f"USER{i}", name=f"회원{i}") for i in range(2, 100)]
    plan = _plan([USER], existing)

    (group,) = plan.groups
    assert group.action == "skip"
    assert group.reason
    assert plan.tests[0].status == "skip"
    assert plan.tests[0].reason
