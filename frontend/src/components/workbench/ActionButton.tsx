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
 * ## 2026-09-09 — 1번이 좁아졌다 (사용자 결정)
 *
 * 위 1번은 예외 없는 규칙이었고, 그것을 한 줄 국면 띠에 평면으로 펼친 결과가 보고됐다:
 * 검토 국면에서 조작 자리 24개 중 14개가 비활성이었고 「처음부터 실행」이 버튼 하나 +
 * 해소 링크 둘로 한 띠에 세 번 나왔다.
 *
 * 이제 1번은 **`visibility: "keep"` 인 비활성**에만 적용된다 — 사용자가 지금 이 화면에서
 * 곧바로 해소할 수 있는 전제(이름 미입력·Step 미선택·요청 진행 중·저장할 것 없음)다.
 * `"hide"` 인 것은 「이 상태의 조작이 아니다」이며 그리지 않는다.
 *
 * **판정은 여기 없다.** 어느 이유가 어느 쪽인지는 `capabilities.ts` 의 `REASON_VISIBILITY`
 * 하나가 정한다 — 이 컴포넌트가 이유 문구를 보고 판단하면 그 판단이 표 밖으로 새고,
 * 새는 순간이 UC-000 이 없애려던 상태다.
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


import { Button, type ButtonVariant } from "../../ui/Button";
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
  // 「이 상태의 조작이 아니다」도 그리지 않는다 (2026-09-09). 판정은 표가 했다.
  if (capability.kind === "disabled" && capability.visibility === "hide") return null;

  const disabled = capability.kind === "disabled";
  const text = label ?? ACTION_LABEL[action];

  // 정본 `.btn` 수식자 이름을 그대로 쓰던 자리다. 이제 `ui/Button` 의 variant 를 고른다 —
  // 수식 없음은 `""` 가 아니라 `"default"` 다 (015 T016).
  const variant: ButtonVariant = disabled
    ? "off"
    : emphasis === true
      ? "primary"
      : danger
        ? "danger"
        : emphasis === "quiet"
          ? "quiet"
          : "default";

  const button = (
    <Button
      type="button"
      data-action={action}
      disabled={disabled}
      aria-describedby={disabled ? reasonId : undefined}
      onClick={disabled ? undefined : onRun}
      size={compact ? "sm" : "md"}
      variant={variant}
      /*
        **버튼은 줄지 않는다.** 국면 띠는 한 줄이고, 줄 폭이 모자랄 때 눌러야 할 것이
        먼저 찌그러지면 안 된다 — 줄어드는 것은 이유 문구 쪽이다 (아래).
      */
      layout="flex-none"
    >
      {icon}
      {text}
    </Button>
  );

  if (!disabled) return button;

  /*
    **이유는 자리를 무한히 쓰지 않는다** (사용자 보고 · 2026-09-09 — 국면 띠가 가로로
    터짐).

    한 줄짜리 국면 띠에서 여러 조작이 동시에 잠기면 이유 문구가 나란히 붙어 띠를 창 밖
    으로 밀어낸다. 실제로 실행 중 네 조작이 한꺼번에 잠기자 띠가 두 배 폭으로 늘어났고,
    같은 줄의 결말 요약은 폭 0 으로 찌그러져 **한 글자씩 세로로 쌓였다.**

    그래서 보이는 문구는 줄어들고 넘치면 말줄임한다. **버리는 것이 아니다** —
    `aria-describedby` 로 버튼에 묶인 전체 문장은 그대로이고 (ui-contract §7), `title`
    이 마우스에도 전체를 준다. 해소 수단은 **줄지 않는다**: 빠져나갈 길이 말줄임에
    잘리면 이유를 읽고도 할 수 있는 일이 없다 (ui-contract §4-1 의 3번).
  */
  return (
    <span className="flex items-center gap-s2 min-w-0">
      {button}
      {/*
        이유는 **시각적으로만** 두지 않는다. `aria-describedby` 로 버튼에 묶여 있어야
        비활성 이유가 보조 기술에 전달된다 (ui-contract §7).
      */}
      <span
        id={reasonId}
        data-disabled-reason={action}
        className="font-sans text-[11px] leading-[1.4] text-ink-3 inline-flex items-center gap-s1 flex-initial min-w-0 max-w-[260px]"
      >
        <span
          data-disabled-reason-text
          title={capability.reason}
          className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap"
        >
          {capability.reason}
        </span>
        {capability.remedy !== null && onRemedy !== undefined && (
          <button
            type="button"
            data-remedy-for={action}
            className="border-0 p-0 h-auto bg-transparent shadow-none text-run font-sans text-[12px] font-semibold leading-[1.4] underline cursor-pointer flex-none"
            onClick={() => onRemedy(capability.remedy!.action)}
          >
            {ACTION_LABEL[capability.remedy.action]}
          </button>
        )}
      </span>
    </span>
  );
}
