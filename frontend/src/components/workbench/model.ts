/**
 * 통합 작업 화면의 표시 모델 (007 T014·T015 · data-model.md §2).
 *
 * **이 파일은 저장 형식이 아니다.** Step DSL·정의 파일·결과 파일·세션 상태의 스키마는
 * 그대로다 (FR-250). 여기 있는 것은 **화면 안에서만 사는** 표시 모델이고, 권위 정의는
 * 여전히 `backend/src/itb/domain/*.py` 에서 생성된 `types/generated/*` 다.
 *
 * 국면 어댑터(`SessionScreen` · `ResultView` · `EditView`)가 이것을 만들고,
 * `Workbench` 가 이것만 받아 그린다. 표시 컴포넌트는 데이터를 읽지 않고 명령을 만들지
 * 않는다 — 001 research R2 가 규명한 얽힘(화면 선택이 세션 상태 조합에 매달린 것)이
 * 되살아나지 않게 하는 배치다.
 */

import type { ReactNode } from "react";

import type { ArtifactKind, RepickSlot, RunPacing } from "../../api/client";
import type { ErrorInfo } from "../ErrorNotice";
import type { ActionId } from "../../lib/actions";
import type { CapabilityMap } from "../../lib/capabilities";
import type { Phase } from "../../lib/phase";
import type { OutcomeTone } from "../../lib/wording";
import type { Step, TargetLocator } from "../../types/generated/step";
import type { ErrorCode, LocatorAttempt, StepResult } from "../../types/generated/run-result";

/**
 * Step 하나의 표시 상태.
 *
 * `skipped`(건너뜀)와 `not_run`(미실행)이 **서로 다른 값**인 것이 005 FR-151 이다.
 * 이전에는 둘 다 `pending` 으로 뭉개져 "안 돌린 것" 과 "앞선 실패로 도달 못한 것" 을
 * 구분할 수 없었다 (U-21).
 *
 * **`recorded`(기록됨)를 007 이 더한다** (research R4 · FR-225). 녹화·AI 작성·사람이 직접
 * 조작 국면의 Step 은 **일어난 일**이지만 재생 통과가 아니다. 그런데 AI 작성 화면은 그
 * 자리에 **항상 체크 표식**을 그렸다 (S-09) — 결말을 모르는데 통과처럼 보였다.
 * 005 가 `skipped`·`not_run` 을 가른 것과 같은 종류의 구별이다.
 */
export type StepOutcome =
  | "pass"
  | "fail"
  | "running"
  | "pending"
  | "skipped"
  | "not_run"
  /** 기록됨 — 작성 국면. **통과가 아니다** (FR-225) */
  | "recorded";

/**
 * 만들기 국면의 방법. **둘뿐이다** (FR-258a).
 *
 * 「빈 테스트」 같은 새 방법을 만들지 않는다 — 지금 제품에 없다.
 */
export type ComposeMode = "record" | "ai";

/** 층② 국면 띠 (74px). */
export interface PhaseBar {
  /** 국면 표시. 화면에 하나뿐이다 (FR-219) */
  phaseLabel: string;
  /** 색 역할. **색은 보조이며 라벨이 항상 함께 있다** (005 FR-141) */
  phaseTone: OutcomeTone;
  /** 결말 요약. 화면에 하나뿐이다 (FR-218d · 005 FR-140) */
  runSummary: string | null;
  /** 진행 표시. 실행 중 국면의 `step 04 / 05` 자리 */
  progressLabel: string | null;
}

/** 왜 비었는지 구별한다 (FR-245 · 005 FR-173). */
export type EmptyReason = "not_started" | "not_collected" | "session_lost" | "not_supported";

/**
 * 층③ 좌측 대상 앱 영역. **자리는 고정, 내용만 국면이 정한다** (FR-244).
 *
 * `empty` 가 별도 값인 이유는 "아직 시작하지 않음" 과 "수집하지 않음" 과 "세션 유실" 이
 * 사용자에게 **서로 다른 다음 행동**을 요구하기 때문이다. 지금 결과 화면의 빈 산출물
 * 탭이 "(기록 없음)" 한 줄이었던 것이 005 U-22 다.
 */
