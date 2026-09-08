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
import type { ReactNode } from "react";

import { ErrorNotice } from "../ErrorNotice";
import { STALE_OVERWRITE_LABEL, editSavedNotice, staleReloadLabel } from "../../lib/wording";
import type { AiBlockedState, ComposeMode, WorkAreaView } from "./model";
import type { SlotSize, SlotStyle } from "../../lib/layout";

/**
 * 국면 안내 띠 **자체**의 높이. `RunnerPaused`·`Takeover` 의 `flex: 0 0 42px`.
 *
 * **자리의 최소 높이와 다른 값이다.** 자리의 크기는 `size` 인자로 오고 (FR-256), 이것은
 * 그 안에 놓이는 띠 하나의 높이다. 1회차에는 둘이 같은 `MIN_HEIGHT` 상수였고, 그래서
 * 자리의 크기를 고치려면 띠의 높이도 함께 움직였다.
 */
const GUIDE_BAND_HEIGHT = 32;

export interface WorkAreaProps {
  work: WorkAreaView;
  /**
   * 이 자리의 크기. **국면이 정하고 `Workbench` 가 내려 준다** (FR-256).
   *
   * 이미 CSS `flex`·`minHeight` 로 환산된 값이다 — 이 파일은 `SlotSize` 의 뜻(42px 최소,
   * 424px 고정 등)을 알 필요가 없다.
   */
  size: SlotStyle;
  /** 어느 국면의 것인지. 검사와 대조 기록이 읽는 표식일 뿐 분기에 쓰지 않는다 */
  sizeKind: SlotSize["kind"];
  /** AI 선택지 조작의 상태. 고를 것이 없어도 자리와 이유는 남는다 (FR-234) */
  chooseBlocked?: { kind: "enabled" } | { kind: "disabled"; reason: string } | { kind: "not_applicable" };
  onChooseBlocked?: (choice: string) => void;
  onReload?: () => void;
  onOverwriteStale?: () => void;
  /**
   * Step 상세를 이 자리에 걸었을 때의 그것 (008 · `DETAIL_PLACEMENT`).
   *
   * `Workbench` 가 국면 표를 보고 인라인이면 여기로, 겹침이면 자기가 직접 띄운다.
   * **이 파일은 어느 쪽인지 판단하지 않는다** — 받으면 그린다.
   */
  detail?: ReactNode;
  busy?: boolean;
}

