"""2026-09-10 사용자 보고 1·2번의 계약.

## 1번 — 「a 프로젝트에서 새 테스트를 만들었는데 b 프로젝트 목록에 들어갔다」

원인은 시작 URL 이 아니다. 서버는 열린 프로젝트를 **하나만** 들고 있고 (`AppState.
repository`), 화면은 자기가 보는 프로젝트를 따로 기억한다. 둘이 갈라지는 경로가
실재한다 — `POST /api/project/create` 는 만드는 즉시 서버를 새 프로젝트로 옮기는데,
화면에서 「계속」 대신 「돌아가기」를 누르면 화면은 이전 프로젝트에 남는다.

여기서 지키는 것: 요청이 `X-ITB-Project-Root` 로 자기가 믿는 프로젝트를 말하면, 다르면
**아무 일도 하기 전에** 409 `PROJECT_MISMATCH` 다. 헤더가 없으면 지금까지 그대로다.

## 2번 — 「번호를 일괄적으로 맞추거나 재조정하는 방법이 있으면 좋겠다」

여기서 지키는 것: 빈자리가 사라지고, 접두어와 상대 순서는 그대로이며, 두 번 해도 같다.
"""

from __future__ import annotations

import pathlib
import urllib.parse
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.api.state import PROJECT_ROOT_HEADER
from itb.secrets.keys import KeyPaths
from tests.conftest import pin_playwright_browsers

CLOSE_TAB = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]
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
    return resp.json()["root"]


def _repo(root: str):  # noqa: ANN202
    from itb.storage.repository import ProjectRepository

    return ProjectRepository.open(pathlib.Path(root))


def _write(root: str, test_id: str, name: str) -> None:
    from itb.domain.test_case import Test

    _repo(root).write_test(
        Test(
            id=test_id,
            name=name,
            authoring_mode="record",
            start_url=START_URL,
            steps=CLOSE_TAB,
        )
    )


# ─── 1번: 프로젝트 대조 ─────────────────────────────────────────────────────


def test_create_switches_open_project(client: TestClient) -> None:
    """만들기가 서버의 열린 프로젝트를 옮긴다 — **이것이 갈라짐의 출처다.**

    동작을 바꾸지 않고 사실로 못박는다. 여기를 바꾸면 계약 테스트 다수가 이 전제 위에
    서 있으므로 함께 무너진다 (`conftest.py` 의 `project_client`).
    """
    _create(client, "a")
    root_b = _create(client, "b")
    assert client.get("/api/project").json()["root"] == root_b


def test_mismatched_header_is_refused_before_anything_happens(client: TestClient) -> None:
    root_a = _create(client, "a")
    _create(client, "b")  # 서버가 b 로 옮겨 갔다

    resp = client.get("/api/tests", headers={PROJECT_ROOT_HEADER: root_a})

    assert resp.status_code == 409, resp.text
    error = resp.json()["error"]
    assert error["code"] == "PROJECT_MISMATCH"
    assert error["category"] == "blocked"
    assert error["detail"]["expected_root"] == root_a


def test_matching_header_passes(client: TestClient) -> None:
    root_a = _create(client, "a")
    assert client.get("/api/tests", headers={PROJECT_ROOT_HEADER: root_a}).status_code == 200


def test_no_header_keeps_previous_behaviour(client: TestClient) -> None:
    """헤더가 없으면 대조하지 않는다 — 기존 클라이언트와 `curl` 이 그대로 돈다."""
    _create(client, "a")
    _create(client, "b")
    assert client.get("/api/tests").status_code == 200


def test_percent_encoded_header_is_understood(client: TestClient) -> None:
    """헤더는 **퍼센트 인코딩**되어 온다 — 한글 프로젝트 이름이 흔하기 때문이다.

    HTTP 헤더 값은 ISO-8859-1 이고 프로젝트 디렉터리 이름에는 한글이 들어간다
    (`storage/paths.py` 의 `slugify` 가 한글을 남긴다). 인코딩하지 않으면 브라우저가
    `fetch` 자체를 거절해 **요청이 나가지도 않는다** — 실측으로 확인했다.
    """
    root = _create(client, "한글 프로젝트")
    assert "한글" in root

    encoded = urllib.parse.quote(root)
    assert client.get("/api/tests", headers={PROJECT_ROOT_HEADER: encoded}).status_code == 200

    _create(client, "다른 것")
    refused = client.get("/api/tests", headers={PROJECT_ROOT_HEADER: encoded})
    assert refused.status_code == 409
    assert refused.json()["error"]["detail"]["expected_root"] == root


def test_project_routes_are_exempt(client: TestClient) -> None:
    """프로젝트를 바꾸는 조작 자체는 막지 않는다 — 막으면 화면이 프로젝트를 옮길 수 없다."""
    root_a = _create(client, "a")
    _create(client, "b")

    resp = client.post(
        "/api/project/open", json={"path": root_a}, headers={PROJECT_ROOT_HEADER: root_a}
    )

    assert resp.status_code == 200, resp.text
    assert client.get("/api/project").json()["root"] == root_a


# ─── 2번: 번호 재정렬 ───────────────────────────────────────────────────────


def _ids(client: TestClient) -> list[str]:
    return [t["id"] for t in client.get("/api/tests").json()["tests"]]


