"""US9 — 초안을 녹화로 완성하고 왕복이 이어진다 (014 T065 · quickstart §2 이야기 3).

**이 검증의 목적은 왕복이 닫히는지 보는 것이다.** 엑셀 → 초안 → 테스트 → 엑셀 로 한 바퀴
돌았을 때 「테스트항목」과 「수행자」가 그대로 있어야 한다. 그 둘이 사라지면 사용자는 매번
설계서를 손으로 다시 채워야 하고, 가져오기의 가치 절반이 없어진다.

브라우저를 띄우지 않는다 — 확인하려는 것은 녹화가 아니라 **초안과 테스트와 워크북 사이의
연결**이다. 녹화 자체는 US1~US6 이 지킨다.
"""

from __future__ import annotations

import pytest
from excel_support import build_xlsx, click, read_back, repo_of, row, upload
from fastapi.testclient import TestClient

from itb.api.routes.sessions import _WORK, SessionWork
from itb.domain.test_case import AuthoringMode

COMMIT = "/api/import/commit"
EXPORT = "/api/export"


@pytest.fixture
def recorded_session():
    """녹화가 끝난 세션을 흉내 낸다 — 저장할 Step 이 있고 초안을 가리킨다."""

    class _NoCaptures:
        sensitive_captures: tuple[()] = ()

    def make(draft_id: str, instruction: str) -> str:
        session_id = f"s-{draft_id}"
        work = SessionWork.__new__(SessionWork)
        work.session = None  # type: ignore[assignment]
        work.recorder = _NoCaptures()  # type: ignore[assignment]
        work.store = None
        work.steps = [click(1, "로그인 화면을 연다"), click(2, "로그인 버튼을 누른다")]
        work.start_url = "https://example.internal/login"
        work.authoring_mode = AuthoringMode.AI
        work.ai_instruction = instruction
        work.saved_test_id = None
        work.saved_test_name = None
        work.draft_id = draft_id
        work.saved_at = None
        work.saved_snapshot = []
        work.base_variables = []
        # 016 FR-029 — 저장 경로가 「확정되지 않은 교체가 있는가」를 본다.
        work.rerecord = None
        _WORK[session_id] = work
        return session_id

    yield make
    _WORK.clear()


def test_초안이_테스트가_되고_왕복이_이어진다(
    project_client: TestClient, recorded_session
) -> None:
    client = project_client

    # ── 설계서를 가져온다 ───────────────────────────────────────────────
    data = build_xlsx(
        {
            "회원": [
                row(
                    "USER-003",
                    "로그인",
                    "올바른 자격 증명으로 로그인되는지 확인한다",
                    "관리자",
                    "1. 로그인 화면을 연다\n2. 로그인 버튼을 누른다",
                    "1. 대시보드로 이동한다",
                )
            ]
        }
    )
    plan = upload(client, data, "통합테스트설계서.xlsx").json()
    made = client.post(COMMIT, json={"plan_id": plan["plan_id"]})
    assert made.status_code == 201, made.text
    draft_id = made.json()["drafts"][0]["draft_id"]

    # ── 초안 상세: 지시문이 지어져 있다 (FR-031) ────────────────────────
    detail = client.get(f"/api/drafts/{draft_id}").json()
    instruction = detail["suggested_instruction"]
    assert "제목: 로그인" in instruction
    assert "올바른 자격 증명으로 로그인되는지 확인한다" in instruction
    assert "관리자 역할로 수행한다." in instruction
    assert "1. 로그인 화면을 연다" in instruction
    assert "1. 대시보드로 이동한다" in instruction

    # ── 녹화하고 저장한다 ───────────────────────────────────────────────
    session_id = recorded_session(draft_id, instruction)
    saved = client.post(f"/api/sessions/{session_id}/save", json={"name": "로그인"})
    assert saved.status_code == 200, saved.text
    body = saved.json()

    # 희망 번호를 그대로 받았다 (FR-032).
    assert body["id"] == "USER-003"
    assert body["desired_id_taken"] is None
    assert body["from_draft"] == draft_id

    # ── 초안은 사라지고 테스트가 생겼다 (FR-033) ────────────────────────
    assert client.get("/api/drafts").json()["count"] == 0
    listing = client.get("/api/tests").json()
    assert [t["id"] for t in listing["tests"]] == ["USER-003"]
    assert listing["draft_count"] == 0

    # ── 저장 형식은 손으로 만든 테스트와 같다 (FR-034) ──────────────────
    test = repo_of(client).read_test("USER-003")
    assert test.dsl_version == 1
    assert len(test.steps) == 2

    # ── 다시 내보내면 왕복이 이어진다 ───────────────────────────────────
    resp = client.get(EXPORT)
    assert resp.status_code == 200, resp.text
    sheets = read_back(resp.content)

    # 그룹 시트에 그 테스트가 있다.
    assert "회원" in sheets
    exported = sheets["회원"][1]
    assert exported[0] == "USER-003"
    assert exported[1] == "로그인"
    # **이 둘이 핵심이다** — 초안에 있던 값이 테스트를 거쳐 다시 표로 돌아왔다.
    assert exported[2] == "올바른 자격 증명으로 로그인되는지 확인한다"
    assert exported[3] == "관리자"
    # 절차는 녹화한 스텝에서 다시 만들어진다 — 원본 문장이 아니라 **실제 스텝**이다.
    assert exported[4] == "1. 로그인 화면을 연다\n2. 로그인 버튼을 누른다"
    # 아직 실행하지 않았으므로 결과는 비어 있다.
    assert exported[6] in (None, "")
