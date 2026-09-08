/**
 * 화면 어휘의 유일한 출처 (005 T011 · FR-138·FR-141).
 *
 * 리포트 22건 중 12건 이상이 표시·문구 문제였고, 그것들은 개별 화면의 취향이 아니라
 * **한 계약이 없어서** 생긴 것이었다 (contracts/ui-contract.md).
 *
 * - 결말을 화면마다 다른 말로 불렀다 — 배지는 「완료」/「실패」, 요약 바는 `PASS`/`FAIL`,
 *   목록 칩은 `PASS`/`FAIL`, 목록 배너는 「완료」/「실패」/「실행 중」/「검토 중」 (U-20)
 * - Step 표기가 "Step"·"step"·"단계"로 섞였다 (U-20)
 * - 8곳이 `index + 1` 을 각자 하고 **한 곳만 빠뜨려** 목록의 실패 Step 번호가 1 작았다
 *   (U-07). 한 줄 고치면 증상은 사라지지만 같은 실수가 다시 난다
 *
 * 그래서 화면은 문구를 직접 만들지 않고 여기서 받는다.
 */

import type { Outcome, RunScope, StepOutcome } from "../types/generated/run-result";
import type { ActionId } from "./actions";
import type { Phase } from "./phase";
import type { StepOutcome as WorkbenchStepOutcome } from "../components/workbench/model";

/** 사용자에게 보이는 결말 문장 (ui-contract §1). */
export function outcomeLabel(outcome: Outcome | null | undefined): string {
  switch (outcome) {
    case "pass":
      return "통과";
    case "fail":
      return "실패";
    case "stopped":
      return "중지";
    case "partial_pass":
      return "부분 성공";
    default:
      // 알 수 없는 값은 **실패로 취급한다** (data-model.md §1 보수적 기본값).
      // 통과로 표시하면 결말이 늘 때마다 화면이 조용히 성공을 말한다.
      return outcome == null ? "—" : "실패";
  }
}

/** 칩에 쓰는 기술 라벨. 확정 디자인이 대문자 칩을 쓰므로 유지한다 (ui-contract §1-2). */
export function outcomeChip(outcome: Outcome | null | undefined): string {
  switch (outcome) {
    case "pass":
      return "PASS";
    case "fail":
      return "FAIL";
    case "stopped":
      return "STOPPED";
    case "partial_pass":
      return "PARTIAL";
    default:
      return outcome == null ? "—" : "FAIL";
  }
}

/** 칩·배지의 색 역할. 색만으로 구분하지 않으므로 라벨과 **함께** 쓴다 (ui-contract §1-4). */
export type OutcomeTone = "success" | "danger" | "neutral" | "warn" | "unknown";

export function outcomeTone(outcome: Outcome | null | undefined): OutcomeTone {
  switch (outcome) {
    case "pass":
      return "success";
    case "fail":
      return "danger";
    case "stopped":
      return "neutral";
    case "partial_pass":
      return "warn";
    default:
      return outcome == null ? "unknown" : "danger";
  }
}

/**
 * 실패로 집계하는 결말인가 (FR-131). 중지와 부분 성공은 실패가 **아니다.**
 *
 * 아는 세 값(`pass`·`stopped`·`partial_pass`)만 실패가 아니라고 말한다. 그 밖의 값은
 * 실패로 센다 — `outcomeLabel`·`outcomeChip`·`outcomeTone` 과 같은 보수적 기본값이다
 * (data-model.md §1). 여기만 `=== "fail"` 로 두면 화면이 「실패」라고 쓰고 그 옆에서
 * 실패 집계는 0 이 되는, 자기와 어긋나는 화면이 만들어진다.
 */
export function countsAsFailure(outcome: Outcome | null | undefined): boolean {
  if (outcome == null) return false;
  switch (outcome) {
    case "pass":
    case "stopped":
    case "partial_pass":
      return false;
    default:
      return true;
  }
}

/**
 * 0-기반 인덱스 → 사용자에게 보이는 Step 이름 (FR-138).
 *
 * **이 함수가 변환의 유일한 지점이다.** 저장·API·이벤트의 인덱스는 0-기반이고 그것을
 * 바꾸지 않는다(contracts/rest-api.md §6). 화면이 각자 `+ 1` 을 하면 한 곳이 빠뜨린다 —
 * 그것이 U-07 이었고, 사용자는 목록에서 05 를 보고 결과에서 06 을 봤다.
 */
export function stepLabel(index0: number | null | undefined): string {
  if (index0 == null || index0 < 0) return "Step —";
  return `Step ${String(index0 + 1).padStart(2, "0")}`;
}

/** 번호만 필요한 자리 (예: "01~05"). 같은 변환 규칙을 쓴다. */
export function stepNumber(index0: number | null | undefined): string {
  if (index0 == null || index0 < 0) return "—";
  return String(index0 + 1).padStart(2, "0");
}

