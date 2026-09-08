/**
 * 조작 하나를 그리는 버튼 (007 T017 · contracts/ui-contract.md §4-1).
 *
 * **`CapabilityState` 를 받아 그린다.** 스스로 판단하지 않는다 — 판단은
 * `lib/capabilities.ts` 의 표가 한다 (UC-000).
 *
 * ○ 인 조작은 셋을 **모두** 갖는다 (FR-234).
 *
 * 1. **같은 자리에 그린다.** 감추지 않는다 — 감추면 사용자는 자기가 잘못 들어온 줄 안다
 * 2. **이유를 붙인다.** 왜 지금 안 되는지
 * 3. **해소 방법을 붙인다.** 있을 때만이며, **이 화면에 실제로 있는 조작**을 가리킨다
 *
 * 3번이 006 E-03 의 수정이다. "실행을 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로
 * 가는 버튼을 주지 않은 것이 그 결함이었다.
 *
 * ## 2026-09-08 (008)
 *
 * 이전 판은 확정 디자인의 인라인 값을 전사했고, 주 조작의 배경으로 **v1 의 노란색**
 * (`#F5D000`)을 주석에 남긴 채 잉크 채움을 쓰고 있었다. 이제 형태는 정본의 `.btn` 과
 * 변형 넷이 갖는다 — `primary`(잉크 채움) · `danger` · `off`(점선) · `sm`.
 *
 * **비활성의 모양은 v2 에서 바뀌었다** (Language.dc.html §05). 감추지 않는 것은 그대로이고
 * (SC-004), 무게가 내려갔다: v1 은 채운 상자라 활성 조작과 시각적 무게가 비슷했고 이유가
 * 버튼 **아래** 줄로 붙어 48px 띠 안에서 아래 영역을 덮었다. 점선 + 그림자 없음 + 사유는
 * 같은 줄. 층이 늘지 않는다.
 */
import { useId, type ReactNode } from "react";

import type { ActionId } from "../../lib/actions";
import type { CapabilityState } from "../../lib/capabilities";
import { ACTION_LABEL } from "../../lib/wording";

export interface ActionButtonProps {
  action: ActionId;
  capability: CapabilityState;
  onRun?: () => void;
  /** 해소 방법 버튼을 눌렀을 때. 그 조작을 실제로 실행한다 */
  onRemedy?: (action: ActionId) => void;
  /** 라벨을 상황에 맞게 바꿀 때. 없으면 `ACTION_LABEL` 을 쓴다 (005 FR-147·FR-149) */
  label?: string;
  /**
   * 강조 단계.
   *
   * - `true`  — 잉크 채움(`.btn.primary`). **그 국면의 주 조작 하나뿐이다** (FR-269)
   * - `false` — 보통. 정본의 기본 조작
   * - `"quiet"` — **강조를 뺀다** (005 FR-147 · U-08). 끝난 실행의 「닫기」처럼 파괴적
   *   이거나 되돌리기 어려운 조작이 화면에서 가장 눈에 띄는 컨트롤이 되지 않게 한다
   */
  emphasis?: boolean | "quiet";
  icon?: ReactNode;
  /** 작은 자리(Step 행 안 등)의 26px 조작 */
  compact?: boolean;
  /** 되돌리기 어려운 조작 — 중지·버리기 (`.btn.danger`) */
  danger?: boolean;
}

export function ActionButton({
  action,
  capability,
  onRun,
  onRemedy,
  label,
  emphasis = false,
  icon,
  compact = false,
  danger = false,
}: ActionButtonProps) {
  const reasonId = useId();

  // 「해당 없음」은 그리지 않는다. 근거는 표가 갖고 있고 검사가 그것을 센다 (§4-2).
  if (capability.kind === "not_applicable") return null;

  const disabled = capability.kind === "disabled";
  const text = label ?? ACTION_LABEL[action];

  const variant = disabled
    ? "off"
    : emphasis === true
      ? "primary"
      : danger
        ? "danger"
        : emphasis === "quiet"
          ? "quiet"
          : "";

  const button = (
    <button
      type="button"
      data-action={action}
      disabled={disabled}
      aria-describedby={disabled ? reasonId : undefined}
      onClick={disabled ? undefined : onRun}
      className={`btn ${compact ? "sm " : ""}${variant}`.trimEnd()}
    >
      {icon}
      {text}
    </button>
  );

  if (!disabled) return button;

  return (
    <span className="row" style={{ gap: 8 }}>
      {button}
      {/*
        이유는 **시각적으로만** 두지 않는다. `aria-describedby` 로 버튼에 묶여 있어야
        비활성 이유가 보조 기술에 전달된다 (ui-contract §7).
      */}
      <span id={reasonId} data-disabled-reason={action} className="why" style={{ maxWidth: 260 }}>
        {capability.reason}
        {capability.remedy !== null && onRemedy !== undefined && (
          <>
            {" "}
            <button
              type="button"
              data-remedy-for={action}
              className="textlink"
              onClick={() => onRemedy(capability.remedy!.action)}
            >
              {ACTION_LABEL[capability.remedy.action]}
            </button>
          </>
        )}
      </span>
    </span>
  );
}
