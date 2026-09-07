/**
 * AI 지시문 작성. `docs/design/AiRecord.dc.html` 의 **작성 전 상태**다.
 *
 * **이 화면은 007 의 일곱 국면에 속하지 않는다.** 세션이 아직 없고 Step 도 없다 —
 * 통합 작업 화면(`Workbench`)이 다루는 것은 "한 테스트를 놓고 사용자가 지금 있는 위치"
 * 이고, 여기는 그 위치에 들어가기 **전**이다. 그래서 껍데기만 공유하고 3층 구조를
 * 쓰지 않는다.
 *
 * 007 이전에는 `AiRecord` 를 `composing` 으로 그렸다. 그 화면이 통합으로 사라지면서
 * 여기 남은 작성 전 상태를 **자기 자리에** 옮겨 놓는다 — 통합 화면에 "Step 이 없는
 * 국면" 을 하나 더 만드는 것보다 이쪽이 정직하다. 확정 디자인에 대응이 없는 상태이므로
 * `design-conformance/undefined-states.md` 에 기록한다 (DC-009).
 *
 * DR-016 — 실행하면 화면이 **즉시** 바뀐다. 아무 변화 없이 끝나지 않는다.
 */
import { useState } from "react";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { sessions, type SessionView } from "../api/client";
import {
  Artboard,
  BrandMark,
  HeaderBar,
  HeaderDivider,
  StatusPill,
} from "../components/design/Chrome";

const INK = "#14130F";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

export function AiCompose({
  startUrl,
  onCancel,
  onStarted,
}: {
  startUrl: string;
  onCancel: () => void;
  onStarted: (session: SessionView, instruction: string) => void;
}) {
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const start = () => {
    setBusy(true);
    setError(null);
    void sessions
      .create({ mode: "ai", start_url: startUrl, ai_instruction: instruction.trim() })
      .then((session) => onStarted(session, instruction.trim()))
      .catch((exc: unknown) => {
        // DR-016·DR-022 — 조용히 끝나지 않는다. 사유를 화면에 남긴다.
        setError(describeError(exc));
      })
      .finally(() => setBusy(false));
  };

  return (
    <Artboard width={1440} minHeight={900} grow>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <div style={{ font: `500 14px/1 ${SANS}`, color: "#6B675C" }}>
          테스트 <span style={{ color: INK }}>/</span>{" "}
          <span style={{ color: INK, fontWeight: 600 }}>새 테스트</span>
        </div>
        <div style={{ flex: "1" }} />
        <StatusPill background="#F0EBFC" color={INK}>
          지시문 작성
        </StatusPill>
      </HeaderBar>

      <div
        style={{
          flex: "0 0 74px",
          borderBottom: `3px solid ${INK}`,
          background: "#EFEBE0",
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "0 24px",
        }}
      >
        <div
          style={{
            fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
            fontSize: 26,
            lineHeight: 1,
          }}
        >
          AI로 테스트 만들기
        </div>
        <div style={{ font: `400 13px/1 ${MONO}`, color: "#6B675C" }}>{startUrl}</div>
        <div style={{ flex: "1" }} />
        <button className="secondary" disabled={busy} onClick={onCancel}>
          돌아가기
        </button>
      </div>

      {error !== null && (
        <div style={{ borderBottom: `3px solid ${INK}`, padding: "12px 24px", background: "#FBEEEA" }}>
          <ErrorNotice error={error} />
        </div>
      )}

      <div
        style={{
          flex: "1",
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          padding: "24px",
          maxWidth: 900,
        }}
      >
        <label htmlFor="ai-instruction" style={{ font: `600 12px/1 ${MONO}`, letterSpacing: "0.12em", color: "#6B675C" }}>
          자연어 지시
        </label>
        <textarea
          id="ai-instruction"
          aria-label="자연어 지시"
          rows={8}
          value={instruction}
          autoFocus
          onChange={(e) => setInstruction(e.target.value)}
          placeholder={
            "로그인한 다음 프로젝트 메뉴로 이동해서\nTEST라는 프로젝트를 생성하고\n프로젝트 목록에 TEST가 있는지 확인해."
          }
          style={{
            border: `3px solid ${INK}`,
            background: "#F0EBFC",
            padding: 12,
            font: `500 15px/1.5 ${SANS}`,
            minHeight: "auto",
          }}
        />
        {/* 001 FR-064 — 지시문은 기록이며 저장 대상이 아니다. 그 사실을 미리 말한다. */}
        <p className="dim" style={{ margin: 0, font: `400 12.5px/1.6 ${SANS}` }}>
          지시문은 테스트로 저장되지 않습니다. 만들어진 Step 만 저장됩니다.
        </p>
        <div>
          <button disabled={busy || instruction.trim() === ""} onClick={start}>
            AI 실행 →
          </button>
        </div>
      </div>
    </Artboard>
  );
}
