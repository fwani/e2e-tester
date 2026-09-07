/**
 * Interactive Runner — 일시정지 / 편집.
 * **`docs/design/RunnerPaused.dc.html`(1440×900) 전사.** DC-001~DC-008.
 *
 * 001 에서는 `Runner.tsx` 안의 조건부 패널이었다. 확정 디자인이 독립 artboard 로
 * 정의하므로 독립 화면으로 분리했다 (DC-008).
 *
 * **중지 후 검토(`review`)도 이 화면이 맡는다** (DR-010~DR-013). 브라우저는 없지만
 * 기록된 Step 을 보고 고치고 저장할 수 있어야 한다 — 001 에서는 중지하는 순간 목록으로
 * 튕겨 나가 기록이 통째로 유실됐다.
 */
import { useState, type ReactNode } from "react";

import type { AddAssertionBody, RunPacing } from "../api/client";
import type { Step } from "../types/generated/step";
import { AssertionForm } from "../components/AssertionForm";
import { BrowserFrame } from "../components/design/BrowserFrame";
import { stepLabel, stepNumber } from "../lib/wording";

import {
  DesignStepRow,
  StepPanelHeader,
  type StepOutcome,
} from "../components/design/DesignStepList";
import {
  Artboard,
  BrandMark,
  Breadcrumb,
  HeaderBar,
  HeaderDivider,
  StatusPill,
} from "../components/design/Chrome";

export interface RunnerPausedProps {
  title: string;
  /** 어떻게 만드는 세션인가. AI 세션이 멈춰도 배지는 `AI` 여야 한다 — `RECORD` 로 바뀌면
   *  사용자는 다른 모드로 갈아탄 줄 안다 (UX U-07). */
  authoring?: "record" | "ai";
  testId: string;
  /** 중지 후 검토 상태. 브라우저가 없으므로 브라우저 명령을 감춘다 (001 FR-043a). */
  review: boolean;
  currentStepIndex: number;
  editWarnings: string[];
  steps: Step[];
  outcomeOf: (step: Step, index: number) => StepOutcome;
  durationOf: (step: Step) => number | undefined;
  busy: boolean;
  currentUrl: string;
  /** 지금 미러가 보고 있는 탭. 검증 Step 의 기본 대상이 된다 (FR-037). */
  mirroredTab: number;
  mirror: ReactNode;
  tabs?: ReactNode;
  banners?: ReactNode;
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;

  reordering: boolean;
  saveName: string;
  onSaveNameChange: (name: string) => void;
  onSave: () => void;
  onResume: () => void;
  onStop: () => void;
  onRecordActionsStart: () => void;
  onRecordActionsStop: () => void;
  onAddAssertion: (body: AddAssertionBody) => void;
  onEditStep: (stepId: string) => void;
  onToggleReorder: () => void;
  onApplyReorder: (order: string[]) => void;
  onRunFrom: (stepIndex: number) => void;
  onDeleteStep: (stepId: string) => void;
  onNaturalLanguage: (instruction: string) => void;
  onShowResult?: () => void;
  /**
   * 이 세션의 실행 속도 (004).
   *
   * **`한 스텝씩` 의 자동 일시정지와 사용자가 직접 누른 일시정지를 가르는 유일한
   * 근거다.** 둘은 상태가 `paused` 로 같아서 상태로는 구별할 수 없다. 구별하지 않으면
   * 한 스텝씩으로 돌리던 사용자는 왜 멈췄는지 몰라 중지를 누르게 된다.
   */
  pacing?: RunPacing;
  /** 실행 속도 컨트롤 (004). 멈춘 상태에서도 다음 Step 의 속도를 미리 고를 수 있다. */
  pacingControl?: ReactNode;
}

