/**
 * 층③-a 대상 앱 슬롯 (007 T023·T102 · FR-244·FR-245·FR-246·FR-256·FR-261).
 *
 * **자리는 고정, 내용만 국면이 정한다.** 살아 있는 세션은 실시간 미러, 끝난 실행은 그
 * 실행의 산출물, 세션이 없는 편집은 브라우저를 여는 조작이 **같은 자리**를 쓴다.
 *
 * 지금은 그렇지 않다. 결과 화면에는 대상 앱 영역이 아예 없고 산출물이 본문 오른쪽 별도
 * 영역(`flex: 0 0 640px`)에 있어 다른 국면의 미러 자리와 대응하지 않는다 (S-11).
 *
 * **비어 있을 때 이유를 밝힌다** (FR-245). "아직 시작하지 않음" 과 "수집하지 않음" 과
 * "세션 유실" 은 사용자에게 **서로 다른 다음 행동**을 요구한다. 결과 화면의 빈 산출물
 * 탭이 큰 빈 상자에 "(기록 없음)" 한 줄이었던 것이 005 U-22 였다.
 *
 * 인라인 style 값은 `docs/design/Main.dc.html`(좌측 `padding: 20px`)과
 * `RunResult.dc.html`(산출물 영역)에서 그대로 옮겼다 (DC-001).
 *
 * ## 이 파일은 자기 높이를 모른다 (2회차 · FR-256)
 *
 * 1회차에는 여기서 `flex: "1"` 을 하드코딩했다. 그것과 `PhaseAside` 의 `flex: 0 0 auto`
 * 가 합쳐져 **편집 국면에서 채울 것이 없는 이 자리가 700px 를 가져갔다** (spec S-12) —
 * 「브라우저가 열려 있지 않습니다」 두 줄과 버튼 하나를 위해서였다.
 *
 * 높이는 이제 `size` 인자로만 온다. `Workbench` 가 `lib/layout.ts` 의 배분표를 국면으로
 * 조회해 내려 주며, 편집·만들기 국면에서는 118px 이다 (B1). **자리를 없애는 것이 아니라
 * 줄이는 것이다** (FR-261) — 브라우저를 여는 조작은 이 자리 안에 그대로 있다.
 */
import type { ArtifactKind } from "../../api/client";
import { isShown, type CapabilityMap } from "../../lib/capabilities";
import type { SlotSize } from "../../lib/layout";
import { ACTION_LABEL, openBrowserAtStepLabel } from "../../lib/wording";
import { ActionButton } from "./ActionButton";
import type { EmptyReason, TargetView } from "./model";
/** 확정 디자인의 산출물 탭. 순서와 문구를 그대로 옮겼다 (`RunResult.dc.html`). */
const ARTIFACT_TABS: { kind: ArtifactKind; label: string }[] = [
  { kind: "screenshot", label: "SCREENSHOT" },
  { kind: "console", label: "CONSOLE" },
  { kind: "network", label: "NETWORK" },
  { kind: "trace", label: "TRACE" },
];
/**
 * 왜 비었는지 (FR-245 · 005 FR-173).
 *
 * 문구가 `wording.ts` 가 아니라 여기 있는 이유: 이 넷은 **이 영역만의 상태**이고 다른
 * 화면이 쓰지 않는다. 여러 화면이 함께 묻는 질문만 사전으로 올린다.
 */
const EMPTY_MESSAGE: Record<EmptyReason, string> = {
  not_started:
    "아직 브라우저를 열지 않았습니다.\n\n실행을 걸면 대상 앱이 여기 보입니다.",
  not_collected:
    "이 실행에서는 수집되지 않았습니다.\n\n수집하지 않은 것이며 수집했는데 빈 것과 다릅니다.",
  session_lost:
    "브라우저 세션이 유실됐습니다.\n\n이어서 실행할 수 없으니 처음부터 다시 실행해야 합니다.",
  not_supported: "이 종류는 아직 지원되지 않습니다.",
};