/** 건너뛴 구간을 사람 말로 (FR-150). `0..start-1` 을 "01~05" 로 적는다. */
export function skippedRange(startIndex: number): string | null {
  if (startIndex <= 0) return null;
  if (startIndex === 1) return stepNumber(0);
  return `${stepNumber(0)}~${stepNumber(startIndex - 1)}`;
}

/** Step 실행 상태 표시 (ui-contract §3). */
export function stepOutcomeLabel(outcome: StepOutcome | null | undefined): string {
  switch (outcome) {
    case "pass":
      return "통과";
    case "fail":
      return "실패";
    case "skipped":
      return "건너뜀";
    case "not_run":
      return "미실행";
    default:
      return "—";
  }
}

/**
 * 결말 요약 한 문장 (ui-contract §1).
 *
 * **분모는 `attempted`(전체 − 건너뜀)다.** `total` 을 분모로 쓰면 5개를 건너뛴 부분
 * 실행이 `0 / 7` 로 보여, 사용자는 직전 전체 실행(5/7)보다 나빠진 줄 안다 (U-02).
 *
 * 결말이 **앞에 온다** — spec 의 예시는 어순이 다르지만 ui-contract 표를 권위로 삼는다.
 */
export interface RunSummaryInput {
  outcome: Outcome | null | undefined;
  passedCount: number;
  attemptedCount: number;
  totalCount: number;
  totalMs?: number | null;
  scope?: RunScope | null;
  startIndex?: number | null;
  failedStepIndex?: number | null;
  stoppedStepIndex?: number | null;
}

export function runSummary(input: RunSummaryInput): string {
  const parts: string[] = [outcomeLabel(input.outcome)];

  const partial = input.scope === "partial" && (input.startIndex ?? 0) > 0;
  if (partial) {
    const start = input.startIndex ?? 0;
    const end = Math.max(start, input.totalCount - 1);
    parts.push(`부분 실행 ${stepLabel(start)}~${stepNumber(end)}`);
  }

  if (input.outcome === "stopped" && input.stoppedStepIndex != null) {
    parts.push(`${stepLabel(input.stoppedStepIndex)} 에서 중지`);
  } else if (countsAsFailure(input.outcome) && input.failedStepIndex != null) {
    parts.push(`${stepLabel(input.failedStepIndex)} 에서 실패`);
  } else if (input.outcome === "partial_pass" && input.failedStepIndex != null) {
    parts.push(`${stepLabel(input.failedStepIndex)} 건너뜀`);
  }

  // 분모는 실행 대상 수다. 0 이면 아무것도 돌지 않은 것이므로 비율을 적지 않는다 —
  // `0 / 0` 은 정보가 아니라 잡음이다.
  const denominator = input.attemptedCount > 0 ? input.attemptedCount : input.totalCount;
  if (denominator > 0) {
    parts.push(`${input.passedCount} / ${denominator} 통과`);
  }

  if (partial) {
    const skipped = skippedRange(input.startIndex ?? 0);
    if (skipped) parts.push(`(${skipped} 건너뜀)`);
  }

  if (input.totalMs != null) {
    parts.push(`${(input.totalMs / 1000).toFixed(2)} s`);
  }

  return parts.join(" · ");
}

/**
 * 실행 중 진행 표시 (ui-contract §4).
 *
 * **끝난 실행에서는 쓰지 않는다.** `Step 07 / 07` 은 전부 처리한 것으로 읽히지만 실제로는
 * 실패로 07 이 돌지 않은 경우가 있다 (U-14). 끝난 실행은 `runSummary()` 를 쓴다.
 */
export function progressLabel(currentIndex: number, total: number): string {
  const shown = Math.min(Math.max(currentIndex, 0) + 1, total);
  return `${stepLabel(shown - 1)} / ${String(total).padStart(2, "0")}`;
}

/** 부분 실행을 걸기 전 보조 안내 (FR-150). */
export function partialRunNotice(startIndex: number): string | null {
  const skipped = skippedRange(startIndex);
  if (!skipped) return null;
  return `${skipped} 는 건너뜁니다. 로그인 같은 앞선 상태가 필요하면 「처음부터 실행」을 쓰세요.`;
}

/**
 * `run.from` 의 라벨 (005 FR-149 · 007 FR-235·FR-236). 시작점이 라벨에 드러난다.
 *
 * **0번도 번호로 부른다.** 005 의 `runFromLabel()` 은 0번을 「처음부터 실행」이라고
 * 불렀는데, 통합 화면에는 `run.all`(「처음부터 실행」)이 **같은 자리에 함께** 있다.
 * 0번에서 같은 라벨이 되면 한 라벨이 두 조작을 갖고, 그것이 FR-235 가 금지하는 것이며
 * 005 U-08 이 같은 형태였다. `LabelUniqueness` 검사가 이 성질을 센다.
 */
export function runFromStepLabel(index0: number): string {
  return `${stepLabel(index0)}부터 실행`;
}

