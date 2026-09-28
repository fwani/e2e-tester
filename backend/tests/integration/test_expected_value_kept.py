"""기대값이 지시문의 것으로 남는다 (020 T013 · US1 · FR-001~FR-010).

## 이 파일이 재는 것

`fixtures/sample-app/defective-save.html` 은 **일부러 틀리게 동작한다** — 저장하면
`저장되었습니다` 가 아니라 `처리 완료` 가 뜬다. 지시문이 앞쪽을 요구했을 때:

1. 그 값이 그대로 검증 Step 에 남는가 (AS-1)
2. 어긋난 뒤에도 작성이 계속되는가 (AS-2)
3. 어긋남이 쌓여도 막힘으로 끝나지 않는가 (AS-3)

## 무엇을 재지 **못하는가** — 정직하게

이 검증은 드라이버를 대본으로 갈아 끼운다. 갈아 끼우는 것은 「다음에 무엇을 할지 정하는
판단」이고, **기대값을 지킬지 말지가 바로 그 판단이다.** 그러므로 여기서 확인되는 것은
「모델이 기대값을 넘기면 제품이 그것을 보존한다」이지 「모델이 기대값을 지킨다」가 아니다.

후자는 제품이 보장할 수 없다. 제품이 할 수 있는 것은 **지키는 쪽이 손해 보지 않게 하는
것**뿐이고, 그것이 이 파일과 `test_attempt_limits_mismatch.py` 가 함께 재는 것이다 —
기대값을 고수해도 세션이 막히지 않고, Step 이 버려지지 않는다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly
from us4_support import (
    assert_text,
    click_named,
    fill_named,
    install_driver,
    observe,
    start_ai_session,
    wait_for_event,
)

PAGE = "defective-save.html"
EXPECTED = "저장되었습니다"
OBSERVED = "처리 완료"

MISMATCH_TIMEOUT_MS = 700
"""일부러 어긋나는 검증의 제한 시간 (021 T019).

021 부터 값 비교 검증이 제한 시간까지 기다리므로, 기본값(10초)으로 두면 **이 파일이
재려는 것과 무관한 시간**이 검증마다 10초씩 붙는다. 이 파일이 보는 것은 「어긋나도 Step
이 남는가」이지 「얼마나 기다리는가」가 아니다.

제품의 대기 동작을 되돌린 것이 아니다 — 그 동작은
`tests/integration/test_negative_assertion.py` 가 따로 본다.
"""

SAVE_SCRIPT = [
    observe(0),
    fill_named("이름", "가나다"),
    observe(0),
    click_named("저장"),
    observe(0),
    assert_text(EXPECTED, match="contains", timeout_ms=MISMATCH_TIMEOUT_MS),
]
"""지시문이 요구한 대로 한다 — **화면이 무엇을 띄우든 기대값은 지시문의 것이다.**

`contains` 를 쓰는 이유는 **옳은 이유로 실패시키기 위해서**다. 화면 전체 텍스트를
`equals` 로 비교하면 어떤 값을 넣어도 실패하고, 그러면 이 검증은 020 이 고친 것을
재는 것이 아니라 비교 방식의 성질을 재게 된다.
"""


def _steps(client: TestClient, sid: str) -> list[dict]:
    return client.get(f"/api/sessions/{sid}").json()["steps"]


def test_the_instructed_value_survives_a_defective_screen(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**이것이 020 의 전부다** (AS-1).

    020 이전에는 이 검증이 Step 으로 남지 않았고, 모델에게는 통과하는 값을 찾는 것
    외에 선택지가 없었다. 그래서 `처리 완료` 가 정답이 됐다.
    """
    install_driver(monkeypatch, SAVE_SCRIPT)
    sid = start_ai_session(
        keyed_client,
        fixture_app,
        f"이름에 가나다를 넣고 저장한다. '{EXPECTED}' 문구가 뜨는지 확인한다.",
        page=PAGE,
    )
    try:
        wait_for_event(event_log, "ai_finished")
        checks = [s for s in _steps(keyed_client, sid) if s["type"] == "assertion"]

        assert len(checks) == 1, f"검증 Step 이 기록되지 않았다: {checks}"
        assert checks[0]["assertion"]["value"] == EXPECTED, (
            "기대값이 화면에서 읽은 값으로 바뀌었다 — 버그가 정답이 됐다"
        )
        assert checks[0]["mismatch"] is not None, "어긋남이 기록되지 않았다"
        assert OBSERVED in checks[0]["mismatch"]["observed"]
    finally:
        stop_quietly(keyed_client, sid)