export interface TargetPaneProps {
  target: TargetView;
  /**
   * 이 자리의 크기. **국면이 정하고 `Workbench` 가 내려 준다** (FR-256).
   *
   * 이미 CSS 값으로 환산되어 있다 — 이 파일은 118px 이 어디서 왔는지 알 필요가 없다.
   */
  /**
   * 이 자리의 배분 — **클래스로 온다** (015 T029).
   *
   * 이미 CSS 로 환산되어 있다. 이 파일은 88px 이 어디서 왔는지 알 필요가 없다.
   */
  sizeClass: string;
  /** 어느 배분인지. 검사와 대조 기록이 읽는 표식일 뿐 분기에 쓰지 않는다 */
  sizeKind: SlotSize["kind"];
  capabilities: CapabilityMap;
  onSelectArtifact?: (kind: ArtifactKind) => void;
  onOpenBrowser?: () => void;
  onRemedy?: (action: keyof CapabilityMap) => void;
}
/**
 * 조작이 이 국면에 있지만 지금은 쓸 수 없을 때, **그 자리에** 이유를 남긴다 (FR-234).
 *
 * 자리를 비우면 "이 화면에는 원래 없는 것" 과 구별되지 않는다.
 */
function Unavailable({
  action,
  capabilities,
}: {
  action: keyof CapabilityMap;
  capabilities: CapabilityMap;
}) {
  const state = capabilities[action];
  if (state.kind !== "disabled") return null;
  // 「이 상태의 조작이 아니다」는 사유도 그리지 않는다 (2026-09-09 · `capabilities.ts`).
  if (state.visibility === "hide") return null;
  return (
    <span
      data-disabled-reason={action}
      className="font-sans text-[11px] leading-[1.4] text-ink-3"
    >
      {state.reason}
    </span>
  );
}

