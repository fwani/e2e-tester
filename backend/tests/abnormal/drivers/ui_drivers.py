"""화면(ui) 면의 실행 수단 — 18건. **제품 UI 를 실제로 띄워 조작한다** (RG-105).

등록하지 않으면 test_catalogue 의 수단 전수성 검사가 실패한다 (RG-106).

이 저장소에는 제품 화면을 실제로 여는 검증이 없었다. 그래서 아래는 여기서만 판정된다.

- 버튼 연타가 **실제로** 요청을 몇 번 내보내는가 (AS-024)
- 화면을 벗어났다 돌아오면 무엇이 보이는가 (AS-026)
- 두 창에서 같은 것을 조작하면 어떻게 되는가 (AS-046·AS-047)

**판정 근거는 화면에서 읽는다.** 응답이 무엇이었는지가 아니라 사용자가 무엇을 보는지가
이 면의 대상이다. 오류는 공용 통로(`ErrorNotice`)가 남긴 표시로 읽는다 (T016·RG-104-4).

**AS-007 은 프로젝트가 열리기 전에 돌아야 한다.** 제품 화면은 프로젝트가 열려 있으면
목록으로 가고 프로젝트 선택 화면으로 돌아갈 길이 없다 — 닫는 경로가 제품에 없기
때문이다. 목록의 첫 화면 시나리오가 그것이라 순서가 맞고, 어긋나면 `require_no_project`
가 사유와 함께 실패한다. 조용히 건너뛰지 않는다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from tests.abnormal.catalogue import Attempt, driver

LONG_NAME = "가" * 5_000
"""아주 긴 이름. 화면이 이것을 받고도 밀려나지 않아야 한다."""


# ─── 잘못된 입력값 (AS-007~AS-012) ──────────────────────────────────────────


@driver("AS-007")
async def _create_a_project_with_a_blank_name(ctx: Any) -> Attempt:
    """이름을 비운 채 만들기를 누른다. 다른 입력은 화면에 남아야 한다."""
    ctx.require_no_project()
    page = await ctx.open()

    await ctx.click(page, "새 프로젝트 만들기")
    await ctx.fill(page, "기본 시작 URL", "https://example.invalid/login")
    await ctx.fill(page, "프로젝트 이름", "   ")

    blocked = await ctx.is_disabled(page, "만들기")
    # 다른 입력이 화면에 남아 있는가 (판정축 ③ — form-input).
    kept = await page.get_by_label("기본 시작 URL").input_value()
    still_on_setup = await ctx.has_button(page, "만들기")

    return await ctx.from_screen(
        page,
        rejected=blocked,
        prevented=blocked,
        preserved="example.invalid" in kept and still_on_setup,
        surfaced=await ctx.form_guidance(page, "이름")
        or await ctx.disabled_reason(page, "만들기"),
    )


@driver("AS-008")
async def _save_a_test_with_no_steps(ctx: Any) -> Attempt:
    """Step 하나 없이 저장한다.

    저장 상자는 **세션 화면**에 있다. 정의 화면은 읽기 전용이고, AI 작성 화면은 자격
    증명이 없는 환경에서 아예 열리지 않는다 — 화면이 누르기 전에 그렇게 말한다.
    그래서 녹화 세션을 열고 Step 이 하나도 없는 상태에서 저장을 눌러 본다.
    """
    ctx.ensure_project()
    page = await ctx.open()
    session_id = await ctx.start_session_from_ui(page, ctx.fixture("/login.html"))
    ctx.api("POST", f"/api/sessions/{session_id}/pause")
    await ctx.settle(page, ms=2_000)

    name_box = page.get_by_placeholder("테스트 이름")
    typed = await name_box.count() > 0
    if typed:
        await name_box.fill("Step 없는 테스트")
        await ctx.settle(page, ms=400)

    blocked = await ctx.is_disabled(page, "저장")
    kept = (await name_box.input_value()) if typed else ""

    return await ctx.from_screen(
        page,
        rejected=blocked,
        prevented=blocked,
        # 이름을 적어 둔 것이 남아 있는가 (판정축 ③ — form-input).
        preserved=kept == "Step 없는 테스트",
        surfaced=await ctx.form_guidance(page, "저장")
        or await ctx.disabled_reason(page, "저장"),
    )


@driver("AS-009")
async def _store_a_secret_under_a_very_long_name(ctx: Any) -> Attempt:
    """비밀 값 이름에 아주 긴 문자열을 넣는다. 화면이 밀려나지 않아야 한다."""
    ctx.ensure_project()
    page = await ctx.open()

    await ctx.click(page, "비밀 값")
    await ctx.fill(page, "변수 이름", LONG_NAME)
    await ctx.fill(page, "값", "무언가")
    await ctx.click(page, "봉인해 저장")
    await ctx.wait_for_notice(page)

    stored = ctx.api("GET", "/api/secrets")[1]
    names = [n["name"] for n in (stored or {}).get("names", [])]
    return await ctx.from_screen(
        page,
        rejected=not any(len(n) > 1000 for n in names),
        # 입력하던 다른 값이 남아 있는가 — 거부가 화면을 비우면 다시 다 쳐야 한다.
        preserved=await ctx.still_usable(page, "변수 이름"),
    )


@driver("AS-010")
async def _generate_a_key_with_a_passphrase_the_screen_rejects(ctx: Any) -> Attempt:
    """규칙에 맞지 않는 암호구로 키 쌍을 만든다.

    목록은 원래 "암호구 확인란에 다른 값"이라고 적었는데 **화면에 확인란이 없다.**
    같은 자리의 실재하는 규칙(8자 이상)으로 바꿔 적고 근거를 목록의 `note` 에 남겼다.
    """
    ctx.ensure_project()
    page = await ctx.open()

    await ctx.click(page, "키 관리")
    await ctx.fill(page, "암호구", "짧다")

    blocked = await ctx.is_disabled(page, "키 쌍 만들기")
    kept = await page.get_by_label("암호구", exact=False).first.input_value()

    return await ctx.from_screen(
        page,
        rejected=blocked,
        prevented=blocked,
        preserved=kept == "짧다",
        surfaced=await ctx.form_guidance(page, "암호구")
        or await ctx.disabled_reason(page, "키 쌍 만들기"),
    )


@driver("AS-011")
async def _ask_the_ai_without_what_it_needs(ctx: Any) -> Attempt:
    """AI 에게 만들기를 요청한다 — 지시문을 비운 채.

    **007 2회차에 자리가 바뀌었다.** 1회차까지는 「테스트 만들기」 화면에서 「지시문 쓰기」
    버튼을 눌러 별도 화면(`AiCompose`)으로 넘어갔고, 이 수단은 그 버튼이 잠겼는지를
    쟀다. 만들기가 통합 화면의 국면이 되면서 그 이동이 사라졌다 (007 FR-259) — 방법을
    고르면 지시문 자리가 **같은 화면에 펼쳐진다.**

    그래서 이제 목록에 적힌 그대로 잴 수 있다: 지시문을 비운 채 「AI 시작」을 눌러 보고
    막히는지, 왜 막히는지가 화면에 있는지, 넣어 둔 시작 URL 이 남는지. 1회차의 `note`
    (자격 증명이 없으면 지시문 화면에 닿기 전에 막힌다)는 더 이상 필요하지 않다 —
    자격 증명이 없어도 지시문 자리는 있고, 빈 지시문의 거부를 그 자리에서 잴 수 있다.

    빈 지시문 자체의 거부는 요청 경계도 판정한다 (`validate_instruction`). 여기서 재는
    것은 **화면이 요청을 보내기 전에 막는가**다 (007 조건 C14).
    """
    ctx.ensure_project()
    page = await ctx.open()

    await ctx.click(page, "테스트 만들기")
    await ctx.fill(page, "시작 URL", ctx.fixture("/login.html"))
    # 방법을 고르면 지시문 자리가 열린다 — 화면을 갈아타지 않는다 (FR-259)
    await ctx.click(page, "AI로 만들기")
    await ctx.settle(page, ms=1_500)

    # 지시문이 비어 있으므로 잠겨 있어야 한다 (조건 C14)
    blocked = await ctx.is_disabled(page, "AI 시작")
    url_kept = ctx.fixture("/login.html") in await page.get_by_label(
        "시작 URL", exact=False
    ).first.input_value()

    return await ctx.from_screen(
        page,
        rejected=blocked,
        prevented=blocked,
        preserved=url_kept,
        # 왜 막히는지가 그 자리에 있어야 한다 (FR-234)
        surfaced=await ctx.disabled_reason(page, "AI 시작") or await ctx.status_note(page),
    )


@driver("AS-012")
async def _open_a_step_whose_target_has_no_usable_candidate(ctx: Any) -> Attempt:
    """쓸 수 있는 후보가 없는 Step 을 화면이 어떻게 보여 주는가.

    목록은 원래 "후보를 모두 지우고 저장한다"고 적었는데 **화면에 후보를 지우는 조작이
    없다** — 후보는 기록 시점에 수집되고 표시만 된다. 그래서 후보가 하나도 쓸 수 없는
    정의를 만들어 두고, 화면이 그것을 **말없이 정상처럼 보여 주는지**를 본다. 근거는
    목록의 `note` 에 남겼다.
    """
    ctx.ensure_project()
    name = "후보 없는 정의"
    test_id = ctx.make_test_with_unusable_target(name)
    page = await ctx.open()
    await ctx.settle(page)

    opened = await ctx.open_definition(page, name)
    assert opened, "정의 화면으로 들어가지 못했다 — 목록의 ⋮ 메뉴가 바뀌었는지 확인하세요"
    summary = await ctx.target_summary(page)

    # 정의는 그대로 남아 있어야 한다 (판정축 ③ — test-definition).
    status, body = ctx.api("GET", f"/api/tests/{test_id}")
    intact = status == 200 and bool(body.get("steps"))

    # 쓸 수 있는 후보가 없다는 사실을 화면이 말하는가. 말없이 정상처럼 보여 주면
    # 사용자는 그 Step 이 재실행에서 반드시 실패한다는 것을 실행해 봐야 안다.
    warned = any(w in summary for w in ("확인 필요", "쓸 수 없", "없음", "다시 집기"))
    return await ctx.from_screen(
        page,
        rejected=warned,
        prevented=warned,
        preserved=intact,
        surfaced=summary,
    )


# ─── 순서·상태 위반 (AS-024~AS-029) ─────────────────────────────────────────


@driver("AS-024")
async def _press_run_twice_quickly(ctx: Any) -> Attempt:
    """실행 버튼을 빠르게 두 번 누른다. 세션이 둘 생기면 안 된다 (AP-022)."""
    ctx.ensure_project()
    test_id = ctx.make_test("연타 대상")
    page = await ctx.open()

    before = ctx.session_count()
    row = page.get_by_role("button", name="실행", exact=False).first
    await row.wait_for(timeout=8_000)
    # 두 번을 **기다리지 않고** 보낸다. 사람이 연타하는 것과 같다.
    await asyncio.gather(
        row.click(timeout=8_000),
        row.click(timeout=8_000, force=True),
        return_exceptions=True,
    )
    # 세션은 실제 브라우저를 띄운다 — 1초로는 아직 만들어지지 않은 상태를 보게 된다.
    await ctx.settle(page, ms=6_000)

    made = ctx.session_count() - before
    del test_id
    return await ctx.from_screen(
        page,
        rejected=made <= 1,
        preserved=made <= 1 and ctx.sessions_healthy(),
        # 두 번째 누름이 요청을 내보내지 않았으면 화면이 미리 막은 것이다.
        prevented=made <= 1 and await ctx.notice(page) is None,
        surfaced=await ctx.status_summary(page),
    )


@driver("AS-025")
async def _send_an_edit_after_the_pause_was_lifted(ctx: Any) -> Attempt:
    """일시정지가 풀린 뒤에도 남아 있는 편집 조작을 보낸다 (AP-023)."""
    ctx.ensure_project()
    page = await ctx.open()
    session_id = await ctx.start_session_from_ui(page, ctx.fixture("/login.html"))

    ctx.api("POST", f"/api/sessions/{session_id}/pause")
    steps_before = ctx.step_count(session_id)
    # 화면이 일시정지 화면을 그린 뒤, 바깥에서 일시정지를 푼다. 화면은 아직 모른다.
    await ctx.settle(page)
    ctx.api("POST", f"/api/sessions/{session_id}/record-actions:start")

    sent = await ctx.click_if_present(page, "Step 추가")
    await ctx.wait_for_notice(page)

    return await ctx.from_screen(
        page,
        rejected=ctx.step_count(session_id) == steps_before,
        preserved=ctx.step_count(session_id) >= steps_before,
        # 화면이 그 조작을 이미 거두어 갔으면 요청은 나가지 않았다. 오류 본문이 없는
        # 것이 정상이며, 그때는 **무엇이 막는지가 보이는가**만 남는다.
        prevented=not sent,
        surfaced=(await ctx.status_summary(page))
        if sent
        else await ctx.disabled_reason(page, "Step 추가"),
    )


@driver("AS-026")
async def _leave_the_session_screen_and_come_back_after_it_ended(ctx: Any) -> Attempt:
    """세션 화면을 벗어났다가 세션이 끝난 뒤 돌아온다 (AP-023·AS-026).

    거부할 일이 아니다. **옛 상태로 멈춰 있지 않고 지금 상태를 보여 주어야** 한다.
    """
    ctx.ensure_project()
    page = await ctx.open()
    session_id = await ctx.start_session_from_ui(page, ctx.fixture("/login.html"))
    await ctx.settle(page)

    ctx.api("POST", f"/api/sessions/{session_id}/stop")
    # 화면을 떠났다 돌아온다 — 새로 고침이 "돌아오기"다.
    await page.reload(wait_until="domcontentloaded")
    await ctx.settle(page)

    text = await ctx.visible_text(page)
    # 기록이 아직 읽히는가. 그리고 화면이 **그 세션으로 돌아갈 길**을 주는가 —
    # 돌아갈 길이 없으면 기록은 서버에만 남고 사용자에게는 사라진 것과 같다.
    steps_kept = ctx.step_count(session_id) >= 0
    way_back = "이어서 보기" in text or "진행 중인 세션" in text
    # 끝난 세션인데 "녹화 중" 으로 보이면 옛 상태에 멈춘 것이다.
    stale = "녹화 중" in text
    return await ctx.from_screen(
        page,
        rejected=False,
        preserved=steps_kept and way_back and not stale,
        surfaced=await ctx.status_summary(page),
    )


@driver("AS-027")
async def _act_on_a_session_that_already_ended(ctx: Any) -> Attempt:
    """이미 종료된 세션에 조작을 보낸다 (AP-023).

    **누르지 못한 것을 `prevented` 로 기록한다** (005 T114).

    이 드라이버는 한동안 `click_if_present` 의 결과를 버리고 있었고, 그래도 통과했다 —
    화면에 오류 배너가 떠 있었기 때문이다. 그런데 그 배너의 출처는 이 조작이 아니라
    **종료된 세션에 대한 `GET …/tabs` 의 404** 였다. 사용자가 한 일(중지)의 정상적인
    결과를 오류로 말하던 그 배너이고, FR-135 가 없애라고 한 것이다(재점검 U-03-b,
    실측 404 3건). 즉 이 시나리오는 **결함에 기대어 통과**하고 있었다.

    배너가 사라지자 실제 처리가 드러났다 — 화면이 종료를 반영해 「일시정지」를 거두어
    간다. 그것은 거부보다 강한 처리이며(003 AP-020: 안 되는 것을 누르게 두지 않는다)
    `AS-028` 이 이미 같은 형태를 쓴다.

    단정을 약화하지 않는다: 조작이 **실제로 전달된 경우**에는 계약 형태의 오류 본문이
    있어야 하고(판정축 ①), 그것은 `prevented=False` 로 남아 그대로 요구된다.
    """
    ctx.ensure_project()
    page = await ctx.open()
    session_id = await ctx.start_session_from_ui(page, ctx.fixture("/login.html"))
    await ctx.settle(page)

    steps_before = ctx.step_count(session_id)
    ctx.api("POST", f"/api/sessions/{session_id}/stop")
    # 화면은 아직 살아 있다고 믿을 수 있다. 그 상태에서 조작을 보낸다.
    sent = await ctx.click_if_present(page, "일시정지")
    await ctx.wait_for_notice(page)

    return await ctx.from_screen(
        page,
        rejected=True,
        prevented=not sent,
        preserved=ctx.step_count(session_id) >= steps_before,
        surfaced=await ctx.status_summary(page),
    )


@driver("AS-028")
async def _open_the_result_of_a_test_that_was_deleted(ctx: Any) -> Attempt:
    """삭제한 테스트의 결과 보기를 그대로 누른다.

    목록은 새로 고치지 않는다 — **낡은 행이 화면에 남아 있는 상태**가 이 시나리오의
    전부다. 새로 고치면 행이 사라져 누를 것이 없어지고, 아무것도 재지 못한다.
    """
    ctx.ensure_project()
    test_id = ctx.make_test_with_bare_result("지워질 테스트")
    page = await ctx.open()
    await ctx.settle(page)

    # 화면이 목록을 그린 뒤 바깥에서 지운다.
    ctx.api("DELETE", f"/api/tests/{test_id}")
    opened = await ctx.open_result(page)
    await ctx.wait_for_notice(page)

    return await ctx.from_screen(
        page,
        rejected=True,
        prevented=not opened,
        surfaced=await ctx.status_summary(page),
    )


@driver("AS-029")
async def _replace_a_key_when_there_is_none(ctx: Any) -> Attempt:
    """키가 없는 상태에서 키 교체를 누른다."""
    ctx.ensure_project()
    ctx.drop_keys()
    page = await ctx.open()

    await ctx.click(page, "키 관리")
    await ctx.settle(page)

    offered = await ctx.has_button(page, "키 교체")
    secrets_readable = ctx.api("GET", "/api/secrets")[0] == 200
    return await ctx.from_screen(
        page,
        rejected=not offered,
        prevented=not offered,
        preserved=secrets_readable,
        surfaced=await ctx.key_status_summary(page),
    )


# ─── 외부 환경 실패 (AS-037~AS-039) ─────────────────────────────────────────


@driver("AS-037")
async def _look_at_the_screen_when_the_ai_cannot_run(ctx: Any) -> Attempt:
    """AI 를 쓸 수 없는 상태에서 화면을 본다 (AP-032·AP-033).

    목록은 "응답하지 않는 동안" 이라고 적었다. 화면 면은 제품을 **다른 프로세스로**
    띄우므로 언어모델 대역을 끼워 넣을 수 없고, 제품에 지연 스위치를 넣는 것은 헌법
    원칙 II 가 금지한다 (research R4 가 같은 이유로 그 대안을 기각했다). 그래서 밖에서
    실제로 만들어지는 상태 — 자격 증명이 없는 환경 — 를 쓴다. 재려는 것(AI 쪽 사정이
    화면에 드러나고 진행할 길이 남는가)은 같다. 근거는 목록의 `note` 에 남겼다.
    """
    ctx.ensure_project()
    page = await ctx.open()

    await ctx.click(page, "테스트 만들기")
    await ctx.fill(page, "시작 URL", ctx.fixture("/login.html"))
    await ctx.settle(page, ms=1_500)

    note = await ctx.status_note(page)
    # 막혔어도 다른 길이 남아 있어야 한다 — 녹화로는 만들 수 있다 (판정축 ②).
    recording_open = not await ctx.is_disabled(page, "녹화 시작")

    return await ctx.from_screen(
        page,
        rejected=False,
        preserved=recording_open,
        surfaced=note,
    )


@driver("AS-038")
async def _the_screen_receives_a_lost_browser_during_a_run(ctx: Any) -> Attempt:
    """실행 중 브라우저가 사라진 상태를 화면이 받는다 (AP-030)."""
    ctx.ensure_project()
    page = await ctx.open()
    session_id = await ctx.start_session_from_ui(page, ctx.fixture("/login.html"))
    await ctx.settle(page)

    steps_before = ctx.step_count(session_id)
    ctx.lose_browser(session_id)
    await ctx.settle(page, ms=3_000)

    text = await ctx.visible_text(page)
    told = any(w in text for w in ("유실", "브라우저", "보존"))
    return await ctx.from_screen(
        page,
        rejected=False,
        preserved=ctx.step_count(session_id) >= steps_before,
        surfaced=(await ctx.status_summary(page)) if told else "",
    )


@driver("AS-039")
async def _open_a_result_that_has_no_artifacts(ctx: Any) -> Attempt:
    """산출물이 없는 실행 결과를 연다. 빈 화면으로 두지 않는다."""
    ctx.ensure_project()
    test_id = ctx.make_test_with_bare_result("산출물 없는 결과")
    page = await ctx.open()
    await ctx.settle(page)

    opened = await ctx.open_result(page)
    assert opened, f"{test_id} 의 결과 보기 버튼을 찾지 못했다 — 목록이 실패로 그리지 않았다"
    await ctx.settle(page)

    return await ctx.from_screen(
        page, rejected=False, surfaced=await ctx.result_summary(page)
    )


# ─── 동시성 (AS-046~AS-048) ─────────────────────────────────────────────────


@driver("AS-046")
async def _delete_the_same_test_from_two_windows(ctx: Any) -> Attempt:
    """두 화면에서 같은 테스트를 동시에 삭제한다."""
    ctx.ensure_project()
    test_id = ctx.make_test("두 번 지울 테스트")
    first = await ctx.open()
    second = await ctx.open()

    await ctx.settle(first)
    await ctx.settle(second)

    assert await ctx.delete_from_list(first, "두 번 지울 테스트"), (
        "첫 창에서 삭제를 끝내지 못했다 — 확인 상자가 열린 채로 남으면 동시 삭제가 성립하지 않는다"
    )
    # 두 번째 창은 아직 있다고 믿는다. 같은 조작을 보낸다.
    sent = await ctx.delete_from_list(second, "두 번 지울 테스트")
    await ctx.wait_for_notice(second)

    listed = ctx.api("GET", "/api/tests")
    registry_ok = listed[0] == 200
    gone = registry_ok and test_id not in {t["id"] for t in listed[1]["tests"]}

    return await ctx.from_screen(
        second,
        rejected=gone,
        preserved=registry_ok,
        prevented=not sent,
        surfaced=(await ctx.status_summary(second))
        if sent
        else await ctx.status_summary(second),
    )


@driver("AS-047")
async def _send_a_command_to_a_session_another_client_already_moved(ctx: Any) -> Attempt:
    """다른 곳에서 이미 옮겨 놓은 세션에 화면이 조작을 보낸다 (AP-041).

    목록은 원래 "두 화면에서" 라고 적었다. **제품 화면에는 주소가 없어** 두 번째 창을
    같은 세션 화면으로 데려갈 방법이 없다 — 상태로 화면을 고르는 설계라 딥링크가
    없다. 그래서 두 번째 조작 주체를 다른 클라이언트로 두고, 화면 쪽이 **낡은 상태에서
    보낸 조작**을 어떻게 다루는지 본다. 재려는 것(반영되지 않은 조작이 조용히 무시되지
    않는가)은 같다. 근거는 목록의 `note` 에 남겼다.
    """
    ctx.ensure_project()
    page = await ctx.open()
    session_id = await ctx.start_session_from_ui(page, ctx.fixture("/login.html"))
    await ctx.settle(page)

    steps_before = ctx.step_count(session_id)
    # 다른 클라이언트가 먼저 멈춘다. 화면은 아직 녹화 중이라고 믿는다.
    ctx.api("POST", f"/api/sessions/{session_id}/pause")
    sent = await ctx.click_if_present(page, "일시정지")
    await ctx.wait_for_notice(page)

    return await ctx.from_screen(
        page,
        rejected=True,
        preserved=ctx.step_count(session_id) >= steps_before and ctx.sessions_healthy(),
        # 실시간 통로로 바뀐 상태를 받아 그 조작을 이미 거두어 갔으면 요청은 나가지
        # 않았다 — 조용히 무시된 것이 아니라 애초에 보내지 않은 것이다 (AP-041).
        prevented=not sent,
        surfaced=await ctx.status_summary(page),
    )


@driver("AS-048")
async def _leave_the_screen_before_the_save_finishes(ctx: Any) -> Attempt:
    """저장이 끝나기 전에 화면을 떠난다. 저장은 끝나야 한다."""
    ctx.ensure_project()
    ctx.ensure_keys()
    page = await ctx.open()

    await ctx.click(page, "비밀 값")
    await ctx.fill(page, "변수 이름", "LEAVING_EARLY")
    await ctx.fill(page, "값", "떠나기 전 값")
    await ctx.click(page, "봉인해 저장")
    # 응답을 기다리지 않고 곧바로 떠난다.
    await ctx.click_if_present(page, "닫기")
    await ctx.settle(page, ms=2_000)

    names = [n["name"] for n in (ctx.api("GET", "/api/secrets")[1] or {}).get("names", [])]
    return await ctx.from_screen(
        page,
        rejected=False,
        preserved="LEAVING_EARLY" in names,
        surfaced=await ctx.status_summary(page),
    )
