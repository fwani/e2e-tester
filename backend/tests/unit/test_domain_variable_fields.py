"""019 T009 — 변수 참조가 나타날 수 있는 자리가 한 곳에서 온다.

`VARIABLE_VALUE_FIELDS` 는 「이름을 찾는 쪽」(`referenced_variable_names`)과 「자리를 세는
쪽」(`itb.sharing.bundle`)이 함께 보는 목록이다. 세 자리를 두 곳에 베껴 두면 네 번째 자리가
생기는 날 한쪽만 바뀌고, **참조는 찾는데 자리는 못 찾는** 상태가 된다 — 사용자에게는
"채울 목록에 없는데 실행하면 빈 값이 들어간다" 로 보인다.
"""

from __future__ import annotations

from itb.domain.test_case import (
    VARIABLE_VALUE_FIELDS,
    Test,
    referenced_variable_names,
    step_field_text,
    variable_reference,
)

CSS = {"css": {"value": "#x", "status": "verified"}}


def _fill(step_id: str, value: str) -> dict:
    return {
        "id": step_id,
        "label": "입력",
        "type": "fill",
        "target": {"tag": "input", **CSS},
        "value": value,
    }


def _assert_text(step_id: str, value: str) -> dict:
    return {
        "id": step_id,
        "label": "검증",
        "type": "assertion",
        "assertion": {
            "kind": "text",
            "target": {"tag": "div", **CSS},
            "value": value,
            "match": "equals",
        },
    }


def _navigate(step_id: str, url: str) -> dict:
    return {"id": step_id, "label": "이동", "type": "navigate", "url": url}


def _test_with(steps: list[dict], variables: list[dict]) -> Test:
    return Test.model_validate(
        {
            "id": "TC-001",
            "name": "자리 확인",
            "authoring_mode": "record",
            "start_url": "https://example.test",
            "steps": steps,
            "variables": variables,
        }
    )


# ─── 세 자리 모두에서 참조를 찾는다 ────────────────────────────────────────


def test_every_declared_field_is_scanned() -> None:
    """`VARIABLE_VALUE_FIELDS` 의 자리 각각에 넣은 참조가 전부 발견된다."""
    test = _test_with(
        steps=[
            _fill("step-01", variable_reference("IN_VALUE")),
            _assert_text("step-02", variable_reference("IN_ASSERTION")),
            _navigate("step-03", f"https://example.test/{variable_reference('IN_URL')}"),
        ],
        variables=[
            {"name": n, "value": "x", "sensitive": False}
            for n in ("IN_VALUE", "IN_ASSERTION", "IN_URL")
        ],
    )
    assert referenced_variable_names(test.steps) == {"IN_VALUE", "IN_ASSERTION", "IN_URL"}


def test_model_method_delegates_to_module_function() -> None:
    """`Test.referenced_variables` 가 같은 답을 준다 — 두 벌이 아니다 (T006)."""
    test = _test_with(
        steps=[_assert_text("step-01", variable_reference("SAME"))],
        variables=[{"name": "SAME", "value": "x", "sensitive": False}],
    )
    assert test.referenced_variables() == referenced_variable_names(test.steps)


def test_field_list_covers_the_three_known_places() -> None:
    """자리가 늘거나 줄면 이 단언이 먼저 실패한다 — 다른 쪽도 함께 고치라는 신호다."""
    assert VARIABLE_VALUE_FIELDS == ("value", "assertion.value", "url")


# ─── step_field_text 의 안전성 ─────────────────────────────────────────────


def test_missing_field_reads_as_none_without_raising() -> None:
    """Step 종류마다 있는 자리가 다른 것은 정상이다. 예외를 올리면 안 된다."""
    test = _test_with(
        steps=[_navigate("step-01", "https://example.test")],
        variables=[],
    )
    step = test.steps[0]
    assert step_field_text(step, "url") == "https://example.test"
    for field in ("value", "assertion.value"):
        assert step_field_text(step, field) is None


def test_non_string_field_reads_as_none() -> None:
    """문자열이 아닌 자리는 참조를 담을 수 없다. 숫자를 정규식에 넘기지 않는다."""
    test = _test_with(steps=[_fill("step-01", "평문")], variables=[])
    assert step_field_text(test.steps[0], "timeout_ms") is None


def test_no_reference_means_empty_set() -> None:
    test = _test_with(steps=[_fill("step-01", "평문값")], variables=[])
    assert referenced_variable_names(test.steps) == set()
