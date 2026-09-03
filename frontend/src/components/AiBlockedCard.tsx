/**
 * AI 실패 카드 (T127). FR-069·FR-070.
 *
 * 실패한 동작 + 이유 + 4선택지. **세션이 유지되고 있음을 함께 표시한다** — 실패 화면이
 * "끝났다" 로 읽히면 사용자는 이어받을 수 있다는 사실을 모른다.
 *
 * 선택지 순서는 디자인을 따른다: 직접 수행 → AI에게 다시 → 건너뛰기 → 종료.
 * 되돌릴 수 없는 것(종료)을 마지막에 두고 색으로도 구분한다.
 */
import type { AiChoice } from "../api/client";

export interface AiBlockedCardProps {
  /** 시도하던 동작. 서버가 아는 만큼만 온다 (없을 수 있다). */
  attempted?: string | null;
  reason: string;
  choices?: AiChoice[];
  busy?: boolean;
  onChoose: (choice: AiChoice) => void;
}

const LABELS: Record<AiChoice, { label: string; hint: string; tone?: string }> = {
  takeover: {
    label: "직접 수행",
    hint: "AI 가 남긴 화면 그대로 이어받아 조작합니다. 브라우저는 닫히지 않습니다.",
  },
  retry: {
    label: "AI에게 다시",
    hint: "지금 화면 상태에서 다시 시도합니다. 되돌리지 않습니다.",
  },
  skip: {
    label: "건너뛰기",
    hint: "이 동작은 Step 으로 남기지 않고 다음 지시로 넘어갑니다.",
  },
  abort: {
    label: "종료",
    hint: "세션을 끝냅니다. 그때까지의 Step 은 저장할 수 있습니다.",
    tone: "danger",
  },
};

const DEFAULT_ORDER: AiChoice[] = ["takeover", "retry", "skip", "abort"];

export function AiBlockedCard({
  attempted = null,
  reason,
  choices = DEFAULT_ORDER,
  busy = false,
  onChoose,
}: AiBlockedCardProps) {
  // 서버가 준 선택지만 보여 준다. 순서는 디자인 순서로 맞춘다.
  const ordered = DEFAULT_ORDER.filter((c) => choices.includes(c));

  return (
    <div
      role="alertdialog"
      aria-label="AI 가 막혔습니다"
      style={{
        border: "3px solid var(--ink)",
        background: "var(--paper)",
        boxShadow: "5px 5px 0 var(--fail)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div className="row" style={{ gap: 8 }}>
        <strong style={{ fontSize: 14 }}>AI 가 더 진행하지 못했습니다</strong>
        <span className="spacer" />
        <span className="badge warn">세션 유지</span>
      </div>

      {attempted !== null && attempted !== "" && (
        <p className="mono" style={{ margin: 0, fontSize: 12 }}>
          시도한 동작: {attempted}
        </p>
      )}

      <p style={{ margin: 0, fontSize: 13, whiteSpace: "pre-wrap" }}>{reason}</p>

      <p className="dim" style={{ margin: 0, fontSize: 11.5 }}>
        브라우저와 화면 상태는 그대로 유지되고 있습니다. 이어받아 직접 마무리할 수 있습니다.
      </p>

      <div style={{ display: "grid", gap: 6 }}>
        {ordered.map((choice) => {
          const entry = LABELS[choice];
          return (
            <div key={choice}>
              <button
                className={entry.tone ?? (choice === "takeover" ? "" : "secondary")}
                disabled={busy}
                onClick={() => onChoose(choice)}
                style={{ width: "100%" }}
              >
                {entry.label}
              </button>
              <p className="dim" style={{ margin: "2px 0 0", fontSize: 11.5 }}>
                {entry.hint}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
