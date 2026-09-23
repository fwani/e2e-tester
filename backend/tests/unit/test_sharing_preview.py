"""019 T073 — 읽을 수 없는 테스트가 있어도 내보내기를 막지 않는다 (research R11).

깨진 파일 하나 때문에 아무것도 못 하게 되면 사용자는 그것을 고치기 전까지 갇힌다.
자기 프로젝트를 고칠 수 있는 사람은 **보내는 쪽**이므로, 빠진다는 사실만 알리고 나머지는
내보낸다 — 014 의 `_collect` 와 같은 판단이다.

**가져오기 쪽은 반대다.** 거기서는 한 건이 깨져도 전체를 거부한다 (FR-023). 받는 사람은
그 파일을 고칠 수 없기 때문이다.
"""

from __future__ import annotations

from sharing_support import click, fill, make_test

from itb.domain.test_case import Project, Variable, variable_reference
from itb.sharing.builder import review_export


def _project() -> Project:
    return Project(name="dev-graphio", default_start_url="https://example.internal")


def test_unreadable_tests_are_reported_not_fatal() -> None:
    review = review_export(
        _project(),
        [make_test("TC-001", "가")],
        unreadable=["TC-004: 정의를 읽을 수 없습니다"],
    )
    assert review.test_count == 1
    assert review.unreadable == ["TC-004: 정의를 읽을 수 없습니다"]


def test_nothing_unreadable_leaves_the_list_empty() -> None:
    review = review_export(_project(), [make_test("TC-001", "가")])
    assert review.unreadable == []


def test_plaintext_values_are_not_masked() -> None:
    """가려 놓으면 사번이 섞여 있어도 발견할 수 없다. 이 목록의 목적이 보여 주는 것이다."""
    test = make_test(
        "TC-001",
        "로그인",
        steps=[fill(1, "사번 입력", "2019-0421"), click(2, "확인")],
    )
    (row,) = review_export(_project(), [test]).plaintext_values
    assert row.value == "2019-0421"


def test_pure_reference_is_not_a_plaintext_value() -> None:
    test = make_test(
        "TC-001",
        "로그인",
        steps=[fill(1, "비밀번호", variable_reference("SECRET_PW")), click(2, "확인")],
        variables=[Variable(name="SECRET_PW", value=None, sensitive=True)],
    )
    assert review_export(_project(), [test]).plaintext_values == []


def test_group_count_follows_the_selection() -> None:
    """고른 테스트만 내보낼 때는 그 테스트가 쓰는 그룹만 센다 (data-model §2.2)."""
    from itb.domain.test_case import TestGroup

    project = Project(
        name="p",
        default_start_url="https://x.test",
        groups=[TestGroup(prefix="USER", name="사용자"), TestGroup(prefix="DATA", name="데이터")],
    )
    whole = review_export(project, [make_test("USER-001", "가")], whole_project=True)
    picked = review_export(project, [make_test("USER-001", "가")], whole_project=False)
    assert whole.group_count == 2
    assert picked.group_count == 1


def test_review_does_not_build_a_file() -> None:
    """미리보기는 바이트를 만들지 않는다 — 만들면 그 자체가 비용이고 실패 지점이다."""
    review = review_export(_project(), [make_test("TC-001", "가")])
    assert not hasattr(review, "data")
    assert review.test_count == 1