def test_authoring_continues_after_a_mismatch(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """어긋난 검증이 뒤따르는 동작을 막지 않는다 (AS-2).

    막으면 사용자는 「결함이 있는 화면은 작성 자체가 안 된다」를 겪는다 — 정작 테스트가
    가장 필요한 화면에서.
    """
    script = [*SAVE_SCRIPT, observe(0), click_named("빠른 저장")]
    install_driver(monkeypatch, script)
    sid = start_ai_session(
        keyed_client,
        fixture_app,
        f"저장하고 '{EXPECTED}' 를 확인한 뒤 빠른 저장도 눌러 본다.",
        page=PAGE,
    )
    try:
        wait_for_event(event_log, "ai_finished")
        labels = [s["label"] for s in _steps(keyed_client, sid)]
        assert any("빠른 저장" in label for label in labels), (
            f"어긋남 뒤의 동작이 수행되지 않았다: {labels}"
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_repeated_mismatches_do_not_block_the_session(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 검증이 여러 번 어긋나도 막힘으로 끝나지 않는다 (AS-3 · FR-009).

    **이것이 「틀린 답이 보상받지 않는다」의 통합 확인이다.** 연속 실패 상한이 어긋남을
    세면, 기대값을 고수하는 모델이 세션을 잃는다.
    """
    script = [
        *SAVE_SCRIPT,
        assert_text(EXPECTED, match="contains", timeout_ms=MISMATCH_TIMEOUT_MS),
        assert_text(EXPECTED, match="contains", timeout_ms=MISMATCH_TIMEOUT_MS),
    ]
    install_driver(monkeypatch, script)
    sid = start_ai_session(
        keyed_client, fixture_app, f"'{EXPECTED}' 를 세 번 확인한다.", page=PAGE
    )
    try:
        wait_for_event(event_log, "ai_finished")
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] != "ai_blocked", "어긋남이 세션을 막았다"

        checks = [s for s in view["steps"] if s["type"] == "assertion"]
        assert len(checks) == 3, f"어긋난 검증이 버려졌다: {len(checks)}건"
        assert all(c["mismatch"] is not None for c in checks)
    finally:
        stop_quietly(keyed_client, sid)


def test_finished_event_carries_the_mismatch_count(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """작성 직후에 몇 건인지 알린다 (FR-013).

    작성 직후가 사람이 맥락을 가장 많이 들고 있는 시점이다.
    """
    install_driver(monkeypatch, SAVE_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "저장 문구 확인", page=PAGE)
    try:
        payload = wait_for_event(event_log, "ai_finished")
        assert payload.get("mismatch_count") == 1, payload
    finally:
        stop_quietly(keyed_client, sid)


def test_no_mismatch_means_no_count_in_the_event(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**0건이면 필드 자체가 없다** (FR-013).

    없는 것을 0으로 알리면 화면이 「결함 후보 0건」을 표시할지 다시 판단해야 하고,
    정상 완료가 경고처럼 보인다.
    """
    # 화면이 실제로 띄우는 값을 확인한다 — **어긋나지 않는 경로**다.
    install_driver(
        monkeypatch,
        [
            observe(0),
            click_named("저장"),
            observe(0),
            assert_text(OBSERVED, match="contains", timeout_ms=MISMATCH_TIMEOUT_MS),
        ],
    )
    sid = start_ai_session(
        keyed_client, fixture_app, f"저장하면 '{OBSERVED}' 가 뜨는지 확인", page=PAGE
    )
    try:
        payload = wait_for_event(event_log, "ai_finished")
        assert "mismatch_count" not in payload, payload
    finally:
        stop_quietly(keyed_client, sid)
