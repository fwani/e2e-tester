"""턴 저널 — 무엇을 남기고 무엇을 남기지 않는가 (025 T007·T009).

## 이 파일이 지키는 성질

저널의 값은 **다음 턴의 모델이 읽는다.** 그래서 두 가지가 동시에 참이어야 한다.

1. 「이미 해 본 일」이 빠짐없이 남는다 — 빠지면 다음 턴이 되풀이한다 (FR-004)
2. 다음 턴에 **해로운 것**은 남지 않는다 — 낡은 요소 참조, 화면 원문, 입력값 (FR-003)

둘째가 이 파일의 무게중심이다. 첫째는 빠지면 눈에 띄지만, 둘째는 빠져도 한동안 아무도
모른다 — 값이 새는 것은 실패로 보이지 않기 때문이다.
"""

from __future__ import annotations

from itb.authoring.journal import (
    MAX_JOURNAL_BYTES,
    OMITTED_MARK,
    UNNAMED_TARGET,
    TurnJournal,
    fold_old_records,
)


def test_records_what_was_done() -> None:
    """한 일이 순서대로 남는다."""
    journal = TurnJournal()
    journal.note("화면 관찰", "요소 12개 확인", target="탭 0")
    journal.note("click", "완료", target="로그인", step_label="로그인 클릭")

    rendered = journal.render()

    assert "[내가 한 일]" in rendered
    assert "화면 관찰" in rendered
    assert "로그인" in rendered
    assert "Step「로그인 클릭」" in rendered
    assert rendered.index("화면 관찰") < rendered.index("click")


def test_records_actions_that_made_no_step() -> None:
    """**Step 이 생기지 않은 것도 남는다** (FR-004).

    관찰·실패한 시도·거절된 조작이 「이미 해 본 일」이다. 이것이 빠지면 다음 턴이 같은
    시도를 되풀이하고, 되풀이는 예산을 깎는다.
    """
    journal = TurnJournal()
    journal.note("화면 관찰", "요소 3개 확인", target="탭 0")
    journal.note("click", "실패: 요소를 찾지 못했다", target="저장")
    journal.note("조작", "거절됨: 가리키는 자리가 하나로 좁혀지지 않는다", target="삭제")

    rendered = journal.render()

    assert "실패" in rendered
    assert "거절됨" in rendered
    assert rendered.count("- ") == 3


def test_blocked_carries_its_question() -> None:
    """막힘에는 **물음이 함께 남는다**.

    다음 턴이 그 물음에 대한 답으로 시작하기 때문이다. 물음이 없으면 모델은 사용자가
    무엇에 답한 것인지 모른다.
    """
    journal = TurnJournal()
    journal.block("「저장」 버튼이 셋이다", "needs_input", "어느 저장 버튼입니까?")

    rendered = journal.render()

    assert "막힘(needs_input)" in rendered
    assert "어느 저장 버튼입니까?" in rendered


def test_reply_is_merged_into_one_message() -> None:
    """수행 기록과 모델의 답이 **한 덩어리**로 나온다 (research R3).

    나누면 어시스턴트 차례가 연달아 오고, 그것은 다시 「대화가 아닌 더미」다.
    """
    journal = TurnJournal()
    journal.note("click", "완료", target="로그인")

    rendered = journal.render("로그인까지 마쳤습니다.")

    assert "[내가 한 일]" in rendered
    assert "로그인까지 마쳤습니다." in rendered


def test_empty_journal_renders_nothing() -> None:
    """빈 턴은 빈 문자열이다 — 이력에 뜻 없는 차례를 남기지 않는다."""
    assert TurnJournal().render() == ""
    assert TurnJournal().render("   ") == ""


def test_journal_has_no_place_for_values() -> None:
    """**값을 받는 자리가 없다** (FR-003 · 016 민감값 규칙).

    016 의 `summary.py` 는 「값을 읽되 반환 경로에 싣지 않는다」로 풀었다. 여기서는
    **애초에 받지 않는** 것이 가능했고, 받지 않으면 샐 자리가 없다.

    이 검증은 서명을 본다 — 구현이 아니라 **구조**를 고정한다. 누군가 `value` 인자를
    더하면 여기서 실패하고, 그때 「왜 값이 필요한가」를 먼저 답해야 한다.
    """
    import inspect

    names = set(inspect.signature(TurnJournal.note).parameters)
    assert "value" not in names
    assert names == {"self", "tool", "outcome", "target", "step_label"}


def test_unnamed_target_does_not_leak_a_reference() -> None:
    """이름을 모르면 **그 사실을 적는다.** 요소 참조를 대신 쓰지 않는다.

    참조(`e17`)는 화면이 바뀌면 낡는다. 낡은 참조를 본 모델은 관찰 없이 그것을 집어
    들고, 그 시도는 거절되지만 예산을 깎는다.
    """
    journal = TurnJournal()
    journal.note("click", "완료", target=UNNAMED_TARGET)

    rendered = journal.render()

    assert UNNAMED_TARGET in rendered
    assert "e1" not in rendered


def test_fold_keeps_recent_and_marks_omission() -> None:
    """상한을 넘으면 **오래된 것부터** 접고 **생략을 명시한다** (FR-006).

    조용히 사라지면 모델은 남은 것이 전부라고 믿는다.
    """
    big = "x" * 20000
    messages: list[dict[str, object]] = [
        {"role": "user", "content": "원 지시문"},
        {"role": "assistant", "content": f"턴1 {big}"},
        {"role": "user", "content": "사용자 답변"},
        {"role": "assistant", "content": f"턴2 {big}"},
        {"role": "assistant", "content": "턴3 최근"},
    ]

    out = fold_old_records(messages, budget=32768)
    contents = [str(m["content"]) for m in out]

    assert "원 지시문" in contents[0], "사용자 메시지는 접지 않는다"
    assert any(OMITTED_MARK.format(n=1) == c for c in contents), "생략을 명시해야 한다"
    assert any("턴3 최근" == c for c in contents), "가장 최근 턴이 남아야 한다"
    assert "사용자 답변" in contents


def test_fold_marks_omission_in_place() -> None:
    """생략 표시가 **접힌 자리**에 남는다.

    초안은 표시를 맨 앞에 붙였고, 그러면 원 지시문 **앞**에 「앞선 턴 생략」이 온다 —
    모델은 그것을 「지시문 이전에 무언가 있었다」로 읽는다. 시간순으로 거짓이다.
    """
    big = "y" * 20000
    messages: list[dict[str, object]] = [
        {"role": "user", "content": "원 지시문"},
        {"role": "assistant", "content": f"턴1 {big}"},
        {"role": "assistant", "content": f"턴2 {big}"},
        {"role": "assistant", "content": "턴3 최근"},
    ]

    contents = [str(m["content"]) for m in fold_old_records(messages, budget=32768)]

    assert contents[0] == "원 지시문"
    assert contents[1].startswith("[앞선")


def test_fold_is_a_no_op_under_budget() -> None:
    """상한 안이면 아무것도 건드리지 않는다."""
    messages: list[dict[str, object]] = [
        {"role": "user", "content": "지시"},
        {"role": "assistant", "content": "짧은 기록"},
    ]

    out = fold_old_records(messages, budget=MAX_JOURNAL_BYTES)

    assert out == messages
    assert out is not messages, "원본 리스트를 돌려주지 않는다 — 사본이어야 한다"
