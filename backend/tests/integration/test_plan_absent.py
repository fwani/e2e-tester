"""계획이 없어도 돈다 — 025 의 회귀 방어선 (T036 · FR-012).

## 이 파일이 존재하는 이유

025 는 기존 작성 경로 위에 얹힌다. 얹힌 것이 아래를 막으면 이 기능은 값이 아니라 비용이다.

계획 없이 시작되는 경로가 넷이다.

| 경로 | 왜 계획이 없는가 |
|---|---|
| 정제를 거절한 세션 | 사용자가 원문으로 진행을 골랐다 (FR-019) |
| 정제가 실패한 세션 | 모델 오류·응답 이상 (FR-020) |
| 구간 재녹화 | 이미 저장된 테스트를 다루므로 계획이 성립하지 않는다 |
| 녹화에서 시작해 대화로 넘어온 세션 | 애초에 지시문이 없었다 |

넷 다 **016 이전과 정확히 같이** 동작해야 한다.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly
from us4_support import (
    assert_url_contains,
    click_named,
    fill_named,
    fill_password,
    install_driver,
    observe,
    start_ai_session,
    wait_for_event,
)

LOGIN_SCRIPT = [
    observe(0),
    fill_named("이메일", "tester@example.com"),
    fill_password("not-a-real-secret"),
    observe(0),
    click_named("로그인"),
    observe(0),
    assert_url_contains("projects.html"),
]


def test_ai_session_without_a_plan_works_as_before(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """계획 없이 시작한 AI 작성이 끝까지 간다.

    이것이 깨지면 025 는 기존 사용자의 작업을 막는 기능이 된다.
    """
    install_driver(monkeypatch, LOGIN_SCRIPT)

    session_id = start_ai_session(keyed_client, fixture_app, "로그인한다")
    finished = wait_for_event(event_log, "ai_finished")

    assert finished["step_count"] >= 3, "계획 없이도 Step 이 만들어져야 한다"

    stop_quietly(keyed_client, session_id)


def test_injection_without_a_plan_matches_the_old_shape(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**계획이 없으면 붙는 것이 016 이전과 같다.**

    「지금 테스트」 하나만 붙고, 그 앞에 아무것도 없어야 한다. 빈 줄이나 빈 머리표가
    붙으면 모델은 그것을 「비어 있는 무엇」으로 읽는다.
    """
    seen: list[list[dict[str, Any]]] = []

    def spy(tools: list[Any], messages: list[dict[str, Any]], _config: Any):
        seen.append([dict(m) for m in messages])

        async def run() -> Any:
            for action in [observe(0)]:
                name, kwargs = action({})
                await next(t for t in tools if t.name == name).call(kwargs)
            yield _Msg("끝냈습니다.")

        return run()

    from itb.authoring import agent as agent_mod

    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = start_ai_session(keyed_client, fixture_app, "화면을 확인한다")
    wait_for_event(event_log, "ai_finished")

    assert seen, "드라이버가 불리지 않았다"
    first = str(seen[0][0]["content"])

    assert first.startswith("[지금 테스트]"), (
        f"계획이 없는데 앞에 무언가 붙었다: {first[:80]!r}"
    )
    assert "[반드시 지킬 것]" not in first
    assert "[할 일]" not in first

    stop_quietly(keyed_client, session_id)


def test_work_plan_is_refused_outside_ai_mode(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """녹화 모드에 계획이 오면 **조용히 무시하지 않고 거절한다**.

    무시하면 사용자는 계획이 쓰이고 있다고 믿고, 그 믿음은 AI 가 계획을 어길 때까지
    깨지지 않는다 — 그런데 애초에 AI 가 돌지 않는 세션이다.
    """
    refused = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "record",
            "start_url": f"{fixture_app}/login.html",
            "work_plan": {"items": [], "constraints": [], "source": "refined"},
        },
    )

    assert refused.status_code == 400, refused.text
    assert "AI 작성에서만" in refused.text


class _Msg:
    def __init__(self, text: str) -> None:
        self.content = [_Blk(text)]
        self.stop_reason = "end_turn"


class _Blk:
    def __init__(self, text: str) -> None:
        self.text = text
        self.type = "text"
