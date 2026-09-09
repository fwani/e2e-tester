/**
 * Step 행의 조작 — 칸 5 (009 FR-298~FR-304 · 계약 §3-2).
 *
 * ## 왜 행에 있는가
 *
 * 007 이 Step 조작을 팔레트 한 자리로 모았고, 그 판단은 「한 조작에 한 자리」를 세우기
 * 위해 옳았다. 다만 **대상이 행인 조작까지 팔레트로 보내면 왕복이 생긴다** — 「먼저 Step
 * 을 고르세요 → 화면 아래로 내려가 누르세요」다 (009 관찰 M-07).
 *
 * 그 왕복이 만든 것: 편집 화면에서 Step 하나를 세 칸 내리는 데 **여섯 번**이 걸렸다.
 * 아래로 옮기기가 없어 아래 Step 세 개를 각각 고르고 각각 올려야 했다 (M-05).
 *
 * ## 순서가 고정이다
 *
 *   [위로 ↑] [아래로 ↓] [이 앞에 추가 +] [지우기 ×]
 *
 * 국면이 이 순서를 바꾸지 않는다. 자리가 흔들리면 근육 기억이 서지 않는다.
 *
 * ## hover 로 드러내지 않는다
 *
 * 항상 보인다. 보이지 않는 조작은 없는 조작이다 (FR-234) — `rowActions` 자리가 이미
 * 열려 있는데도 아무도 쓰지 않은 것(M-08)이 그 증거다.
 */
import type { ActionId } from "../../lib/actions";
import type { CapabilityMap, CapabilityState } from "../../lib/capabilities";
import { ACTION_LABEL } from "../../lib/wording";

/** 칸 5 의 조작과 그 표식. 라벨은 접근 가능한 이름이 갖는다. */
const OPS: { action: ActionId; mark: string; danger?: boolean }[] = [
  { action: "step.moveUp", mark: "↑" },
  { action: "step.moveDown", mark: "↓" },
  { action: "step.insertManual", mark: "+" },
  { action: "step.delete", mark: "×", danger: true },
];

/** 끝단에서 그 방향이 잠기는 이유 (FR-300). **해소 방법을 달지 않는다.** */
export const AT_TOP = "맨 위입니다";
export const AT_BOTTOM = "맨 아래입니다";

export interface StepRowOpsProps {
  /** 이 행이 목록에서 몇 번째인가 — 끝단 판정에 쓴다 */
  index: number;
  total: number;
  /** 그 Step 의 이름. 접근 가능한 이름에 들어간다 (FR-303) */
  label: string;
  capabilities: CapabilityMap;
  busy?: boolean;
  onRun: (action: ActionId, index: number) => void;
}

export function StepRowOps({
  index,
  total,
  label,
  capabilities,
  busy = false,
  onRun,
}: StepRowOpsProps) {
  /*
    표는 **국면**을 본다. 「첫 행이다」는 국면이 아니므로 표에 담을 수 없고, 담지 않으면
    갈 곳이 없는 방향이 활성으로 남아 눌러도 아무 일이 없다 (계약 §2-3).

    `EditView.narrowByPick` 과 같은 형태다 — 표를 대신하지 않고 그 결과를 좁힌다.
  */
  const narrow = (action: ActionId): CapabilityState => {
    const base = capabilities[action];
    if (base.kind !== "enabled") return base;
    if (action === "step.moveUp" && index === 0) {
      // `keep` — 갈 곳이 없다는 사실은 그 자리에서 말한다 (행 조작은 자리가 고정이다).
      return { kind: "disabled", reason: AT_TOP, remedy: null, visibility: "keep" };
    }
    if (action === "step.moveDown" && index >= total - 1) {
      return { kind: "disabled", reason: AT_BOTTOM, remedy: null, visibility: "keep" };
    }
    return base;
  };

  return (
    <>
      {OPS.map(({ action, mark, danger }) => {
        const state = narrow(action);
        // 「해당 없음」인 조작은 그리지 않는다 — 근거 있는 부재다 (ui-contract §4-2).
        if (state.kind === "not_applicable") return null;
        const disabled = state.kind !== "enabled" || busy;
        const why = state.kind === "disabled" ? ` — ${state.reason}` : "";
        return (
          <button
            key={action}
            type="button"
            data-row-action={action}
            className={`op${danger === true ? " danger" : ""}${disabled ? " off" : ""}`}
            /*
              FR-303 — 접근 가능한 이름의 형태를 지킨다. 기존 「〈이름〉 위로」·「〈이름〉
              아래로」가 그 형태이며, 키보드만 쓰는 사용자가 목록을 훑을 때 어느 Step 의
              어느 방향인지가 이름만으로 구별되어야 한다.
            */
            aria-label={`${label} ${ACTION_LABEL[action]}${why}`}
            aria-disabled={disabled ? "true" : undefined}
            disabled={disabled}
            title={`${ACTION_LABEL[action]}${why}`}
            onClick={(e) => {
              // 행 전체가 지목 대상이므로 조작이 지목까지 일으키지 않게 막는다.
              e.stopPropagation();
              onRun(action, index);
            }}
          >
            {mark}
          </button>
        );
      })}
    </>
  );
}


/**
 * 지우기 확인 — **행 안에서** 묻는다 (009 FR-302).
 *
 * 지금 Step 삭제에는 확인이 없었다. 확인 상태를 가진 화면은 테스트 목록의 테스트 삭제뿐
 * 이고(`pages/TestList.tsx`), 그 방식을 행에 적용한다.
 *
 * **겹침 대화상자를 쓰지 않는다.** 행 조작의 결과를 행이 아닌 곳에서 확인하면 대상이
 * 무엇이었는지 다시 확인해야 한다 — 지우려던 것이 이 행이라는 사실이 화면에서 사라진다.
 */
export function ConfirmDelete({
  label,
  onConfirm,
  onCancel,
}: {
  label: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <>
      <span className="why" role="status" style={{ whiteSpace: "nowrap" }}>
        지울까요?
      </span>
      <button
        type="button"
        data-row-action="step.delete.confirm"
        className="op danger"
        aria-label={`${label} 지우기 확인`}
        onClick={(e) => {
          e.stopPropagation();
          onConfirm();
        }}
      >
        ✓
      </button>
      <button
        type="button"
        data-row-action="step.delete.cancel"
        className="op"
        aria-label={`${label} 지우기 취소`}
        onClick={(e) => {
          e.stopPropagation();
          onCancel();
        }}
      >
        ↩
      </button>
    </>
  );
}
