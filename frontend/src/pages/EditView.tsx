/**
 * 편집 국면의 **어댑터** (007 T052~T054 · FR-217·FR-230·FR-237).
 *
 * 007 이전에는 `TestDefinition.tsx` 였고, **일곱 국면 중 껍데기 자체가 다른 유일한
 * 화면**이었다 — 다른 화면은 기준 폭 1440 아트보드 + 60px 헤더인데 이것만 최대 폭
 * 1080 의 가운데 정렬 본문이고 헤더·경로·상태 표시가 없었다 (S-06). Step 상세도
 * 혼자만 목록 아래 인라인으로 펼쳤다 (S-05).
 *
 * 이제 껍데기와 Step 상세를 나머지 국면과 공유한다. **행동은 그대로다.**
 *
 * ## 초안은 편집 연산 목록이다 (006 research R3)
 *
 * 화면이 편집 **결과**를 서버에 보내면 "어느 Step 종류가 값을 갖는가" 같은 판정이 여기로
 * 넘어오고, 그것이 편집 규칙의 두 번째 구현이 된다. 연산을 보내면 서버의 `step_edits` 가
 * 유일한 구현으로 남는다. 연산 개수가 곧 변경 건수이고(FR-189), 되돌리기는 목록에서
 * 빼는 것이다(FR-190).
 *
 * **초안을 브라우저 저장소에 넣지 않는다** (006 research R8). 정의 파일이 유일한 진실
 * 이므로, 낡은 초안이 남으면 어느 쪽이 맞는지 화면이 말할 수 없는 상태가 된다.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  definition,
  tests,
  type DefinitionView,
  type EditOp,
  type ManualStepSpec,
} from "../api/client";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";
import { StepEditFields } from "../components/StepEditFields";
import { ActionButton } from "../components/workbench/ActionButton";
import { ActionPalette } from "../components/workbench/ActionPalette";
import { InsertStepForm } from "../components/workbench/InsertStepForm";
import { ConfirmDelete, StepRowOps } from "../components/workbench/StepRowOps";
import { Workbench } from "../components/workbench/Workbench";
import type { Notice, WorkbenchModel, WorkbenchStep } from "../components/workbench/model";
import type { ActionId } from "../lib/actions";
import {
  capabilitiesFor,
  type CapabilityFacts,
  type CapabilityState,
} from "../lib/capabilities";
import {
  EDIT_BLOCKED_BY_RUN,
  OPEN_RUNNING_SESSION,
  PHASE_LABEL,
  SAVE_BEFORE_OPEN_BROWSER,
  SAVE_THEN_OPEN_BROWSER,
  lockedFieldNotice,
  manualStepLabel,
  runFromStepLabel,
  saveEditsLabel,
  stepNumber,
  unsavedLeaveWarning,
} from "../lib/wording";
import type { Step } from "../types/generated/step";
import type { Test } from "../types/generated/step-dsl";


export interface EditViewProps {
  testId: string;
  /** 결과 국면에서 지목해 들어온 Step (FR-056·FR-180·FR-239). */
  focusStepId?: string | null;
  onBack: () => void;
  onRun?: (testId: string, fromStepIndex?: number) => void;
  /**
   * 브라우저 편집 세션을 연다 (006 FR-200). 지정한 Step 직전에서 멈춘다.
   *
   * `stepId` 를 함께 넘기는 이유는 세션이 끝난 뒤 **이 화면의 이 Step 으로** 돌아오기
   * 위해서다 (FR-204). 인덱스가 아니라 id 로 넘긴다 — 세션에서 Step 을 지우거나 순서를
   * 바꿨으면 인덱스는 다른 Step 을 가리킨다.
   */
  onOpenBrowserAt?: (testId: string, stepIndex: number, stepId: string | null) => void;
  /** 실행 중이라는 안내가 가리킨 세션으로 이동한다 (005 FR-126). */
  onOpenSession?: (sessionId: string) => void;
  /** 결과 국면으로 이동 (FR-239 의 왕복). */
  onShowResult?: (testId: string, stepId?: string | null) => void;
  /** 실행 요청이 진행 중인가 (005 FR-127). 덮어쓰기 O1 의 근거다. */
  runPending?: boolean;
}

export const PENDING_ID_PREFIX = "pending-";
/**
 * 저장 전 삽입 Step 의 임시 식별자 접두어.
 *
 * 진짜 id 는 서버가 `allocate_step_id` 로 매긴다 (009 research R6). 화면이 번호를
 * 만들면 리코더가 매긴 번호와 충돌한다. 그래서 저장 전에는 **자리만** 나타내는 표식을 쓰고,
 * 저장 응답이 오면 서버가 매긴 목록으로 통째 교체된다.
 *
 * 이 접두어가 곧 「저장되지 않은 삽입」의 근거다 — 행의 「미저장」 칩(FR-310)과 옮기기·
 * 지우기가 이것을 본다.
 */

