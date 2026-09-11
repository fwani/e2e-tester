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
import { flexClassOf, splitFor } from "../../lib/layout";
import { NoticeStack } from "./NoticeStack";
import { PhaseBar, type PhaseGroupPick, type PhaseNameEdit } from "./PhaseBar";
import { StepDetail } from "./StepDetail";
import { StepList } from "./StepList";
import { TargetPane } from "./TargetPane";
import { WorkArea } from "./WorkArea";
import type { WorkbenchModel } from "./model";

import { Lbl } from "../../ui/Field";
import { Scrim } from "../../ui/Surface";
import { Row } from "../../ui/Table";
import { Pill } from "../../ui/Chip";


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
  /** 저장할 그룹 (013 FR-443). 국면 어댑터가 만든다 */
  phaseGroup?: PhaseGroupPick;
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
  /**
   * 좌측 열 **아래**에 얹는 것 (016).
   *
   * 016 의 대화 패널이 여기 산다. 배치 계약(007 FR-218·008)을 건드리지 않기 위해
   * 새 영역을 만드는 대신 확장 자리를 하나 더 뒀다 — 영역의 **순서와 개수**가 국면에
   * 따라 바뀌지 않는다는 성질(FR-218c)이 그대로여야 한다.
   *
   * `noticesExtra`·`stepHeaderExtra` 와 같은 종류의 자리이며, 없으면 **아무 자리도
   * 차지하지 않는다.**
   */
  leftExtra?: ReactNode;
  /** Step 이 0개일 때의 안내. 국면마다 다르다 */
  stepEmptyNotice?: ReactNode;
  /**
   * 삭제 대상 고르기 (011). `StepList` 로 그대로 내려간다.
   *
   * `rowActions`·`phaseName` 과 같은 규율이다 — 국면 어댑터가 만들고 이 컴포넌트는
   * 자리만 준다. 주지 않으면 체크 칸을 그리지 않는다 (UC-011-14).
   */
  deleteTargets?: Parameters<typeof StepList>[0]["deleteTargets"];
  /** 016 — 교체 대상인 Step id 들 (FR-024). `StepList` 로 그대로 내려간다 */
  rerecordTargets?: Parameters<typeof StepList>[0]["rerecordTargets"];
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
  onChooseBlocked?: (choice: string, answer?: string) => void;
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
  phaseGroup,
  noticesExtra,
  headerActions,
  rowActions,
  stepHeaderExtra,
  leftExtra,
  stepEmptyNotice,
  deleteTargets,
  rerecordTargets,
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
  const targetClass = flexClassOf(split.targetSlot);
  const workClass = flexClassOf(split.workArea);

  /*
    Step 상세 — **구현도 하나, 자리도 하나다** (FR-229·FR-230).

    008 은 자리를 국면별 표(`DETAIL_PLACEMENT`)로 뺐고 편집 국면만 ③-b 인라인이었다.
    사용자가 그 배치를 문제로 보고했다 (2026-09-09 — 「한쪽에 뜨도록 해야함」). 자리는
    우측 겹침 하나로 돌아왔고 표는 없어졌다 (`lib/layout.ts` 의 그 자리 주석).
  */
  /**
   * 지목한 Step 의 화면 (011). 모델의 Step 목록에서 지목한 것을 찾아 꺼낸다.
   *
   * **`WorkbenchStep` 에서 읽는다** — 상세 모델(`StepDetail`)에 넣지 않은 이유는 그것이
   * 「정의와 그때 시도한 것」의 모음이고, 화면은 **행의 사실**이기 때문이다. 결과 목록의
   * 행이 이미 그 값을 들고 있다.
   */
  const focusedStep = model.steps.find((s) => s.id === model.focusedStepId);
  const detailShot =
    focusedStep === undefined || focusedStep.screenshotUrl === undefined
      ? undefined
      : {
          url: focusedStep.screenshotUrl,
          note: focusedStep.screenshotNote ?? "이 Step 의 화면이 남아 있지 않습니다.",
        };

  const detailNode =
    model.detail === null ? null : (
      <StepDetail
        detail={model.detail}
        capabilities={capabilities}
        /*
          011 UC-011-20 — 지목한 Step 의 화면. **모델에서 온다** — 이 컴포넌트는 데이터를
          읽지 않는다 (007 의 소유와 표시 분리). 결과 국면 어댑터만 값을 채운다.
        */
        shot={detailShot}
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
        {/* 정본 `.row.muted` — `.muted` 는 `--ink-2` 다 (`--ink-3` 는 `.dim`). */}
        {model.testId !== null ? (
          <Breadcrumb testId={model.testId} />
        ) : (
          <Row layout="text-ink-2">
            <Lbl>테스트</Lbl>
            {/* 정본 `.pill mono` — `.pill` 이 `.mono` 보다 뒤에 정의돼 **글꼴은 sans 였다.** */}
            <Pill>초안</Pill>
          </Row>
        )}
        <div className="flex-1" />
        {headerActions}
      </HeaderBar>

      {/* ─── 층② 국면 띠 74px ─────────────────────────────────────────────── */}
      <PhaseBar
        bar={model.phaseBar}
        testName={model.testName}
        rename={phaseName}
        group={phaseGroup}
        actions={phaseActions}
      />

      {/* ─── 층③ 본문 ──────────────────────────────────────────────────────── */}
      {/*
        `position: relative` 는 Step 상세 겹침 패널의 기준이다. `Artboard` 를 고치지
        않고 여기서 기준을 잡는다 — `Artboard` 는 확정 디자인 8종이 공유하는 껍데기이므로
        007 이 그 안쪽 배치를 바꾸지 않는다.
      */}
      <div className="flex-1 min-h-0 flex relative">
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

          ## 자리 — **오른쪽 위** (2026-09-10 사용자 결정)

          「토스트 알림의 위치를 오른쪽 위로 정의한다 (mac 의 알림과 같은 개념)」.

          2026-09-09 에는 좌측 영역 **아래쪽**이었다. 근거는 「위쪽에 두면 미러의 머리를
          가린다」였는데, 그 자리는 미러가 있는 국면에서만 뜻이 있었다 — 결과·편집
          국면에서는 본문 위 아무 데나였다. 자리를 뷰포트에 고정하면 그 차이가 사라지고,
          「알림은 늘 같은 데서 뜬다」가 국면을 넘어 성립한다 (FR-235 와 같은 성질).

          형태는 정본이 갖는다 (`tokens.css` 의 `.toast-layer`).
        */}
        <div data-workbench-notice-layer className="fixed right-s4 z-[60] top-[calc(var(--h-header)+8px)] w-[min(420px,calc(100vw-32px))] max-h-[calc(100vh-var(--h-header)-24px)] overflow-y-auto flex flex-col gap-s2 pointer-events-none [&>*]:pointer-events-auto">
          {noticesExtra}
          <NoticeStack notices={model.notices} onAct={onAction} onDismiss={onDismissNotice} />
        </div>

        {/*
          좌 — ③-a 대상 앱 슬롯 + ③-b 국면 작업 영역. 남는 **폭**을 가져간다 (FR-218a).
          두 자리의 **순서와 개수**는 국면에 따라 바뀌지 않고 (FR-218c), 세로 비율만
          국면이 정한다 (FR-256).
        */}
        {/*
          좌 — 대상 앱 + 국면 작업 영역. **남는 폭 전부** (FR-218a).

          `data-workbench-left-column` 은 011 이 더한 표식이다. Step 상세가 이 영역 **위로**
          겹치므로(밀어내지 않으므로), 「상세를 열고 닫아도 이 열의 폭 선언이 같은가」를
          검사가 셀 수 있어야 한다 (UC-011-8).
        */}
        <div data-workbench-left-column className="flex-1 min-w-0 flex flex-col">
          <TargetPane
            target={model.target}
            sizeClass={targetClass}
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
              sizeClass={workClass}
              sizeKind={split.workArea.kind}
              chooseBlocked={capabilities["ai.chooseBlocked"]}
              onChooseBlocked={onChooseBlocked}
              onReload={onReloadDefinition}
              onOverwriteStale={onOverwriteStale}
              busy={busy}
            />
          )}
          {/*
            016 — 대화 패널. 없으면 자리를 차지하지 않는다 (`WorkArea` 와 같은 규칙).
            대상 앱과 작업 영역 **아래**인 이유: 대화는 화면을 보면서 하는 일이고,
            화면을 밀어내면 그 전제가 깨진다.
          */}
          {leftExtra}
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
          deleteTargets={deleteTargets}
          rerecordTargets={rerecordTargets}
          footer={stepFooter}
        />

        {/*
          Step 상세 — **모든 국면에서 이 자리다** (FR-230 · 2026-09-09 사용자 보고).

          007 이 자리를 하나로 고정한 이유는 S-05 였고, 그 실제 원인은 구현이 둘이라
          갈라진 것이었다. 008 은 그 사실에 근거해 자리를 국면별 표로 뺐지만, 사용자가
          필요로 한 것은 **자리도 하나**라는 성질이었다 — 같은 것을 보는 곳이 두 군데면
          매번 어디를 볼지 판단해야 한다.

          ## 2026-09-10 (011) — 오른쪽에서 왼쪽으로

          사용자 보고: 「STEP 상세 는 오버레이로 오른쪽으로 뜨고있는데 스텝리스트 왼쪽으로
          수정한다」. `right: 0` 이면 상세가 **Step 목록을 덮는다** — 방금 고른 행을 보면서
          상세를 읽을 수 없고, 무엇을 골랐는지 확인하려면 닫아야 했다.

          `right-steps`(= `--w-steps` = `STEP_PANEL_WIDTH`) 로 목록 왼쪽 가장자리에 붙인다. 1440px 기준으로 상세
          640px 왼쪽에 대상 앱 340px 가 남는다.

          **겹침은 유지한다** (clarify 결정 1). 대상 앱을 밀어 나란히 놓으면 최소 기준
          폭에서 미러가 **상시로** 좁아지는데, 상세가 닫혀 있는 시간이 열려 있는 시간보다
          길다. 볼 때만 가리는 쪽이 총비용이 작다.

          **`left: 0` 이 필요하다** (UC-011-9). 없으면 절대 배치 상자가 내용 폭으로 줄어들고,
          판 옆의 빈 자리에서 클릭이 그 아래 미러에 닿는다 — 010 이 미러 조작을 만들었으므로
          사용자가 보이지 않는 곳을 실제로 조작하게 된다. 층이 그 영역을 덮어 삼킨다.
        */}
        {model.detail !== null && (
          <Scrim
            data-workbench-detail-layer
            strength="soft"
            /*
              `right-steps` 는 Step 패널 폭(`--w-steps` = 460px)이다 — 상세가 목록을
              덮지 않는다는 계약이 이 한 값에 걸려 있다.

              DC-011 — 창이 확정 디자인의 기준 폭(640px)보다 좁으면 **기준 폭을 유지한
              채 스크롤한다.** 겹침이 절대 배치라 페이지 스크롤이 닿지 않으므로 가로
              스크롤을 여기서 준다. 없으면 좁은 창에서 판이 잘린 채 접근할 수 없다.
            */
            layout="absolute top-0 left-0 right-steps bottom-0 flex justify-end z-20 overflow-x-auto overflow-y-auto"
          >
            {detailNode}
          </Scrim>
        )}
      </div>
    </Artboard>
  );
}
