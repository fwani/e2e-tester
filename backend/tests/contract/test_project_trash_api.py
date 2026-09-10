"""프로젝트 삭제(휴지통 이동) 계약. 012 FR-409~FR-421 · contracts/api-contract.md §2.

**「목록에서 치우기」로는 관리 위치의 프로젝트를 없앨 수 없었다.** 목록이 스캔 ∪
레지스트리라서 스캔에 다시 걸려 돌아왔고, 사용자는 파일 탐색기로 직접 디렉터리를
지우는 수밖에 없었다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.execution.state_machine import SessionState
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
    root = str(resp.json()["root"])
    definition = pathlib.Path(root) / "tests" / "TC-001-로그인.yaml"
    definition.write_text("id: TC-001\n", encoding="utf-8")
    return root


def _roots(client: TestClient) -> list[str]:
    return [p["root"] for p in client.get("/api/project/list").json()["projects"]]


# ─── 성공 경로 ──────────────────────────────────────────────────────────────


def test_trashing_moves_the_project_and_reports_where(client: TestClient) -> None:
    """FR-410 — **옮겨진 위치가 되돌리는 방법 전부다.**

    204 로 끝냈다면 사용자는 되돌릴 수 없고, "지우지 않고 옮긴다" 는 이 기능의 성질이
    사용자에게는 그냥 삭제와 구별되지 않는다.
    """
    root = _create(client, "옛 프로젝트")

    resp = client.post("/api/project/trash", json={"root": root})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "옛 프로젝트"
    assert body["trashed_to"] is not None
    assert not pathlib.Path(root).exists()
    assert pathlib.Path(body["trashed_to"]).is_dir()


def test_the_test_definitions_survive_intact(client: TestClient) -> None:
    """SC-616 — `tests/*.yaml` 은 헌법 원칙 V 가 지키는 사용자 자산이다."""
    root = _create(client, "자산")

    destination = client.post("/api/project/trash", json={"root": root}).json()["trashed_to"]

    moved = pathlib.Path(destination) / "tests" / "TC-001-로그인.yaml"
    assert moved.read_text(encoding="utf-8") == "id: TC-001\n"


def test_the_project_leaves_the_listing(client: TestClient) -> None:
    """FR-413·FR-421 — 「목록에서 치우기」와 달리 스캔에 다시 걸리지 않는다."""
    root = _create(client, "옛 프로젝트")

    client.post("/api/project/trash", json={"root": root})

    assert root not in _roots(client)


def test_an_already_missing_directory_is_removed_from_the_list_only(client: TestClient) -> None:
    """FR-420 — 이미 없어진 것을 실패로 보고하지 않는다."""
    root = _create(client, "밖에서 지워진 것")
    import shutil

    shutil.rmtree(root)

    resp = client.post("/api/project/trash", json={"root": root})

    assert resp.status_code == 200, resp.text
    assert resp.json()["trashed_to"] is None
    assert root not in _roots(client)


def test_trashing_the_open_project_closes_it(client: TestClient) -> None:
    """FR-416 — 사라진 프로젝트를 가리키는 상태로 두지 않는다."""
    root = _create(client, "열려 있는 것")

    resp = client.post("/api/project/trash", json={"root": root})

    assert resp.json()["was_open"] is True
    assert client.get("/api/project").status_code == 404
    assert client.get("/api/project").json()["error"]["code"] == "PROJECT_NOT_OPEN"


# ─── 거절·실패 ──────────────────────────────────────────────────────────────


def test_unknown_paths_are_refused(client: TestClient, tmp_path: pathlib.Path) -> None:
    """FR-419 — 임의 경로를 받아 디렉터리를 옮기는 엔드포인트가 되어서는 안 된다."""
    stranger = tmp_path / "남의-폴더"
    stranger.mkdir()

    resp = client.post("/api/project/trash", json={"root": str(stranger)})

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PATH"
    assert stranger.exists()


def test_a_live_session_blocks_the_delete_without_tearing_it_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-417 · SC-621 — 거절은 요청을 받지 않은 것과 같아야 한다.

    브라우저를 닫으면서 거절하면 헌법 원칙 III(세션은 살아 있어야 한다)을 어긴다.
    """
    root = _create(client, "실행 중")

    class _Live:
        state = SessionState.PAUSED

    live = _Live()
    monkeypatch.setattr(
        type(client.app.state.itb.sessions), "all_sessions", lambda _self: [live]
    )

    resp = client.post("/api/project/trash", json={"root": root})

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PROJECT_IN_USE"
    assert resp.json()["error"]["next_action"]
    assert pathlib.Path(root).exists()
    assert root in _roots(client)


def test_a_failed_move_keeps_the_project_in_the_listing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-414 · SC-618 — **순서가 계약이다.**

    옮기기가 실패하면 레지스트리를 건드리지 않는다. 그러므로 500 을 받은 화면이 목록을
    다시 부르면 그 프로젝트가 그대로 있다. 목록에서는 사라졌는데 자산은 원래 자리에
    남는 상태는 이 계약에서 발생할 수 없다.
    """
    root = _create(client, "못 옮기는 것")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError(13, "Permission denied")

    monkeypatch.setattr("itb.storage.trash.shutil.move", boom)

    resp = client.post("/api/project/trash", json={"root": root})

    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "PROJECT_DELETE_FAILED"
    assert "그대로" in resp.json()["error"]["next_action"]
    assert pathlib.Path(root).exists()
    assert root in _roots(client)


# ─── 확인 단계가 쓸 요약 (FR-411) ──────────────────────────────────────────


def test_summary_counts_what_will_disappear(client: TestClient) -> None:
    root = _create(client, "지울 것")

    resp = client.get("/api/project/summary", params={"root": root})

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "root": root,
        "name": "지울 것",
        "test_count": 1,
        "origin": "managed",
    }


def test_summary_refuses_unknown_paths(client: TestClient, tmp_path: pathlib.Path) -> None:
    stranger = tmp_path / "남의-폴더"
    stranger.mkdir()

    resp = client.get("/api/project/summary", params={"root": str(stranger)})

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PATH"
