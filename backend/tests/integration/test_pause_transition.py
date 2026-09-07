"""일시정지 전이 (005 T048·T049 · FR-142·FR-146).

리포트 U-04 는 화면 문제로 보였지만, 화면이 진실을 말할 **근거가 없다**는 것이 절반이었다.
세션 뷰는 `state=paused` 만 주고, "요청은 갔지만 아직 Step 경계에 닿지 않았다" 는 사실을
어디에도 담지 않았다. 그래서 화면은 요청 즉시 정지라고 말할 수밖에 없었다.

`pause_settled` 가 그 근거다.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient
from us2_support import record_login, start_replay, stop_quietly, wait_for_run


def test_pause_settled_is_true_when_not_paused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """일시정지 상태가 아니면 `pause_settled` 는 참이다.

    "전이 중이 아니다" 가 맞는 답이다. 거짓을 기본값으로 두면 실행 중 화면이 전이 표시를
    켠다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["pause_settled"] is True, view["state"]
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_pause_settles_and_view_says_so(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """정지가 성립하면 `pause_settled` 가 참이 된다 (FR-142).

    화면은 이 값으로 전이 표시를 걷고 편집 팔레트를 연다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        # Step 하나가 끝난 뒤 일시정지를 요청한다.
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if sum(1 for t, _ in event_log if t == "step_finished") >= 1:
                break
            keyed_client.get(f"/api/sessions/{sid}")
            time.sleep(0.05)

        paused = keyed_client.post(f"/api/sessions/{sid}/pause")
        assert paused.status_code == 200, paused.text
        body = paused.json()
        if body["state"] == "paused":
            # 경계에 닿았으면 성립이다. 짧은 Step 이므로 대개 이 경로다.
            assert body["pause_settled"] is True, (
                "경계에 닿았는데 전이 중으로 보고했다 — 화면이 전이 표시를 걷지 못한다"
            )
        else:
            # 멈추기 전에 실행이 끝난 경우다 (FR-146). 그때는 결말 상태여야 한다.
            assert body["state"] in {"completed", "failed"}, body["state"]
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_paused_session_keeps_browser_alive(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """일시정지에서 브라우저 세션은 살아 있다 (헌법 원칙 III · 불변식 1).

    005 는 처음에 `PAUSED → COMPLETED/FAILED` 전이를 더하려 했다. 불변식 1 테스트가
    그것을 거절했고 **그 거절이 옳다** — 실행이 끝났다고 해서 사용자가 고쳐서 다시 돌릴
    세션을 빼앗을 이유가 없다.

    문제의 정체는 전이가 아니라 두 축(실행 결말 · 세션 상태)을 한 값으로 읽은 것이었다.
    이 테스트가 그 결정을 고정한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if sum(1 for t, _ in event_log if t == "step_finished") >= 1:
                break
            keyed_client.get(f"/api/sessions/{sid}")
            time.sleep(0.05)
        view = keyed_client.post(f"/api/sessions/{sid}/pause").json()
        if view["state"] != "paused":
            return  # 멈추기 전에 끝났다 — 이 검증의 전제가 성립하지 않는다

        session = keyed_client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "일시정지에서 탭이 사라졌다 — 원칙 III 위반"
        assert "edit_steps" in view["allowed_commands"], (
            "일시정지에서 편집이 허용되지 않는다 — 원칙 III 위반"
        )
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_step_results_survive_a_fresh_view(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """세션 뷰가 Step별 결과를 싣는다 (FR-171 · U-18·U-05).

    화면을 다시 그려도 그때까지의 결과가 남아야 한다. 이전에는 이벤트로만 채워지는
    로컬 상태에 있어 모든 Step 이 빈 체크박스가 됐다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        wait_for_run(keyed_client, sid)
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        results = view["step_results"]
        assert results, "세션 뷰에 Step 결과가 없다 — 화면은 이벤트 없이 복원할 수 없다"
        assert all("step_id" in r and "outcome" in r for r in results), results
        # 아직 돌지 않은 Step 은 싣지 않는다 — 없는 것을 있는 것처럼 보이지 않게.
        assert all(r["outcome"] != "not_run" for r in results), results
    finally:
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")
