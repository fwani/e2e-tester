"""006 T004·T007·T009·T022·T023 — 편집 핵심이 **한 곳**임을 고정한다.

이 파일이 지키는 것은 기능이 아니라 **구조**다. 006 의 설계 주장은 "편집 능력은 이미
있고, 없는 것은 그리로 가는 길" 이었다. 그 주장이 유지되려면 정의 편집이 세션 편집과 같은
모듈을 써야 하고, 두 번째 구현이 생기지 않아야 한다 (research R2·R3·R5).

구조는 테스트로 고정하지 않으면 다음 사람이 조용히 두 벌로 만든다.
"""

from __future__ import annotations

import ast
import hashlib
import pathlib

import pytest
from pydantic import TypeAdapter

from itb.domain.step import Step
from itb.domain.test_case import (
    Variable,
    derive_variables,
    referenced_variable_names,
    undefined_variable_references,
)
from itb.execution.step_edits import (
    FieldNotSupportedError,
    ValueNotSupportedError,
    update_step,
)

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "itb"
TESTS_ROUTES = SRC / "api" / "routes" / "tests.py"

TARGET = {"tag": "input", "css": {"value": "#u", "status": "verified"}}
STEP_ADAPTER: TypeAdapter[Step] = TypeAdapter(Step)


def _mk(payload: dict[str, object]) -> Step:
    return STEP_ADAPTER.validate_python(payload)


# ─── T004 · update_step 이 늘어난 인자를 받는다 ────────────────────────────


def test_update_step_can_change_tab() -> None:
    """006 FR-183 — 대상 탭. 정의 편집만을 위한 분기를 만들지 않았다."""
    steps = [_mk({"type": "click", "id": "step-01", "label": "x", "target": TARGET})]
    out = update_step(steps, 0, "step-01", tab=2)
    assert out.steps[0].tab == 2


def test_update_step_can_change_navigate_url_and_assertion_value() -> None:
    steps = [
        _mk({"type": "navigate", "id": "step-01", "label": "이동", "url": "http://a/"}),
        _mk(
            {
                "type": "assertion",
                "id": "step-02",
                "label": "검증",
                "assertion": {"kind": "text", "value": "before"},
            }
        ),
    ]
    out = update_step(steps, 0, "step-01", url="http://b/")
    assert out.steps[0].url == "http://b/"
    out = update_step(out.steps, 0, "step-02", assertion_value="after")
    assert out.steps[1].assertion.value == "after"
    # 검증 대상(target)은 건드리지 않는다 — 원칙 IV.
    assert out.steps[1].assertion.target is None


def test_update_step_rejects_fields_the_step_type_lacks() -> None:
    steps = [_mk({"type": "click", "id": "step-01", "label": "x", "target": TARGET})]
    with pytest.raises(ValueNotSupportedError):
        update_step(steps, 0, "step-01", value="x")
    with pytest.raises(FieldNotSupportedError):
        update_step(steps, 0, "step-01", url="http://a/")
    with pytest.raises(FieldNotSupportedError):
        update_step(steps, 0, "step-01", assertion_value="x")


def test_editing_with_index_zero_produces_no_warnings() -> None:
    """정의 편집이 `step_edits` 를 **고치지 않고** 쓸 수 있는 근거 (research R3).

    실행 위치가 없으므로 `current_step_index=0` 으로 부른다. 어떤 인덱스도 0보다 앞일 수
    없어 "이미 실행된 구간을 고쳤다" 경고가 생기지 않는다.
    """
    steps = [
        _mk({"type": "click", "id": f"step-0{i}", "label": "x", "target": TARGET})
        for i in (1, 2, 3)
    ]
    for step_id in ("step-01", "step-02", "step-03"):
        assert update_step(steps, 0, step_id, label="새 이름").warnings == []


def test_update_step_has_no_target_parameter() -> None:
    """FR-187 제외 결정 · 원칙 IV — 후보를 편집 인자로 받지 않는다.

    받으면 검증되지 않은 후보가 정의에 들어간다. 다시 집기는 살아 있는 페이지에서만 된다.
    """
    import inspect

    params = set(inspect.signature(update_step).parameters)
    assert not params & {"target", "drop_target", "css", "test_id", "role"}


# ─── T007 · 변수 파생이 한 곳이다 ──────────────────────────────────────────


