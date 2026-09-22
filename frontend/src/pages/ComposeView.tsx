/** Start a test with only its URL, authoring method and selected start action. */
import { useEffect, useState } from "react";
import { ApiError, ai } from "../api/client";
import type { ProjectView } from "../api/client";
import { describeError, type ErrorInfo } from "../components/ErrorNotice";
import { ActionButton } from "../components/workbench/ActionButton";
import { WorkArea } from "../components/workbench/WorkArea";
import type { ComposeMode } from "../components/workbench/model";
import { capabilitiesFor } from "../lib/capabilities";
export interface ComposeViewProps {
  project: ProjectView | null;
  onCancel: () => void;
  /**
   * 직접 녹화 — 시작 URL 을 들고 녹화 세션을 만든다 (`record.start`).
   *
   * `CreateTest.onRecord` 와 같은 계약이다. `App` 의 기존 `sessions.create` 경로를
   * 그대로 쓴다.
   */
  onRecord: (startUrl: string) => void;
  /**
   * AI 시작 — 지시문과 함께 AI 세션을 만든다 (`ai.start`).
   *
   * 1회차에는 `CreateTest` 가 지시문 화면으로 넘기고 그 화면이 세션을 만들었다.
   * 화면이 하나가 되면서 **중간 단계가 사라진다** — 그것이 SC-011(껍데기가 바뀌는 횟수
   * 0)의 뜻이다.
   */
  onStartAi: (startUrl: string, instruction: string) => void;
  busy?: boolean;
  /**
   * 초안에서 출발했을 때 지시문 칸을 미리 채운다 (014 FR-031).
   *
   * **사용자가 고칠 수 있어야 한다** — 서버가 지은 문장이 늘 맞지는 않고, 고칠 수
   * 없으면 사용자는 초안을 지우고 처음부터 쓰게 된다. 그래서 값이 아니라 **초기값**이다.
   */
  initialInstruction?: string | null;
  /** 초안에서 출발했음을 화면에 알린다. 어느 초안인지 보여 줄 때 쓴다. */
  fromDraft?: { draft_id: string; name: string } | null;
}

export function ComposeView({ project, onCancel, onRecord, onStartAi, busy = false,
  initialInstruction = null, fromDraft = null }: ComposeViewProps) {
  const [startUrl, setStartUrl] = useState(project?.default_start_url ?? "");
  const [mode, setMode] = useState<ComposeMode>(fromDraft !== null ? "ai" : "record");
  const [instruction, setInstruction] = useState(initialInstruction ?? "");
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [aiReady, setAiReady] = useState<{ available: boolean; reason: string | null } | null>(null);
  useEffect(() => {
    void ai.availability().then(setAiReady).catch((exc: unknown) =>
      setAiReady({ available: false, reason: exc instanceof ApiError ? exc.message : String(exc) }));
  }, []);
  const capabilities = capabilitiesFor("composing", {
    hasInstruction: instruction.trim() !== "", aiModeChosen: mode === "ai", busy,
  });
  const start = () => {
    if (busy) return;
    setError(null);
    if (!/^https?:\/\//.test(startUrl.trim())) {
      setError(describeError(new Error("시작 URL 이 http:// 또는 https:// 로 시작해야 합니다.")));
      return;
    }
    if (mode === "ai") {
      if (!instruction.trim()) return;
      onStartAi(startUrl.trim(), instruction.trim());
    } else onRecord(startUrl.trim());
  };
  const action = mode === "ai" ? "ai.start" : "record.start";
  return (
    <main className="compose-start" data-compose-start aria-labelledby="compose-title">
      <header className="compose-start-heading">
        <h1 id="compose-title">새 테스트</h1>
        <p>시작 주소를 입력하고 테스트를 작성하세요.</p>
      </header>
      {fromDraft !== null && (
        <p className="compose-draft" data-from-draft={fromDraft.draft_id}>
          초안 「{fromDraft.name}」에서 시작합니다. 지시문을 고쳐도 됩니다. 저장하면 이 초안은 사라집니다.
        </p>
      )}
      <WorkArea work={{
        kind: "compose_form", startUrl, mode, instruction, aiReady, error,
        onStartUrlChange: (value) => { setStartUrl(value); setError(null); },
        onModeChange: setMode, onInstructionChange: setInstruction,
      }} sizeClass="" sizeKind="content" busy={busy} />
      <div className="compose-start-actions">
        <ActionButton action={action} capability={capabilities[action]} emphasis onRun={start} />
        <ActionButton action="nav.back" capability={capabilities["nav.back"]} onRun={onCancel} emphasis="quiet" />
      </div>
    </main>
  );
}
