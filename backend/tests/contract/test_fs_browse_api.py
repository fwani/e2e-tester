"""디렉터리 탐색 계약. DR-005. contracts/rest-api-delta.md §4.

**이 엔드포인트는 002 가 여는 유일한 새 공격면이다.** 그래서 경계 검증이 이 파일의
핵심이다 (헌법 "모든 외부 입력은 경계에서 검증").

브라우저가 절대 경로를 줄 수 없어 서버가 목록을 그린다. 그 대가로 범위를 좁게 잡는다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.secrets.keys import KeyPaths
from tests.conftest import pin_playwright_browsers


@pytest.fixture
def home(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    h = tmp_path / "home"
    (h / "work" / "proj").mkdir(parents=True)
    (h / "work" / "proj" / "itb-project.yaml").write_text("name: p\n", encoding="utf-8")
    (h / "work" / "plain").mkdir()
    (h / ".ssh").mkdir()
    (h / "work" / "notes.txt").write_text("secret notes", encoding="utf-8")
    pin_playwright_browsers(monkeypatch)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(h / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(h / ".local" / "share"))
    return h


@pytest.fixture
def client(tmp_path: pathlib.Path, home: pathlib.Path) -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        yield c


# ─── 정상 동작 ──────────────────────────────────────────────────────────────


def test_default_is_user_home(client: TestClient, home: pathlib.Path) -> None:
    body = client.get("/api/fs/browse").json()

    assert pathlib.Path(body["path"]) == home.resolve()
    assert body["parent"] is None, "홈 최상위에서 위로 올라갈 수 있으면 경계가 새어 나간다"


def test_lists_child_directories(client: TestClient, home: pathlib.Path) -> None:
    body = client.get("/api/fs/browse", params={"path": str(home / "work")}).json()

    assert {e["name"] for e in body["entries"]} == {"proj", "plain"}
    assert pathlib.Path(body["parent"]) == home.resolve()


def test_marks_which_entries_are_projects(client: TestClient, home: pathlib.Path) -> None:
    """사용자가 어디를 골라야 하는지 알려 준다."""
    body = client.get("/api/fs/browse", params={"path": str(home / "work")}).json()
    flags = {e["name"]: e["is_project"] for e in body["entries"]}

    assert flags == {"proj": True, "plain": False}


# ─── 유출 방지 ──────────────────────────────────────────────────────────────


def test_files_are_never_listed(client: TestClient, home: pathlib.Path) -> None:
    """**파일 이름조차 주지 않는다.** 탐색기가 파일 유출 통로가 되면 안 된다."""
    resp = client.get("/api/fs/browse", params={"path": str(home / "work")})

    assert "notes.txt" not in resp.text
    assert all(e["name"] != "notes.txt" for e in resp.json()["entries"])


def test_hidden_directories_are_excluded(client: TestClient) -> None:
    """`.ssh` 노출과 목록 소음을 함께 막는다."""
    body = client.get("/api/fs/browse").json()

    assert all(not e["name"].startswith(".") for e in body["entries"])
    assert ".ssh" not in [e["name"] for e in body["entries"]]


# ─── 경계 (보안) ────────────────────────────────────────────────────────────


def test_outside_home_is_rejected(client: TestClient) -> None:
    resp = client.get("/api/fs/browse", params={"path": "/etc"})

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "INVALID_PATH"


def test_dotdot_escape_is_rejected(client: TestClient, home: pathlib.Path) -> None:
    """문자열 검사만 하면 통과한다. 정규화 후에 판정해야 막힌다."""
    resp = client.get("/api/fs/browse", params={"path": str(home / ".." / ".." / "etc")})

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PATH"


def test_symlink_escape_is_rejected(
    client: TestClient, home: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    """심볼릭 링크는 따라간 뒤 **실제 위치로** 판정한다."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "loot").mkdir()
    (home / "escape").symlink_to(outside)

    resp = client.get("/api/fs/browse", params={"path": str(home / "escape")})
    assert resp.status_code == 400, resp.text

    # 목록에도 넣지 않는다 — 누를 수 있게 두면 사용자가 막히는 경험을 하게 된다.
    listing = client.get("/api/fs/browse").json()
    assert "escape" not in [e["name"] for e in listing["entries"]]


def test_nonexistent_path_is_rejected_with_reason(client: TestClient, home: pathlib.Path) -> None:
    resp = client.get("/api/fs/browse", params={"path": str(home / "nope")})

    assert resp.status_code == 400
    assert resp.json()["error"]["message"], "조용한 빈 목록은 진단할 수 없다"


def test_file_path_is_rejected(client: TestClient, home: pathlib.Path) -> None:
    resp = client.get("/api/fs/browse", params={"path": str(home / "work" / "notes.txt")})

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PATH"


def test_unreadable_directory_reports_permission(client: TestClient, home: pathlib.Path) -> None:
    """조용한 빈 목록 대신 사유를 준다."""
    locked = home / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        resp = client.get("/api/fs/browse", params={"path": str(locked)})
        assert resp.status_code == 400, resp.text
        assert "권한" in resp.json()["error"]["message"]
    finally:
        locked.chmod(0o755)


def test_response_shape_is_closed(client: TestClient) -> None:
    """계약에 없는 필드가 새어 나가지 않는다."""
    body = client.get("/api/fs/browse").json()

    assert set(body) == {"path", "parent", "entries"}
    if body["entries"]:
        assert set(body["entries"][0]) == {"name", "path", "is_project"}