def test_referenced_names_cover_every_value_bearing_slot() -> None:
    """한 자리를 빠뜨리면 그 참조가 정의에 반영되지 않고 빈 값이 채워진다."""
    steps = [
        _mk({"type": "navigate", "id": "step-01", "label": "x", "url": "http://a/{{HOST}}"}),
        _mk(
            {
                "type": "fill",
                "id": "step-02",
                "label": "x",
                "target": TARGET,
                "value": "{{USER}}",
            }
        ),
        _mk(
            {
                "type": "assertion",
                "id": "step-03",
                "label": "x",
                "assertion": {"kind": "text", "value": "{{GREETING}}"},
            }
        ),
    ]
    assert referenced_variable_names(steps) == {"HOST", "USER", "GREETING"}


def test_derive_variables_keeps_loaded_sensitive_flag() -> None:
    """FR-214 · research R5 — 강등되면 재실행이 빈 값을 채운다 (조용한 실패)."""
    steps = [
        _mk(
            {
                "type": "fill",
                "id": "step-01",
                "label": "x",
                "target": TARGET,
                "value": "{{SECRET_PW}}",
            }
        )
    ]
    out = derive_variables(
        steps, base_variables=[Variable(name="SECRET_PW", sensitive=True)]
    )
    assert out == [{"name": "SECRET_PW", "value": None, "sensitive": True}]


def test_derive_variables_marks_captured_and_sealed_as_sensitive() -> None:
    steps = [
        _mk(
            {
                "type": "fill",
                "id": "step-01",
                "label": "x",
                "target": TARGET,
                "value": "{{A}}{{B}}{{C}}",
            }
        )
    ]
    out = {v["name"]: v for v in derive_variables(steps, captured_names={"A"}, sealed_names={"B"})}
    assert out["A"]["sensitive"] is True
    assert out["B"]["sensitive"] is True
    assert out["C"] == {"name": "C", "value": "", "sensitive": False}


def test_undefined_references_exclude_sensitive_variables() -> None:
    """민감 변수는 정의에 값을 갖지 않는 것이 정상이다 (FR-082)."""
    steps = [
        _mk(
            {
                "type": "fill",
                "id": "step-01",
                "label": "x",
                "target": TARGET,
                "value": "{{SECRET_PW}}{{TOKEN}}",
            }
        )
    ]
    missing = undefined_variable_references(
        steps,
        [Variable(name="SECRET_PW", sensitive=True), Variable(name="TOKEN", value="")],
    )
    assert missing == ["TOKEN"]


# ─── T009 · revision 은 내용에서 나온다 ────────────────────────────────────


