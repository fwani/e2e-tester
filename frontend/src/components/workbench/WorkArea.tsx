/**
 * 층③-b 국면 작업 영역 (007 T024·T101·T103 · FR-218e·FR-218e-1·FR-218f·FR-256).
 *
 * **그 국면에서 사용자가 실제로 하는 일의 유일한 자리다.** 만들기의 시작 조건, AI
 * 지시문·진행 로그·차단 사유와 선택지, 사람이 직접 조작 안내, 일시정지의 검증 추가 폼,
 * 결과의 실패 상세와 시도한 locator, 편집의 Step 편집면이 여기 온다.
 *
 * 자리의 근거는 `RunnerPaused.dc.html`·`Takeover.dc.html` 이 미러에 붙여 둔 국면 안내
 * 띠(`flex: 0 0 42px`)다. 내용에 따라 늘어나는 것은 **확정 디자인에 대응이 없으므로**
 * 승인 대상이다 (research R8 A1 · `design-conformance/undefined-states.md`).
 *
 * ## 이 파일은 자기 높이를 모른다 (2회차 · FR-256)
 *
 * 1회차에는 여기서 `flex: 0 0 auto` 와 `maxHeight: 45%` 를 하드코딩했다. 그것과
 * `TargetPane` 의 `flex: "1"` 이 합쳐져 **편집 국면에서 주 자리와 보조 자리가 뒤바뀌었다**
 * (spec S-12). 크기는 이제 `size` 인자로만 온다 — `Workbench` 가 `lib/layout.ts` 의
 * 배분표를 국면으로 조회해 내려 준다.
 *
 * 이름이 `PhaseAside`(국면 **보조** 영역)에서 바뀐 것도 같은 수정의 일부다 (FR-218e-1).
 * 그 이름이 이 자리가 담는 것을 보조로 규정했고, 그 규정이 편집 폼 전체를 42px 띠에 넣는
 * 판단으로 이어졌다.
 *
 * ## 이 파일의 유일한 불변식
 *
 * **`error` 와 `blocked` 는 값이 있으면 조건 없이 그린다** (FR-218f · FR-253).
 *
 * 001 research R2 가 규명한 결함이 정확히 이것이었다 — `ai_error` 를 렌더하는 유일한
 * 컴포넌트가 `isAiSession` 조건 뒤에 숨어, 실패가 상태에 담겨도 화면에 도달하지 못했다.
 * 사용자에게는 "아무 일도 일어나지 않음" 으로 보였다. 접힘·탭·겹침 뒤에 두지 않는다.
 */
import { useEffect, useRef, useState } from "react";

import { ErrorNotice } from "../ErrorNotice";
import { STALE_OVERWRITE_LABEL, editSavedNotice, staleReloadLabel } from "../../lib/wording";
import type { AiBlockedState, ComposeMode, WorkAreaView } from "./model";
import type { SlotSize } from "../../lib/layout";

import { Button } from "../../ui/Button";

export interface WorkAreaProps {
  work: WorkAreaView;
  /**
   * 이 자리의 크기. **국면이 정하고 `Workbench` 가 내려 준다** (FR-256).
   *
   * 이미 CSS `flex`·`minHeight` 로 환산된 값이다 — 이 파일은 `SlotSize` 의 뜻(42px 최소,
   * 424px 고정 등)을 알 필요가 없다.
   */
  /**
   * 이 자리의 배분 — **클래스로 온다** (015 T029).
   *
   * 이미 CSS 로 환산되어 있다. 이 파일은 424px 고정이 어디서 왔는지 알 필요가 없다.
   */
  sizeClass: string;
  /** 어느 국면의 것인지. 검사와 대조 기록이 읽는 표식일 뿐 분기에 쓰지 않는다 */
  sizeKind: SlotSize["kind"];
  /** AI 선택지 조작의 상태. 고를 것이 없어도 자리와 이유는 남는다 (FR-234) */
  chooseBlocked?: { kind: "enabled" } | { kind: "disabled"; reason: string } | { kind: "not_applicable" };
  onChooseBlocked?: (choice: string, answer?: string) => void;
  onReload?: () => void;
  onOverwriteStale?: () => void;
  busy?: boolean;
}

