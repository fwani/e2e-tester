"""초안이 테스트가 되는 순간 (014 T063 · FR-030·FR-032·FR-033·FR-071).

세션을 실제로 만들지 않고 **저장 경로만** 지나간다. 브라우저를 띄우면 이 검증이 느려지고,
확인하려는 것(번호 부여·필드 이전·초안 삭제)은 저장 시점의 판단이지 녹화의 판단이 아니다.
녹화 자체는 US1~US6 이 이미 지킨다.
"""

from __future__ import annotations

import pytest
from excel_support import click, make_test, preview, repo_of, row
from fastapi.testclient import TestClient

from itb.api.routes.sessions import _WORK, SessionWork
from itb.domain.test_case import AuthoringMode

COMMIT = "/api/import/commit"


def seed_draft(client: TestClient, rows: list[list[object]] | None = None) -> list[dict]:
    plan = preview(
        client,
        {"회원": rows or [row("USER-003", "로그인", "자격 증명 확인", "관리자", "1. 연다")]},
    )
    resp = client.post(COMMIT, json={"plan_id": plan["plan_id"]})
    assert resp.status_code == 201, resp.text
    return resp.json()["drafts"]


@pytest.fixture
def fake_session(project_client: TestClient):
    """저장할 것이 있는 가짜 세션을 `_WORK` 에 심는다.

    `SessionWork` 는 브라우저 세션과 리코더를 요구하지만, 저장 경로는 `steps`·`start_url`·
    `draft_id` 만 본다. 나머지는 저장에 닿지 않으므로 최소한만 채운다.
    """

    class _NoCaptures:
        """저장 경로가 리코더에서 보는 것은 이것 하나다 (`_variables_for`)."""

        sensitive_captures: tuple[()] = ()

    def make(draft_id: str | None) -> str:
        session_id = f"s-{draft_id or 'none'}"
        work = SessionWork.__new__(SessionWork)
        work.session = None  # type: ignore[assignment]
        work.recorder = _NoCaptures()  # type: ignore[assignment]
        work.store = None
        work.steps = [click(1, "로그인 버튼")]
        work.start_url = "https://example.internal/login"
        work.authoring_mode = AuthoringMode.AI
        work.ai_instruction = "제목: 로그인"
        work.saved_test_id = None
        work.saved_test_name = None
        work.draft_id = draft_id
        work.saved_at = None
        work.saved_snapshot = []
        work.base_variables = []
        _WORK[session_id] = work
        return session_id

    yield make
    _WORK.clear()


def save(client: TestClient, session_id: str, name: str = "로그인") -> dict:
    resp = client.post(f"/api/sessions/{session_id}/save", json={"name": name})
    assert resp.status_code == 200, resp.text
    return resp.json()


class DesiredIdTests:
    def test_희망_번호가_비어_있으면_그것을_받는다(
        self, project_client: TestClient, fake_session
    ) -> None:
        made = seed_draft(project_client)
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        assert saved["id"] == "USER-003"
        assert saved["desired_id_taken"] is None

    def test_이미_쓰이면_다른_번호를_받는다(
        self, project_client: TestClient, fake_session
    ) -> None:
        made = seed_draft(project_client)
        repo_of(project_client).write_test(make_test("USER-003", "먼저 가져간 것"))
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        assert saved["id"] != "USER-003"

    def test_다른_번호를_받았음을_알린다(
        self, project_client: TestClient, fake_session
    ) -> None:
        # **조용히 다른 번호를 주지 않는다** (FR-032). 사용자의 설계서에는 원래 번호가
        # 적혀 있고, 어긋났다는 사실을 지금 말하지 않으면 나중에 발견하게 된다.
        made = seed_draft(project_client)
        repo_of(project_client).write_test(make_test("USER-003", "먼저 가져간 것"))
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        assert saved["desired_id_taken"] == {"wanted": "USER-003", "assigned": saved["id"]}

    def test_새_번호는_소속_그룹을_지킨다(
        self, project_client: TestClient, fake_session
    ) -> None:
        made = seed_draft(project_client)
        repo_of(project_client).write_test(make_test("USER-003", "먼저 가져간 것"))
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        assert saved["id"].startswith("USER-")

    def test_초안에서_왔음을_알린다(self, project_client: TestClient, fake_session) -> None:
        made = seed_draft(project_client)
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        assert saved["from_draft"] == made[0]["draft_id"]

    def test_초안이_아닌_세션은_그_사실이_비어_있다(
        self, project_client: TestClient, fake_session
    ) -> None:
        saved = save(project_client, fake_session(None))
        assert saved["from_draft"] is None
        assert saved["desired_id_taken"] is None


