"""진척이 이어진다 — 어디까지 했는지를 제품이 들고 간다 (025 US5 · T059·T060).

## 이 파일이 확인하는 것

「해야 할 구획을 건너뛴다」와 「이미 한 일을 다시 한다」가 여기서 멈춘다.

가장 중요한 것은 **완료 보고가 남은 일을 덮지 않는다**는 것이다 (FR-028). 모델은
「끝냈다」고 말할 수 있고 실제로 구획 하나를 건너뛰었을 수 있다 — 제품이 센 값이 모델의
말을 이긴다 (022 FR-003 과 같은 판단).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly
from us4_support import observe, wait_for_event

PLAN = {
    "items": [
        {"id": "i1", "order": 1, "text": "로그인한다", "status": "pending"},
        {"id": "i2", "order": 2, "text": "메뉴관리로 이동한다", "status": "pending"},
        {"id": "i3", "order": 3, "text": "새 메뉴를 등록한다", "status": "pending"},
    ],
    "constraints": [{"text": "기존 데이터는 검증에 쓰지 않는다", "scope": "global"}],
    "source": "refined",
}


def _start(client: TestClient, fixture_app: str, plan: dict[str, Any] | None = PLAN) -> str:
    body: dict[str, Any] = {
        "mode": "ai",
        "start_url": f"{fixture_app}/login.html",
        "ai_instruction": "메뉴를 등록한다",
    }
    if plan is not None:
        body["work_plan"] = plan
    created = client.post("/api/sessions", json=body)
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])


class _Spy:
    """대본을 돌리며 모델이 받은 이력을 기록한다."""

    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.turns: list[list[dict[str, Any]]] = []

    def __call__(self, tools: list[Any], messages: list[dict[str, Any]], _c: Any):
        self.turns.append([dict(m) for m in messages])
        by_name = {t.name: t for t in tools}
        script = self.script

        async def run() -> Any:
            state: dict[str, Any] = {}
            for action in script:
                planned = action(state)
                if planned is None:
                    continue
                name, kwargs = planned
                result = await by_name[name].call(kwargs)
                if name == "observe_page" and isinstance(result, dict):
                    state = result
            yield _Msg("끝냈습니다.")

        return run()


def mark(item_id: str, status: str = "done", reason: str | None = None):
    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        args: dict[str, Any] = {"item_id": item_id, "status": status}
        if reason:
            args["reason"] = reason
        return ("mark_item", args)

    return action


def test_plan_is_injected_with_progress(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**계획과 진척이 매 턴 주입된다** (FR-008·FR-011)."""
    from itb.authoring import agent as agent_mod

    spy = _Spy([observe(0), mark("i1"), mark("i2")])
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = _start(keyed_client, fixture_app)
    wait_for_event(event_log, "ai_finished")

    first = str(spy.turns[0][0]["content"])
    assert "[반드시 지킬 것]" in first
    assert "기존 데이터는 검증에 쓰지 않는다" in first
    assert "[할 일]" in first
    assert "▶" in first, "다음 할 일을 제품이 지목해야 한다"
    assert "[지금 테스트]" in first, "016 의 주입이 함께 있어야 한다 (FR-011)"

    stop_quietly(keyed_client, session_id)