export function RunnerPaused(props: RunnerPausedProps) {
  const {
    title,
    authoring = "record",
    testId,
    review,
    currentStepIndex,
    editWarnings,
    steps,
    outcomeOf,
    durationOf,
    busy,
    currentUrl,
    mirroredTab,
    mirror,
    tabs,
    banners,
    selectedStepId,
    onSelectStep,
    reordering,
    saveName,
    onSaveNameChange,
    onSave,
    onResume,
    onStop,
    onRecordActionsStart,
    onAddAssertion,
    onEditStep,
    onToggleReorder,
    onApplyReorder,
    onRunFrom,
    onDeleteStep,
    onNaturalLanguage,
    onShowResult,
    pacing,
    pacingControl,
  } = props;

  const [nl, setNl] = useState("");
  const [assertOpen, setAssertOpen] = useState(false);

  /**
   * 자동 일시정지인가 (004 FR-108, research R7).
   *
   * `한 스텝씩` 의 멈춤과 사용자가 직접 누른 멈춤은 **상태가 같다** (`paused`). 새 상태를
   * 만들지 않는 것이 설계이므로, 구별의 근거는 상태가 아니라 속도다. 구별하지 않으면
   * 한 스텝씩으로 돌리던 사용자는 왜 멈췄는지 몰라 중지를 누른다.
   */
  const stepByStep = !review && pacing === "step";

  const selectedIndex = steps.findIndex((s) => s.id === selectedStepId);

  return (
    <Artboard width={1440} height={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <Breadcrumb testId={testId} />
        <div style={{ flex: "1" }} />
        <StatusPill background={review ? "#FFFDF6" : "#F5D000"} color="#14130F">
          <svg width="13" height="13" viewBox="0 0 16 16">
            <rect x="3" y="2" width="3.5" height="12" fill="currentColor" />
            <rect x="9.5" y="2" width="3.5" height="12" fill="currentColor" />
          </svg>
          {review ? "REVIEW" : stepByStep ? "STEP" : "PAUSED"}
        </StatusPill>
      </HeaderBar>

      <div
        style={{
          flex: "0 0 74px",
          borderBottom: "3px solid #14130F",
          background: "#EFEBE0",
          display: "flex",
          alignItems: "center",
          gap: "16px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
            fontSize: "26px",
            lineHeight: "1",
          }}
        >
          {title} 초안
        </div>
        <div style={{ font: "400 14px/1 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
          {review
            ? `기록된 Step ${steps.length}개 · 브라우저 종료됨`
            : `${stepLabel(currentStepIndex)} 이후 정지`}
        </div>
        <div style={{ flex: "1" }} />
        {/* 멈춘 상태에서도 다음 Step 의 속도를 미리 고를 수 있다. 검토 상태에는
            브라우저가 없어 적용할 실행이 없으므로 그리지 않는다. */}
        {!review && pacingControl}

        {onShowResult && (
          <button className="secondary" onClick={onShowResult} disabled={busy}>
            실행 결과 보기
          </button>
        )}

        {/* 검토 상태에는 브라우저가 없으므로 「계속하기」를 그리지 않는다 (001 FR-043a). */}
        {!review && (
          <button
            disabled={busy}
            onClick={onResume}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "9px",
              height: "46px",
              padding: "0 18px",
              border: "3px solid #14130F",
              background: "#14130F",
              color: "#F5F2E9",
              boxShadow: "5px 5px 0 #F5D000",
              font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 16 16">
              <path d="M4 2l10 6-10 6z" fill="currentColor" />
            </svg>
            계속하기
          </button>
        )}

        <button
          disabled={busy}
          onClick={onStop}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "9px",
            height: "46px",
            padding: "0 18px",
            border: "3px solid #14130F",
            background: "#FFFDF6",
            color: "#14130F",
            boxShadow: "5px 5px 0 #14130F",
            font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <rect x="3" y="3" width="10" height="10" fill="currentColor" />
          </svg>
          {review ? "나가기" : "중지"}
        </button>
      </div>

      {banners}

      {editWarnings.length > 0 && (
        <div
          role="status"
          style={{
            borderBottom: "3px solid #14130F",
            background: "#FFF9D6",
            padding: "10px 24px",
          }}
        >
          {editWarnings.map((w) => (
            <div key={w}>{w}</div>
          ))}
        </div>
      )}

      <div style={{ flex: "1", minHeight: "0", display: "flex" }}>
        <div style={{ flex: "1", minWidth: "0", padding: "20px", display: "flex", flexDirection: "column" }}>
          {tabs}
          <BrowserFrame
            url={currentUrl}
            badge={
              review
                ? { label: "SESSION ENDED", background: "#6B675C", color: "#FFFDF6" }
                : stepByStep
                  ? {
                      label: "한 스텝씩 — 다음 Step 을 기다립니다",
                      background: "#F5D000",
                      color: "#14130F",
                    }
                  : { label: "PAUSED", background: "#F5D000", color: "#14130F" }
            }
          >
            {mirror}
          </BrowserFrame>
        </div>

        <div
          style={{
            flex: "0 0 460px",
            borderLeft: "3px solid #14130F",
            background: "#FFFDF6",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <StepPanelHeader authoring={authoring} count={steps.length} />

          <div style={{ flex: "1", minHeight: "0", overflowY: "auto" }}>
            {steps.length === 0 && (
              <div style={{ padding: "16px 18px", color: "#9A968A" }}>
                기록된 Step 이 없습니다.
              </div>
            )}
            {steps.map((step, index) => (
              <DesignStepRow
                key={step.id}
                index={index}
                step={step}
                outcome={outcomeOf(step, index)}
                durationMs={durationOf(step)}
                selected={selectedStepId === step.id}
                paused={!review && index === currentStepIndex}
                onSelect={() => onSelectStep(step.id)}
              />
            ))}
          </div>

          {reordering && (
            <ReorderPanel
              steps={steps.map((s) => ({ id: s.id, label: s.label }))}
              busy={busy}
              onApply={onApplyReorder}
              onCancel={onToggleReorder}
            />
          )}

          <div
            style={{
              borderTop: "3px solid #14130F",
              background: "#EFEBE0",
              padding: "14px 18px 16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <div
              style={{
                font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace",
                letterSpacing: "0.12em",
                color: "#6B675C",
              }}
            >
              지금 할 수 있는 것
            </div>

            {/* 자연어로 Step 추가 (FR-078). 검토 상태에는 브라우저가 없어 감춘다. */}
            {!review && (
              <div style={{ display: "flex", gap: "10px" }}>
                <input
                  aria-label="자연어로 Step 추가"
                  value={nl}
                  onChange={(e) => setNl(e.target.value)}
                  placeholder="생성된 프로젝트가 목록에 있는지 확인해."
                  style={{
                    flex: "1",
                    minWidth: "0",
                    height: "48px",
                    minHeight: "48px",
                    padding: "0 12px",
                    border: "3px solid #7C4DDB",
                    background: "#FFFDF6",
                    font: "400 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
                  }}
                />
                <button
                  aria-label="자연어 Step 추가 실행"
                  disabled={busy || nl.trim() === ""}
                  onClick={() => {
                    onNaturalLanguage(nl.trim());
                    setNl("");
                  }}
                  style={{
                    flex: "0 0 48px",
                    height: "48px",
                    width: "48px",
                    padding: 0,
                    border: "3px solid #14130F",
                    background: "#7C4DDB",
                    color: "#FFFDF6",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "none",
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                    <path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3" />
                  </svg>
                </button>
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "10px" }}>
              {!review && (
                <ToolButton onClick={onRecordActionsStart} disabled={busy}>
                  <svg width="16" height="16" viewBox="0 0 20 20">
                    <circle cx="10" cy="10" r="5" fill="#D9502F" />
                  </svg>
                  직접 동작 추가
                </ToolButton>
              )}
              {!review && (
                <ToolButton onClick={() => setAssertOpen((v) => !v)} disabled={busy}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#14130F" strokeWidth="2.2">
                    <circle cx="8" cy="8" r="5.2" />
                    <circle cx="8" cy="8" r="1.4" fill="#14130F" />
                  </svg>
                  Assertion 추가
                </ToolButton>
              )}
              <ToolButton
                onClick={() => selectedStepId !== null && onEditStep(selectedStepId)}
                disabled={busy || selectedStepId === null}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#14130F" strokeWidth="2.2">
                  <path d="M11 2.5l2.5 2.5-8 8H3v-2.5z" />
                </svg>
                Step 수정
              </ToolButton>
              <ToolButton onClick={onToggleReorder} disabled={busy || steps.length < 2}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#14130F" strokeWidth="2.2">
                  <path d="M8 2.5v11M4.5 6L8 2.5 11.5 6M4.5 10L8 13.5 11.5 10" />
                </svg>
                순서 변경
              </ToolButton>
              {!review && (
                <ToolButton
                  onClick={() => selectedIndex >= 0 && onRunFrom(selectedIndex)}
                  disabled={busy || selectedIndex < 0}
                >
                  <svg width="16" height="16" viewBox="0 0 16 16">
                    <path d="M4 2l10 6-10 6z" fill="#14130F" />
                  </svg>
                  이 Step부터
                </ToolButton>
              )}
              <ToolButton
                danger
                onClick={() => selectedStepId !== null && onDeleteStep(selectedStepId)}
                disabled={busy || selectedStepId === null}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M3 5h10M6 5V3h4v2M4.5 5l0.7 8h5.6l0.7-8" />
                </svg>
                Step 삭제
              </ToolButton>
            </div>

            {assertOpen && !review && (
              <AssertionForm
                busy={busy}
                tab={mirroredTab}
                onSubmit={(body) => {
                  onAddAssertion(body);
                  setAssertOpen(false);
                }}
                onCancel={() => setAssertOpen(false)}
              />
            )}

            {/* 확정 디자인에 저장 영역이 없다 — 저장에는 이름이 필요하다 (FR-028·DC-009). */}
            <div style={{ display: "flex", gap: "10px", borderTop: "2px solid #DCD8CC", paddingTop: 12 }}>
              <input
                aria-label="테스트 이름"
                value={saveName}
                onChange={(e) => onSaveNameChange(e.target.value)}
                placeholder="테스트 이름"
                style={{ flex: 1, minHeight: "46px", border: "3px solid #14130F" }}
              />
              <button disabled={busy || steps.length === 0 || saveName.trim() === ""} onClick={onSave}>
                저장
              </button>
            </div>
            {steps.length === 0 && (
              <div style={{ color: "#6B675C", fontSize: 13 }}>Step 이 없으면 저장할 수 없습니다.</div>
            )}
          </div>
        </div>
      </div>
    </Artboard>
  );
}

function ToolButton({
  children,
  onClick,
  disabled,
  danger,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "9px",
        height: "46px",
        padding: "0 12px",
        border: `3px solid ${danger ? "#D9502F" : "#14130F"}`,
        background: danger ? "#FBEEEA" : "#FFFDF6",
        color: danger ? "#A83A22" : "#14130F",
        font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
        boxShadow: "none",
        justifyContent: "flex-start",
      }}
    >
      {children}
    </button>
  );
}

/**
 * 순서 변경 (FR-035).
 *
 * 드래그 앤 드롭을 쓰지 않는다. 목록이 200개까지 갈 수 있고(research R8) 드래그는 긴
 * 목록에서 정확히 놓기 어렵다. 위·아래 이동 버튼이 느리지만 틀리지 않는다.
 */
function ReorderPanel({
  steps,
  busy,
  onApply,
  onCancel,
}: {
  steps: { id: string; label: string }[];
  busy: boolean;
  onApply: (order: string[]) => void;
  onCancel: () => void;
}) {
  const [order, setOrder] = useState(steps.map((s) => s.id));
  const labelOf = (id: string) => steps.find((s) => s.id === id)?.label ?? id;

  const move = (index: number, delta: number) => {
    const next = [...order];
    const target = index + delta;
    const a = next[index];
    const b = next[target];
    if (target < 0 || target >= next.length || a === undefined || b === undefined) return;
    next[index] = b;
    next[target] = a;
    setOrder(next);
  };

  return (
    <div style={{ borderTop: "3px solid #14130F", background: "#FFFDF6", padding: 12, maxHeight: 260, overflowY: "auto" }}>
      <strong style={{ font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.12em" }}>
        순서 변경
      </strong>
      {order.map((id, index) => (
        <div key={id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
          <span className="mono dim">{stepNumber(index)}</span>
          <span style={{ flex: 1 }}>{labelOf(id)}</span>
          <button className="ghost" aria-label={`${labelOf(id)} 위로`} onClick={() => move(index, -1)}>
            ↑
          </button>
          <button className="ghost" aria-label={`${labelOf(id)} 아래로`} onClick={() => move(index, 1)}>
            ↓
          </button>
        </div>
      ))}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
        <button className="secondary" onClick={onCancel}>
          취소
        </button>
        <button disabled={busy} onClick={() => onApply(order)}>
          적용
        </button>
      </div>
    </div>
  );
}
