"""AI 편집과 사람 편집이 **구별되지 않는다**. 016 FR-036·FR-039 · SC-006 (T053).

헌법 원칙 I (NON-NEGOTIABLE) — 「A Step MUST NOT carry information about who authored
it as a semantic difference」.

## 무엇을 어떻게 확인하는가

`test_tool_surface.py` 가 **같은 함수를 지나는지**를 구조로 고정한다. 이 파일은 그
결과가 실제로 같은지를 **값으로** 본다. 둘 다 필요하다 — 구조만 보면 같은 함수를
부르면서 앞뒤로 다른 일을 할 수 있고, 값만 보면 다음 사람이 우연히 같아 보이는 다른
길을 내도 통과한다.
"""

from __future__ import annotations

import pytest

from itb.authoring.tools import BrowserToolbox
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import Author, ClickStep, FillStep, Step
from itb.execution.step_edits import EditResult, delete_step, reorder_steps, update_step


def target(name: str) -> TargetLocator:
    return TargetLocator(
        role="button",
        accessible_name=name,
        css=Candidate(value=f"button.{name}", status=CandidateStatus.VERIFIED),
    )


def mixed_steps() -> list[Step]:
    """사람이 만든 것과 AI 가 만든 것을 섞는다.

    `author` 가 섞여 있어도 편집 결과가 같아야 한다 — 그것이 「작성 주체가 의미 차이를
    만들지 않는다」의 뜻이다.
    """
    return [
        ClickStep(id="step-01", label="사람 클릭", target=target("a"), author=Author.HUMAN),
        FillStep(
            id="step-02",
            label="AI 입력",
            target=target("b"),
            value="{{값}}",
            author=Author.AI,
        ),
        ClickStep(id="step-03", label="AI 클릭", target=target("c"), author=Author.AI),
    ]


class Harness:
    def __init__(self, steps: list[Step]) -> None:
        self.steps = list(steps)
        self.box = BrowserToolbox(
            session=None,  # type: ignore[arg-type]
            executor=None,  # type: ignore[arg-type]
            allocate_step_id=lambda: "step-99",
            on_step=_unused,
            steps_source=lambda: self.steps,
            on_edit=self._apply,
            in_scope=lambda _sid: True,
        )

    async def _apply(self, result: EditResult) -> None:
        self.steps = result.steps


async def _unused(_step: Step) -> None:  # pragma: no cover
    raise AssertionError


def shape(steps: list[Step]) -> list[str]:
    """저장될 모양. **`author` 를 포함해** 통째로 비교한다."""
    return [s.model_dump_json() for s in steps]


# ─── 같은 편집, 같은 결과 (SC-006) ──────────────────────────────────────────


@pytest.mark.anyio
async def test_update_matches_the_human_path() -> None:
    """표시 이름 고치기 — AI 와 사람의 결과가 **저장 형식까지 같다**."""
    h = Harness(mixed_steps())
    await h.box.update_step("step-02", "label", "주문 저장")

    human = update_step(mixed_steps(), 0, "step-02", label="주문 저장")
    assert shape(h.steps) == shape(human.steps)


@pytest.mark.anyio
async def test_updating_a_value_matches_the_human_path() -> None:
    h = Harness(mixed_steps())
    await h.box.update_step("step-02", "value", "{{다른값}}")

    human = update_step(mixed_steps(), 0, "step-02", value="{{다른값}}")
    assert shape(h.steps) == shape(human.steps)


@pytest.mark.anyio
async def test_delete_matches_the_human_path() -> None:
    h = Harness(mixed_steps())
    await h.box.delete_step("step-02")

    human = delete_step(mixed_steps(), 0, "step-02")
    assert shape(h.steps) == shape(human.steps)


@pytest.mark.anyio
async def test_move_matches_the_human_path() -> None:
    """순서 바꾸기 — AI 의 `move_step(down)` 과 사람의 `reorder_steps` 가 같다."""
    h = Harness(mixed_steps())
    await h.box.move_step("step-01", "down")

    human = reorder_steps(mixed_steps(), 0, ["step-02", "step-01", "step-03"])
    assert shape(h.steps) == shape(human.steps)


