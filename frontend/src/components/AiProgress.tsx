/**
 * AI 진행 표시 (T117). FR-060.
 *
 * `ai_progress` 이벤트를 시간 순으로 보여 준다. **최신이 위로 오지 않는다** — AI 가 무엇을
 * 어떤 순서로 했는지가 그대로 Step 목록의 순서이므로, 두 목록이 같은 방향으로 읽혀야
 * 사용자가 대응시킬 수 있다.
 *
 * 진행 목록은 **기록이 아니다.** 저장되지 않고 세션이 끝나면 사라진다 — 저장되는 것은
 * Step 뿐이다 (FR-063).
 */

export interface AiProgressProps {
  messages: string[];
  /** AI 가 지금 수행 중인가. 끝난 뒤에는 표시를 바꾼다. */
  running?: boolean;
  /** 언어모델 실패 사유 (`ai_error`). 있으면 그것을 먼저 보여 준다 (FR-067). */
  error?: string | null;
  limit?: number;
}

export function AiProgress({
  messages,
  running = false,
  error = null,
  limit = 30,
}: AiProgressProps) {
  const shown = messages.slice(-limit);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="row" style={{ gap: 8 }}>
        <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
          AI 진행
        </strong>
        {running && <span className="badge ai">AI 수행 중</span>}
        {!running && messages.length > 0 && error === null && (
          <span className="badge pass">수행 완료</span>
        )}
      </div>

      {error !== null && (
        <p
          role="status"
          style={{
            margin: 0,
            padding: "8px 10px",
            background: "var(--fail-tint)",
            border: "2px solid var(--fail)",
            color: "var(--fail-dark)",
            fontSize: 12.5,
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
        </p>
      )}

      {shown.length === 0 ? (
        <p className="dim" style={{ margin: 0, fontSize: 12 }}>
          {running
            ? "화면을 살펴보는 중입니다…"
            : "아직 진행 내용이 없습니다."}
        </p>
      ) : (
        <ol
          style={{
            margin: 0,
            paddingLeft: 18,
            fontSize: 12.5,
            lineHeight: 1.7,
            maxHeight: 220,
            overflowY: "auto",
          }}
        >
          {shown.map((message, index) => (
            // 같은 문장이 반복될 수 있으므로 인덱스를 키에 넣는다.
            <li key={`${index}-${message}`} className="muted">
              {message}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
