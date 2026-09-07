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
import { NoticeStack } from "./NoticeStack";
import { PhaseAside } from "./PhaseAside";
import { PhaseBar } from "./PhaseBar";
import { StepDetail } from "./StepDetail";
import { StepList } from "./StepList";
import { TargetPane } from "./TargetPane";
import type { WorkbenchModel } from "./model";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

/** 최소 기준 폭. 확정 디자인 6종 공통값 (research R1). */
export const BASE_WIDTH = 1440;

export interface WorkbenchProps {
  model: WorkbenchModel;

  /** 국면 띠 오른쪽의 주요 조작. 어댑터가 `ActionButton` 으로 만들어 넘긴다 */
  phaseActions: ReactNode;
  /** 헤더 오른쪽의 이동 조작 */
  headerActions?: ReactNode;
  /** Step 행 안의 편집 조작 */
  rowActions?: WorkbenchStepActions;
  /** Step 패널 헤더 오른쪽에 얹는 것 */
  stepHeaderExtra?: ReactNode;
  /** Step 이 0개일 때의 안내. 국면마다 다르다 */
  stepEmptyNotice?: ReactNode;

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
  headerActions,
  rowActions,
  stepHeaderExtra,
  stepEmptyNotice,
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
          <div style={{ font: `500 14px/1 ${MONO}`, color: "#6B675C" }}>테스트 / 초안</div>
        )}
        <div style={{ flex: "1" }} />
        {headerActions}
      </HeaderBar>

      {/* ─── 층② 국면 띠 74px ─────────────────────────────────────────────── */}
      <PhaseBar bar={model.phaseBar} testName={model.testName} actions={phaseActions} />

      {/* 알림 — 국면 띠 바로 아래 한 자리 */}
      <NoticeStack notices={model.notices} onAct={onAction} onDismiss={onDismissNotice} />

      {/* ─── 층③ 본문 ──────────────────────────────────────────────────────── */}
      {/*
        `position: relative` 는 Step 상세 겹침 패널의 기준이다. `Artboard` 를 고치지
        않고 여기서 기준을 잡는다 — `Artboard` 는 확정 디자인 8종이 공유하는 껍데기이므로
        007 이 그 안쪽 배치를 바꾸지 않는다.
      */}
      <div style={{ flex: "1", minHeight: "0", display: "flex", position: "relative" }}>
        {/* 좌 — 대상 앱 영역 + 국면 보조 영역. 남는 폭을 가져간다 (FR-218a) */}
        <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column" }}>
          <TargetPane
            target={model.target}
            capabilities={capabilities}
            onSelectArtifact={onSelectArtifact}
            onOpenBrowser={onOpenBrowser}
            onRemedy={onAction}
          />
          {/*
            국면 보조 영역이 없으면 **자리를 차지하지 않는다.** 그것 때문에 다른 영역의
            자리가 바뀌어서는 안 된다 (FR-218e) — 위의 `TargetPane` 이 `flex: 1` 이므로
            아래가 없어지면 위가 그만큼 늘어난다. 영역의 순서·개수는 그대로다.
          */}
          {model.aside !== null && (
            <PhaseAside
              aside={model.aside}
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
        />

        {/*
          Step 상세 — 우측에서 겹치는 640px. **모든 국면에서 같은 자리다** (FR-230).
          이전에는 세션 화면이 겹침으로, 편집 화면이 목록 아래 인라인으로 열었다 (S-05).
        */}
        {model.detail !== null && (
          <div
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              justifyContent: "flex-end",
              background: "rgba(20,19,15,0.28)",
              zIndex: 20,
            }}
          >
            <StepDetail
              detail={model.detail}
              capabilities={capabilities}
              busy={busy}
              onSave={onSaveStep ?? (() => undefined)}
              onRepick={onRepick ?? (() => undefined)}
              onClose={onCloseDetail}
              onRemedy={onAction}
            />
          </div>
        )}
      </div>
    </Artboard>
  );
}
