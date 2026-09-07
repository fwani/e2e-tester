"""언어모델 사용 가능 여부 계약. DR-021. contracts/rest-api-delta.md §8.

**실행 전에 알리기 위한 것이다.** 눌렀는데 아무 일도 없는 것이 이 라운드가 고치는
결함이고, 그 절반은 "쓸 수 없는 걸 쓸 수 있는 것처럼 보여 준" 데서 온다.
"""

from __future__ import annotations

import pathlib
import shutil
from collections.abc import Iterator
from importlib.util import find_spec

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.secrets.keys import KeyPaths
from tests.conftest import pin_playwright_browsers

CREDENTIAL_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")


@pytest.fixture
def client(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    pin_playwright_browsers(monkeypatch)
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        yield c


def test_shape_is_closed(client: TestClient) -> None:
    resp = client.get("/api/ai/availability")

    assert resp.status_code == 200, resp.text
    assert set(resp.json()) == {"available", "reason"}


def test_never_returns_credential_material(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**자격 증명의 어떤 조각도 응답에 들어가지 않는다** (헌법 보안 요구)."""
    secret = "sk-ant-this-must-never-appear"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)

    resp = client.get("/api/ai/availability")

    assert resp.status_code == 200
    assert secret not in resp.text


def test_available_when_credentials_resolve(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-placeholder-for-resolution-only")

    body = client.get("/api/ai/availability").json()

    assert body["available"] is True
    assert body["reason"] is None


def test_unavailable_without_credentials_still_returns_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**점검 실패를 오류로 만들지 않는다.**

    500 을 내면 화면이 또 조용해진다 — 그것이 이 라운드가 고치는 결함이다 (DR-016).
    """
    pin_playwright_browsers(monkeypatch)
    for name in CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)
    # SDK 가 사용자 홈의 로그인 프로필로 넘어가지 않게 홈도 비운다.
    monkeypatch.setenv("HOME", "/nonexistent-home-for-this-test")

    resp = client.get("/api/ai/availability")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    if body["available"] is False:
        assert body["reason"], "쓸 수 없다면 무엇을 하면 되는지 알려야 한다 (DR-021)"


def test_does_not_require_an_open_project(client: TestClient) -> None:
    """프로젝트를 열기 전에도 물어볼 수 있다. 만들기 화면이 이것으로 판단한다."""
    assert client.get("/api/project").status_code == 404
    assert client.get("/api/ai/availability").status_code == 200


def test_replay_path_does_not_import_the_llm_boundary() -> None:
    """**원칙 II** — 이 엔드포인트가 재실행 경로를 오염시키지 않았는지 확인한다.

    `.importlinter` 가 빌드에서 강제하지만, 여기서도 확인해 두면 계약이 깨진 순간을
    테스트가 먼저 잡는다.
    """
    import importlib

    execution = importlib.import_module("itb.execution.session")
    module_names = {
        getattr(value, "__module__", "") for value in vars(execution).values()
    }
    assert not any(name.startswith("itb.llm") for name in module_names)
    assert not any(name.startswith("itb.authoring") for name in module_names)


# ─── 개발용 드라이버 (ITB_AI_DRIVER=claude-code) ──────────────────────────────
# 이 분기가 없으면 개발용 드라이버로 돌려도 화면은 "자격 증명 없음" 을 계속 보여주고
# 버튼이 잠긴 채로 남는다 — 백엔드는 되는데 화면에서 안 되는 상태다.


def test_claude_code_driver_ignores_api_credentials(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """개발용 드라이버가 켜져 있으면 **API 자격 증명을 보지 않는다.**

    키가 하나도 없어도 `claude` 가 있으면 쓸 수 있다 — 그것이 이 스위치의 목적이다.
    """
    for name in CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", "/nonexistent-home-for-this-test")
    monkeypatch.setenv("ITB_AI_DRIVER", "claude-code")

    body = client.get("/api/ai/availability").json()

    if shutil.which("claude") is not None and find_spec("claude_agent_sdk") is not None:
        assert body["available"] is True
        assert body["reason"] is None
    else:
        # 준비가 안 된 환경에서는 **무엇을 하면 되는지** 말해야 한다 (DR-021).
        assert body["available"] is False
        assert body["reason"]


def test_claude_code_driver_reports_missing_executable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`claude` 가 없으면 사유가 그것을 지목한다."""
    monkeypatch.setenv("ITB_AI_DRIVER", "claude-code")
    monkeypatch.setattr("itb.api.routes.ai.shutil.which", lambda _name: None)

    body = client.get("/api/ai/availability").json()

    assert body["available"] is False
    assert "claude" in body["reason"]


def test_claude_code_driver_shape_stays_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """드라이버를 바꿔도 응답 모양은 그대로다 — REST 계약을 건드리지 않았다."""
    monkeypatch.setenv("ITB_AI_DRIVER", "claude-code")

    resp = client.get("/api/ai/availability")

    assert resp.status_code == 200, resp.text
    assert set(resp.json()) == {"available", "reason"}


def test_unrecognised_driver_value_uses_the_default_path(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """오타는 개발용 분기를 켜지 않는다. 자격 증명을 실제로 해석해야 한다."""
    monkeypatch.setenv("ITB_AI_DRIVER", "claude_code")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-placeholder-for-resolution-only")

    body = client.get("/api/ai/availability").json()

    assert body["available"] is True
