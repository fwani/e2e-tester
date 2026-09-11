"""같은 `id` 를 쓰는 요소가 둘일 때 **고른 것이 조작된다** (2026-09-11 실측).

## 무엇을 봤나

대상 앱의 사용자 관리 화면에서 AI 에게 「이름 검색란에 user 를 넣고 검색해」를 시켰다.
AI 는 목록의 이름 검색 칸을 정확히 지목했고 도구도 성공을 돌려줬는데, **값은 헤더의
전역 검색 칸에 들어갔다.** 목록은 그대로였고 AI 는 「검색이 동작하지 않는다」로 판단해
막혔다. 사용자에게는 「AI 로 스텝 녹화가 안 된다」로 보였다.

## 왜 그랬나

`cssPath` 가 id 를 만나면 「id 는 문서에서 유일해야 하므로 더 올라갈 이유가 없다」며
멈췄다. 그것은 규격이 지켜진다는 **가정**이고, 그 화면은 지키지 않았다 — 두 칸이
`input#text-input-example-11` 이라는 같은 경로를 받았다.

경로가 같으면 그 뒤가 전부 조용히 어긋난다. `observe_page` 는 둘에 같은 경로를 주고,
도구는 그 경로로 요소를 **다시 찾는다**(`collect_by_selector` → `querySelector`) —
문서 순서상 첫 번째가 잡힌다.

## `test_twin_search.py` 와 무엇이 다른가

그쪽은 「이름이 같아 **고를 수 없다**」이고 여기는 「고를 수는 있는데 **고른 것이
실행되지 않는다**」다. 다른 고장이며 고치는 자리도 다르다 (관찰 정보 ↔ 경로 생성).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly
from us4_support import (
    Action,
    install_driver,
    observe,
    start_ai_session,
    wait_for_event,
)

SHARED_ID = "text-input-example-11"
"""두 칸이 **공유**하는 id. 실측한 화면의 값을 그대로 쓴다."""

LIST_PLACEHOLDER = "이름 또는 아이디 이메일을 검색하세요."
GLOBAL_PLACEHOLDER = "새로운 질문을 입력하세요."


def capture(sink: list[dict[str, Any]]) -> Action:
    """마지막 관찰 결과를 검사 쪽으로 가져온다. 도구는 부르지 않는다."""

    def action(state: dict[str, Any]) -> None:
        sink.append(state)
        return None

    return action


def fill_by_placeholder(placeholder: str, value: str) -> Action:
    """**placeholder 로 골라서** 입력한다 — 지시문이 가리키는 그 칸이다.

    id 는 둘이 같으므로 구별에 쓸 수 없다. 이름(placeholder 에서 온다)은 다르므로
    **고르는 것 자체는 수정 전에도 됐다.** 이 대본이 재는 것은 그 다음이다.
    """

    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        for element in state.get("elements") or []:
            if element.get("placeholder") == placeholder:
                return ("fill", {"element_ref": str(element["element_ref"]), "value": value})
        pytest.fail(
            f"관찰 결과에 placeholder={placeholder} 인 요소가 없다. "
            f"관찰된 것: {[e.get('placeholder') for e in state.get('elements') or []]}"
        )
        raise AssertionError  # pragma: no cover

    return action


def click_by_id(element_id: str) -> Action:
    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        for element in state.get("elements") or []:
            if element.get("id") == element_id:
                return ("click", {"element_ref": str(element["element_ref"])})
        pytest.fail(f"관찰 결과에 id={element_id} 인 요소가 없다")
        raise AssertionError  # pragma: no cover

    return action


def assert_text_contains(value: str) -> Action:
    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return ("assert_condition", {"kind": "text", "value": value, "match": "contains"})

    return action


def shared_id_inputs(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        element
        for element in observed.get("elements") or []
        if element.get("tag") == "input" and element.get("id") == SHARED_ID
    ]


def test_the_element_the_agent_picked_is_the_one_that_gets_the_value(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**고른 칸에 값이 간다.** 이 파일의 요점이며, 수정 전에는 옆 칸에 갔다."""
    seen: list[dict[str, Any]] = []
    script = [
        observe(0),
        capture(seen),
        # 지시문이 가리키는 쪽 — 목록의 이름 검색 칸이다.
        fill_by_placeholder(LIST_PLACEHOLDER, "user"),
        click_by_id("list-go"),
        observe(0),
        # 쓴 쪽에는 값이 갔고,
        assert_text_contains("목록 검색 결과: user"),
        # 옆 칸은 건드리지 않았다. **두 줄이 함께 통과해야 뜻이 있다** — 수정 전에는
        # 첫 줄이 실패하고 전역 쪽이 값을 받았다.
        assert_text_contains("전역 검색 없음"),
    ]
    install_driver(monkeypatch, script)

    sid = start_ai_session(
        keyed_client,
        fixture_app,
        f'사용자 목록의 "{LIST_PLACEHOLDER}" 칸에 user 를 넣고 검색해',
        page="duplicate-id.html",
    )
    try:
        wait_for_event(event_log, "ai_finished")

        assert seen, "관찰 결과를 한 번도 받지 못했다"
        boxes = shared_id_inputs(seen[0])

        # (1) 보고된 조건이 실제로 재현된다 — 같은 id 를 쓰는 입력이 둘이다.
        assert len(boxes) == 2, f"같은 id 를 쓰는 입력이 둘인 화면이 아니다: {boxes}"
        assert {box.get("placeholder") for box in boxes} == {
            GLOBAL_PLACEHOLDER,
            LIST_PLACEHOLDER,
        }

        # (2) **경로가 갈린다.** 수정 전에는 둘 다 `input#text-input-example-11` 이었다.
        #     관찰 결과는 경로를 직접 싣지 않는다. 대신 유일하지 **않을 때만**
        #     `unique: false` 가 붙으므로, 그 표식이 없다는 것이 갈렸다는 뜻이다.
        assert not any(box.get("unique") is False for box in boxes), (
            "같은 id 를 쓰는 칸의 경로가 유일하지 않다 — cssPath 가 id 에서 멈췄다"
        )

        # (3) **정말 그 칸에 썼다.** 검증 둘이 Step 으로 남았다는 것이 그 증거다 —
        #     통과하지 않은 검증은 Step 이 되지 않는다 (FR-061).
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        labels = [step["label"] for step in view["steps"]]
        assert any("목록 검색 결과: user" in label for label in labels), labels
        assert any("전역 검색 없음" in label for label in labels), labels

        # (4) 기록된 Step 의 셀렉터도 갈라져 있다 — 재실행이 같은 칸을 잡는다.
        fills = [step for step in view["steps"] if step["type"] == "fill"]
        assert len(fills) == 1, fills
        css = fills[0]["target"]["css"]
        assert css["status"] == "verified", (
            f"기록된 셀렉터가 유일하지 않다: {css} — 재실행이 다른 칸을 잡는다"
        )
    finally:
        stop_quietly(keyed_client, sid)
