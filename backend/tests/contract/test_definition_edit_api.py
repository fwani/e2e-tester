"""006 T015~T023·T032b·T067·T068·T076~T078 — 정의 편집 계약.

`specs/006-edit-saved-test/contracts/rest-api.md` §1·§2.

**브라우저를 띄우지 않는다.** 그것이 이 기능의 주장이다 (FR-182·SC-302) — 저장된 테스트를
고치는 데 브라우저와 대상 앱이 필요하지 않아야 한다. 이 파일이 한 번도 Playwright 를
기동하지 않고 편집·저장 전체를 검증하는 것 자체가 그 주장의 증거다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.domain.test_case import Test
from itb.secrets.keys import KeyPaths
from itb.storage.repository import ProjectRepository
from tests.conftest import pin_playwright_browsers

START_URL = "http://127.0.0.1:4300/login.html"


def _steps() -> list[dict[str, object]]:
    """TC-PASS 계열 재료 (quickstart §0).

    `fill` 두 개 중 하나는 **민감 참조**다 — 없으면 FR-212·FR-213 을 걸 수 없다.
    """
    target = {"tag": "input", "css": {"value": "#u", "status": "verified"}}
    button = {"tag": "button", "css": {"value": "#go", "status": "verified"}}
    return [
        {"type": "navigate", "id": "step-01", "label": "로그인 화면", "url": START_URL},
        {
            "type": "fill",
            "id": "step-02",
            "label": "아이디",
            "target": target,
            "value": "admin",
        },
        {
            "type": "fill",
            "id": "step-03",
            "label": "비밀번호",
            "target": target,
            "value": "{{SECRET_PASSWORD}}",
        },
        {"type": "click", "id": "step-04", "label": "로그인", "target": button},
        {
            "type": "assertion",
            "id": "step-05",
            "label": "환영 문구",
            "assertion": {"kind": "text", "value": "환영합니다"},
        },
    ]


@pytest.fixture
def client(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    pin_playwright_browsers(monkeypatch)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        yield c


@pytest.fixture
def opened(client: TestClient) -> TestClient:
    resp = client.post(
        "/api/project/create",
        json={"name": "편집 계약", "default_start_url": START_URL},
    )
    assert resp.status_code == 201, resp.text
    return client


def _repo(client: TestClient) -> ProjectRepository:
    return ProjectRepository.open(pathlib.Path(client.get("/api/project").json()["root"]))


@pytest.fixture
def saved(opened: TestClient) -> TestClient:
    """정의 파일을 직접 써서 재료를 만든다. 브라우저를 쓰지 않는다."""
    _repo(opened).write_test(
        Test(
            id="TC-001",
            name="로그인",
            authoring_mode="record",
            start_url=START_URL,
            variables=[{"name": "SECRET_PASSWORD", "sensitive": True}],
            steps=_steps(),
        )
    )
    return opened


def _view(client: TestClient, test_id: str = "TC-001") -> dict:
    resp = client.get(f"/api/tests/{test_id}/definition")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _save(client: TestClient, edits: list[dict], *, revision: str | None = None):
    rev = revision if revision is not None else _view(client)["revision"]
    return client.put(
        "/api/tests/TC-001/definition", json={"revision": rev, "edits": edits}
    )


# ─── T015 · GET /definition ─────────────────────────────────────────────────


def test_get_definition_returns_view_without_browser(saved: TestClient) -> None:
    """FR-182 · SC-302 — 브라우저 없이 200 이고 편집에 필요한 것을 모두 준다."""
    body = _view(saved)
    assert set(body) == {
        "test",
        "revision",
        "editable",
        "blocked_by",
        "blocking_session_id",
        "locked_fields",
        "warnings",
    }
    assert body["test"]["id"] == "TC-001"
    assert len(body["test"]["steps"]) == 5
    assert body["revision"]
    assert body["editable"] is True
    assert body["blocked_by"] is None
    # 살아 있는 세션이 하나도 만들어지지 않았다 — 이 기능의 주장이다.
    assert saved.get("/api/sessions").json()["sessions"] == []


def test_locked_fields_name_what_cannot_be_edited(saved: TestClient) -> None:
    """FR-191 — 편집 불가 항목의 근거를 서버가 준다. 화면이 표를 따로 갖지 않는다."""
    locked = {f["field"]: f["reason"] for f in _view(saved)["locked_fields"]}
    assert locked["steps[].target"] == "live_browser_required"
    assert locked["steps[].type"] == "delete_and_insert_instead"
    assert locked["ai_instruction"] == "record_only"


def test_get_definition_unknown_test_is_404(opened: TestClient) -> None:
    resp = opened.get("/api/tests/TC-404/definition")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


# ─── T016 · 여섯 연산이 정의에 반영된다 ────────────────────────────────────


def test_update_value_is_persisted(saved: TestClient) -> None:
    """FR-183 · FR-193 — 값이 바뀌고 같은 테스트를 덮어쓴다."""
    resp = _save(saved, [{"op": "update", "step_id": "step-02", "value": "operator"}])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["test"]["steps"][1]["value"] == "operator"
    # 파일에도 반영됐다 — 응답만 바뀐 것이 아니다.
    assert _repo(saved).read_test("TC-001").steps[1].value == "operator"
    # 새 테스트가 만들어지지 않았다.
    assert [t["id"] for t in saved.get("/api/tests").json()["tests"]] == ["TC-001"]


def test_update_label_timeout_tab_are_persisted(saved: TestClient) -> None:
    """FR-183 — 라벨·대기시간·탭."""
    resp = _save(
        saved,
        [
            {
                "op": "update",
                "step_id": "step-04",
                "label": "로그인 누르기",
                "timeout_ms": 30000,
                "tab": 1,
            }
        ],
    )
    assert resp.status_code == 200, resp.text
    step = resp.json()["test"]["steps"][3]
    assert step["label"] == "로그인 누르기"
    assert step["timeout_ms"] == 30000
    assert step["tab"] == 1


def test_update_navigate_url_and_assertion_value(saved: TestClient) -> None:
    """FR-183 — `navigate` 주소와 검증 기대값."""
    resp = _save(
        saved,
        [
            {
                "op": "update",
                "step_id": "step-01",
                "url": "http://127.0.0.1:4300/other.html",
            },
            {"op": "update", "step_id": "step-05", "assertion_value": "반갑습니다"},
        ],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["test"]
    assert body["steps"][0]["url"] == "http://127.0.0.1:4300/other.html"
    assert body["steps"][4]["assertion"]["value"] == "반갑습니다"


def test_delete_and_reorder_are_persisted(saved: TestClient) -> None:
    """FR-184 · FR-185."""
    resp = _save(saved, [{"op": "delete", "step_id": "step-05"}])
    assert resp.status_code == 200, resp.text
    assert [s["id"] for s in resp.json()["test"]["steps"]] == [
        "step-01",
        "step-02",
        "step-03",
        "step-04",
    ]

    resp = _save(
        saved,
        [{"op": "reorder", "order": ["step-01", "step-03", "step-02", "step-04"]}],
    )
    assert resp.status_code == 200, resp.text
    assert [s["id"] for s in resp.json()["test"]["steps"]] == [
        "step-01",
        "step-03",
        "step-02",
        "step-04",
    ]


def test_set_name_and_start_url_are_persisted(saved: TestClient) -> None:
    """FR-186."""
    resp = _save(
        saved,
        [
            {"op": "set_name", "name": "로그인 후 대시보드"},
            {"op": "set_start_url", "url": "http://127.0.0.1:4300/start.html"},
        ],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["test"]["name"] == "로그인 후 대시보드"
    assert resp.json()["test"]["start_url"] == "http://127.0.0.1:4300/start.html"
    assert _repo(saved).read_test("TC-001").name == "로그인 후 대시보드"


def test_save_returns_new_revision(saved: TestClient) -> None:
    """계약 §2 — 저장 응답이 새 `revision` 을 준다. 화면이 다시 조회하지 않는다."""
    before = _view(saved)["revision"]
    body = _save(saved, [{"op": "update", "step_id": "step-02", "value": "x"}]).json()
    assert body["revision"] != before
    # 그 값으로 곧바로 다음 저장이 된다.
    assert (
        _save(
            saved,
            [{"op": "update", "step_id": "step-02", "value": "y"}],
            revision=body["revision"],
        ).status_code
        == 200
    )


# ─── T017 · 거절 계약 ───────────────────────────────────────────────────────


def test_unknown_step_id_is_rejected(saved: TestClient) -> None:
    resp = _save(saved, [{"op": "update", "step_id": "step-99", "value": "x"}])
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_value_on_step_type_without_value_is_rejected(saved: TestClient) -> None:
    """`click` 은 입력값을 갖지 않는다 — `step_edits` 의 문장을 그대로 옮긴다."""
    resp = _save(saved, [{"op": "update", "step_id": "step-04", "value": "x"}])
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    assert "입력값" in resp.json()["error"]["message"]


def test_url_on_non_navigate_step_is_rejected(saved: TestClient) -> None:
    resp = _save(saved, [{"op": "update", "step_id": "step-04", "url": "http://x/"}])
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_reorder_mismatch_is_rejected_without_partial_apply(saved: TestClient) -> None:
    """절반만 옮긴 목록은 사용자가 의도한 어떤 상태도 아니다."""
    resp = _save(saved, [{"op": "reorder", "order": ["step-01", "step-02"]}])
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    # 파일은 그대로다.
    assert [s.id for s in _repo(saved).read_test("TC-001").steps] == [
        "step-01",
        "step-02",
        "step-03",
        "step-04",
        "step-05",
    ]


def test_deleting_every_step_is_rejected(saved: TestClient) -> None:
    """FR-197 — Step 0개는 저장할 수 없다."""
    resp = _save(
        saved, [{"op": "delete", "step_id": f"step-0{i}"} for i in range(1, 6)]
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "STEP_LIST_EMPTY"
    assert resp.json()["error"]["next_action"]
    assert len(_repo(saved).read_test("TC-001").steps) == 5


def test_empty_edits_is_rejected(saved: TestClient) -> None:
    """저장할 것이 없는 저장은 없다 (FR-195 의 서버 쪽 짝)."""
    resp = _save(saved, [])
    assert resp.status_code == 422


def test_update_without_any_field_is_rejected(saved: TestClient) -> None:
    resp = _save(saved, [{"op": "update", "step_id": "step-02"}])
    assert resp.status_code == 422


def test_all_or_nothing_when_a_later_op_fails(saved: TestClient) -> None:
    """V4 — 하나라도 실패하면 파일을 쓰지 않는다."""
    resp = _save(
        saved,
        [
            {"op": "update", "step_id": "step-02", "value": "changed"},
            {"op": "update", "step_id": "step-99", "value": "boom"},
        ],
    )
    assert resp.status_code == 400
    assert _repo(saved).read_test("TC-001").steps[1].value == "admin"


# ─── T012 · T013 · 요청 모델이 구조적으로 막는 것 ──────────────────────────


@pytest.mark.parametrize(
    "extra",
    [
        {"target": {"css": {"value": "#x", "status": "verified"}}},
        {"css": "#x"},
        {"test_id": "dashboard-open"},
        {"role": "button"},
        {"drop_target": {"css": {"value": "#y", "status": "verified"}}},
    ],
)
def test_locator_fields_are_not_accepted(saved: TestClient, extra: dict) -> None:
    """FR-187 제외 결정 · 원칙 IV — 편집 요청으로 후보를 손댈 수 없다.

    후보는 살아 있는 페이지에서만 수집·검증된다. 손으로 넣은 값은 `verified` 를 얻을 수
    없으므로, 받아 주면 거짓말이거나 조용한 무효 편집이 된다 (research R6).
    """
    resp = _save(saved, [{"op": "update", "step_id": "step-02", **extra}])
    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize("extra", [{"secret": "hunter2"}, {"plaintext": "hunter2"}])
def test_no_field_accepts_plaintext_secrets(saved: TestClient, extra: dict) -> None:
    """FR-215 — 평문 민감 값을 받는 필드가 존재하지 않는다."""
    resp = _save(saved, [{"op": "update", "step_id": "step-03", **extra}])
    assert resp.status_code == 422, resp.text


def test_unknown_op_is_rejected(saved: TestClient) -> None:
    resp = _save(saved, [{"op": "set_target", "step_id": "step-02"}])
    assert resp.status_code == 422


# ─── T018 · T019 · 민감 값 ──────────────────────────────────────────────────


def test_replacing_secret_reference_with_plaintext_is_rejected(
    saved: TestClient,
) -> None:
    """FR-213 — 값 자체는 비밀 값 화면에서 다룬다."""
    resp = _save(saved, [{"op": "update", "step_id": "step-03", "value": "hunter2"}])
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "DEFINITION_INVALID"
    assert "비밀 값" in err["next_action"]
    # 평문이 파일에 닿지 않았다.
    assert _repo(saved).read_test("TC-001").steps[2].value == "{{SECRET_PASSWORD}}"


def test_replacing_plain_reference_with_literal_is_allowed(saved: TestClient) -> None:
    """비민감 참조를 평문으로 바꾸는 것은 정상 편집이다 — 과하게 막지 않는다."""
    resp = _save(saved, [{"op": "update", "step_id": "step-02", "value": "{{USER}}"}])
    assert resp.status_code == 200, resp.text
    resp = _save(saved, [{"op": "update", "step_id": "step-02", "value": "admin"}])
    assert resp.status_code == 200, resp.text


def test_sensitive_flag_survives_editing(saved: TestClient) -> None:
    """FR-214 — 편집·저장이 민감 표시를 강등하지 않는다.

    강등되면 재실행이 빈 값을 채운다 — FR-082 위반이자 조용한 실패다.
    """
    body = _save(saved, [{"op": "update", "step_id": "step-02", "value": "x"}]).json()
    by_name = {v["name"]: v for v in body["test"]["variables"]}
    assert by_name["SECRET_PASSWORD"]["sensitive"] is True
    assert by_name["SECRET_PASSWORD"]["value"] is None


def test_response_never_carries_plaintext_secret(saved: TestClient) -> None:
    """FR-215 — 참조만 오간다. 응답 어디에도 평문이 없다."""
    body = _save(saved, [{"op": "update", "step_id": "step-04", "tab": 0}]).text
    assert "{{SECRET_PASSWORD}}" in body
    assert "hunter2" not in body


# ─── T020 · 경고 ────────────────────────────────────────────────────────────


def test_undefined_reference_warns_without_blocking(saved: TestClient) -> None:
    """FR-216 — 막지 않고 알린다. 실행 시 빈 값으로 조용히 실패하는 것을 막는다."""
    resp = _save(saved, [{"op": "update", "step_id": "step-02", "value": "{{TOKEN}}"}])
    assert resp.status_code == 200, resp.text
    assert any("{{TOKEN}}" in w for w in resp.json()["warnings"])


def test_reorder_warning_when_navigate_moves_back(saved: TestClient) -> None:
    """T032b — 주소 이동 Step 이 뒤로 밀리면 경고한다. 저장은 성공한다."""
    resp = _save(
        saved,
        [
            {
                "op": "reorder",
                "order": ["step-02", "step-01", "step-03", "step-04", "step-05"],
            }
        ],
    )
    assert resp.status_code == 200, resp.text
    assert any("주소 이동" in w for w in resp.json()["warnings"])


def test_no_reorder_warning_when_order_is_unchanged(saved: TestClient) -> None:
    resp = _save(
        saved,
        [
            {
                "op": "reorder",
                "order": ["step-01", "step-02", "step-03", "step-04", "step-05"],
            }
        ],
    )
    assert resp.status_code == 200, resp.text
    assert not [w for w in resp.json()["warnings"] if "주소 이동" in w]


# ─── T067 · T068 · 외부 변경 충돌 ──────────────────────────────────────────


def test_stale_revision_is_rejected_with_current_definition(saved: TestClient) -> None:
    """FR-209 — 조용히 덮어쓰지 않고, 화면이 두 선택을 줄 수 있게 현재 내용을 준다."""
    stale = _view(saved)["revision"]
    # 파일이 밖에서 바뀌었다 (사용자가 편집기로 고친 상황).
    repo = _repo(saved)
    repo.write_test(repo.read_test("TC-001").model_copy(update={"name": "밖에서 바꿈"}))

    resp = _save(
        saved,
        [{"op": "update", "step_id": "step-02", "value": "x"}],
        revision=stale,
    )
    assert resp.status_code == 409
    err = resp.json()["error"]
    assert err["code"] == "DEFINITION_STALE"
    assert err["next_action"]
    assert err["detail"]["revision"] != stale
    assert err["detail"]["test"]["name"] == "밖에서 바꿈"


def test_retrying_with_current_revision_overwrites(saved: TestClient) -> None:
    """계약 §2 — 덮어쓰기는 현재 `revision` 을 실어 다시 보내는 것이다.

    "강제" 플래그를 두지 않는다. 플래그는 습관이 되고, 습관이 되면 감지가 무의미해진다.
    """
    stale = _view(saved)["revision"]
    repo = _repo(saved)
    repo.write_test(repo.read_test("TC-001").model_copy(update={"name": "밖에서"}))

    rejected = _save(
        saved, [{"op": "update", "step_id": "step-02", "value": "x"}], revision=stale
    )
    fresh = rejected.json()["error"]["detail"]["revision"]
    resp = _save(
        saved, [{"op": "update", "step_id": "step-02", "value": "x"}], revision=fresh
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["test"]["steps"][1]["value"] == "x"


# ─── T021 · 깨진 정의 파일 ──────────────────────────────────────────────────


def test_invalid_definition_file_is_diagnosable(saved: TestClient) -> None:
    """FR-196 — 어디가 왜 잘못됐는지 말한다. 반쯤 읽어 저장하지 않는다."""
    path = _repo(saved).find_test_path("TC-001")
    assert path is not None
    path.write_text("id: TC-001\nname: 깨짐\nsteps: []\n", encoding="utf-8")

    resp = saved.get("/api/tests/TC-001/definition")
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "DEFINITION_INVALID"
    assert err["message"]

    resp = saved.put(
        "/api/tests/TC-001/definition",
        json={"revision": "whatever", "edits": [{"op": "set_name", "name": "x"}]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


# ─── T032 · 저장 형식 불변 (원칙 V) ────────────────────────────────────────


def test_saving_keeps_the_plain_text_definition_shape(saved: TestClient) -> None:
    """FR-199 · 원칙 V — 편집이 저장 형식을 바꾸지 않는다.

    저장이 파일을 재배치하면 사용자의 버전 관리가 쓸모 없어진다.
    """
    path = _repo(saved).find_test_path("TC-001")
    assert path is not None
    before = path.read_text(encoding="utf-8").splitlines()

    _save(saved, [{"op": "update", "step_id": "step-02", "value": "operator"}])

    after = path.read_text(encoding="utf-8").splitlines()
    changed = [
        line for line in after if line not in before and "updated_at" not in line
    ]
    assert changed == ["  value: operator"], changed


# ─── 009 T020 · insert 연산 (FR-285~FR-289·FR-312 · 계약 §4-1) ──────────────
#
# **브라우저를 띄우지 않는다.** 위 파일 전체가 그 주장의 증거이고, 삽입도 같다 — 요소를
# 지목하지 않는 Step 종류는 정의만으로 만들어진다 (009 FR-285).


def _insert(at: int, spec: dict[str, object]) -> dict[str, object]:
    return {"op": "insert", "at": at, "spec": spec}


@pytest.mark.parametrize(
    ("spec", "expect_type"),
    [
        ({"kind": "navigate", "url": "/orders"}, "navigate"),
        ({"kind": "close_tab", "tab": 0}, "close_tab"),
        ({"kind": "assert_url", "url": "/done", "match": "contains"}, "assertion"),
        ({"kind": "assert_text", "value": "주문 완료"}, "assertion"),
    ],
)
def test_insert_네_종류가_지정_위치에_들어간다(
    saved: TestClient, spec: dict[str, object], expect_type: str
) -> None:
    """FR-285·FR-286 — 요소 지목이 필요 없는 넷은 브라우저 없이 들어간다."""
    resp = _save(saved, [_insert(3, spec)])
    assert resp.status_code == 200, resp.text

    steps = resp.json()["test"]["steps"]
    assert len(steps) == 6
    assert steps[3]["type"] == expect_type
    # 손으로 넣은 것은 사람이 만든 것이다 (원칙 I · FR-014).
    assert steps[3]["author"] == "human"
    # 이후 번호가 하나씩 밀린다 — id 는 자리가 아니라 정체성이므로 그대로다.
    assert [s["id"] for s in steps[4:]] == ["step-04", "step-05"]


def test_insert_는_라벨을_서버가_만든다(saved: TestClient) -> None:
    """research R6 — 화면이 만들면 만든 경로에 따라 이름이 갈린다."""
    resp = _save(saved, [_insert(0, {"kind": "navigate", "url": "/orders"})])
    assert resp.status_code == 200, resp.text
    assert resp.json()["test"]["steps"][0]["label"] == "주소로 이동 — /orders"


def test_insert_id_는_쓰인_번호를_피한다(saved: TestClient) -> None:
    """`allocate_step_id` 의 규칙이 여기에도 적용된다 (research R6)."""
    resp = _save(saved, [_insert(5, {"kind": "navigate", "url": "/a"})])
    assert resp.status_code == 200, resp.text

    ids = [s["id"] for s in resp.json()["test"]["steps"]]
    assert len(set(ids)) == len(ids)
    assert "step-06" in ids


def test_insert_맨_앞과_맨_뒤에_넣을_수_있다(saved: TestClient) -> None:
    """명세 Edge Case — 한쪽 끝에 도달할 수 없는 결함을 만들지 않는다."""
    resp = _save(
        saved,
        [
            _insert(0, {"kind": "navigate", "url": "/first"}),
            _insert(6, {"kind": "close_tab", "tab": 0}),
        ],
    )
    assert resp.status_code == 200, resp.text

    steps = resp.json()["test"]["steps"]
    assert steps[0]["type"] == "navigate"
    assert steps[0]["url"] == "/first"
    assert steps[-1]["type"] == "close_tab"


def test_insert_at_이_범위를_벗어나면_거절한다(saved: TestClient) -> None:
    """조용히 다른 자리에 넣지 않는다 — 사용자가 의도한 어떤 상태도 아니다."""
    resp = _save(saved, [_insert(99, {"kind": "navigate", "url": "/a"})])

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    # 저장되지 않았다.
    assert len(_view(saved)["test"]["steps"]) == 5


@pytest.mark.parametrize("kind", ["click", "fill", "select", "hover", "drag"])
def test_insert_요소를_요구하는_종류는_거절한다(saved: TestClient, kind: str) -> None:
    """FR-287 · 원칙 IV — 판별 유니온에 그 종류가 없다. 런타임 검사가 아니다.

    **422 이고 400 이 아니다.** 요청의 *모양*이 계약에 맞지 않는 것이므로 전역
    `RequestValidationError` 핸들러가 받는다 — 라우트 안에서 거절하는 것(`at` 범위 초과
    등)은 400 이다. 오류 코드는 둘 다 `DEFINITION_INVALID` 로 같다 (003 EC-006).
    """
    resp = _save(saved, [_insert(0, {"kind": kind, "url": "/x"})])

    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_insert_거절_응답에_넘어온_값이_실리지_않는다(saved: TestClient) -> None:
    """003 EC-005 — pydantic 원문에는 입력이 통째로 들어 있다.

    이 라우트의 판별 유니온 거절은 **전역 `RequestValidationError` 핸들러**를 타고,
    `itb/api/errors.py` 의 `_reason` 이 닫힌 문구 집합만 쓰므로 값이 실리지 않는다.
    **규칙이 있다는 것과 그 경로를 탄다는 것은 다른 사실이므로** 실제로 확인한다.
    """
    secret = "비밀번호1234"
    resp = _save(saved, [_insert(0, {"kind": "click", "value": secret})])

    assert resp.status_code in (400, 422)
    assert secret not in resp.text


def test_insert_target_을_실어_보낼_수_없다(saved: TestClient) -> None:
    """손으로 넣은 후보는 검증 상태를 얻을 수 없다 (원칙 IV · 006 FR-187)."""
    resp = _save(
        saved,
        [
            _insert(
                0,
                {
                    "kind": "assert_url",
                    "url": "/done",
                    "target": {"css": {"value": "a", "status": "verified"}},
                },
            )
        ],
    )

    assert resp.status_code in (400, 422)


def test_insert_는_다른_연산과_한_묶음에서_순서대로_적용된다(saved: TestClient) -> None:
    """FR-288 — 같은 저장에 섞이고, 앞선 연산의 결과 위에서 다음 연산이 돈다."""
    resp = _save(
        saved,
        [
            _insert(0, {"kind": "navigate", "url": "/first"}),
            {"op": "delete", "step_id": "step-05"},
            {"op": "set_name", "name": "고친 로그인"},
        ],
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()["test"]
    assert body["name"] == "고친 로그인"
    assert body["steps"][0]["url"] == "/first"
    assert "step-05" not in [s["id"] for s in body["steps"]]


def test_insert_묶음_하나가_실패하면_파일이_쓰이지_않는다(saved: TestClient) -> None:
    """전부 또는 전무 — 절반 적용된 정의는 사용자가 의도한 어떤 상태도 아니다."""
    before = _view(saved)
    resp = _save(
        saved,
        [
            _insert(0, {"kind": "navigate", "url": "/first"}),
            {"op": "delete", "step_id": "step-99"},
        ],
    )

    assert resp.status_code == 400
    after = _view(saved)
    assert after["revision"] == before["revision"]
    assert len(after["test"]["steps"]) == 5


def test_insert_는_revision_없이_저장되지_않는다(saved: TestClient) -> None:
    """006 FR-209 — 바탕이 바뀐 것을 모르고 덮어쓰는 경로를 만들지 않는다."""
    resp = saved.put(
        "/api/tests/TC-001/definition",
        json={"edits": [_insert(0, {"kind": "navigate", "url": "/a"})]},
    )

    assert resp.status_code == 422


def test_insert_바탕이_바뀌면_충돌_흐름을_탄다(saved: TestClient) -> None:
    """삽입도 다른 연산과 같은 충돌 흐름이다 (006 FR-209)."""
    stale = _view(saved)["revision"]
    assert _save(saved, [{"op": "set_name", "name": "먼저 바꾼다"}]).status_code == 200

    resp = _save(saved, [_insert(0, {"kind": "navigate", "url": "/a"})], revision=stale)

    assert resp.status_code == 409


def test_insert_중간의_주소_이동은_경고를_남기고_저장은_된다(saved: TestClient) -> None:
    """FR-312 — 막지 않는다. 무엇이 선행 상태인지는 대상 앱마다 다르다."""
    resp = _save(saved, [_insert(3, {"kind": "navigate", "url": "/orders"})])

    assert resp.status_code == 200, resp.text
    assert any("주소 이동" in w for w in resp.json()["warnings"])


def test_insert_열리지_않은_탭을_닫으면_경고를_남긴다(saved: TestClient) -> None:
    """FR-312 — 번호의 유효성은 실행 흐름에 달려 있으므로 저장 시점에 막지 않는다."""
    resp = _save(saved, [_insert(2, {"kind": "close_tab", "tab": 3})])

    assert resp.status_code == 200, resp.text
    assert any("탭 3" in w for w in resp.json()["warnings"])


def test_insert_맨_앞의_주소_이동은_경고하지_않는다(saved: TestClient) -> None:
    """앞으로 밀려난 Step 이 없으면 경고할 것이 없다 — 없는 위험을 말하지 않는다."""
    resp = _save(saved, [_insert(0, {"kind": "navigate", "url": "/orders"})])

    assert resp.status_code == 200, resp.text
    assert not any("주소 이동" in w for w in resp.json()["warnings"])


def test_insert_뒤_다시_읽어도_그_자리에_있다(saved: TestClient) -> None:
    """SC-510 의 앞 절반. 실행까지 보는 것은 통합 검사가 한다 (T023)."""
    assert _save(saved, [_insert(2, {"kind": "assert_url", "url": "/x"})]).status_code == 200

    steps = _view(saved)["test"]["steps"]
    assert steps[2]["type"] == "assertion"
    assert steps[2]["assertion"]["kind"] == "url"
    assert steps[2]["assertion"]["value"] == "/x"


# ─── 009 T054·T055 · 세 입구의 잠금과 결과 일치 ─────────────────────────────


def test_실행_중에는_삽입도_거절된다(saved: TestClient) -> None:
    """009 FR-306 — 세 입구 **전부**가 잠긴다.

    세션 두 입구는 `require_paused` 가 막고(`test_step_edit_api.py`), 이 입구는 실행
    예약이 막는다 (FR-207). 근거가 다르지만 사용자에게는 같은 사실이어야 한다 — 러너가
    전진하는 동안 목록을 고치면 같은 Step 이 두 번 돈다.
    """
    saved.app.state.itb.sessions.reserve_for_test("TC-001", "sess-running")
    try:
        resp = _save(saved, [_insert(0, {"kind": "navigate", "url": "/a"})])

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SESSION_ALREADY_ACTIVE"
        # 저장되지 않았다.
        assert len(_view(saved)["test"]["steps"]) == 5
    finally:
        saved.app.state.itb.sessions.release_reservation("TC-001", "sess-running")


def test_정의_편집_입구도_같은_step_을_만든다(saved: TestClient) -> None:
    """009 research R2 의 전제 — 세 입구가 같은 목록을 만든다.

    세션 두 입구의 대조는 `test_step_edit_api.py::test_세_입구가_같은_목록을_만든다` 가
    한다. 여기서는 **정의 편집 입구**가 같은 서술로 같은 Step 을 만드는지 본다 — 삽입
    규칙이 갈리면 「어디서 넣었는지」에 따라 정의가 달라진다.
    """
    spec = {"kind": "assert_url", "url": "/done", "match": "contains"}
    resp = _save(saved, [_insert(2, spec)])
    assert resp.status_code == 200, resp.text

    made = resp.json()["test"]["steps"][2]
    # 서버가 조립한 결과 — 라벨·작성자·검증 모양이 `manual_step.build_step` 과 같다.
    assert made["type"] == "assertion"
    assert made["author"] == "human"
    assert made["label"] == "주소 검증 — /done"
    assert made["assertion"] == {
        "kind": "url",
        "target": None,
        "match": "contains",
        "value": "/done",
    }
