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
 * 인라인 style 값은 `docs/design/Main.dc.html` 의 74px 띠 버튼에서 그대로 옮겼다 —
 * 축약·토큰 치환을 하지 않는다 (DC-001).
 */
import { useId, type ReactNode } from "react";

import type { ActionId } from "../../lib/actions";
import type { CapabilityState } from "../../lib/capabilities";
import { ACTION_LABEL } from "../../lib/wording";

const INK = "#14171C";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

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
   * - `true`  — 확정 디자인의 노란 배경(`#F5D000`). 그 국면의 주 조작
   * - `false` — 보통. 종이 배경 + 그림자
   * - `"quiet"` — **강조를 뺀다** (005 FR-147 · U-08). 끝난 실행의 「닫기」처럼 파괴적
   *   이거나 되돌리기 어려운 조작이 화면에서 가장 눈에 띄는 컨트롤이 되지 않게 한다
   */
  emphasis?: boolean | "quiet";
  icon?: ReactNode;
  /** 확정 디자인의 46px 버튼이 아닌 작은 자리(Step 행 안 등) */
  compact?: boolean;
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
}: ActionButtonProps) {
  const reasonId = useId();

  // 「해당 없음」은 그리지 않는다. 근거는 표가 갖고 있고 검사가 그것을 센다 (§4-2).
  if (capability.kind === "not_applicable") return null;

  const disabled = capability.kind === "disabled";
  const text = label ?? ACTION_LABEL[action];

  const base = {
    display: "inline-flex",
    alignItems: "center",
    gap: compact ? "6px" : "9px",
    height: compact ? "26px" : "32px",
    padding: compact ? "0 10px" : "0 18px",
    border: `1px solid ${INK}`,
    borderRadius: "3px",
    font: compact ? `600 12px/1 ${SANS}` : `600 15px/1 ${SANS}`,
    color: INK,
  } as const;

  const quiet = emphasis === "quiet";
  const live = {
    ...base,
    background: emphasis === true ? INK : "#FFFFFF",
    border: `1px solid ${emphasis === true ? INK : quiet ? "#CBD0D8" : "#CBD0D8"}`,
    borderRadius: "3px",
    color: emphasis === true ? "#FFFFFF" : quiet ? "#4A515C" : INK,
    boxShadow: compact || quiet ? "none" : "0 1px 2px rgba(20, 23, 28, 0.07)",
    cursor: "pointer",
  } as const;

  /**
   * 비활성의 모양 (008「계기판」 · Language.dc.html §05).
   *
   * **감추지 않는다** (SC-004). 바뀐 것은 무게다 — v1 은 채운 상자(`#EAEDF2`)라 활성
   * 조작과 시각적 무게가 비슷했고, 이유가 버튼 **아래** 줄로 붙어 층을 하나 더 만들었다.
   * 48px 국면 띠 안에서 그 층은 아래 영역을 덮었다.
   *
   * 점선 + 그림자 없음 + 사유는 같은 줄. 층이 늘지 않는다.
   */
  const dead = {
    ...base,
    background: "transparent",
    border: "1px dashed #CBD0D8",
    boxShadow: "none",
    color: "#6E757F",
    fontWeight: 500,
    cursor: "not-allowed",
  } as const;

  const button = (
    <button
      type="button"
      data-action={action}
      disabled={disabled}
      aria-describedby={disabled ? reasonId : undefined}
      onClick={disabled ? undefined : onRun}
      style={disabled ? dead : live}
    >
      {icon}
      {text}
    </button>
  );

  if (!disabled) return button;

  return (
    <span style={{ display: "inline-flex", flexDirection: "row", gap: 8, alignItems: "center" }}>
      {button}
      {/*
        이유는 **시각적으로만** 두지 않는다. `aria-describedby` 로 버튼에 묶여 있어야
        비활성 이유가 보조 기술에 전달된다 (ui-contract §7).
      */}
      <span
        id={reasonId}
        data-disabled-reason={action}
        style={{ font: `400 11px/1.35 ${SANS}`, color: "#6E757F", maxWidth: 260 }}
      >
        {capability.reason}
        {capability.remedy !== null && onRemedy !== undefined && (
          <>
            {" "}
            <button
              type="button"
              data-remedy-for={action}
              onClick={() => onRemedy(capability.remedy!.action)}
              style={{
                border: "none",
                borderRadius: "3px",
                background: "transparent",
                boxShadow: "none",
                padding: 0,
                font: `600 12px/1.4 ${SANS}`,
                color: "#5732B0",
                textDecoration: "underline",
                cursor: "pointer",
              }}
            >
              {ACTION_LABEL[capability.remedy.action]}
            </button>
          </>
        )}
      </span>
    </span>
  );
}
