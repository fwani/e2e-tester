"""공유 묶음 규모 (019 T091 · SC-008).

**테스트 50건을 내보내고 가져오는 것이 각각 10초 안에 끝난다.** 여기서 느리면 사용자는
버튼을 누르고 무슨 일이 일어나는지 모른 채 기다린다.

`timing` 계층에 둔다 — 시간을 재는 검증은 프로세스를 나눠 돌리면 값이 그 순간의 부하가
된다 (`tests/tiers.py`).
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from sharing_support import COMMIT, EXPORT, PLAN, check, click, fill, make_test, write_tests

TESTS = 50
STEPS_PER_TEST = 20
BUDGET_S = 10.0


def _bulky(index: int):
    """스텝이 넉넉한 테스트 하나. 실제 프로젝트의 테스트는 스텝이 여럿이다."""
    steps = []
    for i in range(1, STEPS_PER_TEST):
        steps.append(
            fill(i, f"입력 {i}", f"값-{index}-{i}") if i % 2 else click(i, f"클릭 {i}")
        )
    steps.append(check(STEPS_PER_TEST, "결과 확인", "완료"))
    return make_test(f"TC-{index:03d}", f"테스트 {index}", steps=steps)


@pytest.mark.timing
def test_테스트_50건을_10초_안에_내보낸다(project_client: TestClient) -> None:
    write_tests(project_client, *(_bulky(i) for i in range(1, TESTS + 1)))

    started = time.monotonic()
    resp = project_client.post(EXPORT, json={})
    elapsed = time.monotonic() - started

    assert resp.status_code == 200, resp.text
    assert resp.headers["x-itb-share-test-count"] == str(TESTS)
    assert elapsed < BUDGET_S, f"내보내기 {elapsed:.1f}초 (예산 {BUDGET_S}초)"


@pytest.mark.timing
def test_테스트_50건을_10초_안에_가져온다(project_client: TestClient) -> None:
    write_tests(project_client, *(_bulky(i) for i in range(1, TESTS + 1)))
    data = project_client.post(EXPORT, json={}).content

    started = time.monotonic()
    plan = project_client.post(
        f"{PLAN}?target=new",
        files={"file": ("big.itbshare.yaml", data, "application/yaml")},
    )
    assert plan.status_code == 201, plan.text
    report = project_client.post(COMMIT, json={"plan_id": plan.json()["plan_id"]})
    elapsed = time.monotonic() - started

    assert report.status_code == 201, report.text
    assert len(report.json()["created_tests"]) == TESTS
    assert elapsed < BUDGET_S, f"가져오기 {elapsed:.1f}초 (예산 {BUDGET_S}초)"