def test_renumber_closes_gaps(client: TestClient) -> None:
    root = _create(client, "번호")
    for test_id, name in [("TC-001", "하나"), ("TC-002", "둘"), ("TC-005", "셋"), ("TC-009", "넷")]:
        _write(root, test_id, name)

    resp = client.post("/api/tests:renumber")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unchanged"] == 2
    assert [(m["from_id"], m["to_id"]) for m in body["renumbered"]] == [
        ("TC-005", "TC-003"),
        ("TC-009", "TC-004"),
    ]
    assert _ids(client) == ["TC-001", "TC-002", "TC-003", "TC-004"]


def test_renumber_numbers_each_group_from_one(client: TestClient) -> None:
    """접두어는 그대로고, **그룹마다 1번부터** 다시 매긴다 (014 3차 요청).

    프로젝트 전체에 이어 붙이면 `USER` 가 2~3 에서 시작해, 사용자가 「그룹마다 1번부터」로
    정한 뜻과 어긋난다.
    """
    root = _create(client, "그룹")
    client.post("/api/groups", json={"prefix": "USER", "name": "사용자"})
    _write(root, "TC-002", "묶이지 않은 것")
    _write(root, "USER-004", "사용자 것")
    _write(root, "USER-007", "사용자 것 둘")

    assert client.post("/api/tests:renumber").status_code == 200

    assert sorted(_ids(client)) == ["TC-001", "USER-001", "USER-002"]


def test_renumber_keeps_order_within_a_group(client: TestClient) -> None:
    """그룹 안에서는 지금 번호가 작은 순서를 지킨다."""
    root = _create(client, "순서")
    client.post("/api/groups", json={"prefix": "USER", "name": "사용자"})
    _write(root, "USER-009", "나중 것")
    _write(root, "USER-002", "먼저 것")

    assert client.post("/api/tests:renumber").status_code == 200

    listing = client.get("/api/tests").json()["tests"]
    by_id = {t["id"]: t["name"] for t in listing}
    assert by_id["USER-001"] == "먼저 것"
    assert by_id["USER-002"] == "나중 것"


def test_renumber_moves_run_artifacts_with_the_test(client: TestClient) -> None:
    """정의만 옮기면 사용자에게는 **결과가 사라진 것**으로 보인다 (013 research R5)."""
    root = _create(client, "산출물")
    _write(root, "TC-001", "하나")
    _write(root, "TC-004", "둘")
    runs = _repo(root).paths.run_dir("TC-004")
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "marker.json").write_text("{}", encoding="utf-8")

    assert client.post("/api/tests:renumber").status_code == 200

    assert (_repo(root).paths.run_dir("TC-002") / "marker.json").exists()
    assert not _repo(root).paths.run_dir("TC-004").exists()


def test_renumber_is_idempotent(client: TestClient) -> None:
    root = _create(client, "멱등")
    _write(root, "TC-003", "하나")

    assert client.post("/api/tests:renumber").status_code == 200
    second = client.post("/api/tests:renumber").json()

    assert second == {"renumbered": [], "unchanged": 1}
    assert _ids(client) == ["TC-001"]


def test_renumber_refuses_when_a_definition_is_unreadable(client: TestClient) -> None:
    """건너뛴 파일의 번호는 **빈자리로 보인다** — 그 자리에 다른 테스트가 들어가면 겹친다."""
    root = _create(client, "깨진 것")
    _write(root, "TC-001", "하나")
    _write(root, "TC-005", "둘")
    (_repo(root).paths.tests_dir / "TC-003-깨진것.yaml").write_text(
        "id: TC-003\nname: 깨진 것\n", encoding="utf-8"
    )

    resp = client.post("/api/tests:renumber")

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    assert _ids(client) == ["TC-001", "TC-005"]


def test_renumber_leaves_the_project_openable_with_many_groups(client: TestClient) -> None:
    """번호 정리가 프로젝트 파일을 못 읽게 만들지 않는다 (014 수렴 2회차).

    번호를 그룹마다 세게 되면서 그룹 둘이 각각 600개를 가질 수 있게 됐다. 정리 뒤
    `next_test_number` 에 전체 수(1201)를 쓰면 `le=999` 검증에 걸려, **다음에 그 파일을
    읽는 순간 프로젝트가 열리지 않는다.** 쓰기는 조용히 성공하므로 그때는 드러나지 않는다.

    600개를 만드는 대신 상한을 넘길 수 있는 최소 구성으로 같은 성질을 본다 — 정리 뒤에도
    프로젝트를 다시 읽을 수 있어야 한다.
    """
    root = _create(client, "많은 그룹")
    client.post("/api/groups", json={"prefix": "USER", "name": "사용자"})
    client.post("/api/groups", json={"prefix": "DATA", "name": "데이터"})
    _write(root, "USER-005", "가")
    _write(root, "DATA-009", "나")
    _write(root, "TC-003", "다")

    assert client.post("/api/tests:renumber").status_code == 200

    # 다시 읽을 수 있어야 한다 — 여기서 500 이 나면 파일이 깨진 것이다.
    assert client.get("/api/project").status_code == 200
    assert client.get("/api/tests").status_code == 200
    assert sorted(_ids(client)) == ["DATA-001", "TC-001", "USER-001"]


def test_renumber_does_not_touch_the_legacy_counter(client: TestClient) -> None:
    """읽지도 않는 값을 쓰지 않는다 (014 수렴 2회차)."""
    root = _create(client, "카운터")
    _write(root, "TC-004", "하나")

    before = _repo(root).read_project().next_test_number
    assert client.post("/api/tests:renumber").status_code == 200
    assert _repo(root).read_project().next_test_number == before