/**
 * 부분 실행에서 요소를 찾지 못한 실패의 진단 첫 줄 (FR-153).
 *
 * **규칙 기반 순수 함수다. 언어모델을 부르지 않는다** (헌법 원칙 II).
 *
 * 리포트가 잡은 것은 안내가 **틀린 방향**을 지시한 것이었다 — 로그인 Step 을 건너뛰어
 * 대시보드 버튼이 있을 수 없는 상황인데 "대상 화면이 느릴 수 있습니다 — 실행 속도를
 * '느림'으로 낮추거나 대기 시간을 늘리세요" 라고 말했다. 사용자는 대기 시간을 늘리며
 * 몇 바퀴를 헛돈다 (U-02 관찰 4).
 */
export function partialRunDiagnosis(startIndex: number): string | null {
  const skipped = skippedRange(startIndex);
  if (!skipped) return null;
  return (
    `앞선 Step(${skipped})을 건너뛰었기 때문에 로그인 같은 선행 상태가 없을 수 있습니다. ` +
    `먼저 「처음부터 실행」으로 확인하세요.`
  );
}

// ─── 편집 어휘 (006 T034 · contracts/ui-contract.md §9) ─────────────────────
//
// 화면 파일에 문장을 직접 쓰지 않는다. 005 가 결말 어휘를 여기 모은 것과 같은 이유다 —
// 문구가 화면마다 흩어지면 같은 것을 다른 말로 부르게 되고, 그것을 고칠 때 한 곳을
// 빠뜨린다.
//
// Step 번호는 반드시 위의 `stepLabel()`·`stepNumber()` 를 쓴다. 여기서 다시
// `index + 1` 을 쓰면 U-07(목록의 실패 Step 번호가 1 작았다)이 되살아난다.

/** 편집 진입점 라벨 (FR-175). 「정의 보기」를 대체한다. */
export const EDIT_ENTRY_LABEL = "편집";

/**
 * 저장 버튼 라벨 (FR-195 · 005 FR-156).
 *
 * 저장할 것이 없으면 버튼은 비활성이고, 라벨은 그대로 「변경 저장」이다 — 라벨을 바꾸면
 * 사용자가 무엇을 누를 수 있는지 배운 것이 흔들린다.
 */
export function saveEditsLabel(pendingCount: number, saving: boolean): string {
  if (saving) return "저장 중…";
  return pendingCount > 0 ? `변경 저장 (${pendingCount}건)` : "변경 저장";
}

/**
 * 세션(일시정지·검토) 화면의 저장 라벨 (005 FR-155·FR-156).
 *
 * 편집 화면의 `saveEditsLabel()` 과 **규칙이 다르다** — 세션에는 변경 건수 개념이 없고
 * 처음 저장은 이름을 정하는 일이다. 그래서 함수를 합치지 않고 **같은 자리에 둔다**:
 * 문구가 두 파일에 흩어져 있으면 한쪽을 고칠 때 다른 쪽을 빠뜨린다.
 */
export function sessionSaveLabel(alreadySaved: boolean): string {
  return alreadySaved ? "변경 저장" : "저장";
}

/** 저장 성공 확인줄 (FR-194 · 005 FR-158). 화면을 옮기지 않고 알린다. */
export function editSavedNotice(testName: string): string {
  return `저장했습니다 · ${testName}`;
}

/** 실행 중이어서 편집할 수 없다 (FR-206). 세션 식별자를 넣지 않는다 (005 FR-135). */
export const EDIT_BLOCKED_BY_RUN = "실행 중이어서 편집할 수 없습니다";

/** 그 실행으로 가는 버튼. 005 와 **같은 문구를 재사용한다** (FR-126). */
export const OPEN_RUNNING_SESSION = "실행 중인 세션 보기";

/** 브라우저를 열어 지정한 Step 직전에서 멈춘다 (FR-200). 시작점을 라벨에 박는다. */
export function openBrowserAtStepLabel(index: number): string {
  return `브라우저 열어 ${stepLabel(index)} 에서 멈추기`;
}

/** 저장하지 않은 변경이 있는 상태에서 브라우저를 열려 할 때 (FR-203). */
export const SAVE_THEN_OPEN_BROWSER = "저장하고 열기";
export const SAVE_BEFORE_OPEN_BROWSER =
  "먼저 저장해야 합니다. 저장한 내용으로 브라우저를 엽니다.";

/** 이탈 확인 (FR-208). 건수를 밝힌다 — 무엇을 잃는지 알아야 고를 수 있다. */
export function unsavedLeaveWarning(pendingCount: number): string {
  return `저장하지 않은 변경 ${pendingCount}건이 있습니다`;
}

/** 편집 불가 항목의 문구 (FR-191 · ui-contract §4). 이유 키를 문장으로 바꾼다. */
export function lockedFieldNotice(
  reason: "live_browser_required" | "delete_and_insert_instead" | "record_only",
): string {
  switch (reason) {
    case "live_browser_required":
      return "이 대상은 살아 있는 화면에서만 다시 집을 수 있습니다.";
    case "delete_and_insert_instead":
      return "Step 종류는 바꿀 수 없습니다. 지우고 새로 넣으세요.";
    case "record_only":
      return "기록입니다. 편집 대상이 아닙니다.";
  }
}

