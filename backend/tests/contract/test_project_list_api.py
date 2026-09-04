"""프로젝트 목록·등록 계약. DR-002·DR-003·DR-004·DR-006·DR-007·DR-009.

첫 화면이 이것으로 그려진다. 이 엔드포인트가 없어서 사용자가 절대 경로를 타이핑해야
했고, 그래서 아무도 기존 프로젝트를 열지 못했다 (research R4).
"""

from __future__ import annotations

import pathlib
import shutil
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.secrets.keys import KeyPaths
from tests.conftest import pin_playwright_browsers

START_URL = "http://127.0.0.1:4300/login.html"


@pytest.fixture
def home(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    h = tmp_path / "home"
    h.mkdir(parents=True)
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


def _create(client: TestClient, name: str) -> str:
    resp = client.post(
        "/api/project/create", json={"name": name, "default_start_url": START_URL}
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["root"])


# ─── 목록 ──────────────────────────────────────────────────────────────────


def test_empty_list_is_200_not_an_error(client: TestClient) -> None:
    """프로젝트가 없는 첫 실행은 정상이다. 404 면 화면이 오류를 그린다."""
    resp = client.get("/api/project/list")

    assert resp.status_code == 200
    assert resp.json() == {"projects": [], "warning": None}


def test_created_project_appears_in_list(client: TestClient) -> None:
    """SC-101 — 만든 프로젝트가 목록에 나타난다."""
    root = _create(client, "데이터 플랫폼")

    projects = client.get("/api/project/list").json()["projects"]
    assert [(p["name"], p["root"]) for p in projects] == [("데이터 플랫폼", root)]
    assert projects[0]["origin"] == "managed"
    assert projects[0]["accessible"] is True


def test_list_survives_restart(client: TestClient, tmp_path: pathlib.Path, home: pathlib.Path) -> None:
    """**이것이 이 라운드의 핵심이다.** 서버를 다시 띄워도 목록이 남아야 한다.

    이전에는 열린 프로젝트가 프로세스 메모리에만 있어 재시작하면 사라졌다.
    """
    _create(client, "재시작 후에도")

    with TestClient(create_app()) as fresh:
        fresh.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        projects = fresh.get("/api/project/list").json()["projects"]

    assert [p["name"] for p in projects] == ["재시작 후에도"]


def test_sorted_by_last_opened_descending(client: TestClient) -> None:
    """DR-004."""
    for name in ("첫째", "둘째", "셋째"):
        _create(client, name)

    projects = client.get("/api/project/list").json()["projects"]
    stamps = [p["last_opened_at"] for p in projects]
    assert stamps == sorted(stamps, reverse=True)


def test_externally_opened_project_is_remembered(client: TestClient, home: pathlib.Path) -> None:
    """DR-007 — 관리 위치 밖에서 연 프로젝트도 다음에 목록에 나온다."""
    outside = home / "elsewhere" / "mine"
    outside.mkdir(parents=True)
    (outside / "itb-project.yaml").write_text(
        f"name: 외부 프로젝트\ndefault_start_url: {START_URL}\n", encoding="utf-8"
    )

    assert client.post("/api/project/open", json={"path": str(outside)}).status_code == 200

    projects = client.get("/api/project/list").json()["projects"]
    assert [(p["name"], p["origin"]) for p in projects] == [("외부 프로젝트", "external")]


def test_inaccessible_project_is_marked_not_hidden(client: TestClient, home: pathlib.Path) -> None:
    """DR-009 — 사라진 프로젝트를 조용히 빼지 않는다. 왜 못 여는지 알려준다."""
    outside = home / "gone"
    outside.mkdir()
    (outside / "itb-project.yaml").write_text(f"name: 사라질 것\ndefault_start_url: {START_URL}\n", encoding="utf-8")
    client.post("/api/project/open", json={"path": str(outside)})

    shutil.rmtree(outside)  # 열면서 .gitignore·tests/ 가 생기므로 통째로 지운다

    projects = client.get("/api/project/list").json()["projects"]
    assert len(projects) == 1
    assert projects[0]["accessible"] is False
    assert projects[0]["unavailable_reason"]


# ─── 생성 (DR-001·DR-006) ───────────────────────────────────────────────────


def test_create_reports_where_it_made_the_project(client: TestClient, home: pathlib.Path) -> None:
    """DR-006 — 사용자가 위치를 정하지 않으므로, 어디에 만들어졌는지 알려줘야 한다."""
    root = pathlib.Path(_create(client, "어디에"))

    assert root.is_dir()
    assert (home / ".local" / "share" / "itb" / "projects") in root.parents


def test_create_does_not_accept_a_path(client: TestClient) -> None:
    """SC-102 — 경로 입력이 계약에서 사라졌다."""
    resp = client.post(
        "/api/project/create",
        json={"name": "x", "default_start_url": START_URL, "path": "/anywhere"},
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["detail"]["fields"][0]["loc"] == "path"


def test_hostile_name_stays_inside_workspace(client: TestClient, home: pathlib.Path) -> None:
    """이름이 경로가 되는 지점이다 (헌법 보안 요구)."""
    root = pathlib.Path(_create(client, "../../etc/passwd"))

    assert (home / ".local" / "share" / "itb" / "projects") in root.parents


# ─── 목록에서 치우기 (DR-009) ───────────────────────────────────────────────


def test_forget_removes_external_entry_but_keeps_files(
    client: TestClient, home: pathlib.Path
) -> None:
    """목록 정리와 자산 삭제는 다른 조작이다."""
    outside = home / "keepme"
    outside.mkdir()
    (outside / "itb-project.yaml").write_text(f"name: 유지\ndefault_start_url: {START_URL}\n", encoding="utf-8")
    client.post("/api/project/open", json={"path": str(outside)})

    resp = client.request("DELETE", "/api/project/registry", json={"root": str(outside)})

    assert resp.status_code == 204
    assert client.get("/api/project/list").json()["projects"] == []
    assert (outside / "itb-project.yaml").exists(), "디스크의 프로젝트를 지웠다"


def test_forget_managed_project_still_found_by_scan(client: TestClient) -> None:
    """관리 위치에 실재하면 스캔에 다시 걸린다. 정상이다 — 목록은 스캔 ∪ 레지스트리다."""
    root = _create(client, "관리 대상")

    client.request("DELETE", "/api/project/registry", json={"root": root})

    projects = client.get("/api/project/list").json()["projects"]
    assert [p["root"] for p in projects] == [root]


# ─── RG-003 — 기존에 저장된 프로젝트·테스트가 그대로 열린다 ─────────────────


def test_project_made_before_002_still_opens(client: TestClient, home: pathlib.Path) -> None:
    """RG-003 — 저장 위치가 바뀌어도 예전 위치의 프로젝트를 열 수 있다.

    002 는 **새로 만드는 곳**을 정했을 뿐 기존 자산을 옮기지 않는다. 사용자가 001 로
    만들어 둔 프로젝트는 임의 위치에 있고, 「기존 프로젝트 열기」로 찾아 열면 된다.
    옮기거나 요구했다면 그것이야말로 회귀다.
    """
    legacy = home / "old-place" / "my-project"
    (legacy / "tests").mkdir(parents=True)
    (legacy / "itb-project.yaml").write_text(
        f"name: 001 때 만든 것\ndefault_start_url: {START_URL}\n", encoding="utf-8"
    )
    (legacy / "tests" / "TC-001-login.yaml").write_text(
        "id: TC-001\n"
        "name: 로그인\n"
        "authoring_mode: record\n"
        f"start_url: {START_URL}\n"
        "variables: []\n"
        "steps:\n"
        "  - id: step-01\n"
        "    type: navigate\n"
        "    label: 시작\n"
        "    author: human\n"
        "    tab: 0\n"
        "    timeout_ms: 5000\n"
        f"    url: {START_URL}\n",
        encoding="utf-8",
    )

    opened = client.post("/api/project/open", json={"path": str(legacy)})
    assert opened.status_code == 200, opened.text
    assert opened.json()["name"] == "001 때 만든 것"

    # 저장된 테스트 정의가 그대로 읽힌다.
    listing = client.get("/api/tests")
    assert listing.status_code == 200, listing.text
    assert "로그인" in [t["name"] for t in listing.json()["tests"]]

    definition = client.get("/api/tests/TC-001")
    assert definition.status_code == 200, definition.text
    assert definition.json()["steps"][0]["type"] == "navigate"
