/**
 * Step 수정 띠 — 무엇을 고치는 중이고 어떻게 끝낼 것인가 (026 US2 · ui-contract §3).
 *
 * `step_edit !== null` 일 때만 나타난다. `RerecordBar` 와 **자리가 같고 말이 다르다.**
 *
 * ## 왜 `RerecordBar` 를 재사용하지 않는가
 *
 * 두 띠가 말하는 것이 정반대이기 때문이다.
 *
 * | | 재녹화 띠 | 이 띠 |
 * |---|---|---|
 * | 대상의 운명 | 확정하면 **사라진다** | 확정해도 **남는다** |
 * | 「만든 것 0개」 | 확정이 잠긴다 | 확정된다 (026 research R5) |
 * | 버리기가 하는 일 | 만든 것을 지운다 | 그에 더해 **대상을 원본으로 되돌린다** |
 *
 * 한 컴포넌트에 담으면 매 문장이 분기가 되고, 그 분기가 프론트에 생긴 두 번째 모드
 * 구현이다. 겉모습이 닮은 것과 하는 일이 같은 것은 다르다.
 *
 * ## 확정 가능 여부는 서버가 판정한다
 *
 * `can_commit` 을 화면이 다시 세지 않는다 — 016 과 같은 규칙이다. 다만 **값의 뜻이
 * 다르다**: 여기서는 만든 것이 없어도 참이다.
 */
import type { StepEditView } from "../../api/client";
import type { ActionId } from "../../lib/actions";
import type { CapabilityMap } from "../../lib/capabilities";
import { stepNumber } from "../../lib/wording";
import { Notice } from "../../ui/Notice";
import { ActionButton } from "./ActionButton";

export interface StepEditBarProps {
  stepEdit: StepEditView;
  capabilities: CapabilityMap;
  /** 대상이 목록에서 몇 번인가. 사용자가 보는 번호(1-기반)다. */
  targetLabel: string;
  /**
   * 026 FR-034 — **지금까지 바뀐 항목들** (사람이 읽는 이름).
   *
   * 무엇이 바뀌었는지 모르면 확정할지 버릴지 판단할 수 없다. 비어 있으면 아직 아무것도
   * 바뀌지 않았다는 뜻이며, 그 사실도 말해야 한다 — 「AI 에게 물어만 보고 그만두기」가
   * 정상 경로이기 때문이다 (research R5).
   *
   * **계산은 화면이 한다.** 서버가 하면 「어떤 필드가 바뀐 것인가」의 정의가 서버
   * 계약에 굳는다 (data-model §5).
   */
  changed: string[];
  onCommit: () => void;
  onDiscard: () => void;
  onRemedy?: (action: ActionId) => void;
}

export function StepEditBar({
  stepEdit,
  capabilities,
  targetLabel,
  changed,
  onCommit,
  onDiscard,
  onRemedy,
}: StepEditBarProps) {
  const made = stepEdit.created_step_ids.length;

  return (
    <Notice tone="ai" aria-label="Step 수정" layout="w-full">
      {/*
        **「고치는 중」이라고 말한다.** 재녹화 띠의 「교체 중」과 한 낱말이 다르고, 그
        한 낱말이 대상의 운명을 가른다 (FR-031).
      */}
      <span className="font-semibold">고치는 중 — {targetLabel}</span>
      {/*
        026 FR-034 — **무엇이 바뀌었는지 말한다.**

        이것이 없으면 사용자는 확정할지 버릴지를 목록을 눈으로 훑어 판단해야 한다.
        값이 아니라 **항목 이름**만 말하는 이유는, 값까지 보이면 띠가 목록이 되기
        때문이다 — 값은 바로 아래 Step 행에 이미 그려져 있다.
      */}
      <span className="text-ink-3" data-cell="step-edit-changes">
        {changed.length === 0 ? "아직 바뀐 것이 없습니다" : `바뀐 것 — ${changed.join(" · ")}`}
      </span>
      <span className="text-ink-3">
        {made === 0
          ? "이 Step 은 확정해도 남습니다"
          : `고치면서 새로 만든 것 ${made}개`}
      </span>

      <div className="ml-auto flex items-center gap-s2">
        <ActionButton
          action="ai.stepEditCommit"
          capability={capabilities["ai.stepEditCommit"]}
          emphasis
          onRun={onCommit}
          onRemedy={onRemedy}
        />
        <ActionButton
          action="ai.stepEditDiscard"
          capability={capabilities["ai.stepEditDiscard"]}
          onRun={onDiscard}
          onRemedy={onRemedy}
        />
      </div>
    </Notice>
  );
}

/**
 * 수정 대상을 사람이 읽는 문장으로 (`Step 5`).
 *
 * **번호는 지금 목록에서 센다** — `rangeLabelOf` 와 같은 이유다. 대상은 id 로 잡혀
 * 있고 번호는 앞에 Step 이 들어올 때마다 밀리므로, 받은 번호를 들고 있으면 곧 거짓이
 * 된다.
 *
 * 목록에 없으면 (AI 가 지웠다) 그 사실을 말한다 — 버리기로 되돌아온다.
 */
export function targetLabelOf(targetStepId: string, allStepIds: string[]): string {
  const index = allStepIds.indexOf(targetStepId);
  if (index < 0) return `${targetStepId} (지금 목록에 없음)`;
  // **번호 조립은 `wording.ts` 한 곳에서만 한다** (FR-138 · `StepNumberConsistency`).
  return stepNumber(index);
}