@pytest.mark.anyio
async def test_editing_does_not_change_the_author_field() -> None:
    """**AI 가 고쳐도 `author` 가 바뀌지 않는다.**

    바뀌면 「누가 만들었는가」가 「누가 마지막에 손댔는가」로 뜻이 흔들린다. 그리고
    `author` 는 실행 방식을 바꾸지 않으므로(원칙 I), 바꿀 이유도 없다.
    """
    h = Harness(mixed_steps())
    await h.box.update_step("step-01", "label", "AI 가 이름만 고쳤다")

    changed = next(s for s in h.steps if s.id == "step-01")
    assert changed.author is Author.HUMAN, (
        "사람이 만든 Step 을 AI 가 고쳤다고 작성 주체가 바뀌면 안 된다"
    )


@pytest.mark.anyio
async def test_an_edited_step_still_validates_as_the_stored_model() -> None:
    """고친 Step 이 **저장 모델로 그대로 유효하다**.

    편집이 pydantic 검증을 우회하면, 후보가 하나도 없는 `TargetLocator` 같은 상태가
    조용히 저장될 수 있다 (원칙 IV 의 불변식이 깨진다).
    """
    from pydantic import TypeAdapter

    h = Harness(mixed_steps())
    await h.box.update_step("step-02", "label", "검증")
    adapter = TypeAdapter(Step)
    for s in h.steps:
        adapter.validate_python(s.model_dump(mode="python"))


# ─── 같은 이벤트 (FR-039) ───────────────────────────────────────────────────


def test_ai_edits_go_out_as_the_same_events_humans_do() -> None:
    """AI 의 편집이 **사람 편집과 같은 이벤트 이름**으로 나간다 (FR-039).

    같은 함수를 지나는 것(SC-006)과 같은 이벤트를 내는 것은 **다른 보장**이다. 화면이
    「AI 가 고친 것」과 「사람이 고친 것」을 다른 통로로 받으면, 한쪽만 그리는 자리가
    생긴다.

    구조로 본다 — AI 경로의 반영 함수가 내는 이벤트 이름이 사람 경로의 것에 포함되는지.
    """
    import inspect

    from itb.api.routes import sessions as ai_routes
    from itb.api.routes import steps as human_routes

    human_source = inspect.getsource(human_routes)
    emitted = emitted_event_names(ai_routes._apply_ai_edit)

    assert emitted, "AI 편집이 아무 이벤트도 내지 않는다"
    step_events = {n for n in emitted if n.startswith("step")}
    assert step_events, "Step 변경을 알리는 이벤트가 없다"
    for name in step_events:
        assert f'"{name}"' in human_source, (
            f"AI 만 내는 이벤트가 있다: {name} — 작성 주체별 통로를 만들지 않는다 (FR-039)"
        )


def emitted_event_names(fn: object) -> set[str]:
    """그 함수가 `emit("...")` 로 내는 이벤트 이름들.

    **소스 문자열을 훑지 않고 호출 인자만 본다.** 처음에는 소스에 `"ai_"` 가 있는지
    보게 짰는데, 함수 이름(`_apply_ai_edit`) 자체가 걸려서 검사가 거짓 경보를 냈다 —
    이름을 잡는 검사가 아니라 **이벤트**를 잡는 검사여야 한다.
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "emit"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.add(node.args[0].value)
    return names


def test_no_event_name_mentions_ai() -> None:
    """이벤트 **이름**에 작성 주체가 들어가지 않는다.

    `ai_step_updated` 같은 이름이 생기는 순간 화면에 분기가 생기고, 원칙 I 이 화면
    계층에서 깨진다. (`ai_progress`·`ai_blocked`·`ai_finished` 는 **작성 과정**의
    이벤트이지 Step 변경 이벤트가 아니므로 해당하지 않는다.)
    """
    from itb.api.routes import sessions as ai_routes

    names = emitted_event_names(ai_routes._apply_ai_edit)
    assert names, "AI 편집이 아무 이벤트도 내지 않는다"
    for name in names:
        assert not name.startswith("ai_"), (
            f"작성 주체가 이벤트 이름에 들어갔다: {name} — 화면에 분기가 생긴다"
        )
