"""`ai_focus` — AI 가 만진 요소의 자리 (024 T024·T025·T025a·T025b·T041).

계약은 `specs/024-ai-focus-overlay/contracts/ai-focus.md` 다.

## 이 파일이 지키는 성질 하나

**자리를 모르면 이벤트가 나가지 않는다.** 「자리 없음」을 나타내는 값이 없다는 것이
이 계약의 핵심이고, 그것이 깨지면 화면은 「지난 표시를 지울 것인가」를 매 건마다 판단하게
된다 — 그 판단은 표시의 수명이 이미 하고 있다.

자리를 모르는 경우는 셋이다. 요소를 못 찾은 실패, 가리키는 자리가 하나로 좁혀지지 않아
거절된 조작, 그리고 **화면을 살펴보는 중**이다. 마지막 것은 지금 우연히 충족된다 —
`observe_page` 가 `_act_on_element` 를 지나지 않기 때문이다. 우연은 깨지고, 깨진 것을
아무도 모른다. 그래서 여기서 못 박는다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us4_support import (
    assert_url_contains,
    click_missing,
    click_named,
    fill_named,
    fill_password,
    install_driver,
    observe,
    start_ai_session,
    wait_for_event,
)

from tests.us2_support import stop_quietly

pytestmark = pytest.mark.browser

LOGIN_SCRIPT = [
    observe(0),
    fill_named("이메일", "tester@example.com"),
    fill_password("ai-authored-not-a-real-secret"),
    observe(0),
    click_named("로그인"),
    observe(0),
    assert_url_contains("projects.html"),
]


def _focus_events(event_log: list[tuple[str, dict]]) -> list[dict]:
    return [payload for kind, payload in event_log if kind == "ai_focus"]


def test_focus_events_carry_the_contracted_shape(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T024 — 네 필드가 모두 실린다 (contracts §1).

    **`tab` 이 빠지면 화면이 어느 그림 위에 그릴지 판정할 수 없다** (FR-004). 좌표만
    맞아도 다른 탭의 화면 위에 그려지면 엉뚱한 요소를 가리킨다.
    """
    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        events = _focus_events(event_log)
        assert events, "요소를 조작했는데 ai_focus 가 한 건도 없다"

        for payload in events:
            assert isinstance(payload["tab"], int), "어느 탭인지가 없다 (FR-004)"
            assert payload["status"] in {"done", "failed"}, (
                "「수행 중」은 없다 — 자리는 요소가 확정된 뒤에야 알 수 있다 (research R2)"
            )
            assert isinstance(payload["label"], str) and payload["label"], (
                "이름표가 없으면 화면이 진행 문구와 짝지어 읽을 수 없다 (FR-009)"
            )
            rect = payload["rect"]
            assert set(rect) == {"x", "y", "width", "height"}
            assert all(isinstance(v, (int, float)) for v in rect.values())
            # 크기가 0 이면 그릴 자리가 없다 — 그런 것은 애초에 나가지 않아야 한다.
            assert rect["width"] > 0 and rect["height"] > 0


        assert any(p["status"] == "done" for p in events), "성공한 조작의 자리가 없다"
    finally:
        stop_quietly(keyed_client, sid)


