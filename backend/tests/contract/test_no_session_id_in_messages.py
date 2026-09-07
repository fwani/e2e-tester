"""005 T114 — 사용자에게 보이는 문구에 세션 식별자를 넣지 않는다 (FR-135 · 재점검 U-03-b).

리포트가 본 것은 중지 직후 화면의 붉은 배너 "세션을 찾을 수 없습니다: f345e93a…" 였다.
내부 UUID 는 사용자가 할 수 있는 일과 아무 관계가 없고, 화면을 읽는 사람에게는 잡음이자
불안 신호다. 게다가 그 404 는 **사용자가 방금 한 일(중지)의 정상적인 결과**였다.

T046 이 `sessions.py` 의 `work_of` 를 고쳤지만 `tabs.py` 는 `str(exc)` 를 그대로 올렸고,
`SessionError` 의 문장에는 진단을 위해 UUID 가 들어 있다. 그래서 재점검은 같은 배너를
다시 봤다 — 실측 404 3건.

**엔드포인트 하나를 고치는 것으로는 부족하다.** 이 파일은 세션 식별자로 조회하는 경로
전부를 훑어, `message` 에 UUID 가 실리지 않는지 본다. 식별자가 필요한 화면은
`detail.session_id` 에서 받는다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

GONE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
"""없는 세션의 식별자. 형태는 실제 UUID 와 같게 둔다 — 짧은 문자열을 쓰면 문구에
섞여 들어가도 눈에 띄지 않는다."""

# 세션 식별자를 경로에 받는 조회·명령. 없는 세션에 오면 전부 404 다.
SESSION_PATHS = [
    ("GET", f"/api/sessions/{GONE}"),
    ("GET", f"/api/sessions/{GONE}/tabs"),
    ("POST", f"/api/sessions/{GONE}/mirror-tab"),
    ("POST", f"/api/sessions/{GONE}/pause"),
    ("POST", f"/api/sessions/{GONE}/resume"),
    ("POST", f"/api/sessions/{GONE}/stop"),
]


@pytest.mark.parametrize(("method", "path"), SESSION_PATHS)
def test_message_never_carries_the_session_id(
    keyed_client: TestClient, method: str, path: str
) -> None:
    """FR-135 — `message` 에 세션 UUID 가 없다."""
    body = {"tab_index": 0} if path.endswith("mirror-tab") else None
    response = keyed_client.request(method, path, json=body)
    assert response.status_code == 404, f"{method} {path} → {response.status_code}"

    error = response.json()["error"]
    # 화면이 배너로 그리는 두 줄이다 (`ErrorNotice`: message + next_action).
    shown = f"{error['message']} {error.get('next_action') or ''}"
    assert GONE not in shown, (
        f"{method} {path} 의 문구에 세션 식별자가 들어 있다. 화면은 이것을 배너로 "
        f"띄운다: {shown}"
    )


@pytest.mark.parametrize(("method", "path"), SESSION_PATHS)
def test_identifier_is_available_in_detail(
    keyed_client: TestClient, method: str, path: str
) -> None:
    """식별자를 **버리지는 않는다.**

    진단과 "그 세션으로 이동" 같은 화면 동작에는 식별자가 필요하다. 규칙은 "없애라" 가
    아니라 "사용자에게 보이는 문구에 넣지 마라" 다 — `detail` 이 그 자리다.
    """
    body = {"tab_index": 0} if path.endswith("mirror-tab") else None
    response = keyed_client.request(method, path, json=body)
    detail = response.json()["error"].get("detail") or {}
    assert detail.get("session_id") == GONE, (
        f"{method} {path} 가 식별자를 어디에도 남기지 않았다 — 진단할 근거가 없다: {detail}"
    )


def test_same_fact_is_said_the_same_way(keyed_client: TestClient) -> None:
    """FR-141 — 같은 사실을 두 엔드포인트가 다른 말로 부르지 않는다.

    같은 사실에 다른 문장을 주면 사용자는 다른 일이 일어난 줄 안다. `tabs.py` 가
    `sessions.py` 와 다른 문장을 쓰던 것이 이 결함의 절반이었다.
    """
    view = keyed_client.get(f"/api/sessions/{GONE}").json()["error"]["message"]
    tabs = keyed_client.get(f"/api/sessions/{GONE}/tabs").json()["error"]["message"]
    assert view == tabs, f"세션 조회는 {view!r}, 탭 조회는 {tabs!r} 라고 말한다"
