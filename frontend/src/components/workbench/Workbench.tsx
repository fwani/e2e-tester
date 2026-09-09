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
import { PhaseBar, type PhaseNameEdit } from "./PhaseBar";
import { StepDetail } from "./StepDetail";
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
   * 국면 띠의 테스트 이름을 **그 자리에서** 고친다 (011 UC-011-2).
   *
   * `phaseActions` 와 같은 규율이다 — 국면 어댑터가 만들어 넘기고 이 컴포넌트는 자리만
   * 준다. 주지 않으면 이름은 읽기 전용 표시로 남는다.
   */
  phaseName?: PhaseNameEdit;
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
  phaseName,
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
    Step 상세 — **구현도 하나, 자리도 하나다** (FR-229·FR-230).

    008 은 자리를 국면별 표(`DETAIL_PLACEMENT`)로 뺐고 편집 국면만 ③-b 인라인이었다.
    사용자가 그 배치를 문제로 보고했다 (2026-09-09 — 「한쪽에 뜨도록 해야함」). 자리는
    우측 겹침 하나로 돌아왔고 표는 없어졌다 (`lib/layout.ts` 의 그 자리 주석).
  */
  const detailNode =
    model.detail === null ? null : (
      <StepDetail
        detail={model.detail}
        capabilities={capabilities}
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
    /*
      `fill` — **화면 전체 높이를 창에 맞추고 Step 목록이 스크롤한다.**

      이전에는 `minHeight` 만 있어 Step 이 쌓일수록 아트보드가 길어졌다. 목록에는 이미
      `overflowY: auto` 가 있었지만 부모가 무한히 늘어나므로 스크롤할 것이 남지 않았고,
      그 결과 헤더·국면 띠·미러가 위로 밀려 올라갔다 — 사용자가 Step 을 볼수록 지금
      무엇이 일어나는지를 보지 못하게 된다.

      창이 기준 높이(900)보다 작으면 `minHeight` 가 이겨 종전처럼 페이지가 스크롤한다.
    */
    <Artboard width={BASE_WIDTH} minHeight={900} grow fill>
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
      <PhaseBar
        bar={model.phaseBar}
        testName={model.testName}
        rename={phaseName}
        actions={phaseActions}
      />

      {/* ─── 층③ 본문 ──────────────────────────────────────────────────────── */}
      {/*
        `position: relative` 는 Step 상세 겹침 패널의 기준이다. `Artboard` 를 고치지
        않고 여기서 기준을 잡는다 — `Artboard` 는 확정 디자인 8종이 공유하는 껍데기이므로
        007 이 그 안쪽 배치를 바꾸지 않는다.
      */}
      <div style={{ flex: "1", minHeight: "0", display: "flex", position: "relative" }}>
        {/*
          알림 — **한 자리이고, 화면을 밀어내지 않는다** (2026-09-09 사용자 보고).

          ## 무엇이 문제였나

          이전에는 국면 띠 바로 아래 **문서 흐름 안에** 있었다. 자리를 하나로 모은 것은
          007 T020 의 옳은 결정이었지만, 흐름 안에 있으면 알림이 뜰 때마다 아래 전부가
          그만큼 내려간다. 사용자가 보고한 것: 「알림으로 인해 아래 화면들이 내려가는데,
          화면이 내려가서 문제」. 미러가 줄고, 보고 있던 Step 행의 자리가 바뀐다.

          ## 왜 사라지는 토스트가 아닌가

          사용자는 「토스트로 만들어야함」이라고 적었고, 요구의 실체는 **화면을 밀지 말라**
          는 것이다. 그러나 이 저장소는 알림을 사라지게 두지 않는다 — 005 FR-154·FR-158
          (U-09)이 「토스트로 끝내지 않는 이유는 사라지면 근거가 남지 않기 때문이다」로
          정했고, 실패 사유·세션 유실·저장 안내는 사용자가 다시 읽어야 하는 것들이다.

          그래서 **띄우기만 한다**: 겹쳐 뜨고, 스스로 사라지지 않는다. 지울 수 있는 것은
          지금처럼 「닫기」로 지운다.

          ## 자리

          좌측 영역 **아래쪽**이다. 위쪽에 두면 미러의 머리(대상 앱의 주소·상단 바)를
          가리는데, 녹화 중 사용자가 보는 곳이 정확히 거기다. 폭은 560px 로 묶어 미러를
          통째로 덮지 않고, 넘치면 이 묶음 안에서 스크롤한다 — 알림이 많다고 화면이
          늘어나지 않는다.
        */}
        <div
          data-workbench-notice-layer
          style={{
            position: "absolute",
            left: 16,
            bottom: 16,
            width: "min(560px, calc(100% - 492px))",
            maxHeight: "60%",
            overflowY: "auto",
            zIndex: 12,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            /*
              **비어 있을 때 아래를 막지 않는다.** 이 층은 알림이 없어도 자리를 잡고
              있으므로, 포인터를 통과시키지 않으면 미러의 그 띠가 조용히 클릭을 먹는다 —
              010 SC-516 이 0건으로 두려는 조용한 실패와 같은 형태다. 알림 자체는 아래
              `auto` 로 되돌려 버튼을 누를 수 있게 한다.
            */
            pointerEvents: "none",
          }}
        >
          <div style={{ pointerEvents: "auto" }}>{noticesExtra}</div>
          <div style={{ pointerEvents: "auto" }}>
            <NoticeStack notices={model.notices} onAct={onAction} onDismiss={onDismissNotice} />
          </div>
        </div>

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
          {model.work !== null && (
            <WorkArea
              work={model.work}
              size={workStyle}
              sizeKind={split.workArea.kind}
              chooseBlocked={capabilities["ai.chooseBlocked"]}
              onChooseBlocked={onChooseBlocked}
              onReload={onReloadDefinition}
              onOverwriteStale={onOverwriteStale}
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
          Step 상세 — **모든 국면에서 이 자리다** (FR-230 · 2026-09-09 사용자 보고).

          007 이 자리를 하나로 고정한 이유는 S-05 였고, 그 실제 원인은 구현이 둘이라
          갈라진 것이었다. 008 은 그 사실에 근거해 자리를 국면별 표로 뺐지만, 사용자가
          필요로 한 것은 **자리도 하나**라는 성질이었다 — 같은 것을 보는 곳이 두 군데면
          매번 어디를 볼지 판단해야 한다.
        */}
        {model.detail !== null && (
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
