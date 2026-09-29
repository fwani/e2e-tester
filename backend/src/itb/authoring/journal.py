"""턴 저널 — 한 턴에 무엇을 했는지를 다음 턴에 전한다. 025 FR-001~FR-007.

## 이 모듈이 존재하는 이유

작성 에이전트의 대화 이력에는 **사용자 메시지밖에 없었다.** SDK 의 tool runner 가 넘겨받은
`messages` 를 복사해 자기 안에서만 늘리기 때문이다 (research R1, `tests/contract/
test_tool_runner_history.py` 가 그 계약을 못 박는다).

그래서 한 턴이 끝나면 **그 턴에 무엇을 관찰했는지, 무엇을 했는지, 무엇을 하다 막혔는지,
무엇이라고 답했는지가 전부 사라졌다.** 제품은 「막힌 자리에서 이어서 하라」고 말하는데,
모델에게는 막힌 자리가 남아 있지 않았다. 사용자는 그것을 「대화가 거듭될수록 AI 가 딴 일을
한다」로 겪었다.

## **제품이 아는 사실로 만든다** (FR-005)

모델에게 요약을 시키지 않는다. 호출이 한 번 더 늘고, 무엇이 사라졌는지 말해 주지 않는다 —
사라진 것이 하필 제약일 때 그 사실이 드러나지 않는다.

제품은 이미 전부 알고 있다. 어떤 도구를 불렀고, 대상이 무엇이었고, 성공했는지 실패했는지,
Step 이 만들어졌는지. 그것을 모으면 된다.

## **원문을 남기지 않는다** (FR-003)

runner 가 쌓은 것을 그대로 이어 붙이는 길이 있었다. 그러지 않는 이유는 크기다 — 화면 관찰
한 번이 상한 근처에서 **66.7KB** 이고(`specs/025-ai-instruction-context/baseline.md` 실측),
한 턴에 스무 장이 쌓인다. 그것을 턴마다 이어 붙이면 몇 번 만에 못 쓰게 된다.

남기는 것은 **무엇을 했는가**이지 **화면이 어땠는가**가 아니다.

## 남기지 않는 세 가지

| | 왜 |
|---|---|
| 요소 참조 (`e17`) | 화면이 바뀌면 낡는다. 낡은 참조를 본 모델은 관찰 없이 그것을 |
| | 쓰려 들고, 그 시도는 거절되지만 예산을 깎는다 |
| 화면 요소 목록·본문 텍스트 | 이 모듈이 없애려는 바로 그 크기다 |
| 조작에 넘긴 값 | 016 정의 요약과 같은 민감값 규칙 — 값이 밖으로 나가는 가지를 만들지 않는다 |

마지막 것이 이 모듈에 `value` 를 받는 자리가 하나도 없는 이유다. 016 의 `summary.py` 는
「값을 읽되 반환 경로에 싣지 않는다」로 풀었는데, 여기서는 **애초에 받지 않는** 것이 가능하다.
받지 않으면 샐 자리가 없다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_JOURNAL_BYTES = 32768
"""이력에 쌓이는 수행 기록의 총량 상한 (FR-006).

**매 턴 붙는 앞머리(16KB)와 성격이 다르다.** 그쪽은 턴마다 새로 만들어지지만 이것은
누적된다 — 열 턴이면 열 개가 쌓인다.

32KB 로 둔 근거: 한 턴의 기록이 보통 1~2KB 다(동작 열 건 남짓에 줄당 60~100바이트).
스무 턴 분이 들어가는 크기이고, 그보다 오래된 것은 「어디까지 했는가」를 작업 계획이
대신 들고 있으므로 접혀도 잃는 것이 적다.

**확인 필요**: 실제 세션에서 턴당 기록 크기를 재어 이 값을 다시 본다. 016 이 8KB 초안을
실측으로 16KB 로 고친 전례가 있다.
"""

UNNAMED_TARGET = "(이름 없는 요소)"
"""이름을 모르는 대상.

**요소 참조를 대신 쓰지 않는다.** `BrowserToolbox._label` 은 이름이 없으면 참조를
그대로 쓰는데(`e17 클릭`), 그 문자열이 이력에 남으면 다음 턴의 모델이 낡은 참조를
집어 든다. 이름을 모른다는 사실을 그대로 적는 편이 낫다.
"""

OMITTED_MARK = "[앞선 {n}개 턴 생략]"
"""접힌 구간 표시.

