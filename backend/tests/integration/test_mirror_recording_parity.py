"""두 경로 동등성 (010 T033 · FR-322~FR-324 · SC-513 · 헌법 원칙 I·IV).

**이 파일이 이 기능을 켜 둘 수 있는 근거다.** 같은 화면에서 같은 조작을 미러 경로와 창
경로로 했을 때 만들어지는 Step 이 **완전히 같아야 한다** — 종류·값·요소 후보 집합·검증
상태 전부.

> tasks.md 의 「멈춰야 하는 조건」: 이 검증이 통과하지 않으면 US2 로 가지 않는다.
> 원칙 I 은 이 기능의 전제이며 나중에 고칠 수 있는 항목이 아니다.

## 왜 같아야 하는가, 그리고 왜 같은가

같아야 하는 이유는 헌법 원칙 I 이다 — 같은 조작이 경로에 따라 다른 Step 이 되면 Step
모델이 하나가 아니게 된다.

같은 이유는 구조다 (research R1). CDP `Input` 으로 만든 입력은 대상 페이지에서
`isTrusted: true` 이벤트가 되고, 리코더는 `isTrusted` 를 검사하지 않는다. 즉 리코더는
두 경로를 **구분할 수 없다.** 서버가 조작 사건을 Step 으로 변환하는 경로를 만들지 않은
것이 그 구조를 지킨다.

이 파일은 그 구조가 실제로 성립하는지를 **살아 있는 브라우저에서** 확인한다. 단위 검증은
가짜 CDP 로 「무엇을 보냈는가」까지만 볼 수 있고, 「대상 페이지가 그것을 사람의 조작과
같게 받았는가」는 볼 수 없다.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

CONTROL_PATH = "/api/sessions/{sid}/control"

SETTLE_S = 0.6
"""조작 뒤 Step 이 쌓이기를 기다리는 시간.

