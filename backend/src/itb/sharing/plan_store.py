"""가져오기 계획 보관소 (기능 019 · data-model §3).

**디스크에 쓰지 않는다.** 확정 전에는 아무것도 만들지 않아야 하는데, 디스크에 쓰면 그
자체가 "만든 것" 이 된다. 서버가 죽으면 계획이 사라지는 것은 맞는 동작이다 — 사용자는
파일을 다시 고르면 되고, 그 사이 아무것도 만들어지지 않았다.

계획 ID 로 미리보기와 확정을 묶는 이유는 두 가지다. 확정 때 파일을 다시 올리게 하면
(a) 사용자가 같은 파일을 두 번 올려야 하고, (b) 미리보기에서 본 것과 확정하는 것이 같은
파일이라는 보장이 없다.

**014 의 `itb.portability.plan_store` 와 합치지 않았다.** 담는 타입이 다르고, 합치려면
기존 엑셀 경로를 건드려야 하며, 얻는 것은 40줄 남짓이다 (research R8). 상한값은 각자의
`limits.py` 에 있고 의미가 같은 값은 같은 근거를 달아 두었다.
"""

from __future__ import annotations

import datetime as dt

from itb.sharing.limits import MAX_SHARE_PLANS, SHARE_PLAN_TTL_SECONDS
from itb.sharing.planner import SharePlan


class SharePlanStore:
    """짧게 사는 계획들. 앱 상태에 하나 둔다."""

    def __init__(
        self,
        *,
        ttl_seconds: int = SHARE_PLAN_TTL_SECONDS,
        capacity: int = MAX_SHARE_PLANS,
    ) -> None:
        self._ttl = dt.timedelta(seconds=ttl_seconds)
        self._capacity = capacity
        self._plans: dict[str, SharePlan] = {}

    def put(self, plan: SharePlan) -> SharePlan:
        """계획을 넣는다. 상한을 넘으면 **오래된 것부터** 버린다."""
        self._sweep()
        self._plans[plan.plan_id] = plan
        while len(self._plans) > self._capacity:
            oldest = min(self._plans.values(), key=lambda p: p.created_at)
            del self._plans[oldest.plan_id]
        return plan

    def get(self, plan_id: str) -> SharePlan | None:
        """만료됐으면 `None`. **만료와 없음을 구별하지 않는다** — 사용자가 할 일이 같다."""
        self._sweep()
        return self._plans.get(plan_id)

    def drop(self, plan_id: str) -> None:
        """확정이 끝난 계획을 치운다. 같은 계획을 두 번 확정하지 못하게 한다."""
        self._plans.pop(plan_id, None)

    def _sweep(self) -> None:
        for plan_id, plan in list(self._plans.items()):
            if plan.expired:
                del self._plans[plan_id]

    def __len__(self) -> int:
        self._sweep()
        return len(self._plans)
