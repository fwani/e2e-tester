"""US8 — 설계 스프레드시트를 넣어 초안을 만든다 (014 T045 · quickstart §2 이야기 2).

사용자가 실제로 밟는 순서를 한 흐름으로 따라간다: 파일을 고르고 → 미리보기를 보고 →
**취소하고** → 다시 열어 접두어를 넣고 → 확정한다.

취소를 중간에 넣은 것이 이 검증의 핵심이다. "확정 전에는 아무것도 만들지 않는다"(FR-016)는
취소해 봐야만 확인된다.
"""

from __future__ import annotations

from excel_support import build_xlsx, row, upload
from fastapi.testclient import TestClient

from itb.portability.sheet_name import UNGROUPED_SHEET_NAME

COMMIT = "/api/import/commit"


def test_설계서를_손_입력_없이_옮긴다(project_client: TestClient) -> None:
    client = project_client

    # 시트 3개: 그룹 없음 · 접두어 있음(중복 포함) · 접두어 없음.
    # 여기에 제목이 빈 행과 완전히 빈 행을 섞는다.
    data = build_xlsx(
        {
            UNGROUPED_SHEET_NAME: [
                row("TC-001", "첫 번째"),
                row("TC-002", "두 번째"),
            ],
            "회원": [
                row("USER-010", "로그인", "자격 증명 확인", "관리자", "1. 연다", "1. 이동한다"),
                row("USER-011", "로그아웃"),
                row("USER-010", "중복된 것"),  # 파일 안 중복
                row("USER-012", None),  # 제목이 빈 행
                row(),  # 완전히 빈 행
            ],
            "데이터관리": [
                row(None, "목록 조회"),
                row(None, "상세 조회"),
            ],
        }
    )

    # ── 미리보기 ────────────────────────────────────────────────────────
    resp = upload(client, data, "통합테스트설계서.xlsx")
    assert resp.status_code == 200, resp.text
    plan = resp.json()

    by_name = {s["sheet_name"]: s for s in plan["sheets"]}

    # 접두어를 읽어낸 시트와 물어야 하는 시트가 갈린다.
    assert by_name["회원"]["prefix"] == "USER"
    assert by_name["회원"]["needs_prefix"] is False
    assert by_name["데이터관리"]["needs_prefix"] is True
    assert plan["sheets"][0]["prefix"] == "TC"

    # 중복 번호가 바뀐 사실을 원래 값과 함께 알린다.
    renumbered = by_name["회원"]["renumbered"]
    assert len(renumbered) == 1
    assert renumbered[0]["from"] == "USER-010"
    assert renumbered[0]["to"] != "USER-010"

    # 건너뛸 행을 시트 이름·행 번호와 함께 알린다.
    #
    # **완전히 빈 행은 여기 오지 않는다** (T087). 스프레드시트 도구가 딸려 보내는 빈 행을
    # 보고하면 목록이 그것으로 뒤덮여, 사용자가 정말 봐야 하는 「제목이 빈 행」이 묻힌다.
    reasons = {(s["sheet_name"], s["row"]): s["reason"] for s in plan["skipped"]}
    assert reasons == {("회원", 5): "no_title"}

    # 접두어를 모르는 시트는 아직 초안 수에 들지 않지만, 몇 건이 기다리는지는 보인다.
    # 그룹없음 2 + 회원 3. 중복된 행도 **살아남는다** — 새 번호를 받을 뿐이다 (FR-023a).
    # 제목이 빈 행과 완전히 빈 행만 빠진다.
    assert plan["draft_count"] == 5
    assert by_name["데이터관리"]["row_count"] == 2

    # ── 취소한다: 아무것도 만들어지지 않아야 한다 (FR-016) ──────────────
    assert client.get("/api/drafts").json()["count"] == 0
    assert client.get("/api/groups").json()["groups"] == []
    assert client.get("/api/tests").json()["counts"]["total"] == 0

    # ── 다시 열어 접두어를 넣고 확정한다 ────────────────────────────────
    plan2 = upload(client, data, "통합테스트설계서.xlsx").json()
    made = client.post(
        COMMIT,
        json={"plan_id": plan2["plan_id"], "prefixes": {"데이터관리": "DATA"}},
    )
    assert made.status_code == 201, made.text
    body = made.json()

    # 그룹 둘이 만들어졌다. 그룹 없음 시트는 그룹을 만들지 않는다.
    assert {g["prefix"] for g in body["created_groups"]} == {"USER", "DATA"}

    # 초안 7건 = 그룹없음 2 + 회원 3 + 데이터관리 2.
    drafts = client.get("/api/drafts").json()
    assert drafts["count"] == len(body["drafts"])

    by_group: dict[str, int] = {}
    for d in drafts["drafts"]:
        by_group[d["group_prefix"]] = by_group.get(d["group_prefix"], 0) + 1
    assert by_group == {"TC": 2, "USER": 3, "DATA": 2}

    # 모든 칸이 보존됐다.
    login = next(d for d in drafts["drafts"] if d["name"] == "로그인")
    assert login["description"] == "자격 증명 확인"
    assert login["actor"] == "관리자"
    assert login["source"]["file_name"] == "통합테스트설계서.xlsx"
    assert login["source"]["sheet_name"] == "회원"

    detail = client.get(f"/api/drafts/{login['draft_id']}").json()
    assert detail["procedure"] == "1. 연다"
    assert detail["expectation"] == "1. 이동한다"
    assert "관리자" in detail["suggested_instruction"]

    # ── 초안은 테스트가 아니다 (FR-027) ─────────────────────────────────
    listing = client.get("/api/tests").json()
    assert listing["tests"] == []
    assert listing["counts"]["total"] == 0
    assert listing["draft_count"] == drafts["count"]