export type TargetView =
  | { kind: "mirror"; mirror: ReactNode; currentUrl: string; tabs: ReactNode | null }
  | {
      kind: "artifacts";
      selected: ArtifactKind;
      /** 그 종류를 고를 수 있는가. 지원되지 않는 것은 비활성 + 이유로 남는다 (FR-246) */
      available: ArtifactKind[];
      body: ReactNode;
    }
  | {
      kind: "open_browser";
      stepIndex: number | null;
      /** 저장이 먼저 필요할 때 라벨이 그 사실을 말한다 (006 FR-203). */
      label?: string;
    }
  | { kind: "empty"; reason: EmptyReason };

/** AI 가 막힌 자리. 세션 상태와 무관하게 그린다 (FR-218f). */
export interface AiBlockedState {
  attempted: string | null;
  reason: string;
  choices: string[];
}

/** 외부 변경 충돌 (006 FR-209). */
export interface StaleInfo {
  revision: string;
}

/**
 * 층③-b 국면 작업 영역 — 그 국면에서 사용자가 **실제로 하는 일**의 유일한 자리
 * (FR-218e · FR-218e-1).
 *
 * ## 이름이 바뀐 이유 (FR-218e-1)
 *
 * 1회차의 이름은 `PhaseAside`(국면 **보조** 영역)였고, 그 이름이 이 자리가 담는 것을
 * 보조로 규정했다. 그 규정이 **편집 폼 전체를 42px 띠에 넣는 판단**으로 이어졌다
 * (spec S-12). 이름은 판단을 유도한다 — 그래서 이름을 고치는 것이 2회차 수정의 일부다.
 *
 * 높이는 이 타입이 갖지 않는다. `lib/layout.ts` 의 배분표가 국면별로 정한다 (FR-256).
 *
 * **`error` 와 `blocked` 는 국면 상태와 무관하게 그린다** (FR-218f · FR-253). 값이 있으면
 * 보인다 — 접힘·탭·겹침 뒤에 두지 않는다. 001 research R2 가 규명한 결함이 정확히
 * "실패를 그리는 유일한 컴포넌트가 조건 뒤에 숨은 것" 이었다.
 */
