"""요청 경계(api) 면의 실행 수단 — 19건.

등록하지 않으면 test_catalogue 의 수단 전수성 검사가 실패한다 (RG-106).

각 수단은 이상 조작 하나를 가하고 :class:`Attempt` 를 돌려준다. **기대 응답을 적지 않는다** —
판정은 3축이 한다. 수단이 하는 일은 "조작을 가하고, 무엇이 남았는지 재는 것"뿐이다.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.abnormal.catalogue import Attempt, driver

# 상위 경로를 가리키는 값. 홈 밖으로 나가려는 시도다.
ESCAPE = "../../../../etc/passwd"
HUGE = "가" * 100_000


def _tests_intact(client: TestClient) -> bool:
    """테스트 목록이 여전히 읽히는가 — 주변 자산이 손상되지 않았다는 뜻이다."""
    resp = client.get("/api/tests")
    return resp.status_code == 200 and "tests" in resp.json()


def _registry_intact(client: TestClient) -> bool:
    return client.get("/api/project/list").status_code == 200


def _secrets_intact(client: TestClient) -> bool:
    return client.get("/api/secrets").status_code == 200


def _session_usable(client: TestClient, session_id: str) -> bool:
    """거부 뒤에도 이 세션을 계속 쓸 수 있는가 (AP-024)."""
    return client.get(f"/api/sessions/{session_id}").status_code == 200


# ─── 잘못된 입력값 (AS-001~AS-006) ──────────────────────────────────────────


@driver("AS-001")
def _blank_project_name(ctx: Any) -> Attempt:
    resp = ctx.client.post(
        "/api/project/create",
        json={"name": "   ", "default_start_url": ctx.fixture_app + "/login.html"},
    )
    return Attempt.from_response(resp, preserved=_registry_intact(ctx.client))


@driver("AS-002")
def _project_path_escape(ctx: Any) -> Attempt:
    resp = ctx.client.post("/api/project/open", json={"path": ESCAPE})
    return Attempt.from_response(resp, preserved=_registry_intact(ctx.client))


@driver("AS-003")
def _secret_name_with_separators_and_emoji(ctx: Any) -> Attempt:
    resp = ctx.client.put("/api/secrets/a%2Fb%F0%9F%98%80", json={"value": "x"})
    return Attempt.from_response(resp, preserved=_secrets_intact(ctx.client))


@driver("AS-004")
def _session_start_url_not_a_url(ctx: Any) -> Attempt:
    resp = ctx.client.post("/api/sessions", json={"mode": "record", "start_url": "not-a-url"})
    return Attempt.from_response(resp)


@driver("AS-005")
def _rename_test_to_an_existing_name(ctx: Any) -> Attempt:
    first, second = ctx.two_tests()
    original = ctx.client.get(f"/api/tests/{second}").json()["name"]
    taken = ctx.client.get(f"/api/tests/{first}").json()["name"]

    resp = ctx.client.patch(f"/api/tests/{second}", json={"name": taken})

    # 이름 유일성 규칙이 없으므로 거부는 기대하지 않는다. 판정 대상은 **기존 테스트가
    # 덮어써지지 않았는가**다 (AP-014).
    del original
    still_there = ctx.client.get(f"/api/tests/{first}").status_code == 200
    name_kept = ctx.client.get(f"/api/tests/{first}").json()["name"] == taken
    return Attempt.from_response(resp, preserved=still_there and name_kept)


@driver("AS-006")
def _huge_step_value(ctx: Any) -> Attempt:
    session_id = ctx.paused_session()
    resp = ctx.client.post(
        f"/api/sessions/{session_id}/steps",
        json={
            "step": {
                "type": "fill",
                "id": "step-01",
                "label": "긴 값",
                "value": HUGE,
                "target": {"candidates": []},
            }
        },
    )
    at = Attempt.from_response(resp, preserved=_session_usable(ctx.client, session_id))
    # 아주 긴 입력이 거부될 때 원본을 그대로 되돌려 보내면 화면이 망가진다 (AP-015).
    if at.error is not None and HUGE[:200] in str(at.error):
        at.notes.append("거부 응답이 입력 원본을 되돌려 보낸다 (AP-015)")
        at.crashed = True
    return at


# ─── 순서·상태 위반 (AS-018~AS-023) ─────────────────────────────────────────


@driver("AS-018")
def _stop_recording_that_never_started(ctx: Any) -> Attempt:
    # 일시정지 상태 — `record-actions:start` 를 부른 적이 없다. `mode: record` 세션은
    # 처음부터 녹화 중이라 "시작하지 않았다" 는 상황이 되지 않는다.
    session_id = ctx.paused_session()
    resp = ctx.client.post(f"/api/sessions/{session_id}/record-actions:stop")
    return Attempt.from_response(resp, preserved=_session_usable(ctx.client, session_id))


@driver("AS-019")
def _resume_a_finished_session(ctx: Any) -> Attempt:
    session_id = ctx.finished_session()
    resp = ctx.client.post(f"/api/sessions/{session_id}/resume")
    # 끝난 세션이라도 그 세션에서 만든 결과는 조회할 수 있어야 한다 (AP-002).
    readable = ctx.client.get(f"/api/sessions/{session_id}").status_code in (200, 404)
    return Attempt.from_response(resp, preserved=readable)


@driver("AS-020")
def _patch_a_step_that_does_not_exist(ctx: Any) -> Attempt:
    session_id = ctx.session()
    before = ctx.step_count(session_id)
    resp = ctx.client.patch(
        f"/api/sessions/{session_id}/steps/step-없음", json={"label": "바꿔보기"}
    )
    return Attempt.from_response(resp, preserved=ctx.step_count(session_id) == before)


@driver("AS-021")
def _reorder_with_an_unknown_step(ctx: Any) -> Attempt:
    session_id = ctx.session()
    before = ctx.step_count(session_id)
    resp = ctx.client.post(
        f"/api/sessions/{session_id}/steps:reorder", json={"order": ["step-없음"]}
    )
    return Attempt.from_response(resp, preserved=ctx.step_count(session_id) == before)


@driver("AS-022")
def _pause_an_already_paused_session(ctx: Any) -> Attempt:
    session_id = ctx.paused_session()
    resp = ctx.client.post(f"/api/sessions/{session_id}/pause")
    return Attempt.from_response(resp, preserved=_session_usable(ctx.client, session_id))


@driver("AS-023")
def _save_a_discarded_session(ctx: Any) -> Attempt:
    session_id = ctx.session()
    ctx.client.post(f"/api/sessions/{session_id}/discard")
    resp = ctx.client.post(f"/api/sessions/{session_id}/save", json={"name": "버린 세션"})
    return Attempt.from_response(resp)


# ─── 외부 환경 실패 (AS-033~AS-036) ─────────────────────────────────────────


@driver("AS-033")
def _ai_availability_without_credentials(ctx: Any) -> Attempt:
    """자격이 없어도 가용성 질문 자체는 답을 받아야 한다 — 실패가 아니다."""
    resp = ctx.client.get("/api/ai/availability")
    return Attempt.from_response(resp)


@driver("AS-034")
def _ai_step_when_the_model_errors(ctx: Any) -> Attempt:
    session_id = ctx.paused_session()
    before = ctx.step_count(session_id)
    with ctx.ai_failing():
        resp = ctx.client.post(
            f"/api/sessions/{session_id}/ai-step", json={"instruction": "로그인해"}
        )
    # AI 가 실패해도 이미 만들어진 Step 은 남아야 한다 (AP-032).
    return Attempt.from_response(resp, preserved=ctx.step_count(session_id) >= before)


@driver("AS-035")
def _ai_choice_when_the_model_times_out(ctx: Any) -> Attempt:
    session_id = ctx.paused_session()
    before = ctx.step_count(session_id)
    with ctx.ai_timing_out():
        resp = ctx.client.post(f"/api/sessions/{session_id}/ai-choice", json={"choice": "continue"})
    return Attempt.from_response(resp, preserved=ctx.step_count(session_id) >= before)


@driver("AS-036")
def _read_a_session_that_lost_its_browser(ctx: Any) -> Attempt:
    session_id, steps_before = ctx.session_with_lost_browser()
    resp = ctx.client.get(f"/api/sessions/{session_id}")
    # 브라우저를 잃어도 기록된 Step 은 읽혀야 한다 (AP-030).
    preserved = resp.status_code == 200 and len(resp.json().get("steps", [])) >= steps_before
    return Attempt.from_response(resp, preserved=preserved)


# ─── 동시성·중복 실행 (AS-043~AS-045) ───────────────────────────────────────


@driver("AS-043")
def _two_sessions_for_the_same_test(ctx: Any) -> Attempt:
    """FR-043 — 테스트당 동시 실행 1건.

    **오래 도는 테스트를 쓴다** (005). 이전에는 `CLOSE_TAB` 한 Step 짜리를 써서 첫 실행이
    즉시 끝났고, 두 세션이 실제로는 겹치지 않았다. 그런데도 이 시나리오가 통과했던 이유는
    종료된 세션까지 **등록만으로** 다음 실행을 막았기 때문이다 — 그것이 U-01 의 결함이고,
    사용자는 방금 끝난 실행 뒤 재실행이 항상 거절되는 것을 만났다.

    005 가 판정을 살아 있는 세션으로 좁히면서 이 드라이버가 **주장한 것과 실제로 검증하던
    것의 차이**가 드러났다. 단정(거절되어야 한다)은 그대로 두고 전제를 실제로 만든다.
    """
    test_id = ctx.slow_test()
    first = ctx.client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert first.status_code < 400, f"전제 실패 — 첫 세션을 만들지 못했다: {first.text}"
    first_id = first.json()["session_id"]

    # 첫 세션이 **정말 살아 있는지** 확인한다. 끝났다면 이 시나리오는 동시성을 검증하지
    # 못하며, 그때 두 번째가 성공하는 것은 결함이 아니라 FR-124 의 의도다.
    state = ctx.client.get(f"/api/sessions/{first_id}").json().get("state")
    assert state in {"starting", "replaying", "paused"}, (
        f"전제 실패 — 첫 실행이 이미 끝났다({state}). 동시성을 검증할 수 없다"
    )

    second = ctx.client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    # 두 번째가 첫 실행을 방해하지 않아야 한다 (AP-040).
    first_alive = _session_usable(ctx.client, first_id)
    return Attempt.from_response(second, preserved=first_alive)


@driver("AS-044")
def _save_the_same_session_twice(ctx: Any) -> Attempt:
    session_id = ctx.session_with_steps()
    before = len(ctx.client.get("/api/tests").json()["tests"])
    ctx.client.post(f"/api/sessions/{session_id}/save", json={"name": "중복 저장"})
    resp = ctx.client.post(f"/api/sessions/{session_id}/save", json={"name": "중복 저장"})
    after = len(ctx.client.get("/api/tests").json()["tests"])
    # 두 번째 저장이 테스트를 하나 더 만들면 안 된다 — 저장은 멱등이다.
    return Attempt.from_response(resp, preserved=after == before + 1 and _tests_intact(ctx.client))


@driver("AS-045")
def _reorder_and_delete_at_once(ctx: Any) -> Attempt:
    session_id = ctx.session_with_steps()
    order = ctx.step_ids(session_id)
    ctx.client.delete(f"/api/sessions/{session_id}/steps/{order[0]}")
    resp = ctx.client.post(f"/api/sessions/{session_id}/steps:reorder", json={"order": order})
    return Attempt.from_response(resp, preserved=_session_usable(ctx.client, session_id))
