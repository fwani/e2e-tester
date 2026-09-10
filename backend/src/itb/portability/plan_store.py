"""가져오기 계획 보관소 (기능 014 · research R8).

**디스크에 쓰지 않는다.** 확정 전에는 아무것도 만들지 않아야 하는데(FR-016), 디스크에 쓰면
그 자체가 "만든 것"이 된다. 서버가 죽으면 계획이 사라지는 것은 맞는 동작이다 — 사용자는
파일을 다시 고르면 되고, 그 사이 아무것도 만들어지지 않았다.

계획 ID 로 미리보기와 확정을 묶는 이유는 두 가지다. 확정 때 파일을 다시 올리게 하면
(a) 사용자가 100MB 를 두 번 올려야 하고, (b) 미리보기에서 본 것과 확정하는 것이 같은
파일이라는 보장이 없다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from itb.portability.importer import ImportPlan
from itb.portability.limits import IMPORT_PLAN_TTL_SECONDS, MAX_IMPORT_PLANS
from itb.portability.workbook import ParsedWorkbook


@dataclass(slots=True)
class StoredPlan:
    """계획과, 그 계획을 **다시 세우는 데 필요한 재료**.

    확정할 때 사용자가 시트 선택과 컬럼 짝짓기를 보내면 계획을 다시 세워야 한다 —
    어느 열이 어느 컬럼인지가 바뀌면 **행이 다르게 읽히기** 때문이다. 접두어처럼
    자리에서 갈아 끼울 수 있는 값이 아니다.

    그래서 해석 결과(:class:`ParsedWorkbook`)를 함께 들고 있는다. 파일을 다시 올리게
    하지 않는 이유와 같다 — 미리보기에서 본 것과 확정하는 것이 같은 파일이어야 한다.
    행 상한이 5,000 이므로 메모리는 유계다.
    """

    plan: ImportPlan
    parsed: ParsedWorkbook


class ImportPlanStore:
    """짧게 사는 계획들. 앱 상태에 하나 둔다."""

    def __init__(
        self,
        *,
        ttl_seconds: int = IMPORT_PLAN_TTL_SECONDS,
        capacity: int = MAX_IMPORT_PLANS,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._capacity = capacity
        self._plans: dict[str, StoredPlan] = {}

    def put(self, plan: ImportPlan, parsed: ParsedWorkbook) -> ImportPlan:
        """계획을 넣는다. 상한을 넘으면 **오래된 것부터** 버린다."""
        self._sweep()
        self._plans[plan.plan_id] = StoredPlan(plan=plan, parsed=parsed)
        while len(self._plans) > self._capacity:
            oldest = min(self._plans.values(), key=lambda e: e.plan.created_at)
            del self._plans[oldest.plan.plan_id]
        return plan

    def get(self, plan_id: str) -> ImportPlan | None:
        """계획 하나. 만료됐으면 ``None`` 이며, 그때 함께 치운다."""
        entry = self.entry(plan_id)
        return entry.plan if entry else None

    def entry(self, plan_id: str) -> StoredPlan | None:
        """계획과 재료. 다시 세울 때 쓴다."""
        self._sweep()
        return self._plans.get(plan_id)

    def drop(self, plan_id: str) -> None:
        """확정에 썼으면 치운다. 같은 계획으로 두 번 만들지 않게 한다."""
        self._plans.pop(plan_id, None)

    def expires_at(self, plan: ImportPlan) -> datetime:
        return plan.created_at + self._ttl

    def _sweep(self) -> None:
        cutoff = datetime.now(UTC) - self._ttl
        stale = [e.plan.plan_id for e in self._plans.values() if e.plan.created_at < cutoff]
        for plan_id in stale:
            del self._plans[plan_id]
