"""요청 경계 수단이 쓰는 실행 맥락.

수단은 "조작을 가하고 무엇이 남았는지 재는 것"만 한다. 그 조작에 필요한 **상태를 만드는
일**(세션을 열고, 일시정지시키고, 브라우저를 잃게 하고, AI 를 실패시키는 일)은 여기 모은다.

수단마다 상태 만들기를 반복하면 수단이 길어지고, 길어진 수단은 무엇을 재는지 읽히지 않는다.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from itb.llm.client import LlmUnavailableError

CLOSE_TAB = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]

SLOW_ASSERT = [
    {
        "type": "assertion",
        "id": "step-01",
        "label": "오래 기다리는 확인",
        "timeout_ms": 30_000,
        "assertion": {
            "kind": "visible",
            "target": {
                "tag": "div",
                "test_id": {"value": "never-appears-005", "status": "verified"},
                "css": {"value": '[data-testid="never-appears-005"]', "status": "verified"},
            },
        },
    }
]
"""실행이 **끝나지 않는** Step 하나 (005).

동시성 시나리오(AS-043)가 필요로 하는 것은 "첫 세션이 아직 살아 있는 상태" 다.
`CLOSE_TAB` 은 즉시 끝나므로 두 세션이 실제로는 겹치지 않았다 — 그런데도 그 시나리오가
통과했던 이유는 종료된 세션까지 등록만으로 다음 실행을 막았기 때문이다(U-01 의 결함).

005 가 그것을 고치면서 이 드라이버가 **주장한 것과 실제로 검증하던 것의 차이**가 드러났다.
FR-043(테스트당 동시 실행 1건) 검증을 잃지 않으려면 첫 세션이 살아 있어야 한다.
"""


@dataclass
class ApiContext:
    """열린 프로젝트를 가진 클라이언트와, 이상 조작에 필요한 상태를 만드는 도구."""

    client: TestClient
    fixture_app: str
    monkeypatch: Any

    # ─── 상태 만들기 ────────────────────────────────────────────────────────

    def session(self) -> str:
        """녹화 세션 하나. 실패하면 그 자리에서 알린다 — 조용히 건너뛰지 않는다."""
        resp = self.client.post(
            "/api/sessions",
            json={"mode": "record", "start_url": f"{self.fixture_app}/login.html"},
        )
        assert resp.status_code == 201, f"세션을 만들지 못했다: {resp.text}"
        return str(resp.json()["session_id"])

    def session_with_steps(self) -> str:
        """Step 이 하나 이상 있는 세션. 저장·순서 변경 조작의 전제다.

        Step 추가는 **일시정지 상태에서만** 받는다. 그래서 먼저 멈춘다.
        """
        sid = self.session()
        self.client.post(f"/api/sessions/{sid}/pause")
        resp = self.client.post(
            f"/api/sessions/{sid}/steps",
            json={"step": {"type": "close_tab", "id": "step-01", "label": "탭 닫기"}},
        )
        assert resp.status_code < 400, f"Step 을 넣지 못했다: {resp.text}"
        return sid

    def paused_session(self) -> str:
        sid = self.session()
        self.client.post(f"/api/sessions/{sid}/pause")
        return sid

    def finished_session(self) -> str:
        sid = self.session()
        self.client.post(f"/api/sessions/{sid}/stop")
        return sid

    def session_with_lost_browser(self) -> tuple[str, int]:
        """브라우저를 **바깥에서** 닫는다. 제품에 실패 주입 스위치를 넣지 않는다."""
        sid = self.session_with_steps()
        before = self.step_count(sid)

        async def close_it() -> None:
            session = self.client.app.state.itb.sessions.require(sid)  # type: ignore[attr-defined]
            for tab in list(session.tabs):
                with contextlib.suppress(Exception):
                    await tab.page.close()

        with contextlib.suppress(Exception):
            self.client.portal.call(close_it)  # type: ignore[attr-defined]
        return sid, before

    def saved_test(self) -> str:
        """저장된 테스트 하나. 정의를 직접 써서 브라우저 없이 만든다."""
        import pathlib

        from itb.domain.test_case import Test
        from itb.storage.repository import ProjectRepository

        root = pathlib.Path(self.client.get("/api/project").json()["root"])
        repo = ProjectRepository.open(root)
        existing = {t["id"] for t in self.client.get("/api/tests").json()["tests"]}
        test_id = f"TC-{len(existing) + 1:03d}"
        repo.write_test(
            Test(
                id=test_id,
                name=f"이상 조작용 {test_id}",
                authoring_mode="record",
                start_url=f"{self.fixture_app}/login.html",
                steps=CLOSE_TAB,
            )
        )
        return test_id

    def slow_test(self) -> str:
        """실행이 오래 걸리는 테스트 (005).

        동시성 시나리오에서 **첫 세션이 살아 있음을 보장**하기 위한 것이다.
        """
        import pathlib

        from itb.domain.test_case import Test
        from itb.storage.repository import ProjectRepository

        root = pathlib.Path(self.client.get("/api/project").json()["root"])
        repo = ProjectRepository.open(root)
        existing = {t["id"] for t in self.client.get("/api/tests").json()["tests"]}
        test_id = f"TC-{len(existing) + 1:03d}"
        repo.write_test(
            Test(
                id=test_id,
                name=f"오래 도는 {test_id}",
                authoring_mode="record",
                start_url=f"{self.fixture_app}/login.html",
                steps=SLOW_ASSERT,
            )
        )
        return test_id

    def two_tests(self) -> tuple[str, str]:
        return self.saved_test(), self.saved_test()

    # ─── 상태 재기 ──────────────────────────────────────────────────────────

    def step_count(self, session_id: str) -> int:
        resp = self.client.get(f"/api/sessions/{session_id}")
        if resp.status_code != 200:
            return -1
        return len(resp.json().get("steps", []))

    def step_ids(self, session_id: str) -> list[str]:
        resp = self.client.get(f"/api/sessions/{session_id}")
        return [s["id"] for s in resp.json().get("steps", [])] if resp.status_code == 200 else []

    # ─── 외부 경계 대역 ─────────────────────────────────────────────────────
    #
    # `create_client` 는 호출부가 모두 함수 안에서 늦게 임포트하므로, 이것 하나를
    # 바꿔치기하면 제품 코드를 고치지 않고 실패를 재현할 수 있다 (research R4).

    @contextlib.contextmanager
    def ai_failing(self) -> Iterator[None]:
        def boom() -> Any:
            raise LlmUnavailableError("검증용 대역: AI 를 쓸 수 없다")

        self.monkeypatch.setattr("itb.llm.client.create_client", boom)
        try:
            yield
        finally:
            self.monkeypatch.undo()

    @contextlib.contextmanager
    def ai_timing_out(self) -> Iterator[None]:
        def stall() -> Any:
            raise TimeoutError("검증용 대역: 응답이 제때 오지 않았다")

        self.monkeypatch.setattr("itb.llm.client.create_client", stall)
        try:
            yield
        finally:
            self.monkeypatch.undo()
