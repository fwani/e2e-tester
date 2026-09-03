"""T075 — 멀티 탭 재실행 (FR-030d, SC-012).

녹화 때 탭 1에서 일어난 동작은 재실행 때도 탭 1에서 일어나야 한다. 탭은 대상 앱이 여는
것이므로 실행 시점에 아직 없을 수 있다 — **기다린 뒤** 실행한다. 기다려도 열리지 않으면
"어느 탭을 기다렸는지"가 담긴 사유로 실패해야 한다. 사유가 없으면 사용자는 원인을
추측할 수밖에 없다.
"""

from __future__ import annotations

import pytest
import yaml
from fastapi.testclient import TestClient
from us2_support import record_new_tab_flow, replay, result_of


@pytest.mark.usefixtures("fixture_app")
def test_new_tab_steps_replay_on_the_right_tab(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-030d — 탭이 열리기를 기다렸다가 그 탭에서 실행한다."""
    test_id = record_new_tab_flow(keyed_client, fixture_app)

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", f"멀티 탭 재실행이 실패했다: {view['state']}"

    result = result_of(keyed_client, test_id)
    assert result["outcome"] == "pass"
    tabs_used = {s["tab"] for s in result["steps"]}
    assert 1 in tabs_used, f"탭 1에서 실행된 Step 이 없다: {tabs_used}"

    waited = [s for s in result["steps"] if s["tab"] == 1]
    assert waited, "탭 1 Step 결과가 없다"
    assert all(s["outcome"] == "pass" for s in waited), (
        f"탭 1 Step 이 실패했다: {[(s['step_id'], s['error_message']) for s in waited]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_missing_tab_fails_with_the_tab_number_in_the_reason(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-030d — 탭이 열리지 않으면 어느 탭을 기다렸는지 밝히며 실패한다.

    정의에 존재할 수 없는 탭 번호를 넣어 "탭이 안 열리는" 상황을 만든다.
    """
    test_id = record_new_tab_flow(keyed_client, fixture_app)

    repo = keyed_client.app.state.itb.repository
    path = repo.find_test_path(test_id)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    target_index = next(
        i for i, s in enumerate(raw["steps"]) if s["tab"] == 1
    )
    raw["steps"][target_index]["tab"] = 7  # 대상 앱이 열지 않는 번호
    raw["steps"][target_index]["timeout_ms"] = 1200
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")

    view = replay(keyed_client, test_id)
    assert view["state"] == "failed", f"탭이 없는데 실패하지 않았다: {view['state']}"

    result = result_of(keyed_client, test_id)
    assert result["failed_step_index"] == target_index
    failing = result["steps"][target_index]
    message = failing["error_message"] or ""
    assert "탭 7" in message, f"어느 탭을 기다렸는지가 사유에 없다: {message!r}"
    assert failing["tab_wait_ms"] > 0, (
        f"탭을 기다린 시간이 기록되지 않았다: {failing['tab_wait_ms']}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_out_of_order_tab_reference_reports_the_mismatch(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """SC-012 — 탭 순서가 녹화 때와 다르면 그 사실이 사유에 드러난다.

    탭 0 동작을 탭 2로 바꾸면, 탭 2는 결코 열리지 않는다. 사용자가 "왜 멈췄는지"를
    사유만 읽고 알 수 있어야 한다.
    """
    test_id = record_new_tab_flow(keyed_client, fixture_app)

    repo = keyed_client.app.state.itb.repository
    path = repo.find_test_path(test_id)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["steps"][0]["tab"] = 2
    raw["steps"][0]["timeout_ms"] = 1200
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")

    view = replay(keyed_client, test_id)
    assert view["state"] == "failed"

    result = result_of(keyed_client, test_id)
    assert result["failed_step_index"] == 0
    message = result["steps"][0]["error_message"] or ""
    assert "탭 2" in message, f"탭 번호가 사유에 없다: {message!r}"
    assert "순서" in message or "열리지 않" in message, (
        f"녹화 때와 다른 탭 상황임을 알 수 없는 사유다: {message!r}"
    )
    # 실패 이후 Step 은 실행하지 않는다 (FR-049).
    assert all(s["outcome"] == "not_run" for s in result["steps"][1:]), (
        "실패 후에도 실행이 계속됐다"
    )
