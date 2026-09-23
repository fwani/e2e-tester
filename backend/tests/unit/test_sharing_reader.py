"""019 T031 — 묶음 읽기.

검증이 **다섯 겹**이고 앞의 겹을 통과하지 못하면 뒤를 시도하지 않는다 (data-model §6).
겹의 순서가 이 파일의 확인 대상이다 — 순서가 흐트러지면 막는 시점이 늦어지고, 늦게 막는
것은 막지 않은 것과 같다.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sharing_support import make_test

from itb.domain.test_case import Project
from itb.sharing.builder import build_bundle, dump_bundle
from itb.sharing.limits import MAX_BUNDLE_BYTES
from itb.sharing.reader import (
    BundleMalformedError,
    BundleTooLargeError,
    BundleVersionError,
    InvalidTestError,
    read_bundle,
)


def _project() -> Project:
    return Project(name="dev-graphio", default_start_url="https://example.internal")


def _bytes(**overrides: object) -> bytes:
    bundle = build_bundle(
        _project(),
        [make_test("TC-001", "로그인")],
        created_at=dt.datetime(2026, 9, 23, tzinfo=dt.UTC),
    )
    data = dump_bundle(bundle)
    if not overrides:
        return data
    text = data.decode("utf-8")
    for key, value in overrides.items():
        text = text.replace(f"{key}: 1", f"{key}: {value}", 1)
    return text.encode("utf-8")


# ─── 정상 경로 ─────────────────────────────────────────────────────────────


def test_reads_a_bundle_we_produced() -> None:
    """우리가 만든 것을 우리가 읽는다 — 왕복의 첫 절반이다."""
    bundle = read_bundle(_bytes())
    assert bundle.bundle_version == 1
    assert [t.id for t in bundle.tests] == ["TC-001"]
    assert bundle.project.name == "dev-graphio"


def test_korean_survives_the_round_trip() -> None:
    made = build_bundle(_project(), [make_test("TC-001", "로그인 확인")])
    bundle = read_bundle(dump_bundle(made))
    assert bundle.tests[0].name == "로그인 확인"


# ─── 1겹: 바이트 상한 (파싱 전) ────────────────────────────────────────────


def test_oversized_input_is_rejected_before_parsing() -> None:
    """**해석을 시작하기 전에** 거절한다. 늦게 막으면 막지 않은 것과 같다."""
    with pytest.raises(BundleTooLargeError):
        read_bundle(b"x" * (MAX_BUNDLE_BYTES + 1))


def test_size_check_does_not_need_valid_yaml() -> None:
    """상한 판정이 파싱에 앞선다는 증거 — 이 입력은 YAML 로도 읽히지 않는다."""
    with pytest.raises(BundleTooLargeError):
        read_bundle(b"[" * (MAX_BUNDLE_BYTES + 1))


# ─── 2겹: YAML ─────────────────────────────────────────────────────────────


def test_unparseable_yaml_is_rejected() -> None:
    with pytest.raises(BundleMalformedError):
        read_bundle(b"bundle_version: [\n")


def test_non_mapping_top_level_is_rejected() -> None:
    with pytest.raises(BundleMalformedError):
        read_bundle(b"- just\n- a\n- list\n")


def test_empty_input_is_rejected() -> None:
    with pytest.raises(BundleMalformedError):
        read_bundle(b"")


def test_invalid_utf8_is_rejected() -> None:
    """전송 중 손상된 파일이 예외로 터지지 않고 사유가 되어야 한다."""
    with pytest.raises(BundleMalformedError):
        read_bundle(b"\xff\xfe bundle_version: 1")


# ─── 3겹: 묶음 모델 ────────────────────────────────────────────────────────


def test_future_version_is_rejected() -> None:
    """모르는 필드를 버리고 억지로 복원하면 실행되지 않는 테스트가 조용히 만들어진다."""
    with pytest.raises(BundleVersionError):
        read_bundle(_bytes(bundle_version=99))


def test_older_version_is_rejected_too() -> None:
    """이 도구에 그런 버전이 없다. 「읽을 수 있다」고 가정하지 않는다."""
    with pytest.raises(BundleVersionError):
        read_bundle(_bytes(bundle_version=0))


def test_bundle_without_tests_is_rejected() -> None:
    with pytest.raises(BundleMalformedError):
        read_bundle(b"bundle_version: 1\ncreated_at: 2026-09-23T00:00:00Z\ntests: []\n")


def test_unknown_manifest_field_is_rejected() -> None:
    """`extra="forbid"` — 모르는 키를 조용히 무시하면 뜻이 사라진다."""
    text = _bytes().decode("utf-8").replace("generator:", "surprise: 1\ngenerator:", 1)
    with pytest.raises(BundleMalformedError):
        read_bundle(text.encode("utf-8"))


# ─── 5겹: 도메인 검증 ──────────────────────────────────────────────────────


def test_invalid_step_fails_the_whole_bundle() -> None:
    """한 건이라도 실패하면 전체를 거부한다 (FR-023·FR-024).

    일부만 살려 들이면 "가져왔는데 왜 3개뿐이지" 를 사용자가 추적할 수 없다.
    """
    text = _bytes().decode("utf-8").replace("type: fill", "type: 알수없음", 1)
    with pytest.raises(InvalidTestError) as exc:
        read_bundle(text.encode("utf-8"))
    assert exc.value.problems, "어느 테스트의 무엇이 문제인지 실려야 한다"


def test_problems_name_the_test() -> None:
    text = _bytes().decode("utf-8").replace("type: fill", "type: 알수없음", 1)
    with pytest.raises(InvalidTestError) as exc:
        read_bundle(text.encode("utf-8"))
    assert any("TC-001" in p for p in exc.value.problems)