export function TargetPane({
  target,
  sizeClass,
  sizeKind,
  capabilities,
  onSelectArtifact,
  onOpenBrowser,
  onRemedy,
}: TargetPaneProps) {
  return (
    <div
      data-workbench-target
      data-slot-size={sizeKind}
      className={`${sizeClass} min-w-0 p-s5 flex flex-col gap-[14px]`}
    >
      {target.kind === "mirror" && (
        <>
          {/*
            탭 고르기의 **자리** (`tab.select`). 목록을 아직 받지 못했어도 자리는 남고,
            왜 고를 수 없는지 그 자리에서 말한다 (FR-234) — 자리가 사라지면 사용자는
            탭이라는 것이 없는 줄 안다.
          */}
          {/*
            2026-09-09 — **자리째 접는다.** 브라우저가 닫힌 국면(검토·실행 종료)에서는
            고를 탭이 존재하지 않는다. 이전에는 빈 자리가 남아 「탭 줄이 사라졌다」가
            아니라 「탭 줄이 비었다」로 보였고, 그 둘은 사용자에게 다른 뜻이다.
          */}
          {isShown(capabilities["tab.select"]) && (
            <div data-action="tab.select">
              {target.tabs ?? <Unavailable action="tab.select" capabilities={capabilities} />}
            </div>
          )}
          <div className="flex-1 min-h-0 flex">{target.mirror}</div>
        </>
      )}

      {target.kind === "artifacts" && (
        <div
          className="bg-panel border border-hair rounded-base flex-1 min-h-0 flex flex-col"
        >
          {/*
            산출물 종류를 고르는 조작은 **이 영역 안에** 있다 (FR-246). 지원되지 않는
            종류는 비활성으로 남기고 이유를 붙인다 — 확정 디자인에 있는 것을 빼지 않는다
            (DC-007). `TRACE` 는 서버가 501 을 준다 (001 의 알려진 차이).
          */}
          <div
            /* 산출물 고르기의 자리 (`artifact.select`). */
            data-action="artifact.select"
            className="bg-sunken border-b border-hair-2 [&>button]:border-0 [&>button]:border-r [&>button]:border-hair-2 [&>button]:rounded-none [&>button]:bg-transparent [&>button]:shadow-none [&>button]:text-ink-2 [&>button]:font-mono [&>button]:text-[11px] [&>button]:font-semibold [&>button]:leading-none [&>button]:tracking-[0.1em] [&>button[aria-pressed=true]]:bg-panel [&>button[aria-pressed=true]]:text-ink [&>button:disabled]:border-solid [&>button:disabled]:text-ink-3 flex-[0_0_36px] flex items-stretch"
          >
            {ARTIFACT_TABS.map((t) => {
              const usable = target.available.includes(t.kind);
              const active = target.selected === t.kind;
              return (
                <button
                  key={t.kind}
                  type="button"
                  data-artifact-tab={t.kind}
                  disabled={!usable}
                  aria-pressed={active}
                  title={usable ? undefined : EMPTY_MESSAGE.not_supported}
                  onClick={usable ? () => onSelectArtifact?.(t.kind) : undefined}
                  className={`px-s4 ${usable ? "cursor-pointer" : "cursor-not-allowed"}`}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
          {/*
            005 FR-172 (U-22) — **비활성인 이유를 화면에도 남긴다.** `title` 은 마우스를
            올려야 보이고, 그러면 왜 못 누르는지 알아내는 데 한 번 더 시도가 필요하다.
            확정 디자인에 있는 탭을 빼지 않는 대신(DC-007) 이유를 붙여 남긴다.
          */}
          {target.available.length < ARTIFACT_TABS.length && (
            <div
              data-disabled-reason="artifact.select"
              className="font-sans text-[11px] leading-[1.4] text-ink-3 border-b border-hair py-[6px] px-s4"
            >
              {ARTIFACT_TABS.filter((t) => !target.available.includes(t.kind))
                .map((t) => t.label)
                .join(" · ")}{" "}
              는 이 실행에 남지 않았습니다 (MVP 미지원).
            </div>
          )}
          <div className="flex-1 min-h-0 overflow-auto p-s4">
            {target.body}
          </div>
        </div>
      )}

      {target.kind === "open_browser" && (
        <div
          /*
            008 — **가로 한 줄이다.** v1 은 제목 · 설명 · 버튼을 세로로 쌓아 166px 를
            썼고, 그 자리가 118px 로 정해지면서 내용이 잘렸다. 담는 것은 그대로다.
          */
          className="bg-panel border border-hair rounded-base flex-1 min-h-0 flex flex-row items-center gap-s4 py-0 px-[14px]"
        >
          <div className="flex-1 min-w-0 flex flex-col gap-[2px]">
            <div className="font-sans text-[13px] font-semibold leading-none">브라우저가 열려 있지 않습니다</div>
            <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
              값·순서·삭제는 브라우저 없이 고칠 수 있습니다. 요소를 다시 집거나 직접
              조작으로 Step 을 더하려면 브라우저가 필요합니다.
            </p>
          </div>
          <ActionButton
            action="browser.openAt"
            capability={capabilities["browser.openAt"]}
            label={
              target.label ??
              (target.stepIndex !== null
                ? openBrowserAtStepLabel(target.stepIndex)
                : ACTION_LABEL["browser.openAt"])
            }
            emphasis
            onRun={onOpenBrowser}
            onRemedy={onRemedy}
          />
        </div>
      )}

      {/*
        007 T077 — 빈 이유 4종을 구별한다 (FR-245 · 005 FR-173). "아직 시작하지 않음" 과
        "수집되지 않음" 과 "세션 유실" 은 사용자에게 **서로 다른 다음 행동**을 요구한다.
      */}
      {target.kind === "empty" && (
        <div
          data-target-empty={target.reason}
          role="status"
          className="bg-panel border border-hair rounded-base font-sans text-[13.5px] leading-[1.7] text-ink-2 flex-1 min-h-0 flex items-center justify-center p-s5 whitespace-pre-wrap text-center"
        >
          {EMPTY_MESSAGE[target.reason]}
        </div>
      )}
    </div>
  );
}
