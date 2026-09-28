import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { IconButton } from "../../ui/IconButton";
import { Button } from "../../ui/Button";
import { AlwaysVisibleFailure, type WorkAreaProps } from "./WorkArea";

/**
 * 작성 현황은 **하나의 대화다** (2026-09-28 사용자 요청).
 *
 * > 「사람이 입력한 최초 프롬프트부터 시작해서, ai 의 답변, 사람이 재입력한 내용등
 * > 대화형태처럼 확인하면 좋겠다」
 *
 * 그 전에는 같은 한 흐름이 세 곳에 흩어져 있었다 — 최초 지시문은 **어디에도 없었고**
 * (`view.ai_instruction` 을 이 패널이 받지 않았다), AI 의 답과 사람의 재입력은 아래
 * 대화 칸에, 수행 자취는 위 목록에 쌓였다. 사용자는 「내가 무엇을 시켰고 AI 가 무엇을
 * 답했는가」를 두 자리를 오가며 맞춰야 했고, 처음 시킨 말은 맞출 수조차 없었다.
 *
 * 이제 한 줄기로 쌓는다. 순서는 **받은 순서**이며 그것이 실제 순서다 — `chat_turn` 과
 * `ai_progress` 는 같은 통로로 오므로 화면이 시각을 비교해 다시 세울 이유가 없다
 * (`SessionScreen` 의 `authoringLog`).
 *
 * ## 자취는 대화에 딸린다
 *
 * 수행 자취(`ai_progress`)는 AI 의 차례 **안**의 것이지 별개의 차례가 아니다. 연이은
 * 자취를 한 묶음으로 접어 대화 차례 사이에 끼운다 — 그러지 않으면 수십 줄의 자취가
 * 대화 두 마디를 갈라놓아, 합친 뜻이 사라진다.
 *
 * 자취 전체를 끌 수 있다 (「자취 숨기기」). 무엇을 시키고 무엇을 답받았는지만 훑을
 * 때 쓴다 — 옛 「진행 기록 접기」가 하던 일을 대화 기준으로 옮긴 것이다.
 */
export type AuthoringEntry =
  /** 사람이 쓴 것 — 최초 지시문·대화·막힘 답변이 모두 여기 온다. */
  | { kind: "user"; text: string; at: string }
  /** AI 가 답한 것 (`chat_turn` 의 assistant 차례). */
  | { kind: "assistant"; text: string; at: string }
  /** AI 가 수행 중에 알린 것 (`ai_progress`). */
  | { kind: "progress"; text: string; at: string }
  /** 수행이 실패했다는 사실 (`ai_error`). 자취와 같은 자리에 선다. */
  | { kind: "error"; text: string; at: string };

/** 대화 차례인가 — 자취(progress·error)와 가르는 기준. */
function isSpeech(entry: AuthoringEntry): boolean {
  return entry.kind === "user" || entry.kind === "assistant";
}

/** 말 한 마디, 또는 연이은 자취 한 묶음. */
type Block =
  | { type: "speech"; entry: AuthoringEntry; index: number }
  | { type: "trace"; entries: AuthoringEntry[]; index: number };

/**
 * 받은 순서를 지키며 **연이은 자취만** 묶는다.
 *
 * 묶음이 대화를 건너뛰지 않는 것이 요점이다 — 건너뛰면 어느 차례에 딸린 자취인지
 * 알 수 없고, 그러면 자취를 대화 안으로 옮긴 뜻이 없다.
 */
function blocksOf(entries: AuthoringEntry[]): Block[] {
  const blocks: Block[] = [];
  for (const [index, entry] of entries.entries()) {
    if (isSpeech(entry)) {
      blocks.push({ type: "speech", entry, index });
      continue;
    }
    const last = blocks.at(-1);
    if (last?.type === "trace") last.entries.push(entry);
    else blocks.push({ type: "trace", entries: [entry], index });
  }
  return blocks;
}

