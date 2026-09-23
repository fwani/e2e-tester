"""019 T019 — 묶음 만들기.

`build_bundle` 이 무엇을 싣고 무엇을 비우는지 확인한다. 「실리지 않는다」쪽이 더 중요하다 —
실리지 않아야 할 것이 실리면 되돌릴 방법이 없다.
"""

from __future__ import annotations

import datetime as dt

import yaml
from sharing_support import click, fill, make_test

from itb.domain.test_case import (
    ImportProvenance,
    Project,
    TestGroup,
    Variable,
    variable_reference,
)
from itb.sharing.builder import build_bundle, dump_bundle
from itb.sharing.limits import BUNDLE_VERSION


def _project(groups: list[TestGroup] | None = None) -> Project:
    return Project(
        name="dev-graphio",
        default_start_url="https://example.internal",
        test_id_attribute="data-testid",
        groups=groups or [],
    )


# ─── 무엇이 실리는가 ───────────────────────────────────────────────────────


def test_bundle_carries_project_settings() -> None:
    bundle = build_bundle(_project(), [make_test("TC-001", "로그인")])
    assert bundle.project.name == "dev-graphio"
    assert bundle.project.default_start_url == "https://example.internal"
    assert bundle.project.test_id_attribute == "data-testid"
    assert bundle.bundle_version == BUNDLE_VERSION


def test_steps_travel_whole_with_every_locator_candidate() -> None:
    """로케이터 후보를 축약하면 받은 쪽의 복원력이 보낸 쪽보다 낮아진다 (헌법 원칙 IV)."""
    test = make_test("TC-001", "로그인")
    bundle = build_bundle(_project(), [test])
    assert bundle.tests[0].model_dump(mode="json") == test.model_dump(
        mode="json", exclude={"imported_from"}
    ) | {"imported_from": None}


def test_only_groups_in_use_travel_for_a_selection() -> None:
    """고른 테스트만 내보낼 때 빈 그룹을 옮기면 받는 쪽에 테스트 없는 그룹이 생긴다."""
    groups = [TestGroup(prefix="USER", name="사용자관리"), TestGroup(prefix="DATA", name="데이터")]
    tests = [make_test("USER-001", "가")]
    bundle = build_bundle(_project(groups), tests, whole_project=False)
    assert [g.prefix for g in bundle.project.groups] == ["USER"]


def test_whole_project_export_keeps_empty_groups() -> None:
    """프로젝트 전체를 옮길 때는 빈 그룹도 프로젝트 구성이다."""
    groups = [TestGroup(prefix="USER", name="사용자관리"), TestGroup(prefix="DATA", name="데이터")]
    bundle = build_bundle(_project(groups), [make_test("USER-001", "가")], whole_project=True)
    assert {g.prefix for g in bundle.project.groups} == {"USER", "DATA"}


# ─── 무엇이 실리지 않는가 ──────────────────────────────────────────────────


def test_import_provenance_is_cleared() -> None:
    """A→B→C 로 전달될 때 B 의 가져오기 기록이 C 에게 갈 이유가 없다 (research R9).

    파일 이름이 사내 경로를 흘릴 수도 있다.
    """
    test = make_test("TC-001", "로그인").model_copy(
        update={
            "imported_from": ImportProvenance(
                source_file="내부-프로젝트-묶음.itbshare.yaml",
                imported_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC),
                original_id="TC-042",
            )
        }
    )
    bundle = build_bundle(_project(), [test])
    assert bundle.tests[0].imported_from is None
    assert "내부-프로젝트-묶음" not in dump_bundle(bundle).decode("utf-8")


def test_sensitive_value_has_no_place_to_live() -> None:
    """도메인 불변식이 막는다 — 걸러 내는 것이 아니라 자리가 없다 (research R3)."""
    test = make_test(
        "TC-001",
        "로그인",
        steps=[fill(1, "비밀번호", variable_reference("SECRET_PW")), click(2, "확인")],
        variables=[Variable(name="SECRET_PW", value=None, sensitive=True)],
    )
    text = dump_bundle(build_bundle(_project(), [test])).decode("utf-8")
    loaded = yaml.safe_load(text)
    (var,) = [v for v in loaded["tests"][0]["variables"] if v["name"] == "SECRET_PW"]
    assert var["value"] is None


def test_next_test_number_does_not_travel() -> None:
    """이미 쓰이지 않는 하위 호환 잔재다. 새 형식이 물려받을 이유가 없다 (data-model §2.2)."""
    text = dump_bundle(build_bundle(_project(), [make_test("TC-001", "가")])).decode("utf-8")
    assert "next_test_number" not in text


def test_run_artifacts_do_not_travel() -> None:
    """실행 산출물은 재생성 가능하고 민감 정보 흔적이 남을 수 있다 (FR-005)."""
    text = dump_bundle(build_bundle(_project(), [make_test("TC-001", "가")])).decode("utf-8")
    for key in ("outcome", "screenshot", "total_ms", "passed_count"):
        assert key not in text


# ─── 직렬화 형태 ───────────────────────────────────────────────────────────


def test_dump_starts_with_a_notice_for_the_reader() -> None:
    """파일을 열어 본 사람이 가장 먼저 읽을 것이 '비밀번호는 없다' 여야 한다."""
    text = dump_bundle(build_bundle(_project(), [make_test("TC-001", "가")])).decode("utf-8")
    assert text.startswith("#")
    head = text.split("bundle_version")[0]
    assert "민감" in head


def test_dump_keeps_key_order_stable() -> None:
    """경고가 맨 위여야 하고, 같은 프로젝트에서 매번 같은 파일이 나와야 한다."""
    bundle = build_bundle(_project(), [make_test("TC-001", "가")])
    first = dump_bundle(bundle)
    assert dump_bundle(bundle) == first
    lines = first.decode("utf-8").splitlines()
    keys = [line.split(":")[0] for line in lines if line and line[0].isalpha()]
    assert keys[:5] == ["bundle_version", "generator", "created_at", "project", "required_values"]


def test_dump_keeps_korean_readable() -> None:
    """이스케이프된 유니코드는 사람이 읽을 수 없다 — 열어 볼 수 있다는 것이 설계 근거다."""
    bundle = build_bundle(_project(), [make_test("TC-001", "로그인 확인")])
    text = dump_bundle(bundle).decode("utf-8")
    assert "로그인 확인" in text
