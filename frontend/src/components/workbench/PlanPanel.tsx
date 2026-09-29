import { Button } from "../../ui/Button";
import type { PlanItem, WorkPlan } from "../../api/client";

/**
 * 작업 계획의 진척 (025 US5 · FR-028).
 *
 * ## 사용자와 AI 가 **같은 목록**을 본다
 *
 * AI 에게 매 턴 주입되는 것과 여기 보이는 것이 같은 값이다. 둘이 갈라지면 사용자는
 * 「AI 가 무엇을 하고 있는지」를 추측해야 하고, 그 추측이 이 기능 전체가 없애려는
 * 것이다.
 *
 * ## 되돌리기는 사용자만 한다
 *
 * 모델은 `done`·`skipped` 로만 옮길 수 있다. 자기 표시를 취소할 수 있으면 「했다」가
 * 무엇을 뜻하는지 알 수 없기 때문이다 (data-model §2). 그래서 이 패널에만 되돌리기가
 * 있다.
 *
 * ## 계획이 없으면 그리지 않는다
 *
 * 정제에 실패했거나 사용자가 거절한 세션이 그렇다. 빈 목록을 그리면 사용자는 「할 일이
 * 없다」로 읽는데, 사실은 「할 일 목록을 쓰지 않는 세션」이다 — 다른 사실이다.
 */
export interface PlanPanelProps {
  plan: WorkPlan | null;
  /** 항목을 되돌린다. 진행 중이면 잠긴다 — 되돌리기는 AI 가 읽는 값을 바꾼다. */
  onRevert?: (itemId: string) => void;
  busy?: boolean;
}

/** 상태별 표시. AI 에게 가는 문자열(`✓`·`▶`·`—`)과 **같은 기호**를 쓴다. */
function markOf(item: PlanItem, isNext: boolean): string {
  if (item.status === "done") return "✓";
  if (item.status === "skipped") return "—";
  return isNext ? "▶" : " ";
}

export function PlanPanel({ plan, onRevert, busy = false }: PlanPanelProps) {
  if (plan === null || (plan.items.length === 0 && plan.constraints.length === 0)) {
    return null;
  }

  const nextId = plan.items.find((i) => i.status === "pending")?.id ?? null;
  const remaining = plan.items.filter((i) => i.status === "pending").length;

  return (
    <section className="plan-panel" aria-label="할 일">
      {plan.constraints.length > 0 && (
        <div className="plan-constraints">
          <h3>반드시 지킬 것</h3>
          <ul>
            {plan.constraints.map((constraint, index) => (
              <li key={`${constraint.text}-${index}`}>{constraint.text}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="plan-items">
        <h3>
          할 일
          <span className="plan-remaining">
            {remaining === 0 ? "남은 것 없음" : `${remaining}개 남음`}
          </span>
        </h3>
        <ol>
          {plan.items.map((item) => (
            <li key={item.id} data-status={item.status} data-next={item.id === nextId}>
              <span className="plan-mark" aria-hidden="true">
                {markOf(item, item.id === nextId)}
              </span>
              <span className="plan-text">{item.text}</span>
              {item.status === "skipped" && item.skip_reason && (
                <span className="plan-reason">건너뜀: {item.skip_reason}</span>
              )}
              {item.status !== "pending" && onRevert && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busy}
                  onClick={() => onRevert(item.id)}
                >
                  되돌리기
                </Button>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
