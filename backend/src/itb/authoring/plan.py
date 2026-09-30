"""작업 계획 — 이 작성 세션이 **요구받은 것**의 정본. 025 FR-008~FR-029.

## 이 모듈이 존재하는 이유

016 이 「지금 테스트」 Step 목록을 매 턴 다시 붙이기로 했다. 그 판단은 옳았고 효과가
있었다. 그러나 그것이 말해 주는 것은 **내가 만든 것**뿐이다.

모델에게 없던 것이 둘이다.

| | 어디에 있었나 |
|---|---|
| **내가 요구받은 것** | 첫 사용자 메시지 한 번뿐 |
| **어디까지 했는가** | 아무도 들고 있지 않았다 |

앞의 빈칸이 「지시문이 준 값을 다른 값으로 바꾼다」와 「금지한 것을 한다」를 만들고, 뒤의
빈칸이 「이미 한 일을 다시 한다」와 「해야 할 구획을 건너뛴다」를 만든다.

## 순수 모듈이다

언어모델도 브라우저도 알지 못한다. 계획을 **만드는** 것은 `refine.py` 이고, 계획을
**주입 문자열로 펴는** 것은 `summary.py` 이며, 계획을 **소유하는** 것은 세션이다.

이 모듈이 아는 것은 「계획이 어떤 모양이고 어떤 변화가 허용되는가」뿐이다. 상태 전이를
한 곳에 모아 두면, 모델이 표시한 것과 사람이 되돌린 것이 같은 규칙을 지난다.

## **상태의 소유자는 제품이다** (FR-025)

모델의 표시는 입력이지 최종 판정이 아니다. 그래서 `mark` 가 거절을 돌려줄 수 있고,
거절 사유가 모델에게 돌아간다. 그것만으로 Step 이 생기지 않는 것은 물론이다 — Step 을
만드는 것은 도구뿐이다 (헌법 원칙 I · FR-037).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

MAX_PLAN_ITEMS = 200
"""계획 항목 수 상한 (contracts/api-contract.md §2).

**매 턴 주입되는 값이므로 상한 없이 받지 않는다.** 그보다 많으면 예산 축약이 상시로
일어나 계획이 늘 부분만 보이고, 그러면 계획을 붙이는 뜻이 사라진다.

