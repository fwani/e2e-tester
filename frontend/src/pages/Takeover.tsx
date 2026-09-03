/**
 * 사람 인수 화면 (T126). `Takeover.dc.html` 이식. FR-071·FR-075·FR-077.
 *
 * 표시해야 하는 것이 세 가지다.
 *
 * 1. `사람이 녹화 중` — 지금 조작이 기록되고 있다
 * 2. `세션 유지` — AI 가 남긴 화면이 그대로다. 처음부터 다시 하지 않는다
 * 3. **"이어서 진행하면 AI가 남은 지시를 다시 맡습니다"** (FR-077)
 *
 * 3번이 이 화면의 요점이다. 사용자가 "계속하기" 를 누르면 무엇이 일어나는지 모르면,
 * 인수를 끝낸 뒤 무엇을 해야 하는지 알 수 없다.
 *
 * **조작은 실제 브라우저 창에서 한다** (clarify 결정 3). 미러는 읽기 전용이므로 그 사실도
 * 함께 알린다 (FR-023b).
 */

export const RESUME_NOTICE = "이어서 진행하면 AI가 남은 지시를 다시 맡습니다.";

export interface TakeoverProps {
  /** AI 가 막힌 이유. 사용자가 무엇을 이어받는지 알아야 한다. */
  blockedReason?: string | null;
  /** 인수 중 기록된 Step 수. 0이면 아직 아무것도 하지 않은 것이다. */
  recordedCount: number;
  busy?: boolean;
  onResume: () => void;
  onStop: () => void;
  /** 실제 창을 다시 앞으로 가져온다 (spec 엣지 케이스 — 창을 잃어버린 경우). */
  onBringToFront?: () => void;
}

/** 상단 배너 — 사람이 녹화 중이며 세션이 유지되고 있음을 명시한다. */
export function TakeoverBanner() {
  return (
    <div
      role="status"
      className="row"
      style={{
        gap: 10,
        padding: "10px 14px",
        background: "var(--ink)",
        color: "var(--paper)",
        borderBottom: "3px solid var(--ink)",
        fontSize: 13,
        fontWeight: 700,
      }}
    >
      <span className="badge fail">REC</span>
      <span>사람이 녹화 중 — AI가 남긴 화면 상태를 그대로 이어받았습니다.</span>
      <span className="spacer" />
      <span className="badge warn">세션 유지</span>
    </div>
  );
}

export function Takeover({
  blockedReason = null,
  recordedCount,
  busy = false,
  onResume,
  onStop,
  onBringToFront,
}: TakeoverProps) {
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
      {blockedReason !== null && (
        <p className="muted" style={{ margin: 0, fontSize: 12.5 }}>
          AI 가 막힌 지점: {blockedReason}
        </p>
      )}

      <p style={{ margin: 0, fontSize: 13 }}>
        <strong>실제 브라우저 창에서 조작하세요.</strong> 왼쪽 미러는 읽기 전용이며,
        조작은 전달되지 않습니다. 지금 하는 동작은 <span className="badge">HUMAN</span>{" "}
        배지로 기록됩니다.
      </p>

      <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
        인수 중 기록된 Step: {recordedCount}개
      </p>

      <div className="row" style={{ gap: 8 }}>
        <button disabled={busy} onClick={onResume}>
          ▶ 계속하기
        </button>
        {onBringToFront && (
          <button className="secondary" disabled={busy} onClick={onBringToFront}>
            브라우저 창 앞으로
          </button>
        )}
        <span className="spacer" />
        <button className="danger" disabled={busy} onClick={onStop}>
          ■ 중지
        </button>
      </div>

      <p
        style={{
          margin: 0,
          padding: "8px 10px",
          background: "var(--ai-tint)",
          border: "2px solid var(--ai)",
          fontSize: 12,
        }}
      >
        {RESUME_NOTICE}
      </p>
    </div>
  );
}
