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
  /**
   * 마지막 저장 시각 (005 FR-155·FR-134). `null` 이면 아직 저장하지 않았다.
   *
   * 이 값이 있으면 제목에 「초안」을 쓰지 않는다. 저장된 테스트를 재실행하다 중지한
   * 세션까지 「초안」으로 보여 사용자는 작성 중인 것으로 오해했다 (U-03).
   */
  savedAt?: string | null;
  /**
   * 저장할 변경이 남아 있는가 (005 FR-156).
   *
   * 저장 직후에는 거짓이다 — 같은 내용을 다시 저장하도록 유도하지 않는다.
   */
  hasChangesToSave?: boolean;
  /** 목록으로 이동 (005 FR-154 의 「목록에서 보기」). */
  onShowList?: () => void;
  /**
   * 중지로 끝난 실행의 결말과 다음 행동 (005 FR-133 · U-03).
   *
   * 중지는 화면을 떠나지 않는다(DR-010). 다만 그 화면이 **저장 프롬프트**여서는 안
   * 된다 — 리포트는 중지 직후 화면이 「TC-002 초안」 저장 화면이 되고, 배너가 권하는
   * "저장하거나 처음부터 다시 실행할 수 있습니다" 를 **그 화면에서는 할 수 없는** 것을
   * 봤다. 저장은 비활성이고 실행 버튼은 없었다.
   */
  /**
   * 일시정지 전이 중인가 (005 FR-142~FR-145 · U-04).
   *
   * 일시정지는 Step 경계에서만 걸린다. 요청과 성립 사이에 최대 10초가 있고, 리포트는
   * 그 구간에 화면이 이미 `PAUSED` 라고 말하면서 **모든 버튼을 비활성으로 두고 아무
   * 설명도 하지 않는** 것을 봤다. 실측 19초 뒤 실행이 끝났다.
   */
  pausing?: boolean;
  /** 대기 중인 Step 의 대기 예산(ms). 남은 시간을 보여 주는 근거다 (FR-145). */
  pausingBudgetMs?: number | null;
  /**
   * 멈추기 전에 실행이 끝난 경우의 결말 (005 FR-146).
   *
   * 실행 결말과 세션 상태는 다른 축이다 — 둘 다 참이므로 관계를 설명해야 한다.
   */
  finishedWhilePausing?: { summary: string; failureReason: string | null; onShowResult?: () => void } | null;
  stopResult?: {
    summary: string;
    stoppedStepIndex: number | null;
    onRerunAll?: () => void;
    onRerunFromStop?: () => void;
    onBack?: () => void;
  } | null;
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
    savedAt = null,
    hasChangesToSave = true,
    onShowList,
    pausing = false,
    pausingBudgetMs = null,
    finishedWhilePausing = null,
    stopResult = null,
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
  /**
   * 실패한 Step 의 인덱스 (005 FR-136). 없으면 `null`.
   *
   * 표시 상태에서 읽는다 — 세션 뷰의 `step_results` 로 복원된 값도 여기 반영된다
   * (FR-171). 이벤트를 놓친 화면이 실패를 없었던 것처럼 보이면 차단도 풀린다.
   */
  const failedStepIndex = (() => {
    const at = steps.findIndex((step, index) => outcomeOf(step, index) === "fail");
    return at < 0 ? null : at;
  })();

  return (
    <Artboard width={1440} height={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <Breadcrumb testId={testId} />
        <div style={{ flex: "1" }} />
        {/*
          005 FR-142·FR-146 — 헤더 배지도 전이와 종료를 반영한다.

          미러 위 배지만 고치고 이것을 남겨 두면 한 화면에서 두 배지가 다른 말을 한다 —
          U-20 이 지적한 "같은 결말을 화면마다 다른 말로 부른다" 를 그대로 재생산한다.
        */}
        <StatusPill
          background={
            finishedWhilePausing !== null ? "#EDEAE0" : review ? "#FFFDF6" : pausing ? "#EDEAE0" : "#F5D000"
          }
          color="#14130F"
        >
          {finishedWhilePausing === null && (
            <svg width="13" height="13" viewBox="0 0 16 16">
              <rect x="3" y="2" width="3.5" height="12" fill="currentColor" />
              <rect x="9.5" y="2" width="3.5" height="12" fill="currentColor" />
            </svg>
          )}
          {finishedWhilePausing !== null
            ? "실행 종료"
            : pausing
              ? "일시정지 중…"
              : review
                ? "REVIEW"
                : stepByStep
                  ? "STEP"
                  : "PAUSED"}
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
          {/*
            005 FR-134·FR-155 — 저장된 것은 「초안」이 아니다.

            저장된 테스트를 재실행하다 중지했을 뿐인데 제목이 「TC-002 초안」이 되고
            하단에 이름 입력칸과 「저장」이 떴다 — 사용자는 작성 중인 초안으로 읽었다
            (U-03). 저장 성공 뒤에도 「초안」이 남아 저장 여부를 알 수 없었다 (U-09).
          */}
          {savedAt !== null ? `${title} · 저장됨` : `${title} 초안`}
        </div>
        <div style={{ font: "400 14px/1 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
          {finishedWhilePausing !== null
            ? finishedWhilePausing.summary
            : pausing
              ? // 005 FR-142·FR-145 — 기다리는 이유와 남은 예산을 **즉시** 말한다.
                // 이전에는 10초가 지나서야 노란 배너로 알렸다.
                `현재 Step 이 끝나면 멈춥니다 · ${stepLabel(currentStepIndex)} 대기 중` +
                (pausingBudgetMs ? ` (최대 ${Math.round(pausingBudgetMs / 1000)}s)` : "")
              : review
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

        {/*
          005 FR-136 (U-05) — 실패한 Step 이 있으면 「계속하기」를 잠그고 이유를 준다.

          이전에는 「계속하기」가 실패한 Step 을 조용히 지나가고 배지를 「완료」로 바꿨다.
          저장된 결과는 실패인데 화면은 완료라고 말했다 — 사용자는 실패를 못 본 채
          통과했다고 믿고 넘어갈 수 있었다.

          005 FR-144 — 전이 중에도 「계속하기」는 잠근다(아직 멈추지 않았다). 대신
          「중지」는 살린다 — 기다리다 포기하는 것이 가장 자연스러운 다음 행동이다.
        */}
        {!review && failedStepIndex !== null && (
          <span
            className="muted"
            style={{ maxWidth: 320, font: "400 12px/1.45 'IBM Plex Sans KR', system-ui, sans-serif" }}
          >
            {`${stepLabel(failedStepIndex)} 이 실패해 이어서 갈 수 없습니다. ` +
              `「${stepLabel(failedStepIndex)} 고치기」 또는 「${stepLabel(failedStepIndex)}부터 실행」을 쓰세요.`}
          </span>
        )}
        {!review && (
          <button
            disabled={busy || pausing || failedStepIndex !== null}
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
          /*
            005 FR-144 — 전이 중에도 누를 수 있다. `busy` 는 pause 요청이 진행 중이라는
            뜻인데, 그 10초 동안 중지까지 잠그면 사용자는 기다리는 것 말고 할 일이
            없다 — 리포트가 본 "10초간 모든 버튼 비활성, 아무 설명 없음" 이 그것이다.
          */
          disabled={busy && !pausing}
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
          {/*
            005 FR-133 (U-03) — 중지 결과 화면.

            "중지했습니다" 와 결말 요약, 그리고 **그 자리에서 할 수 있는 다음 행동**을
            둔다. 이전에는 화면이 세션 유실 오류와 저장 프롬프트로 바뀌고, 배너가 권하는
            행동을 그 화면에서 할 수 없었다.
          */}
          {stopResult !== null && (
            <div
              style={{
                border: "3px solid #14130F",
                background: "#FFFDF6",
                padding: "14px 18px",
                marginBottom: 12,
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 240 }}>
                <strong style={{ font: "600 15px/1.2 'IBM Plex Sans KR', system-ui, sans-serif" }}>
                  실행을 중지했습니다.
                </strong>
                <span
                  className="mono"
                  style={{ font: "400 13px/1.3 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}
                >
                  {stopResult.summary}
                </span>
              </div>
              {onShowResult && (
                <button className="secondary" onClick={onShowResult} disabled={busy}>
                  결과 자세히 보기
                </button>
              )}
              {stopResult.onRerunAll && (
                <button className="secondary" onClick={stopResult.onRerunAll} disabled={busy}>
                  처음부터 실행
                </button>
              )}
              {stopResult.onRerunFromStop && stopResult.stoppedStepIndex !== null && (
                <button className="secondary" onClick={stopResult.onRerunFromStop} disabled={busy}>
                  {`${stepLabel(stopResult.stoppedStepIndex)}부터 실행`}
                </button>
              )}
              {stopResult.onBack && (
                <button className="ghost" onClick={stopResult.onBack} disabled={busy}>
                  목록으로
                </button>
              )}
            </div>
          )}

          <BrowserFrame
            url={currentUrl}
            badge={
              finishedWhilePausing !== null
                ? // 005 FR-146 — 멈추기 전에 끝났으면 일시정지가 아니라 결말을 말한다.
                  { label: "실행 종료", background: "#6B675C", color: "#FFFDF6" }
                : pausing
                  ? // 005 FR-142 — 아직 정지가 아니다. 그 사실을 배지가 말한다.
                    { label: "일시정지 중…", background: "#EDEAE0", color: "#14130F" }
                  : review
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

            {/*
              005 FR-143 (U-04) — 전이 중에는 편집 팔레트를 **열지 않는다.**

              리포트는 요청 0.12초 뒤에 편집 팔레트가 전부 노출되는 것을 봤다. 그 상태에서
              Step 을 고치면 무엇에 적용되는지 알 수 없다 — 실행은 아직 돌고 있었다.
              여기서 "정지되면 편집할 수 있습니다" 를 대신 보여 준다.
            */}
            {pausing && finishedWhilePausing === null ? (
              <div
                style={{
                  border: "3px dashed #9A968A",
                  background: "#F5F2E9",
                  padding: "16px 18px",
                  color: "#6B675C",
                  font: "400 14px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
                }}
              >
                정지되면 편집할 수 있습니다. 현재 Step 이 끝나기를 기다리고 있습니다.
              </div>
            ) : (
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
            )}

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
              {/*
                005 FR-156 (U-09) — 저장 후에는 「변경 저장」이고, 바뀐 것이 없으면
                비활성이다.

                이전에는 저장 성공 뒤에도 「저장」이 그대로 활성이었다. 성공 표시가
                없으니 사용자는 저장됐는지 알 수 없었고, 버튼이 눌리므로 계속 다시
                눌렀다. 중복 저장은 in-flight 가드가 막았지만, **연타할 이유가 계속
                생기는 것** 자체가 결함이었다.
              */}
              <button
                disabled={busy || steps.length === 0 || saveName.trim() === "" || !hasChangesToSave}
                onClick={onSave}
              >
                {savedAt !== null ? "변경 저장" : "저장"}
              </button>
            </div>

            {/*
              005 FR-154·FR-158 (U-09) — **저장 성공을 화면을 옮기지 않고 알 수 있다.**

              리포트가 본 것은 이랬다 — `POST …/save` 는 30 ms 에 200 으로 성공하는데
              화면의 유일한 변화는 빵부스러기가 "새 테스트" → "TC-001" 로 바뀐 것
              하나였다. 토스트도, 이동도, 체크 표시도 없었다. 저장 여부를 확인하려면
              목록으로 나가야 했다.

              토스트로 끝내지 않는 이유는 사라지면 근거가 남지 않기 때문이다.
            */}
            {savedAt !== null && (
              <div
                role="status"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  border: "3px solid #2E9455",
                  background: "#F0F7F2",
                  padding: "10px 14px",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#2E9455" strokeWidth="2.8">
                  <path d="M3 8.5l3.5 3.5L13 4.5" />
                </svg>
                <span style={{ font: "600 14px/1.3 'IBM Plex Sans KR', system-ui, sans-serif" }}>
                  {`저장했습니다 · ${title}`}
                </span>
                <div style={{ flex: 1 }} />
                {onShowList && (
                  <button className="ghost" onClick={onShowList} disabled={busy}>
                    목록에서 보기
                  </button>
                )}
              </div>
            )}

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
