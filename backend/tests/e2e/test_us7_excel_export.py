"""US7 — 프로젝트를 스프레드시트로 내보낸다 (014 T030 · quickstart §2 이야기 1).

사용자가 실제로 밟는 순서를 한 흐름으로 따라간다: 프로젝트를 열고 → 그룹을 만들고 →
테스트를 저장하고 → 실행 결과를 남기고 → 내보내고 → **받은 파일을 다시 연다**.

브라우저를 쓰지 않는다. 내보내기가 보는 것은 저장된 정의와 실행 결과뿐이므로, 녹화를
돌리지 않아도 이 흐름의 모든 갈래를 만들 수 있다. 녹화 자체는 US1~US6 이 이미 지킨다.
"""

from __future__ import annotations

from excel_support import check, click, make_result, make_test, read_back, repo_of, sheet_names
from fastapi.testclient import TestClient

from itb.domain.run_result import Outcome
from itb.portability.columns import ORDER
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME

EXPORT = "/api/export"


def test_설계와_결과를_팀_형식으로_꺼낸다(project_client: TestClient) -> None:
    client = project_client

    # ── 그룹 둘을 만든다 ────────────────────────────────────────────────
    for prefix, name in (("USER", "사용자관리"), ("DATA", "데이터")):
        made = client.post("/api/groups", json={"prefix": prefix, "name": name})
        assert made.status_code == 201, made.text

    # ── 테스트를 심는다: 그룹 둘 + 미그룹 ──────────────────────────────
    repo = repo_of(client)
    repo.write_test(
        make_test(
            "USER-001",
            "로그인",
            description="올바른 자격 증명으로 로그인되는지 확인한다",
            actor="관리자",
            steps=[
                click(1, "로그인 화면을 연다"),
                click(2, "로그인 버튼을 누른다"),
                check(3, "대시보드로 이동한다", "대시보드"),
            ],
        )
    )
    repo.write_test(make_test("USER-002", "로그아웃"))
    repo.write_test(make_test("DATA-003", "목록 조회"))
    repo.write_test(make_test("TC-004", "그룹 없는 것"))

    # ── 실행 결과를 남긴다: 통과·실패·미실행이 섞이게 ──────────────────
    repo.write_result(make_result("USER-001", Outcome.PASS))
    repo.write_result(make_result("USER-002", Outcome.FAIL))
    # DATA-003 과 TC-004 는 실행하지 않는다.

    # ── 내보낸다 ────────────────────────────────────────────────────────
    resp = client.get(EXPORT)
    assert resp.status_code == 200, resp.text
    assert "attachment" in resp.headers["content-disposition"]

    # ── 받은 파일을 다시 연다 ──────────────────────────────────────────
    assert sheet_names(resp.content) == [UNGROUPED_SHEET_NAME, "사용자관리", "데이터"]

    sheets = read_back(resp.content)
    header = [c.value for c in ORDER]
    assert all(rows[0] == header for rows in sheets.values())

    # 그룹마다 제 테스트만 들어 있다.
    assert [r[0] for r in sheets["사용자관리"][1:]] == ["USER-001", "USER-002"]
    assert [r[0] for r in sheets["데이터"][1:]] == ["DATA-003"]
    assert [r[0] for r in sheets[UNGROUPED_SHEET_NAME][1:]] == ["TC-004"]

    # 첫 행의 모든 칸이 뜻대로 채워졌다.
    row = sheets["사용자관리"][1]
    assert row[0] == "USER-001"
    assert row[1] == "로그인"
    assert row[2] == "올바른 자격 증명으로 로그인되는지 확인한다"
    assert row[3] == "관리자"
    assert row[4] == "1. 로그인 화면을 연다\n2. 로그인 버튼을 누른다"
    assert row[5] == "1. 대시보드로 이동한다"
    assert row[6] == "P"

    # 실패와 미실행이 구별된다.
    assert sheets["사용자관리"][2][6] == "F"
    assert sheets["데이터"][1][6] in (None, "")

    # ── 내보내기가 프로젝트를 바꾸지 않았다 ────────────────────────────
    listing = client.get("/api/tests").json()
    assert listing["counts"]["total"] == 4
    assert listing["problems"] == []