리코더는 입력 확정(`change`·`blur`)과 150ms 디바운스를 지나 Step 을 만든다. 그보다
넉넉히 두는 이유는 이 파일이 **타이밍을 재지 않기** 때문이다 — 재는 것은 두 경로가 같은
Step 을 내는가 하나다.
"""


def _start(client: TestClient, url: str) -> str:
    created = client.post("/api/sessions", json={"mode": "record", "start_url": url})
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])


def _page(client: TestClient, session_id: str) -> Any:
    return client.app.state.itb.sessions.require(session_id).tabs[0].page


def _steps(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    return list(client.get(f"/api/sessions/{session_id}").json()["steps"])


def _center(client: TestClient, session_id: str, selector: str) -> tuple[float, float]:
    """대상 화면 좌표계에서의 요소 중심.

    **프레임이 실어 오는 `width`·`height` 와 같은 좌표계다** (data-model §2). 프론트는
    표시 좌표를 여기로 되돌려 보내고, 이 검증은 그 되돌림이 끝난 지점부터 잰다 — 변환
    자체는 `frontend/tests/MirrorInput.test.ts` 가 순수 함수로 잰다.
    """
    page = _page(client, session_id)

    async def read(p: Any = page) -> dict[str, float]:
        box = await p.locator(selector).bounding_box()
        assert box is not None, f"{selector} 의 위치를 읽을 수 없다"
        return box

    box = client.portal.call(read)  # type: ignore[attr-defined]
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _click_through_mirror(client: TestClient, session_id: str, selector: str) -> None:
    """미러 경로로 클릭한다 — 조작 채널에 사건을 보낸다.

    사람이 미러 영역에서 하는 것과 같은 순서다: 올려놓기 → 누르기 → 놓기. 순서를 줄이면
    호버로 열리는 메뉴가 열리지 않고, 그것은 창 조작과 다른 결과를 만든다.
    """
    x, y = _center(client, session_id, selector)
    with client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
        for event in (
            {"kind": "pointer.move", "tab": 0, "x": x, "y": y},
            {"kind": "pointer.down", "tab": 0, "x": x, "y": y, "button": "left"},
            {"kind": "pointer.up", "tab": 0, "x": x, "y": y, "button": "left"},
        ):
            ws.send_text(json.dumps(event))
        _settle(client)


def _click_through_window(client: TestClient, session_id: str, selector: str) -> None:
    """창 경로로 클릭한다 — 사람이 실제 창에서 하는 것과 같다.

    `us2_support.click_like_a_person` 과 같은 순서를 쓴다 (올려놓기 → 기다림 → 누르기).
    """
    page = _page(client, session_id)

    async def act(p: Any = page) -> None:
        await p.hover(selector)
        await asyncio.sleep(0.15)
        await p.click(selector)

    client.portal.call(act)  # type: ignore[attr-defined]
    _settle(client)


def _settle(client: TestClient) -> None:
    async def wait() -> None:
        await asyncio.sleep(SETTLE_S)

    client.portal.call(wait)  # type: ignore[attr-defined]


def _comparable(step: dict[str, Any]) -> dict[str, Any]:
    """비교에 쓰는 Step 의 모습 (SC-513).

    **id·시각·순번은 뺀다.** 두 세션에서 만들어진 Step 이므로 그것들은 당연히 다르고,
    같기를 요구하면 검증이 성립하지 않는다.

    **뺀 것 말고는 전부 비교한다** — 종류·값·요소 후보 집합·검증 상태. 후보 집합을 빼면
    이 검증이 원칙 IV 의 증거가 되지 못한다.
    """
    ignored = {"id", "created_at", "recorded_at", "index", "order"}
    return {k: v for k, v in step.items() if k not in ignored}


@pytest.mark.browser
def test_mirror_and_window_clicks_produce_identical_steps(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**같은 클릭이 두 경로에서 같은 Step 이 된다** (FR-322~FR-324 · SC-513 · 원칙 I).

    이 검증이 깨지면 미러 조작을 켜 둘 수 없다. 기능이 아니라 결함이다.
    """
    url = f"{fixture_app}/interactions.html"
    selector = "[data-testid=tools-menu]"

    window_session = _start(keyed_client, url)
    try:
        _click_through_window(keyed_client, window_session, selector)
        window_steps = _steps(keyed_client, window_session)
    finally:
        stop_quietly(keyed_client, window_session)

    mirror_session = _start(keyed_client, url)
    try:
        _click_through_mirror(keyed_client, mirror_session, selector)
        mirror_steps = _steps(keyed_client, mirror_session)
    finally:
        stop_quietly(keyed_client, mirror_session)

    assert window_steps, "창 경로가 Step 을 만들지 못했다 — 비교할 기준이 없다"
    assert len(mirror_steps) == len(window_steps), (
        "두 경로가 다른 개수의 Step 을 만들었다 (FR-321). "
        f"창 {[s['type'] for s in window_steps]} / 미러 {[s['type'] for s in mirror_steps]}"
    )

    for mirror_step, window_step in zip(mirror_steps, window_steps, strict=True):
        assert _comparable(mirror_step) == _comparable(window_step), (
            "미러 조작과 창 조작이 다른 Step 을 만들었다 (SC-513 · 헌법 원칙 I).\n"
            f"미러: {_comparable(mirror_step)}\n"
            f"창  : {_comparable(window_step)}"
        )


