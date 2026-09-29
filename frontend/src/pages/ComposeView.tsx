/** Start a test with only its URL, authoring method and selected start action. */
import { useEffect, useState } from "react";
import { ApiError, ai } from "../api/client";
import type { ProjectView, RefineResponse, WorkPlan } from "../api/client";
import { describeError, type ErrorInfo } from "../components/ErrorNotice";
import { ActionButton } from "../components/workbench/ActionButton";
import { PlanPanel } from "../components/workbench/PlanPanel";
import { WorkArea } from "../components/workbench/WorkArea";
import type { ComposeMode } from "../components/workbench/model";
import { capabilitiesFor } from "../lib/capabilities";
import { Button } from "../ui/Button";
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
  onStartAi: (
    startUrl: string,
    instruction: string,
    /**
     * 사용자가 확인하고 확정한 작업 계획 (025 FR-018).
     *
     * **`null` 일 수 있다** — 정제에 실패했거나 사용자가 원문으로 진행을 골랐다.
     * 그때 작성은 016 이전과 같이 동작한다 (FR-012).
     */
    plan?: WorkPlan | null,
  ) => void;
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
  /**
   * 정제 결과. **작성을 시작하기 전에 사용자가 확인한다** (025 FR-018).
   *
   * 브라우저가 뜬 뒤에 고치게 하면 사용자는 이미 시작된 일을 되돌려야 한다. 두 단계로
   * 나누면 「시작했다가 취소한 세션」이라는 상태 자체가 생기지 않는다 (research R7).
   */
  const [refined, setRefined] = useState<RefineResponse | null>(null);
  const [refining, setRefining] = useState(false);
  /** 정제 중에는 시작 버튼을 잠근다 — 두 번 눌러 두 번 정제하는 일을 막는다. */
  useEffect(() => {
    void ai.availability().then(setAiReady).catch((exc: unknown) =>
      setAiReady({ available: false, reason: exc instanceof ApiError ? exc.message : String(exc) }));
  }, []);
  const capabilities = capabilitiesFor("composing", {
    // 정제 중에도 잠근다 — 두 번 눌러 두 번 정제하는 일을 막는다. 정제는 모델 호출이다.
    hasInstruction: instruction.trim() !== "", aiModeChosen: mode === "ai", busy: busy || refining,
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
      void refineThenAsk();
    } else onRecord(startUrl.trim());
  };

  /**
   * 정제하고 **사용자에게 보여 준다.** 아직 세션을 만들지 않는다 (FR-018).
   *
   * **정제 실패를 오류로 다루지 않는다** (FR-020). 실패해도 원문으로 진행하는 길이
   * 열려 있어야 하고, 그것이 이 기능의 경계다 — 정제가 작성을 막는 관문이 되면 안 된다.
   */
  const refineThenAsk = async () => {
    setRefining(true);
    try {
      const result = await ai.refine(instruction.trim());
      setRefined(result);
    } catch {
      // 호출 자체가 실패해도 같은 자리로 수렴한다. 사용자는 원문으로 진행할 수 있다.
      setRefined({
        refined: false,
        plan: null,
        notes: ["지시문을 정제하지 못했습니다. 원문 그대로 진행할 수 있습니다."],
      });
    } finally {
      setRefining(false);
    }
  };

  /** 확정한 계획으로 시작한다. 거절했으면 `null` 이 간다. */
  const startWith = (plan: WorkPlan | null) => {
    onStartAi(startUrl.trim(), instruction.trim(), plan);
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
      {refined !== null && (
        <section className="compose-refined" aria-label="정제 결과">
          <h2>이렇게 진행합니다</h2>
          {refined.notes.length > 0 && (
            <ul className="compose-refined-notes">
              {refined.notes.map((note, index) => (
                <li key={`${note}-${index}`}>{note}</li>
              ))}
            </ul>
          )}
          <PlanPanel plan={refined.plan} />
          <div className="compose-refined-actions">
            {refined.plan !== null && (
              <Button variant="primary" onClick={() => startWith(refined.plan)} disabled={busy}>
                이 계획으로 시작
              </Button>
            )}
            {/*
              **원문으로 진행하는 길은 항상 열려 있다** (FR-019·FR-020). 정제가 실패했든
              사용자가 결과를 받아들이지 않든, 작성을 시작할 수 있어야 한다.
            */}
            <Button variant="ghost" onClick={() => startWith(null)} disabled={busy}>
              원문으로 시작
            </Button>
            <Button variant="ghost" onClick={() => setRefined(null)} disabled={busy}>
              지시문 고치기
            </Button>
          </div>
        </section>
      )}
      <div className="compose-start-actions">
        {refined === null && (
          <ActionButton
            action={action}
            capability={capabilities[action]}
            emphasis
            onRun={start}
          />
        )}
        <ActionButton action="nav.back" capability={capabilities["nav.back"]} onRun={onCancel} emphasis="quiet" />
      </div>
    </main>
  );
}