200 은 016 의 정의 요약이 Step 100개를 기준으로 잡은 것의 두 배다 — 한 항목이 여러
Step 이 되는 경우가 흔하므로 항목이 Step 보다 적을 것 같지만, 검증만 하는 항목은 Step 을
만들지 않으므로 반대 방향도 있다. 어느 쪽이든 200 을 넘는 지시문은 여러 테스트로 나누는
것이 맞다.
"""


class ItemStatus(StrEnum):
    PENDING = "pending"
    """아직 안 함."""

    DONE = "done"
    """했음. **모델이 표시하거나 사람이 표시한다.**"""

    SKIPPED = "skipped"
    """건너뜀. **사유가 반드시 있다** (FR-027).

    사유 없는 건너뜀은 「하지 않았다」와 구별되지 않고, 그러면 완료 보고가 남은 일을
    덮는다.
    """


class ConstraintScope(StrEnum):
    GLOBAL = "global"
    ITEM = "item"


class PlanSource(StrEnum):
    REFINED = "refined"
    """정제가 만들었다."""

    MANUAL = "manual"
    """사용자가 고쳤다. **정제 결과와 갈라 둔다** — 사용자가 손댄 계획을 다시 정제하면
    그 손댐이 지워진다."""


@dataclass(slots=True)
class Constraint:
    """지켜야 할 것 하나.

    **구체값도 제약이다.** 「연결 주소는 (주소 A) 를 쓴다」는 특정 항목에 걸린 제약이고,
    「기존 데이터는 검증에 쓰지 않는다」는 전역 제약이다. 둘을 다른 종류로 나누지 않는
    이유는 모델에게 둘 다 「어겨서는 안 되는 것」 하나이기 때문이다.
    """

    text: str
    scope: ConstraintScope = ConstraintScope.GLOBAL
    item_id: str | None = None


@dataclass(slots=True)
class PlanItem:
    """할 일 하나."""

    id: str
    order: int
    text: str
    status: ItemStatus = ItemStatus.PENDING
    skip_reason: str | None = None


class PlanError(ValueError):
    """계획을 바꿀 수 없다. 사유가 모델 또는 사용자에게 돌아간다."""


@dataclass(slots=True)
class WorkPlan:
    """한 작성 세션이 요구받은 것.

    **Step 을 참조하지 않는다.** 항목과 Step 은 1:N 도 1:1 도 아니다 — 검증만 하는
    항목은 Step 을 만들지 않고, 한 항목이 여러 Step 이 되기도 한다. 참조를 두면 그
    어긋남을 누군가 메워야 하고, 메우는 쪽은 반드시 짐작한다.
    """

    items: list[PlanItem] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    source: PlanSource = PlanSource.REFINED

    @property
    def empty(self) -> bool:
        """계획이 없는 것과 같은가.

        정제에 실패했거나 사용자가 거절한 세션이 그렇다. 그때 주입은 016 이전과 같이
        정의 요약만 붙는다 (FR-012).
        """
        return not self.items and not self.constraints

    @property
    def remaining(self) -> list[PlanItem]:
        """아직 안 한 것. `ai_finished` 가 이것을 싣는다 (FR-028)."""
        return [i for i in self.items if i.status is ItemStatus.PENDING]

    @property
    def next_item(self) -> PlanItem | None:
        """다음에 할 것.

        **제품이 지목한다** (contracts/agent-context.md §1 의 `▶`). 목록만 주면 모델이
        어디서 이어야 하는지를 스스로 판정해야 하고, 그 판정이 「되풀이」와 「건너뜀」이
        생기는 자리다.
        """
        return self.remaining[0] if self.remaining else None

    def find(self, item_id: str) -> PlanItem | None:
        """항목을 찾는다 — **id 로도, 목록에 보이는 번호로도** (2026-09-30 사용자 보고).

        ## 무엇이 문제였나

        보고 문장: 「`mark_item` 은 id 형식(`1`, `item-01`, `todo-01`, `checklist-1` 등)이
        모두 거부되어 할 일 진행 표시를 남기지 못했습니다.」 — 매 세션 나왔다.

        **모델은 id 를 알 방법이 없었다.** 주입되는 목록(`summary._item_line`)은
        `  1. ▶ 로그인한다` 처럼 **`order` 만** 적고 `id` 는 어디에도 싣지 않는다. 그런데
        이 함수는 `id` 정확 일치만 봤고, 실제 값은 `i1`(정제) 또는 `i5-3847`(대화로 추가,
        해시가 붙는다)이라 추측할 수 있는 형태가 아니다. 모델은 보이는 번호를 넣고,
        거부되면 흔한 규칙을 차례로 시도하다 포기했다.

        ## 왜 목록에 id 를 적는 쪽이 아닌가

        `renumber` 가 「사용자가 보는 번호와 모델에게 가는 번호가 같아야 한다」고 이미
        정해 두었다. 목록에 id 를 덧붙이면 **사람이 보는 것과 모델이 쓰는 것이 다시
        갈라지고**, 줄마다 기계용 문자열이 붙어 주입 예산(`PLAN_BUDGET`)도 먹는다.
        보이는 것으로 지목할 수 있게 하는 편이 규칙이 하나다.

        ## 번호가 바뀌는 것은 위험하지 않은가

        `renumber` 는 항목이 **빠질 때** 번호를 당긴다. 그런데 목록은 매 턴 새로 주입되고
        `add` 는 끝에 붙이므로(기존 번호가 밀리지 않는다), 모델이 그 턴에 본 번호는 그
        턴 안에서 유효하다. id 를 먼저 보므로 **id 를 가진 호출자(프론트의 되돌리기)는
        영향을 받지 않는다.**
        """
        found = next((i for i in self.items if i.id == item_id), None)
        if found is not None:
            return found
        # 목록에 보이는 번호. `id` 는 `i1`·`i5-3847` 형태라 순수 숫자와 겹치지 않는다.
        text = item_id.strip()
        if not text.isdigit():
            return None
        return next((i for i in self.items if i.order == int(text)), None)

    def renumber(self) -> None:
        """순번을 1부터 다시 매긴다.

        **사용자가 보는 번호와 모델에게 가는 번호가 같아야 한다.** 016 의 정의 요약이
        1부터 매긴 것과 같은 판단이다 — 어긋나면 사용자가 「3번을 다시」라고 말했을 때
        모델이 다른 것을 집는다.
        """
        for index, item in enumerate(self.items, start=1):
            item.order = index

    def mark(
        self, item_id: str, status: ItemStatus, reason: str | None = None
    ) -> PlanItem:
        """항목의 상태를 바꾼다. **모델과 사람이 같은 문을 지난다.**

        ## 모델이 되돌릴 수 없는 이유 (data-model §2)

        `pending` 으로 옮기는 것은 사용자만 한다 (`revert`). 모델이 자기 표시를 취소할
        수 있으면 「했다」가 무엇을 뜻하는지 알 수 없다 — 했다가 안 했다가 하는 값은
        진척이 아니다.

        ## 같은 항목을 여러 번 표시해도 한 번만 바뀐다

        모델이 성실히 표시하다 중복해도 해롭지 않아야 한다 (research R9). 이미 그 상태면
        조용히 같은 항목을 돌려준다 — 거절하면 모델이 「무언가 잘못됐다」로 읽는다.
        """
        item = self.find(item_id)
        if item is None:
            # **쓸 수 있는 것을 말한다.** 옛 문면은 「번호와 id 를 확인하세요」였는데,
            # 목록에 id 가 없으므로 모델은 확인할 것이 없었고 같은 추측을 반복했다.
            span = f"1~{len(self.items)}" if self.items else "없음"
            msg = (
                f"그런 항목이 없습니다: {item_id}. "
                f"[할 일] 목록에 보이는 번호를 그대로 쓰세요 (지금 있는 번호: {span})."
            )
            raise PlanError(msg)
        if status is ItemStatus.PENDING:
            msg = "완료 표시를 되돌리는 것은 사용자만 할 수 있습니다."
            raise PlanError(msg)
        if status is ItemStatus.SKIPPED and not (reason or "").strip():
            msg = "건너뛰는 이유를 적어 주세요. 사유 없는 건너뜀은 기록되지 않습니다."
            raise PlanError(msg)
        if item.status is status:
            return item
        item.status = status
        item.skip_reason = (reason or "").strip() or None if status is ItemStatus.SKIPPED else None
        return item

    def revert(self, item_id: str) -> PlanItem:
        """사용자가 항목을 미완료로 되돌린다."""
        item = self.find(item_id)
        if item is None:
            msg = f"그런 항목이 없습니다: {item_id}"
            raise PlanError(msg)
        item.status = ItemStatus.PENDING
        item.skip_reason = None
        return item

    def append(self, text: str) -> PlanItem:
        """대화로 온 새 지시를 항목으로 더한다 (FR-029).

        계획에 없던 일이 생기는 것은 정상이다 — 사용자는 작성 도중에 마음을 바꾼다.
        그것이 계획에 들어가지 않으면 진척이 거짓이 된다.
        """
        if len(self.items) >= MAX_PLAN_ITEMS:
            msg = f"할 일이 너무 많습니다({MAX_PLAN_ITEMS}개 상한)."
            raise PlanError(msg)
        item = PlanItem(
            id=f"i{len(self.items) + 1}-{abs(hash(text)) % 10000}",
            order=len(self.items) + 1,
            text=text.strip(),
        )
        self.items.append(item)
        self.renumber()
        return item

    def constraints_for(self, item_id: str | None = None) -> list[Constraint]:
        """전역 제약과, 주어진 항목에 걸린 제약."""
        return [
            c
            for c in self.constraints
            if c.scope is ConstraintScope.GLOBAL
            or (item_id is not None and c.item_id == item_id)
        ]
