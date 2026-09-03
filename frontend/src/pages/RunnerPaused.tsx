/**
 * 일시정지 화면 (T102). `RunnerPaused.dc.html` 이식.
 *
 * **구성 방식에 대한 결정**: 별도 화면으로 갈라 놓지 않고 `Runner` 가 일시정지 상태에서
 * 끼워 넣는 패널로 만들었다. 디자인의 좌측(미러)·우측(Step 목록)은 실행 중과 동일하고
 * 달라지는 것은 ① 상단 안내 배너 ② 우측 액션 패널 두 곳뿐이다. 화면을 복제하면 미러·탭·
 * Step 목록 배선이 두 벌이 되어 한쪽만 고치는 실수가 생긴다.
 *
 * FR-033: 브라우저 세션과 화면 상태를 유지하고 있음을 **명시한다.** 이 배너가 사용자가
 * "내 로그인 상태가 살아 있다" 를 확인하는 유일한 수단이다.
 * FR-034: 일시정지 위치는 `StepList` 가 구분선으로 그린다.
 */
import { EditWarningBanner } from "../components/EditWarningBanner";
import { PauseActions, type PauseActionsProps } from "../components/PauseActions";

export interface RunnerPausedProps extends Omit<PauseActionsProps, "busy" | "tab"> {
  /** 멈춘 지점. "step N 이후 정지" 표기에 쓴다. */
  currentStepIndex: number;
  totalSteps: number;
  editWarnings: string[];
  onDismissWarnings?: () => void;
  busy?: boolean;
  tab?: number;
}

/** 상단 배너 — FR-033 의 사용자 향 표현. */
export function PausedBanner({
  currentStepIndex,
  totalSteps,
}: {
  currentStepIndex: number;
  totalSteps: number;
}) {
  const after = Math.max(0, Math.min(currentStepIndex, totalSteps));
  return (
    <div
      role="status"
      className="row"
      style={{
        gap: 10,
        padding: "10px 14px",
        background: "var(--warn)",
        borderBottom: "3px solid var(--ink)",
        fontWeight: 700,
        fontSize: 13,
      }}
    >
      <span aria-hidden>⏸</span>
      <span>
        일시정지 — 브라우저 세션과 화면 상태를 그대로 유지하고 있습니다.
      </span>
      <span className="spacer" />
      <span className="mono" style={{ fontWeight: 400 }}>
        {after === 0
          ? "첫 Step 이전에서 정지"
          : `step ${String(after).padStart(2, "0")} 이후 정지`}
      </span>
    </div>
  );
}

/** 우측 액션 패널 — 경고 배너 + "지금 할 수 있는 것". */
export function RunnerPaused({
  currentStepIndex,
  totalSteps,
  editWarnings,
  onDismissWarnings,
  busy = false,
  tab,
  ...actions
}: RunnerPausedProps) {
  return (
    <div
      style={{
        borderTop: "3px solid var(--ink)",
        background: "var(--surface-soft)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <EditWarningBanner warnings={editWarnings} onDismiss={onDismissWarnings} />
      <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
        편집은 테스트 정의만 바꿉니다. 브라우저 화면은 되돌아가지 않습니다 (FR-040a).
        전체 {totalSteps}개 중 {Math.min(currentStepIndex, totalSteps)}개가 실행됐습니다.
      </p>
      <PauseActions busy={busy} tab={tab} {...actions} />
    </div>
  );
}
