/**
 * **단일 Step 목록** (007 T021 · FR-221·FR-222·FR-223).
 *
 * 007 이 고치는 것의 핵심이다. 이 파일이 생기기 전 Step 목록을 그리는 구현이 **4벌**
 * 따로 있었다.
 *
 *   `components/design/DesignStepList.tsx` 의 `DesignStepRow`  ← 실행·일시정지·사람조작
 *   `pages/AiRecord.tsx:532` 의 `StepRow`                       ← AI 작성
 *   `pages/RunResult.tsx:718` 의 `StepRow`                      ← 결과보기
 *   `pages/TestDefinition.tsx:540` 의 인라인 렌더                ← 편집
 *
 * 그 결과 같은 정보가 국면에 따라 정반대 자리에 있었다 — 결말 표식이 세션 화면은 행의
 * **오른쪽 끝**, 결과 화면은 행의 **왼쪽 첫 칸**이었다 (S-02). AI 작성 화면에는 Step
 * 번호가 아예 없어서(S-08) 「Step 06 …」 안내와 대응되지 않았고, 결말 자리에는 **항상
 * 체크 표식**이 있어 통과처럼 보였다 (S-09).
 *
 * **칸의 자리는 국면과 무관하게 고정이다** (FR-222).
 *
 *   [번호 26px] [이름 + 동작 칩 + 탭 배지 + 대상 요약 + 값] [소요 시간] [결말 표식 24px]
 *
 * 그 국면에서 값이 없는 칸은 **비우되 다른 칸을 그 자리로 당기지 않는다** (FR-223).
 *
 * 인라인 style 값은 `docs/design/Main.dc.html`·`RunnerPaused.dc.html` 에서 그대로 옮겼다
 * (DC-001). `DesignStepList.tsx` 가 이미 그렇게 옮겨 둔 것을 흡수했다.
 */
import type { ReactNode } from "react";

import { displayOutcomeLabel, stepNumber } from "../../lib/wording";
import type { Step, TargetLocator } from "../../types/generated/step";
import type { StepOutcome, WorkbenchStep } from "./model";

const INK = "#14171C";

/**
 * 행 왼쪽 3px 결말 표식의 색 (008 「계기판」).
 *
 * **색만으로 구분하지 않는다.** 이 표식은 오른쪽 칸 4 의 형태 표식(체크·X·이중 화살표·
 * 점선 원)과 짝을 이루며, 접근 가능한 이름은 `displayOutcomeLabel` 이 준다
 * (005 FR-141·FR-151). 색을 못 보는 사람에게도 형태와 이름이 남는다.
 *
 * `Record<StepOutcome, …>` 로 두면 결말이 늘어날 때 컴파일러가 요구한다.
 */
const OUTCOME_MARK: Record<StepOutcome, string> = {
  pass: "#1A7F45",
  fail: "#C8371D",
  running: "#0B6BCB",
  pending: "transparent",
  skipped: "transparent",
  not_run: "transparent",
  recorded: "transparent",
};
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

/**
 * 확정 디자인의 헤더 바 (잉크 배경 + TEST STEPS + 작성 배지 + 개수).
 * `Main.dc.html` 의 `flex: 0 0 50px` 블록 전사.
 */
export function StepPanelHeader({
  authoring,
  count,
  children,
}: {
  authoring: "record" | "ai";
  count: number;
  children?: ReactNode;
}) {
  return (
    <div
      style={{
        flex: "0 0 50px",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "0 18px",
        background: INK,
        color: "#F2F4F7",
      }}
    >
      <div style={{ font: `600 12px/1 ${MONO}`, letterSpacing: "0.12em" }}>TEST STEPS</div>
      <div style={{ flex: "1" }} />
      {children}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "7px",
          padding: "5px 9px",
          border: "1px solid #4A515C",
          borderRadius: "3px",
          font: `600 11px/1 ${MONO}`,
          letterSpacing: "0.06em",
        }}
      >
        {authoring === "ai" ? (
          <svg width="10" height="10" viewBox="0 0 18 18" fill="none" stroke="#6B3FD4" strokeWidth="2.4">
            <path d="M9 1.5v4M9 12.5v4M1.5 9h4M12.5 9h4" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 12 12">
            <circle cx="6" cy="6" r="4" fill="#C8371D" />
          </svg>
        )}
        작성 {authoring === "ai" ? "AI" : "RECORD"}
      </div>
      <div style={{ font: `700 14px/1 ${MONO}` }}>{count}</div>
    </div>
  );
}