class FieldCarryOverTests:
    def test_설명과_수행자가_테스트로_옮겨간다(
        self, project_client: TestClient, fake_session
    ) -> None:
        # 이것이 없으면 다시 내보낼 때 두 칸이 비어 **왕복이 끊긴다** (FR-071).
        made = seed_draft(project_client)
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        assert saved["description"] == "자격 증명 확인"
        assert saved["actor"] == "관리자"

    def test_저장된_파일에도_남는다(self, project_client: TestClient, fake_session) -> None:
        made = seed_draft(project_client)
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        test = repo_of(project_client).read_test(saved["id"])
        assert test.description == "자격 증명 확인"
        assert test.actor == "관리자"

    def test_저장_형식에_초안_흔적이_남지_않는다(
        self, project_client: TestClient, fake_session
    ) -> None:
        # from_draft·desired_id_taken 은 이번 저장에서만 참인 사실이다. 파일에 남으면
        # 다음에 읽을 때 거짓이 된다.
        made = seed_draft(project_client)
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        path = repo_of(project_client).find_test_path(saved["id"])
        assert path is not None
        text = path.read_text(encoding="utf-8")
        assert "from_draft" not in text
        assert "desired_id_taken" not in text


class DraftLifecycleTests:
    def test_저장에_성공하면_초안이_사라진다(
        self, project_client: TestClient, fake_session
    ) -> None:
        made = seed_draft(project_client)
        save(project_client, fake_session(made[0]["draft_id"]))
        assert project_client.get("/api/drafts").json()["count"] == 0

    def test_다른_초안은_남는다(self, project_client: TestClient, fake_session) -> None:
        made = seed_draft(
            project_client, [row("USER-003", "로그인"), row("USER-004", "로그아웃")]
        )
        save(project_client, fake_session(made[0]["draft_id"]))
        remaining = project_client.get("/api/drafts").json()
        assert remaining["count"] == 1
        assert remaining["drafts"][0]["draft_id"] == made[1]["draft_id"]

    def test_저장하지_않으면_초안이_남는다(
        self, project_client: TestClient, fake_session
    ) -> None:
        made = seed_draft(project_client)
        fake_session(made[0]["draft_id"])  # 세션만 만들고 저장하지 않는다
        assert project_client.get("/api/drafts").json()["count"] == 1

    def test_초안이_사라져도_저장은_성공한다(
        self, project_client: TestClient, fake_session
    ) -> None:
        # 다른 창에서 지웠을 수 있다. 그때 저장을 막으면 사용자는 방금 녹화한 것을 잃는다.
        made = seed_draft(project_client)
        session_id = fake_session(made[0]["draft_id"])
        project_client.delete(f"/api/drafts/{made[0]['draft_id']}")
        saved = save(project_client, session_id)
        assert saved["id"].startswith("TC-")  # 초안을 못 읽었으므로 보통 경로로 받는다

    def test_저장된_테스트가_목록에_보인다(
        self, project_client: TestClient, fake_session
    ) -> None:
        made = seed_draft(project_client)
        saved = save(project_client, fake_session(made[0]["draft_id"]))
        listing = project_client.get("/api/tests").json()
        assert [t["id"] for t in listing["tests"]] == [saved["id"]]
        assert listing["draft_count"] == 0


class RecordModeTests:
    """초안에서 **손으로 녹화**하는 것도 온전한 방법이다 (수렴 2회차).

    화면은 초안에서 시작할 때 「직접 녹화」와 「AI」 두 갈래를 나란히 보여 주면서
    「저장하면 이 초안은 사라집니다」라고 안내한다. 녹화 쪽이 초안과 이어지지 않으면
    **그 안내가 거짓**이 된다 — 저장해도 초안이 남고 희망 번호도 받지 못한다.
    """

    def test_record_모드가_초안을_거절하지_않는다(self, project_client: TestClient) -> None:
        made = seed_draft(project_client)
        resp = project_client.post(
            "/api/sessions",
            json={
                "mode": "record",
                "start_url": "https://example.internal/login",
                "draft_id": made[0]["draft_id"],
            },
        )
        # 이 URL 은 닿지 않으므로 브라우저 단계에서 실패한다 — 그것은 환경 문제다.
        # 확인하려는 것은 **초안 때문에 거절되지 않는다**는 것이므로 코드를 본다.
        code = resp.json()["error"]["code"] if resp.status_code >= 400 else None
        assert code != "DEFINITION_INVALID", resp.text

    def test_replay_모드는_초안을_거절한다(self, project_client: TestClient) -> None:
        # 재실행은 이미 저장된 테스트를 돌리는 것이므로 초안과 상관이 없다.
        # 테스트가 실제로 있어야 초안 검사에 닿는다 — 없으면 404 가 먼저 난다.
        made = seed_draft(project_client)
        repo_of(project_client).write_test(make_test("USER-003", "이미 있는 것"))

        resp = project_client.post(
            "/api/sessions",
            json={"mode": "replay", "test_id": "USER-003", "draft_id": made[0]["draft_id"]},
        )
        assert resp.status_code == 400, resp.text
        assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
