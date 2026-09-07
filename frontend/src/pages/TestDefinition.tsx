/**
 * **확정 디자인에 대응 화면이 없다** — 8종 artboard 어디에도 정의 화면이 없다.
 * 1:1 대조 의무가 적용되지 않고(DC-010) 대신 8화면의 시각 언어를 따른다:
 * 3px 잉크 테두리, 직각, 하드 오프셋 그림자.
 *
 * 저장된 테스트의 **편집 화면** (006 US1·US2 · FR-179).
 *
 * **실행하지 않고 볼 수 있어야 한다.** 이 화면이 생기기 전에는 Step 목록과 후보를 보려면
 * 재실행 세션을 시작해야 했다 — 브라우저를 띄우고 대상 앱에 접속해야 Step 하나를 확인할
 * 수 있었다는 뜻이다.
 *
 * **006 이 그 논리를 편집까지 연장했다.** 이 화면은 읽기 전용이었고, "대상을 다시
 * 지정하려면 실행을 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로 가는 버튼을 주지
 * 않았다 (E-02·E-03). 결과 화면의 「Step nn 고치기」도 이 읽기 전용 화면으로 데려왔다
 * (E-04) — 이름이 「고치기」인데 고칠 수 없었다.
 *
 * 이제 화면은 하나이고 **모드가 둘**이다 (ui-contract §2):
 *
 * - 편집 가능 — 평상시. 값·라벨·대기시간·탭·순서·삭제·이름·시작주소를 고친다
 * - 읽기 전용 — 그 테스트가 실행 중일 때. 컨트롤을 **감추지 않고** 비활성으로 두고 이유를
 *   붙인다 (감추면 사용자는 자기가 잘못 들어온 줄 안다)
 *
 * **초안은 편집 연산 목록이다** (research R3). 화면이 편집 결과를 서버에 보내면 "어느 Step
 * 종류가 값을 갖는가" 같은 판정이 여기로 넘어오고, 그것이 편집 규칙의 두 번째 구현이 된다.
 * 연산을 보내면 서버의 `step_edits` 가 유일한 구현으로 남는다. 연산 개수가 곧 변경
 * 건수이고(FR-189), 되돌리기는 목록에서 빼는 것이다(FR-190).
 *
 * **초안을 브라우저 저장소에 넣지 않는다** (research R8). 정의 파일이 유일한 진실이므로,
 * 낡은 초안이 남으면 어느 쪽이 맞는지 화면이 말할 수 없는 상태가 된다.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { definition, type DefinitionView, type EditOp } from "../api/client";
import { LocatorPriorityTable } from "../components/LocatorPriorityTable";
import { StepEditFields } from "../components/StepEditFields";
import { AuthoringBadge, AuthorBadge, StepTypeBadge, TabBadge } from "../components/Badges";
import type { Step } from "../types/generated/step";
import type { Test } from "../types/generated/step-dsl";
import {
  EDIT_BLOCKED_BY_RUN,
  OPEN_RUNNING_SESSION,
  SAVE_BEFORE_OPEN_BROWSER,
  SAVE_THEN_OPEN_BROWSER,
  STALE_OVERWRITE_LABEL,
  editSavedNotice,
  lockedFieldNotice,
  openBrowserAtStepLabel,
  runFromLabel,
  saveEditsLabel,
  staleReloadLabel,
  stepLabel,
  stepNumber,
  unsavedLeaveWarning,
} from "../lib/wording";

export interface TestDefinitionProps {
  testId: string;
  /** 결과 화면에서 실패한 Step 을 지목해 들어온 경우 (FR-056·FR-180). */
  focusStepId?: string | null;
  onBack: () => void;
  onRun?: (testId: string, fromStepIndex?: number) => void;
  /**
   * 브라우저 편집 세션을 연다 (FR-200). 지정한 Step 직전에서 멈춘다.
   *
   * `stepId` 를 함께 넘기는 이유는 세션이 끝난 뒤 **이 화면의 이 Step 으로** 돌아오기
   * 위해서다 (FR-204). 인덱스가 아니라 id 로 넘긴다 — 세션에서 Step 을 지우거나 순서를
   * 바꿨으면 인덱스는 다른 Step 을 가리킨다.
   */
  onOpenBrowserAt?: (
    testId: string,
    stepIndex: number,
    stepId: string | null,
  ) => void;
  /** 실행 중이라는 안내가 가리킨 세션으로 이동한다 (005 FR-126). */
  onOpenSession?: (sessionId: string) => void;
}

