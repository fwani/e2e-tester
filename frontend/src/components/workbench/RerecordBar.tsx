/**
 * 재녹화 띠 — 무엇을 교체 중이고 어떻게 끝낼 것인가 (016 US2 · contracts/ui-contract.md §3-2).
 *
 * `rerecord !== null` 일 때만 나타난다.
 *
 * ## 확정 가능 여부는 서버가 판정한다
 *
 * `can_commit` 을 화면이 다시 세지 않는다. 「만든 Step 이 1개 이상인가」를 여기서
 * 판단하면 서버와 갈리고, 갈리면 활성으로 그린 버튼이 눌린 뒤 거절된다 — 005 U-01 이
 * 그 형태였다.
 *
 * ## 버리기는 만든 것이 없어도 활성이다
 *
 * 확정과 다른 점이다. 아무것도 만들지 않은 채 그만두는 것은 **정상**이고, 그때 버리기는
 * 세션을 도착점으로 되돌려 다시 시도할 수 있게 한다 (FR-031).
 *
 * **세션을 끝내지 않는다** (FR-031a). 끝내는 조작은 기존 「중지」이며 이 띠에 두지
 * 않는다 — 둘이 나란히 있으면 사용자는 누를 때마다 차이를 확인해야 한다.
 */
import type { RerecordView } from "../../api/client";
import type { ActionId } from "../../lib/actions";
import type { CapabilityMap } from "../../lib/capabilities";
import { Notice } from "../../ui/Notice";
import { ActionButton } from "./ActionButton";

export interface RerecordBarProps {
  rerecord: RerecordView;
  capabilities: CapabilityMap;
  /** 교체 구간이 목록에서 몇 번부터 몇 번인가. 사용자가 보는 번호(1-기반)다. */
  rangeLabel: string;
  onCommit: () => void;
  onDiscard: () => void;
  onRemedy?: (action: ActionId) => void;
}

export function RerecordBar({
  rerecord,
  capabilities,
  rangeLabel,
  onCommit,
  onDiscard,
  onRemedy,
}: RerecordBarProps) {
  const made = rerecord.created_step_ids.length;

  return (
    <Notice tone="ai" aria-label="구간 재녹화" layout="w-full">
      <span className="font-semibold">교체 중 — {rangeLabel}</span>
      <span className="text-ink-3">
        {made === 0 ? "아직 만든 Step 이 없습니다" : `새로 만든 것 ${made}개`}
      </span>

      <div className="ml-auto flex items-center gap-s2">
        <ActionButton
          action="ai.rerecordCommit"
          capability={capabilities["ai.rerecordCommit"]}
          emphasis
          onRun={onCommit}
          onRemedy={onRemedy}
        />
        <ActionButton
          action="ai.rerecordDiscard"
          capability={capabilities["ai.rerecordDiscard"]}
          onRun={onDiscard}
          onRemedy={onRemedy}
        />
      </div>
    </Notice>
  );
}

/**
 * 교체 구간을 사람이 읽는 문장으로 (`Step 5~9 (5개)`).
 *
 * **번호는 지금 목록에서 센다.** 구간은 id 로 잡혀 있고(data-model §1-1) 번호는 앞
 * 구간에 Step 이 들어올 때마다 밀리므로, 서버가 준 번호를 들고 있으면 곧 거짓이 된다.
 */
export function rangeLabelOf(rangeStepIds: string[], allStepIds: string[]): string {
  const positions = rangeStepIds
    .map((id) => allStepIds.indexOf(id))
    .filter((i) => i >= 0)
    .sort((a, b) => a - b);

  const head = positions[0];
  const tail = positions[positions.length - 1];
  if (head === undefined || tail === undefined) return "교체 대상을 찾을 수 없습니다";
  const first = head + 1;
  const last = tail + 1;
  const span = first === last ? `Step ${first}` : `Step ${first}~${last}`;
  return `${span} (${positions.length}개)`;
}
