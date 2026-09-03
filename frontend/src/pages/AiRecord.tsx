/**
 * AI 작성 화면 (T116). `AiRecord.dc.html` 이식.
 *
 * `RunnerPaused` 와 같은 구성 방식을 쓴다 — 별도 화면으로 복제하지 않고 `Runner` 가 AI
 * 세션에서 끼워 넣는 패널이다. 좌측 미러·우측 Step 목록은 실행 중과 동일하고, 달라지는
 * 것은 진행 표시와 안내 문구뿐이다.
 *
 * **FR-064 의 문구가 이 화면의 핵심이다.** "지시문은 테스트로 저장되지 않으며, 다시 돌릴
 * 때는 AI를 쓰지 않는다" 를 작성 시점에 명시해야, 사용자가 저장된 것이 무엇인지 오해하지
 * 않는다. 원칙 II 를 사용자가 읽을 수 있게 만드는 지점이다.
 */
import type { AiChoice } from "../api/client";
import { AiBlockedCard } from "../components/AiBlockedCard";
import { AiProgress } from "../components/AiProgress";

export const INSTRUCTION_NOTICE =
  "지시문은 테스트로 저장되지 않습니다. AI가 실제로 성공한 동작만 Step으로 저장되고, " +
  "다시 돌릴 때는 AI를 쓰지 않습니다.";

export interface AiBlockedState {
  attempted: string | null;
  reason: string;
  choices: AiChoice[];
}

export interface AiRecordProps {
  /** 사용자가 준 지시문 원문. 작성 의도의 기록으로만 남는다 (FR-063). */
  instruction: string | null;
  messages: string[];
  running: boolean;
  error?: string | null;
  blocked?: AiBlockedState | null;
  stepCount: number;
  busy?: boolean;
  onChoose: (choice: AiChoice) => void;
}

/** AI 작성 세션의 우측 패널 — 지시문·진행·안내. */
export function AiRecord({
  instruction,
  messages,
  running,
  error = null,
  blocked = null,
  stepCount,
  busy = false,
  onChoose,
}: AiRecordProps) {
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
      {instruction !== null && instruction !== "" && (
        <div>
          <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
            지시문
          </strong>
          <p
            style={{
              margin: "4px 0 0",
              padding: "8px 10px",
              background: "var(--paper)",
              border: "2px solid var(--border)",
              fontSize: 13,
              whiteSpace: "pre-wrap",
            }}
          >
            {instruction}
          </p>
        </div>
      )}

      {blocked !== null ? (
        <AiBlockedCard
          attempted={blocked.attempted}
          reason={blocked.reason}
          choices={blocked.choices}
          busy={busy}
          onChoose={onChoose}
        />
      ) : (
        <AiProgress messages={messages} running={running} error={error} />
      )}

      <p
        className="muted"
        style={{
          margin: 0,
          padding: "8px 10px",
          background: "var(--ai-tint)",
          border: `2px solid var(--ai)`,
          fontSize: 12,
          lineHeight: 1.6,
        }}
      >
        {INSTRUCTION_NOTICE}
      </p>

      {!running && blocked === null && stepCount > 0 && (
        <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
          Step {stepCount}개가 기록됐습니다. 아래에서 이름을 붙여 저장하세요. 저장 전에
          검증 Step 을 더하거나 자연어로 Step 을 추가할 수 있습니다.
        </p>
      )}
    </div>
  );
}