**조용히 자르지 않는다** (FR-006). 생략을 말하지 않으면 모델은 남은 것이 전부라고 믿고,
이미 한 일을 다시 하거나 없던 일을 있었다고 여긴다.
"""


@dataclass(slots=True)
class ActionNote:
    """도구 호출 하나의 기록.

    `target` 은 **사람이 읽는 이름**이다. 참조가 아니다 — 위 머리말의 표를 보라.
    """

    tool: str
    outcome: str
    target: str | None = None
    step_label: str | None = None

    def render(self) -> str:
        head = f"- {self.tool}"
        if self.target:
            head = f"- 「{self.target}」 {self.tool}"
        line = f"{head} — {self.outcome}"
        if self.step_label:
            line = f"{line} · Step「{self.step_label}」"
        return line


@dataclass(slots=True)
class BlockedNote:
    """막힘 하나의 기록.

    `question` 을 함께 싣는 이유는, 다음 턴이 **그 질문에 대한 답**으로 시작하기
    때문이다. 질문이 없으면 모델은 사용자가 무엇에 답한 것인지 모른다.
    """

    reason: str
    kind: str
    question: str | None = None

    def render(self) -> str:
        line = f"- 막힘({self.kind}): {self.reason}"
        if self.question:
            line = f"{line}\n  (물음: {self.question})"
        return line


@dataclass(slots=True)
class TurnJournal:
    """한 턴 동안 쌓이는 기록. `BrowserToolbox` 가 소유한다.

    **턴마다 비운다.** 앞선 턴의 기록이 이번 턴 기록에 섞이면 같은 동작이 두 번 실린
    것으로 보이고, 모델은 자기가 그 일을 두 번 했다고 읽는다.
    """

    actions: list[ActionNote] = field(default_factory=list)
    blocked: BlockedNote | None = None

    def clear(self) -> None:
        self.actions.clear()
        self.blocked = None

    def note(
        self,
        tool: str,
        outcome: str,
        target: str | None = None,
        step_label: str | None = None,
    ) -> None:
        """동작 하나를 적는다.

        **Step 이 만들어지지 않은 것도 적는다** (FR-004). 관찰·실패한 시도·거절된
        조작이 「이미 해 본 일」이고, 그것을 모르면 다음 턴이 같은 시도를 되풀이한다.
        """
        self.actions.append(
            ActionNote(
                tool=tool,
                outcome=outcome,
                target=target or None,
                step_label=step_label or None,
            )
        )

    def block(self, reason: str, kind: str, question: str | None = None) -> None:
        self.blocked = BlockedNote(reason=reason, kind=kind, question=question)

    @property
    def empty(self) -> bool:
        return not self.actions and self.blocked is None

    def render(self, reply: str = "") -> str:
        """이력에 실릴 한 덩어리로 편다.

        **모델의 답을 같은 메시지에 합친다** (research R3). 나누면 어시스턴트 차례가
        연달아 오고, 그것은 다시 「대화가 아닌 더미」다.
        """
        parts: list[str] = []
        if not self.empty:
            lines = ["[내가 한 일]"]
            lines.extend(a.render() for a in self.actions)
            if self.blocked is not None:
                lines.append(self.blocked.render())
            parts.append("\n".join(lines))
        if reply.strip():
            parts.append(reply.strip())
        return "\n\n".join(parts)


def fold_old_records(
    messages: list[dict[str, object]], budget: int = MAX_JOURNAL_BYTES
) -> list[dict[str, object]]:
    """쌓인 수행 기록이 상한을 넘으면 **오래된 것부터** 접는다 (FR-006).

    ## 무엇을 접고 무엇을 접지 않는가

    접는 것은 **어시스턴트 차례**뿐이다. 사용자 메시지는 접지 않는다 — 거기에 지시문과
    사용자가 한 말이 들어 있고, 그것이 사라지면 이 기능이 고치려는 문제가 더 나빠진다.

    ## 왜 오래된 것부터인가

    가장 최근 턴이 「방금 무엇을 하다 멈췄는가」이고, 재개가 이어지려면 그것이 있어야
    한다. 오래된 턴은 「전체에서 어디쯤인가」를 말하는데, 그 사실은 작업 계획의 진척이
    따로 들고 있다 (data-model §4) — 그래서 접혀도 잃는 것이 적다.

    ## 생략을 명시한다

    조용히 사라지면 모델은 남은 것이 전부라고 믿는다. 몇 개가 접혔는지를 그 자리에 남긴다.

    **원본 리스트를 바꾸지 않는다.** 제품이 든 이력과 모델에게 가는 사본을 가르는 것은
    이 기능 전체의 규칙이다 (FR-033 과 같은 판단).
    """
    total = sum(len(str(m.get("content", "")).encode()) for m in messages)
    if total <= budget:
        return list(messages)

    # 어느 것을 접을지 **먼저 정한다.** 담으면서 지우면 표시를 남길 자리를 잃는다 —
    # 초안이 그렇게 만들어 생략 표시가 첫 사용자 메시지 앞에 붙었고, 그것은 시간순으로
    # 거짓이다 (모델은 그 표시를 「지시문 이전에 무언가 있었다」로 읽는다).
    drop: set[int] = set()
    used = 0
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        size = len(str(message.get("content", "")).encode())
        if message.get("role") != "assistant":
            used += size
            continue
        if used + size > budget:
            drop.add(index)
            continue
        used += size

    if not drop:
        return list(messages)

    out: list[dict[str, object]] = []
    marked = False
    for index, message in enumerate(messages):
        if index in drop:
            if not marked:
                # 접힌 구간의 **첫 자리**에 한 번만 남긴다. 접힌 것마다 표시를 남기면
                # 표시 자체가 다시 이력을 채운다.
                out.append(
                    {"role": "assistant", "content": OMITTED_MARK.format(n=len(drop))}
                )
                marked = True
            continue
        out.append(message)
    return out