export function WorkArea({
  work,
  size,
  sizeKind,
  chooseBlocked,
  onChooseBlocked,
  onReload,
  onOverwriteStale,
  detail,
  busy = false,
}: WorkAreaProps) {
  return (
    <div
      data-workbench-work={work.kind}
      data-slot-size={sizeKind}
      className="steps-ft"
      style={{ ...size, padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 }}
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
              className="mono"
            />
          </Section>

          <Section title="만드는 방법">
            <div style={{ display: "flex", gap: 14 }}>
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
              className="tint-warn line"
              style={{ padding: "10px 12px", whiteSpace: "pre-wrap" }}
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
                className="ai"
                style={{ minHeight: "auto" }}
              />
            {work.composeReason !== null && (
              <span
                data-disabled-reason="ai.compose"
                className="why"
              >
                {work.composeReason}
              </span>
            )}
            {/* 001 FR-064 — 지시문은 기록이며 저장 대상이 아니다. 그 사실을 미리 말한다 */}
            <p className="why" style={{ margin: 0 }}>
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
              <p className="why mono" style={{ margin: 0 }}>
                아직 기록이 없습니다.
              </p>
            ) : (
              <ol className="mono why" style={{ margin: 0, paddingLeft: 18 }}>
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
            className={`${work.recording ? "tint-fail" : "tint-warn"} strong-sm`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              minHeight: GUIDE_BAND_HEIGHT,
              padding: "0 12px",
            }}
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
            <p className="line fail-ink" style={{ margin: 0 }}>
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
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {work.step.locator_attempts.map((a) => (
                  <div
                    key={`${a.candidate}-${a.expression}`}
                    className="row mono why"
                  >
                    <span className={a.matched ? "pass-ink" : "fail-ink"}>
                      {a.matched ? "✓" : "×"}
                    </span>
                    <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {a.expression}
                    </span>
                  </div>
                ))}
                {/*
                  004 FR-121 — **실제로 기다린 시간**이다. 예전에는 후보별 대기 중
                  최댓값을 "timeout" 이라 불렀는데, 그것은 설정값도 실측값도 아니었다.
                */}
                <div className="why mono" style={{ paddingLeft: 20 }}>
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
              className="tint-warn line"
              style={{ padding: "12px 14px" }}
            >
              {work.diagnosis}
            </div>
          )}
        </>
      )}

      {work.kind === "edit_fields" && (
        <>
          <div
            className="strong-sm"
            style={{ display: "flex", alignItems: "center", gap: 12, minHeight: GUIDE_BAND_HEIGHT }}
          >
            <span data-pending-edits>
              {work.pendingCount === 0
                ? "바꾼 것이 없습니다"
                : `저장할 변경 ${work.pendingCount}건`}
            </span>
            {work.savedName !== null && (
              <span role="status" className="strong-sm pass-ink">
                ✓ {editSavedNotice(work.savedName)}
              </span>
            )}
          </div>

          {/* FR-216 — 저장을 막지 않는 것들. 경고로만 알린다. */}
          {work.warnings.length > 0 && (
            <ul className="warn-ink line" style={{ margin: 0, paddingLeft: 18 }}>
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
              className="tint-warn"
              style={{ padding: 14 }}
            >
              <strong className="strong-sm">
                ⚠ 이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.
              </strong>
              <p className="why" style={{ margin: "6px 0 10px" }}>
                파일 밖에서 고친 내용이 있습니다. 어떻게 할지 고르세요.
              </p>
              {/* 무엇을 버리는지 라벨에 적는다 (006 FR-209 · ui-contract §7). */}
              <div className="row" style={{ gap: 8 }}>
                <button className="btn sm" onClick={onReload}>
                  {staleReloadLabel(work.pendingCount)}
                </button>
                <button className="btn sm primary" data-action="save.overwriteStale" onClick={onOverwriteStale}>
                  {STALE_OVERWRITE_LABEL}
                </button>
              </div>
            </div>
          )}
        </>
      )}
      {/*
        008 — **Step 편집면이 이 자리의 본체다.**

        `VERTICAL_SPLIT.editing` 이 이 자리에 `fill` 을 주는 근거가 「하는 일은 Step
        편집이다」였는데 정작 그 폼은 겹침에 있었다. 007 이 남긴 모순이며, 자리 배분과
        내용이 어긋난 채였다 (S-12 와 같은 형태).

        **kind 분기 밖에 둔다.** 안에 두면 그 국면의 작업 종류가 바뀌는 순간 상세가
        조용히 사라진다 — 받으면 그린다. 구현은 겹침과 같은 한 벌이다 (FR-229 · SC-001).
      */}
      {detail}
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
      className={`pane pick${selected ? " on" : ""}${ai ? " tint-ai" : ""}`}
      style={{
        flex: 1,
        minWidth: 0,
        textAlign: "left",
        height: "auto",
        padding: "16px 18px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        cursor: "pointer",
      }}
    >
      <span className="subtitle">{title}</span>
      <span className="note">{summary}</span>
      <span style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {bullets.map((b) => (
          <span key={b} className="why mono">
            {b}
          </span>
        ))}
      </span>
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div className="lbl">{title}</div>
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
  onChoose?: (choice: string) => void;
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
        className="why"
      >
        {choose.reason}
      </span>
    ) : null;
  if (error === null && blocked === null) return placeholder;
  return (
    <div data-always-visible-failure style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {error !== null && <ErrorNotice error={error} />}
      {blocked !== null && (
        <div
          role="alert"
          className="tint-fail"
          style={{ padding: "12px 14px" }}
        >
          <strong className="strong-sm fail-ink">AI 가 막혔습니다</strong>
          {blocked.attempted !== null && (
            <p className="why mono" style={{ margin: "6px 0 0" }}>
              시도: {blocked.attempted}
            </p>
          )}
          <p className="line" style={{ margin: "6px 0 10px" }}>
            {blocked.reason}
          </p>
          <div className="row" data-action="ai.chooseBlocked" style={{ gap: 8, flexWrap: "wrap" }}>
            {blocked.choices.map((c) => (
              <button key={c} className="btn sm" disabled={busy} onClick={() => onChoose?.(c)}>
                {c}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
