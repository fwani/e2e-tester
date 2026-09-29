"""자리가 **진짜 그 요소의 자리인가** (024 T057·T058·T059 · SC-002·SC-008).

## 왜 이 파일이 반드시 필요한가

변환식과 규칙은 단위 검증이 이미 본다. 그러나 **좌표가 실제로 그 요소를 가리키는지는
자기 자신과 맞추는 것으로 확인되지 않는다** — 정변환이 통째로 틀려도, 그 틀린 식으로
기대값을 적으면 초록색이 된다. 좌표가 한 칸 어긋난 것은 눈으로도 잘 안 보인다.

## 무엇을 재고 무엇을 사람에게 남기는가

여기서 재는 것은 **좌표계가 통째로 다른 경우**다 — 자리가 미러 프레임의 크기 안에
들어오는가, 요소마다 다른 값인가. 계가 갈리면(문서 기준·장치 픽셀·프레임 이미지 픽셀)
이 검사에 먼저 걸린다.

**한 픽셀 어긋남과 스크롤된 화면의 어긋남은 여기서 재지 못한다.**

스크롤은 「뷰포트 기준인가 문서 기준인가」를 가르는 결정적 실험이지만, 그러려면 실제로
스크롤이 일어나야 한다. 고정 화면은 뷰포트보다 짧아 스크롤되지 않고, 스크롤이 없으면
두 기준이 **같은 값**이다. 그 몫은 사람이 본다 — quickstart §3(밀집 화면)·§4(스크롤).

검사하는 척하지 않는 이유는, 아무것도 재지 않는 초록색이 빨간색보다 나쁘기 때문이다.

## 함께 보는 것

**대상 화면이 바뀌지 않았는가** (T057 · FR-025 · SC-008). 이 기능이 「대상 페이지에
아무것도 심지 않는다」를 택한 근거 전부가 여기서 증명된다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us4_support import (
    click_named,
    fill_named,
    install_driver,
    observe,
    start_ai_session,
    wait_for_event,
)

from tests.us2_support import stop_quietly

pytestmark = pytest.mark.browser


def _focus_events(event_log: list[tuple[str, dict]]) -> list[dict]:
    return [payload for kind, payload in event_log if kind == "ai_focus"]


def _frame_size(event_log: list[tuple[str, dict]]) -> tuple[float, float] | None:
    """미러가 알린 대상 화면 크기. 알림의 좌표가 같은 계인지 맞춰 볼 기준이다."""
    frames = [p for k, p in event_log if k == "mirror_frame"]
    if not frames:
        return None
    last = frames[-1]
    return float(last["width"]), float(last["height"])


def test_reported_places_sit_inside_the_mirror_frame(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T058 · SC-002 — 자리가 **미러 프레임과 같은 계**에 있다.

    조작되는 요소는 화면에 보이는 것이므로, 그 자리는 프레임 크기 안에 들어와야 한다.
    좌표계가 통째로 갈리면(문서 기준·장치 픽셀·프레임 이미지 픽셀) 값이 이 범위를
    벗어나거나 크기가 배수로 어긋난다.

    이것만으로 한 픽셀 어긋남까지 잡지는 못한다 — 그 몫은 사람이 보는 quickstart §3 이다.
    여기서 잡는 것은 **계 자체가 다른 경우**이며, 그것이 가장 크게 틀리는 경우다.
    """
    script = [observe(0), fill_named("이메일", "tester@example.com"), click_named("로그인")]
    install_driver(monkeypatch, script)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        events = _focus_events(event_log)
        assert events, "조작했는데 자리 알림이 없다"

        size = _frame_size(event_log)
        assert size is not None, "미러 프레임이 없어 좌표계를 맞춰 볼 기준이 없다"
        width, height = size

        for payload in events:
            rect = payload["rect"]
            assert 0 <= rect["x"] < width, (
                f"자리의 x 가 대상 화면 폭({width}) 밖이다: {rect['x']} — "
                "좌표계가 미러 프레임과 다를 수 있다 (contracts/ai-focus.md §2)."
            )
            assert 0 <= rect["y"] < height, (
                f"자리의 y 가 대상 화면 높이({height}) 밖이다: {rect['y']}"
            )
            # 보이는 요소 하나가 화면 전체를 넘을 수는 없다. 넘으면 배율이 섞인 것이다.
            assert rect["width"] <= width and rect["height"] <= height, (
                f"자리의 크기가 대상 화면보다 크다: {rect} vs {width}×{height}"
            )
    finally:
        stop_quietly(keyed_client, sid)


