"""외부 경계(boundary) 면의 실행 수단 — 14건.

등록하지 않으면 test_catalogue 의 수단 전수성 검사가 실패한다 (RG-106).

이 면이 흔드는 것은 **제품이 바깥과 맞닿는 자리**다 — 대상 사이트, 브라우저, 언어모델,
파일 쓰기. 제품에 실패 주입 스위치를 넣지 않는다 (헌법 원칙 II). 대상 사이트가 느린 것은
고정 앱이 실제로 느려서고, 브라우저가 사라지는 것은 바깥에서 실제로 닫아서다.

각 수단은 이상 조작 하나를 가하고 :class:`Attempt` 를 돌려준다. **기대 응답을 적지 않는다** —
판정은 3축이 한다.
"""

from __future__ import annotations

from typing import Any

from itb.domain.error import ErrorCode, error_body
from tests.abnormal.boundary_context import (
    BOOM_PATH,
    HANG_PATH,
    NAMELESS_PATH,
    NOISY_PATH,
    SLOW_PATH,
    StepOutcome,
)
from tests.abnormal.catalogue import Attempt, driver

# 세션이 없어도 화면 조작은 계속 가능해야 한다 — 그 판정에 쓰는 사유 문구.
NO_SESSION = "세션을 만들지 못했습니다"


def _from_step(outcome: StepOutcome, *, preserved: bool | None = None) -> Attempt:
    """Step 실행 결과 하나를 판정 대상으로 옮긴다.

    실행기는 HTTP 응답을 내지 않는다. 실패하면 **분류와 사람이 읽을 사유**를 든
    `StepFailure` 를 던지고, 러너가 그것을 `step_failed` 이벤트의 계약 형태 본문으로
    바꿔 화면에 보낸다. 여기서는 그 변환을 **러너와 같은 함수로** 한다 — 수단이 분류를
    지어내지 않고 옮기기만 한다는 뜻이다.

    러너가 실제로 그렇게 내보내는지는 이 수단이 아니라
    `test_boundary_surface.py::test_step_failure_reaches_the_screen_classified` 가
    실제 소켓으로 확인한다. 그 검증이 없으면 이 변환은 자기 자신을 재는 것이 된다.
    """
    return Attempt(
        rejected=not outcome.ok,
        error=None if outcome.ok else error_body(outcome.code, outcome.reason),
        surfaced=outcome.reason or None,
        preserved=preserved,
        crashed=outcome.code is ErrorCode.INTERNAL_ERROR,
    )


# ─── 잘못된 입력값 — 바깥이 이상한 것을 준다 (AS-013~AS-017) ────────────────


@driver("AS-013")
def _ai_returns_a_body_that_is_not_json(ctx: Any) -> Attempt:
    """모델 응답을 해석할 수 없다. 그때까지의 Step 은 남아야 한다 (AP-032)."""
    session_id = ctx.paused_session()
    before = ctx.step_count(session_id)
    with ctx.ai_returning_garbage():
        resp = ctx.client.post(
            f"/api/sessions/{session_id}/ai-step", json={"instruction": "로그인해"}
        )

    at = Attempt.from_response(resp, preserved=ctx.step_count(session_id) >= before)
    if resp.status_code < 400:
        body = resp.json()
        # `ai-step` 은 실패를 200 으로 알린다 — 만들지 못했다는 사실은 `created` 에 있다.
        at.rejected = not body.get("created", False)
        at.surfaced = body.get("message")
    return at


@driver("AS-014")
def _ai_asks_for_a_step_type_that_does_not_exist(ctx: Any) -> Attempt:
    """모델이 없는 종류를 지시한다. 도구가 거절하고 Step 이 만들어지지 않아야 한다."""
    session_id = ctx.paused_session()
    before = ctx.step_count(session_id)
    # 도구함은 에이전트를 만들 때 준비된다. 먼저 한 번 불러 그것을 만든다.
    ctx.client.post(f"/api/sessions/{session_id}/ai-step", json={"instruction": "화면을 본다"})

    with ctx.ai_asking_for_unknown_step(session_id):
        resp = ctx.client.post(
            f"/api/sessions/{session_id}/ai-step", json={"instruction": "이상한 검증을 걸어"}
        )

    at = Attempt.from_response(resp, preserved=ctx.step_count(session_id) >= before)
    if resp.status_code < 400:
        body = resp.json()
        at.rejected = not body.get("created", False)
        at.surfaced = body.get("message")
    return at


