"""019 T082 — 그룹 용량 (research R6 · FR-036b 와 같은 성질).

**확정 도중 번호가 바닥나는 상태를 만들지 않는다.** 그렇게 되면 절반만 들어간 프로젝트가
남고, 사용자는 무엇이 들어왔는지 세어 봐야 한다.

파일을 **읽는** 상한과 프로젝트가 **수용하는** 양은 다른 것이다 (014 limits 주석).
"""

from __future__ import annotations

from sharing_support import make_test

from itb.domain.test_case import MAX_TEST_NUMBER, Project
from itb.sharing.builder import build_bundle, dump_bundle
from itb.sharing.planner import plan_import
from itb.sharing.reader import read_bundle


def _plan(count: int, used: set[int]):
    project = Project(name="p", default_start_url="https://x.test")
    tests = [make_test(f"TC-{i:03d}", f"테스트 {i}") for i in range(1, count + 1)]
    read = read_bundle(dump_bundle(build_bundle(project, tests)))
    return plan_import(
        read,
        target="current",
        file_name="b.itbshare.yaml",
        used_numbers={"TC": used},
    )


def test_capacity_is_reported_per_group() -> None:
    plan = _plan(2, {1, 2, 3})
    (capacity,) = plan.capacity
    assert capacity.prefix == "TC"
    assert capacity.needed == 2
    assert capacity.available == MAX_TEST_NUMBER - 3
    assert capacity.ok is True


def test_full_group_blocks_before_commit() -> None:
    """**계획 단계에서** 잡힌다. 확정 도중 바닥나면 절반만 들어간 상태가 남는다."""
    plan = _plan(1, set(range(1, MAX_TEST_NUMBER + 1)))
    assert plan.blocking
    assert plan.tests[0].status == "skip"
    assert "찼습니다" in (plan.tests[0].reason or "")


def test_nearly_full_group_still_fits_what_it_can_hold() -> None:
    plan = _plan(1, set(range(1, MAX_TEST_NUMBER)))
    assert plan.blocking == []
    assert plan.tests[0].target_id == f"TC-{MAX_TEST_NUMBER:03d}"


def test_more_than_room_is_blocking() -> None:
    """들어올 것이 남은 자리보다 많으면 막는다 — 일부만 넣지 않는다."""
    plan = _plan(3, set(range(1, MAX_TEST_NUMBER)))
    assert plan.blocking
    assert not all(t.status == "create" for t in plan.tests)


def test_limit_comes_from_the_domain_not_a_copy() -> None:
    """상한을 이 기능이 새로 만들지 않는다. 출처가 하나여야 한다 (research R12)."""
    from itb.sharing import limits

    assert not hasattr(limits, "MAX_TEST_NUMBER")