/**
 * 저장 전 삽입 연산 중 그 임시 id 를 만든 것의 자리 (FR-289).
 *
 * `preview` 가 붙이는 표식과 같은 규칙으로 되짚는다 — 표식을 만드는 곳과 읽는 곳이
 * 갈리면 「넣었다가 지웠는데 변경이 남는」 상태가 된다.
 */
function pendingInsertIndex(ops: EditOp[], pendingId: string): number {
  let seen = 0;
  for (let i = 0; i < ops.length; i += 1) {
    const op = ops[i];
    if (op === undefined || op.op !== "insert") continue;
    const at = Math.max(0, op.at);
    if (`${PENDING_ID_PREFIX}${at}-${op.spec.kind}` === pendingId) return i;
    seen += 1;
  }
  return seen > 0 ? -1 : -1;
}

/** 삽입 연산 하나를 미리보기 Step 으로 만든다. **표시 전용이며 저장되지 않는다.** */
function previewStep(op: Extract<EditOp, { op: "insert" }>, at: number): Step {
  const spec = op.spec;
  const id = `${PENDING_ID_PREFIX}${at}-${spec.kind}`;
  const base = { id, label: spec.label ?? manualStepLabel(spec), author: "human" as const,
    tab: spec.tab ?? 0, timeout_ms: spec.timeout_ms ?? 10_000, frame_url: null };
  if (spec.kind === "navigate") return { ...base, type: "navigate", url: spec.url } as Step;
  if (spec.kind === "close_tab") return { ...base, type: "close_tab" } as Step;
  if (spec.kind === "assert_url") {
    return {
      ...base,
      type: "assertion",
      assertion: { kind: "url", target: null, match: spec.match ?? "equals", value: spec.url },
    } as Step;
  }
  return {
    ...base,
    type: "assertion",
    assertion: { kind: "text", target: null, match: spec.match ?? "contains", value: spec.value },
  } as Step;
}

/**
 * 편집 연산 목록을 저장된 정의에 **표시용으로** 얕게 적용한다.
 *
 * **판정하지 않는다** (006 data-model §5). 여기서 "이 종류는 값을 못 갖는다" 를
 * 결정하면 서버와 두 벌이 된다. 서버가 거절하면 그 문구를 그대로 보여준다.
 */
function preview(test: Test, ops: EditOp[]): Test {
  let steps = test.steps as unknown as Step[];
  let name = test.name;
  let startUrl = test.start_url;

  for (const op of ops) {
    if (op.op === "insert") {
      /*
        미리보기용 Step 을 만든다. **id 는 서버가 매기므로 여기서는 임시 표식**이다
        (`PENDING_ID_PREFIX`). 그 표식이 「저장 전 삽입」을 나타내며 행의 「미저장」 칩과
        저장 직전 위치 계산이 그것을 본다 (FR-310 · research R7).

        **판정하지 않는다** — 값이 유효한지는 서버가 정한다. 여기서 정하면 두 벌이 된다.
      */
      const at = Math.max(0, Math.min(op.at, steps.length));
      steps = [...steps.slice(0, at), previewStep(op, at), ...steps.slice(at)];
    } else if (op.op === "update") {
      steps = steps.map((s) => {
        if (s.id !== op.step_id) return s;
        const next = { ...s } as Record<string, unknown>;
        if (op.label !== undefined) next.label = op.label;
        if (op.value !== undefined) next.value = op.value;
        if (op.timeout_ms !== undefined) next.timeout_ms = op.timeout_ms;
        if (op.tab !== undefined) next.tab = op.tab;
        if (op.url !== undefined) next.url = op.url;
        if (op.assertion_value !== undefined && "assertion" in s) {
          next.assertion = { ...s.assertion, value: op.assertion_value };
        }
        return next as unknown as Step;
      });
    } else if (op.op === "delete") {
      steps = steps.filter((s) => s.id !== op.step_id);
    } else if (op.op === "reorder") {
      const byId = new Map(steps.map((s) => [s.id, s]));
      steps = op.order.map((id) => byId.get(id)).filter((s): s is Step => s !== undefined);
    } else if (op.op === "set_name") {
      name = op.name;
    } else {
      startUrl = op.url;
    }
  }
  return { ...test, name, start_url: startUrl, steps: steps as unknown as Test["steps"] };
}

/**
 * 같은 Step 의 연속 `update` 를 하나로 합친다.
 *
 * 합치지 않으면 값 칸에 다섯 글자를 타이핑한 것이 변경 5건으로 세어진다 — 사용자가 센
 * 것과 화면이 말하는 것이 어긋나고, 그것은 FR-189 가 요구하는 것이 아니다.
 */
