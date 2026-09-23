import { useEffect, useRef, useState, type ReactNode } from "react";
import { IconButton } from "../../ui/IconButton";
import { Button } from "../../ui/Button";
import { AlwaysVisibleFailure, type WorkAreaProps } from "./WorkArea";

/** 작성 기록과 대화는 브라우저와 높이를 나누지 않는다. */
export function AiAuthoringPanel({ work, messages, status, chooseBlocked, onChooseBlocked, busy, children }: {
  work: WorkAreaProps["work"] | null;
  messages: string[];
  status: string;
  chooseBlocked: WorkAreaProps["chooseBlocked"];
  onChooseBlocked: WorkAreaProps["onChooseBlocked"];
  busy: boolean;
  children: ReactNode;
}) {
  const log = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const [hasNew, setHasNew] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(true);
  const failure = work?.kind === "ai_progress" || work?.kind === "takeover_guide" ? work : null;
  const latest = messages.at(-1);
  const scrollToLatest = () => {
    following.current = true;
    setHasNew(false);
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  };
  useEffect(() => {
    if (following.current) scrollToLatest();
    else setHasNew(true);
  }, [messages.length, historyOpen]);
  return (
    <div className="ai-authoring-content">
      <div className="ai-current-status" role="status">
        <strong>{status}</strong>
        {work?.kind === "takeover_guide" && work.recording && <p>직접 조작하는 내용이 Step으로 기록됩니다.</p>}
        {latest && <p>{latest}</p>}
      </div>
      <div className="ai-timeline-heading">
        <strong>진행 기록 {messages.length}개</strong>
        <IconButton label={`진행 기록 ${historyOpen ? "접기" : "펼치기"}`} icon={historyOpen ? "collapse" : "expand"} variant="ghost" aria-expanded={historyOpen} aria-controls="ai-authoring-log" onClick={() => setHistoryOpen(!historyOpen)} />
        {hasNew && <Button size="sm" variant="ghost" onClick={() => { setHistoryOpen(true); scrollToLatest(); }}>최신 내역 보기</Button>}
      </div>
      <div id="ai-authoring-log" className="ai-timeline" ref={log} hidden={!historyOpen}
        role="region" aria-label="AI 작성 진행 기록" tabIndex={0}
        onScroll={() => {
          const el = log.current;
          if (!el) return;
          following.current = el.scrollHeight - el.scrollTop - el.clientHeight < 32;
          if (following.current) setHasNew(false);
        }}>
        {messages.length === 0 ? <p>AI가 작성할 내용을 확인하고 있습니다.</p> :
          <ol>{messages.map((message, index) => <li key={index} aria-current={index === messages.length - 1 ? "step" : undefined}>{message}</li>)}</ol>}
      </div>
      {failure && (failure.error !== null || failure.blocked !== null) && <div className="ai-authoring-attention">
        <AlwaysVisibleFailure error={failure.error} blocked={failure.blocked} choose={chooseBlocked} onChoose={onChooseBlocked} busy={busy} buttonSize="md" />
      </div>}
      <div className="ai-authoring-chat" hidden={failure?.blocked != null}>{children}</div>
    </div>
  );
}
