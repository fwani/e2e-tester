"""019 T012 — 필요 값 산출.

`collect_required_values` 가 받는 사람에게 보여 줄 「채워야 할 것」 목록을 만든다.
담는 기준이 두 갈래이고(민감은 전부, 비민감은 빈 것만), 자리 계산이
`VARIABLE_VALUE_FIELDS` 를 돈다는 것이 확인 대상이다.
"""

from __future__ import annotations

from itb.domain.test_case import Test, variable_reference
from itb.sharing.bundle import collect_required_values

CSS = {"css": {"value": "#x", "status": "verified"}}


def _fill(step_id: str, label: str, value: str) -> dict:
    return {
        "id": step_id,
        "label": label,
        "type": "fill",
        "target": {"tag": "input", **CSS},
        "value": value,
    }


def _assertion(step_id: str, label: str, value: str) -> dict:
    return {
        "id": step_id,
        "label": label,
        "type": "assertion",
        "assertion": {
            "kind": "text",
            "target": {"tag": "div", **CSS},
            "value": value,
            "match": "equals",
        },
    }


def _navigate(step_id: str, label: str, url: str) -> dict:
    return {"id": step_id, "label": label, "type": "navigate", "url": url}


def _test(test_id: str, steps: list[dict], variables: list[dict]) -> Test:
    return Test.model_validate(
        {
            "id": test_id,
            "name": f"{test_id} 테스트",
            "authoring_mode": "record",
            "start_url": "https://example.test",
            "steps": steps,
            "variables": variables,
        }
    )


# ─── 담는 기준 ─────────────────────────────────────────────────────────────


def test_sensitive_variables_are_always_required() -> None:
    """민감 변수는 정의에 값을 가질 수 없으므로 언제나 채워야 한다."""
    test = _test(
        "TC-001",
        [_fill("step-01", "비밀번호 입력", variable_reference("SECRET_PW"))],
        [{"name": "SECRET_PW", "value": None, "sensitive": True}],
    )
    values = collect_required_values([test])
    assert [v.name for v in values] == ["SECRET_PW"]
    assert values[0].sensitive is True
    assert values[0].declared is True


def test_non_sensitive_with_value_is_not_required() -> None:
    """값이 있으면 채울 것이 없다."""
    test = _test(
        "TC-001",
        [_fill("step-01", "아이디 입력", variable_reference("LOGIN_ID"))],
        [{"name": "LOGIN_ID", "value": "platform1", "sensitive": False}],
    )
    assert collect_required_values([test]) == []


def test_non_sensitive_with_empty_value_is_required() -> None:
    """값이 비어 있으면 받는 사람이 채워야 한다 (FR-040)."""
    test = _test(
        "TC-001",
        [_fill("step-01", "아이디 입력", variable_reference("LOGIN_ID"))],
        [{"name": "LOGIN_ID", "value": "", "sensitive": False}],
    )
    values = collect_required_values([test])
    assert [(v.name, v.sensitive) for v in values] == [("LOGIN_ID", False)]


def test_variable_without_any_usage_is_excluded() -> None:
    """선언만 남고 참조가 없는 변수는 채워도 쓰이지 않는다. 목록에 올리지 않는다."""
    test = _test(
        "TC-001",
        [_fill("step-01", "평문 입력", "그냥 값")],
        [{"name": "SECRET_ORPHAN", "value": None, "sensitive": True}],
    )
    assert collect_required_values([test]) == []


# ─── 자리 계산 ─────────────────────────────────────────────────────────────


def test_usages_span_every_value_field() -> None:
    """`VARIABLE_VALUE_FIELDS` 의 세 자리 모두에서 쓰임을 찾는다."""
    test = _test(
        "TC-001",
        [
            _fill("step-01", "입력", variable_reference("SECRET_A")),
            _assertion("step-02", "검증", variable_reference("SECRET_A")),
            _navigate("step-03", "이동", f"https://x.test/{variable_reference('SECRET_A')}"),
        ],
        [{"name": "SECRET_A", "value": None, "sensitive": True}],
    )
    (value,) = collect_required_values([test])
    assert {u.field for u in value.usages} == {"value", "assertion.value", "url"}
    assert {u.step_id for u in value.usages} == {"step-01", "step-02", "step-03"}


def test_usage_carries_step_label_for_the_reader() -> None:
    """이름만으로는 무엇을 넣을지 모른다 — 라벨이 함께 가야 한다 (FR-040)."""
    test = _test(
        "TC-001",
        [_fill("step-01", "비밀번호 입력", variable_reference("SECRET_PW"))],
        [{"name": "SECRET_PW", "value": None, "sensitive": True}],
    )
    (value,) = collect_required_values([test])
    assert value.usages[0].step_label == "비밀번호 입력"
    assert value.usages[0].test_id == "TC-001"


def test_usages_are_collected_across_tests() -> None:
    """같은 변수를 여러 테스트가 쓰면 자리가 모두 모인다. 항목은 하나다."""
    tests = [
        _test(
            "TC-001",
            [_fill("step-01", "입력", variable_reference("SECRET_PW"))],
            [{"name": "SECRET_PW", "value": None, "sensitive": True}],
        ),
        _test(
            "TC-002",
            [_fill("step-01", "입력", variable_reference("SECRET_PW"))],
            [{"name": "SECRET_PW", "value": None, "sensitive": True}],
        ),
    ]
    (value,) = collect_required_values(tests)
    assert {u.test_id for u in value.usages} == {"TC-001", "TC-002"}


def test_output_is_sorted_by_name() -> None:
    """순서가 실행마다 달라지면 같은 프로젝트에서 매번 다른 묶음이 나온다."""
    test = _test(
        "TC-001",
        [
            _fill("step-01", "b", variable_reference("SECRET_B")),
            _fill("step-02", "a", variable_reference("SECRET_A")),
        ],
        [
            {"name": "SECRET_B", "value": None, "sensitive": True},
            {"name": "SECRET_A", "value": None, "sensitive": True},
        ],
    )
    assert [v.name for v in collect_required_values([test])] == ["SECRET_A", "SECRET_B"]