function mergeOps(ops: EditOp[], next: EditOp): EditOp[] {
  if (next.op === "update") {
    const at = ops.findIndex((o) => o.op === "update" && o.step_id === next.step_id);
    if (at >= 0) {
      const merged = { ...(ops[at] as object), ...next } as EditOp;
      return [...ops.slice(0, at), merged, ...ops.slice(at + 1)];
    }
  }
  /*
    009 FR-289 — 저장 전에 넣은 Step 을 지우면 **`insert` 연산 자체를 뺀다.**

    `insert` + `delete` 두 건으로 남기면 「저장할 변경 3건」이 사용자가 인지한 것과
    달라진다. 넣었다가 지운 것은 아무것도 하지 않은 것과 같아야 한다.
  */
  if (next.op === "delete" && next.step_id.startsWith(PENDING_ID_PREFIX)) {
    const at = pendingInsertIndex(ops, next.step_id);
    return at >= 0 ? [...ops.slice(0, at), ...ops.slice(at + 1)] : ops;
  }
  if (next.op === "reorder" || next.op === "set_name" || next.op === "set_start_url") {
    // 마지막 것만 의미가 있다. 쌓아 두면 변경 건수가 실제로 바뀐 것보다 많아진다.
    return [...ops.filter((o) => o.op !== next.op), next];
  }
  return [...ops, next];
}

