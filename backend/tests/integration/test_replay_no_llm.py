"""T071 — 재실행 경로에 언어모델이 없다 (SC-006, 헌법 원칙 II 동적 검증).

임포트 경계(import-linter)는 **정적** 보증이다. 이 파일은 **동적** 보증을 맡는다:
실제 재실행을 한 번 돌리는 동안 `anthropic` 클라이언트가 한 번도 만들어지지 않았는지 본다.

정적 검사만으로 충분해 보이지만 그렇지 않다. `importlib` 로 지연 임포트하거나 실행 경로가
API 계층을 우회해 언어모델에 닿는 경로는 임포트 계약이 잡지 못한다. 두 검사가 겹치더라도
서로 놓치는 곳이 다르다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, result_of


def _spy_on_llm_clients(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`anthropic` 클라이언트 생성마다 이름을 기록하는 스파이를 심는다."""
    import anthropic

    constructions: list[str] = []
    for class_name in ("Anthropic", "AsyncAnthropic"):
        cls = getattr(anthropic, class_name, None)
        if cls is None:  # pragma: no cover - SDK 구조가 바뀐 경우
            continue
        original = cls.__init__

        def spy(self, *args, _name=class_name, _original=original, **kwargs):  # noqa: ANN001, ANN202
            constructions.append(_name)
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", spy)
    assert constructions == []
    return constructions


@pytest.mark.usefixtures("fixture_app")
def test_replay_never_constructs_an_llm_client(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-006 — 재실행 중 언어모델 클라이언트 생성 0건."""
    constructions = _spy_on_llm_clients(monkeypatch)

    test_id = record_login(keyed_client, fixture_app)
    assert not constructions, "녹화 단계에서 이미 언어모델 클라이언트가 생성됐다"

    view = replay(keyed_client, test_id)

    assert view["state"] == "completed", f"재실행이 통과하지 않았다: {view['state']}"
    assert not constructions, (
        f"재실행 중 언어모델 클라이언트가 {len(constructions)}회 생성됐다 "
        f"({constructions}) — 헌법 원칙 II 위반"
    )
    assert result_of(keyed_client, test_id)["outcome"] == "pass"


@pytest.mark.usefixtures("fixture_app")
def test_replay_session_emits_no_ai_events(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """contracts/websocket.md — `replay` 세션에서 `ai_*` 이벤트가 관측되면 원칙 II 위반."""
    test_id = record_login(keyed_client, fixture_app)
    event_log.clear()  # 녹화 단계의 이벤트는 검사 대상이 아니다

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", f"재실행이 통과하지 않았다: {view['state']}"

    ai_events = [name for name, _ in event_log if name.startswith("ai_")]
    assert not ai_events, f"replay 세션에서 AI 이벤트가 나왔다: {ai_events}"
    assert any(name == "step_finished" for name, _ in event_log), (
        f"실행 이벤트 자체가 없다 — 검증이 성립하지 않는다: "
        f"{sorted({n for n, _ in event_log})}"
    )