@driver("AS-015")
def _target_page_has_very_long_text_and_control_characters(ctx: Any) -> Attempt:
    """지저분한 화면이어도 세션이 서고 기록이 남아야 한다. 거부할 일이 아니다."""
    _, session_id, text = ctx.session_at(NOISY_PATH)
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    outcome = ctx.run_step(
        session_id,
        {
            "type": "click",
            "id": "step-99",
            "label": "긴 라벨 누르기",
            "timeout_ms": 3000,
            "target": {"test_id": {"value": "noisy-long", "status": "verified"}},
        },
    )
    return _from_step(outcome, preserved=ctx.session_readable(session_id))


@driver("AS-016")
def _target_page_has_no_accessible_names(ctx: Any) -> Attempt:
    """이름이 하나도 없는 화면. 후보가 css 하나뿐이어도 무너지지 않아야 한다."""
    _, session_id, text = ctx.session_at(NAMELESS_PATH)
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    outcome = ctx.run_step(
        session_id,
        {
            "type": "click",
            "id": "step-99",
            "label": "이름 없는 버튼",
            "timeout_ms": 3000,
            "target": {"css": {"value": ".row > button:nth-child(1)", "status": "verified"}},
        },
    )
    return _from_step(outcome, preserved=ctx.session_readable(session_id))


@driver("AS-017")
def _target_site_answers_with_an_error_and_a_body_that_is_not_html(ctx: Any) -> Attempt:
    """대상이 503 과 이진 본문을 준다. 제품은 그것을 옮길 뿐 깨지지 않아야 한다."""
    _, session_id, text = ctx.session_at("/login.html")
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    outcome = ctx.goto(session_id, BOOM_PATH)
    return _from_step(outcome, preserved=ctx.session_readable(session_id))


# ─── 순서·상태 위반 (AS-030~AS-032) ─────────────────────────────────────────


@driver("AS-030")
def _run_a_step_against_a_tab_that_was_closed(ctx: Any) -> Attempt:
    """탭을 바깥에서 닫고 그 탭에 Step 을 건다 (AP-030)."""
    _, session_id, text = ctx.session_at("/login.html")
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    ctx.close_tab_outside(session_id, 0)
    outcome = ctx.run_step(
        session_id,
        {
            "type": "click",
            "id": "step-99",
            "label": "닫힌 탭에서 누르기",
            "tab": 0,
            "timeout_ms": 1500,
            "target": {"test_id": {"value": "login-submit", "status": "verified"}},
        },
    )
    return _from_step(outcome, preserved=ctx.session_readable(session_id))


@driver("AS-031")
def _the_page_navigates_away_while_an_element_is_being_found(ctx: Any) -> Attempt:
    """요소를 찾는 도중 페이지가 옮겨간다. 거부할 일이 아니라 다시 잡을 일이다."""
    _, session_id, text = ctx.session_at("/login.html")
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    # 느린 화면으로 옮기는 중에 요소를 찾게 만든다. 이동이 끝나면 그 요소는 없다.
    async def start_navigation() -> None:
        session = ctx.session_obj(session_id)
        handle = session.find_tab(0)
        if handle is not None:
            # 기다리지 않고 띄운다 — 이동 도중이라는 상태를 만드는 것이 목적이다.
            import asyncio  # noqa: PLC0415 - 이 자리에서만 쓴다

            asyncio.ensure_future(handle.page.goto(ctx.target(SLOW_PATH)))  # noqa: RUF006

    ctx.call(start_navigation)
    outcome = ctx.run_step(
        session_id,
        {
            "type": "click",
            "id": "step-99",
            "label": "이동 중에 누르기",
            "timeout_ms": 4000,
            "target": {"test_id": {"value": "slow-action", "status": "verified"}},
        },
    )
    return _from_step(outcome, preserved=ctx.session_readable(session_id))


@driver("AS-032")
def _mirror_asks_for_frames_after_the_session_ended(ctx: Any) -> Attempt:
    """끝난 세션의 미러가 표시 탭을 바꾸려 한다. 거절돼야 한다."""
    session_id = ctx.finished_session()
    resp = ctx.client.post(f"/api/sessions/{session_id}/mirror-tab", json={"tab_index": 0})
    return Attempt.from_response(resp)


# ─── 외부 환경 실패 (AS-040~AS-042) ─────────────────────────────────────────


@driver("AS-040")
def _the_browser_is_closed_from_outside(ctx: Any) -> Attempt:
    """세션이 쥔 브라우저를 바깥에서 닫는다. 기록된 Step 은 남아야 한다 (AP-030)."""
    session_id, steps_before = ctx.session_with_lost_browser()
    resp = ctx.client.get(f"/api/sessions/{session_id}")
    preserved = resp.status_code == 200 and len(resp.json().get("steps", [])) >= steps_before
    return Attempt.from_response(resp, preserved=preserved)