/** 민감 참조 값 칸의 안내 (FR-212·FR-213). 평문이 이 화면에 들어올 자리를 만들지 않는다. */
export const SENSITIVE_VALUE_NOTICE =
  "민감 값은 참조로만 다룹니다. 실제 값은 「비밀 값」 화면에서 바꾸세요.";

/** 외부 변경 충돌의 두 선택 (FR-209 · ui-contract §7). 무엇을 버리는지 라벨에 적는다. */
export function staleReloadLabel(pendingCount: number): string {
  return `바뀐 내용으로 다시 읽기 (내 편집 ${pendingCount}건을 버립니다)`;
}

export const STALE_OVERWRITE_LABEL = "내 편집으로 덮어쓰기 (파일의 변경을 버립니다)";

// ─── 세션 화면 어휘 (005 Phase 12 · ui-contract §7·§8·§10) ──────────────────
//
// 재점검(docs/ux/ux-recheck-005.md)이 남긴 U-03·U-04 의 곁가지는 전부 **문구가 화면
// 파일에 박혀 있어서** 생겼다. 배지는 고쳐졌는데 같은 화면의 부제·오버레이가 낡은 말을
// 그대로 했다 — 한 곳을 고치고 다른 곳을 빠뜨리는, 이 사전이 없애려는 그 실수다.

/**
 * 세션 화면의 제목 (FR-134·FR-155 · ui-contract §8 금지 1).
 *
 * **「초안」은 아직 파일이 없는 것에만 붙인다.** 재점검 U-03-a: 저장 경로(T079)는
 * 고쳐졌지만 재실행 세션은 여전히 「TC-001 초안」이었다 — 이 세션에서 저장한 적이 없다는
 * 것(`savedAt === null`)을 "저장된 적 없다" 로 읽었기 때문이다. 둘은 다르다. 저장된
 * 테스트를 재실행하는 세션은 처음부터 파일이 있다.
 */
export function sessionTitle(input: {
  title: string;
  /** 이 세션의 대상이 이미 정의 파일로 존재하는가. 재실행이면 참이다. */
  persisted: boolean;
  /** 이 세션에서 저장한 시각. 없으면 이 세션은 저장을 하지 않았다. */
  savedAt: string | null;
  /** 저장하지 않은 편집이 남아 있는가. */
  hasUnsavedChanges: boolean;
}): string {
  const saved = input.persisted || input.savedAt !== null;
  if (!saved) return `${input.title} 초안`;
  if (input.hasUnsavedChanges) return `${input.title} · 저장하지 않은 변경 있음`;
  return `${input.title} · 저장됨`;
}

/**
 * 일시정지에서 멈춘 지점 (FR-138 · 재점검 N-06).
 *
 * `current_step_index` 는 **다음에 실행할 Step** 이다 (`execution/session.py`). 그것을
 * 그대로 `stepLabel()` 에 넘기면 5개를 녹화하고 멈춘 화면이 「Step 06 이후 정지」라고
 * 말한다 — 존재하지 않는 Step 번호다. 멈춘 지점은 **직전** Step 이다.
 *
 * `stepLabel` 은 옳고 인자가 틀렸던 것이므로, 변환을 다시 쓰지 않고 여기서 인덱스를
 * 옮긴 뒤 같은 함수를 지난다.
 */
export function pausedAfterLabel(nextIndex: number | null | undefined): string {
  const at = (nextIndex ?? 0) - 1;
  if (at < 0) return "첫 Step 실행 전 정지";
  return `${stepLabel(at)} 이후 정지`;
}

/**
 * 미리보기(미러) 상단 안내 (ui-contract §10 · FR-142·FR-146).
 *
 * 재점검 U-04-b: 전이 중과 실행 종료 후에도 「일시정지 · 브라우저 세션과 화면 상태를
 * 그대로 유지하고 있습니다」로 **단정했다.** 전이 중에는 아직 멈추지 않았고, 실행이
 * 끝난 뒤에는 일시정지가 아니다. 같은 화면의 배지는 이미 그 사실을 말하고 있었으므로
 * 한 화면이 두 가지를 주장했다.
 */
export type MirrorNoticePhase =
  | "manipulation"
  | "observation"
  | "pausing"
  | "paused"
  | "finished"
  | "terminated";

export interface MirrorNotice {
  /** 굵은 상태 이름. 배지와 같은 말을 쓴다. */
  title: string;
  /** 그 상태에서 참인 사실. 단정할 수 없으면 단정하지 않는다. */
  detail: string;
}

export function mirrorNotice(phase: MirrorNoticePhase): MirrorNotice | null {
  switch (phase) {
    case "manipulation":
      return {
        title: "실제 브라우저 창에서 조작 중",
        detail: "이 영역은 관찰용이며 조작 대상이 아닙니다.",
      };
    case "pausing":
      return {
        title: "일시정지 중…",
        detail: "현재 Step 이 끝나면 멈춥니다. 아직 실행 중입니다.",
      };
    case "paused":
      return {
        title: "일시정지",
        detail: "브라우저 세션과 화면 상태를 그대로 유지하고 있습니다.",
      };
    case "finished":
      return {
        title: "실행 종료",
        detail: "브라우저 창은 아직 열려 있습니다. 마지막 화면을 표시합니다.",
      };
    case "observation":
      return { title: "읽기 전용", detail: "실행 중인 화면을 관찰합니다" };
    case "terminated":
      return null;
  }
}