export type WorkAreaView =
  /**
   * 만들기 국면의 시작 조건 (2회차 · FR-258·FR-258a).
   *
   * 항목은 **현재 만들기 흐름에 있는 것뿐이다** — 시작 URL · 방법 2택 · 지시문.
   * 테스트 이름과 「빈 테스트」는 없다. 이름은 저장 시점(일시정지 국면)에 정하고,
   * 둘 다 지금 제품에 없는 조작이므로 만드는 것은 범위 밖이다 (research R11).
   */
  | {
      kind: "compose_form";
      startUrl: string;
      /** 고른 방법. 아직 안 골랐으면 `null` */
      mode: ComposeMode | null;
      instruction: string;
      /** AI 사용 가능 여부. 눌러 봐야 아는 것은 늦다 (001 DR-021) */
      aiReady: { available: boolean; reason: string | null } | null;
      /** `ai.compose` 가 비활성인 이유. 자리는 늘 있고 이유가 붙는다 (FR-234 · 조건 C15) */
      composeReason: string | null;
      error: ErrorInfo | null;
      onStartUrlChange: (next: string) => void;
      onModeChange: (next: ComposeMode) => void;
      onInstructionChange: (next: string) => void;
    }
  | {
      kind: "ai_progress";
      instruction: string;
      messages: string[];
      error: ErrorInfo | null;
      blocked: AiBlockedState | null;
    }
  | {
      kind: "takeover_guide";
      recording: boolean;
      blocked: AiBlockedState | null;
      error: ErrorInfo | null;
    }
  | { kind: "paused_tools"; tools: ReactNode }
  /*
    **실행 중·녹화 국면에는 이 자리의 내용이 없다** (2회차 T107 판정).

    계획은 「42px 진행 띠가 `noticesExtra` 로 우회해 들어가 있으니 타입 안으로 들이자」
    였는데, 구현에서 대조해 보니 **그런 띠가 없다.** `noticesExtra` 가 나르는 것은
    실시간 통로 끊김 배너이며 그것은 알림이고 알림 자리(국면 띠 아래)가 제 집이다.
    진행은 `phaseBar.progressLabel`, 실행 속도는 `phaseActions` 에 이미 있다.

    없는 것을 만들면 (가) 없던 요소가 생기고 (나) `run.pacing` 이 확립된 자리에서
    옮겨져 FR-235(같은 자리)를 어긴다. 그래서 이 국면들은 `work: null` 이고, 배분표의
    `content` 는 「내용이 있으면 그 높이」라는 뜻으로 남는다 (FR-218e).
  */
  /*
    실패 상세 (FR-262).

    **시도한 locator 를 따로 싣지 않는다.** `step.locator_attempts` 에 이미 있고,
    `WorkArea` 가 1회차부터 그것을 그려 왔다 — 같은 값을 두 곳에 두면 흡수 시점에 어느
    쪽이 진실인지 알 수 없다 (T015 가 `recorded` 에서 같은 판단을 했다).

    2회차가 고치는 것은 **내용이 아니라 자리의 크기**다. 1회차에는 이 영역이
    `minHeight: 42` · `maxHeight: 45%` 였고, 실패 사유와 시도한 locator 표가 그 안에서
    스크롤에 갇혔다. `layout.ts` 의 `result.workArea = fixed 424` 가 그것을 푼다.
  */
  | { kind: "failure_detail"; step: StepResult; diagnosis: string | null }
  | {
      kind: "edit_fields";
      pendingCount: number;
      warnings: string[];
      stale: StaleInfo | null;
      savedName: string | null;
      /**
       * 편집 국면 고유의 나머지 — 테스트 이름·시작 주소·지시문 기록·개별 되돌리기.
       *
       * **Step 이 아니라 테스트에 속한 것들**이라 Step 패널 바닥(조작 팔레트)에 둘 수
       * 없고, 그렇다고 국면 띠에 넣으면 74px 안에 입력칸이 들어간다. 국면 작업 영역이
       * 「그 국면에서 실제로 하는 일의 유일한 자리」(FR-218e)이므로 여기가 그 자리다.
       *
       * **2회차: 이 자리가 남는 높이 전부를 갖는다** (FR-257 · `layout.ts` 의
       * `editing: { workArea: fill }`). 1회차에는 같은 내용이 42px 띠에 있었다.
       */
      fields?: ReactNode;
    };

/** 1회차 이름. 부르는 곳이 남아 있어도 같은 것을 가리킨다 (FR-218e-1 이행 중). */
export type PhaseAside = WorkAreaView;

/**
 * 층③ 우측 Step 행 — **단일 구현이 그리는 단일 모델** (FR-221·FR-222).
 *
 * `step` 이 `null` 일 수 있는 것은 결과 국면 때문이다. `StepResult` 에는 Step DSL 이 없어
 * (`type`·`target`·`value`·`author` 가 없다) 정의와 `step_id` 로 매칭해 채우는데, 결과
 * 이후 정의가 바뀌면 매칭되지 않는 행이 남는다 (research R3). 그 행은 동작 종류·대상
 * 요약·값 칸이 **비고, 다른 칸이 그 자리로 당겨지지 않는다** (FR-223).
 */
export interface WorkbenchStep {
  /** 정의의 `Step.id` = 결과의 `step_id` (`runner.py:398` 에서 확인) */
  id: string;
  /** 0-기반. 표시는 `stepNumber()` 가 1-기반으로 한다 (FR-224) */
  index: number;
  /** 정의에서. 결과 국면에서 매칭 실패면 `null` */
  step: Step | null;
  /** 결과 국면은 결과의 `label`, 그 외는 `step.label` */
  label: string;
  outcome: StepOutcome;
  /** 결과·실행에서. 그 외 `null` → 자리를 비운다 (FR-223) */
  durationMs: number | null;
  /** 일시정지 위치 (FR-034) */
  isPausedHere: boolean;
}

