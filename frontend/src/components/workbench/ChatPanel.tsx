/**
 * AI 와의 대화 (016 US1 · FR-007~FR-014 · contracts/ui-contract.md §3-1).
 *
 * ## 자리는 보이되 잠긴다
 *
 * 세션이 없는 편집 국면에서도 **자리가 보인다.** 잠긴 채로, 「먼저 AI 로 다시 만들기로
 * 시작하세요」를 가리키면서. 감추면 이 기능이 있다는 사실을 알 방법이 없고, 그것이
 * 감춰진 조작이다 (FR-234).
 *
 * 판단은 여기 없다 — `capabilities.ts` 의 표가 `ai.chat` 셀로 정한다 (UC-000).
 *
 * ## 막힘은 그리지 않는다
 *
 * AI 가 막히면 기존 `ai_blocked` 5선택지가 뜬다. 이 패널은 **그리로 가리키기만** 한다
 * (`USE_BLOCKED_ANSWER`). 두 곳에서 답을 받으면 사용자는 어느 쪽에 써야 하는지 모르고,
 * 그것이 초안 국면표가 `cond(C11)` 로 만들려던 상태였다 (analyze F1).
 *
 * ## 진행과 중지는 기존 것을 쓴다
 *
 * 진행은 `ai_progress` 이벤트(FR-060)가 이미 흐르고, 중지는 `run.pause` 다. 새 버튼을
 * 만들지 않는다 — 「한 조작에 한 자리」(FR-235)이고, 중지 버튼이 둘이면 사용자는 어느
 * 쪽이 무엇을 멈추는지 판단해야 한다.
 */
import { useEffect, useRef, useState, type FormEvent } from "react";

import type { ChatTurn } from "../../api/client";
import type { ActionId } from "../../lib/actions";
import type { CapabilityState } from "../../lib/capabilities";
import { Notice } from "../../ui/Notice";
import { ActionButton } from "./ActionButton";

/** 지시문과 **같은 상한**이다 (FR-010). 두 입구가 다르면 사용자가 외워야 한다. */
export const CHAT_MAX_CHARS = 8000;

export interface ChatPanelProps {
  turns: ChatTurn[];
  capability: CapabilityState;
  /** 지금 AI 가 도는 중인가. `ai_progress` 의 마지막 메시지를 함께 보여 준다. */
  busy?: boolean;
  progress?: string | null;
  /** 언어모델을 쓸 수 없을 때의 사유 (FR-012). 서버가 준 문장을 **그대로** 쓴다. */
  unavailableReason?: string | null;
  onSend: (text: string) => void;
  onRemedy?: (action: ActionId) => void;
}

export function ChatPanel({
  turns,
  capability,
  busy = false,
  progress = null,
  unavailableReason = null,
  onSend,
  onRemedy,
}: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const tail = useRef<HTMLDivElement | null>(null);

  /*
    새 차례가 붙으면 끝으로 따라간다. 따라가지 않으면 사용자가 매번 스크롤해야 하고,
    AI 가 길게 답할수록 그 비용이 커진다.

    **있는지 확인하고 부른다.** `scrollIntoView` 는 jsdom 에 없다 — 검사 환경에서
    터지면 「대화 패널이 있는가」를 묻는 검사가 스크롤 때문에 실패한다. 편의 기능이
    없는 환경에서 화면이 죽지 않는 것이 옳기도 하다.
  */
  useEffect(() => {
    tail.current?.scrollIntoView?.({ block: "end" });
  }, [turns.length, progress]);

  const enabled = capability.kind === "enabled" && !busy && unavailableReason === null;
  const tooLong = draft.length > CHAT_MAX_CHARS;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const text = draft.trim();
    if (!enabled || !text || tooLong) return;
    onSend(text);
    setDraft("");
  };

  return (
    <section className="flex flex-col gap-s3" aria-label="AI 와 대화">
      <div className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">
        AI 와 대화
      </div>

      {/*
        **언어모델을 쓸 수 없을 때** (FR-012).
        서버가 준 사유를 그대로 보여 준다 — 화면이 문장을 지어내면 실제 원인과 갈린다.
        나머지 편집 조작은 영향을 받지 않으므로 이 자리만 말한다.
      */}
      {unavailableReason !== null && (
        <Notice tone="warn" role="status">
          {unavailableReason}
        </Notice>
      )}

      <div
        className="flex flex-col gap-s2 overflow-y-auto"
        role="log"
        aria-live="polite"
        aria-label="대화 기록"
      >
        {turns.length === 0 && unavailableReason === null && (
          <p className="text-ink-3">
            이 테스트에 대해 물어보거나, 다시 만들 내용을 지시하세요.
          </p>
        )}
        {turns.map((turn, index) => (
          <ChatBubble key={`${turn.at}-${index}`} turn={turn} />
        ))}
        {busy && (
          <p className="text-ink-3" role="status">
            {progress ?? "AI 가 수행 중입니다…"}
          </p>
        )}
        <div ref={tail} />
      </div>

      <form onSubmit={submit} className="flex flex-col gap-s2">
        <label className="sr-only" htmlFor="ai-chat-input">
          AI 에게 할 말
        </label>
        <textarea
          id="ai-chat-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!enabled}
          rows={3}
          placeholder="예: 이번엔 SSO 로 로그인해"
        />
        {/*
          상한을 **입력 시점에** 보여 준다 (FR-010). 보낸 뒤에 거절하면 사용자는 쓴 것을
          다시 줄여야 하고, 긴 지시일수록 그 손실이 크다.
        */}
        <div className="flex items-center justify-between gap-s2">
          <span className={tooLong ? "text-fail" : "text-ink-3"}>
            {draft.length} / {CHAT_MAX_CHARS}
          </span>
          <ActionButton
            action="ai.chat"
            capability={capability}
            emphasis
            onRun={() => submit(new Event("submit") as unknown as FormEvent)}
            onRemedy={onRemedy}
          />
        </div>
      </form>
    </section>
  );
}

function ChatBubble({ turn }: { turn: ChatTurn }) {
  const mine = turn.role === "user";
  return (
    <div className="flex flex-col gap-[2px]">
      <span className="font-mono text-[11px] uppercase tracking-[.08em] text-ink-3">
        {mine ? "나" : "AI"}
      </span>
      <p className="whitespace-pre-wrap">{turn.text}</p>
    </div>
  );
}
