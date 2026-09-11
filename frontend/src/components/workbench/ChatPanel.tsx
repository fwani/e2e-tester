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
  /** 지금 AI 가 도는 중인가. */
  busy?: boolean;
  /**
   * 이번 턴에 AI 가 **무엇을 하고 있는지** (FR-011 · 2026-09-11 사용자 요청).
   *
   * **마지막 한 줄이 아니라 자취 전체다.** 한 줄만 보이면 사용자는 「지금」만 알고
   * 「무엇을 거쳐 왔는지」를 모른다 — 막히거나 엉뚱한 것을 눌렀을 때 어디서
   * 어긋났는지 되짚을 수 없다.
   *
   * `ai_progress` 이벤트를 턴 단위로 모은 것이며, 턴이 시작될 때 비워진다.
   */
  progress?: string[];
  /** 언어모델을 쓸 수 없을 때의 사유 (FR-012). 서버가 준 문장을 **그대로** 쓴다. */
  unavailableReason?: string | null;
  onSend: (text: string) => void;
  onRemedy?: (action: ActionId) => void;
}

export function ChatPanel({
  turns,
  capability,
  busy = false,
  progress = [],
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
  }, [turns.length, progress.length]);

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
        {/*
          **자취를 그대로 보인다** (FR-011).

          AI 가 도는 동안 무엇을 하는 중인지가 사용자가 읽는 것이다. 도구가 시도
          **전에** 알리므로(`BrowserToolbox._announce`), 요소를 기다리는 동안에도
          줄이 하나 서 있고 실패하면 그 줄 다음에 사유가 붙는다.

          턴이 끝나면 사라진다 — 남은 기록은 AI 의 답(대화 차례)이다. 둘을 함께
          쌓으면 「무엇을 했는가」와 「무엇을 하는 중인가」가 섞인다.
        */}
        {busy && (
          <div className="flex flex-col gap-[2px]" role="status" aria-live="polite">
            <span className="font-mono text-[11px] uppercase tracking-[.08em] text-ink-3">
              수행 중
            </span>
            {progress.length === 0 ? (
              <p className="text-ink-3">AI 가 수행 중입니다…</p>
            ) : (
              <ol className="flex flex-col gap-[2px]">
                {progress.map((line, i) => (
                  <li
                    key={`${i}-${line}`}
                    /* 마지막 줄이 지금 하는 일이다. 앞의 것은 지나간 것이므로 흐린다 */
                    /* 마지막 줄은 기본 글자색 — 따로 지정하지 않는다 */
                    className={i === progress.length - 1 ? undefined : "text-ink-3"}
                  >
                    {line}
                  </li>
                ))}
              </ol>
            )}
          </div>
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
