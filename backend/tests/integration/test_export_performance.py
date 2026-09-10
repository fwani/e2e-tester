"""내보내기 성능 (014 T094 · SC-002).

**테스트 100건·그룹 10개 내보내기가 10초 안에 끝난다.** 이 규모는 실제 프로젝트의
흔한 크기이며, 여기서 느리면 사용자는 「엑셀로 내보내기」를 누르고 무슨 일이 일어나는지
모른 채 기다리게 된다.

`timing` 계층에 둔다 — 시간을 재는 검증은 프로세스를 나눠 돌리면 값이 흔들린다.
"""

from __future__ import annotations

import time

import pytest
from excel_support import check, click, make_result, make_test, read_back, repo_of
from fastapi.testclient import TestClient

from itb.domain.run_result import Outcome

EXPORT = "/api/export"

TESTS = 100
GROUPS = 10
BUDGET_S = 10.0


@pytest.mark.timing
def test_테스트_100건을_10초_안에_내보낸다(project_client: TestClient) -> None:
    client = project_client

    prefixes = [f"G{i}" for i in range(GROUPS)]
    for i, prefix in enumerate(prefixes):
        made = client.post("/api/groups", json={"prefix": prefix, "name": f"그룹 {i}"})
        assert made.status_code == 201, made.text

    repo = repo_of(client)
    for n in range(1, TESTS + 1):
        prefix = prefixes[n % GROUPS]
        repo.write_test(
            make_test(
                f"{prefix}-{n:03d}",
                f"테스트 {n}",
                description=f"{n}번째 테스트의 설명",
                actor="관리자",
                steps=[
                    click(1, f"{n} 화면을 연다"),
                    click(2, f"{n} 버튼을 누른다"),
                    check(3, f"{n} 결과가 보인다", "결과"),
                ],
            )
        )
        if n % 3 == 0:
            repo.write_result(make_result(f"{prefix}-{n:03d}", Outcome.PASS))

    started = time.monotonic()
    resp = client.get(EXPORT)
    elapsed = time.monotonic() - started

    assert resp.status_code == 200, resp.text
    assert elapsed < BUDGET_S, f"내보내기가 {elapsed:.1f}초 걸렸다 (예산 {BUDGET_S}초)"

    # 느린 것만 아니라 **맞게** 나왔는지도 본다 — 빨리 틀리는 것은 개선이 아니다.
    sheets = read_back(resp.content)
    assert len(sheets) == GROUPS + 1
    assert sum(len(rows) - 1 for rows in sheets.values()) == TESTS