def test_label_matches_the_step_label(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-009 — 이름표는 Step 의 것과 **같은 값**이다.

    다르면 화면이 문구와 테두리를 짝지을 수 없고, 사용자는 「저 문구가 저 테두리를
    말하는가」를 다시 추측하게 된다 — 이 기능이 없애려던 바로 그 추측이다.
    """
    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        labels = {s["label"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]}
        for payload in _focus_events(event_log):
            if payload["status"] != "done":
                continue
            assert payload["label"] in labels, (
                f"자리 알림의 이름표 {payload['label']!r} 가 Step 목록에 없다"
            )
    finally:
        stop_quietly(keyed_client, sid)


def test_no_event_when_the_element_was_never_found(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T025·T041 — 요소를 못 찾은 실패에는 **자리가 없다** (FR-010).

    실패했다는 사실은 진행 문구와 막힘 안내가 나른다. 자리를 모르면서 하나를 골라
    그리면 그것이 곧 거짓말이다.
    """
    script = [*LOGIN_SCRIPT[:2], click_missing(), *LOGIN_SCRIPT[2:]]
    install_driver(monkeypatch, script)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        # 없는 요소를 클릭한 실패가 자리를 만들어 내지 않았다 — 실패 알림이 있더라도
        # 그것은 「요소는 찾았는데 동작이 안 된」 경우여야 한다.
        for payload in _focus_events(event_log):
            assert payload["rect"]["width"] > 0, "자리 없는 실패가 알림을 냈다"
    finally:
        stop_quietly(keyed_client, sid)


def test_observing_the_page_announces_no_place(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T025a — **화면을 살펴보는 동안에는 자리를 알리지 않는다** (FR-011).

    그때 대상은 하나가 아니다. 여럿을 그리면 「무엇이 조작되는가」가 아니라 「화면에
    무엇이 있는가」를 말하게 되고, 화면은 테두리로 덮여 읽기 어려워진다.

    지금 이것이 충족되는 이유는 `observe_page` 가 `_act_on_element` 를 지나지 않기
    때문이다 — **우연이다.** 우연은 깨지고, 깨진 것을 아무도 모른다.
    """
    # 살펴보기만 하고 아무것도 조작하지 않는 대본.
    install_driver(monkeypatch, [observe(0), observe(0)])
    sid = start_ai_session(keyed_client, fixture_app, "화면을 살펴봐")
    try:
        wait_for_event(event_log, "ai_finished")
        assert _focus_events(event_log) == [], (
            "살펴보기만 했는데 자리 알림이 나갔다 (FR-011)"
        )
        # 진행 문구는 그대로 나간다 — 이 기능이 문구를 대체하지 않는다 (FR-023).
        assert [p for k, p in event_log if k == "ai_progress"], "진행 문구까지 사라졌다"
    finally:
        stop_quietly(keyed_client, sid)


def test_a_blocked_action_reports_the_place_it_was_blocked_at(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T063 · US2/AC1 · SC-003 · FR-008 — **요소는 찾았는데 동작이 실패한 자리.**

    ## 왜 이것이 US2 의 본체인가

    실패에는 두 종류가 있고 자리의 유무가 갈린다.

    | 실패 | 자리 | 표시 |
    |---|---|---|
    | 요소를 **못 찾았다** | 없다 | 하지 않는다 (FR-010) |
    | 요소는 찾았는데 **동작이 안 됐다** | **있다** | **실패로 표시한다** |

    아랫줄이 US2 가 겨냥하는 경우다 — 사용자가 이어받아야 하는 순간이 바로 그때이고,
    필요한 것은 「어디서 막혔는지」다. 이 검증이 없으면 `StepFailure.rect` 배선이 끊겨도
    아무도 모른다. 윗줄만 재는 검증은 **자리가 없는 쪽만** 확인하므로 그 배선을 지나지
    않는다.

    비활성 버튼을 고른 이유는 그것이 **요소를 찾는 데는 성공하는** 실패이기 때문이다 —
    화면에 보이고 문서에도 있으며, 막히는 것은 클릭뿐이다.
    """
    install_driver(monkeypatch, [observe(0), click_named("삭제")])
    sid = start_ai_session(
        keyed_client,
        fixture_app,
        "삭제 버튼을 누른다",
        page="locked-controls.html",
    )
    try:
        wait_for_event(event_log, "ai_finished")
        failed = [p for p in _focus_events(event_log) if p["status"] == "failed"]
        assert failed, (
            "요소는 찾았는데 동작이 실패했는데 자리 알림이 없다 — US2 의 본체가 "
            "동작하지 않는다 (StepFailure.rect 배선을 보라)."
        )
        for payload in failed:
            rect = payload["rect"]
            assert rect["width"] > 0 and rect["height"] > 0, (
                f"실패 알림에 그릴 자리가 없다: {rect}"
            )
            assert isinstance(payload["tab"], int)
            assert payload["label"], "무엇을 하다 막혔는지가 없다 (FR-009)"
    finally:
        stop_quietly(keyed_client, sid)


def test_the_display_does_not_change_what_gets_authored(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T059a · FR-024 · SC-007 — **표시가 있든 없든 같은 Step 이 만들어진다.**

    이 기능은 화면에 무언가를 더할 뿐, 작성의 결과를 건드리지 않아야 한다. 건드린다면
    그것은 관찰 도구가 관찰 대상을 바꾼 것과 같은 종류의 문제다.

    통로를 떼고 한 번, 붙이고 한 번 돌려 Step 목록을 비교한다. **`id` 는 뺀다** — 그것은
    실행마다 새로 부여되는 값이고, 이 검증이 묻는 것은 「무엇을 어떤 순서로 만들었나」다.
    """

    def run_and_collect(*, with_focus: bool) -> list[tuple[str, str]]:
        event_log.clear()
        if not with_focus:
            # 통로를 떼면 알림이 한 건도 나가지 않는다 — 024 이전과 같은 상태다.
            from itb.authoring import tools as tools_module  # noqa: PLC0415

            async def silent(self: object, *args: object, **kwargs: object) -> None:
                return None

            monkeypatch.setattr(tools_module.BrowserToolbox, "_focus", silent)

        install_driver(monkeypatch, LOGIN_SCRIPT)
        sid = start_ai_session(keyed_client, fixture_app, "로그인해")
        try:
            wait_for_event(event_log, "ai_finished")
            steps = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
            return [(s["type"], s["label"]) for s in steps]
        finally:
            stop_quietly(keyed_client, sid)

    with_display = run_and_collect(with_focus=True)
    without_display = run_and_collect(with_focus=False)

    assert with_display, "Step 이 하나도 만들어지지 않아 비교가 무의미하다"
    assert with_display == without_display, (
        "표시 유무에 따라 만들어진 Step 이 다르다 — FR-024·SC-007 위반.\n"
        f"표시 있음: {with_display}\n표시 없음: {without_display}"
    )


def test_a_broken_focus_sink_does_not_stop_authoring(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T025b — **알림 통로가 터져도 작성은 끝까지 간다** (FR-006 · SC-009).

    표시는 곁가지다. 그것 때문에 테스트 작성이 끊기면, 이 기능은 도움이 아니라 새 고장
    지점이 된다.

    `_measure` 가 흡수하는 것은 **측정** 실패이고, 여기서 재는 것은 **알림** 실패다 —
    다른 자리이며 둘 다 막혀 있어야 한다.
    """
    from itb.authoring import tools as tools_module

    async def exploding_sink(_notice: object) -> None:
        msg = "자리 알림 통로가 터졌다"
        raise RuntimeError(msg)

    original = tools_module.BrowserToolbox._focus  # noqa: SLF001

    async def patched(self: object, *args: object, **kwargs: object) -> None:
        # 통로를 실제로 터뜨린다 — `_focus` 가 예외를 삼키는지가 요점이다.
        object.__setattr__(self, "on_focus", exploding_sink)
        await original(self, *args, **kwargs)

    monkeypatch.setattr(tools_module.BrowserToolbox, "_focus", patched)

    install_driver(monkeypatch, LOGIN_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        steps = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert steps, "알림 통로가 터지자 Step 이 하나도 만들어지지 않았다 (FR-006 위반)"
    finally:
        stop_quietly(keyed_client, sid)