function valueOf(step: Step): string | null {
  if (step.type === "fill" || step.type === "select") return step.value;
  if (step.type === "navigate") return step.url;
  return null;
}

/** 민감 값은 참조로만 저장된다 (FR-082). 참조는 그대로 보여도 안전하다. */
function isReference(value: string): boolean {
  return /^\{\{[A-Z][A-Z0-9_]*\}\}$/.test(value);
}

/**
 * 편집 연산 목록을 저장된 정의에 **표시용으로** 얕게 적용한다.
 *
 * **판정하지 않는다** (data-model §5). 여기서 "이 종류는 값을 못 갖는다" 를 결정하면
 * 서버와 두 벌이 된다. 서버가 거절하면 그 문구를 그대로 보여준다.
 */
function preview(test: Test, ops: EditOp[]): Test {
  let steps = test.steps as unknown as Step[];
  let name = test.name;
  let startUrl = test.start_url;

  for (const op of ops) {
    if (op.op === "update") {
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
  if (next.op === "reorder" || next.op === "set_name" || next.op === "set_start_url") {
    // 마지막 것만 의미가 있다. 쌓아 두면 변경 건수가 실제로 바뀐 것보다 많아진다.
    return [...ops.filter((o) => o.op !== next.op), next];
  }
  return [...ops, next];
}

export function TestDefinition({
  testId,
  focusStepId = null,
  onBack,
  onRun,
  onOpenBrowserAt,
  onOpenSession,
}: TestDefinitionProps) {
  const [view, setView] = useState<DefinitionView | null>(null);
  const [ops, setOps] = useState<EditOp[]>([]);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [selected, setSelected] = useState<string | null>(focusStepId);
  const [saving, setSaving] = useState(false);
  const [savedName, setSavedName] = useState<string | null>(null);
  /** 외부 변경 충돌. 화면을 옮기지 않고 그 자리에서 두 선택을 준다 (FR-209). */
  const [stale, setStale] = useState<{ revision: string } | null>(null);
  /** 이탈 확인 대기 중인 다음 행동 (FR-208). */
  const [leaving, setLeaving] = useState<null | (() => void)>(null);

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
  useEffect(() => setSelected(focusStepId), [focusStepId]);

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

  const revert = (index: number) =>
    setOps((prev) => prev.filter((_, i) => i !== index));

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
  const test = useMemo(
    () => (view === null ? null : preview(view.test, ops)),
    [view, ops],
  );

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

  const steps = test.steps as unknown as Step[];
  const current = steps.find((s) => s.id === selected) ?? null;
  const currentIndex = current ? steps.findIndex((s) => s.id === current.id) : -1;
  const sensitive = (test.variables ?? []).filter((v) => v.sensitive);
  const sensitiveNames = sensitive.map((v) => v.name);
  const editable = view.editable;
  const lockedReason = (field: string) =>
    view.locked_fields.find((f) => f.field === field)?.reason ?? null;

  const move = (index: number, delta: number) => {
    const to = index + delta;
    if (to < 0 || to >= steps.length) return;
    // `noUncheckedIndexedAccess` 아래에서 자리 맞바꾸기를 안전하게 표현한다.
    const ids = steps.map((s) => s.id);
    const order = ids.map((id, i) => (i === index ? ids[to] : i === to ? ids[index] : id));
    apply({ op: "reorder", order: order as string[] });
  };

  const openBrowserHere = () => {
    if (current === null || currentIndex < 0 || onOpenBrowserAt === undefined) return;
    onOpenBrowserAt(testId, currentIndex, current.id);
  };

  return (
    <main style={{ maxWidth: 1080, margin: "24px auto", padding: "0 16px" }}>
      <div className="row" style={{ gap: 10 }}>
        <div>
          <div className="dim mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
            TEST DEFINITION
          </div>
          {/* 저장된 테스트를 고치는 화면이다 — 「초안」이 아니다 (005 U-03 과 같은 뿌리). */}
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 24, margin: 0 }}>
            {test.name}
          </h1>
        </div>
        <span className="mono dim">{test.id}</span>
        <AuthoringBadge mode={test.authoring_mode as "record" | "ai"} />
        <span className="spacer" />
        {onRun && (
          <button className="secondary" disabled={!editable} onClick={() => guard(() => onRun(test.id))}>
            ▶ 실행
          </button>
        )}
        <button className="secondary" onClick={() => guard(onBack)}>
          목록으로
        </button>
      </div>

      {/* 실행 중이면 화면은 열리되 읽기 전용이다 (FR-206). 감추지 않고 이유를 붙인다. */}
      {!editable && (
        <div
          role="status"
          className="row"
          style={{
            gap: 10,
            border: "3px solid var(--ink)",
            background: "#FFF6D8",
            padding: "10px 14px",
            marginTop: 12,
          }}
        >
          <strong style={{ fontSize: 13 }}>{EDIT_BLOCKED_BY_RUN}</strong>
          <span className="spacer" />
          {view.blocking_session_id && onOpenSession && (
            <button onClick={() => onOpenSession(view.blocking_session_id as string)}>
              {OPEN_RUNNING_SESSION}
            </button>
          )}
        </div>
      )}

      <p className="muted" style={{ fontSize: 12.5 }}>
        시작 주소{" "}
        <input
          aria-label="시작 주소"
          className="mono"
          value={test.start_url}
          disabled={!editable}
          maxLength={2000}
          style={{ width: 340 }}
          onChange={(e) => apply({ op: "set_start_url", url: e.target.value })}
        />{" "}
        · Step {steps.length}개
        {sensitive.length > 0 && (
          <>
            {" "}
            · 민감 변수{" "}
            <span className="mono">{sensitiveNames.join(", ")}</span>{" "}
            (값은 표시되지 않습니다)
          </>
        )}
      </p>

      <label className="row" style={{ gap: 8, fontSize: 12.5 }}>
        <span className="dim">테스트 이름</span>
        <input
          aria-label="테스트 이름"
          value={test.name}
          disabled={!editable}
          maxLength={200}
          onChange={(e) => apply({ op: "set_name", name: e.target.value })}
        />
      </label>

      {test.ai_instruction && (
        <div
          style={{
            border: "3px solid var(--ai)",
            background: "var(--ai-tint)",
            padding: 18,
            marginTop: 12,
          }}
        >
          <strong style={{ fontSize: 12 }}>작성 의도 (지시문)</strong>
          <p style={{ margin: "4px 0 0", fontSize: 13, whiteSpace: "pre-wrap" }}>
            {test.ai_instruction}
          </p>
          <p className="dim" style={{ margin: "6px 0 0", fontSize: 11.5 }}>
            이 문장은 기록일 뿐 실행 대상이 아닙니다. 다시 돌릴 때는 아래 Step 만
            실행합니다. {lockedFieldNotice("record_only")}
          </p>
        </div>
      )}

      {/* ─── 저장 영역 (ui-contract §3) ─────────────────────────────────── */}
      <div
        className="row"
        style={{
          gap: 10,
          border: "3px solid var(--ink)",
          background: "var(--paper)",
          boxShadow: "6px 6px 0 var(--ink)",
          padding: "12px 14px",
          marginTop: 16,
        }}
      >
        <button disabled={!editable || saving || pending === 0} onClick={() => save()}>
          {saveEditsLabel(pending, saving)}
        </button>
        {pending > 0 && (
          <button className="ghost" disabled={saving} onClick={() => setOps([])}>
            변경 전부 되돌리기
          </button>
        )}
        <span className="spacer" />
        {savedName !== null && (
          <span role="status" style={{ color: "#1F7A3D", fontSize: 13, fontWeight: 600 }}>
            ✓ {editSavedNotice(savedName)}
          </span>
        )}
      </div>

      {/* 저장 성공 뒤 그 자리에서 다시 실행을 건다 (US2 시나리오 2). */}
      {savedName !== null && onRun && (
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          {currentIndex > 0 && (
            <button className="secondary" onClick={() => onRun(test.id, currentIndex)}>
              {runFromLabel(currentIndex)}
            </button>
          )}
          <button className="secondary" onClick={() => onRun(test.id)}>
            {runFromLabel(0)}
          </button>
        </div>
      )}

      {/* 저장을 막지 않는 것들 (FR-216 · 순서 변경 경고). */}
      {view.warnings.length > 0 && (
        <ul style={{ marginTop: 10, fontSize: 12.5, color: "#8A6A16" }}>
          {view.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      {/* ─── 외부 변경 충돌 (FR-209 · ui-contract §7) ───────────────────── */}
      {stale !== null && (
        <div
          role="alert"
          style={{
            border: "3px solid var(--ink)",
            background: "#FFF6D8",
            padding: 14,
            marginTop: 12,
          }}
        >
          <strong style={{ fontSize: 13 }}>
            ⚠ 이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.
          </strong>
          <p style={{ fontSize: 12.5, margin: "6px 0 10px" }}>
            파일 밖에서 고친 내용이 있습니다. 어떻게 할지 고르세요.
          </p>
          <div className="row" style={{ gap: 8 }}>
            <button className="secondary" onClick={load}>
              {staleReloadLabel(pending)}
            </button>
            <button onClick={() => save(stale.revision)}>{STALE_OVERWRITE_LABEL}</button>
          </div>
        </div>
      )}

      {/* ─── 이탈 확인 (FR-208 · ui-contract §6) ────────────────────────── */}
      {leaving !== null && (
        <div
          role="alertdialog"
          aria-label="저장하지 않은 변경 확인"
          style={{
            border: "3px solid var(--ink)",
            background: "var(--paper)",
            boxShadow: "6px 6px 0 var(--ink)",
            padding: 14,
            marginTop: 12,
          }}
        >
          <strong style={{ fontSize: 13 }}>{unsavedLeaveWarning(pending)}</strong>
          <div className="row" style={{ gap: 8, marginTop: 10 }}>
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
      )}

      {error !== null && (
        <div style={{ marginTop: 12 }}>
          <ErrorNotice error={error} />
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: current === null ? "1fr" : "1fr 460px",
          gap: 16,
          marginTop: 16,
          alignItems: "start",
        }}
      >
        <div
          style={{
            border: "3px solid var(--ink)",
            background: "var(--paper)",
            boxShadow: "6px 6px 0 var(--ink)",
            overflow: "hidden",
          }}
        >
          {steps.map((step, index) => (
            <div
              key={step.id}
              className="row"
              style={{
                width: "100%",
                gap: 10,
                padding: "10px 14px",
                borderTop: index === 0 ? "none" : "2px solid var(--border)",
                background: step.id === selected ? "var(--surface)" : "var(--paper)",
              }}
            >
              <button
                onClick={() => setSelected(step.id === selected ? null : step.id)}
                className="row"
                style={{
                  flex: 1,
                  gap: 10,
                  textAlign: "left",
                  border: "none",
                  boxShadow: "none",
                  background: "transparent",
                  cursor: "pointer",
                }}
              >
                <span className="mono dim" style={{ width: 28 }}>
                  {stepNumber(index)}
                </span>
                <StepTypeBadge type={step.type} />
                <span className="spacer">{step.label}</span>
                {valueOf(step) !== null && (
                  <span className="mono dim" style={{ fontSize: 11.5 }}>
                    {isReference(valueOf(step) as string)
                      ? valueOf(step)
                      : `"${valueOf(step)}"`}
                  </span>
                )}
                <TabBadge tab={step.tab} />
                <AuthorBadge author={step.author} />
              </button>
              <button
                className="ghost"
                aria-label={`${stepLabel(index)} 위로`}
                disabled={!editable || index === 0}
                onClick={() => move(index, -1)}
              >
                ↑
              </button>
              <button
                className="ghost"
                aria-label={`${stepLabel(index)} 아래로`}
                disabled={!editable || index === steps.length - 1}
                onClick={() => move(index, 1)}
              >
                ↓
              </button>
              <button
                className="ghost"
                aria-label={`${stepLabel(index)} 삭제`}
                disabled={!editable}
                style={{ color: "#A83A22" }}
                onClick={() => apply({ op: "delete", step_id: step.id })}
              >
                삭제
              </button>
            </div>
          ))}
        </div>

        {current !== null && (
          <div
            style={{
              border: "3px solid var(--ink)",
              background: "var(--paper)",
              boxShadow: "6px 6px 0 var(--ink)",
              padding: 18,
            }}
          >
            <div className="row" style={{ gap: 8 }}>
              <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
                {current.id.toUpperCase()} · {current.type.toUpperCase()}
              </strong>
              <span className="spacer" />
              <button className="ghost" onClick={() => setSelected(null)}>
                닫기
              </button>
            </div>

            {/* Step 종류는 편집 대상이 아니다 — 지우고 새로 넣는 일이다 (FR-191). */}
            <p className="dim" style={{ fontSize: 11.5, margin: "6px 0 0" }}>
              {lockedFieldNotice(lockedReason("steps[].type") ?? "delete_and_insert_instead")}
            </p>

            <StepEditFields
              step={current}
              sensitiveNames={sensitiveNames}
              editable={editable}
              onChange={(patch) =>
                apply({ op: "update", step_id: current.id, ...patch })
              }
            />

            {/*
              FR-191 — 잠긴 대상은 **모두** 이유를 밝힌다. 서버가 `locked_fields` 로 세
              가지(`target`·`drop_target`·`assertion.target`)를 보내는데 화면이 하나만
              쓰면, `drag`·`assertion` Step 을 고른 사용자는 왜 못 고치는지 알 수 없다
              (converge T095).
            */}
            {"target" in current && (
              <div style={{ marginTop: 14 }}>
                <LocatorPriorityTable
                  target={current.target}
                  title={current.type === "drag" ? "끄는 대상" : "대상 요소"}
                />
                <p className="dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
                  {lockedFieldNotice(
                    lockedReason("steps[].target") ?? "live_browser_required",
                  )}
                </p>
              </div>
            )}
            {current.type === "drag" && (
              <div style={{ marginTop: 12 }}>
                <LocatorPriorityTable target={current.drop_target} title="놓는 위치" />
                <p className="dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
                  {lockedFieldNotice(
                    lockedReason("steps[].drop_target") ?? "live_browser_required",
                  )}
                </p>
              </div>
            )}
            {current.type === "assertion" && current.assertion.target && (
              <div style={{ marginTop: 12 }}>
                <LocatorPriorityTable target={current.assertion.target} title="검증 대상" />
                <p className="dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
                  {lockedFieldNotice(
                    lockedReason("steps[].assertion.target") ?? "live_browser_required",
                  )}
                </p>
              </div>
            )}

            {/*
              FR-202 — 브라우저가 필요한 편집은 **왜 필요한지와 가는 길**을 함께 준다.
              회색 버튼만 두지 않는다. 이 자리가 006 이 없앤 E-03 의 자리다.
            */}
            <div
              style={{
                borderTop: "2px solid var(--border)",
                marginTop: 14,
                paddingTop: 12,
              }}
            >
              <p className="dim" style={{ fontSize: 11.5, margin: 0 }}>
                요소 다시 집기, 직접 조작으로 Step 추가, 자연어로 Step 추가, 검증 추가는
                살아 있는 화면에서만 됩니다.
              </p>
              {onOpenBrowserAt && (
                <div style={{ marginTop: 8 }}>
                  {pending > 0 && (
                    <p className="dim" style={{ fontSize: 11.5, margin: "0 0 6px" }}>
                      {SAVE_BEFORE_OPEN_BROWSER}
                    </p>
                  )}
                  <button
                    disabled={!editable || saving}
                    onClick={() => {
                      if (pending > 0) {
                        // 두 경로가 같은 Step 을 다르게 들고 있는 상태를 만들지 않는다
                        // (FR-203). 저장이 끝난 뒤에 세션을 연다.
                        setSaving(true);
                        void definition
                          .save(testId, view.revision, ops)
                          .then((v) => {
                            setView(v);
                            setOps([]);
                            setSavedName(v.test.name);
                            openBrowserHere();
                          })
                          .catch((exc: unknown) => setError(describeError(exc)))
                          .finally(() => setSaving(false));
                        return;
                      }
                      openBrowserHere();
                    }}
                  >
                    {pending > 0
                      ? SAVE_THEN_OPEN_BROWSER
                      : openBrowserAtStepLabel(currentIndex)}
                  </button>
                </div>
              )}
            </div>

            {/* 개별 되돌리기 (FR-190). 되돌리기는 연산을 목록에서 빼는 것이다. */}
            {pending > 0 && (
              <div style={{ marginTop: 14 }}>
                <strong style={{ fontSize: 11.5 }}>저장하지 않은 변경</strong>
                <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12 }}>
                  {ops.map((op, i) => (
                    <li key={`${op.op}-${i}`} className="row" style={{ gap: 6 }}>
                      <span className="mono spacer">{describeOp(op, steps)}</span>
                      <button className="ghost" onClick={() => revert(i)}>
                        되돌리기
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

/** 변경 하나를 사람이 읽을 수 있게 적는다. 무엇을 되돌리는지 알아야 고를 수 있다. */
function describeOp(op: EditOp, steps: Step[]): string {
  const numberOf = (id: string) => {
    const at = steps.findIndex((s) => s.id === id);
    return at >= 0 ? stepNumber(at) : id;
  };
  switch (op.op) {
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