@driver("AS-041")
def _target_site_holds_the_connection_open(ctx: Any) -> Attempt:
    """대상이 응답을 끝내지 않는다. 무한정 기다리면 안 된다 (AP-031)."""
    _, session_id, text = ctx.session_at("/login.html")
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    outcome = ctx.goto(session_id, HANG_PATH, timeout_ms=3000)
    return _from_step(outcome, preserved=ctx.session_readable(session_id))


@driver("AS-042")
def _the_ai_call_fails_while_connecting(ctx: Any) -> Attempt:
    """요청이 나가지도 못했다. 세션은 유지돼야 한다 (AP-032)."""
    session_id = ctx.paused_session()
    before = ctx.step_count(session_id)
    with ctx.ai_transport_failing():
        resp = ctx.client.post(
            f"/api/sessions/{session_id}/ai-step", json={"instruction": "로그인해"}
        )

    at = Attempt.from_response(resp, preserved=ctx.step_count(session_id) >= before)
    if resp.status_code < 400:
        body = resp.json()
        at.rejected = not body.get("created", False)
        at.surfaced = body.get("message")
    return at


# ─── 동시성·중단 (AS-049~AS-051) ────────────────────────────────────────────


@driver("AS-049")
def _the_definition_write_is_cut_off_halfway(ctx: Any) -> Attempt:
    """정의를 쓰는 도중 끊긴다. **앞선 정의가 살아 있어야 한다** (AP-042)."""
    test_id = ctx.saved_test()
    assert ctx.definition_readable(test_id), "준비 단계에서 정의를 만들지 못했다"

    with ctx.writes_interrupted(contains=".yaml"):
        resp = ctx.client.patch(f"/api/tests/{test_id}", json={"name": "쓰다 만 이름"})

    return Attempt.from_response(resp, preserved=ctx.definition_readable(test_id))


@driver("AS-050")
def _the_secret_store_write_is_cut_off_halfway(ctx: Any) -> Attempt:
    """비밀 값 저장소를 쓰는 도중 끊긴다. 앞서 넣은 이름이 남아야 한다 (AS-050)."""
    ctx.client.post("/api/keys/generate", json={"passphrase": None})
    ctx.client.put("/api/secrets/FIRST_ONE", json={"value": "먼저 넣은 값"})
    before = ctx.secret_names() or []

    with ctx.writes_interrupted(contains=".yaml"):
        resp = ctx.client.put("/api/secrets/SECOND_ONE", json={"value": "쓰다 만 값"})

    after = ctx.secret_names()
    preserved = after is not None and all(name in after for name in before)
    return Attempt.from_response(resp, preserved=preserved)


@driver("AS-051")
def _two_tabs_deliver_element_events_at_once(ctx: Any) -> Attempt:
    """탭 둘에서 동시에 조작이 도착한다. 어느 쪽도 잃지 않아야 한다."""
    # 고정 앱은 로그인하지 않은 채 다른 화면을 열면 login.html 로 되돌린다. 두 탭이
    # 서로 다른 화면이어야 "각 탭이 제 요소를 잡았는가"를 잴 수 있으므로 그 규칙을
    # 지나지 않는 화면 둘을 쓴다.
    _, session_id, text = ctx.session_at("/login.html")
    if session_id is None:
        return Attempt(rejected=True, surfaced=f"{NO_SESSION}: {text}", crashed=True)

    async def open_second_tab() -> None:
        # 등록은 `context.on("page")` 가 이미 한다. 여기서 또 하면 탭이 둘로 세어진다.
        session = ctx.session_obj(session_id)
        page = await session.context.new_page()
        await page.goto(ctx.target("/terms.html"))

    ctx.call(open_second_tab)

    # 두 탭에 각각 Step 을 건다. 실행기는 탭을 해석해 서로 다른 페이지를 잡아야 한다.
    first = ctx.run_step(
        session_id,
        {
            "type": "click",
            "id": "step-98",
            "label": "탭 0 에서 누르기",
            "tab": 0,
            "timeout_ms": 3000,
            "target": {"test_id": {"value": "login-submit", "status": "verified"}},
        },
    )
    second = ctx.run_step(
        session_id,
        {
            "type": "click",
            "id": "step-99",
            "label": "탭 1 에서 누르기",
            "tab": 1,
            "timeout_ms": 3000,
            "target": {"test_id": {"value": "close-terms", "status": "verified"}},
        },
    )

    # 둘 중 하나라도 실패하면 그 조작이 유실된 것이다. 실패한 쪽의 분류를 그대로 든다.
    failed = first if not first.ok else second
    both = StepOutcome(
        ok=first.ok and second.ok,
        reason=" / ".join(r for r in (first.reason, second.reason) if r),
        code=failed.code,
    )
    return _from_step(both, preserved=ctx.session_readable(session_id))
