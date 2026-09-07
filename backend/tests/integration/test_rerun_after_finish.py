"""끝난 실행 뒤의 재실행과 연타 방어 (005 T013·T014·T015).

**리포트가 "가장 아픈 것" 으로 지목한 결함이 이 파일의 대상이다.**

- 결과 화면에서 재실행을 네 번 눌러 `POST /api/sessions` 4건이 **모두 409** 였다.
  화면은 "먼저 중지하세요" 라고 했지만 그 화면에는 중지가 없었다 (U-01)
- 「처음부터 실행」을 52 ms 안에 5회 눌러 요청 5건이 나가고 **2건이 201** 이었다.
  실제 브라우저 창 두 개가 떠 같은 테스트를 동시에 두 번 돌았다 (U-06)
"""

from __future__ import annotations

import asyncio
import threading

from fastapi.testclient import TestClient
from us2_support import record_login, start_replay, stop_quietly, wait_for_run


def test_finished_session_does_not_block_rerun(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """종료된 세션이 남아 있어도 재실행이 시작된다 (FR-124·SC-212).

    이전에는 실행이 끝나도 세션이 `failed`/`completed` 상태로 등록에 남았고,
    `active_session_for_test()` 가 상태를 보지 않아 **종료된 세션도 "실행 중" 으로
    셌다.** 그래서 방금 끝난 실행 뒤의 재실행이 항상 거절됐다.
    """
    test_id = record_login(keyed_client, fixture_app)

    first = start_replay(keyed_client, test_id)
    view = wait_for_run(keyed_client, first)
    assert view["state"] in {"completed", "failed"}, f"실행이 끝나지 않았다: {view['state']}"

    # **세션을 정리하지 않은 채** 곧바로 다시 실행한다 — 사용자가 결과 화면에서
    # 재실행을 누르는 상황과 같다.
    again = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert again.status_code == 201, (
        f"종료된 세션이 재실행을 막았다 (U-01): {again.status_code} {again.text}"
    )
    try:
        assert again.json()["session_id"] != first
    finally:
        stop_quietly(keyed_client, again.json()["session_id"])
        stop_quietly(keyed_client, first)


def test_finished_session_is_dropped_from_registry(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """종료된 세션은 등록에서 떼어낸다 (FR-124).

    남겨 두면 같은 판정을 매 호출마다 다시 해야 하고, 판정을 지나지 않는 경로가
    하나라도 생기면 그곳에서 옛 결함이 되살아난다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    wait_for_run(keyed_client, sid)

    manager = keyed_client.app.state.itb.sessions
    assert manager.active_session_for_test(test_id) is None, (
        "종료된 세션이 활성으로 남아 있다"
    )
    stop_quietly(keyed_client, sid)


def test_live_session_still_blocks_and_says_where_to_go(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """정말 실행 중이면 거절한다. **다만 어디로 가야 하는지 준다** (FR-126·FR-135).

    FR-043(테스트당 동시 실행 1건)은 유지된다 — 이 라운드가 바꾼 것은 거절의 정확성과,
    거절 화면에서 그 세션에 도달할 수 있다는 것이다.
    """
    test_id = record_login(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        rejected = keyed_client.post(
            "/api/sessions", json={"mode": "replay", "test_id": test_id}
        )
        assert rejected.status_code == 409, rejected.text
        body = rejected.json()["error"]
        assert body["code"] == "SESSION_ALREADY_ACTIVE"

        # 화면이 그 세션으로 가는 버튼을 만들 수 있어야 한다.
        assert body["detail"]["session_id"] == sid, (
            "거절 응답이 활성 세션을 가리키지 않는다 — 화면은 이동 수단을 만들 수 없다"
        )

        # 사용자에게 보이는 문구에는 세션 식별자를 넣지 않는다 (FR-135).
        assert sid not in body["message"]
        assert sid not in (body.get("next_action") or "")
        # "먼저 중지하세요" 라고만 말하고 방법을 주지 않던 문구는 없다.
        assert "먼저 중지하세요" not in body["message"]
    finally:
        stop_quietly(keyed_client, sid)


def test_concurrent_create_yields_exactly_one_session(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """동시에 도착한 생성 요청 중 **정확히 1건만** 201 이다 (FR-128·SC-213·U-06).

    이전에는 확인과 생성 사이에 await 경계가 있고 락이 없어 다섯 요청이 모두 검사를
    통과했다. FR-043 이 경계에서 지켜지지 않았던 것이다.

    `TestClient` 는 요청을 스레드로 보내므로 실제 동시성이 만들어진다.
    """
    test_id = record_login(keyed_client, fixture_app)

    results: list[int] = []
    session_ids: list[str] = []
    lock = threading.Lock()
    ready = threading.Barrier(5)

    def attempt() -> None:
        # 다섯 스레드가 같은 순간에 출발하게 맞춘다 — 연타를 흉내 내는 것이 목적이다.
        ready.wait(timeout=30)
        resp = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
        with lock:
            results.append(resp.status_code)
            if resp.status_code == 201:
                session_ids.append(resp.json()["session_id"])

    threads = [threading.Thread(target=attempt) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)

    try:
        created = [c for c in results if c == 201]
        rejected = [c for c in results if c == 409]
        assert len(created) == 1, (
            f"동시 5건 중 {len(created)}건이 세션을 만들었다 (U-06). 상태 코드: {results}"
        )
        assert len(rejected) == 4, f"나머지가 409 로 거절되지 않았다: {results}"
        assert len(session_ids) == 1
    finally:
        for sid in session_ids:
            stop_quietly(keyed_client, sid)


def test_repeated_create_after_cleanup_is_allowed(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """예약이 새지 않는다.

    락·예약을 넣으면서 가장 위험한 실수는 **예약을 놓지 않는 것**이다. 그러면 그 테스트가
    프로세스가 끝날 때까지 "실행 중" 으로 잠긴다 — 고치려던 결함보다 나쁘다.
    """
    test_id = record_login(keyed_client, fixture_app)
    for _ in range(3):
        sid = start_replay(keyed_client, test_id)
        stop_quietly(keyed_client, sid)
        keyed_client.post(f"/api/sessions/{sid}/discard")


def test_unreachable_target_releases_reservation(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """생성이 실패해도 예약을 놓는다.

    대상 앱이 안 떠 있는 것은 이 도구에서 가장 흔한 첫 실패다. 그때 예약이 남으면
    사용자는 앱을 띄운 뒤에도 실행할 수 없다.
    """
    test_id = record_login(keyed_client, fixture_app)

    # 저장된 정의의 start_url 을 닫힌 포트로 바꿔 생성이 실패하게 만든다.
    repo = keyed_client.app.state.itb.require_repository()
    test = repo.read_test(test_id)
    broken = test.model_copy(update={"start_url": "http://127.0.0.1:9/"})
    repo.write_test(broken)

    failed = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert failed.status_code == 400, failed.text

    manager = keyed_client.app.state.itb.sessions
    assert manager.reservation_for_test(test_id) is None, (
        "생성 실패 뒤 예약이 남았다 — 그 테스트는 영구히 잠긴다"
    )

    # 정의를 되돌리면 다시 실행할 수 있어야 한다.
    repo.write_test(test)
    sid = start_replay(keyed_client, test_id)
    stop_quietly(keyed_client, sid)


def test_asyncio_gather_create_is_also_serialized(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """락이 **같은 이벤트 루프 안의** 동시 요청도 막는다 (FR-128).

    스레드 경로만 검증하면 `asyncio.Lock` 이 아니라 GIL 우연에 의존하는 구현도 통과할
    수 있다. 루프 안에서도 직렬화되는지 확인한다.
    """
    test_id = record_login(keyed_client, fixture_app)
    manager = keyed_client.app.state.itb.sessions

    async def race() -> list[str | None]:
        # 실제 세션을 만들지 않고 **예약 경쟁만** 본다. 브라우저 다섯 개를 띄우지 않고
        # 경계 보호를 확인하는 방법이다.
        async def one(token: str) -> str | None:
            held = manager.reservation_for_test(test_id)
            if held:
                return None
            manager.reserve_for_test(test_id, token)
            await asyncio.sleep(0)  # 예약 후 경계를 한 번 지난다
            return token

        return list(await asyncio.gather(*(one(f"t{i}") for i in range(5))))

    winners = [w for w in asyncio.run(race()) if w is not None]
    manager.release_reservation(test_id, winners[0])
    assert len(winners) == 1, f"예약이 여럿 잡혔다: {winners}"
