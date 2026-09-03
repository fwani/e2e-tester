/**
 * 테스트 만들기 (T065). `CreateTest.dc.html` 이식.
 *
 * FR-008·FR-009: 작성 방식·시작 URL·브라우저 선택. **두 방식이 같은 Step 모델로
 * 저장됨을 사용자에게 알린다** — 원칙 I 을 사용자에게 설명하는 지점이다.
 */
import { useState } from "react";

import { ApiError, sessions, type ProjectView, type SessionView } from "../api/client";

export interface CreateTestProps {
  project: ProjectView;
  /** 세션과 함께 지시문을 넘긴다 — Runner 가 화면에 표시한다 (FR-064). */
  onStarted: (session: SessionView, aiInstruction: string | null) => void;
  onCancel: () => void;
}

type Mode = "record" | "ai";

export function CreateTest({ project, onStarted, onCancel }: CreateTestProps) {
  const [mode, setMode] = useState<Mode>("record");
  const [startUrl, setStartUrl] = useState(project.default_start_url);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const aiInstruction = mode === "ai" ? instruction.trim() : null;
      onStarted(
        await sessions.create({
          mode,
          start_url: startUrl.trim(),
          ai_instruction: aiInstruction,
        }),
        aiInstruction,
      );
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main style={{ maxWidth: 760, margin: "32px auto", padding: "0 16px" }}>
      <div className="row">
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: 22, margin: 0 }}>
          테스트 만들기
        </h1>
        <span className="spacer" />
        <button className="ghost" onClick={onCancel} aria-label="닫기">
          ✕
        </button>
      </div>

      <p className="muted">
        만드는 방법을 고르세요. 어느 쪽으로 만들어도 <strong>같은 Step 모델</strong>로
        저장되고, 실행은 Playwright 가 합니다.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <MethodCard
          selected={mode === "record"}
          onSelect={() => setMode("record")}
          title="직접 녹화"
          description="브라우저를 직접 조작해서 테스트를 만듭니다."
          bullets={[
            "클릭 · 입력 · 선택 · 화면 이동을 그대로 기록",
            "기록 중 언제든 멈추고 고칠 수 있음",
          ]}
          cta="녹화 시작"
        />
        <MethodCard
          selected={mode === "ai"}
          onSelect={() => setMode("ai")}
          title="✨ AI 로 만들기"
          description="할 일을 말로 적으면 AI 가 브라우저에서 해봅니다."
          bullets={["성공한 동작만 Step 으로 기록", "다시 돌릴 때는 AI 를 쓰지 않음"]}
          cta="지시문 쓰기"
          accent
        />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <label htmlFor="start-url">시작 URL</label>
        <input
          id="start-url"
          value={startUrl}
          onChange={(e) => setStartUrl(e.target.value)}
        />

        <label htmlFor="browser">브라우저</label>
        <select id="browser" value={project.browser} disabled>
          <option value="chromium">Chromium</option>
        </select>
        <p className="dim" style={{ fontSize: 12, marginTop: 4 }}>
          MVP 는 Chromium 만 지원합니다.
        </p>

        {mode === "ai" && (
          <>
            <label htmlFor="instruction">자연어 지시</label>
            <textarea
              id="instruction"
              rows={4}
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder={
                "로그인한 다음 프로젝트 메뉴로 이동해서\nTEST 라는 프로젝트를 생성하고\n" +
                "프로젝트 목록에 TEST 가 있는지 확인해."
              }
            />
            <p className="dim" style={{ fontSize: 12, marginTop: 4 }}>
              지시문은 테스트로 저장되지 않습니다. AI 가 실제로 성공한 동작만 Step 으로
              저장되고, 다시 돌릴 때는 AI 를 쓰지 않습니다.
            </p>
          </>
        )}

        {error !== null && (
          <p style={{ color: "var(--fail-dark)", whiteSpace: "pre-wrap" }}>{error}</p>
        )}

        <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}>
          <button className="secondary" onClick={onCancel}>
            취소
          </button>
          <button
            disabled={
              busy ||
              startUrl.trim() === "" ||
              (mode === "ai" && instruction.trim() === "")
            }
            onClick={() => void start()}
          >
            {mode === "record" ? "녹화 시작 →" : "AI 실행 →"}
          </button>
        </div>
      </div>
    </main>
  );
}

function MethodCard({
  selected,
  onSelect,
  title,
  description,
  bullets,
  cta,
  accent = false,
}: {
  selected: boolean;
  onSelect: () => void;
  title: string;
  description: string;
  bullets: string[];
  cta: string;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className="secondary"
      style={{
        display: "block",
        textAlign: "left",
        padding: 18,
        borderRadius: "var(--radius)",
        borderWidth: 2,
        borderColor: selected ? (accent ? "var(--ai)" : "var(--ink)") : "var(--border)",
        background: selected && accent ? "var(--ai-tint)" : "var(--paper)",
      }}
    >
      <strong style={{ fontSize: 15 }}>{title}</strong>
      <p className="muted" style={{ margin: "8px 0" }}>
        {description}
      </p>
      <ul className="dim" style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
        {bullets.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
      <div style={{ marginTop: 12, fontWeight: 600 }}>{cta} →</div>
    </button>
  );
}