@pytest.mark.browser
def test_locator_candidates_are_the_same_on_both_paths(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**요소 후보 집합과 검증 상태가 같다** (FR-322 · 헌법 원칙 IV).

    위 검증에 이미 포함되지만 따로 둔다. 이것이 깨졌을 때의 진단이 다르기 때문이다 —
    개수가 같은데 후보가 다르면 문제는 좌표가 아니라 **후보 수집 경로**에 있고, 그것은
    「좌표는 입력을 어디로 보낼지만 정하고 요소를 무엇으로 식별할지에는 관여하지
    않는다」(plan 원칙 IV)가 깨졌다는 뜻이다.
    """
    url = f"{fixture_app}/login.html"
    selector = "[data-testid=login-submit]"

    window_session = _start(keyed_client, url)
    try:
        _click_through_window(keyed_client, window_session, selector)
        window_steps = _steps(keyed_client, window_session)
    finally:
        stop_quietly(keyed_client, window_session)

    mirror_session = _start(keyed_client, url)
    try:
        _click_through_mirror(keyed_client, mirror_session, selector)
        mirror_steps = _steps(keyed_client, mirror_session)
    finally:
        stop_quietly(keyed_client, mirror_session)

    assert window_steps and mirror_steps

    def candidates(step: dict[str, Any]) -> Any:
        return step.get("target", {}).get("candidates")

    assert candidates(mirror_steps[0]) == candidates(window_steps[0]), (
        "두 경로의 요소 후보 집합이 다르다 (원칙 IV). "
        "좌표가 요소 식별에 관여하고 있다는 뜻이다."
    )
    assert mirror_steps[0].get("target", {}).get("verified") == window_steps[0].get(
        "target", {}
    ).get("verified"), "두 경로의 검증 상태가 다르다 (FR-322)"


@pytest.mark.browser
def test_mirror_double_click_collapses_like_the_window_path(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**미러 조작이라고 다르게 접히지 않는다** (FR-321 · US1 인수 2).

    같은 자리를 빠르게 두 번 눌러도 Step 은 하나다. 기존 중복 접기 규칙이 그대로
    적용되어야 한다 — 미러 경로가 그 규칙을 지나지 않는다면 리코더가 아닌 어딘가에서
    Step 이 만들어지고 있다는 뜻이고, 그것이 원칙 I 위반이다.
    """
    url = f"{fixture_app}/interactions.html"
    selector = "[data-testid=tools-menu]"
    session_id = _start(keyed_client, url)
    try:
        x, y = _center(keyed_client, session_id, selector)
        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            for _ in range(2):
                for event in (
                    {"kind": "pointer.down", "tab": 0, "x": x, "y": y, "button": "left"},
                    {"kind": "pointer.up", "tab": 0, "x": x, "y": y, "button": "left"},
                ):
                    ws.send_text(json.dumps(event))
            _settle(keyed_client)
        clicks = [s for s in _steps(keyed_client, session_id) if s["type"] == "click"]
    finally:
        stop_quietly(keyed_client, session_id)

    assert len(clicks) == 1, (
        f"미러에서 두 번 누른 것이 Step {len(clicks)}개가 됐다 — 중복 접기 규칙이 "
        "미러 경로에 적용되지 않았다 (FR-321)"
    )


@pytest.mark.browser
def test_mirror_wheel_scrolls_without_making_a_step(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """휠은 대상 페이지를 스크롤하되 **그것만으로는 Step 을 만들지 않는다** (US1 인수 4).

    스크롤은 조작의 준비이지 조작이 아니다. Step 이 되면 재실행이 사람의 눈 움직임까지
    재현하려 들고, 화면 크기가 다른 환경에서 그 Step 은 뜻을 잃는다.
    """
    url = f"{fixture_app}/interactions.html"
    session_id = _start(keyed_client, url)
    try:
        # 픽스처 화면은 한 뷰포트에 들어간다 — 스크롤할 것이 없으면 이 검증은 아무것도
        # 재지 못한다. 스크롤될 높이를 만들어 두고 시작한다.
        page = _page(keyed_client, session_id)

        async def make_tall(p: Any = page) -> None:
            await p.evaluate("document.body.style.minHeight = '4000px'")

        keyed_client.portal.call(make_tall)  # type: ignore[attr-defined]
        before = len(_steps(keyed_client, session_id))
        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            ws.send_text(
                json.dumps(
                    {"kind": "wheel", "tab": 0, "x": 100, "y": 100, "deltaX": 0, "deltaY": 400}
                )
            )
            _settle(keyed_client)

        async def read(p: Any = page) -> float:
            return float(await p.evaluate("window.scrollY"))

        scrolled = keyed_client.portal.call(read)  # type: ignore[attr-defined]
        after = len(_steps(keyed_client, session_id))
    finally:
        stop_quietly(keyed_client, session_id)

    assert scrolled > 0, "미러에서 굴린 휠이 대상 페이지를 스크롤하지 못했다"
    assert after == before, f"스크롤만으로 Step 이 {after - before}개 쌓였다"


# ─── US2: 한글 입력 (T049·T050 · FR-326~FR-328 · SC-515) ────────────────────


def _type_korean_through_mirror(
    client: TestClient, session_id: str, selector: str, text: str
) -> None:
    """미러 경로로 한글을 입력한다 — 조합 중 상태를 그대로 옮긴다 (FR-327).

    사용자의 기계에 있는 IME 가 만드는 것과 같은 순서다: 글자마다 조합 갱신, 마지막에
    확정 하나. 확정만 보내면 대상 화면이 실제 사용자와 다르게 반응한다 (research R2).
    """
    x, y = _center(client, session_id, selector)
    with client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
        for event in (
            {"kind": "pointer.down", "tab": 0, "x": x, "y": y, "button": "left"},
            {"kind": "pointer.up", "tab": 0, "x": x, "y": y, "button": "left"},
        ):
            ws.send_text(json.dumps(event))
        for i in range(1, len(text) + 1):
            partial = text[:i]
            ws.send_text(
                json.dumps(
                    {
                        "kind": "ime.compose",
                        "tab": 0,
                        "text": partial,
                        "compositionRange": [len(partial), len(partial)],
                    }
                )
            )
        ws.send_text(json.dumps({"kind": "ime.commit", "tab": 0, "text": text}))
        _settle(client)


def _value_of(client: TestClient, session_id: str, selector: str) -> str:
    page = _page(client, session_id)

    async def read(p: Any = page) -> str:
        return str(await p.input_value(selector))

    return client.portal.call(read)  # type: ignore[attr-defined]


@pytest.mark.browser
def test_korean_typed_through_the_mirror_reaches_the_target(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**미러에서 친 한글이 대상 입력 요소에 정확히 들어간다** (FR-325 · SC-515).

    자모를 그대로 보내면 「ㅈㅜㅁㅜㄴ」이 된다 — 대상 브라우저에는 IME 가 없기 때문이다
    (research R2 가 버린 대안). 조합 상태를 옮기는 것이 그 문제의 해법이고, 이 검증이
    그 해법이 실제로 동작하는지를 본다.
    """
    session_id = _start(keyed_client, f"{fixture_app}/login.html")
    try:
        _type_korean_through_mirror(keyed_client, session_id, "#email", "주문 내역")
        value = _value_of(keyed_client, session_id, "#email")
    finally:
        stop_quietly(keyed_client, session_id)

    assert value == "주문 내역", f"대상 입력 요소의 값이 다르다: {value!r}"


@pytest.mark.browser
def test_composing_values_never_become_steps(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**조합 중인 값이 Step 으로 새지 않는다** (FR-326·FR-327c · SC-515).

    조합 중 값이 대상 입력 요소에 들어가 있는 것과 그것이 Step 이 되는 것은 별개다.
    리코더의 `composing` 플래그가 조합 중 `input` 을 무시하는 것이 그 구분이고, 이
    검증은 그것이 **미러 경로에서도** 성립하는지를 본다.
    """
    session_id = _start(keyed_client, f"{fixture_app}/login.html")
    try:
        _type_korean_through_mirror(keyed_client, session_id, "#email", "주문 내역")
        fills = [s for s in _steps(keyed_client, session_id) if s["type"] == "fill"]
    finally:
        stop_quietly(keyed_client, session_id)

    leaked = [s for s in fills if s.get("value") not in ("주문 내역", None)]
    assert not leaked, (
        "조합 중인 값이 Step 으로 새어 나왔다 (FR-326). "
        f"새어 나온 값: {[s.get('value') for s in leaked]}"
    )


@pytest.mark.browser
def test_input_survives_without_a_confirming_click(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**확정 계기가 없어도 입력이 Step 으로 남는다** (FR-328 · T048).

    입력만 하고 다른 곳을 누르지 않은 채 녹화를 멈추는 경우다. 확정 계기(`change`·`blur`)
    가 없으므로 150ms 디바운스 경로가 Step 을 만들어야 한다.

    **미러 경로에는 그 경로가 원래 없었다** (T048 실측). CDP `Input.insertText` 로 조합을
    확정하면 그 뒤에 `input` 이 발생하지 않고, 조합 중의 `input` 은 `composing` 때문에
    전부 건너뛰었으므로 걸린 디바운스도 없었다. 리코더가 `compositionend` 에서 디바운스를
    걸도록 고친 것이 T048 이고, 이 검증이 그 수정을 고정한다.
    """
    session_id = _start(keyed_client, f"{fixture_app}/login.html")
    try:
        _type_korean_through_mirror(keyed_client, session_id, "#email", "주문 내역")
        # **아무 곳도 클릭하지 않는다.** 확정 계기를 만들지 않는 것이 이 검증의 조건이다.
        fills = [s for s in _steps(keyed_client, session_id) if s["type"] == "fill"]
    finally:
        stop_quietly(keyed_client, session_id)

    assert fills, "확정 계기가 없다는 이유로 입력이 통째로 사라졌다 (FR-328)"
    assert fills[-1].get("value") == "주문 내역", (
        f"남은 입력 Step 의 값이 다르다: {fills[-1].get('value')!r}"
    )


@pytest.mark.browser
def test_long_korean_input_keeps_order_and_loses_nothing(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**연속 타이핑에서 키가 유실되거나 순서가 바뀌지 않는다** (SC-515b · FR-327b).

    중간 상태의 유실이 최종 값의 오류로 남아서는 안 된다. 확정을 전체 문자열 하나로
    보내는 설계가 그것을 보장한다 — 중간 상태는 화면 반응을 위한 것이고 값의 근거가
    아니다.
    """
    text = "주문 내역 조회"  # 8자 — research R2 의 측정 문자열
    session_id = _start(keyed_client, f"{fixture_app}/login.html")
    try:
        _type_korean_through_mirror(keyed_client, session_id, "#email", text)
        value = _value_of(keyed_client, session_id, "#email")
    finally:
        stop_quietly(keyed_client, session_id)

    assert value == text, f"연속 입력의 최종 값이 어긋났다: {value!r}"


@pytest.mark.browser
def test_sensitive_input_through_the_mirror_is_stored_as_a_variable(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**미러 경로의 비밀번호도 변수 참조로 저장된다** (FR-329 · T047 · 헌법 보안 요건).

    치환은 미러가 하지 않는다 — 리코더가 Step 을 만들기 때문에 기존 파이프라인(수집 →
    검증 → 치환 → Step → 이벤트)이 그대로 적용된다. 이 검증은 그 전제가 실제로 성립하는지,
    즉 **평문이 Step 에 남지 않는지**를 본다.
    """
    secret = "mirror-path-not-a-real-secret"
    session_id = _start(keyed_client, f"{fixture_app}/login.html")
    try:
        x, y = _center(keyed_client, session_id, "#password")
        with keyed_client.websocket_connect(CONTROL_PATH.format(sid=session_id)) as ws:
            for event in (
                {"kind": "pointer.down", "tab": 0, "x": x, "y": y, "button": "left"},
                {"kind": "pointer.up", "tab": 0, "x": x, "y": y, "button": "left"},
                {"kind": "text.insert", "tab": 0, "text": secret},
            ):
                ws.send_text(json.dumps(event))
            _settle(keyed_client)
        raw = keyed_client.get(f"/api/sessions/{session_id}").text
        fills = [s for s in _steps(keyed_client, session_id) if s["type"] == "fill"]
    finally:
        stop_quietly(keyed_client, session_id)

    assert secret not in raw, "비밀번호 평문이 세션 응답에 그대로 있다 (FR-329)"
    assert fills, "비밀번호 입력이 Step 으로 남지 않았다"

    # **민감함은 별도 표식이 아니라 값의 모습으로 나타난다.** 저장된 Step 의 값이 변수
    # 참조(`{{...}}`)이고 평문이 아니라는 것이 FR-329 가 요구하는 상태다 — 치환이
    # 이벤트 발행보다 먼저 일어났다는 증거이기도 하다.
    values = [str(s.get("value", "")) for s in fills]
    assert any(v.startswith("{{") and v.endswith("}}") for v in values), (
        f"비밀번호가 변수 참조로 저장되지 않았다: {values}"
    )
    assert secret not in str(fills), "민감 Step 안에 평문이 남았다"