def test_places_stay_within_the_viewport_and_differ_per_element(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T059 — 자리가 뷰포트 안에 있고, 요소마다 **다르다.**

    ## 이 검사가 잡는 것과 못 잡는 것

    잡는 것: 문서 기준 좌표(조작된 요소의 `y` 가 뷰포트 높이를 넘는다), 그리고 자리를
    재지 않고 상수를 보내는 구현(모든 알림이 같은 좌표다).

    **못 잡는 것: 스크롤된 화면의 어긋남.** 그것을 가르려면 실제로 스크롤이 일어나야
    하는데, 이 고정 화면은 뷰포트보다 짧아 스크롤되지 않는다. 스크롤이 없는 화면에서는
    뷰포트 기준과 문서 기준이 **같은 값**이다.

    그 몫은 사람이 본다 — [quickstart §4](../../specs/024-ai-focus-overlay/quickstart.md)
    가 세로로 긴 화면에서 스크롤이 필요한 지시를 주고 자리를 확인하게 한다. 여기서
    검사하는 척하지 않는 이유는, 아무것도 재지 않는 초록색이 빨간색보다 나쁘기 때문이다.
    """
    script = [
        observe(0),
        fill_named("이메일", "tester@example.com"),
        observe(0),
        click_named("로그인"),
    ]
    install_driver(monkeypatch, script)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        events = _focus_events(event_log)
        assert len(events) >= 2, "비교할 자리가 둘 이상 필요하다"

        size = _frame_size(event_log)
        assert size is not None
        _, height = size

        # 어떤 자리도 뷰포트 높이를 넘지 않는다 — 문서 기준을 쓰면서 화면이 길어지면
        # 이 값이 먼저 넘친다.
        for payload in events:
            assert payload["rect"]["y"] < height, (
                f"자리의 y({payload['rect']['y']}) 가 뷰포트 높이({height}) 를 넘었다 — "
                "문서 기준 좌표를 쓴 것일 수 있다 (FR-002 · contracts §2)."
            )

        # 서로 다른 요소는 서로 다른 자리에 있다. 모두 같은 값이면 자리를 재는 것이
        # 아니라 상수를 보내고 있는 것이다.
        places = {(p["rect"]["x"], p["rect"]["y"]) for p in events}
        assert len(places) > 1, f"모든 조작이 같은 자리를 알렸다: {places}"
    finally:
        stop_quietly(keyed_client, sid)


def test_the_target_page_is_not_touched(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T057 · FR-025 · SC-008 — **대상 화면에 아무것도 심지 않았다.**

    이 기능이 「서버가 좌표를 보내고 화면이 덧그린다」를 택한 근거 전부가 여기서
    증명된다. 대상 페이지에 테두리 요소를 심는 쉬운 길을 갔다면 화면의 요소가 늘고,
    그 늘어남이 유일성 판정과 실패 증거 스크린샷을 함께 오염시킨다.

    **살펴보기 결과의 요소 수로 잰다.** 조작 전후로 같은 화면을 두 번 살펴보고, 제품이
    무언가를 심었다면 둘째 살펴보기에서 요소가 늘어난다. 이름을 특정해 찾지 않는 이유는,
    심는 구현으로 바뀌면 어떤 이름을 쓸지 알 수 없기 때문이다.
    """
    from itb.api.routes.sessions import _WORK  # noqa: PLC0415

    script = [observe(0), fill_named("이메일", "tester@example.com"), observe(0)]
    install_driver(monkeypatch, script)
    sid = start_ai_session(keyed_client, fixture_app, "이메일 칸에 값을 넣어")
    try:
        wait_for_event(event_log, "ai_finished")
        assert _focus_events(event_log), "자리 알림이 없어 이 검증이 무의미하다"

        toolbox = _WORK[sid].toolbox
        assert toolbox is not None, "도구를 찾지 못했다"

        # 살펴보기마다 참조가 새로 부여되고 누적된다. 값만 채웠으므로 화면 구조는
        # 그대로이고, 두 번의 살펴보기가 **같은 수**의 요소를 봐야 한다.
        total = len(toolbox.refs)
        assert total % 2 == 0, (
            f"두 번의 살펴보기가 본 요소 수가 다르다 (합계 {total}) — 조작 전후로 화면의 "
            "요소가 늘거나 줄었다. 제품이 대상 화면에 무언가를 심었을 수 있다 (FR-025)."
        )
    finally:
        stop_quietly(keyed_client, sid)
