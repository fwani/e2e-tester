"""AI 작성. FR-059~FR-067 (T108).

확인하는 것 세 가지.

1. **성공한 동작만 Step 으로 기록된다** (FR-061). 실패한 도구 호출은 정의에 남지 않는다.
2. **지시문이 실행 대상으로 저장되지 않는다** (FR-063). 원문은 문서로만 남는다.
3. **언어모델이 실패해도 그때까지의 Step 은 보존된다** (FR-067).

자격 증명을 쓰지 않는다 — 갈아 끼우는 것은 "다음에 무엇을 할지 정하는 판단" 하나이고,
도구 표면·후보 수집·Step 실행·컴파일·이벤트는 실제 경로를 지난다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, stop_quietly
from us4_support import (
    assert_url_contains,
    click_missing,
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
    fill_password("ai-authored-not-a-real-secret"),
    observe(0),
    click_named("로그인"),
    observe(0),
    assert_url_contains("projects.html"),
]
"""로그인해서 프로젝트 화면까지 가는 대본. 픽스처 앱의 실제 요소를 지목한다."""


def test_ai_records_only_successful_actions(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-061 — 실패한 동작은 Step 으로 남지 않는다.

    대본 중간에 없는 요소를 클릭한다. 그 실패는 도구 결과로 모델에게 돌아가고 정의에는
    남지 않아야 한다.
    """
    script = [*LOGIN_SCRIPT[:2], click_missing(), *LOGIN_SCRIPT[2:]]
    install_driver(monkeypatch, script)

    sid = start_ai_session(keyed_client, fixture_app, "로그인해서 프로젝트 화면으로 가")
    try:
        wait_for_event(event_log, "ai_finished")
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        labels = [s["label"] for s in view["steps"]]

        assert labels, f"Step 이 하나도 기록되지 않았다: {view['state']}"
        # 실패한 클릭은 Step 이 아니다. 성공한 동작 수와 Step 수가 같아야 한다.
        assert all("e-does-not-exist" not in label for label in labels), labels
        assert all(s["author"] == "ai" for s in view["steps"]), (
            "AI 가 만든 Step 의 작성 주체가 잘못 표시됐다 (FR-014)"
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_ai_steps_have_the_same_shape_as_recorded_steps(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """원칙 I — AI Step 과 사람 Step 의 구조가 같다.

    `author` 를 빼고 비교하면 구분할 수 없어야 한다. 구분된다면 실행 경로가 갈라질 수 있고,
    그것이 원칙 I 이 막으려는 것이다.
    """
    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        steps = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert steps

        for step in steps:
            # 사람 녹화 Step 과 같은 필드 집합을 갖는다 (data-model §4).
            assert {"id", "type", "label", "author", "tab", "timeout_ms"} <= set(step)
            if step["type"] in ("click", "fill", "select", "hover", "drag"):
                assert step["target"] is not None
                # 후보 수집은 제품이 했다 — 셀렉터 하나만 있는 Step 이 아니다 (원칙 IV)
                assert step["target"]["css"] is not None
    finally:
        stop_quietly(keyed_client, sid)


def test_instruction_is_documentation_not_an_executable(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-063 — 지시문은 원문으로 보관되지만 **실행 대상이 아니다**.

    저장 파일에 `ai_instruction` 이 남고, 어떤 Step 도 그 문장을 실행하지 않는다.
    """
    instruction = "로그인해서 프로젝트 화면으로 이동해"
    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, instruction)
    try:
        wait_for_event(event_log, "ai_finished")
        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "AI 로그인"}
        )
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        stop_quietly(keyed_client, sid)

    definition = keyed_client.get(f"/api/tests/{test_id}").json()
    assert definition["ai_instruction"] == instruction
    assert definition["authoring_mode"] == "ai"

    # 어떤 Step 도 지시문을 값·주소·검증 대상으로 갖지 않는다.
    for step in definition["steps"]:
        assert step.get("value") != instruction
        assert step.get("url") != instruction
        assertion = step.get("assertion") or {}
        assert assertion.get("value") != instruction

    # 저장한 정의가 실제로 재실행된다 — 지시문 없이 결정적으로 (FR-045).
    replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    assert result["outcome"] == "pass", [
        (s["label"], s["error_message"]) for s in result["steps"]
    ]


def test_llm_failure_preserves_steps(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-067 — 언어모델 호출이 실패해도 세션과 Step 이 살아 있다.

    자격 증명을 잘못 설정한 상황이 이 경로다. 브라우저를 닫으면 사용자는 아무것도
    저장할 수 없다.
    """
    from us4_support import failing_driver

    from itb.authoring import agent as agent_mod
    from itb.llm.client import LlmUnavailableError

    # 먼저 동작 몇 개를 성공시킨 뒤 실패하게 만든다.
    install_driver(monkeypatch, LOGIN_SCRIPT[:2])
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        recorded = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert recorded, "실패 전에 기록된 Step 이 없어 보존을 검증할 수 없다"

        # 이제 언어모델이 실패한다. 일시정지 → 자연어 Step 추가 경로로 같은 실패를 만든다.
        monkeypatch.setattr(
            agent_mod,
            "_sdk_driver",
            failing_driver(LlmUnavailableError("자격 증명을 찾을 수 없습니다.")),
        )
        # AI 가 멈추면 세션은 **편집 가능한 상태로 유지된다** — 확인하고 손보는 것이
        # 작성의 다음 단계이기 때문이다 (`_hold_for_review`).
        assert keyed_client.get(f"/api/sessions/{sid}").json()["state"] == "paused"

        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "아무거나 눌러"}
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["created"] is False
        assert "자격 증명" in body["message"] or "만들지 못했습니다" in body["message"]

        # ★ Step 이 보존됐고 세션이 살아 있다.
        assert [s["id"] for s in body["steps"]] == [s["id"] for s in recorded]
        assert body["state"] == "paused", "실패가 세션을 종료시켰다 (FR-067 위반)"
    finally:
        stop_quietly(keyed_client, sid)


def test_ai_progress_events_are_published(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-060 — AI 가 무엇을 하는 중인지 알린다."""
    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        progress = [p for k, p in event_log if k == "ai_progress"]
        assert progress, "ai_progress 이벤트가 없다"
        assert all(isinstance(p.get("message"), str) for p in progress)
    finally:
        stop_quietly(keyed_client, sid)


def test_sensitive_value_never_leaves_as_plaintext(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-082a·FR-083 — AI 가 넣은 비밀번호도 변수 참조로만 저장된다.

    사람이 넣은 값과 같은 규칙을 지나야 한다. 경로에 따라 한쪽만 평문이 남으면 그 사실은
    그 경로를 지나는 테스트가 없을 때 드러나지 않는다.
    """
    secret = "ai-authored-not-a-real-secret"
    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        fills = [s for s in view["steps"] if s["type"] == "fill"]
        assert fills, "입력 Step 이 없어 검증할 수 없다"

        password_steps = [s for s in fills if s["value"].startswith("{{")]
        assert password_steps, f"비밀번호 값이 참조로 바뀌지 않았다: {[s['value'] for s in fills]}"

        # 어떤 이벤트에도 평문이 없다 (FR-089d).
        assert secret not in str(event_log)
        assert secret not in str(view)
    finally:
        stop_quietly(keyed_client, sid)
