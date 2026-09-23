"""019 코드 리뷰가 잡은 결함의 회귀 검증.

전부 **조용한 손실**이었다 — 실패하지 않고, 사용자에게 보고되지 않고, 나중에 발견된다.
그래서 각 항목이 "무엇이 사라지는가" 를 직접 단언한다.
"""

from __future__ import annotations

import yaml
from sharing_support import click, fill, make_test

from itb.domain.test_case import Project, Variable, variable_reference
from itb.secrets.readiness import assess
from itb.sharing.builder import build_bundle, dump_bundle, review_export
from itb.sharing.bundle import collect_required_values
from itb.sharing.reader import InvalidTestError, read_bundle


def _project() -> Project:
    return Project(name="p", default_start_url="https://x.test")


def _with_ids(*ids: str) -> bytes:
    """같은 식별자를 둘 이상 가진 묶음. 두 묶음을 손으로 이어 붙이면 이 모양이 된다."""
    tests = [make_test(f"TC-{i:03d}", f"테스트 {i}") for i in range(1, len(ids) + 1)]
    raw = yaml.safe_load(dump_bundle(build_bundle(_project(), tests)))
    for entry, wanted in zip(raw["tests"], ids, strict=True):
        entry["id"] = wanted
    return yaml.safe_dump(raw, sort_keys=False, allow_unicode=True).encode("utf-8")


# ─── A1: 중복 식별자 ───────────────────────────────────────────────────────


def test_duplicate_test_ids_are_rejected() -> None:
    """겹치면 하나가 **조용히 사라진다** — 계획과 확정이 source_id 를 키로 쓰기 때문이다.

    계획은 2건을 예고하고 결과는 2건을 만들었다고 말하는데, 디스크에는 1건만 남는다.
    """
    try:
        read_bundle(_with_ids("TC-001", "TC-001"))
    except InvalidTestError as exc:
        assert any("TC-001" in p for p in exc.problems)
    else:
        raise AssertionError("중복 식별자가 통과했다 — 테스트 하나가 사라진다")


def test_distinct_ids_still_pass() -> None:
    bundle = read_bundle(_with_ids("TC-001", "TC-002"))
    assert [t.id for t in bundle.tests] == ["TC-001", "TC-002"]


# ─── A2: 채운 값이 다른 테스트의 값을 덮어쓴다 ────────────────────────────


def _two_tests_sharing_a_name():
    """같은 변수 이름을 쓰되 한쪽만 값이 비어 있다."""
    empty = make_test(
        "TC-001",
        "빈 쪽",
        steps=[fill(1, "입력", variable_reference("A")), click(2, "확인")],
        variables=[Variable(name="A", value="", sensitive=False)],
    )
    filled = make_test(
        "TC-002",
        "값 있는 쪽",
        steps=[fill(1, "입력", variable_reference("A")), click(2, "확인")],
        variables=[Variable(name="A", value="keep", sensitive=False)],
    )
    return empty, filled


def test_filling_a_value_does_not_touch_tests_that_already_have_one() -> None:
    """사용자가 손댄 적 없는 테스트가 조용히 바뀌면 안 된다."""
    from itb.sharing.applier import _prepared_tests
    from itb.sharing.planner import plan_import

    empty, filled = _two_tests_sharing_a_name()
    read = read_bundle(dump_bundle(build_bundle(_project(), [empty, filled])))
    plan = plan_import(read, target="new", file_name="b.itbshare.yaml")

    prepared = _prepared_tests(plan, variable_values={"A": "new"})
    by_id = {t.id: {v.name: v.value for v in t.variables} for t, _p in prepared}

    assert by_id["TC-001"]["A"] == "new", "빈 값은 채워져야 한다"
    assert by_id["TC-002"]["A"] == "keep", "값이 있던 쪽이 덮어써졌다"


