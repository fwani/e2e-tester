"""헌법 원칙 II — **시간 축**에서 본다. 016 T014·T015 (research R9 · 불변식 6).

## 왜 린터만으로 부족한가

`.importlinter` 의 `execution-no-llm` 계약은 `itb.execution → itb.authoring` 임포트를
막는다. 그것은 **구조적 도달 불가**를 보장하지만, `itb.api` 는 그 계약의
`source_modules` 에 없다. 그래서 API 계층이 러너를 돌리는 **동시에** 에이전트를 돌리는
코드를 써도 린터는 통과한다.

원칙 II 가 금지하는 것은 임포트가 아니라 **재실행 중 언어모델 호출**이다. 따라서 시간
축의 검사가 필요하다.

## 016 이 이 파일을 만든 이유

016 은 `PAUSED + BEGIN_AI → AI_RUNNING` 전이를 더하면서, 옛 단언
(`test_paused_from_replay_cannot_reach_ai_states`)을 좁혔다. 그 단언은 **상태 이름**을
지키고 있었고, 이름을 우회하는 경로(`ai_step`, US6)는 이미 통과하고 있었다.

여기 있는 검사는 이름이 아니라 **호출**을 본다. 약화가 아니라 교체이며, 이쪽이 더 강하다.

## 무엇을 세는가

`AuthoringAgent.driver` 교체 지점(`itb.authoring.agent._sdk_driver`)에 **호출 횟수를
세는 가짜 드라이버**를 끼운다. 실제 도구·후보 수집·Step 실행은 그대로 돌고, 대체되는
것은 「다음에 무엇을 할지 정하는 판단」뿐이다 — 그 판단만이 언어모델의 몫이다.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly

pytestmark = pytest.mark.browser


# ─── 호출을 세는 가짜 드라이버 ──────────────────────────────────────────────


class DriverLedger:
    """드라이버가 언제 몇 번 불렸는지 기록한다.

    시각까지 남기는 이유는 **겹침**을 보려는 것이기 때문이다. 횟수만 세면 「러너가
    끝난 뒤 불렸는지」와 「도는 중에 불렸는지」를 구별할 수 없다.
    """

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __len__(self) -> int:
        return len(self.calls)

    def since(self, mark: float) -> int:
        return sum(1 for t in self.calls if t >= mark)


class _Msg:
    def __init__(self, text: str) -> None:
        self.content = [_Text(text)]
        self.stop_reason = "end_turn"


class _Text:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


@pytest.fixture
def ledger(monkeypatch: pytest.MonkeyPatch) -> Iterator[DriverLedger]:
    """드라이버 호출을 세는 원장을 끼운다.

    **아무 도구도 부르지 않는다.** 이 파일이 보려는 것은 「불렸는가」이지 「무엇을
    했는가」가 아니다. 도구를 부르면 Step 이 생기고, 그러면 실패 원인이 둘이 된다.
    """
    from itb.authoring import agent as agent_mod

    book = DriverLedger()

    def counting_driver(_tools: list[Any], _messages: list[Any], _config: Any) -> Any:
        book.calls.append(time.monotonic())

        async def run() -> Any:
            yield _Msg("확인했습니다.")

        return run()

    monkeypatch.setattr(agent_mod, "_sdk_driver", counting_driver)
    yield book


# ─── T014 — 도착점 만들기 구간에서 드라이버 호출 0회 ────────────────────────


def test_reaching_the_arrival_point_never_calls_the_driver(
    keyed_client: TestClient, fixture_app: str, ledger: DriverLedger
) -> None:
    """`mode=rerecord` 세션을 만드는 동안 **언어모델이 한 번도 불리지 않는다** (FR-019).

    이 구간은 저장된 Step 을 러너가 실행하는 구간이다 — 원칙 II 가 말하는 재실행
    그대로이며, 재녹화라는 이름이 붙었다고 달라지지 않는다.
    """
    test_id = record_login(keyed_client, fixture_app)
    steps = keyed_client.get(f"/api/tests/{test_id}").json()["steps"]
    assert len(steps) >= 2, "구간을 고르려면 Step 이 둘 이상 필요하다"

    created = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "rerecord",
            "test_id": test_id,
            "rerecord_step_ids": [steps[-1]["id"]],
        },
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        _wait_until_paused(keyed_client, sid)
        assert len(ledger) == 0, (
            f"도착점 만들기 구간에서 드라이버가 {len(ledger)}회 불렸다 — 원칙 II 위반. "
            "러너가 멈춘 뒤에 에이전트를 만들어야 한다 (api-contract §1 의 순서)."
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_a_plain_replay_never_calls_the_driver(
    keyed_client: TestClient, fixture_app: str, ledger: DriverLedger
) -> None:
    """저장된 테스트를 그냥 실행하는 것도 마찬가지다 (기존 보장의 재확인).

    016 이 세션 생성 분기를 건드렸으므로, 손대지 않은 경로가 그대로인지 함께 본다.
    """
    test_id = record_login(keyed_client, fixture_app)
    created = keyed_client.post(
        "/api/sessions", json={"mode": "replay", "test_id": test_id}
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        _wait_until_settled(keyed_client, sid)
        assert len(ledger) == 0, "재실행에서 드라이버가 불렸다 — 원칙 II 위반"
    finally:
        stop_quietly(keyed_client, sid)


# ─── T015 — 러너와 에이전트 태스크의 생존 구간이 겹치지 않는다 (불변식 6) ───


def test_runner_and_agent_never_live_at_the_same_time(
    keyed_client: TestClient, fixture_app: str, ledger: DriverLedger
) -> None:
    """**불변식 6.** 한 세션에서 러너가 도는 동안 에이전트 태스크는 살아 있지 않다.

    이것이 원칙 II 를 시간 축에서 표현한 것이다. 구조(임포트)로는 막을 수 없는 자리이며,
    `itb.api` 가 두 태스크를 모두 띄울 수 있기 때문에 필요하다.

    검사 방법: 세션이 살아 있는 동안 짧은 주기로 두 태스크의 생존을 함께 본다. 둘이
    동시에 살아 있는 순간이 한 번이라도 관측되면 실패다.
    """
    test_id = record_login(keyed_client, fixture_app)
    steps = keyed_client.get(f"/api/tests/{test_id}").json()["steps"]

    created = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "rerecord",
            "test_id": test_id,
            "rerecord_step_ids": [steps[-1]["id"]],
        },
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        overlaps = _watch_for_overlap(keyed_client, sid, until_paused=True)
        assert overlaps == [], (
            f"러너와 에이전트 태스크가 동시에 살아 있었다 ({len(overlaps)}회 관측) — "
            "불변식 6 위반이며 원칙 II 를 시간 축에서 깬다."
        )
    finally:
        stop_quietly(keyed_client, sid)


def _work_of(client: TestClient, sid: str) -> Any:
    from itb.api.routes.sessions import _WORK

    return _WORK.get(sid)


def _watch_for_overlap(
    client: TestClient, sid: str, until_paused: bool, timeout_s: float = 90.0
) -> list[float]:
    """세션이 일시정지에 닿을 때까지 지켜보며 겹침을 기록한다."""
    seen: list[float] = []
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        work = _work_of(client, sid)
        if work is not None:
            runner_alive = work.runner is not None and work.runner.running
            task = work.agent_task
            agent_alive = task is not None and not task.done()
            if runner_alive and agent_alive:
                seen.append(time.monotonic())
        state = client.get(f"/api/sessions/{sid}").json()["state"]
        if until_paused and state == "paused":
            return seen
        if state in {"completed", "failed", "stopped", "lost", "review"}:
            return seen
        time.sleep(0.02)
    pytest.fail(f"세션이 제 시간에 멈추지 않았다 (sid={sid})")
    raise AssertionError  # pragma: no cover


def _wait_until_paused(client: TestClient, sid: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = client.get(f"/api/sessions/{sid}").json()["state"]
        if state == "paused":
            return
        if state in {"failed", "stopped", "lost", "review"}:
            pytest.fail(f"도착점에 닿기 전에 세션이 끝났다: {state}")
        time.sleep(0.05)
    pytest.fail("도착점에 닿지 못했다")


def _wait_until_settled(client: TestClient, sid: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = client.get(f"/api/sessions/{sid}").json()["state"]
        if state in {"completed", "failed", "stopped", "lost", "review", "paused"}:
            return
        time.sleep(0.05)
    pytest.fail("실행이 끝나지 않았다")
