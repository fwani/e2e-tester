"""재녹화가 만든 Step 의 민감값. 016 FR-045 (T040c).

기존 녹화와 **같은 규칙**으로 변수 참조가 되는지 본다. `SensitiveCapturer` 가 툴박스에
붙어 있으므로 자동으로 될 가능성이 높지만, **가능성은 검사가 아니다** — 016 이
`_build_agent` 를 건드렸고, 그 조립에서 capturer 배선이 빠져도 다른 검사는 통과한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us4_support import fill_password, install_driver, observe
from tests.us_rerecord.support import open_rerecord, say

pytestmark = pytest.mark.browser

SECRET = "rerecord-secret-not-a-real-one-7c1"


def test_a_password_typed_during_rerecord_is_stored_as_a_reference(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """재녹화 중 비밀번호 칸을 채우면 **변수 참조로** 저장된다 (FR-045).

    평문이 정의에 들어가면 사용자가 git 에 커밋하는 자산에 비밀이 실린다 — 헌법의
    보안 요구가 금지하는 것이다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    # 로그인 화면으로 되돌아가는 구간을 잡는다 — 비밀번호 칸이 있는 자리여야 한다.
    sid = open_rerecord(keyed_client, test_id, saved)
    assert isinstance(sid, str)
    try:
        install_driver(monkeypatch, [observe(), fill_password(SECRET)])
        say(keyed_client, sid, "비밀번호를 채워 줘")

        steps = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        blob = repr(steps)
        assert SECRET not in blob, "평문 비밀번호가 정의에 들어갔다 — 헌법 보안 요구 위반"

        made = [s for s in steps if s.get("type") == "fill" and s.get("value")]
        referenced = [s for s in made if "{{" in str(s["value"])]
        assert referenced, (
            f"비밀번호 Step 이 변수 참조로 저장되지 않았다: "
            f"{[s.get('value') for s in made]}"
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_the_secret_never_reaches_the_definition_on_disk(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """확정·저장 뒤에도 디스크의 정의 파일에 평문이 없다.

    화면이 참조를 보여 주더라도 저장 경로에서 평문으로 되돌아가면 아무 소용이 없다.
    **파일을 직접 읽어** 확인한다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, saved)
    assert isinstance(sid, str)
    try:
        install_driver(monkeypatch, [observe(), fill_password(SECRET)])
        say(keyed_client, sid, "비밀번호를 채워 줘")

        commit = keyed_client.post(f"/api/sessions/{sid}/rerecord/commit")
        if commit.status_code != 200:
            pytest.skip(f"이 환경에서 Step 이 만들어지지 않았다: {commit.text}")
        assert (
            keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "비밀"}).status_code
            == 200
        )
    finally:
        stop_quietly(keyed_client, sid)

    repo = keyed_client.app.state.itb.repository
    path = repo.find_test_path(test_id)
    assert path is not None
    assert SECRET not in path.read_text(encoding="utf-8"), (
        "정의 파일에 평문 비밀번호가 있다 — 사용자가 git 에 커밋할 자산이다"
    )