/**
 * 결말 표식. **일곱 값 전부 텍스트 라벨을 갖는다** (005 FR-141·FR-151).
 *
 * `recorded`(기록됨)가 007 이 더한 값이다. 통과 체크를 그리지 않는다 — 근거는
 * `design-conformance/undefined-states.md` 에 있다 (research R4).
 */
export function OutcomeMark({ outcome }: { outcome: StepOutcome }) {
  const label = displayOutcomeLabel(outcome);

  /*
    008「계기판」 — **형태로 말한다** (Language.dc.html §04).

    v1 은 24px 채운 상자 여섯 종이었다. 52px 행에서 그 상자는 너무 크고, 무엇보다
    `pending` 의 빈 사각형이 **체크박스로 읽혔다** — 편집 국면의 목록 오른쪽 끝에 빈
    네모가 13개 줄지어 있으면 고를 수 있는 것처럼 보인다.

    아이콘으로 바꾸되 **접근 가능한 이름은 그대로 둔다** — 색과 형태만으로 구분하지
    않는다는 규칙은 v1 과 같다 (005 FR-141·FR-151). 행 왼쪽 3px 표식(`OUTCOME_MARK`)이
    같은 결말을 색으로도 말하므로 둘이 짝을 이룬다.
  */
  const box = {
    width: "18px",
    height: "18px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  } as const;

  if (outcome === "pass") {
    return (
      <div aria-label={label} data-outcome="pass" style={box}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#1A7F45" strokeWidth="2.2">
          <path d="M3 8.4l3.2 3.2L13 4.8" />
        </svg>
      </div>
    );
  }

  if (outcome === "fail") {
    return (
      <div aria-label={label} data-outcome="fail" style={box}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#C8371D" strokeWidth="2.2">
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      </div>
    );
  }

  if (outcome === "running") {
    return (
      <div aria-label={label} data-outcome="running" style={box}>
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="4.5" fill="#0B6BCB" />
        </svg>
      </div>
    );
  }

  if (outcome === "skipped") {
    return (
      <div
        aria-label={label}
        title={`${label} — 이 실행에서 실행 대상이 아니었습니다`}
        data-outcome="skipped"
        style={box}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#6E757F" strokeWidth="2">
          <path d="M4 4l4 4-4 4M9 4l4 4-4 4" />
        </svg>
      </div>
    );
  }

  if (outcome === "not_run") {
    return (
      <div
        aria-label={label}
        title={`${label} — 앞선 Step 이 실패해 도달하지 못했습니다`}
        data-outcome="not_run"
        style={box}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#CBD0D8" strokeWidth="2" strokeDasharray="2.6 2.4">
          <circle cx="8" cy="8" r="5" />
        </svg>
      </div>
    );
  }

  if (outcome === "recorded") {
    return (
      <div
        aria-label={label}
        title={`${label} — 작성 중이라 재생 결말이 아직 없습니다`}
        data-outcome="recorded"
        style={box}
      >
        <svg width="16" height="16" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="3.4" fill="#C8371D" />
        </svg>
      </div>
    );
  }

  /*
    `pending` — 아직 돌리지 않았다. **아무것도 그리지 않는다.** 칸은 남긴다
    (FR-223 — 다른 칸을 그 자리로 당기지 않는다). 편집 국면의 목록 전체가 이 상태이고,
    거기에 표식을 그리면 없는 결말을 있다고 말하는 것이 된다.
  */
  return <div aria-label={label} data-outcome={outcome} style={box} />;
}


/**
 * 요소를 어떻게 찾는지 한 줄로. 확정 디자인의 `role=menuitem`·`testId=…` 형태.
 *
 * **`verified` 후보만 쓴다** (원칙 IV). 모호하거나 검증에 실패한 후보를 요약에 넣으면
 * 실제로 쓰이지 않을 후보를 "이걸로 찾습니다" 라고 보여 주는 셈이 된다.
 */
export function locatorSummary(step: Step): string {
  if (step.type === "navigate") return step.url;
  if (step.type === "close_tab") return `탭 ${step.tab}`;
  if (step.type === "assertion") {
    const a = step.assertion;
    return a.value ? `${a.kind} ${a.value}` : a.kind;
  }
  if (step.type === "drag") {
    // 끄는 대상만 보여주면 어디로 놓는지 알 수 없다 — 두 요소를 함께 요약한다.
    return `${describeTarget(step.target)} → ${describeTarget(step.drop_target)}`;
  }
  return describeTarget(step.target);
}

function describeTarget(t: TargetLocator): string {
  if (t.test_id?.status === "verified") return `testId=${t.test_id.value}`;
  if (t.role && t.accessible_name && t.role_status === "verified")
    return `role=${t.role} "${t.accessible_name}"`;
  if (t.label?.status === "verified") return `label=${t.label.value}`;
  if (t.text?.status === "verified") return `text="${t.text.value}"`;
  if (t.css?.status === "verified") return `css=${t.css.value}`;
  return "식별 후보 없음";
}

/** 입력값. 민감 값은 `{{변수명}}` 참조로만 저장되므로 그대로 보여도 안전하다 (FR-083). */
function stepValue(step: Step): string | null {
  if (step.type === "fill" || step.type === "select") return step.value;
  return null;
}

export interface StepListProps {
  steps: WorkbenchStep[];
  authoring: "record" | "ai";
  focusedStepId: string | null;
  /** Step 지목. 일곱 국면 전부에서 같은 방식이다 (FR-227) */
  onSelect: (stepId: string) => void;
  /** 행 안의 편집 조작. 권한이 허락하는 국면에서만 어댑터가 준다 */
  rowActions?: (step: WorkbenchStep) => ReactNode;
  /** 헤더 오른쪽에 얹는 것 (순서 변경 토글 등) */
  headerExtra?: ReactNode;
  /** Step 이 0개일 때의 안내. 국면마다 다르다 */
  emptyNotice?: ReactNode;
  /**
   * 패널 바닥 — Step 을 대상으로 하는 조작의 **유일한 자리** (FR-235).
   *
   * 확정 디자인 3종(`Main`·`RunnerPaused`·`Takeover`)이 모두 460px 패널 아래에 잉크
   * 테두리로 구분된 조작 블록을 갖는다. 007 이 새로 만드는 자리가 아니라 이미 공유되던
   * 자리이며, 조작이 국면마다 다른 곳에 있던 것을 여기 하나로 모은다.
   */
  footer?: ReactNode;
}

/**
 * 우측 460px 패널. `Main.dc.html`·`RunnerPaused.dc.html`·`Takeover.dc.html` 공통.
 */
export function StepList({
  steps,
  authoring,
  focusedStepId,
  onSelect,
  rowActions,
  headerExtra,
  emptyNotice,
  footer,
}: StepListProps) {
  return (
    <div
      data-workbench-step-panel
      /*
        Step 지목(`step.select`)의 **자리**는 이 패널이다 (ui-contract §4-1). 행마다
        표시하면 자리가 200개가 되고, "한 조작에 한 자리" 를 셀 수 없다 (FR-235).
      */
      data-action="step.select"
      style={{
        flex: "0 0 460px",
        borderLeft: `1px solid ${INK}`,
        background: "#FFFFFF",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <StepPanelHeader authoring={authoring} count={steps.length}>
        {headerExtra}
      </StepPanelHeader>

      <div style={{ flex: "1", minHeight: "0", overflowY: "auto" }}>
        {/*
          007 T071 (FR-243) — **지목한 Step 이 더 이상 없다.**

          결과 국면에서 편집으로 갔다가 그 Step 을 지우고 돌아오는 길에 생긴다. 사실을
          밝히고 목록은 **정상으로** 보여 준다 — 조용히 첫 Step 을 고르면 사용자는
          자기가 보던 것이 그것이라고 믿고, 빈 화면을 주면 목록을 잃는다.
        */}
        {focusedStepId !== null && !steps.some((s) => s.id === focusedStepId) && (
          <div
            role="status"
            data-focus-missing
            style={{
              padding: "12px 18px",
              borderBottom: "1px solid #E3E6EB",
              background: "#FBF3E2",
              font: `400 12.5px/1.6 ${SANS}`,
            }}
          >
            보고 있던 Step 이 이 목록에 없습니다. 그 사이에 지워졌거나 순서가 바뀌었을 수
            있습니다.
          </div>
        )}
        {steps.length === 0 && (
          <div style={{ padding: "18px", color: "#6E757F", font: `400 13px/1.5 ${SANS}` }}>
            {emptyNotice ?? "아직 Step 이 없습니다."}
          </div>
        )}
        {steps.map((s) => (
          <StepRow
            key={s.id}
            step={s}
            selected={s.id === focusedStepId}
            onSelect={() => onSelect(s.id)}
            actions={rowActions?.(s)}
          />
        ))}
      </div>

      {footer !== undefined && footer !== null && (
        <div
          data-workbench-step-footer
          style={{
            borderTop: `1px solid ${INK}`,
            background: "#F2F4F7",
            padding: "14px 18px 16px",
            maxHeight: "52%",
            overflowY: "auto",
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
}

/**
 * Step 행 하나 — **유일한 구현**.
 *
 * 행 전체가 누를 수 있는 요소다. `button` 역할을 갖는 이유는 접근성이자 기존 테스트의
 * `getByRole` 이 그것에 의존하기 때문이다 (002 §2 의 4번 예외).
 */
function StepRow({
  step,
  selected,
  onSelect,
  actions,
}: {
  step: WorkbenchStep;
  selected: boolean;
  onSelect: () => void;
  actions?: ReactNode;
}) {
  const dsl = step.step;
  const value = dsl ? stepValue(dsl) : null;

  return (
    <div
      data-step-row={step.id}
      /* 일시정지 위치는 **속성으로** 말한다. 008 에서 모든 행이 결말 표식으로
         왼쪽 테두리를 갖게 됐으므로, 인라인 스타일을 훑어서는 구분할 수 없다. */
      data-paused-here={step.isPausedHere ? "" : undefined}
      style={{
        display: "flex",
        gap: "10px",
        // v1 은 `15px 18px` + 15px 이름 + 6px 간격이라 행이 125px 였고, 900px 창에서
        // 5행밖에 보이지 않았다. 실무 테스트는 20~50 Step 이다. 칸은 그대로 넷이고
        // 정보도 그대로다 — 여백과 글자 크기만 내렸다 (5행 → 13행).
        minHeight: "52px",
        padding: "6px 12px 6px 9px",
        borderBottom: "1px solid #E3E6EB",
        // 결말을 왼쪽 3px 표식으로도 말한다. 색만으로 구분하지 않기 위해서다 —
        // 오른쪽 칸 4 의 형태 표식과 짝을 이룬다 (005 FR-141·FR-151).
        borderLeft: `3px solid ${OUTCOME_MARK[step.outcome] ?? "transparent"}`,
        alignItems: "center",
        ...(step.outcome === "fail" ? { background: "#FCEDE9" } : {}),
        ...(step.isPausedHere ? { borderLeftColor: "#8F5A00", background: "#FBF3E2" } : {}),
        ...(selected && !step.isPausedHere ? { background: "#F7F8FA" } : {}),
      }}
    >
      {/* 칸 1 — 번호 26px. **모든 국면에서 보인다** (FR-224 · S-08) */}
      <div
        data-cell="number"
        style={{ flex: "0 0 26px", textAlign: "right", font: `500 12px/1 ${MONO}`, color: "#6E757F" }}
      >
        {stepNumber(step.index)}
      </div>

      {/* 칸 2 — 이름과 부속 정보 */}
      <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "6px" }}>
        <button
          type="button"
          onClick={onSelect}
          aria-pressed={selected}
          style={{
            border: "none",
            borderRadius: "3px",
            background: "transparent",
            boxShadow: "none",
            padding: 0,
            textAlign: "left",
            font: `600 13px/1.25 ${SANS}`,
            color: INK,
            cursor: "pointer",
            // 한 줄로 자른다. 감싸면 행 높이가 흔들려 52px 가 성립하지 않는다.
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            height: "18px",
          }}
        >
          {step.label}
        </button>

        <div
          data-cell="detail"
          style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "nowrap", minWidth: 0, overflow: "hidden", height: 17 }}
        >
          {/*
            결과 국면에서 정의와 매칭되지 않은 행은 이 칸들이 **빈다.** 다른 칸을 그
            자리로 당기지 않는다 (FR-223 · research R3).
          */}
          {dsl !== null && (
            <>
              <div
                data-cell="type"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  flex: "0 0 auto",
                  height: "19px",
                  padding: "0 6px",
                  border: `1px solid ${dsl.author === "ai" ? "#6B3FD4" : "#CBD0D8"}`,
                  borderRadius: "2px",
                  background: dsl.author === "ai" ? "#F0EBFB" : "#F7F8FA",
                  color: dsl.author === "ai" ? "#6B3FD4" : "#4A515C",
                  font: `600 10px/1 ${MONO}`,
                  letterSpacing: "0.06em",
                }}
              >
                {dsl.type.toUpperCase()}
              </div>

              {/* FR-030a — 최초 탭이 아닌 Step 은 어느 탭에서 일어나는지 보여야 한다 */}
              {dsl.tab > 0 && (
                <div
                  data-cell="tab"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    flex: "0 0 auto",
                    height: "19px",
                    padding: "0 6px",
                    border: "1px solid #CBD0D8",
                    borderRadius: "2px",
                    background: "#FFFFFF",
                    color: "#4A515C",
                    font: `600 10px/1 ${MONO}`,
                    letterSpacing: "0.06em",
                  }}
                >
                  탭 {dsl.tab}
                </div>
              )}

              <div data-cell="locator" style={{ minWidth: 0, font: `400 11px/1 ${MONO}`, color: "#6E757F", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {locatorSummary(dsl)}
              </div>

              {/* FR-083 — 민감 값은 참조로만 저장되므로 표시해도 평문이 새지 않는다 */}
              {value !== null && (
                <div data-cell="value" style={{ flex: "0 0 auto", font: `400 11px/1 ${MONO}`, color: "#5732B0", whiteSpace: "nowrap" }}>
                  {value}
                </div>
              )}
            </>
          )}
        </div>
        {actions}
      </div>

      {/* 칸 3 — 소요 시간. 없으면 자리를 비운다 (FR-223) */}
      <div
        data-cell="duration"
        style={{
          flex: "0 0 58px",
          textAlign: "right",
          font: `400 11px/1 ${MONO}`,
          color: "#6E757F",
        }}
      >
        {step.durationMs !== null ? `${step.durationMs} ms` : ""}
      </div>

      {/* 칸 4 — 결말 표식 24px. **오른쪽 끝이다** (S-02 해소) */}
      <div data-cell="outcome" style={{ flex: "0 0 20px" }}>
        <OutcomeMark outcome={step.outcome} />
      </div>
    </div>
  );
}