export function EditView({
  testId,
  focusStepId = null,
  onBack,
  onRun,
  onOpenBrowserAt,
  onOpenSession,
  onShowResult,
  runPending = false,
}: EditViewProps) {
  const [view, setView] = useState<DefinitionView | null>(null);
  const [ops, setOps] = useState<EditOp[]>([]);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [selected, setSelected] = useState<string | null>(focusStepId);
  const [detailOpen, setDetailOpen] = useState(focusStepId !== null);
  const [saving, setSaving] = useState(false);
  const [savedName, setSavedName] = useState<string | null>(null);
  /** 외부 변경 충돌. 화면을 옮기지 않고 그 자리에서 두 선택을 준다 (FR-209). */
  const [stale, setStale] = useState<{ revision: string } | null>(null);
  /** 이탈 확인 대기 중인 다음 행동 (FR-208). */
  const [leaving, setLeaving] = useState<null | (() => void)>(null);
  /** 볼 결과가 있는가 (조건 C13). 없으면 「결과 자세히 보기」가 이유와 함께 잠긴다. */
  const [hasResult, setHasResult] = useState(false);
  /**
   * 삽입 입력면이 열려 있는가 (009 FR-285).
   *
   * **자연어 추가·검증 추가와 같은 문법이다** — 조작 하나가 그 자리에서 입력면을 여닫는다.
   * 닫혀 있으면 자리를 차지하지 않는다.
   */
  const [insertOpen, setInsertOpen] = useState(false);
  /**
   * 지우기 확인을 기다리는 Step (009 FR-302).
   *
   * **행 안에서 확인한다** — 겹침 대화상자를 쓰지 않는다. 행 조작의 결과를 행이 아닌
   * 곳에서 확인하면 대상이 무엇이었는지 다시 확인해야 한다. `TestList` 의 테스트 삭제가
   * 같은 방식이며 그 선례를 따른다.
   */
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const load = useCallback(() => {
    void definition
      .get(testId)
      .then((v) => {
        setView(v);
        setOps([]);
        setStale(null);
        setError(null);
      })
      .catch((exc: unknown) => setError(describeError(exc)));
  }, [testId]);

  useEffect(load, [load]);
  useEffect(() => {
    setSelected(focusStepId);
    setDetailOpen(focusStepId !== null);
  }, [focusStepId]);
  useEffect(() => {
    // 결과 유무는 **조회로만** 알 수 있다. 실패는 "없다" 로 읽는다 — 결과가 없는 것이
    // 404 의 정상적인 뜻이고, 그것 때문에 편집 화면이 오류를 띄울 이유는 없다.
    void tests
      .result(testId)
      .then(() => setHasResult(true))
      .catch(() => setHasResult(false));
  }, [testId]);

  const pending = ops.length;

  /**
   * 005 FR-166 계열 — 새로고침·탭 닫기로 미저장 변경을 잃지 않는다 (FR-208).
   *
   * 인앱 이동은 아래 `guard()` 가 막고, 브라우저 수준 이탈은 이것이 막는다. 초안을
   * 저장소에 넣지 않기로 했으므로(R8) 이 확인이 그 자리를 메운다.
   */
  useEffect(() => {
    if (pending === 0) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [pending]);

  /** 물어볼 것이 없을 때 묻지 않는다 (FR-208 시나리오 3). */
  const guard = (next: () => void) => {
    if (pending === 0) {
      next();
      return;
    }
    setLeaving(() => next);
  };

  const apply = (op: EditOp) => {
    setSavedName(null);
    setOps((prev) => mergeOps(prev, op));
  };

  const revert = (index: number) => setOps((prev) => prev.filter((_, i) => i !== index));

  const save = (revision?: string) => {
    if (view === null || saving || pending === 0) return;
    setSaving(true);
    setError(null);
    void definition
      .save(testId, revision ?? view.revision, ops)
      .then((v) => {
        setView(v);
        setOps([]);
        setStale(null);
        setSavedName(v.test.name);
      })
      .catch((exc: unknown) => {
        const info = describeError(exc);
        if (info.code === "DEFINITION_STALE" && info.staleRevision) {
          // 화면을 옮기지 않는다. 사용자가 두 선택 중 하나를 고른다.
          setStale({ revision: info.staleRevision });
          return;
        }
        setError(info);
      })
      .finally(() => setSaving(false));
  };

  /**
   * 표시용 정의. **이른 반환보다 위에 있어야 한다** — 훅은 렌더마다 같은 순서로 불려야
   * 하고, 이른 반환 뒤에 두면 로딩 화면과 본 화면의 훅 개수가 달라진다.
   */
  const test = useMemo(() => (view === null ? null : preview(view.test, ops)), [view, ops]);

  if (error !== null && view === null) {
    return (
      <main style={{ maxWidth: 900, margin: "32px auto", padding: "0 16px" }}>
        <ErrorNotice error={error} />
        <button className="secondary" onClick={onBack}>
          목록으로
        </button>
      </main>
    );
  }

  if (view === null || test === null) {
    return (
      <main style={{ padding: 32 }} className="muted">
        불러오는 중…
      </main>
    );
  }

  /** 이른 반환 뒤의 확정된 정의. 클로저 안에서는 상태 변수의 좁힘이 유지되지 않는다. */
  const loaded = view;
  const dslSteps = test.steps as unknown as Step[];
  const current = dslSteps.find((s) => s.id === selected) ?? null;
  const currentIndex = current ? dslSteps.findIndex((s) => s.id === current.id) : -1;

  /*
    009 research R7 — 넣을 자리는 **미리보기 목록 기준**이다.

    `dslSteps` 는 저장된 정의에 미저장 연산을 적용한 결과다. 저장된 목록의 인덱스로 계산하면
    앞선 삽입·삭제·순서 변경이 가리키는 곳을 바꿔 버린다.

    고른 Step 이 없으면 **맨 뒤**다 — 「어디에 넣을지 먼저 고르세요」로 잠그지 않는다.
    맨 뒤에 넣는 것은 실무에서 가장 흔하고, 그것을 막을 근거가 없다.
  */
  const insertAt = currentIndex >= 0 ? currentIndex : dslSteps.length;
  const insertAtLabel =
    currentIndex >= 0 ? `Step ${stepNumber(currentIndex)}` : "목록 맨 뒤";

  const submitInsert = (spec: ManualStepSpec) => {
    apply({ op: "insert", at: insertAt, spec });
    setInsertOpen(false);
  };

  /*
    009 FR-298 — **행에서 바로 조작한다.**

    이전에는 팔레트가 「지목한 Step」을 대상으로 했으므로 옮기려는 Step 을 먼저 골라야
    했다. 여기서는 **그 행의 자리(index)를 인자로 받는다** — 고르는 조작이 끼지 않는다.
    그것이 세 칸 내리기를 여섯 번에서 세 번으로 줄이는 것의 전부다 (SC-503).
  */
  const runRowAction = (action: ActionId, index: number) => {
    const step = dslSteps[index];
    if (step === undefined) return;
    switch (action) {
      case "step.moveUp":
        move(index, -1);
        break;
      case "step.moveDown":
        move(index, 1);
        break;
      case "step.delete":
        // FR-302 — 확인을 거친다. 무엇이 지워지는지 그 행에서 보인다.
        setConfirmDelete(step.id);
        break;
      case "step.insertManual":
        // 그 행 **앞**에 넣는다 — 행을 고르고 입력면을 연다.
        setSelected(step.id);
        setInsertOpen(true);
        break;
      default:
        break;
    }
  };
  const sensitiveNames = (test.variables ?? []).filter((v) => v.sensitive).map((v) => v.name);
  const editable = view.editable;
  const lockedReason = (field: string) =>
    view.locked_fields.find((f) => f.field === field)?.reason ?? null;

  const steps: WorkbenchStep[] = dslSteps.map((step, index) => ({
    id: step.id,
    index,
    step,
    label: step.label,
    // 편집 국면에는 실행 결말이 없다. 「대기」로 두고 표식 자리를 비운다 (FR-223).
    outcome: "pending",
    durationMs: null,
    isPausedHere: false,
    // 009 FR-310 — 임시 표식을 가진 것이 저장 전 삽입이다 (`PENDING_ID_PREFIX`).
    isUnsaved: step.id.startsWith(PENDING_ID_PREFIX),
  }));

  const facts: CapabilityFacts = {
    definitionEditable: editable,
    hasSteps: steps.length > 0,
    hasPendingEdits: pending > 0,
    staleConflict: stale !== null,
    blockingSession: view.blocking_session_id != null,
    hasResult,
    runPending,
  };
  const capabilities = capabilitiesFor("editing", facts);

  const move = (index: number, delta: number) => {
    const to = index + delta;
    if (to < 0 || to >= dslSteps.length) return;
    // `noUncheckedIndexedAccess` 아래에서 자리 맞바꾸기를 안전하게 표현한다.
    const ids = dslSteps.map((s) => s.id);
    const order = ids.map((id, i) => (i === index ? ids[to] : i === to ? ids[index] : id));
    apply({ op: "reorder", order: order as string[] });
  };

  const openBrowserHere = () => {
    if (current === null || currentIndex < 0 || onOpenBrowserAt === undefined) return;
    onOpenBrowserAt(testId, currentIndex, current.id);
  };

  /**
   * 006 FR-203 — 저장하지 않은 변경이 있으면 **먼저 저장한 뒤** 세션을 연다.
   *
   * 두 경로가 같은 Step 을 다르게 들고 있는 상태를 만들지 않는다.
   */
  const openBrowser = () => {
    if (pending === 0) {
      openBrowserHere();
      return;
    }
    setSaving(true);
    void definition
      .save(testId, loaded.revision, ops)
      .then((v) => {
        setView(v);
        setOps([]);
        setSavedName(v.test.name);
        openBrowserHere();
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setSaving(false));
  };

  function runAction(action: ActionId) {
    switch (action) {
      case "run.all":
        guard(() => onRun?.(testId));
        break;
      case "run.from":
        if (currentIndex >= 0) guard(() => onRun?.(testId, currentIndex));
        break;
      case "save":
        save();
        break;
      case "save.overwriteStale":
        if (stale !== null) save(stale.revision);
        break;
      case "edits.revert":
        setOps([]);
        break;
      case "browser.openAt":
        openBrowser();
        break;
      case "session.open":
        if (loaded.blocking_session_id) onOpenSession?.(loaded.blocking_session_id);
        break;
      case "result.show":
        guard(() => onShowResult?.(testId, selected));
        break;
      case "nav.back":
        guard(onBack);
        break;
      case "step.insertManual":
        setInsertOpen((v) => !v);
        break;
      case "step.delete":
        if (current !== null) apply({ op: "delete", step_id: current.id });
        break;
      case "step.moveUp":
        if (currentIndex >= 0) move(currentIndex, -1);
        break;
      case "step.moveDown":
        if (currentIndex >= 0) move(currentIndex, 1);
        break;
      default:
        break;
    }
  }

  /** 지목한 Step 이 있어야 뜻이 있는 조작. 표는 국면을, 이것은 화면이 아는 사실을 본다. */
  const STEP_SCOPED: ActionId[] = [
    "step.moveUp",
    "step.moveDown",
    "step.delete",
    "browser.openAt",
  ];
  const narrowByPick = (id: ActionId, base: CapabilityState) =>
    STEP_SCOPED.includes(id) && currentIndex < 0 && base.kind === "enabled"
      ? ({
          kind: "disabled",
          reason: "먼저 Step 을 고르세요",
          remedy: { action: "step.select" as ActionId },
        } as const)
      : base;

  const needsTarget = (id: ActionId) =>
    currentIndex < 0 && capabilities[id].kind === "enabled"
      ? ({
          kind: "disabled",
          reason: "먼저 Step 을 고르세요",
          remedy: { action: "step.select" as ActionId },
        } as const)
      : capabilities[id];

  /*
    S-07 · FR-237 — 실행 조작은 **저장 여부와 무관하게** 같은 자리에 있다. 이전에는
    저장에 성공한 뒤에만 실행 버튼이 나타나, 사용자는 그것이 저장의 결과인지 원래
    있던 것인지 알 수 없었다.
  */
  const phaseActions = (
    <>
      <ActionButton
        action="run.all"
        capability={capabilities["run.all"]}
        onRun={() => runAction("run.all")}
        onRemedy={runAction}
      />
      <ActionButton
        action="run.from"
        capability={needsTarget("run.from")}
        label={runFromStepLabel(Math.max(currentIndex, 0))}
        onRun={() => runAction("run.from")}
        onRemedy={runAction}
      />
    </>
  );

  const headerActions = (
    <>
      <ActionButton
        action="session.open"
        capability={capabilities["session.open"]}
        label={OPEN_RUNNING_SESSION}
        compact
        onRun={() => runAction("session.open")}
        onRemedy={runAction}
      />
      <ActionButton
        action="result.show"
        capability={capabilities["result.show"]}
        compact
        onRun={() => runAction("result.show")}
        onRemedy={runAction}
      />
      <ActionButton
        action="nav.back"
        capability={capabilities["nav.back"]}
        compact
        onRun={() => runAction("nav.back")}
        onRemedy={runAction}
      />
    </>
  );

  const notices: Notice[] = [];
  // 006 FR-206 — 실행 중이면 화면은 열리되 읽기 전용이다. 감추지 않고 이유를 붙인다.
  if (!editable) {
    notices.push({
      id: "not-editable",
      tone: "warn",
      role: "status",
      message: EDIT_BLOCKED_BY_RUN,
      // 그 세션으로 가는 버튼은 **헤더에 하나** 있다 (FR-235). 여기 또 두면 같은 라벨이
      // 두 자리에 생기고, 사용자는 둘이 다른 것인지 확인하느라 멈춘다.
      nextAction: `「${OPEN_RUNNING_SESSION}」로 그 실행을 볼 수 있습니다.`,
      action: null,
      dismissible: false,
    });
  }
  for (const w of view.warnings) {
    notices.push({
      id: `warn-${w}`,
      tone: "warn",
      role: "status",
      message: w,
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }
  if (error !== null) {
    notices.push({
      id: "error",
      tone: "error",
      role: "alert",
      message: error.message,
      nextAction: error.nextAction || null,
      action: null,
      dismissible: false,
    });
  }
  if (pending > 0 && onOpenBrowserAt) {
    // 006 FR-203 — 브라우저를 열기 전에 저장한다는 사실을 미리 말한다.
    notices.push({
      id: "save-before-browser",
      tone: "info",
      role: "note",
      message: SAVE_BEFORE_OPEN_BROWSER,
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }

  const model: WorkbenchModel = {
    phase: "editing",
    testId,
    // 저장된 테스트를 고치는 화면이다 — 「초안」이 아니다 (005 U-03 과 같은 뿌리).
    testName: test.name,
    phaseBar: {
      phaseLabel: PHASE_LABEL.editing,
      phaseTone: "neutral",
      // 편집 국면에는 결말이 없다. 자리를 비운다 — 없는 결말을 지어내지 않는다.
      runSummary: null,
      progressLabel: `Step ${steps.length}개`,
    },
    /*
      T079·T105 — 브라우저를 여는 조작이 ③-a 대상 앱 슬롯 **안에** 있다 (FR-244·FR-261).

      2회차: 이 자리의 높이는 118px 다 (`layout.ts` 의 `editing.targetSlot`). 1회차에는
      남는 높이 전부(약 700px)를 가져갔고, 담는 것은 안내 두 줄과 버튼 하나였다
      (spec S-12). **자리를 없애지 않고 줄인다** — 없애면 「이 화면에는 원래 브라우저가
      없는 것」과 구별되지 않는다.
    */
    target: {
      kind: "open_browser",
      stepIndex: currentIndex >= 0 ? currentIndex : null,
      // 006 FR-203 — 저장하지 않은 변경이 있으면 라벨이 **먼저 저장한다는 사실**을 말한다.
      label: pending > 0 ? SAVE_THEN_OPEN_BROWSER : undefined,
    },
    /*
      ③-b 국면 작업 영역 — **편집 국면에서 실제로 하는 일이 여기 있다** (FR-257).

      2회차: 이 자리가 남는 높이 전부를 갖는다 (`layout.ts` 의 `editing.workArea`).
      1회차에는 같은 내용이 42px 띠(최대 45%)에 들어갔다 — 그것이 사용자가 다시 제기한
      것이고, 「국면 보조 영역」이라는 이름이 그 판단을 유도했다 (FR-218e-1).
    */
    work: {
      kind: "edit_fields",
      pendingCount: pending,
      warnings: [],
      stale,
      savedName,
      fields: (
        <EditFields
          sensitiveNames={sensitiveNames}
          ops={ops}
          steps={dslSteps}
          onRevert={revert}
          /*
            008 — Step 상세가 이 자리에 인라인으로 걸리면(`DETAIL_PLACEMENT.editing`)
            빈 상태 안내를 그리지 않는다. 「고칠 Step 을 고르세요」와 그 Step 의 편집면이
            함께 떠 있으면 화면이 두 가지를 주장한다.
          */
          stepFocused={selected !== null}
        />
      ),
    },
    steps,
    focusedStepId: selected,
    detail:
      detailOpen && current !== null
        ? {
            step: current,
            index: currentIndex,
            // 편집 국면에는 그때의 시도 기록이 없다 — 그것은 결과 국면의 축이다.
            attempts: null,
            candidates:
              "target" in current
                ? current.target
                : current.type === "assertion"
                  ? (current.assertion.target ?? null)
                  : null,
            dropCandidates: current.type === "drag" ? current.drop_target : null,
            repickWaiting: null,
            failure: null,
          }
        : null,
    capabilities,
    notices,
    authoring: test.authoring_mode === "ai" ? "ai" : "record",
    pacing: null,
  };

  return (
    <>
      <Workbench
        model={model}
        phaseActions={phaseActions}
        headerActions={headerActions}
        /*
          009 FR-298 — 행 조작. `rowActions` 자리는 007 이 열어 두었고 넘기는 화면이
          없었다 (관찰 M-08). 이 화면이 첫 소비자다.
        */
        rowActions={(step) =>
          confirmDelete === step.id ? (
            <ConfirmDelete
              label={step.label}
              onConfirm={() => {
                apply({ op: "delete", step_id: step.id });
                setConfirmDelete(null);
              }}
              onCancel={() => setConfirmDelete(null)}
            />
          ) : (
            <StepRowOps
              index={step.index}
              total={steps.length}
              label={step.label}
              capabilities={capabilities}
              busy={saving}
              onRun={runRowAction}
            />
          )
        }
        stepEmptyNotice="이 테스트에는 Step 이 없습니다."
        stepFooter={
          <ActionPalette
            capabilities={capabilities}
            onRun={runAction}
            onRemedy={runAction}
            narrow={narrowByPick}
            /*
              이 국면에서 자리가 다른 둘 — 브라우저 열기는 대상 앱 영역(T079), 충돌
              중의 덮어쓰기는 「다시 읽기」와 짝을 이루는 보조 영역(FR-209)이 갖는다.
            */
            hidden={stale !== null ? ["browser.openAt", "save.overwriteStale"] : ["browser.openAt"]}
            nl={{ value: "", onChange: () => undefined, onSubmit: () => undefined }}
            insert={{
              open: insertOpen,
              form: (
                <InsertStepForm
                  atLabel={insertAtLabel}
                  busy={saving}
                  capability={capabilities["step.insertManual"]}
                  browserCapability={narrowByPick(
                    "browser.openAt",
                    capabilities["browser.openAt"],
                  )}
                  onSubmit={submitInsert}
                  onOpenBrowser={() => runAction("browser.openAt")}
                  onCancel={() => setInsertOpen(false)}
                />
              ),
            }}
            name={test.name}
            onNameChange={(v) => apply({ op: "set_name", name: v })}
            startUrl={test.start_url}
            onStartUrlChange={(v) => apply({ op: "set_start_url", url: v })}
            instruction={test.ai_instruction ?? null}
            saveLabel={saveEditsLabel(pending, saving)}
            stepCount={dslSteps.length}
            emptyHint="이 테스트에는 Step 이 없습니다."
          />
        }
        onSelectStep={(stepId) => {
          setSelected(stepId);
          setDetailOpen(true);
        }}
        onCloseDetail={() => setDetailOpen(false)}
        /*
          편집 국면의 나머지 필드(`tab`·`url`·`기대값`)를 상세 **안**에 얹는다.
          자리를 따로 만들면 국면마다 다른 상세가 다시 생긴다 (FR-230).
        */
        /* 편집면은 `stepDetailExtra` 가 갖는다 — 상세가 자기 입력을 또 그리면 중복이다 */
        stepDetailOwnFields={false}
        stepDetailExtra={
          current !== null ? (
            <>
              {/* Step 종류는 편집 대상이 아니다 — 지우고 새로 넣는 일이다 (006 FR-191). */}
              <p className="why" style={{ margin: 0 }}>
                {lockedFieldNotice(
                  lockedReason("steps[].type") ?? "delete_and_insert_instead",
                )}
              </p>
              <StepEditFields
                step={current}
                sensitiveNames={sensitiveNames}
                editable={editable}
                onChange={(patch) => apply({ op: "update", step_id: current.id, ...patch })}
              />
              {/*
                006 FR-191 — 잠긴 대상은 **모두** 이유를 밝힌다. 서버가 세 가지를
                보내는데 화면이 하나만 쓰면 `drag`·`assertion` Step 을 고른 사용자는
                왜 못 고치는지 알 수 없다.
              */}
              {"target" in current && (
                <p className="why" style={{ margin: 0 }}>
                  {lockedFieldNotice(lockedReason("steps[].target") ?? "live_browser_required")}
                </p>
              )}
              {current.type === "drag" && (
                <p className="why" style={{ margin: 0 }}>
                  {lockedFieldNotice(
                    lockedReason("steps[].drop_target") ?? "live_browser_required",
                  )}
                </p>
              )}
              {current.type === "assertion" && current.assertion.target && (
                <p className="why" style={{ margin: 0 }}>
                  {lockedFieldNotice(
                    lockedReason("steps[].assertion.target") ?? "live_browser_required",
                  )}
                </p>
              )}
            </>
          ) : null
        }
        onSaveStep={(patch) => {
          if (current === null) return;
          apply({ op: "update", step_id: current.id, ...patch });
        }}
        onOpenBrowser={openBrowser}
        onReloadDefinition={load}
        onOverwriteStale={() => runAction("save.overwriteStale")}
        onAction={runAction}
        busy={saving}
      />

      {/* ─── 이탈 확인 (006 FR-208 · ui-contract §6) ────────────────────────── */}
      {leaving !== null && (
        <div
          role="alertdialog"
          aria-label="저장하지 않은 변경 확인"
          className="modal-scrim"
          style={{
            position: "fixed",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 30,
          }}
        >
          <div className="modal" style={{ width: 520, padding: 24 }}>
            <strong className="subtitle">{unsavedLeaveWarning(pending)}</strong>
            <div className="row" style={{ gap: 8, marginTop: 12 }}>
              <button
                onClick={() => {
                  const next = leaving;
                  setLeaving(null);
                  save();
                  next();
                }}
              >
                저장하고 나가기
              </button>
              <button
                className="secondary"
                onClick={() => {
                  const next = leaving;
                  setOps([]);
                  setLeaving(null);
                  next();
                }}
              >
                버리고 나가기
              </button>
              <button className="ghost" onClick={() => setLeaving(null)}>
                머무르기
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/**
 * 국면 보조 영역의 편집 국면 고유 내용.
 *
 * 테스트 이름·시작 주소·지시문은 **조작 팔레트**가 갖는다 (FR-235 — 조작마다 집이
 * 하나다). 여기 남는 것은 조작이 아닌 것 둘 — 민감 변수 공개와 개별 되돌리기다.
 */
function EditFields({
  sensitiveNames,
  ops,
  steps,
  onRevert,
  stepFocused,
}: {
  sensitiveNames: string[];
  ops: EditOp[];
  steps: Step[];
  onRevert: (index: number) => void;
  /** 이 자리에 Step 편집면이 함께 걸려 있는가 (008 · `DETAIL_PLACEMENT.editing`) */
  stepFocused: boolean;
}) {
  /*
    008 — **빈 자리를 빈 채로 두지 않는다.**

    이 영역은 007 2회차에 남는 높이 전부를 갖게 됐다 (FR-257). 그런데 담을 것이
    「민감 변수 안내」와 「저장하지 않은 변경」 둘뿐이라, 갓 들어온 편집 화면에서는 둘 다
    비어 화면의 절반이 아무 말도 하지 않았다. 1회차에는 같은 내용이 42px 띠에 있어서
    보이지 않던 공백이다.

    무엇을 하면 되는지 말한다 — 자리를 없애지는 않는다 (FR-261).
  */
  if (!stepFocused && sensitiveNames.length === 0 && ops.length === 0) {
    return (
      <div
        data-edit-fields-empty
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
          textAlign: "center",
        }}
      >
        <svg className="dim" width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="3" y="5" width="26" height="6" rx="1.5" />
          <rect x="3" y="13" width="26" height="6" rx="1.5" strokeDasharray="3 3" />
          <rect x="3" y="21" width="26" height="6" rx="1.5" strokeDasharray="3 3" />
        </svg>
        <div className="strong-sm">고칠 Step 을 고르세요</div>
        <div className="why" style={{ maxWidth: 420 }}>
          오른쪽 목록에서 Step 을 누르면 상세가 열립니다. 값 · 순서 · 삭제는 브라우저 없이
          고칠 수 있고, 고친 것은 여기에 「저장하지 않은 변경」으로 쌓입니다.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* FR-212 — 어떤 변수가 민감인지 밝히고, 값은 화면에 오지 않는다고 말한다. */}
      {sensitiveNames.length > 0 && (
        <p className="why" style={{ margin: 0 }}>
          민감 변수 <span className="mono">{sensitiveNames.join(", ")}</span> (값은 표시되지
          않습니다)
        </p>
      )}

      {/* 개별 되돌리기 (006 FR-190). 되돌리기는 연산을 목록에서 빼는 것이다. */}
      {ops.length > 0 && (
        <div>
          <strong className="lbl">저장하지 않은 변경</strong>
          <ul className="why" style={{ margin: "6px 0 0", paddingLeft: 18 }}>
            {ops.map((op, i) => (
              <li key={`${op.op}-${i}`} className="row" style={{ gap: 6 }}>
                <span className="mono spacer">{describeOp(op, steps)}</span>
                <button className="navlink" onClick={() => onRevert(i)}>
                  되돌리기
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** 변경 하나를 사람이 읽을 수 있게 적는다. 무엇을 되돌리는지 알아야 고를 수 있다. */
function describeOp(op: EditOp, steps: Step[]): string {
  const numberOf = (id: string) => {
    const at = steps.findIndex((s) => s.id === id);
    return at >= 0 ? stepNumber(at) : id;
  };
  switch (op.op) {
    case "insert":
      return `Step ${stepNumber(op.at)} 자리에 ${manualStepLabel(op.spec)} 추가`;
    case "update": {
      const fields = [
        op.label !== undefined ? "이름" : null,
        op.value !== undefined ? "입력값" : null,
        op.timeout_ms !== undefined ? "대기 시간" : null,
        op.tab !== undefined ? "탭" : null,
        op.url !== undefined ? "주소" : null,
        op.assertion_value !== undefined ? "기대값" : null,
      ].filter((f): f is string => f !== null);
      return `Step ${numberOf(op.step_id)} · ${fields.join("·")} 수정`;
    }
    case "delete":
      return `Step ${op.step_id} 삭제`;
    case "reorder":
      return "Step 순서 변경";
    case "set_name":
      return `테스트 이름 → ${op.name}`;
    case "set_start_url":
      return `시작 주소 → ${op.url}`;
  }
}