/** 프레임을 한 장도 못 받은 미리보기의 안내 (FR-163). */
export function mirrorEmptyMessage(phase: MirrorNoticePhase): string {
  switch (phase) {
    case "observation":
      return "대상 화면이 표시되기를 기다리고 있습니다. 대상 브라우저 창은 이미 열려 있습니다.";
    case "manipulation":
      return "실제 브라우저 창에서 조작하세요. 이 영역은 관찰용입니다.";
    case "pausing":
      return "현재 Step 이 끝나기를 기다리고 있습니다. 멈추면 마지막 화면을 표시합니다.";
    case "paused":
      return "일시정지 중입니다. 마지막 화면을 표시합니다.";
    case "finished":
      return "실행이 끝났습니다. 마지막 화면을 받지 못했습니다.";
    case "terminated":
      return "세션이 종료되어 미러가 중단됐습니다.";
  }
}

/** 멈추기 전에 실행이 끝난 화면의 제목 (FR-146). */
export const FINISHED_WHILE_PAUSING_TITLE = "멈추기 전에 실행이 끝났습니다";

/** 결과 화면으로 가는 버튼. ui-contract §8 의 첫 번째 다음 행동이다. */
export const SHOW_RESULT_DETAIL = "결과 자세히 보기";

/**
 * 실패한 Step 을 건너뛰고 이어가는 별도 조작 (FR-137 · ui-contract §6-5).
 *
 * 「계속하기」와 **다른 버튼이어야 한다.** 같은 버튼이 실패를 조용히 지나가던 것이
 * U-05 였다. 라벨에 "건너뛰고" 를 박아 무엇을 포기하는지 누르기 전에 알게 한다.
 */
export const RESUME_SKIPPING_FAILURE = "실패한 Step 건너뛰고 계속";

/** 그 버튼 옆 보조 문구 (quickstart §3 S3-7). 결말이 달라진다는 사실을 미리 말한다. */
export function skipFailureNotice(failedIndex: number): string {
  return (
    `${stepLabel(failedIndex)} 을 건너뛰고 다음 Step 부터 이어갑니다. ` +
    `그 Step 에 걸려 있던 화면 상태가 없으므로 뒤따르는 Step 도 실패할 수 있고, ` +
    `이 실행의 결말은 「${outcomeLabel("partial_pass")}」이 됩니다.`
  );
}

/* ─── 007 통합 작업 화면 (T013 · contracts/ui-contract.md §5) ────────────────
 *
 * 국면 이름 · 조작 라벨 · 비활성 이유 · 해소 방법을 여기 둔다. 컴포넌트에 문자열
 * 리터럴을 두지 않는다.
 *
 * **왜 문구까지 한 곳인가.** 007 이 고치는 것 중 하나가 "같은 조작이 국면마다 다른
 * 라벨을 갖는" 것이다 — 실행 진입이 목록에서는 「실행」, 편집에서는 「▶ 실행」,
 * 결과에서는 「처음부터 실행」이었다 (S-07). 문구가 화면에 흩어져 있으면 그 어긋남을
 * 검사로 잡을 수 없다.
 */


/** 국면 이름. 화면 상단의 국면 표시에 그대로 쓴다 (FR-219). */
export const PHASE_LABEL: Record<Phase, string> = {
  composing: "만들기",
  recording: "녹화 중",
  ai_authoring: "AI 작성 중",
  takeover: "사람이 직접 조작",
  running: "실행 중",
  paused: "일시정지",
  result: "결과",
  editing: "편집",
};

/**
 * 세션 국면의 국면 표시 (007 T091 걷기가 잡은 것 · FR-219 · 005 FR-141·U-20).
 *
 * **끝난 실행은 「실행 중」이 아니다.** `phaseOfSession()` 은 종료 상태(`completed`·
 * `failed`·`stopped`)를 `running` 으로 판정한다 — 그것은 옳다. 세션이 아직 열려 있고
 * 화면이 마지막 미러와 Step 목록을 그대로 보여 주므로, 사용자가 있는 위치는 여전히
 * 실행 국면이다.
 *
 * 그러나 **표시**는 다르다. 걷기(W-1)가 본 것은 국면 알약이 「실행 중」이라고 말하는
 * 옆에서 결말 요약이 「실패 · Step 06 에서 실패」라고 말하는 화면이었다. 한 화면이 두
 * 가지를 주장하는 것이 005 U-20 이고, 그것을 없애려고 어휘를 한 곳에 모았다.
 *
 * 판정을 고치지 않고 **표시만** 고치는 이유: 국면이 바뀌면 권한표가 통째로 갈린다.
 * 끝난 실행에서 무엇을 할 수 있는지는 지금 표가 정확히 말하고 있다(덮어쓰기 O5).
 */
