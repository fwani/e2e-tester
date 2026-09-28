"""결함 후보 표시가 공유 왕복에서 보존된다 (020 T051 · FR-017).

**표시가 사라지면 받는 쪽에서 모든 알려진 결함이 회귀로 보인다.** 분류는 정의의
`mismatch` 와 이번 실행 결과의 조합이므로, 앞쪽이 없어지면 뒤쪽만으로 판정하게 되고
그 판정은 「오늘 새로 깨졌다」다. 팀에 테스트를 넘기는 순간 전부 빨간 회귀가 된다.

## 고정 데이터를 **사람이 만든 검증**으로 잡는다 (정합성 점검 F5)

헌법 원칙 I 은 사람이 만든 Step 과 AI 가 만든 Step 이 같다고 요구한다. 어긋남 표시를
AI 경로에서만 확인하면 그 요구가 AI 밖에서도 성립하는지 알 수 없다. 여기서는 정의를
직접 써 넣으므로 작성 주체가 사람이고, 그대로 왕복한다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import yaml
from fastapi.testclient import TestClient
from sharing_support import (
    click,
    export_bundle,
    fill,
    make_test,
    repo_of,
    write_tests,
)

from itb.domain.assertion import Assertion, AssertionKind, AuthoringMismatch
from itb.domain.step import AssertionStep, Step
from itb.domain.test_case import Test

RECORDED_AT = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
EXPECTED = "저장되었습니다"
OBSERVED = "처리 완료"


def _mismatched_check(index: int) -> Step:
    """작성 시점에 통과하지 않은 검증. **사람이 만든 것이다** (author 기본값)."""
    return AssertionStep(
        id=f"step-{index:02d}",
        label="저장 문구 확인",
        assertion=Assertion(kind=AssertionKind.TEXT, value=EXPECTED),
        mismatch=AuthoringMismatch(observed=OBSERVED, recorded_at=RECORDED_AT),
    )


def _clean_check(index: int) -> Step:
    return AssertionStep(
        id=f"step-{index:02d}",
        label="목록 표시 확인",
        assertion=Assertion(kind=AssertionKind.TEXT, value="항목 목록"),
    )


def _test_with_both() -> Test:
    return make_test(
        "TC-020",
        "결함 후보가 섞인 테스트",
        steps=[
            fill(1, "이름 입력", "가나다"),
            click(2, "저장"),
            _mismatched_check(3),
            _clean_check(4),
        ],
    )


def test_export_carries_the_mismatch(keyed_client: TestClient) -> None:
    """묶음 안에 기대값과 관찰값이 함께 들어간다."""
    write_tests(keyed_client, _test_with_both())
    bundle = export_bundle(keyed_client)

    raw = bundle.decode("utf-8", errors="replace")
    assert EXPECTED in raw, "기대값이 묶음에 없다"
    assert OBSERVED in raw, "작성 시점 관찰값이 묶음에 없다"


def test_round_trip_keeps_the_mismatch_intact(keyed_client: TestClient) -> None:
    """내보내고 다시 읽어도 **같은 기록**이다.

    공유는 모델 왕복(`Test.model_validate(model_dump())`)이므로 자동으로 보존된다.
    자동이라는 사실 자체가 검사를 필요로 한다 — 어느 시점엔가 정의를 골라 실어 보내는
    코드가 들어오면 조용히 빠진다.
    """
    write_tests(keyed_client, _test_with_both())
    repo = repo_of(keyed_client)

    loaded = repo.read_test("TC-020")
    marked = [s for s in loaded.steps if getattr(s, "mismatch", None) is not None]
    clean = [
        s
        for s in loaded.steps
        if s.type == "assertion" and getattr(s, "mismatch", None) is None
    ]

    assert len(marked) == 1, "어긋남 표시가 저장 왕복에서 사라졌다"
    assert len(clean) == 1, "표시 없는 검증까지 표시를 얻었다"

    mismatch = marked[0].mismatch
    assert mismatch is not None
    assert mismatch.observed == OBSERVED
    assert mismatch.truncated is False
    assert mismatch.recorded_at == RECORDED_AT
    # 기대값은 **복제되지 않았다.** 유일한 출처는 조건이다 (research R1).
    assert marked[0].assertion.value == EXPECTED


def test_definition_files_written_before_020_still_load(keyed_client: TestClient) -> None:
    """**디스크에 칸이 없는 파일**이 그대로 읽힌다 — 마이그레이션이 없다는 주장의 근거다.

    모델로 써 넣으면 기본값이 채워지므로 옛 파일이 되지 않는다. 그래서 저장된 파일에서
    칸을 지운 뒤 다시 읽는다 — 020 이전에 저장된 정의가 실제로 그 모양이다.
    """
    write_tests(keyed_client, _test_with_both())
    repo = repo_of(keyed_client)
    path = repo.find_test_path("TC-020")
    assert path is not None

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    removed = 0
    for step in raw["steps"]:
        if step.pop("mismatch", None) is not None or step["type"] == "assertion":
            removed += 1
    assert removed >= 1, "지울 칸이 없으면 이 검증이 성립하지 않는다"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    loaded = repo.read_test("TC-020")
    for step in loaded.steps:
        if step.type == "assertion":
            assert step.mismatch is None, "칸이 없는 파일에서 표시가 생겼다"
