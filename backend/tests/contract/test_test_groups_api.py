"""테스트 그룹 계약. 013 FR-438~FR-451 · contracts/api-contract.md §5.

**한 프로젝트 안에서 테스트를 묶을 방법이 없었다.** 목록이 한 덩어리라 「사용자관리」와
「데이터 관리」를 눈으로 갈라야 했고, 이름에 접두어를 손으로 붙이는 것 말고는 방법이 없었다.

그룹은 **테스트가 아니라 프로젝트 설정**이다 — `Project.groups` 에 살고, 테스트가 하나도
없어도 존재한다. 그래서 라우트도 `tests.py` 가 아니라 여기에 있다.
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
            id=test_id, name=name, authoring_mode="record", start_url=START_URL, steps=CLOSE_TAB
        )
    )


def _mk(client: TestClient, prefix: str, name: str) -> None:
    resp = client.post("/api/groups", json={"prefix": prefix, "name": name})
    assert resp.status_code == 201, resp.text


# ─── 만들기·조회 ────────────────────────────────────────────────────────────


def test_a_group_has_a_name_and_a_prefix(opened: TestClient) -> None:
    """FR-444d — **둘을 따로 받는다.** 한글 이름을 유지하면서 식별자는 짧게 둔다."""
    resp = opened.post("/api/groups", json={"prefix": "USER", "name": "사용자관리 테스트"})

    assert resp.status_code == 201, resp.text
    assert resp.json() == {"prefix": "USER", "name": "사용자관리 테스트", "count": 0}


def test_an_empty_group_still_shows_up(opened: TestClient) -> None:
    """**그룹을 고르는 자리에서는 비어 있는 그룹도 골라야 한다.**

    `GET /api/tests` 의 `groups` 와 개수 규칙이 다르다 — 그쪽은 목록을 어지럽히지 않으려고
    빈 그룹을 뺀다 (FR-450).
    """
    _mk(opened, "USER", "사용자관리 테스트")

    body = opened.get("/api/groups").json()

    assert body["groups"] == [{"prefix": "USER", "name": "사용자관리 테스트", "count": 0}]


def test_the_count_comes_from_the_identifier_prefix(opened: TestClient) -> None:
    """소속을 테스트에 저장하지 않는다 — 접두어가 곧 소속이다 (data-model §3)."""
    _mk(opened, "USER", "사용자관리 테스트")
    _write(opened, "USER-001", "로그인")
    _write(opened, "USER-002", "회원가입")
    _write(opened, "TC-003", "그룹 없는 것")

    body = opened.get("/api/groups").json()

    assert body["groups"][0]["count"] == 2


# ─── 거절 ──────────────────────────────────────────────────────────────────


def test_the_reserved_prefix_is_refused(opened: TestClient) -> None:
    """FR-445a — `TC` 를 쓰면 그룹에 넣은 적 없는 기존 테스트가 그 그룹에 나타난다."""
    resp = opened.post("/api/groups", json={"prefix": "TC", "name": "가로채기"})

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "GROUP_PREFIX_RESERVED"
    assert opened.get("/api/groups").json()["groups"] == []


@pytest.mark.parametrize("bad", ["user", "US ER", "../X", "ABCDEFGHI", "1AB", ""])
def test_malformed_prefixes_are_refused(opened: TestClient, bad: str) -> None:
    """FR-444e — 접두어가 파일 이름이 된다. **허용 목록이라** 경로 문자가 통과하지 못한다."""
    resp = opened.post("/api/groups", json={"prefix": bad, "name": "이름"})

    assert resp.status_code == 422, resp.text


def test_duplicate_prefix_or_name_is_refused(opened: TestClient) -> None:
    """FR-442 — 이름이 겹치면 어느 쪽에 넣었는지 알 수 없고, 접두어가 겹치면 식별자가
    어느 그룹인지 가리키지 못한다."""
    _mk(opened, "USER", "사용자관리 테스트")

    same_prefix = opened.post("/api/groups", json={"prefix": "USER", "name": "다른 이름"})
    same_name = opened.post("/api/groups", json={"prefix": "DATA", "name": "사용자관리 테스트"})

    assert same_prefix.status_code == 409
    assert same_prefix.json()["error"]["code"] == "GROUP_ALREADY_EXISTS"
    assert same_name.status_code == 409
    assert len(opened.get("/api/groups").json()["groups"]) == 1


# ─── 이름 변경 ──────────────────────────────────────────────────────────────


def test_renaming_a_group_keeps_the_prefix(opened: TestClient) -> None:
    """FR-449 — **접두어는 바꾸지 않는다.**

    접두어를 바꾸면 그 그룹의 테스트 식별자가 전부 바뀌고 파일과 산출물을 다 옮겨야 한다.
    그것은 「그룹 이동」이며 다른 라우트가 하는 일이다 — 이름을 고치는 조작에 자산 이동을
    숨기지 않는다.
    """
    _mk(opened, "USER", "옛 이름")
    _write(opened, "USER-001", "로그인")

    resp = opened.patch("/api/groups/USER", json={"name": "새 이름"})

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"prefix": "USER", "name": "새 이름", "count": 1}
    # 테스트는 그대로다 — 파일 이름도 식별자도 바뀌지 않았다.
    assert [t["id"] for t in opened.get("/api/tests").json()["tests"]] == ["USER-001"]


def test_renaming_to_an_existing_name_is_refused(opened: TestClient) -> None:
    _mk(opened, "USER", "사용자관리")
    _mk(opened, "DATA", "데이터 관리")

    resp = opened.patch("/api/groups/DATA", json={"name": "사용자관리"})

    assert resp.status_code == 409


def test_renaming_an_unknown_group_is_404(opened: TestClient) -> None:
    resp = opened.patch("/api/groups/NOPE", json={"name": "이름"})

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "GROUP_NOT_FOUND"


# ─── 목록 응답 (FR-440·FR-441·FR-450) ──────────────────────────────────────


def test_the_listing_carries_groups_with_counts(opened: TestClient) -> None:
    _mk(opened, "USER", "사용자관리 테스트")
    _mk(opened, "DATA", "데이터 관리 테스트")
    _write(opened, "USER-001", "로그인")
    _write(opened, "USER-002", "회원가입")
    _write(opened, "TC-003", "그룹 없는 것")

    body = opened.get("/api/tests").json()

    assert body["groups"] == [
        {"prefix": "TC", "name": None, "count": 1},
        {"prefix": "USER", "name": "사용자관리 테스트", "count": 2},
    ]
    # 테스트가 없는 DATA 는 목록을 어지럽히지 않는다 (FR-450).
    assert "DATA" not in [g["prefix"] for g in body["groups"]]


def test_group_and_search_apply_together(opened: TestClient) -> None:
    """FR-441 — 두 조건이 **함께** 걸린다."""
    _mk(opened, "USER", "사용자관리 테스트")
    _write(opened, "USER-001", "로그인")
    _write(opened, "USER-002", "회원가입")
    _write(opened, "TC-003", "로그인 기록")

    only_group = opened.get("/api/tests", params={"group": "USER"}).json()
    both = opened.get("/api/tests", params={"group": "USER", "q": "로그인"}).json()

    assert [t["id"] for t in only_group["tests"]] == ["USER-001", "USER-002"]
    assert [t["id"] for t in both["tests"]] == ["USER-001"]


def test_group_counts_are_computed_before_filtering(opened: TestClient) -> None:
    """걸러 본 상태에서도 **다른 그룹의 개수를 보고 그리로 갈 수 있어야 한다.**"""
    _mk(opened, "USER", "사용자관리 테스트")
    _write(opened, "USER-001", "로그인")
    _write(opened, "TC-002", "그룹 없는 것")

    body = opened.get("/api/tests", params={"group": "USER"}).json()

    assert [t["id"] for t in body["tests"]] == ["USER-001"]
    assert {g["prefix"]: g["count"] for g in body["groups"]} == {"TC": 1, "USER": 1}


def test_a_prefix_without_a_group_definition_does_not_break_the_listing(
    opened: TestClient,
) -> None:
    """사용자가 그룹을 지웠거나 파일을 손으로 옮긴 경우다 (data-model §3).

    **목록을 막지 않는다.** 접두어를 이름 삼아 보여주고 정의가 없다는 사실을 함께 싣는다 —
    「목록을 그리는 일이 파일 하나 때문에 통째로 실패하면 안 된다」는 기존 규칙과 같다.
    """
    _write(opened, "GHOST-001", "정의 없는 그룹의 테스트")

    body = opened.get("/api/tests").json()

    assert body["groups"] == [{"prefix": "GHOST", "name": None, "count": 1}]
    assert [t["id"] for t in body["tests"]] == ["GHOST-001"]


def test_rows_carry_the_group_prefix(opened: TestClient) -> None:
    """식별자에서 유도한다. 저장된 필드가 아니다 (data-model §3)."""
    _mk(opened, "USER", "사용자관리 테스트")
    _write(opened, "USER-001", "로그인")
    _write(opened, "TC-002", "그룹 없는 것")

    rows = {t["id"]: t["group_prefix"] for t in opened.get("/api/tests").json()["tests"]}

    assert rows == {"USER-001": "USER", "TC-002": "TC"}
