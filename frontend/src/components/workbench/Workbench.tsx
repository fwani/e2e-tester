/**
 * 통합 작업 화면의 껍데기 (007 T018 · FR-217·FR-218·FR-218c).
 *
 * **이 컴포넌트는 표시만 한다.** 데이터를 읽지 않고 명령을 만들지 않는다. 국면 어댑터
 * (`SessionScreen`·`ResultView`·`EditView`)가 `WorkbenchModel` 을 만들어 넘긴다 —
 * 소유와 표시를 나눈 것이 이 라운드의 구조적 수정이다 (research R2).
 *
 * ## 3층 구조
 *
 * 층의 구성·순서·개수는 **국면에 따라 바뀌지 않는다** (FR-218c).
 *
 *   ① 헤더 60px       — 제품 표시 · 구분선 · 경로 · 국면 알약
 *   ② 국면 띠 74px    — 국면 표시 → 테스트 이름 → 결말 요약 → 주요 조작
 *      알림            — 있을 때만
 *   ③ 본문             — 좌: 대상 앱 + 국면 보조 / 우: Step 목록 460px
 *      Step 상세       — 우측에서 겹치는 640px
 *
 * **60px 과 74px 은 007 이 새로 정한 값이 아니다.** 확정 디자인 5종
 * (`Main`·`RunnerPaused`·`Takeover`·`AiRecord`·`RunResult`)에 모두 있다. 460px 은 Step
 * 패널을 가진 3종이 공유한다 (research R1). 통합은 확정 디자인을 벗어나는 일이 아니라
 * 이미 공유되던 문법으로 나머지를 모으는 일이다.
 *
 * ## 폭
 *
 * 최소 기준 폭 1440px. 그보다 좁으면 재배치하지 않고 스크롤한다 (DC-011 유지). 넓으면
 * **좌측 대상 앱 영역만** 늘어나고 Step 패널 460px 은 고정이다 (FR-218a).
 */
import type { ReactNode } from "react";

import type { ArtifactKind, RepickSlot } from "../../api/client";
import { Artboard, BrandMark, Breadcrumb, HeaderBar, HeaderDivider } from "../design/Chrome";
import type { ActionId } from "../../lib/actions";
import type { CapabilityMap } from "../../lib/capabilities";
import { flexOf, splitFor } from "../../lib/layout";
import { NoticeStack } from "./NoticeStack";
import { PhaseBar } from "./PhaseBar";
import { StepDetail } from "./StepDetail";
import { DETAIL_PLACEMENT } from "../../lib/layout";
import { StepList } from "./StepList";
import { TargetPane } from "./TargetPane";
import { WorkArea } from "./WorkArea";
import type { WorkbenchModel } from "./model";


/** 최소 기준 폭. 확정 디자인 6종 공통값 (research R1). */
export const BASE_WIDTH = 1440;

export interface WorkbenchProps {
  model: WorkbenchModel;

  /** 국면 띠 오른쪽의 주요 조작. 어댑터가 `ActionButton` 으로 만들어 넘긴다 */
  phaseActions: ReactNode;
  /**
   * 알림 자리에 함께 오는 것 (실시간 통로 끊김 배너 등).
   *
   * `Notice` 로 표현할 수 없는 알림 — 조작 식별자를 갖지 않는 자체 버튼이 있는 것 —
   * 을 위한 자리다. **자리는 같다** — 알림이 국면마다 다른 곳에 나타나면 사용자는
   * 그것을 찾아야 한다 (T020 의 이유와 같다).
   */
  noticesExtra?: ReactNode;
  /** 헤더 오른쪽의 이동 조작 */
  headerActions?: ReactNode;
  /** Step 행 안의 편집 조작 */
  rowActions?: WorkbenchStepActions;
  /** Step 패널 헤더 오른쪽에 얹는 것 */
  stepHeaderExtra?: ReactNode;
  /** Step 이 0개일 때의 안내. 국면마다 다르다 */
  stepEmptyNotice?: ReactNode;
  /** Step 패널 바닥의 조작 블록. **일곱 국면에서 같은 자리다** (FR-235) */
  stepFooter?: ReactNode;
  /**
   * Step 상세 안, 항목 순서 사이에 국면이 얹는 것 (FR-231).
   *
   * 편집 국면의 `tab`·`url`·`기대값` 처럼 **그 국면에만 있는 필드**의 자리다. 자리를
   * 따로 만들지 않고 상세의 항목 순서 안에 두는 이유는, 국면에 따라 같은 자리가 다른
   * 뜻을 갖지 않게 하는 것이다.
   */
  stepDetailExtra?: ReactNode;
  /**
   * Step 상세가 자기 편집 입력(표시 이름·입력값·대기 시간)을 갖는가 (008).
   *
   * 편집 국면은 `false` 다 — 그 국면은 `stepDetailExtra` 로 **입력할 때마다 변경 연산을
   * 쌓는** 편집면을 넣기 때문에, 둘을 함께 그리면 같은 값에 입력칸이 둘 생기고 커밋
   * 방식이 다른 둘이 한 화면에 놓인다 (006 FR-188~FR-190).
   */
  stepDetailOwnFields?: boolean;

