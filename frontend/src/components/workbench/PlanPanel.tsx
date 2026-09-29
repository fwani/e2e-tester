import { useState } from "react";

import { Button } from "../../ui/Button";
import { IconButton } from "../../ui/IconButton";
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
 * ## **접힌 채로 시작한다** (2026-09-29 사용자 보고)
 *
 * 초안은 항상 펼쳐 두었고, 항목이 21개인 실제 계획에서 **대화 기록과 답변 자리를
 * 밀어냈다.** 사용자가 겪은 것:
 *
 * > 「반드시 지킬 것, 할일 부분이 고정되어서 대화 2차례 · 자취 74줄 부분이 제대로
 * > 안보인다. 답변 대기시 답변을 클릭할수도 없다.」
 *
 * 답변을 클릭할 수 없는 것이 가장 나쁘다 — 막힌 AI 를 풀 수 없다는 뜻이다.
 *
 * **진척의 핵심은 머리줄 한 줄이다** (「3/21 · 남은 것 18」). 목록 전체는 필요할 때
 * 펼친다. 이 패널이 이미 자취에 같은 방식을 쓴다 (`traceOpen`).
 *
 * ## 막혔을 때는 숨는다
 *
 * 답변이 최우선이다. 같은 자리의 대화 입력칸이 이미 그렇게 한다
 * (`hidden={failure?.blocked != null}`).
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
  /** 막힘 답변을 기다리는 중인가. 그때는 숨는다 — 답변이 최우선이다. */
  hidden?: boolean;
}

/** 상태별 표시. AI 에게 가는 문자열(`✓`·`▶`·`—`)과 **같은 기호**를 쓴다. */
function markOf(item: PlanItem, isNext: boolean): string {
  if (item.status === "done") return "✓";
  if (item.status === "skipped") return "—";
  return isNext ? "▶" : " ";
}

export function PlanPanel({
  plan,
  onRevert,
  busy = false,
  hidden = false,
}: PlanPanelProps) {
  const [open, setOpen] = useState(false);
  if (
    hidden ||
    plan === null ||
    (plan.items.length === 0 && plan.constraints.length === 0)
  ) {
    return null;
  }

  const nextId = plan.items.find((i) => i.status === "pending")?.id ?? null;
  const remaining = plan.items.filter((i) => i.status === "pending").length;
  const done = plan.items.length - remaining;
  const next = plan.items.find((i) => i.id === nextId) ?? null;

  return (
    <section className="plan-panel" aria-label="할 일">
      <div className="plan-heading">
        <strong>
          할 일 {done}/{plan.items.length}
          {remaining > 0 ? ` · 남은 것 ${remaining}` : " · 남은 것 없음"}
        </strong>
        <IconButton
          label={`할 일 목록 ${open ? "접기" : "펼치기"}`}
          icon={open ? "collapse" : "expand"}
          variant="ghost"
          aria-expanded={open}
          aria-controls="plan-body"
          onClick={() => setOpen(!open)}
        />
      </div>
      {/*
        접혀 있어도 **다음에 할 일 한 줄은 보인다.** 그것이 「AI 가 지금 무엇을 하고
        있는가」에 가장 가까운 사실이고, 펼치지 않고 알 수 있어야 한다.
      */}
      {!open && next !== null && (
        <p className="plan-next">
          <span aria-hidden="true">▶</span> {next.text}
        </p>
      )}
      <div id="plan-body" className="plan-body" hidden={!open}>
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
        <ol className="plan-items">
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