export function WorkArea({
  work,
  sizeClass,
  sizeKind,
  chooseBlocked,
  onChooseBlocked,
  onReload,
  onOverwriteStale,
  busy = false,
}: WorkAreaProps) {
  return (
    <div
      data-workbench-work={work.kind}
      data-slot-size={sizeKind}
      className={`${`border-t border-hair-2 bg-sunken-2 ${sizeClass} py-s3 px-s4 flex flex-col gap-s3`} flex-1 min-w-0 text-left h-auto py-s4 px-[18px] flex flex-col gap-s2 cursor-pointer`}
    >
      {/*
        만들기 국면 — 시작 조건 (2회차 · FR-258).

        문구와 항목은 `CreateTest.tsx`·`AiCompose.tsx` 에서 그대로 옮겼다. **새로 만든
        항목이 없다** (FR-258a) — 이름 입력과 「빈 테스트」를 그리지 않는 것이 그 뜻이다.
      */}
      {work.kind === "compose_form" && (
        <>
          {/* `test.setStartUrl` 의 자리 — 이 국면에서는 작업 영역이다 (FR-235) */}
          <Section title="시작 URL">
            <input
              id="start-url"
              data-action="test.setStartUrl"
              aria-label="시작 URL"
              value={work.startUrl}
              onChange={(e) => work.onStartUrlChange(e.target.value)}
              placeholder="https://[대상 앱 URL]/login"
              className="font-mono"
            />
          </Section>

          <Section title="만드는 방법">
            <div className="flex gap-[14px]">
              <ModeCard
                mode="record"
                title="직접 녹화"
                summary="브라우저를 직접 조작해서 테스트를 만듭니다."
                bullets={["클릭 · 입력 · 선택 · 화면 이동을 그대로 기록", "기록 중 언제든 멈추고 고칠 수 있음"]}
                selected={work.mode === "record"}
                onPick={work.onModeChange}
              />
              <ModeCard
                mode="ai"
                title="AI로 만들기"
                summary="할 일을 문장으로 쓰면 AI 가 조작하고 Step 을 만듭니다."
                bullets={["성공한 동작만 Step으로 기록", "다시 돌릴 때는 AI를 쓰지 않음"]}
                ai
                selected={work.mode === "ai"}
                onPick={work.onModeChange}
              />
            </div>
          </Section>

          {/*
            001 DR-021 — AI 를 쓸 수 있는지 **눌러 보기 전에** 말한다. 확정 디자인이
            정의하지 않은 상태이며 `CreateTest` 에 있던 것을 그대로 옮겼다.
          */}
          {work.mode === "ai" && work.aiReady !== null && !work.aiReady.available && (
            <div
              role="status"
              className="bg-warn-t border border-warn-line rounded-base font-sans text-[13px] leading-[1.4] py-[10px] px-s3 whitespace-pre-wrap"
            >
              {work.aiReady.reason ?? "AI 를 사용할 수 없습니다."}
            </div>
          )}

          {/*
            `ai.compose` 의 자리 — **방법을 고르기 전에도 있다** (FR-234 · 조건 C15).

            고른 뒤에만 나타나게 하면 「AI 로 만들 때 지시문을 쓴다」는 사실을 고른
            뒤에야 알게 된다. S-15(목록이 0개면 자리도 없다)와 같은 종류의 결함이다.
          */}
          <Section title="자연어 지시">
            <textarea
                id="ai-instruction"
                data-action="ai.compose"
                aria-label="자연어 지시"
                disabled={work.mode !== "ai"}
                rows={6}
                value={work.instruction}
                onChange={(e) => work.onInstructionChange(e.target.value)}
                placeholder={
                  "로그인한 다음 프로젝트 메뉴로 이동해서\nTEST라는 프로젝트를 생성하고\n프로젝트 목록에 TEST가 있는지 확인해."
                }
                className="border-ai min-h-auto"
              />
            {work.composeReason !== null && (
              <span
                data-disabled-reason="ai.compose"
                className="font-sans text-[11px] leading-[1.4] text-ink-3"
              >
                {work.composeReason}
              </span>
            )}
            {/* 001 FR-064 — 지시문은 기록이며 저장 대상이 아니다. 그 사실을 미리 말한다 */}
            <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
              지시문은 테스트로 저장되지 않습니다. 만들어진 Step 만 저장됩니다.
            </p>
          </Section>

          {/* 실패는 조건 없이 그린다 (FR-218f · 001 R2) */}
          {work.error !== null && <ErrorNotice error={work.error} />}
        </>
      )}

      {work.kind === "ai_progress" && (
        <>
          {/*
            **지시문은 여기 없다.** 그것은 `ai.compose` 조작이고 집은 조작 팔레트다
            (FR-235). 두 자리에 두면 같은 값이 화면에 두 번 나오고, 사용자는 둘이 다른
            것인지 확인하느라 멈춘다 — 005 U-19 가 결말 요약에서 겪은 것과 같다.

            실패는 **먼저** 온다. 로그 아래로 밀면 스크롤에 묻힌다.
          */}
          <AlwaysVisibleFailure
            error={work.error}
            blocked={work.blocked}
            choose={chooseBlocked}
            onChoose={onChooseBlocked}
            busy={busy}
          />

          <Section title="진행">
            {work.messages.length === 0 ? (
 <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
                아직 기록이 없습니다.
              </p>
            ) : (
              <ol className="font-mono font-sans text-[11px] leading-[1.4] text-ink-3 m-0 pl-[18px]">
                {work.messages.map((m, i) => (
                  <li key={`${i}-${m}`}>{m}</li>
                ))}
              </ol>
            )}
          </Section>
        </>
      )}

      {work.kind === "takeover_guide" && (
        <>
          <div
            role="status"
            className={`${work.recording ? "bg-fail-t border border-fail-line rounded-base" : "bg-warn-t border border-warn-line rounded-base"} font-sans text-[13px] font-semibold leading-none flex items-center gap-[10px] min-h-notice px-s3`}
          >
            {work.recording
              ? "사람이 조작하는 중입니다 — 지금 하는 조작이 Step 으로 기록됩니다."
              : "AI 가 멈췄습니다. 직접 조작해 이어가거나 AI 에게 돌려줄 수 있습니다."}
          </div>
          <AlwaysVisibleFailure
            error={work.error}
            blocked={work.blocked}
            choose={chooseBlocked}
            onChoose={onChooseBlocked}
            busy={busy}
          />
        </>
      )}

      {work.kind === "paused_tools" && work.tools}

      {work.kind === "failure_detail" && (
        <>
          <Section title={`실패 — ${work.step.label}`}>
            <p className="font-sans text-[13px] leading-[1.4] text-fail m-0">
              {work.step.error_message ?? "실패 이유가 기록되지 않았습니다."}
            </p>
          </Section>

          {/*
            001 FR-021·FR-054 — **그때 무엇을 시도했는가.** 결과 국면에서 사용자가
            알아야 하는 것은 정의의 후보가 아니라 실제 시도다. Step 상세를 열지 않아도
            보여야 한다 — 실패는 이 화면에 온 이유이고, 한 번 더 누르게 하면 그만큼
            원인 파악이 늦어진다 (SC-009).
          */}
          {work.step.locator_attempts.length > 0 && (
            <Section title="시도한 LOCATOR (우선순위 순)">
              <div className="flex flex-col gap-[6px]">
                {work.step.locator_attempts.map((a) => (
                  <div
                    key={`${a.candidate}-${a.expression}`}
                    className="flex items-center gap-s2 font-mono font-sans text-[11px] leading-[1.4] text-ink-3"
                  >
                    <span className={a.matched ? "pass-ink" : "fail-ink"}>
                      {a.matched ? "✓" : "×"}
                    </span>
                    <span className="flex-1 min-w-0 overflow-hidden text-ellipsis">
                      {a.expression}
                    </span>
                  </div>
                ))}
                {/*
                  004 FR-121 — **실제로 기다린 시간**이다. 예전에는 후보별 대기 중
                  최댓값을 "timeout" 이라 불렀는데, 그것은 설정값도 실측값도 아니었다.
                */}
 <div className="font-sans text-[11px] leading-[1.4] text-ink-3 pl-[20px]">
                  {`요소를 ${work.step.element_wait_ms} ms 기다렸습니다`}
                </div>
              </div>
            </Section>
          )}
          {/*
            004 FR-122·FR-123 — 진단은 **`code` 로 분기한다.** 문구를 파싱하지 않는다.
            규칙 기반이며 언어모델을 쓰지 않는다 (Principle II).
          */}
          {work.diagnosis !== null && (
            <div
              role="note"
              className="bg-warn-t border border-warn-line rounded-base font-sans text-[13px] leading-[1.4] py-s3 px-[14px]"
            >
              {work.diagnosis}
            </div>
          )}
        </>
      )}

      {work.kind === "edit_fields" && (
        <>
          <div
            className="font-sans text-[13px] font-semibold leading-none flex items-center gap-s3 min-h-notice"
          >
            <span data-pending-edits>
              {work.pendingCount === 0
                ? "바꾼 것이 없습니다"
                : `저장할 변경 ${work.pendingCount}건`}
            </span>
            {work.savedName !== null && (
              <span role="status" className="font-sans text-[13px] font-semibold leading-none text-pass">
                ✓ {editSavedNotice(work.savedName)}
              </span>
            )}
          </div>

          {/* FR-216 — 저장을 막지 않는 것들. 경고로만 알린다. */}
          {work.warnings.length > 0 && (
            <ul className="text-warn font-sans text-[13px] leading-[1.4] m-0 pl-[18px]">
              {work.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          {work.fields}

          {/* 006 FR-209 — 편집 도중 정의 파일이 밖에서 바뀌었다. */}
          {work.stale !== null && (
            <div
              role="alert"
              className="bg-warn-t border border-warn-line rounded-base p-[14px]"
            >
              <strong className="font-sans text-[13px] font-semibold leading-none">
                ⚠ 이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.
              </strong>
              <p className="font-sans text-[11px] leading-[1.4] text-ink-3 mt-[6px] mx-0 mb-[10px]">
                파일 밖에서 고친 내용이 있습니다. 어떻게 할지 고르세요.
              </p>
              {/* 무엇을 버리는지 라벨에 적는다 (006 FR-209 · ui-contract §7). */}
              <div className="flex items-center gap-s2">
                <Button size="sm" onClick={onReload}>
                  {staleReloadLabel(work.pendingCount)}
                </Button>
                <Button size="sm" variant="primary" data-action="save.overwriteStale" onClick={onOverwriteStale}>
                  {STALE_OVERWRITE_LABEL}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
      {/*
        **Step 상세는 이 자리에 오지 않는다** (2026-09-09).

        008 은 편집 국면에서 상세를 여기 인라인으로 걸었다 — 근거는 `VERTICAL_SPLIT.editing`
        이 이 자리에 `fill` 을 주면서 그 이유를 「하는 일은 Step 편집이다」로 적어 둔 것이
        었다. 사용자가 그 배치를 문제로 보고해(「한쪽에 뜨도록 해야함」) 자리가 우측 겹침
        하나로 돌아왔다 (`lib/layout.ts` 의 그 자리 주석).

        그래서 편집 국면의 이 자리는 `edit_fields` 가 채운다 — 민감 변수·저장하지 않은
        변경이고, 둘 다 없으면 무엇을 하면 되는지 말한다 (008 이 S-12 로 넣은 빈 상태).
      */}
    </div>
  );
}
/**
 * 만드는 방법 카드 (2회차 · FR-258 · 승인 대상 B7).
 *
 * `CreateTest.dc.html` 의 카드 두 장을 국면 작업 영역 폭에 맞춰 옮겼다. 선택 표시는
 * 확정 디자인의 강조 버튼과 같은 문법이다 — 채움 + 하드 오프셋 그림자.
 */
function ModeCard({
  mode,
  title,
  summary,
  bullets,
  ai = false,
  selected,
  onPick,
}: {
  mode: ComposeMode;
  title: string;
  summary: string;
  bullets: string[];
  /** AI 로 만드는 쪽인가. 사람 작성과 구분하는 유일한 색이다 (`--ai`). */
  ai?: boolean;
  selected: boolean;
  onPick: (next: ComposeMode) => void;
}) {
  return (
    <button
      type="button"
      data-compose-mode={mode}
      aria-pressed={selected}
      onClick={() => onPick(mode)}
      className={`bg-panel border border-hair rounded-base text-left text-ink${selected ? " on" : ""}${ai ? " tint-ai" : ""}`}
    >
      <span className="font-sans text-[13.5px] font-bold leading-none">{title}</span>
      <span className="font-sans text-[13.5px] leading-[1.7] text-ink-2">{summary}</span>
      <span className="flex flex-col gap-[5px]">
        {bullets.map((b) => (
 <span key={b} className="font-sans text-[11px] leading-[1.4] text-ink-3">
            {b}
          </span>
        ))}
      </span>
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-[6px]">
      <div className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">{title}</div>
      {children}
    </div>
  );
}
/**
 * 실패와 차단은 **조건 없이** 그린다 (FR-218f · FR-253 · 001 research R2).
 *
 * 이 컴포넌트가 국면·세션 상태를 인자로 받지 않는 것이 요점이다. 받으면 언젠가 그것으로
 * 분기하게 되고, 그 분기가 실패를 숨긴다.
 */
function AlwaysVisibleFailure({
  error,
  blocked,
  choose,
  onChoose,
  busy,
}: {
  error: import("../ErrorNotice").ErrorInfo | null;
  blocked: AiBlockedState | null;
  choose?: WorkAreaProps["chooseBlocked"];
  onChoose?: (choice: string, answer?: string) => void;
  busy: boolean;
}) {
  /*
    **선택지 조작의 자리는 여기다** (`ai.chooseBlocked` · ui-contract §4-1). 고를 것이
    없어도 자리와 이유를 남긴다 — 비우면 사용자는 AI 가 막혔을 때 무엇을 할 수 있는지
    화면에서 배울 수 없다 (FR-234).
  */
  const placeholder =
    error === null && blocked === null && choose !== undefined && choose.kind === "disabled" ? (
      <span
        data-action="ai.chooseBlocked"
        data-disabled-reason="ai.chooseBlocked"
        className="font-sans text-[11px] leading-[1.4] text-ink-3"
      >
        {choose.reason}
      </span>
    ) : null;
  if (error === null && blocked === null) return placeholder;
  return (
    <div data-always-visible-failure className="flex flex-col gap-[10px]">
      {error !== null && <ErrorNotice error={error} />}
      {blocked !== null && (
        <div
          role="alert"
          className="bg-fail-t border border-fail-line rounded-base py-s3 px-[14px]"
        >
          <strong className="font-sans text-[13px] font-semibold leading-none text-fail">AI 가 막혔습니다</strong>
          {blocked.attempted !== null && (
 <p className="font-sans text-[11px] leading-[1.4] text-ink-3 mt-[6px] mx-0 mb-0">
              시도: {blocked.attempted}
            </p>
          )}
          <p className="font-sans text-[13px] leading-[1.4] mt-[6px] mx-0 mb-[10px]">
            {blocked.reason}
          </p>
          {/*
            2026-09-10 사용자 결정 — **답해서 이어 가는 길**.

            「문제가 생기면 사람에게 넘기는데, 넘기는 방법이 현재는 직접 클릭으로
            takeover 하는 개념이다. 대화를 통해서 답변을 하거나 인터뷰로 답변을 하고,
            그러면 다시 AI 가 테스트 스텝을 생성하거나 수정하는 것이다」.

            **답 칸이 선택지보다 위에 온다.** 막힘의 상당수는 AI 가 화면을 못 다루는 것이
            아니라 **모르는 것이 있어서**이고, 그때 사람이 할 일은 한 문장을 쓰는 것이다.
            선택지 뒤에 두면 사용자는 그 전에 「직접 수행」을 누른다.

            질문이 없어도 칸은 열린다 — 물을 것을 특정하지 못한 채 막히는 경우가 있고,
            그때도 사람은 무엇이 문제인지 알 수 있다.
          */}
          {blocked.choices.includes("answer") && (
            <BlockedAnswer
              question={blocked.question}
              busy={busy}
              onSubmit={(text) => onChoose?.("answer", text)}
            />
          )}
          <div className="flex items-center gap-s2 flex-wrap" data-action="ai.chooseBlocked">
            {blocked.choices
              // 답변은 위 칸이 갖는다 — 같은 조작이 두 자리에 있으면 사용자는 둘이 다른
              // 것인지 확인하느라 멈춘다 (FR-235).
              .filter((c) => c !== "answer")
              .map((c) => (
                <Button key={c} size="sm" disabled={busy} onClick={() => onChoose?.(c)}>
                  {AI_CHOICE_LABEL[c] ?? c}
                </Button>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
/**
 * 막힘 선택지의 표시 문구.
 *
 * 이전에는 서버가 준 값(`takeover`·`retry`…)이 **그대로 버튼 글자**였다. 화면에 영어
 * 식별자가 그대로 나오는 자리였고, 「skip」이 무엇을 건너뛰는지 화면이 말하지 않았다.
 *
 * 사전에 없는 값은 값 그대로 보인다 — 서버가 선택지를 늘렸을 때 버튼이 사라지는 것보다
 * 낫다 (읽기 어려운 버튼은 고칠 수 있지만 없는 버튼은 알아챌 수 없다).
 */
const AI_CHOICE_LABEL: Record<string, string> = {
  takeover: "직접 조작해 이어가기",
  answer: "답하고 AI 에게 돌려주기",
  retry: "AI 에게 다시",
  skip: "이 동작 건너뛰기",
  abort: "AI 작성 끝내기",
};
/**
 * AI 에게 답을 써서 돌려주는 칸 (2026-09-10 사용자 결정).
 *
 * **입력을 여기서 들고 있는다.** 바깥(`SessionScreen`)에 두면 막힘 상태가 갱신될 때마다
 * 쓰던 문장이 날아간다 — AI 는 답을 기다리는 동안에도 이벤트를 낸다.
 *
 * `Enter` 로 보내지 않는다. 여러 줄로 설명하는 것이 정상이고, 그 자리에서 `Enter` 가
 * 전송이면 문단을 나누다 실수로 보낸다.
 */
function BlockedAnswer({
  question,
  busy,
  onSubmit,
}: {
  question: string | null;
  busy: boolean;
  onSubmit: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const box = useRef<HTMLTextAreaElement | null>(null);
  const ready = text.trim() !== "";
  /*
    **막힘이 뜨면 초점이 이 칸에 온다.**

    막힘은 세션이 멈춘 상태이고, 이 칸이 그 상태에서 하려는 일의 첫 자리다 (위 주석).
    초점을 옮기지 않으면 키보드로 도는 사용자는 화면 어딘가에 새로 생긴 칸을 Tab 으로
    찾아야 한다 — 세션이 멈춰 있으므로 초점을 빼앗을 다른 일이 없다.

    막힘이 갱신될 때마다 다시 옮기지 않는다(의존성 없음) — 쓰던 중에 초점이 되돌아가면
    커서 위치가 날아간다.
  */
  useEffect(() => {
    box.current?.focus();
  }, []);

  const send = () => {
    if (busy || !ready) return;
    onSubmit(text.trim());
    setText("");
  };

  return (
    <div
      data-blocked-answer
      className="flex flex-col gap-[6px] mb-[10px]"
    >
      {/*
        **질문은 라벨이 아니다.** `.lbl` 은 11px 대문자 모노이고 한 문장을 읽는 형태가
        아니다 — AI 의 질문이 그 형태로 그려지면 사용자는 자기가 무엇을 답해야 하는지
        읽기 어렵다. 이름표는 짧게 두고 질문은 본문으로 읽는다.
      */}
      <label className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3" htmlFor="blocked-answer">
        {question !== null ? "AI 의 질문" : "AI 에게 알려 주기"}
      </label>
      {question !== null && (
        <p className="font-sans text-[13px] leading-[1.4] text-ink m-0" data-blocked-question>
          {question}
        </p>
      )}
      <textarea
        id="blocked-answer"
        ref={box}
        rows={3}
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        /*
          `Enter` 는 줄바꿈이다 — 여러 줄로 설명하는 것이 정상이므로 전송으로 쓰면
          문단을 나누다 실수로 보낸다 (위 주석). 그래도 **손을 마우스로 옮기지 않고
          보낼 길**은 있어야 하므로 `Cmd`/`Ctrl` + `Enter` 를 받는다. 아래 힌트가 그
          사실을 말한다 — 화면이 말하지 않는 단축키는 없는 것과 같다.
        */
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            send();
          }
        }}
        placeholder={
          question !== null
            ? "여기에 답을 적으면 AI 가 그 자리에서 이어서 진행합니다."
            : "무엇을 하면 되는지 알려 주면 AI 가 이어서 진행합니다. 예) 저장 버튼은 오른쪽 위 「등록」입니다."
        }
        className="min-h-auto"
      />
      <div className="flex items-center gap-s2">
        <Button
          size="sm" variant="primary"
          data-blocked-answer-send
          disabled={busy || !ready}
          onClick={send} >
          답하고 계속
        </Button>
        {/*
          힌트를 조건부로 그리면 첫 글자를 치는 순간 그 줄이 사라지고 아래가 위로
          튄다. 자리를 고정하고 문구만 바꾼다 (`.hint-line`).
        */}
        <span data-hint-line className="font-sans text-[11px] leading-[1.4] text-ink-3 min-h-[16px]">
          {ready
            ? "Cmd/Ctrl + Enter 로도 보냅니다. 이미 만든 Step 은 그대로입니다."
            : "답을 적으면 AI 가 같은 대화에 이어서 진행합니다. 이미 만든 Step 은 그대로입니다."}
        </span>
      </div>
    </div>
  );
}