  onSelectStep: (stepId: string) => void;
  onCloseDetail: () => void;
  onSaveStep?: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    sensitive?: boolean;
  }) => void;
  onRepick?: (slot: RepickSlot) => void;
  onSelectArtifact?: (kind: ArtifactKind) => void;
  onOpenBrowser?: () => void;
  onChooseBlocked?: (choice: string) => void;
  onReloadDefinition?: () => void;
  onOverwriteStale?: () => void;
  onDismissNotice?: (id: string) => void;
  /** 비활성 조작의 해소 방법을 눌렀을 때. 그 조작을 실제로 실행한다 */
  onAction?: (action: ActionId) => void;
  busy?: boolean;
}

type WorkbenchStepActions = NonNullable<
  Parameters<typeof StepList>[0]["rowActions"]
>;

export function Workbench({
  model,
  phaseActions,
  noticesExtra,
  headerActions,
  rowActions,
  stepHeaderExtra,
  stepEmptyNotice,
  stepFooter,
  stepDetailExtra,
  stepDetailOwnFields = true,
  onSelectStep,
  onCloseDetail,
  onSaveStep,
  onRepick,
  onSelectArtifact,
  onOpenBrowser,
  onChooseBlocked,
  onReloadDefinition,
  onOverwriteStale,
  onDismissNotice,
  onAction,
  busy = false,
}: WorkbenchProps) {
  const capabilities: CapabilityMap = model.capabilities;

  /**
   * 세로 배분 — **국면으로 한 번 조회한다** (FR-256 · `lib/layout.ts`).
   *
   * 표시 컴포넌트가 배분표를 직접 읽지 않는다. 읽게 하면 각자 해석하게 되고, 그것이
   * 1회차에 두 파일이 각자 하드코딩한 것과 같은 상태다 (spec S-12).
   */
  const split = splitFor(model.phase);
  const targetStyle = flexOf(split.targetSlot);
  const workStyle = flexOf(split.workArea);

  /*
    Step 상세 — **한 번만 만든다.** 겹침이든 인라인이든 같은 원소를 쓴다. 자리마다 따로
    만들면 그 순간 구현이 둘이 되고, 그것이 007 이 고친 S-05 의 원인이다 (FR-229).
  */
  const placement = DETAIL_PLACEMENT[model.phase];
  const detailNode =
    model.detail === null ? null : (
      <StepDetail
        detail={model.detail}
        capabilities={capabilities}
        placement={placement}
        ownFields={stepDetailOwnFields}
        busy={busy}
        onSave={onSaveStep ?? (() => undefined)}
        onRepick={onRepick ?? (() => undefined)}
        onClose={onCloseDetail}
        onRemedy={onAction}
        extraFields={stepDetailExtra}
      />
    );

  return (
    <Artboard width={BASE_WIDTH} minHeight={900} grow>
      {/* ─── 층① 헤더 60px ────────────────────────────────────────────────── */}
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        {/*
          경로. 저장되지 않은 작성 세션은 테스트 식별자가 없다 — 그때도 자리를 비우지
          않고 「초안」을 쓴다. 자리가 사라지면 헤더 구성이 국면에 따라 달라진다
          (FR-217).
        */}
        {model.testId !== null ? (
          <Breadcrumb testId={model.testId} />
        ) : (
          <div className="row muted" style={{ gap: "8px" }}>
            <span className="lbl">테스트</span>
            <span className="pill mono">초안</span>
          </div>
        )}
        <div className="spacer" />
        {headerActions}
      </HeaderBar>

      {/* ─── 층② 국면 띠 74px ─────────────────────────────────────────────── */}
      <PhaseBar bar={model.phaseBar} testName={model.testName} actions={phaseActions} />

      {/* 알림 — 국면 띠 바로 아래 한 자리 */}
      {noticesExtra}
      <NoticeStack notices={model.notices} onAct={onAction} onDismiss={onDismissNotice} />

      {/* ─── 층③ 본문 ──────────────────────────────────────────────────────── */}
      {/*
        `position: relative` 는 Step 상세 겹침 패널의 기준이다. `Artboard` 를 고치지
        않고 여기서 기준을 잡는다 — `Artboard` 는 확정 디자인 8종이 공유하는 껍데기이므로
        007 이 그 안쪽 배치를 바꾸지 않는다.
      */}
      <div style={{ flex: "1", minHeight: "0", display: "flex", position: "relative" }}>
        {/*
          좌 — ③-a 대상 앱 슬롯 + ③-b 국면 작업 영역. 남는 **폭**을 가져간다 (FR-218a).
          두 자리의 **순서와 개수**는 국면에 따라 바뀌지 않고 (FR-218c), 세로 비율만
          국면이 정한다 (FR-256).
        */}
        <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column" }}>
          <TargetPane
            target={model.target}
            size={targetStyle}
            sizeKind={split.targetSlot.kind}
            capabilities={capabilities}
            onSelectArtifact={onSelectArtifact}
            onOpenBrowser={onOpenBrowser}
            onRemedy={onAction}
          />
          {/*
            국면 작업 영역이 없으면 **자리를 차지하지 않는다.** 그것 때문에 다른 영역의
            자리가 바뀌어서는 안 된다 (FR-218e) — 배분표가 그 국면에서 ③-a 를 `fill` 로
            정하므로 아래가 없어지면 위가 그만큼 늘어난다. 영역의 순서·개수는 그대로다.
          */}
          {/*
            008 — `work` 가 없는데 상세를 인라인으로 걸어야 하는 경우에도 ③-b 는 있다.
            자리의 **개수와 순서**는 국면에 따라 바뀌지 않는다 (FR-218c) — 담는 것만
            바뀐다. 이 분기가 없으면 그 국면에서 층이 하나 사라진다.
          */}
          {model.work === null && placement === "inline" && detailNode !== null && (
            <div
              data-workbench-work="step_detail"
              data-slot-size={split.workArea.kind}
              className="steps-ft"
              style={{
                ...workStyle,
                padding: "12px 16px",
                display: "flex",
                flexDirection: "column",
                minHeight: 0,
              }}
            >
              {detailNode}
            </div>
          )}
          {model.work !== null && (
            <WorkArea
              work={model.work}
              size={workStyle}
              sizeKind={split.workArea.kind}
              chooseBlocked={capabilities["ai.chooseBlocked"]}
              onChooseBlocked={onChooseBlocked}
              onReload={onReloadDefinition}
              onOverwriteStale={onOverwriteStale}
              detail={placement === "inline" ? detailNode : undefined}
              busy={busy}
            />
          )}
        </div>

        {/* 우 — Step 목록 460px 고정 */}
        <StepList
          steps={model.steps}
          authoring={model.authoring}
          focusedStepId={model.focusedStepId}
          onSelect={onSelectStep}
          rowActions={rowActions}
          headerExtra={stepHeaderExtra}
          emptyNotice={stepEmptyNotice}
          footer={stepFooter}
        />

        {/*
          Step 상세 — **구현은 한 벌이고 거는 자리만 국면이 정한다** (008 ·
          `DETAIL_PLACEMENT`). 겹침이면 여기, 인라인이면 위의 ③-b 안이다.

          007 이 자리를 하나로 고정한 이유(S-05)는 **두 구현이 갈라진 것**이었다. 구현이
          하나로 남는 한 그 원인은 재발하지 않는다 — 그래서 자리만 표로 뺐다.
        */}
        {model.detail !== null && placement === "overlay" && (
          <div
            className="scrim"
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              justifyContent: "flex-end",
              zIndex: 20,
              /*
                DC-011 — 창이 확정 디자인의 기준 폭(640px)보다 좁으면 **기준 폭을 유지한
                채 스크롤한다.** 겹침이 절대 배치라 페이지 스크롤이 닿지 않으므로 가로
                스크롤을 여기서 준다. 없으면 좁은 창에서 판이 잘린 채 접근할 수 없다.
              */
              overflowX: "auto",
              overflowY: "auto",
            }}
          >
            {detailNode}
          </div>
        )}
      </div>
    </Artboard>
  );
}
