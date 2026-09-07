/**
 * 층② 국면 띠 (007 T019 · FR-218d·FR-219 · 74px).
 *
 * **`docs/design/Main.dc.html`·`RunResult.dc.html` 의 `flex: 0 0 74px` 블록 전사.**
 * 이 74px 는 확정 디자인 5종(`Main`·`RunnerPaused`·`Takeover`·`AiRecord`·`RunResult`)에
 * 모두 있다 — 007 이 새로 만드는 자리가 아니라 이미 공유되던 자리다 (research R1).
 *
 * 담는 것은 넷이고 **순서가 고정이다** — 국면 표시 → 테스트 이름 → 결말 요약 →
 * 그 국면의 주요 조작.
 *
 * **결말 요약은 이 띠에만 있다** (FR-218d · 005 FR-140). 이전에는 결과 화면과 세션 화면이
 * 같은 문장을 각자 만들어 나란히 그렸고, 사용자는 어느 것이 지금 실행인지 알 수 없었다
 * (U-19). `data-run-summary` 로 표시해 화면에 하나뿐임을 검사가 셀 수 있게 한다.
 */
import type { ReactNode } from "react";

import type { OutcomeTone } from "../../lib/wording";
import type { PhaseBar as PhaseBarModel } from "./model";

const INK = "#14130F";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";

/** 결말 색 역할 → 실제 색 (005 FR-141). **색은 보조이며 라벨이 항상 함께 있다.** */
const TONE_COLOR: Record<OutcomeTone, string> = {
  success: "#2E9455",
  danger: "#D9502F",
  neutral: "#6B675C",
  warn: "#B8860B",
  unknown: "#9A968A",
};

export interface PhaseBarProps {
  bar: PhaseBarModel;
  testName: string;
  /** 그 국면의 주요 조작. 오른쪽에 온다 */
  actions: ReactNode;
}

export function PhaseBar({ bar, testName, actions }: PhaseBarProps) {
  return (
    <div
      data-workbench-phase-bar
      style={{
        flex: "0 0 74px",
        borderBottom: `3px solid ${INK}`,
        background: "#EFEBE0",
        display: "flex",
        alignItems: "center",
        gap: "16px",
        padding: "0 24px",
      }}
    >
      {/*
        국면 표시. **화면에 하나뿐이다** (FR-219). 색만으로 국면을 알리지 않으므로
        라벨이 항상 텍스트로 있다 (ui-contract §7).
      */}
      <div
        data-phase-pill
        style={{
          display: "inline-flex",
          alignItems: "center",
          height: "30px",
          padding: "0 11px",
          background: TONE_COLOR[bar.phaseTone],
          color: "#FFFDF6",
          border: `3px solid ${INK}`,
          font: `700 13px/1 ${MONO}`,
          letterSpacing: "0.06em",
          flex: "0 0 auto",
        }}
      >
        {bar.phaseLabel}
      </div>

      <div
        style={{
          fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
          fontSize: "26px",
          lineHeight: "1",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          maxWidth: 300,
        }}
        title={testName}
      >
        {testName}
      </div>

      {bar.progressLabel !== null && (
        <div style={{ font: `400 14px/1 ${MONO}`, color: "#6B675C", flex: "0 0 auto" }}>
          {bar.progressLabel}
        </div>
      )}

      {/* 결말 요약 — **이 자리 하나뿐이다** (FR-218d · 005 FR-140 · U-19) */}
      {bar.runSummary !== null && (
        <div
          data-run-summary
          style={{
            font: `500 13px/1.4 'IBM Plex Sans KR', system-ui, sans-serif`,
            color: INK,
            flex: "1",
            minWidth: 0,
          }}
        >
          {bar.runSummary}
        </div>
      )}

      {bar.runSummary === null && <div style={{ flex: "1" }} />}

      <div style={{ display: "flex", alignItems: "center", gap: 10, flex: "0 0 auto" }}>
        {actions}
      </div>
    </div>
  );
}