export function sessionPhaseLabel(
  phase: Phase,
  state: { finished: boolean; review: boolean; pausing: boolean },
): string {
  if (phase !== "running") return PHASE_LABEL[phase];
  if (state.review) return "검토";
  if (state.finished) return "실행 종료";
  if (state.pausing) return "일시정지 중…";
  return PHASE_LABEL.running;
}

/**
 * 조작의 기본 라벨.
 *
 * 상황에 따라 바뀌는 것(`run.stop` 의 「중지」/「닫기」/「나가기」, `run.from` 의 시작
 * 지점)은 여기 기본형을 두고 전용 함수가 상황형을 만든다. **라벨이 바뀌는 것이 규칙을
 * 지키는 방법이다** — 같은 자리의 같은 라벨이 두 동작을 갖지 않게 한다 (FR-235 ·
 * 005 FR-147).
 */
export const ACTION_LABEL: Record<ActionId, string> = {
  "run.all": "처음부터 실행",
  "run.from": "이 Step 부터 실행",
  "run.fromHere": "이 Step 부터 이어 실행",
  "run.pause": "일시정지",
  "run.resume": "계속하기",
  "run.resumeSkipFailure": RESUME_SKIPPING_FAILURE,
  "run.stop": "중지",
  "run.pacing": "실행 속도",
  /**
   * 009 — 「에서」를 「앞에서」로 고쳤다.
   *
   * 이 조작은 그 Step 을 **실행하지 않고 그 앞에서** 멈춘다(`pause_before_index`). 「이
   * Step 에서 멈추기」는 그 Step 이 이미 수행된 뒤로 읽히고, 무엇을 끼워 넣을 수 있는
   * 자리인지가 뒤집힌다.
   */
  "browser.openAt": "브라우저 열어 이 Step 앞에서 멈추기",
  "session.open": OPEN_RUNNING_SESSION,
  /** 2회차 — 세션을 녹화 모드로 만든다. `step.recordStart` 와 다른 조작이다 */
  "record.start": "녹화 시작",
  "step.recordStart": "직접 조작으로 Step 추가",
  "step.recordStop": "기록 멈추기",
  "step.addNaturalLanguage": "자연어로 Step 추가",
  "step.addAssertion": "검증 추가",
  /** 009 FR-285 — 브라우저 없이 넣는다. 위 셋과 갈리는 유일한 추가 경로다 */
  "step.insertManual": "직접 입력으로 Step 추가",
  "step.select": "Step 상세 보기",
  "step.update": "Step 고치기",
  "step.markSensitive": "민감 값으로 지정",
  "step.repick": "요소 다시 집기",
  "step.delete": "Step 삭제",
  /**
   * 009 — `step.reorder`「순서 변경」을 개칭했다.
   *
   * 이전 이름은 별도 패널을 가리켰고 그 패널은 없어진다(FR-301). 이름이 두 방향을 뜻하는
   * 것처럼 읽히면서 실제로는 위로만 옮긴 것이 관찰 M-05 였다.
   */
  "step.moveUp": "위로 옮기기",
  "step.moveDown": "아래로 옮기기",
  "test.rename": "테스트 이름",
  "test.setStartUrl": "시작 주소",
  save: "저장",
  "save.overwriteStale": STALE_OVERWRITE_LABEL,
  "edits.revert": "변경 전부 되돌리기",
  "ai.compose": "지시문 쓰기",
  "ai.start": "AI 시작",
  "ai.chooseBlocked": "어떻게 할지 고르기",
  "artifact.select": "산출물 보기",
  "result.show": SHOW_RESULT_DETAIL,
  "nav.editStep": "이 Step 고치기",
  "nav.back": "목록으로",
  "tab.select": "탭 고르기",
};

/**
 * 비활성 이유 (ui-contract §3-5 의 조건 C1~C13 · §3-6 의 덮어쓰기 O1~O4).
 *
 * 키가 조건 번호인 이유는 계약과 코드가 같은 이름을 쓰게 하는 것이다. 문구를 고치면
 * 계약의 어느 줄인지 즉시 찾을 수 있다.
 */