def test_marking_does_not_spend_the_budget(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**표시는 예산을 쓰지 않는다** (research R9).

    예산을 쓰게 하면 성실히 표시할수록 할 수 있는 일이 줄어들고, 그러면 모델은 표시를
    덜 하게 된다 — 진척은 다시 비어 간다.
    """
    from itb.authoring import agent as agent_mod

    marks = [mark(f"i{n}") for n in (1, 2, 3)]
    spy = _Spy([observe(0), *marks])
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = _start(keyed_client, fixture_app)
    finished = wait_for_event(event_log, "ai_finished")

    # 관찰 한 번만 예산을 썼다. 표시 세 번은 세지 않는다.
    assert finished.get("tool_calls", 1) <= 1 or True  # 이벤트에 없으면 아래로 확인
    from itb.api.routes.sessions import _WORK  # noqa: PLC0415

    work = _WORK[session_id]
    assert work.toolbox is not None
    assert work.toolbox.limits.calls == 1, (
        f"표시가 예산을 썼다 (호출 {work.toolbox.limits.calls}회). "
        "mark_item 은 record_call() 을 지나지 않아야 한다."
    )

    stop_quietly(keyed_client, session_id)


def test_finish_reports_what_is_left(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**완료 보고가 남은 일을 덮지 않는다** (FR-028).

    모델은 「끝냈다」고 말했지만 세 항목 중 하나만 표시했다. 그 사실이 사용자에게 보여야
    한다 — 제품이 센 값이 모델의 말을 이긴다.
    """
    from itb.authoring import agent as agent_mod

    spy = _Spy([observe(0), mark("i1")])
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = _start(keyed_client, fixture_app)
    finished = wait_for_event(event_log, "ai_finished")

    remaining = finished.get("remaining_items")
    assert remaining, "남은 항목이 실리지 않았다 — 완료 보고가 남은 일을 덮고 있다"
    assert {r["order"] for r in remaining} == {2, 3}

    stop_quietly(keyed_client, session_id)


def test_no_plan_means_no_remaining_field(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """계획이 없으면 남은 항목도 싣지 않는다.

    **없는 것을 0 으로 알리지 않는다** — 화면이 「남은 일 0건」을 표시할지 다시 판단해야
    한다 (020 이 `mismatch_count` 에서 정한 것과 같다).
    """
    from itb.authoring import agent as agent_mod

    spy = _Spy([observe(0)])
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = _start(keyed_client, fixture_app, plan=None)
    finished = wait_for_event(event_log, "ai_finished")

    assert "remaining_items" not in finished

    stop_quietly(keyed_client, session_id)


def test_user_can_revert_what_the_model_marked(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """사용자는 되돌릴 수 있고, 그 사실이 같은 통로로 알려진다 (FR-025)."""
    from itb.authoring import agent as agent_mod

    spy = _Spy([observe(0), mark("i1")])
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = _start(keyed_client, fixture_app)
    wait_for_event(event_log, "ai_finished")

    before = keyed_client.get(f"/api/sessions/{session_id}/plan").json()
    assert before["remaining"] == 2

    patched = keyed_client.patch(
        f"/api/sessions/{session_id}/plan/items/i1", json={"status": "pending"}
    )

    assert patched.status_code == 200, patched.text
    assert patched.json()["remaining"] == 3
    progress = [p for k, p in event_log if k == "plan_progress"]
    assert progress, "되돌리기가 이벤트로 알려지지 않았다"
    assert progress[-1]["status"] == "pending"

    stop_quietly(keyed_client, session_id)


def test_skipping_without_a_reason_is_refused(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**사유 없는 건너뜀은 거절된다** (FR-027).

    거절 사유가 모델에게 돌아가야 한다 — 조용히 무시하면 모델은 표시됐다고 믿고 넘어간다.
    """
    from itb.authoring import agent as agent_mod

    spy = _Spy([observe(0), mark("i1", "skipped")])
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = _start(keyed_client, fixture_app)
    wait_for_event(event_log, "ai_finished")

    plan = keyed_client.get(f"/api/sessions/{session_id}/plan").json()
    statuses = {i["id"]: i["status"] for i in plan["plan"]["items"]}

    assert statuses["i1"] == "pending", "사유 없는 건너뜀이 받아들여졌다"

    stop_quietly(keyed_client, session_id)


class _Msg:
    def __init__(self, text: str) -> None:
        self.content = [_Blk(text)]
        self.stop_reason = "end_turn"


class _Blk:
    def __init__(self, text: str) -> None:
        self.text = text
        self.type = "text"
