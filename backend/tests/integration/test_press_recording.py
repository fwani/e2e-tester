"""023 US1 — 키 입력 녹화 (T021~T023).

## 왜 이 파일이 따로 있는가

`test_recording.py` 는 「입력은 키 단위가 아니라 확정된 값을 잡는다」를 전제로 쓰여 있다.
이 파일은 그 전제가 닿지 않는 자리를 본다 — **값이 아니라 키 자체가 동작인 경우**다.

## 이 파일에서 가장 중요한 검증

`test_korean_composition_enter_is_not_recorded` 다. **영문 검증은 이 결함을 절대 잡지
못한다** — 영문에서는 Enter 가 한 번뿐이라 조합 확정과 제출을 구별할 필요가 없고, 그래서
구별하지 않는 구현도 통과한다. 한글에서만 갈린다 (023 FR-055).

## IME 를 어떻게 흉내 내는가

Playwright 는 실제 IME 조합을 만들지 못한다. 대신 `KeyboardEvent` 를 직접 만들어 보낸다 —
`isComposing` 은 `KeyboardEventInit` 의 필드라 생성 시점에 정할 수 있다.

**이것이 충실한 흉내인 이유**: 제품의 녹화기도, 고정 대상의 태그 위젯도 같은 필드를 읽는다.
둘 다 브라우저가 진짜 IME 에서 넣어 주는 것과 같은 값을 보게 된다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.step_wait import read_steps, wait_for_steps

TAG_FIELD = "#tags"


def _session(client: TestClient, fixture_app: str) -> str:
    """녹화 세션을 연다. **로그인이 필요 없는 화면에서 시작한다.**

    `interactions.html` 을 쓰는 이유는 재실행까지 보기 위해서다 (헌법 품질 게이트 2).
    로그인 단계가 앞에 끼면 비밀번호가 민감 변수로 봉인되고, 재실행이 비밀키와 값을
    요구한다 — **검증하려는 것과 무관한 마찰**이다.
    """
    resp = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["session_id"])


def _stop(client: TestClient, session_id: str) -> None:
    client.post(f"/api/sessions/{session_id}/stop")


def _page(client: TestClient, session_id: str) -> Any:
    manager = client.app.state.itb.sessions
    return manager.require(session_id).tabs[0].page


def _css(step: dict[str, Any]) -> str:
    target = step.get("target") or {}
    return str((target.get("css") or {}).get("value", ""))


def _tag_fills(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """태그 칸의 입력 Step 만. **다른 칸의 입력이 섞이면 판정이 흐려진다.**"""
    return [s for s in steps if s["type"] == "fill" and _css(s).endswith(TAG_FIELD)]


def _presses(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [s for s in steps if s["type"] == "press"]


# ── IME 흉내 ────────────────────────────────────────────────────────────────

_DISPATCH_KEY = """
([sel, key, composing]) => {
  const el = document.querySelector(sel);
  el.focus();
  el.dispatchEvent(new KeyboardEvent('keydown', {
    key, bubbles: true, cancelable: true, isComposing: composing,
  }));
}
"""
"""키 하나를 보낸다. `isComposing` 이 이 흉내의 전부다.