/**
 * Step 상세 — 겹침 640px. 모든 국면에서 같은 자리·같은 구성 (FR-230).
 *
 * `attempts` 와 `candidates` 를 **둘 다** 두는 이유: 결과 국면에서 사용자가 알아야 하는
 * 것은 "정의에 무엇이 있는가" 가 아니라 "그때 무엇을 시도했고 왜 못 찾았는가" 다. 편집
 * 국면에서는 반대다. 한 칸에 뭉개면 국면에 따라 같은 자리가 다른 뜻을 갖는다.
 */
export interface StepDetail {
  step: Step | null;
  index: number;
  /** 그 실행에서 실제로 시도한 locator. 결과 국면에만 있다 */
  attempts: LocatorAttempt[] | null;
  /** 정의가 가진 후보. 적용 순서는 제품 전역 고정 규칙이다 (Principle IV) */
  candidates: TargetLocator | null;
  /** `drag` 는 대상 요소를 둘 갖는다 */
  dropCandidates: TargetLocator | null;
  repickWaiting: RepickSlot | null;
  failure: { code: ErrorCode | null; message: string | null } | null;
}

/**
 * 알림 — 국면 띠 아래에 쌓인다.
 *
 * `nextAction` 이 별도 칸인 이유는 003 EC-004 다 — 문자열로 뭉개면 "대상 앱에 연결할 수
 * 없습니다" 뒤에 와야 하는 "떠 있는지 확인하세요" 가 사라진다.
 */
export interface Notice {
  id: string;
  tone: "error" | "warn" | "info";
  /** 접근성. 지금은 각 화면이 개별로 정해 같은 성격의 배너가 다른 role 을 갖는다 */
  role: "alert" | "status" | "note";
  message: string;
  nextAction: string | null;
  action: { label: string; actionId: ActionId } | null;
  dismissible: boolean;
}

/** 국면 어댑터가 만들고 `Workbench` 가 소비하는 **유일한 입력**. */
export interface WorkbenchModel {
  phase: Phase;
  /** 아직 저장되지 않은 작성 세션은 `null` */
  testId: string | null;
  /** 초안이면 「TC-nnn 초안」 형태 (005 FR-134 · U-03) */
  testName: string;

  phaseBar: PhaseBar;
  /** ③-a 대상 앱 슬롯. 높이는 `layout.ts` 의 배분표가 정한다 (FR-256) */
  target: TargetView;
  /**
   * ③-b 국면 작업 영역. `null` 이면 자리를 차지하지 않는다 (FR-218e).
   *
   * 1회차 이름은 `aside` 였다. 이름이 이 자리를 보조로 규정한 것이 S-12 의 뿌리이므로
   * 필드 이름도 함께 고친다 (FR-218e-1).
   */
  work: WorkAreaView | null;
  steps: WorkbenchStep[];
  /** 국면을 넘어 유지된다 (FR-239) */
  focusedStepId: string | null;
  /** 겹침 640px. `focusedStepId` 가 있을 때만 */
  detail: StepDetail | null;

  /** 조작 → 상태. **화면이 읽는 유일한 근거** (FR-233) */
  capabilities: CapabilityMap;
  notices: Notice[];

  /** 작성 주체 표시. 행 구조를 바꾸지 않는다 (FR-228 · Principle I) */
  authoring: "record" | "ai";
  /** 실행 속도. `run.pacing` 이 활성인 국면에서만 쓰인다 */
  pacing: RunPacing | null;
}

/** 조작 하나를 실제로 실행하는 함수 모음. 어댑터가 준다. */
export type ActionHandlers = Partial<Record<ActionId, (arg?: unknown) => void>>;
