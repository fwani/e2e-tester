"""T014 — 등록된 **모든** 요청 경로가 오류 규약을 지키는지 훑는다 (RG-104-2).

경로마다 검증을 손으로 쓰지 않는다. 앱에서 경로 목록을 읽어 각각에 거부를 유발하고, 나온
응답이 계약을 만족하는지 본다. **새 경로를 추가하면 이 검증이 자동으로 그것을 포함한다.**

거부를 유발하는 방법은 두 층이다.

1. **일반 방법** — 존재하지 않는 식별자를 경로에 넣고, 본문이 필요한 요청에는 빈 본문을 보낸다.
   프로젝트가 열리지 않은 상태이므로 대부분 여기서 거부된다
2. **개별 방법** — 일반 방법으로 거부되지 않는 경로만 `REJECTION_RECIPES` 에 등록한다

**둘 다 없이 통과하는 경로는 실패다.** 거부를 못 만들면 그 경로의 규약 준수는 확인되지 않은
것이고, 확인되지 않은 것을 통과로 세면 이 훑기가 무의미해진다.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from tests.abnormal.catalogue import _LEAK, REQUIRED_ERROR_FIELDS

# 훑기에서 뺀다 — 오류를 낼 일이 없는 관찰용 경로다.
EXEMPT = {("GET", "/api/health")}

# 존재할 리 없는 값. 경로 변수를 이것으로 채운다.
NOWHERE = "__없는-것__"

# 일반 방법으로 거부되지 않는 경로만 여기 등록한다.
# 값은 `(method, path)` → 요청을 만드는 함수다.
RejectionRecipe = Callable[[TestClient, str], Any]
REJECTION_RECIPES: dict[tuple[str, str], RejectionRecipe] = {
    # 홈 밖 경로는 거부된다 (INVALID_PATH).
    ("GET", "/api/fs/browse"): lambda c, url: c.get(url, params={"path": "/etc"}),
    # 첫 번째는 성공한다. 두 번째가 거부된다 (KEY_ALREADY_EXISTS).
    ("POST", "/api/keys/generate"): lambda c, url: (
        c.post(url, json={}),
        c.post(url, json={}),
    )[1],
}

# 거부가 **존재하지 않는** 경로. 상태를 묻기만 하므로 거절할 대상이 없다.
#
# 건너뛰기가 아니다 — 이유를 적어 선언하고, 아래에서 다른 방식으로 검사한다(성공 응답이
# 나오고 내부 정보가 새지 않는지). 새로 추가된 경로는 여기에도 위에도 없으므로 **실패**한다.
NO_REJECTION: dict[tuple[str, str], str] = {
    ("GET", "/api/project/list"): "프로젝트가 없으면 빈 목록이다. 거절할 대상이 없다",
    ("GET", "/api/keys/status"): "키가 없다는 것도 상태다. 없는 것이 오류가 아니다",
    ("GET", "/api/keys/permission-check"): "권한 여부를 알려주는 것이 이 경로의 결과다",
    ("GET", "/api/ai/availability"): "AI 를 쓸 수 없다는 것도 가용성 답변이다",
}


def _routes() -> list[tuple[str, str]]:
    """앱이 스스로 밝히는 경로 목록을 읽는다.

    앱 객체의 내부 구조를 뒤지지 않는다 — 이 FastAPI 판은 포함된 라우터를 펼치지 않고
    감싼 채 두어(`_IncludedRouter`) 최상위만 훑으면 경로를 하나도 못 읽는다. 공개된
    OpenAPI 목록은 판이 바뀌어도 같은 것을 알려준다.
    """
    paths = create_app().openapi().get("paths", {})
    out: list[tuple[str, str]] = []
    for path, operations in paths.items():
        for method in sorted(operations):
            m = method.upper()
            if m in ("HEAD", "OPTIONS", "PARAMETERS"):
                continue
            if (m, path) in EXEMPT:
                continue
            out.append((m, path))
    return sorted(out)


ROUTES = _routes()


def _concrete(path: str) -> str:
    """경로 변수를 존재하지 않는 값으로 채운다."""
    return re.sub(r"\{[^}]+\}", NOWHERE, path)


def _send(client: TestClient, method: str, path: str) -> Any:
    url = _concrete(path)
    recipe = REJECTION_RECIPES.get((method, path))
    if recipe is not None:
        return recipe(client, url)
    if method in ("POST", "PUT", "PATCH"):
        # 빈 본문 — 필수 항목이 있으면 422, 없으면 대상이 없어 404 로 거부된다
        return client.request(method, url, json={})
    return client.request(method, url)


@pytest.mark.parametrize(
    ("method", "path"), ROUTES, ids=[f"{m} {p}" for m, p in ROUTES]
)
def test_every_route_rejects_within_the_contract(
    client: TestClient, method: str, path: str
) -> None:
    resp = _send(client, method, path)

    if (method, path) in NO_REJECTION:
        # 거부가 없다고 선언된 경로. 성공 응답이 나오고 내부 정보가 새지 않는지만 본다.
        assert resp.status_code < 400, (
            f"{method} {path} 는 거부가 없다고 선언됐는데 {resp.status_code} 로 거부됐다. "
            f"선언이 틀렸다면 NO_REJECTION 에서 빼고 REJECTION_RECIPES 로 옮기세요."
        )
        leak = _LEAK.search(resp.text)
        assert leak is None, f"{method} {path}: 성공 응답에 내부 경로가 노출됐다 — {leak.group(0)}"
        return

    if resp.status_code < 400:
        pytest.fail(
            f"{method} {path} 에 거부를 유발하지 못했다 (상태 {resp.status_code}).\n"
            "거부시킬 수 있으면 REJECTION_RECIPES 에, 거부가 존재하지 않으면 이유와 함께 "
            "NO_REJECTION 에 등록하세요. 둘 다 없이 통과시키면 이 경로의 규약 준수는 "
            "확인되지 않은 것이다 (RG-104-2)."
        )

    body = resp.json()
    assert set(body) == {"error"}, f"{method} {path}: 오류 봉투가 계약과 다르다 — {sorted(body)}"

    err = body["error"]
    missing = REQUIRED_ERROR_FIELDS - set(err)
    assert not missing, f"{method} {path}: 오류 본문에 필드가 없다 {sorted(missing)}"

    assert err["category"] in ("blocked", "broken"), f"{method} {path}: 분류가 이상하다"
    assert str(err["message"]).strip(), f"{method} {path}: message 가 비었다"
    assert str(err["next_action"]).strip(), f"{method} {path}: next_action 이 비었다 (EC-004)"

    leak = _LEAK.search(resp.text)
    assert leak is None, (
        f"{method} {path}: 내부 경로·스택이 노출됐다 — {leak.group(0) if leak else ''}"
    )


def test_the_sweep_actually_covers_something() -> None:
    """경로를 하나도 못 읽은 채 통과하는 상태를 막는다."""
    assert len(ROUTES) >= 20, f"경로를 {len(ROUTES)}개밖에 읽지 못했다 — 훑기가 망가졌다"


def test_no_stale_recipes() -> None:
    """사라진 경로의 등록이 남아 있으면 경로 삭제가 조용히 지나간 것이다."""
    known = set(ROUTES)
    stale = sorted(
        f"{m} {p}" for m, p in (*REJECTION_RECIPES, *NO_REJECTION) if (m, p) not in known
    )
    assert not stale, f"존재하지 않는 경로의 등록이 남아 있다: {stale}"


def test_no_rejection_declarations_carry_a_reason() -> None:
    """이유 없는 선언은 건너뛰기와 같다. 이유를 적게 강제한다."""
    empty = sorted(f"{m} {p}" for (m, p), why in NO_REJECTION.items() if not why.strip())
    assert not empty, f"거부 없음 선언에 이유가 없다: {empty}"


def test_most_routes_can_actually_be_rejected() -> None:
    """거부 없음 선언이 늘어나면 이 훑기가 속 빈 껍데기가 된다."""
    ratio = len(NO_REJECTION) / len(ROUTES)
    assert ratio < 0.25, (
        f"거부 없음으로 선언된 경로가 {len(NO_REJECTION)}/{len(ROUTES)} 개다. "
        "훑기가 실제로 검사하는 것이 줄고 있다."
    )
