"""키의 위치와 영향 범위를 **있는 그대로** 말한다 (UX U-09).

워크스루에서 겪은 것: ``XDG_CONFIG_HOME`` 을 격리해 띄웠는데 제품은 사용자의 실제
``~/.config/itb/keys`` 를 읽어 테스트의 비밀값을 봉인했다. 화면은 고정 문구로 그 경로를
안내했고, 「키 교체」 경고는 "이 프로젝트의 암호문" 만 언급했다 — 실제로는 키가 장비에
하나라 다른 모든 프로젝트의 암호문이 함께 못 읽는 상태가 된다.

되돌릴 수 없는 조작의 경고가 실제 영향 범위보다 좁게 말하면 안 된다.
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from itb.secrets.keys import default_key_dir


def test_key_dir_follows_xdg_config_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """설정 디렉터리와 같은 규칙이다. 한쪽만 환경 변수를 따르면 격리가 거짓이 된다."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    assert default_key_dir() == tmp_path / "cfg" / "itb" / "keys"

    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert default_key_dir() == pathlib.Path.home() / ".config" / "itb" / "keys"


def test_key_status_reports_real_dir_and_blast_radius(
    client: TestClient, tmp_path: pathlib.Path
) -> None:
    key_dir = tmp_path / "keys"  # conftest 가 이 위치로 돌려 둔다

    before = client.get("/api/keys/status").json()
    assert before["key_dir"] == str(key_dir), "화면이 찍을 실제 경로가 없다"
    assert before["sealed_projects"] == [], "키도 없는데 영향받는 프로젝트가 있다고 한다"

    # 프로젝트를 열고 키를 만들고 값을 하나 봉인한다 — 이제 이 프로젝트는 키에 묶였다.
    created = client.post(
        "/api/project/create",
        json={"name": "봉인된 프로젝트", "default_start_url": "http://127.0.0.1:1/"},
    )
    assert created.status_code == 201, created.text
    assert client.post("/api/keys/generate", json={}).status_code == 201
    sealed = client.put("/api/secrets/PASSWORD", json={"value": "not-a-real-secret"})
    assert sealed.status_code == 204, sealed.text

    after = client.get("/api/keys/status").json()
    assert after["sealed_projects"] == ["봉인된 프로젝트"], (
        f"교체·삭제 경고가 영향 범위를 말할 수 없다: {after['sealed_projects']}"
    )

    # 값이 없는 프로젝트는 키에 묶이지 않았다 — 영향 범위에 넣으면 겁만 준다.
    assert client.delete("/api/secrets/PASSWORD").status_code == 204
    assert client.get("/api/keys/status").json()["sealed_projects"] == []
