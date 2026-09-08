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
import type { CapabilityMap } from "../../lib/capabilities";
import type { SlotSize, SlotStyle } from "../../lib/layout";
import { ACTION_LABEL, openBrowserAtStepLabel } from "../../lib/wording";
import { ActionButton } from "./ActionButton";
import type { EmptyReason, TargetView } from "./model";

const INK = "#14171C";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

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
  size: SlotStyle;
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
  return (
    <span
      data-disabled-reason={action}
      style={{ font: `400 12px/1.5 ${SANS}`, color: "#4A515C" }}
    >
      {state.reason}
    </span>
  );
}

export function TargetPane({
  target,
  size,
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
      style={{
        ...size,
        minWidth: "0",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
      }}
    >
      {target.kind === "mirror" && (
        <>
          {/*
            탭 고르기의 **자리** (`tab.select`). 목록을 아직 받지 못했어도 자리는 남고,
            왜 고를 수 없는지 그 자리에서 말한다 (FR-234) — 자리가 사라지면 사용자는
            탭이라는 것이 없는 줄 안다.
          */}
          <div data-action="tab.select">
            {target.tabs ?? <Unavailable action="tab.select" capabilities={capabilities} />}
          </div>
          <div style={{ flex: 1, minHeight: 0, display: "flex" }}>{target.mirror}</div>
        </>
      )}

      {target.kind === "artifacts" && (
        <div
          style={{
            flex: 1,
            minHeight: 0,
            border: `1px solid ${INK}`,
            borderRadius: "3px",
            background: "#FFFFFF",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/*
            산출물 종류를 고르는 조작은 **이 영역 안에** 있다 (FR-246). 지원되지 않는
            종류는 비활성으로 남기고 이유를 붙인다 — 확정 디자인에 있는 것을 빼지 않는다
            (DC-007). `TRACE` 는 서버가 501 을 준다 (001 의 알려진 차이).
          */}
          <div
            /* 산출물 고르기의 자리 (`artifact.select`). */
            data-action="artifact.select"
            style={{
              flex: "0 0 46px",
              display: "flex",
              alignItems: "stretch",
              borderBottom: `1px solid ${INK}`,
              background: "#F2F4F7",
            }}
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
                  style={{
                    padding: "0 16px",
                    border: "none",
                    borderRadius: "3px",
                    borderRight: `1px solid ${INK}`,
                    boxShadow: "none",
                    background: active ? INK : "transparent",
                    color: active ? "#F2F4F7" : usable ? INK : "#6E757F",
                    font: `600 11px/1 ${MONO}`,
                    letterSpacing: "0.1em",
                    cursor: usable ? "pointer" : "not-allowed",
                  }}
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
              style={{
                padding: "6px 16px",
                borderBottom: "1px solid #E3E6EB",
                font: `400 12px/1.4 ${MONO}`,
                color: "#6E757F",
              }}
            >
              {ARTIFACT_TABS.filter((t) => !target.available.includes(t.kind))
                .map((t) => t.label)
                .join(" · ")}{" "}
              는 이 실행에 남지 않았습니다 (MVP 미지원).
            </div>
          )}
          <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "16px" }}>
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
          style={{
            flex: 1,
            minHeight: 0,
            border: "1px solid #E3E6EB",
            borderRadius: "3px",
            background: "#FFFFFF",
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            gap: 16,
            padding: "0 14px",
          }}
        >
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 2 }}>
            <div style={{ font: `600 13px/1.4 ${SANS}` }}>
              브라우저가 열려 있지 않습니다
            </div>
            <p className="dim" style={{ font: `400 11px/1.45 ${SANS}`, margin: 0 }}>
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
          style={{
            flex: 1,
            minHeight: 0,
            border: `1px solid ${INK}`,
            borderRadius: "3px",
            background: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            font: `400 14px/1.7 ${SANS}`,
            color: "#4A515C",
            whiteSpace: "pre-wrap",
            textAlign: "center",
          }}
        >
          {EMPTY_MESSAGE[target.reason]}
        </div>
      )}
    </div>
  );
}
