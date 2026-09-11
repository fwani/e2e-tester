"""검색 칸이 둘인 화면에서 **AI 가 어느 쪽인지 알 수 있다** (2026-09-11 사용자 보고).

## 보고된 것

> 「ai 에게 시킬때 검색 input 이 한화면에 두개가 있을때, 명확한 위치를 선택하지 못하고
> 다른 input 에 입력을 하는 문제가 있다」

## 왜 그랬나

`observe_page` 가 주던 줄은 `tag·role·name·visible·disabled·type` 여섯 칸이었다. 같은
placeholder 를 쓰는 검색 칸 둘은 여섯 칸이 **모두 같다** — 에이전트가 아는 차이가 목록
순서뿐이므로 앞의 것을 골랐고, 그것이 사용자가 본 「다른 input 에 입력」이다.

주목할 점은 **지목 자체는 정확했다**는 것이다. `cssPath` 는 유일해질 때까지 경로를
늘리고, 실행부는 `count()==1` 이 아니면 채택하지 않는다. 틀린 것은 「어느 요소를
지목할지 정하는 판단」하나였고, 그 판단에 필요한 정보가 화면에서 모델까지 오지 않았다.

## 이 파일이 재는 것

`tests/unit/test_observe_duplicates.py` 는 묶음 표시를 **순수 함수**로 센다. 이 파일은
**살아 있는 브라우저와 실제 화면**(`fixtures/sample-app/twin-search.html`)에서 셋을 본다.

1. 두 검색 칸이 여섯 칸으로는 구별되지 않는다 — 보고된 조건이 실제로 재현된다
2. 그런데도 관찰 결과가 `id`·`context` 로 갈라 주고 `duplicate_with` 로 겹침을 알린다
3. 그 정보로 고른 참조가 **정말 그 칸에 쓴다** — 옆 칸은 비어 있다

3번이 이 수정의 요점이다. 정보가 실려도 그것으로 고른 것이 딴 데 가면 아무 의미가 없다.

자격 증명을 쓰지 않는다 — 갈아 끼우는 것은 「다음에 무엇을 할지 정하는 판단」 하나이고,
관찰·후보 수집·Step 실행·컴파일은 실제 경로를 지난다 (`us4_support`).
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

SEARCH_PLACEHOLDER = "이름 또는 아이디를 검색하세요."
"""두 칸이 **공유**하는 placeholder. 접근 가능한 이름이 여기서 온다."""

SIX_FIELDS = ("tag", "role", "name", "visible", "disabled", "type")
"""수정 전에 에이전트가 받던 칸 전부. 두 칸이 이것만으로는 갈리지 않는다."""


def capture(sink: list[dict[str, Any]]) -> Action:
    """마지막 관찰 결과를 검사 쪽으로 가져온다. 도구는 부르지 않는다."""

    def action(state: dict[str, Any]) -> None:
        sink.append(state)
        return None

    return action


def fill_by_id(element_id: str, value: str) -> Action:
    """**`id` 로 골라서** 입력한다 — 사용자가 지시문에 적어 주는 그 값이다.

    수정 전에는 이 대본을 쓸 수 없었다. 관찰 결과에 `id` 가 없었으므로 모델이 고를 수
    있는 것은 「이름이 같은 둘 중 앞의 것」뿐이었다.
    """

    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        for element in state.get("elements") or []:
            if element.get("id") == element_id:
                return ("fill", {"element_ref": str(element["element_ref"]), "value": value})
        pytest.fail(
            f"관찰 결과에 id={element_id} 인 요소가 없다. "
            f"관찰된 것: {[(e.get('id'), e.get('name')) for e in state.get('elements') or []]}"
        )
        raise AssertionError  # pragma: no cover

    return action


def click_in_context(name: str, context: str) -> Action:
    """**묶음 이름으로 골라서** 누른다 — 「사용자 목록 쪽 검색 버튼」이 그 뜻이다."""

    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        for element in state.get("elements") or []:
            if (element.get("name") or "") == name and element.get("context") == context:
                return ("click", {"element_ref": str(element["element_ref"])})
        pytest.fail(
            f"관찰 결과에 context={context} 인 «{name}» 이 없다. "
            f"관찰된 것: {[(e.get('name'), e.get('context')) for e in state.get('elements') or []]}"
        )
        raise AssertionError  # pragma: no cover

    return action


def assert_text_contains(value: str) -> Action:
    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return ("assert_condition", {"kind": "text", "value": value, "match": "contains"})

    return action


def inputs_of(observed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        element
        for element in observed.get("elements") or []
        if element.get("tag") == "input" and (element.get("name") or "") == SEARCH_PLACEHOLDER
    ]


def test_two_search_boxes_are_distinguishable_and_the_right_one_gets_the_value(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, Any]] = []
    script = [
        observe(0),
        capture(seen),
        # 지시문이 가리키는 쪽 — 「사용자 목록」의 검색 칸이다.
        fill_by_id("user-search", "user"),
        click_in_context("검색", "사용자 목록"),
        observe(0),
        # 쓴 쪽에는 값이 갔고,
        assert_text_contains("사용자 검색 결과: user"),
        # 옆 칸은 건드리지 않았다. 이 두 줄이 함께 통과해야 뜻이 있다.
        assert_text_contains("조직 검색 결과 없음"),
    ]
    install_driver(monkeypatch, script)

    sid = start_ai_session(
        keyed_client,
        fixture_app,
        '사용자 목록의 "이름 또는 아이디를 검색하세요." 칸에 user 를 넣고 검색해',
        page="twin-search.html",
    )
    try:
        wait_for_event(event_log, "ai_finished")

        assert seen, "관찰 결과를 한 번도 받지 못했다"
        boxes = inputs_of(seen[0])
        assert len(boxes) == 2, f"검색 칸이 둘인 화면이 아니다: {boxes}"

        # (1) 보고된 조건이 실제로 재현된다 — 옛 여섯 칸으로는 갈리지 않는다.
        assert {tuple(box[f] for f in SIX_FIELDS) for box in boxes}.__len__() == 1, (
            "두 칸이 여섯 칸만으로 구별된다 — 픽스처가 보고된 화면이 아니다"
        )

        # (2) 그런데도 구별할 것이 있다.
        by_id = {box.get("id"): box for box in boxes}
        assert set(by_id) == {"user-search", "org-search"}, by_id.keys()
        assert by_id["user-search"]["context"] == "사용자 목록"
        assert by_id["org-search"]["context"] == "조직 목록"
        assert by_id["user-search"]["placeholder"] == SEARCH_PLACEHOLDER

        # (3) 겹친다는 사실이 양쪽에 적혀 있다 — 모델이 「모르겠다」를 알 수 있다.
        assert by_id["user-search"]["duplicate_with"] == [by_id["org-search"]["element_ref"]]
        assert by_id["org-search"]["duplicate_with"] == [by_id["user-search"]["element_ref"]]

        # (4) 「검색」 버튼 둘도 같은 사정이며, 같은 방법으로 갈린다.
        buttons = [
            element
            for element in seen[0]["elements"]
            if (element.get("name") or "") == "검색"
        ]
        assert len(buttons) == 2, buttons
        assert {button.get("context") for button in buttons} == {"사용자 목록", "조직 목록"}
        assert all(button.get("duplicate_with") for button in buttons)

        # (5) **정말 그 칸에 썼다.** 검증 둘이 Step 으로 남았다는 것이 그 증거다 —
        #     통과하지 않은 검증은 Step 이 되지 않는다 (FR-061).
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        labels = [step["label"] for step in view["steps"]]
        assert any("사용자 검색 결과: user" in label for label in labels), labels
        assert any("조직 검색 결과 없음" in label for label in labels), labels
    finally:
        stop_quietly(keyed_client, sid)
