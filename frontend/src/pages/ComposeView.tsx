/**
 * 만들기 국면 어댑터 (007 T113·T114 · FR-217b·FR-258·FR-259·FR-260).
 *
 * **`CreateTest.tsx`(1000px 가운데 정렬)와 `AiCompose.tsx`(1440 비3층)를 대체한다.**
 * 1회차는 만들기를 「일곱 국면에 속하지 않는다」고 판정해 별도 화면 둘로 두었고, 그
 * 결과 한 번의 「테스트를 만든다」 안에서 껍데기가 두 번 바뀌었다 (spec S-14). 세션이
 * 아직 없다는 것은 화면을 갈아탈 이유가 되지 못한다 — 편집 국면도 세션이 없다.
 *
 * ## 조작을 더하지 않는다 (FR-258a)
 *
 * 항목은 두 화면에 있던 것뿐이다 — 시작 URL · 방법 2택 · 지시문 · 취소.
 * **테스트 이름과 「빈 테스트」는 만들지 않는다.** 이름은 지금도 저장 시점(일시정지
 * 국면)에 정하고, 둘 다 제품에 없는 조작이므로 범위 밖이다 (research R11).
 *
 * ## 실행 경로를 새로 만들지 않는다 (FR-248 · 005 U-01·U-06)
 *
 * 세션 생성은 `App` 이 넘겨 준 핸들러가 한다. `CreateTest`·`AiCompose` 가 이미 그
 * 경로를 쓰고 있었으므로 **경로가 늘지 않는다.** 연타 방지는 권한표의 O2(`busy`)가
 * 담당한다 — 화면이 스스로 판단하면 다른 화면이 그 판단을 빠뜨린다.
 */
import { useEffect, useState } from "react";

import { ApiError, ai, type ProjectView } from "../api/client";
import { ErrorNotice, describeError, type ErrorInfo } from "../components/ErrorNotice";
import { ActionButton } from "../components/workbench/ActionButton";
import { ActionPalette } from "../components/workbench/ActionPalette";
import { Workbench } from "../components/workbench/Workbench";
import type { ComposeMode, WorkbenchModel } from "../components/workbench/model";
import { capabilitiesFor } from "../lib/capabilities";
import { PHASE_LABEL } from "../lib/wording";

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
}