def test_unknown_variable_names_are_ignored() -> None:
    """채울 목록에 없는 이름을 보내면 무시한다 — 임의 이름으로 값을 갈아 끼울 수 없다."""
    from itb.sharing.applier import _prepared_tests
    from itb.sharing.planner import plan_import

    empty, filled = _two_tests_sharing_a_name()
    read = read_bundle(dump_bundle(build_bundle(_project(), [empty, filled])))
    plan = plan_import(read, target="new", file_name="b.itbshare.yaml")

    prepared = _prepared_tests(plan, variable_values={"없는변수": "x", "A": "new"})
    names = {v.name for t, _p in prepared for v in t.variables}
    assert "없는변수" not in names


# ─── A3: 검증을 건너뛴 값이 읽을 수 없는 파일을 만든다 ────────────────────


def test_oversized_value_is_refused_before_it_reaches_disk() -> None:
    """`model_copy` 는 재검증하지 않는다. 그대로 쓰면 **다음에 못 읽는 정의**가 남는다."""
    from itb.sharing.applier import ApplyError, _prepared_tests
    from itb.sharing.planner import plan_import

    empty, _filled = _two_tests_sharing_a_name()
    read = read_bundle(dump_bundle(build_bundle(_project(), [empty])))
    plan = plan_import(read, target="new", file_name="b.itbshare.yaml")

    try:
        _prepared_tests(plan, variable_values={"A": "x" * 5000})
    except ApplyError as exc:
        assert "TC-001" in str(exc)
    else:
        raise AssertionError("상한을 넘는 값이 통과했다 — 저장 뒤 읽을 수 없게 된다")


# ─── B5: 채울 목록과 실행 차단의 기준이 같아야 한다 ──────────────────────


def test_unreferenced_secret_does_not_block_the_run() -> None:
    """선언만 있고 어느 스텝도 쓰지 않는 민감 변수로 막으면 **안내 없는 차단**이 된다.

    「채워야 할 값」 목록이 그 변수를 담지 않기 때문이다 — 사용자는 무엇을 채워야 하는지
    어디서도 듣지 못한 채 막힌다.
    """
    orphan = make_test(
        "TC-001",
        "쓰이지 않는 민감 변수",
        steps=[click(1, "확인")],
        variables=[Variable(name="SECRET_OLD", value=None, sensitive=True)],
    )
    assert collect_required_values([orphan]) == []
    assert assess(orphan, None, key_available=True, env={}).missing_secrets == []


def test_referenced_secret_still_blocks() -> None:
    used = make_test(
        "TC-001",
        "쓰이는 민감 변수",
        steps=[fill(1, "비밀번호", variable_reference("SECRET_PW")), click(2, "확인")],
        variables=[Variable(name="SECRET_PW", value=None, sensitive=True)],
    )
    assert [v.name for v in collect_required_values([used])] == ["SECRET_PW"]
    assert assess(used, None, key_available=True, env={}).missing_secrets == ["SECRET_PW"]


# ─── C3: 참조만으로 이루어진 값은 평문이 아니다 ──────────────────────────


def test_value_made_only_of_references_is_not_plaintext() -> None:
    """`{{A}}{{B}}` 에는 평문이 한 글자도 없다. 목록이 시끄러우면 발견율이 떨어진다."""
    test = make_test(
        "TC-001",
        "참조 둘",
        steps=[
            fill(1, "입력", f"{variable_reference('A')}{variable_reference('B')}"),
            click(2, "확인"),
        ],
        variables=[
            Variable(name="A", value="x", sensitive=False),
            Variable(name="B", value="y", sensitive=False),
        ],
    )
    assert review_export(_project(), [test]).plaintext_values == []


def test_reference_mixed_with_text_is_plaintext() -> None:
    """`https://사내주소/{{ID}}/detail` 의 앞부분은 나가는 정보다."""
    test = make_test(
        "TC-001",
        "섞임",
        steps=[
            fill(1, "입력", f"internal.test/{variable_reference('ID')}"),
            click(2, "확인"),
        ],
        variables=[Variable(name="ID", value="42", sensitive=False)],
    )
    (row,) = review_export(_project(), [test]).plaintext_values
    assert "internal.test" in row.value
