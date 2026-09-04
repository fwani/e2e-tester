"""T034 — 명세의 Edge Case 를 확인한다.

시나리오 51건은 "이상 조작 하나" 를 판정한다. 여기서 보는 것은 그 목록이 다루지 않는
**두 가지 다른 질문**이다.

1. **이상 조작을 연달아 반복해도 자원이 누적되지 않는가** — 한 번의 거부는 깨끗한데
   백 번의 거부가 세션·파일 손잡이·메모리를 쌓아 두면 도구는 오래 쓸수록 느려진다
2. **오류 처리 자체가 실패하면 사용자가 무엇을 보는가** — 분류를 붙이는 과정에서
   예외가 나면 그것을 처리할 자리가 없다. 그때도 사용자는 계약 형태의 응답을 받아야 한다

둘 다 "한 건을 재는" 방식으로는 드러나지 않는다.
"""

from __future__ import annotations

import gc
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.domain.error import ErrorCode
from tests.abnormal.catalogue import _LEAK, REQUIRED_ERROR_FIELDS

REPEATS = 120
"""거부를 반복할 횟수. 누수가 있으면 이 규모에서 이미 드러난다."""


# ─── ① 이상 조작을 연달아 반복해도 자원이 누적되지 않는다 ───────────────────


def _burst(client: TestClient, rounds: int) -> set[str]:
    """서로 다른 거부 경로를 섞어 그만큼 몰아친다. 나온 코드를 모아 돌려준다.

    경로 탈출 · 없는 세션 · 잘못된 주소 · 요청 본문 검증 실패 — 네 가지 거부 경로를
    섞는다. 한 경로만 반복하면 그 경로만 깨끗하다는 것밖에 알 수 없다.
    """
    codes: set[str] = set()
    for _ in range(rounds):
        codes.add(
            client.post("/api/project/open", json={"path": "../../../../etc/passwd"}).json()[
                "error"
            ]["code"]
        )
        codes.add(client.post("/api/sessions/__없는것__/pause").json()["error"]["code"])
        codes.add(client.put("/api/secrets/a%2Fb", json={"value": "x"}).json()["error"]["code"])
        codes.add(
            client.post("/api/project/create", json={"name": "   "}).json()["error"]["code"]
        )
    return codes


def test_repeated_rejections_do_not_pile_up_state(project_client: TestClient) -> None:
    """거부된 요청을 즉시 반복해도 세션·객체가 쌓이지 않는다.

    **준비 비용을 먼저 치르고 잰다.** 첫 회차는 임포트와 캐시로 객체가 2천 개 넘게
    늘어난다 — 그것을 누수로 세면 있지도 않은 결함을 보고하게 되고, 반대로 그만큼을
    허용 폭으로 잡으면 진짜 누수를 놓친다. 준비를 끝낸 뒤 같은 크기로 두 번 몰아쳐
    **회차에 비례해 늘어나는 것이 있는지**를 본다 (실측: 240회에 증가 0).
    """
    warmup = 40
    _burst(project_client, warmup)

    before_sessions = project_client.get("/api/health").json()["active_sessions"]
    gc.collect()
    baseline = len(gc.get_objects())

    codes = _burst(project_client, REPEATS)
    gc.collect()
    after_first = len(gc.get_objects())

    codes |= _burst(project_client, REPEATS)
    gc.collect()
    after_second = len(gc.get_objects())

    after_sessions = project_client.get("/api/health").json()["active_sessions"]

    assert after_sessions == before_sessions, (
        f"거부 {REPEATS * 8}회 뒤 세션이 {after_sessions - before_sessions}개 늘었다. "
        "거부는 아무것도 만들지 않는 조작이다"
    )

    # 두 회차의 증가가 회차 수에 비례하면 누수다. 준비가 끝난 뒤라 여유 폭은 좁게 둔다.
    grew_first = after_first - baseline
    grew_second = after_second - after_first
    allowance = REPEATS  # 4회 요청당 1개꼴. 실측은 0 이다
    assert grew_first < allowance and grew_second < allowance, (
        f"거부를 반복하니 객체가 쌓인다 — 1회차 {grew_first}개, 2회차 {grew_second}개 "
        f"(각 {REPEATS * 4}회 요청). 거부 경로가 무언가를 남기고 있다"
    )

    # 같은 조작은 끝까지 같은 코드로 거부된다 — 반복하다 다른 실패로 변하지 않는다.
    assert codes == {
        ErrorCode.INVALID_PATH.value,
        ErrorCode.SESSION_NOT_FOUND.value,
        ErrorCode.DEFINITION_INVALID.value,
    }, f"반복 중 거부 코드가 흔들렸다: {sorted(codes)}"


