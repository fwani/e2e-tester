"""US7 종단 테스트 — quickstart §9 (T136).

Step 이 **어떤 기준으로 요소를 찾는지** 사용자가 확인하고 고칠 수 있어야 한다.
원칙 IV 가 사용자에게 노출되는 지점이며, 그 노출이 정확해야 "다시 집기" 가 의미를 갖는다.

화면 자체(`StepInspector.tsx`)는 프론트 테스트가 본다. 여기서는 **화면이 그릴 데이터가
맞는지** 를 종단으로 확인한다 — 후보와 상태가 실제 수집 결과이고, 정의 파일과 일치하며,
다시 집기가 그 데이터를 갱신한다.
"""

from __future__ import annotations

import yaml
from fastapi.testclient import TestClient
from us2_support import replay, result_of, start_replay, stop_quietly
from us3_support import pause_after, record_login_then_two_menus

from itb.domain.locator import TargetLocator
from itb.locator.display import DisplayState, display_states
from itb.locator.strategy import StrategyKind


def test_quickstart_section9_step_inspector(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """§9 1~6단계."""
    client = keyed_client
    test_id = record_login_then_two_menus(client, fixture_app)
    definition = client.get(f"/api/tests/{test_id}").json()

    # 1·2단계 — 후보가 우선순위와 함께 있고, 상태는 **기록 시점 검증 결과**다
    click_step = next(s for s in definition["steps"] if s["type"] == "click")
    target = TargetLocator.model_validate(click_step["target"])
    states = display_states(target)
    assert set(states) == {
        StrategyKind.TEST_ID,
        StrategyKind.ROLE,
        StrategyKind.LABEL,
        StrategyKind.TEXT,
        StrategyKind.STABLE_ATTR,
        StrategyKind.CSS,
    }
    assert any(state == DisplayState.IN_USE for state in states.values()), states

    # 3단계 — `data-testid` 없는 요소는 `test_id` 가 `수집되지 않음` 이고 다음 후보가 쓰인다
    password_step = next(
        s
        for s in definition["steps"]
        if s["type"] == "fill" and "비밀번호" in s["label"]
    )
    pw_target = TargetLocator.model_validate(password_step["target"])
    pw_states = display_states(pw_target)
    assert pw_states[StrategyKind.TEST_ID] == DisplayState.NOT_COLLECTED, (
        "픽스처 앱의 비밀번호 필드에는 data-testid 가 없다 (README 의 표)"
    )
    in_use = [k for k, v in pw_states.items() if v == DisplayState.IN_USE]
    assert in_use and in_use[0] != StrategyKind.TEST_ID, pw_states

    # 4단계 — 화면이 보여 줄 값이 정의 파일과 일치한다 (FR-016)
    repo = client.app.state.itb.repository
    raw = yaml.safe_load(repo.find_test_path(test_id).read_text(encoding="utf-8"))
    file_target = next(s for s in raw["steps"] if s["type"] == "click")["target"]
    assert file_target == click_step["target"]

    # 5단계 — 표시 이름·입력값을 고치면 목록과 파일에 반영된다
    sid = start_replay(client, test_id)
    try:
        view = pause_after(client, sid, finished_steps=1, events=event_log)
        editable = next(s for s in view["steps"] if s["type"] == "fill")
        patched = client.patch(
            f"/api/sessions/{sid}/steps/{editable['id']}",
            json={"label": "로그인 이메일 입력", "timeout_ms": 8000},
        )
        assert patched.status_code == 200, patched.text

        # 6단계 — "다시 집기" 로 후보를 갱신한다
        click_in_session = next(s for s in view["steps"] if s["type"] == "click")
        repicked = client.post(
            f"/api/sessions/{sid}/steps/{click_in_session['id']}/repick",
            json={"selector": "[data-testid=login-submit]"},
        )
        assert repicked.status_code == 200, repicked.text
        assert repicked.json()["waiting"] is False

        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "상세 편집"})
        assert saved.status_code == 200, saved.text
    finally:
        stop_quietly(client, sid)

    after = client.get(f"/api/tests/{test_id}").json()
    assert any(s["label"] == "로그인 이메일 입력" for s in after["steps"])
    assert any(s.get("timeout_ms") == 8000 for s in after["steps"])

    file_after = yaml.safe_load(repo.find_test_path(test_id).read_text(encoding="utf-8"))
    assert any(s["label"] == "로그인 이메일 입력" for s in file_after["steps"])

    # 고친 정의가 여전히 실행된다 — 편집이 테스트를 깨지 않았다
    view = replay(client, test_id)
    result = result_of(client, test_id)
    assert view["state"] == "completed", [
        (s["label"], s["outcome"], s["error_message"]) for s in result["steps"]
    ]
