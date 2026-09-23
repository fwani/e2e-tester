"""019 T033 (C11) — 선언 없는 변수 참조는 거부가 아니라 보충이다 (FR-047).

`Test._check_refs` 는 선언 없는 참조를 거부한다. 손으로 편집된 묶음이 그것에 걸리면
사용자는 「무엇을 고쳐야 하는지」 대신 「읽을 수 없다」만 받는다.

**보충은 없는 값을 지어내는 것이 아니라 빈 자리를 드러내는 것이다.** 채우는 것은 사용자이며,
민감 변수라면 채우기 전까지 실행이 막힌다 (FR-044).
"""

from __future__ import annotations

import datetime as dt

import yaml
from sharing_support import click, fill, make_test

from itb.domain.test_case import Project
from itb.sharing.builder import build_bundle, dump_bundle
from itb.sharing.reader import read_bundle


def _project() -> Project:
    return Project(name="dev-graphio", default_start_url="https://example.internal")


def _bundle_with_undeclared(*names: str) -> bytes:
    """참조는 있고 선언은 없는 묶음을 만든다 — 손으로 편집된 파일의 모양이다.

    정상 경로로는 만들 수 없다(도메인이 막는다). 선언을 붙여 만든 뒤 **직렬화된 YAML 에서**
    변수 목록을 비운다. 줄 단위로 자르지 않고 문서로 읽어 고치는 이유는, 줄 자르기가
    들여쓰기 한 칸 차이로 조용히 깨진 YAML 을 만들기 때문이다.
    """
    from itb.domain.test_case import Variable, variable_reference

    steps = [fill(i, f"입력 {i}", variable_reference(n)) for i, n in enumerate(names, start=1)]
    steps.append(click(len(names) + 1, "확인"))
    test = make_test(
        "TC-001",
        "로그인",
        steps=steps,
        variables=[
            Variable(name=n, value=None, sensitive=n.startswith("SECRET_")) for n in names
        ],
    )
    bundle = build_bundle(_project(), [test], created_at=dt.datetime(2026, 9, 23, tzinfo=dt.UTC))
    raw = yaml.safe_load(dump_bundle(bundle).decode("utf-8"))
    for entry in raw["tests"]:
        entry["variables"] = []
    raw["required_values"] = []
    return yaml.safe_dump(raw, sort_keys=False, allow_unicode=True).encode("utf-8")


# ─── 거부하지 않는다 ───────────────────────────────────────────────────────


def test_undeclared_reference_is_not_rejected() -> None:
    bundle = read_bundle(_bundle_with_undeclared("SECRET_LOGIN_PW"))
    assert [t.id for t in bundle.tests] == ["TC-001"]


def test_repaired_declaration_appears_on_the_test() -> None:
    bundle = read_bundle(_bundle_with_undeclared("SECRET_LOGIN_PW"))
    (var,) = bundle.tests[0].variables
    assert var.name == "SECRET_LOGIN_PW"
    assert var.sensitive is True
    assert var.value is None


# ─── 무엇으로 보충하는가 ───────────────────────────────────────────────────


def test_secret_prefix_becomes_sensitive() -> None:
    """이름이 판단 근거다. 다른 근거가 파일에 남아 있지 않다."""
    bundle = read_bundle(_bundle_with_undeclared("SECRET_LOGIN_PW"))
    assert bundle.tests[0].variables[0].sensitive is True


def test_other_names_become_empty_plain_variables() -> None:
    """비민감으로 보충하고 값을 비워 둔다 — 사용자가 채울 자리다 (FR-048)."""
    bundle = read_bundle(_bundle_with_undeclared("LOGIN_ID"))
    (var,) = bundle.tests[0].variables
    assert var.sensitive is False
    assert var.value == ""


def test_mixed_names_are_split_by_prefix() -> None:
    bundle = read_bundle(_bundle_with_undeclared("SECRET_PW", "LOGIN_ID"))
    by_name = {v.name: v for v in bundle.tests[0].variables}
    assert by_name["SECRET_PW"].sensitive is True
    assert by_name["LOGIN_ID"].sensitive is False


# ─── 보충한 사실이 남는다 ──────────────────────────────────────────────────


def test_repair_is_reported_not_silent() -> None:
    """조용히 고치면 사용자는 파일이 온전했다고 믿는다 (FR-047)."""
    bundle = read_bundle(_bundle_with_undeclared("SECRET_LOGIN_PW"))
    assert [(r.test_id, r.name, r.sensitive) for r in bundle.repaired] == [
        ("TC-001", "SECRET_LOGIN_PW", True)
    ]


def test_repaired_values_are_marked_undeclared() -> None:
    """채울 목록에서 「보충한 것」과 「원래 있던 것」이 구별되어야 한다."""
    bundle = read_bundle(_bundle_with_undeclared("SECRET_LOGIN_PW"))
    (required,) = bundle.required_values
    assert required.declared is False
    assert required.name == "SECRET_LOGIN_PW"


def test_nothing_to_repair_leaves_the_report_empty() -> None:
    from itb.domain.test_case import Variable, variable_reference

    test = make_test(
        "TC-001",
        "로그인",
        steps=[fill(1, "비밀번호", variable_reference("SECRET_PW")), click(2, "확인")],
        variables=[Variable(name="SECRET_PW", value=None, sensitive=True)],
    )
    bundle = read_bundle(dump_bundle(build_bundle(_project(), [test])))
    assert bundle.repaired == []
    assert bundle.required_values[0].declared is True
