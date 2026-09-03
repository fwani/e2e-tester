/**
 * "지금 할 수 있는 것" 패널 (T103·T132). `RunnerPaused.dc.html` 의 우측 액션 목록.
 *
 * 일시정지 상태에서만 보인다. 6개 액션 + 자연어 입력 박스로 FR-035~FR-039·FR-078 을
 * 한 곳에 모은다 — 사용자가 "멈췄는데 이제 뭘 할 수 있지" 를 화면에서 바로 읽게 하려는
 * 것이 이 패널의 목적이다.
 *
 * **자연어 입력의 실패는 오류가 아니다** (FR-081). 대상을 찾지 못하면 Step 을 만들지 않고
 * 그 사실을 알리며 일시정지 상태를 유지한다 — 만들어 두면 재실행에서 반드시 실패한다.
 */
import { useState } from "react";

import type { AddAssertionBody } from "../api/client";
import { AssertionForm } from "./AssertionForm";

export interface PauseActionsProps {
  /** 선택된 Step. 수정·삭제·"이 Step부터" 의 대상이다. */
  selectedStepId: string | null;
  selectedStepLabel?: string | null;
  /** 선택된 Step 의 위치. "이 Step부터 실행" 에 쓴다. */
  selectedStepIndex?: number | null;
  busy?: boolean;
  /** 지금 미러가 보고 있는 탭. 검증 대상의 기본값이다. */
  tab?: number;
  /** 직접 동작 추가 중인가 (FR-036). */
  recording?: boolean;

  onRecordActionsStart: () => void;
  onRecordActionsStop: () => void;
  onAddAssertion: (body: AddAssertionBody) => void;
  onEditStep: (stepId: string) => void;
  onReorder: () => void;
  onRunFrom: (stepIndex: number) => void;
  onDeleteStep: (stepId: string) => void;
  /** 자연어 Step 추가 (FR-078). 지원되지 않는 세션에서는 생략한다. */
  onNaturalLanguage?: (instruction: string) => void;
  /** 자연어 요청의 결과 안내. 실패 사유도 여기로 온다 (FR-081). */
  naturalLanguageNotice?: string | null;
}

export function PauseActions({
  selectedStepId,
  selectedStepLabel,
  selectedStepIndex = null,
  busy = false,
  tab,
  recording = false,
  onRecordActionsStart,
  onRecordActionsStop,
  onAddAssertion,
  onEditStep,
  onReorder,
  onRunFrom,
  onDeleteStep,
  onNaturalLanguage,
  naturalLanguageNotice = null,
}: PauseActionsProps) {
  const [showAssertion, setShowAssertion] = useState(false);
  const [instruction, setInstruction] = useState("");

  const hasSelection = selectedStepId !== null;
  const selectionHint = hasSelection
    ? `선택: ${selectedStepLabel ?? selectedStepId}`
    : "Step 을 고르면 수정·삭제·이 Step부터 실행을 쓸 수 있습니다.";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
          지금 할 수 있는 것
        </strong>
        <p className="dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
          {selectionHint}
        </p>
      </div>

      <div style={{ display: "grid", gap: 6 }}>
        {recording ? (
          <button className="danger" disabled={busy} onClick={onRecordActionsStop}>
            ■ 직접 동작 추가 끝내기
          </button>
        ) : (
          <button disabled={busy} onClick={onRecordActionsStart}>
            ✚ 직접 동작 추가
          </button>
        )}
        <p className="dim" style={{ fontSize: 11.5, margin: 0 }}>
          {recording
            ? "실제 브라우저 창에서 조작하세요. 기록된 동작이 일시정지 위치에 삽입됩니다."
            : "실제 창을 앞으로 가져와 조작을 기록합니다 (FR-036)."}
        </p>

        <button
          className="secondary"
          disabled={busy || recording}
          onClick={() => setShowAssertion((v) => !v)}
        >
          ✓ Assertion 추가
        </button>

        <button
          className="secondary"
          disabled={busy || recording || !hasSelection}
          onClick={() => selectedStepId && onEditStep(selectedStepId)}
        >
          ✎ Step 수정
        </button>

        <button className="secondary" disabled={busy || recording} onClick={onReorder}>
          ↕ 순서 변경
        </button>

        <button
          className="secondary"
          disabled={busy || recording || selectedStepIndex === null}
          onClick={() => selectedStepIndex !== null && onRunFrom(selectedStepIndex)}
        >
          ▶ 이 Step부터
        </button>

        <button
          className="danger"
          disabled={busy || recording || !hasSelection}
          onClick={() => selectedStepId && onDeleteStep(selectedStepId)}
        >
          ✕ Step 삭제
        </button>
      </div>

      {showAssertion && (
        <AssertionForm
          busy={busy}
          tab={tab}
          onCancel={() => setShowAssertion(false)}
          onSubmit={(body) => {
            onAddAssertion(body);
            setShowAssertion(false);
          }}
        />
      )}

      {onNaturalLanguage && (
        <div
          style={{
            borderTop: "2px solid var(--border)",
            paddingTop: 12,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <label htmlFor="nl-step">자연어로 Step 추가</label>
          <textarea
            id="nl-step"
            rows={3}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="생성된 프로젝트가 목록에 있는지 확인해"
          />
          <button
            className="secondary"
            disabled={busy || recording || instruction.trim() === ""}
            onClick={() => {
              onNaturalLanguage(instruction.trim());
              setInstruction("");
            }}
          >
            ✨ Step 만들기
          </button>
          <p className="dim" style={{ fontSize: 11.5, margin: 0 }}>
            지금 화면을 분석해 Step 하나를 만듭니다. 만들어진 Step 은 수동 Step 과 구조가
            같고, <strong>재실행할 때는 언어모델을 쓰지 않습니다</strong> (FR-080).
          </p>
          {naturalLanguageNotice !== null && (
            <p
              role="status"
              style={{
                margin: 0,
                fontSize: 12,
                padding: "6px 8px",
                background: "var(--warn-tint)",
                border: "2px solid var(--warn)",
              }}
            >
              {naturalLanguageNotice}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