def test_the_project_stays_usable_after_a_burst_of_rejections(
    project_client: TestClient,
) -> None:
    """거부를 몰아친 뒤에도 정상 조작이 그대로 된다 (AP-024 를 반복 규모로 확장)."""
    for _ in range(REPEATS):
        project_client.post("/api/project/create", json={"name": "   "})

    assert project_client.get("/api/project").status_code == 200
    assert project_client.get("/api/tests").status_code == 200
    assert project_client.get("/api/secrets").status_code == 200


# ─── ② 오류 처리 자체가 실패하면 사용자가 무엇을 보는가 ─────────────────────


@pytest.fixture
def app_that_breaks_while_handling_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    """분류를 붙이는 과정에서 터지는 앱.

    `ErrorBody` 를 만드는 자리를 무너뜨린다 — 오류를 계약 형태로 옮기는 바로 그 지점이
    실패하는 상황이며, 그것을 처리할 자리는 그 안에 없다.
    """
    app = create_app()

    @app.get("/api/__오류처리가-깨진다__")
    async def _boom() -> None:
        msg = "의도적으로 처리하지 않은 오류"
        raise RuntimeError(msg)

    def refuse_to_build(*_args: object, **_kwargs: object) -> object:
        msg = "분류를 붙이는 과정 자체가 실패했다 (검증용)"
        raise RuntimeError(msg)

    monkeypatch.setattr("itb.api.app.ErrorBody", refuse_to_build)
    return app


def test_the_user_still_gets_an_answer_when_error_handling_breaks(
    app_that_breaks_while_handling_errors: FastAPI,
) -> None:
    """오류 처리가 실패해도 **무응답이 되지 않는다.**

    처리기 안에서 다시 터지면 프레임워크의 마지막 그물이 받는다. 그때 사용자가 받는
    것은 계약 형태가 아니지만, **응답은 온다** — 무응답은 판정축 ①이 가장 나쁘게 보는
    결과다. 그리고 내부 경로·스택은 그때도 새지 않아야 한다 (EC-005).
    """
    with TestClient(
        app_that_breaks_while_handling_errors, raise_server_exceptions=False
    ) as client:
        resp = client.get("/api/__오류처리가-깨진다__")

    assert resp.status_code >= 500, f"오류인데 {resp.status_code} 로 나갔다"
    leak = _LEAK.search(resp.text)
    assert leak is None, f"오류 처리가 깨진 응답에 내부 정보가 노출됐다: {leak.group(0)}"
    assert "의도적으로 처리하지 않은 오류" not in resp.text, "예외 메시지가 그대로 나갔다"
    assert "검증용" not in resp.text, "두 번째 예외 메시지가 그대로 나갔다"


def test_error_handling_that_works_is_the_normal_case(client: TestClient) -> None:
    """앞 검증이 무엇과 비교되는지 남긴다 — 처리가 멀쩡하면 계약 형태가 나온다.

    이것이 없으면 위 검증이 "그냥 500 이면 통과" 로 읽힌다.
    """
    app = create_app()

    @app.get("/api/__보통의-오류__")
    async def _boom() -> None:
        msg = "의도적으로 처리하지 않은 오류"
        raise RuntimeError(msg)

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/__보통의-오류__")

    assert resp.status_code == 500
    body = resp.json()["error"]
    assert REQUIRED_ERROR_FIELDS <= set(body), f"필드가 빠졌다: {sorted(body)}"
    assert body["code"] == ErrorCode.INTERNAL_ERROR.value
    assert body["category"] == "broken"
    assert body["next_action"].strip(), "깨진 것에도 다음 행동이 있어야 한다"
    assert _LEAK.search(json.dumps(body, ensure_ascii=False)) is None
