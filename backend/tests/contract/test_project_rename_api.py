"""프로젝트 표시 이름 변경 계약. 012 FR-399~FR-408 · contracts/api-contract.md §1.

**프로젝트만 이름을 못 고쳤다.** 테스트에는 이름 변경이 있는데(`PATCH /api/tests/{id}`)
프로젝트에는 없어서, 잘못 지은 이름을 고치려면 새 프로젝트를 만들고 `tests/*.yaml` 을
손으로 옮기는 수밖에 없었다.
"""

from __future__ import annotations

import json
import pathlib
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
    resp = client.post("/api/project/create", json={"name": name, "default_start_url": START_URL})
    assert resp.status_code == 201, resp.text
    return str(resp.json()["root"])


def _row(client: TestClient, root: str) -> dict[str, object]:
    listing = client.get("/api/project/list").json()["projects"]
    return next(p for p in listing if p["root"] == root)


# ─── 성공 경로 ──────────────────────────────────────────────────────────────


def test_rename_changes_the_displayed_name(client: TestClient) -> None:
    root = _create(client, "임시")

    resp = client.patch("/api/project/name", json={"root": root, "name": "결제 회귀"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "결제 회귀"
    assert _row(client, root)["name"] == "결제 회귀"


def test_rename_writes_both_the_project_file_and_the_registry(
    client: TestClient, home: pathlib.Path
) -> None:
    """FR-401 — 한쪽만 바뀌면 다음 조회에서 되돌아간 것처럼 보인다.

    레지스트리 사본이 필요한 이유는 그 프로젝트가 나중에 **접근 불가가 됐을 때**다.
    그때 목록은 저장된 이름으로 떨어진다 (012 research R1).
    """
    root = _create(client, "임시")

    client.patch("/api/project/name", json={"root": root, "name": "결제 회귀"})

    project_file = pathlib.Path(root) / "itb-project.yaml"
    assert "결제 회귀" in project_file.read_text(encoding="utf-8")

    stored = json.loads((home / ".config" / "itb" / "registry.json").read_text(encoding="utf-8"))
    entry = next(p for p in stored["projects"] if p["root"] == root)
    assert entry["name"] == "결제 회귀"


def test_rename_does_not_reorder_the_list(client: TestClient) -> None:
    """`last_opened_at` 이 변하지 않는 것이 계약의 일부다 (012 research R2).

    목록은 그 값의 역순으로 정렬한다. 이름만 고쳤는데 맨 위로 올라오면 "최근 연 순"
    이라는 목록의 약속이 깨진다 — 이름을 고치는 것은 여는 행위가 아니다.
    """
    first = _create(client, "먼저")
    second = _create(client, "나중")
    before = _row(client, first)["last_opened_at"]

    client.patch("/api/project/name", json={"root": first, "name": "이름만 바뀐다"})

    assert _row(client, first)["last_opened_at"] == before
    # 나중에 만든 것이 여전히 맨 위다.
    assert client.get("/api/project/list").json()["projects"][0]["root"] == second


def test_rename_to_the_same_name_does_not_touch_the_file(client: TestClient) -> None:
    """FR-407 — 같은 값을 쓰지 않는다.

    파일을 건드리면 mtime 이 바뀌고, 그것을 보고 있는 것들이 이유 없이 반응한다.
    """
    root = _create(client, "그대로")
    project_file = pathlib.Path(root) / "itb-project.yaml"
    before = project_file.stat().st_mtime_ns

    resp = client.patch("/api/project/name", json={"root": root, "name": "그대로"})

    assert resp.status_code == 200
    assert project_file.stat().st_mtime_ns == before


def test_renaming_the_open_project_keeps_it_open(client: TestClient) -> None:
    """FR-404·FR-405 — 경로가 바뀌지 않으므로 열린 채로 남는다."""
    root = _create(client, "열려 있는 것")

    client.patch("/api/project/name", json={"root": root, "name": "새 이름"})

    current = client.get("/api/project")
    assert current.status_code == 200
    assert current.json()["name"] == "새 이름"
    assert current.json()["root"] == root


# ─── 거절 경로 ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["", "   ", "가" * 101])
def test_empty_or_oversized_names_are_rejected(client: TestClient, name: str) -> None:
    """FR-403 — 만들기와 같은 규칙이다. 공백뿐인 이름이 통과하면 이름 없는 줄이 남는다."""
    root = _create(client, "임시")

    resp = client.patch("/api/project/name", json={"root": root, "name": name})

    assert resp.status_code == 422, resp.text
    assert _row(client, root)["name"] == "임시"


def test_unknown_paths_are_refused(client: TestClient, tmp_path: pathlib.Path) -> None:
    """FR-419 — 임의 경로를 받아 파일을 쓰는 엔드포인트가 되어서는 안 된다."""
    stranger = tmp_path / "남의-폴더"
    stranger.mkdir()

    resp = client.patch("/api/project/name", json={"root": str(stranger), "name": "x"})

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PATH"


def test_a_registry_write_is_skipped_when_the_project_file_cannot_be_written(
    client: TestClient, home: pathlib.Path
) -> None:
    """FR-402 — 파일이 실패하면 레지스트리를 건드리지 않는다.

    반대로 하면 목록의 이름과 파일의 이름이 갈라지고, 사용자는 고쳤다고 믿은 이름이
    다음 조회에서 되돌아가는 것을 본다.
    """
    root = _create(client, "임시")
    project_file = pathlib.Path(root) / "itb-project.yaml"
    original_mode = project_file.parent.stat().st_mode
    project_file.parent.chmod(0o500)  # 디렉터리에 쓸 수 없다 → 원자적 바꿔치기 실패

    try:
        resp = client.patch("/api/project/name", json={"root": root, "name": "새 이름"})
    finally:
        project_file.parent.chmod(original_mode)

    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "STORAGE_WRITE_FAILED"

    stored = json.loads((home / ".config" / "itb" / "registry.json").read_text(encoding="utf-8"))
    entry = next(p for p in stored["projects"] if p["root"] == root)
    assert entry["name"] == "임시"