def test_revision_is_content_addressed_not_mtime(tmp_path: pathlib.Path) -> None:
    """research R4 — mtime 을 기각한 근거를 테스트로 고정한다.

    거짓 충돌은 사용자가 곧 무시하게 되고, 그러면 감지 자체가 무의미해진다.
    """
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    a.write_text("id: TC-001\n", encoding="utf-8")
    b.write_text("id: TC-001\n", encoding="utf-8")

    def rev(p: pathlib.Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

    assert rev(a) == rev(b)  # mtime 이 달라도 내용이 같으면 같다
    b.write_text("id: TC-002\n", encoding="utf-8")
    assert rev(a) != rev(b)


# ─── T022 · T023 · 구조 고정 ────────────────────────────────────────────────


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def test_definition_route_reuses_the_shared_edit_core() -> None:
    """FR-192 · 원칙 I — 편집 규칙의 두 번째 구현이 없다."""
    imported = _imported_modules(TESTS_ROUTES)
    assert "itb.execution.step_edits" in imported
    assert "itb.domain.test_case" in imported

    source = TESTS_ROUTES.read_text(encoding="utf-8")
    for fn in ("update_step(", "delete_step(", "reorder_steps(", "derive_variables("):
        assert fn in source, fn


def test_definition_route_never_reaches_the_authoring_layer() -> None:
    """FR-210 · 원칙 II (NON-NEGOTIABLE) — 편집 경로에 언어모델이 없다."""
    imported = _imported_modules(TESTS_ROUTES)
    assert not [m for m in imported if m.startswith("itb.authoring")]
    source = TESTS_ROUTES.read_text(encoding="utf-8")
    for forbidden in ("anthropic", "validate_instruction", "Agent("):
        assert forbidden not in source, forbidden


def test_step_edits_stays_browser_free() -> None:
    """편집 핵심이 브라우저를 손에 들지 않는다 (원칙 III 불변식 3).

    들고 있으면 "여기서 한 번만 되돌리면 편할 텐데" 가 언제든 들어온다.
    """
    imported = _imported_modules(SRC / "execution" / "step_edits.py")
    assert not [m for m in imported if m.startswith("playwright")]
    assert not [m for m in imported if m.startswith("fastapi")]


def test_locator_priority_is_untouched_by_this_feature() -> None:
    """원칙 IV — 해석 순서는 제품 전역 규칙이고 006 이 바꾸지 않았다."""
    from itb.locator.strategy import PRIORITY, StrategyKind

    assert PRIORITY == (
        StrategyKind.TEST_ID,
        StrategyKind.ROLE,
        StrategyKind.LABEL,
        StrategyKind.TEXT,
        StrategyKind.STABLE_ATTR,
        StrategyKind.CSS,
    )


# ─── 009 T031 · 경고가 가리키는 Step 은 삽입에 밀리지 않는다 (FR-311) ────────
#
# **왜 이것이 검사가 되는가.** 편집 경고는 세션의 `edit_warnings` 에 **쌓여 남는다**.
# 사용자가 읽기 전에 다른 편집이 일어날 수 있고, 그 사이 앞쪽에 Step 이 삽입되면
# 번호를 박아 둔 문장은 다른 Step 을 가리킨다 — 번호는 자리이고 정체성이 아니다.


def _run_steps() -> list[Step]:
    return [
        _mk({"type": "navigate", "id": "step-01", "label": "로그인 화면", "url": "/login"}),
        _mk({"type": "fill", "id": "step-02", "label": "아이디", "target": TARGET, "value": "a"}),
        _mk({"type": "click", "id": "step-03", "label": "로그인 클릭", "target": TARGET}),
    ]


def test_이미_실행된_step_경고는_번호가_아니라_이름을_쓴다() -> None:
    """009 FR-311 — 쌓여 남는 문장에는 정체성을 쓴다."""
    from itb.execution.step_edits import delete_step

    result = delete_step(_run_steps(), current_step_index=2, step_id="step-02")

    assert result.warnings, "이미 실행된 Step 을 지웠는데 경고가 없다 (FR-040b)"
    note = result.warnings[0]
    assert "「아이디」" in note
    # 번호를 박지 않는다 — 삽입으로 밀리면 다른 Step 을 가리키게 된다.
    assert "step 02" not in note
    assert "Step 02" not in note


def test_삽입_후에도_경고가_같은_step_을_가리킨다() -> None:
    """FR-311 의 실제 시나리오 — 경고를 만든 뒤 그 앞에 넣는다."""
    from itb.execution.step_edits import delete_step, insert_step

    steps = _run_steps()
    note = delete_step(steps, current_step_index=2, step_id="step-02").warnings[0]

    # 그 뒤 맨 앞에 Step 이 들어와 번호가 전부 밀린다.
    inserted = insert_step(
        steps,
        current_step_index=2,
        step=_mk({"type": "navigate", "id": "step-09", "label": "먼저 이동", "url": "/x"}),
        at=0,
    ).steps
    assert [s.label for s in inserted][:2] == ["먼저 이동", "로그인 화면"]

    # 「아이디」는 2번이 아니라 3번이 됐지만, 경고가 가리키는 대상은 그대로다.
    assert "「아이디」" in note
    moved = next(s for s in inserted if s.label == "아이디")
    assert inserted.index(moved) == 2, "전제가 깨졌다 — 번호가 밀리지 않았다"


def test_순서_변경_경고는_자리를_지목하지_않는다() -> None:
    """FR-311 — 자리 자체가 바뀌는 상황이므로 자리를 말하지 않는다.

    자리 하나를 지목하면 사용자는 그 Step 만 문제라고 읽는다 — 실제로는 그 자리 이후가
    전부 화면 상태와 어긋난다.
    """
    from itb.execution.step_edits import reorder_steps

    result = reorder_steps(
        _run_steps(), current_step_index=2, order=["step-02", "step-01", "step-03"]
    )

    assert result.warnings
    note = result.warnings[0]
    assert "구간" in note
    assert "step 01" not in note
    assert "「" not in note, "구간 경고가 특정 Step 을 이름으로 지목했다"


def test_삽입도_구간_경고를_쓴다() -> None:
    """이미 실행된 구간 안에 넣으면 그 이후가 전부 어긋난다."""
    from itb.execution.step_edits import insert_step

    result = insert_step(
        _run_steps(),
        current_step_index=2,
        step=_mk({"type": "navigate", "id": "step-09", "label": "끼운 이동", "url": "/x"}),
        at=0,
    )

    assert result.warnings
    assert "구간" in result.warnings[0]


def test_실행_위치_뒤의_편집에는_경고가_없다() -> None:
    """없는 위험을 말하지 않는다 — 아직 돌지 않은 Step 은 화면과 어긋날 것이 없다."""
    from itb.execution.step_edits import delete_step, insert_step

    assert not delete_step(_run_steps(), 1, "step-03").warnings
    assert not insert_step(
        _run_steps(),
        1,
        _mk({"type": "navigate", "id": "step-09", "label": "뒤에 이동", "url": "/x"}),
        at=2,
    ).warnings
