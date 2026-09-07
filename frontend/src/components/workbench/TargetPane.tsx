/**
 * 층③ 좌측 대상 앱 영역 (007 T023 · FR-244·FR-245·FR-246).
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
 * 인라인 style 값은 `docs/design/Main.dc.html`(좌측 `flex: 1; padding: 20px`)과
 * `RunResult.dc.html`(산출물 영역)에서 그대로 옮겼다 (DC-001).
 */
import type { ArtifactKind } from "../../api/client";
import type { CapabilityMap } from "../../lib/capabilities";
import { ACTION_LABEL, openBrowserAtStepLabel } from "../../lib/wording";
import { ActionButton } from "./ActionButton";
import type { EmptyReason, TargetView } from "./model";

const INK = "#14130F";
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
      style={{ font: `400 12px/1.5 ${SANS}`, color: "#6B675C" }}
    >
      {state.reason}
    </span>
  );
}

export function TargetPane({
  target,
  capabilities,
  onSelectArtifact,
  onOpenBrowser,
  onRemedy,
}: TargetPaneProps) {
  return (
    <div
      data-workbench-target
      style={{
        flex: "1",
        minWidth: "0",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        minHeight: 0,
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
            border: `3px solid ${INK}`,
            background: "#FFFDF6",
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
              borderBottom: `3px solid ${INK}`,
              background: "#EFEBE0",
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
                    borderRight: `2px solid ${INK}`,
                    boxShadow: "none",
                    background: active ? INK : "transparent",
                    color: active ? "#EFEBE0" : usable ? INK : "#9A968A",
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
          <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "16px" }}>
            {target.body}
          </div>
        </div>
      )}

      {target.kind === "open_browser" && (
        <div
          style={{
            flex: 1,
            minHeight: 0,
            border: `3px solid ${INK}`,
            background: "#FFFDF6",
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
            justifyContent: "center",
            gap: 14,
            padding: "24px",
          }}
        >
          <div style={{ font: `600 16px/1.5 ${SANS}` }}>
            브라우저가 열려 있지 않습니다.
          </div>
          <p className="dim" style={{ font: `400 13px/1.6 ${SANS}`, margin: 0, maxWidth: 460 }}>
            값·순서·삭제는 브라우저 없이 고칠 수 있습니다. 요소를 다시 집거나 직접
            조작으로 Step 을 더하려면 브라우저가 필요합니다.
          </p>
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
            border: `3px solid ${INK}`,
            background: "#FFFDF6",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            font: `400 14px/1.7 ${SANS}`,
            color: "#6B675C",
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
