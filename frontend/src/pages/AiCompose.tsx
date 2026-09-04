/**
 * AI 지시문 작성. `docs/design/AiRecord.dc.html` 의 **작성 전 상태**다.
 *
 * 확정 디자인은 「AI 수행 중」 하나만 보여준다. 지시문을 쓰는 순간은 정의돼 있지 않아
 * 같은 화면(`AiRecord`)을 `composing` 으로 그린다 — 확정 디자인에 없는 새 화면을
 * 만들지 않는다 (DC-007). 이 결정은 `undefined-states.md` 에 기록했다 (DC-009).
 *
 * **화면을 나누는 이유**: `CreateTest.dc.html` 의 AI 카드 버튼은 「지시문 쓰기」다.
 * 001 은 그 화면에 textarea 를 끼워 넣었는데, 확정 디자인에 없는 요소를 더한 것이라
 * DC-007 위반이었다.
 *
 * DR-016 — 실행하면 화면이 **즉시** 바뀐다. 아무 변화 없이 끝나지 않는다.
 */
import { useState } from "react";
import { describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { sessions, type SessionView } from "../api/client";
import { AiRecord } from "./AiRecord";

export function AiCompose({
  startUrl,
  onCancel,
  onStarted,
}: {
  startUrl: string;
  onCancel: () => void;
  onStarted: (session: SessionView, instruction: string) => void;
}) {
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const start = () => {
    setBusy(true);
    setError(null);
    void sessions
      .create({ mode: "ai", start_url: startUrl, ai_instruction: instruction.trim() })
      .then((session) => onStarted(session, instruction.trim()))
      .catch((exc: unknown) => {
        // DR-016·DR-022 — 조용히 끝나지 않는다. 사유를 화면에 남긴다.
        setError(describeError(exc));
      })
      .finally(() => setBusy(false));
  };

  return (
    <AiRecord
      instruction={instruction}
      composing
      onInstructionChange={setInstruction}
      onStart={start}
      running={false}
      steps={[]}
      messages={[]}
      error={error}
      blocked={null}
      busy={busy}
      saveName=""
      onSaveNameChange={() => undefined}
      onSave={() => undefined}
      onStop={onCancel}
      currentUrl={startUrl}
    />
  );
}