export const DISABLED_REASON = {
  C1: "실행 중인 세션이 열려 있습니다",
  C2: "브라우저가 닫혔습니다",
  C3: "건너뛸 실패가 없습니다",
  /**
   * T041 실측 — 사람이 조작하는 동안 재생 속도는 **지금 실행에 쓰이지 않는다.**
   *
   * 이것은 조작을 막을 근거가 아니라 **라벨의 근거**다 (005 FR-174). 그래서 표의 TKO
   * 열은 `●` 이고, 이 문구는 조건이 거짓일 때가 아니라 컨트롤 라벨(「다음 실행 속도」)
   * 옆에서 쓰인다. 조건 키를 지우지 않는 이유는 계약 §3-5 의 번호가 코드와 같은 이름을
   * 갖게 하려는 것이다.
   */
  C4: "사람이 조작하는 동안에는 실행 속도가 적용되지 않습니다",
  C5: "실행 중인 세션이 없습니다",
  C6: "기록 중이 아닙니다",
  C7: EDIT_BLOCKED_BY_RUN,
  C8: "Step 이 없으면 저장할 수 없습니다",
  C9: "바꾼 것이 없습니다",
  C10: "정의 파일이 밖에서 바뀌지 않았습니다",
  C11: "고를 선택지가 없습니다",
  C12: "실행이 끝나면 볼 수 있습니다",
  C13: "아직 실행한 적이 없습니다",
  /**
   * C14 — 지시문이 비어 있다 (2회차 · ui-contract §3-5).
   *
   * 지금 `AiCompose.tsx` 의 `disabled={busy || instruction.trim() === ""}` 가 하던
   * 판정을 표로 옮긴 것이다. 화면이 스스로 판단하면 다른 화면이 같은 판단을 빠뜨린다.
   */
  C14: "지시문을 쓰면 시작할 수 있습니다",
  /**
   * C15 — 만드는 방법으로 AI 를 골랐다 (2회차 · 만들기 국면).
   *
   * 지시문 자리는 **방법을 고르기 전에도 있다.** 감추면 「AI 로 만들 때 지시문을 쓴다」는
   * 사실을 고른 뒤에야 알게 되고, 그것이 S-15 와 같은 종류의 결함이다 (FR-234).
   */
  C15: "「AI로 만들기」를 고르면 쓸 수 있습니다",
  O1: "실행을 준비하는 중…",
  O2: "요청을 보내는 중…",
  O3: "브라우저 세션이 유실됐습니다",
  O4: "Step 이 없습니다",
  O5: "실행이 이미 끝났습니다",
  O6: "정지되면 할 수 있습니다. 현재 Step 이 끝나기를 기다리고 있습니다",
  O7: "실패한 Step 이 있어 이어서 갈 수 없습니다",
  O8: "중지하는 중…",
  /** O9 — 건너뛸 실패가 없다. 조건 C3 과 같은 사실을 덮어쓰기로 본 것이다 (§3-6). */
  O9: "건너뛸 실패가 없습니다",
  /** 국면 자체가 그 조작을 허용하지 않는 경우. 조건이 아니라 국면의 성질이다. */
  RUNNING_NO_EDIT: EDIT_BLOCKED_BY_RUN,
  RESULT_NO_EDIT: "끝난 실행의 기록은 고칠 수 없습니다",
  NEEDS_BROWSER: "살아 있는 브라우저가 필요합니다",
  NEEDS_PAUSE: "실행을 멈춘 뒤에 할 수 있습니다",
  AI_RUNNING: "AI 가 수행하는 동안에는 할 수 없습니다",
  /**
   * 지시문은 **기록**이다 (001 FR-063·FR-064 · 006 의 결정).
   *
   * 저장되지 않고 실행 대상도 아니다. 「끝난 실행의 기록은 고칠 수 없습니다」로 뭉개면
   * 사용자는 "언젠가 고칠 수 있는 것" 으로 읽는다 — 그런 때는 없다.
   */
  AI_INSTRUCTION_RECORD:
    "이 문장은 기록일 뿐 실행 대상이 아닙니다. 다시 돌릴 때는 Step 만 실행합니다",
  NO_SESSION: "브라우저 세션이 없습니다",
  /**
   * 시작 주소처럼 **세션이 다룰 수 없는** 테스트 속성.
   *
   * 세션의 편집 경로(`/api/sessions/{id}/steps`)는 Step 만 다루고, 시작 주소는 정의
   * 파일의 속성이다. 세션이 이미 그 주소로 이동한 뒤이므로 도중에 바꾸는 것은 뜻이
   * 없다. 그래서 해소 방법은 「브라우저 열기」가 아니라 **중지**다 — 세션을 끝내야
   * 편집 국면에 갈 수 있다.
   *
   * 이 이유 키가 따로 있는 까닭은 T012 의 검사가 잡아냈기 때문이다. 처음에는
   * 「브라우저가 필요합니다 → 브라우저 열어 Step nn 에서 멈추기」로 적었는데, 일시정지
   * 국면에는 그 조작이 **이미 충족되어 존재하지 않는다.** 화면에 없는 조작을 지시하는
   * 것이 006 E-03 이었다.
   */
  EDIT_AFTER_SESSION: "세션을 끝낸 뒤 편집에서 바꿀 수 있습니다",
  /**
   * 만들기 국면 — 아직 아무것도 시작하지 않았다 (2회차 · FR-260).
   *
   * Step 조작 전부의 이유다. **자리를 감추지 않는 것이 요점이다** — 목록이 0개여도
   * 자리를 지키고(FR-260), 그 자리의 조작이 왜 지금 안 되는지와 어떻게 하면 되는지가
   * 함께 있어야 한다. 「조작이 어디에 쌓이는지 시작하기 전에 보인다」가 S-15 의 수정이다.
   */
  NOT_STARTED_YET: "아직 시작하지 않았습니다. 시작하면 Step 이 여기 쌓입니다",
  /**
   * 만들기 국면의 테스트 이름 (2회차 · FR-258a).
   *
   * **이름 입력을 만들기 국면으로 옮기지 않는다.** 지금 제품은 저장 시점(일시정지
   * 국면)에 이름을 정하고, 옮기는 것은 새 조작이므로 범위 밖이다. 자리는 남기고 이유를
   * 붙인다 — 감추면 「만들기에는 이름이 없는 것」으로 읽힌다.
   */
  NAME_ON_SAVE: "저장할 때 이름을 정합니다",
  /** 만들기 국면 — 저장할 정의가 아직 없다 (2회차). */
  NOTHING_TO_SAVE_YET: "아직 저장할 것이 없습니다. 먼저 Step 을 만드세요",
} as const;