export function ComposeView({
  project,
  onCancel,
  onRecord,
  onStartAi,
  busy = false,
}: ComposeViewProps) {
  const [startUrl, setStartUrl] = useState(project?.default_start_url ?? "");
  const [mode, setMode] = useState<ComposeMode | null>(null);
  const [instruction, setInstruction] = useState("");
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [aiReady, setAiReady] = useState<{ available: boolean; reason: string | null } | null>(
    null,
  );

  /*
    001 DR-021 — 화면에 들어오는 순간 확인한다. 눌러 봐야 아는 것은 늦다.
    `CreateTest` 에 있던 것을 그대로 옮겼다.
  */
  useEffect(() => {
    void ai
      .availability()
      .then(setAiReady)
      .catch((exc: unknown) =>
        setAiReady({
          available: false,
          reason: exc instanceof ApiError ? exc.message : String(exc),
        }),
      );
  }, []);

  const urlReady = /^https?:\/\//.test(startUrl.trim());

  /*
    권한 판정은 **표가 한다** (FR-233 · ui-contract §3). 이 화면이 `disabled` 를 스스로
    계산하지 않는다 — 1회차에 `AiCompose` 가 `disabled={busy || instruction.trim() === ""}`
    를 자기 파일에서 판단했고, 그 판단이 표에 없어서 다른 화면이 같은 것을 빠뜨릴 수
    있었다. 지금은 조건 C14 가 그것을 갖는다.
  */
  const capabilities = capabilitiesFor("composing", {
    hasInstruction: instruction.trim() !== "",
    aiModeChosen: mode === "ai",
    busy,
  });

  const compose = capabilities["ai.compose"];

  const model: WorkbenchModel = {
    phase: "composing",
    // 저장된 테스트가 아직 없다. 헤더는 「테스트 / 초안」을 그린다 (FR-217)
    testId: null,
    testName: "새 테스트",
    phaseBar: {
      phaseLabel: PHASE_LABEL.composing,
      phaseTone: "neutral",
      // 만들기 국면에는 결말이 없다. 자리를 비운다 — 없는 결말을 지어내지 않는다
      runSummary: null,
      progressLabel: "Step 0개 · 아직 시작하지 않음",
    },
    /*
      ③-a 대상 앱 슬롯 — **자리는 있고 왜 비었는지 말한다** (FR-244·FR-245).
      배분은 `fixed 118` 이다 (`layout.ts` 의 `composing.targetSlot`).
    */
    target: { kind: "empty", reason: "not_started" },
    /* ③-b 국면 작업 영역 — 이 국면에서 실제로 하는 일 (FR-257·FR-258) */
    work: {
      kind: "compose_form",
      startUrl,
      mode,
      instruction,
      aiReady,
      composeReason: compose.kind === "disabled" ? compose.reason : null,
      error,
      onStartUrlChange: (next) => {
        setStartUrl(next);
        setError(null);
      },
      onModeChange: setMode,
      onInstructionChange: setInstruction,
    },
    /*
      Step 이 0개다. **목록은 사라지지 않는다** (FR-260 · S-15) — 조작이 어디에 쌓이는지
      시작하기 전에 보여야 한다. 빈 안내는 `stepEmptyNotice` 가 그린다.
    */
    steps: [],
    focusedStepId: null,
    /* 만들기 국면에는 Step 이 없다. 자리는 두고 비운다 (011 FR-380) */
    deleteSelection: [],
    detail: null,
    capabilities,
    notices: [],
    /** 고른 방법이 작성 주체다. 아직 안 골랐으면 녹화로 둔다 — 배지가 행 구조를 바꾸지 않는다 */
    authoring: mode === "ai" ? "ai" : "record",
    pacing: null,
  };

  const start = () => {
    setError(null);
    if (!urlReady) {
      setError(describeError(new Error("시작 URL 이 http:// 또는 https:// 로 시작해야 합니다.")));
      return;
    }
    if (mode === "ai") onStartAi(startUrl.trim(), instruction.trim());
    else onRecord(startUrl.trim());
  };

  /*
    국면 띠의 주 조작. **고른 방법에 따라 어느 것이 강조되는지만 바뀐다** — 자리와
    개수는 고정이다 (FR-235·FR-236). 「해당 없음」인 조작은 `ActionButton` 이 스스로
    그리지 않는다.
  */
  const phaseActions = (
    <>
      <ActionButton
        action="record.start"
        capability={capabilities["record.start"]}
        emphasis={mode !== "ai"}
        onRun={start}
      />
      <ActionButton
        action="ai.start"
        capability={capabilities["ai.start"]}
        emphasis={mode === "ai"}
        onRun={start}
      />
      <ActionButton action="nav.back" capability={capabilities["nav.back"]} onRun={onCancel} />
    </>
  );

  return (
    <>
      {/*
        시작 URL 형식 오류는 알림 자리에 온다 — 작업 영역의 `error` 는 요청 실패를
        위한 자리이므로 둘을 섞지 않는다.
      */}
      <Workbench
        model={model}
        phaseActions={phaseActions}
        stepEmptyNotice="아직 Step 이 없습니다. 시작하면 조작 하나가 행 하나로 여기 쌓입니다."
        /*
          Step 패널 바닥의 조작 블록 — **여덟 국면에서 같은 자리다** (FR-235).

          만들기 국면에서 쓸 수 있는 것은 없지만 **자리는 남긴다** (FR-234). 자리를
          감추면 사용자는 「만들기에는 그 조작이 원래 없는 것」으로 읽고, 시작한 뒤에야
          있다는 것을 알게 된다 — S-15 와 같은 종류의 결함이다.

          셋은 여기서 감춘다 — 한 조작이 두 자리를 가지면 라벨이 둘이 되고 사용자는
          둘이 다른 것인지 확인하느라 멈춘다 (FR-235).

            `test.setStartUrl` · `ai.compose`  → 작업 영역이 그 자리다
            `ai.start`                        → 국면 띠가 그 자리다

          `ai.start` 가 국면 띠에 있는 이유: 만들기 국면에서 **시작을 거는 두 조작**
          (`record.start` · `ai.start`)이 나란히 있어야 고른 방법에 따라 어느 것을
          누르는지가 한 자리에서 보인다. `record.start` 는 팔레트 목록에 없다.
        */
        stepFooter={
          <ActionPalette
            capabilities={capabilities}
            onRun={() => {
              /* 만들기 국면에서 쓸 수 있는 팔레트 조작이 없다. 표가 전부 ○ 로 둔다 */
            }}
            onRemedy={(action) => {
              if (action === "record.start") start();
            }}
            hidden={["test.setStartUrl", "ai.compose", "ai.start"]}
            nl={{ value: "", onChange: () => undefined, onSubmit: () => undefined }}
            name=""
            onNameChange={() => undefined}
            startUrl={startUrl}
            onStartUrlChange={setStartUrl}
            instruction={instruction}
            saveLabel="저장"
            stepCount={0}
            emptyHint="시작하면 Step 이 여기 쌓입니다."
          />
        }
        busy={busy}
        onSelectStep={() => {
          /* Step 이 없다. 권한표가 `step.select` 를 비활성으로 두므로 여기 오지 않는다 */
        }}
        onCloseDetail={() => {
          /* 상세가 열릴 수 없다 */
        }}
      />
      {error !== null && (
        <div style={{ position: "fixed", inset: "auto 24px 24px auto", maxWidth: 420 }}>
          <ErrorNotice error={error} />
        </div>
      )}
    </>
  );
}