/** 작성 기록과 대화는 브라우저와 높이를 나누지 않는다. */
export function AiAuthoringPanel({ work, entries, instruction, status, chooseBlocked, onChooseBlocked, busy, onDismissError, children }: {
  work: WorkAreaProps["work"] | null;
  entries: AuthoringEntry[];
  /**
   * 세션을 열 때 사람이 준 지시문 (FR-063).
   *
   * **대화의 첫 차례다.** 서버의 대화 이력(`chat_turns`)에는 들어 있지 않다 — 그쪽은
   * 세션이 열린 **뒤**의 말만 받는다. 여기서 앞에 세우지 않으면 사용자가 무엇을
   * 시켜서 이 모든 것이 시작됐는지가 화면 어디에도 없다.
   */
  instruction: string | null;
  status: string;
  chooseBlocked: WorkAreaProps["chooseBlocked"];
  onChooseBlocked: WorkAreaProps["onChooseBlocked"];
  busy: boolean;
  /**
   * 지나간 실패를 치운다 (2026-09-28 사용자 보고).
   *
   * 실패는 세션을 끝내지 않으므로(FR-067) 그 뒤로도 작성이 이어지는데, 치울 길이
   * 없어 지나간 붉은 문장이 계속 서 있었다. **자취에는 남는다** — 위 타임라인의
   * 「실패: …」 줄이 그것이라, 닫아도 무엇이 있었는지 되짚을 수 있다.
   */
  onDismissError?: (() => void) | null;
  children: ReactNode;
}) {
  const log = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const [hasNew, setHasNew] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [traceOpen, setTraceOpen] = useState(true);
  const failure = work?.kind === "ai_progress" || work?.kind === "takeover_guide" ? work : null;

  /*
    최초 지시문을 첫 차례로 세운다.

    **서버가 이미 실어 준 경우에는 세우지 않는다.** 지금은 그런 경로가 없지만, 생기면
    같은 문장이 두 번 보인다 — 화면이 「없을 것」에 기대는 대신 실제로 확인한다.
  */
  const timeline = useMemo<AuthoringEntry[]>(() => {
    const first = (instruction ?? "").trim();
    if (first === "") return entries;
    if (entries.some((entry) => entry.kind === "user" && entry.text.trim() === first)) return entries;
    return [{ kind: "user", text: first, at: "" }, ...entries];
  }, [entries, instruction]);

  const blocks = useMemo(() => blocksOf(timeline), [timeline]);
  const speechCount = timeline.filter(isSpeech).length;
  const traceCount = timeline.length - speechCount;
  /** 지금 무엇을 하는 중인가 — 자취의 마지막 줄이다. 대화 차례는 여기 오지 않는다. */
  const latest = timeline.filter((entry) => !isSpeech(entry)).at(-1)?.text;

  const scrollToLatest = () => {
    following.current = true;
    setHasNew(false);
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  };
  useEffect(() => {
    if (following.current) scrollToLatest();
    else setHasNew(true);
  }, [timeline.length, historyOpen, traceOpen]);
  return (
    <div className="ai-authoring-content">
      <div className="ai-current-status" role="status">
        <strong>{status}</strong>
        {work?.kind === "takeover_guide" && work.recording && <p>직접 조작하는 내용이 Step으로 기록됩니다.</p>}
        {latest && <p>{latest}</p>}
      </div>
      <div className="ai-timeline-heading">
        <strong>대화 {speechCount}차례{traceCount > 0 ? ` · 자취 ${traceCount}줄` : ""}</strong>
        {traceCount > 0 && <Button size="sm" variant="ghost" aria-pressed={!traceOpen} onClick={() => setTraceOpen(!traceOpen)}>{traceOpen ? "자취 숨기기" : "자취 보기"}</Button>}
        <IconButton label={`대화 기록 ${historyOpen ? "접기" : "펼치기"}`} icon={historyOpen ? "collapse" : "expand"} variant="ghost" aria-expanded={historyOpen} aria-controls="ai-authoring-log" onClick={() => setHistoryOpen(!historyOpen)} />
        {hasNew && <Button size="sm" variant="ghost" onClick={() => { setHistoryOpen(true); scrollToLatest(); }}>최신 내역 보기</Button>}
      </div>
      <div id="ai-authoring-log" className="ai-timeline" ref={log} hidden={!historyOpen}
        role="log" aria-live="polite" aria-label="AI 작성 대화 기록" tabIndex={0}
        onScroll={() => {
          const el = log.current;
          if (!el) return;
          following.current = el.scrollHeight - el.scrollTop - el.clientHeight < 32;
          if (following.current) setHasNew(false);
        }}>
        {timeline.length === 0 ? <p>AI가 작성할 내용을 확인하고 있습니다.</p> :
          <ol className="ai-conversation">
            {blocks.map((block) => block.type === "speech"
              ? <Speech key={`s${block.index}`} entry={block.entry} first={block.index === 0} />
              : traceOpen && <Trace key={`t${block.index}`} entries={block.entries} />)}
          </ol>}
      </div>
      {failure && (failure.error !== null || failure.blocked !== null) && <div className="ai-authoring-attention">
        <AlwaysVisibleFailure error={failure.error} blocked={failure.blocked} choose={chooseBlocked} onChoose={onChooseBlocked} busy={busy} buttonSize="md" onDismissError={onDismissError ?? null} />
      </div>}
      <div className="ai-authoring-chat" hidden={failure?.blocked != null}>{children}</div>
    </div>
  );
}

/**
 * 말 한 마디.
 *
 * 역할 이름은 `ChatPanel` 의 말풍선과 **같은 말을 쓴다** (「나」·「AI」) — 같은 대화를
 * 두 이름으로 부르면 사용자가 둘을 다른 것으로 읽는다.
 */
function Speech({ entry, first }: { entry: AuthoringEntry; first: boolean }) {
  const mine = entry.kind === "user";
  return (
    <li className="ai-say" data-role={mine ? "user" : "assistant"}>
      <span className="ai-say-who">{mine ? "나" : "AI"}{first && mine ? " · 처음 지시" : ""}</span>
      <p>{entry.text}</p>
    </li>
  );
}

/** AI 가 수행하며 알린 것. 대화 차례에 딸린 것이므로 들여쓰고 흐린다. */
function Trace({ entries }: { entries: AuthoringEntry[] }) {
  return (
    <li className="ai-trace">
      <ol>
        {entries.map((entry, index) => (
          <li key={index} data-failed={entry.kind === "error" || undefined}
            aria-current={index === entries.length - 1 ? "step" : undefined}>{entry.text}</li>
        ))}
      </ol>
    </li>
  );
}