실제 한글 IME 에서 브라우저가 넣어 주는 것과 같은 필드이며, 녹화기와 고정 대상이 둘 다
그것을 읽는다.
"""


async def _open_modal(page: Any) -> None:
    """화면이 준비되기를 기다린다. 태그 칸은 처음부터 보인다."""
    await page.wait_for_selector(TAG_FIELD)
    await asyncio.sleep(0.3)


async def _type_tag(page: Any, text: str) -> None:
    """태그 칸에 글자를 넣는다. 조합이 끝난 상태를 흉내 낸다."""
    await page.fill(TAG_FIELD, text)
    await asyncio.sleep(0.4)  # recorder.js 의 input 디바운스(150ms)를 넘긴다


async def _blur_away(page: Any) -> None:
    """다른 곳을 눌러 포커스를 옮긴다.

    **이 단계가 결함의 방아쇠다.** 태그 위젯이 칸을 비운 뒤, 포커스가 떠날 때 `blur` 가
    빈 값으로 발생하고 그것이 앞선 입력 Step 을 덮어쓴다 (023 research R11).
    """
    await page.click("#memo")
    await asyncio.sleep(0.5)


# ── 검증 ────────────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_english_tag_keeps_typed_value_and_records_key(
    project_client: TestClient, fixture_app: str
) -> None:
    """T021 — `E2E` + Enter 가 Step 둘로 남고, 입력 값이 보존된다 (FR-054·FR-056).

    **이것이 023 이전에 깨져 있던 것이다.** 그때는 입력 Step 하나만 남았고 그 값은 빈
    문자열이었다 — 친 글자도 누른 키도 정의에 없었다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await _open_modal(page)
            await _type_tag(page, "E2E")
            await page.press(TAG_FIELD, "Enter")
            await asyncio.sleep(0.4)
            await _blur_away(page)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(
            project_client, sid, lambda ss: len(_presses(ss)) >= 1, timeout_s=10.0
        )
        presses = _presses(steps)
        fills = _tag_fills(steps)

        assert len(presses) == 1, f"키 입력 Step 이 하나여야 한다: {presses}"
        assert presses[0]["key"] == "Enter"
        assert fills, "태그 칸 입력 Step 이 남아야 한다"
        assert fills[-1]["value"] == "E2E", (
            "친 글자가 보존돼야 한다 — 키 뒤의 빈 값 확정이 덮어쓰면 안 된다 (FR-056)"
        )
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_korean_composition_enter_is_not_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """T022 ★ — 조합을 끝내는 Enter 는 기록되지 않는다 (FR-055).

    한글로 태그를 넣으면 Enter 가 **두 번** 눌린다. 첫 번째는 조합 확정이고 두 번째가
    제출이다. 둘을 구별하지 못하면 재실행에서 Enter 가 한 번 더 눌려 빈 태그가 생기거나
    폼이 두 번 제출된다.

    **영문 검증으로는 이 결함이 드러나지 않는다.** 영문은 Enter 가 한 번뿐이라, 구별하지
    않는 구현도 위의 영문 검증을 통과한다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await _open_modal(page)
            await _type_tag(page, "테스트")
            # 1번째 Enter — 조합 확정. 사용자가 뜻한 것은 글자를 굳히는 것이다.
            await page.evaluate(_DISPATCH_KEY, [TAG_FIELD, "Enter", True])
            await asyncio.sleep(0.3)
            # 2번째 Enter — 제출. 이것만 동작이다.
            await page.evaluate(_DISPATCH_KEY, [TAG_FIELD, "Enter", False])
            await asyncio.sleep(0.4)
            await _blur_away(page)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(
            project_client, sid, lambda ss: len(_presses(ss)) >= 1, timeout_s=10.0
        )
        presses = _presses(steps)
        fills = _tag_fills(steps)

        assert len(presses) == 1, (
            f"조합 확정 Enter 가 기록됐다 — 키 입력 Step 이 {len(presses)}개다. "
            f"재실행에서 Enter 가 한 번 더 눌린다: {presses}"
        )
        assert fills, "태그 칸 입력 Step 이 남아야 한다"
        assert fills[-1]["value"] == "테스트"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_repeated_key_is_not_collapsed(
    project_client: TestClient, fixture_app: str
) -> None:
    """T023 — 같은 키를 연달아 누르면 누른 횟수만큼 남는다 (FR-057).

    입력은 접지만(FR-025) 키는 접지 않는다. **Enter 두 번은 Enter 한 번과 다른 동작이고,
    접으면 되돌릴 수 없다.**
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await _open_modal(page)
            await _type_tag(page, "하나")
            await page.press(TAG_FIELD, "Enter")
            await asyncio.sleep(0.3)
            await _type_tag(page, "둘")
            await page.press(TAG_FIELD, "Enter")
            await asyncio.sleep(0.4)
            await _blur_away(page)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(
            project_client, sid, lambda ss: len(_presses(ss)) >= 2, timeout_s=10.0
        )
        assert len(_presses(steps)) == 2, (
            f"키 입력 두 번이 각각 남아야 한다: {_presses(steps)}"
        )
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_space_also_confirms(project_client: TestClient, fixture_app: str) -> None:
    """T021 — Space 도 확정 키다 (FR-053). 사용자가 요구한 둘 중 하나다."""
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await _open_modal(page)
            await _type_tag(page, "스페이스")
            await page.press(TAG_FIELD, "Space")
            await asyncio.sleep(0.4)
            await _blur_away(page)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(
            project_client, sid, lambda ss: len(_presses(ss)) >= 1, timeout_s=10.0
        )
        presses = _presses(steps)
        assert len(presses) == 1, f"Space 가 기록돼야 한다: {presses}"
        assert presses[0]["key"] == "Space"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_out_of_scope_key_is_not_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """T023 — 목록에 없는 키는 Step 이 되지 않는다 (FR-052·FR-060).

    막을 수 있는 일이 아니다 — 사용자는 실제 화면을 조작하고 있다. 그래서 「거절」이
    아니라 「기록하지 않음」이며, **그 사실을 알린다.**
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await _open_modal(page)
            await _type_tag(page, "화살표")
            await page.press(TAG_FIELD, "ArrowUp")
            await asyncio.sleep(0.6)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = read_steps(project_client, sid)
        assert not _presses(steps), f"범위 밖 키가 기록됐다: {_presses(steps)}"
    finally:
        _stop(project_client, sid)


# ── 재실행 (T025) ───────────────────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_recorded_tag_flow_replays(project_client: TestClient, fixture_app: str) -> None:
    """녹화한 태그 흐름이 **재실행에서 같은 결과를 낸다** (헌법 품질 게이트 2).

    Step 이 만들어졌다는 것과 그 Step 으로 같은 결과를 재현할 수 있다는 것은 다른
    주장이다. 023 에서는 특히 그렇다 — 입력 Step 의 값이 보존되고 키 입력 Step 이 그것을
    확정해야 태그가 생기므로, **둘 중 하나만 맞아도 재실행은 틀린다.**

    한글로 한다. 영문으로 하면 IME 처리가 틀려도 통과한다.
    """
    from us2_support import replay, result_of, stop_quietly

    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await _open_modal(page)
            await _type_tag(page, "테스트")
            await page.evaluate(_DISPATCH_KEY, [TAG_FIELD, "Enter", True])
            await asyncio.sleep(0.3)
            await page.evaluate(_DISPATCH_KEY, [TAG_FIELD, "Enter", False])
            await asyncio.sleep(0.4)
            await _blur_away(page)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        wait_for_steps(project_client, sid, lambda ss: len(_presses(ss)) >= 1, timeout_s=10.0)

        saved = project_client.post(f"/api/sessions/{sid}/save", json={"name": "태그 추가"})
        assert saved.status_code == 200, saved.text
        test_id = str(saved.json()["id"])
    finally:
        stop_quietly(project_client, sid)

    view = replay(project_client, test_id)
    result = result_of(project_client, test_id)
    failed = [s for s in result["steps"] if s["outcome"] not in {"pass", "not_run", "skipped"}]
    assert result["outcome"] == "pass", (
        f"재실행 상태={view['state']} 결과={result['outcome']}. "
        f"실패한 Step: {[(s['label'], s.get('error_message')) for s in failed]}"
    )

    # **키 입력 Step 이 실제로 돌았다.** 통과만으로는 부족하다 — Step 이 아예 없어도
    # 「전부 통과」가 되기 때문이다.
    pressed = [s for s in result["steps"] if s["label"].endswith("키 입력")]
    assert pressed, f"키 입력 Step 결과가 없다: {[s['label'] for s in result['steps']]}"


def test_press_label_names_the_key() -> None:
    """T031 — 네 키의 표시 이름이 서로 다르다 (FR-059).

    「키 입력」만 있으면 목록에서 Enter 와 Escape 를 구별할 수 없고, 그 둘은 정반대
    동작이다.
    """
    from itb.domain.step import PressKey, press_label

    labels = {press_label(k) for k in PressKey}
    assert len(labels) == len(PressKey), f"표시 이름이 겹친다: {labels}"
    for k in PressKey:
        assert k.value in press_label(k)
