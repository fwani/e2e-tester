"""테스트 복수 삭제 계약. 013 FR-426~FR-437 · contracts/api-contract.md §2·§3.

**Step 에는 011 이 복수 삭제를 만들었는데 테스트에는 없었다.** 11개를 정리하려면 확인을
11번 거쳐야 했다.

이 파일이 지키는 것은 두 가지다.

1. **전부 되거나 전부 안 되거나** (FR-432). 파일 시스템에는 여러 경로에 걸친 원자적 연산이
   없다 — 삭제를 휴지통 이동으로 정한 결정이 이것을 가능하게 했다 (research R4).
2. **한 개와 여러 개의 결과가 같다** (SC-632). 같은 이름의 조작이 개수에 따라 결과가
   달라지면 사용자는 「삭제」 하나를 두 가지로 배워야 한다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
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
def opened(tmp_path: pathlib.Path, home: pathlib.Path) -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        resp = c.post(
            "/api/project/create", json={"name": "계약 프로젝트", "default_start_url": START_URL}
        )
        assert resp.status_code == 201, resp.text
        yield c


def _repo(client: TestClient):  # noqa: ANN202
    from itb.storage.repository import ProjectRepository

    return ProjectRepository.open(pathlib.Path(client.get("/api/project").json()["root"]))


def _write(client: TestClient, test_id: str, name: str) -> None:
    from itb.domain.test_case import Test

    _repo(client).write_test(
        Test(
            id=test_id,
            name=name,
            authoring_mode="record",
            start_url=START_URL,
            steps=CLOSE_TAB,
        )
    )


def _ids(client: TestClient) -> list[str]:
    return [t["id"] for t in client.get("/api/tests").json()["tests"]]


# ─── 성공 경로 ──────────────────────────────────────────────────────────────


def test_three_go_and_the_rest_stay(opened: TestClient) -> None:
    for i, name in enumerate(("하나", "둘", "셋", "넷", "다섯"), start=1):
        _write(opened, f"TC-{i:03d}", name)

    resp = opened.post("/api/tests:delete", json={"test_ids": ["TC-001", "TC-003", "TC-005"]})

    assert resp.status_code == 200, resp.text
    assert [d["id"] for d in resp.json()["deleted"]] == ["TC-001", "TC-003", "TC-005"]
    assert _ids(opened) == ["TC-002", "TC-004"]


def test_the_definitions_survive_in_the_trash(opened: TestClient) -> None:
    """SC-631 — `tests/*.yaml` 은 헌법 원칙 V 가 지키는 사용자 자산이다."""
    _write(opened, "TC-001", "로그인")

    body = opened.post("/api/tests:delete", json={"test_ids": ["TC-001"]}).json()

    entry = pathlib.Path(body["deleted"][0]["trashed_to"])
    assert entry.is_dir()
    kept = list(entry.glob("TC-001-*.yaml"))
    assert kept, f"정의가 휴지통에 없다: {list(entry.iterdir())}"
    assert "로그인" in kept[0].read_text(encoding="utf-8")


def test_one_and_many_have_the_same_result(opened: TestClient) -> None:
    """SC-632 — 「삭제」가 개수에 따라 뜻이 달라지면 안 된다."""
    _write(opened, "TC-001", "하나로")
    _write(opened, "TC-002", "여럿으로")

    single = opened.delete("/api/tests/TC-001").json()
    many = opened.post("/api/tests:delete", json={"test_ids": ["TC-002"]}).json()["deleted"][0]

    assert pathlib.Path(single["trashed_to"]).is_dir()
    assert pathlib.Path(many["trashed_to"]).is_dir()
    assert list(pathlib.Path(single["trashed_to"]).glob("*.yaml"))
    assert list(pathlib.Path(many["trashed_to"]).glob("*.yaml"))


def test_the_run_artifacts_go_too(opened: TestClient) -> None:
    _write(opened, "TC-001", "결과 있는 것")
    runs = _repo(opened).paths.run_dir("TC-001")
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "result.json").write_text('{"x": 1}', encoding="utf-8")

    body = opened.post("/api/tests:delete", json={"test_ids": ["TC-001"]}).json()

    assert not runs.exists()
    assert (pathlib.Path(body["deleted"][0]["trashed_to"]) / "runs" / "result.json").exists()


# ─── 거절·실패 ──────────────────────────────────────────────────────────────


def test_an_unknown_id_stops_everything(opened: TestClient) -> None:
    """FR-432 — **먼저 전부 검증한다.** 하나가 없으면 아무것도 건드리지 않는다."""
    _write(opened, "TC-001", "있는 것")

    resp = opened.post("/api/tests:delete", json={"test_ids": ["TC-001", "TC-404"]})

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"
    assert _ids(opened) == ["TC-001"], "검증에서 걸렸는데 무언가 지워졌다"


def test_duplicate_ids_are_refused(opened: TestClient) -> None:
    _write(opened, "TC-001", "하나")

    resp = opened.post("/api/tests:delete", json={"test_ids": ["TC-001", "TC-001"]})

    assert resp.status_code == 400
    assert _ids(opened) == ["TC-001"]


def test_a_running_test_blocks_all_of_them_without_tearing_it_down(
    opened: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-433 · SC-624·SC-630 — 하나도 지워지지 않고, 거절이 세션을 끊지 않는다."""
    _write(opened, "TC-001", "실행 중")
    _write(opened, "TC-002", "멀쩡한 것")

    manager = type(opened.app.state.itb.sessions)
    monkeypatch.setattr(
        manager,
        "active_session_for_test",
        lambda _self, test_id: "sess-1" if test_id == "TC-001" else None,
    )

    resp = opened.post("/api/tests:delete", json={"test_ids": ["TC-002", "TC-001"]})

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TEST_IN_USE"
    assert resp.json()["error"]["next_action"]
    assert _ids(opened) == ["TC-001", "TC-002"], "하나가 막혔는데 다른 것이 지워졌다"


def test_a_midway_failure_rolls_everything_back(
    opened: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-432 · SC-624 — 「셋 중 둘만 지워진 채 오류」를 만들지 않는다.

    **이것이 가능한 이유는 삭제가 파괴가 아니라 이동이기 때문이다** (research R4).
    영구 삭제였다면 되돌릴 수 없어 부분 실패가 구조적으로 피할 수 없었다.
    """
    _write(opened, "TC-001", "하나")
    _write(opened, "TC-002", "둘")
    _write(opened, "TC-003", "셋")

    real = pathlib.Path.mkdir
    calls = {"n": 0}

    def fail_on_third(self: pathlib.Path, *a: object, **kw: object) -> None:
        if "trash" in str(self):
            calls["n"] += 1
            if calls["n"] == 3:
                msg = "디스크가 꽉 찼습니다"
                raise OSError(28, msg)
        real(self, *a, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(pathlib.Path, "mkdir", fail_on_third)

    resp = opened.post("/api/tests:delete", json={"test_ids": ["TC-001", "TC-002", "TC-003"]})

    monkeypatch.undo()
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "TEST_DELETE_FAILED"
    assert "원래 자리" in resp.json()["error"]["next_action"]
    assert _ids(opened) == ["TC-001", "TC-002", "TC-003"], "되돌아오지 않았다"