export type DisabledReasonKey = keyof typeof DISABLED_REASON;

/**
 * 「해당 없음」의 근거 (ui-contract §4-2 의 닫힌 목록).
 *
 * `–` 를 쓸 수 있는 경우는 셋뿐이다. 근거 없이 조작을 그리지 않으면 그것은 **감춘
 * 조작**이며 FR-234 위반이다.
 */
export const NOT_APPLICABLE_REASON = {
  /** N1 이미 충족됨 — 그 조작의 목적이 이 국면에서 이미 이루어져 있다 */
  N1: "이미 충족되어 있습니다",
  /** N2 대상이 없음 — 그 조작이 다룰 대상이 이 국면에 존재하지 않는다 */
  N2: "이 국면에는 그 대상이 없습니다",
  /** N3 세션이 없음 — 세션 명령인데 이 국면에는 세션이 없다 */
  N3: "세션 명령이며 이 국면에는 세션이 없습니다",
} as const;

export type NotApplicableKey = keyof typeof NOT_APPLICABLE_REASON;

/**
 * 중지 계열 버튼의 라벨 (005 FR-147 · U-08).
 *
 * 같은 위치의 같은 라벨이 두 동작을 갖지 않게 하는 장치다. 끝난 실행에서 이 버튼은
 * 실행을 멈추는 것이 아니라 세션을 정리하고 화면을 떠나는 것이다.
 */
export function stopLabel(input: {
  finished: boolean;
  pending: boolean;
  review: boolean;
}): string {
  if (input.pending) return "중지 중…";
  if (input.review) return "나가기";
  if (input.finished) return "닫기";
  return ACTION_LABEL["run.stop"];
}

/**
 * 결과가 그때의 정의와 어긋났다는 알림 (007 FR-254 A5 · research R3).
 *
 * 결과 스냅샷에는 Step DSL 이 없어 통합 Step 행의 구조 정보를 **현재 정의**에서 끌어온다.
 * `step_id` 매칭이 실패하면 그 사이에 정의가 바뀐 것이고, 사용자는 지금 보고 있는 대상
 * 요약이 그때의 것이 아님을 알아야 한다. **지금은 알 방법조차 없다.**
 */
export function resultDefinitionDrift(unmatchedCount: number): string {
  return (
    `이 결과 이후 정의가 바뀌었습니다 — Step ${unmatchedCount}개가 지금 정의에 없습니다. ` +
    `결말과 소요 시간은 그때의 기록이고, 동작 종류·대상 요약은 지금 정의를 보여줍니다.`
  );
}

/**
 * 통합 Step 행의 결말 표식 라벨 (007 T015 · research R4 · FR-225·FR-226).
 *
 * `stepOutcomeLabel` 과 **다른 함수인 이유**: 그것은 생성 타입
 * (`run-result.d.ts` 의 `pass|fail|skipped|not_run`)을 받고, 이것은 화면의 표시 값
 * (`components/workbench/model.ts` 의 `StepOutcome`)을 받는다. 표시 값에는 저장되지
 * 않는 상태(`running`·`pending`·`recorded`)가 있다.
 *
 * **「기록됨」이 「통과」와 다른 값인 것이 이 라운드의 수정이다.** AI 작성 화면은 Step
 * 행의 결말 자리에 **항상 체크 표식**을 그렸다 (S-09) — 결말을 모르는 국면인데 통과처럼
 * 보였다. 005 가 `skipped`(건너뜀)와 `not_run`(미실행)을 `pending` 에서 갈라낸 것과
 * 같은 종류의 구별이다 (U-21).
 *
 * **색·형태만으로 구분하지 않는다.** 이 라벨이 표식과 항상 함께 있다 (005 FR-141·FR-151).
 */
export function displayOutcomeLabel(outcome: WorkbenchStepOutcome): string {
  switch (outcome) {
    case "pass":
      return "통과";
    case "fail":
      return "실패";
    case "running":
      return "실행 중";
    case "pending":
      return "대기";
    case "skipped":
      return "건너뜀";
    case "not_run":
      return "미실행";
    case "recorded":
      return "기록됨";
  }
}

/** 그 결말이 **재생 통과**를 뜻하는가. 「기록됨」은 아니다 (FR-225). */
export function meansPassed(outcome: WorkbenchStepOutcome): boolean {
  return outcome === "pass";
}
