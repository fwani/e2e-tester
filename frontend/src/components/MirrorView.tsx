/**
 * 관찰용 읽기 전용 미러 (T088). FR-047·FR-023b.
 *
 * **이 영역은 조작 대상이 아니다** (FR-047a). 사용자 입력을 대상 브라우저로 전달하는
 * 경로를 두지 않는다 — 그래서 프레임을 `<img>` 로 그리고 포인터 이벤트를 끈다.
 * 클릭·키 입력을 받아 전달하는 코드가 이 파일에 없다는 것이 요구사항의 구현이다.
 *
 * 조작 국면(직접 녹화·직접 동작 추가·사람 인수)에서는 **실제 브라우저 창에서 조작한다**
 * (clarify 결정 3). 그 사실을 화면에 명시해야 사용자가 이 영역을 클릭하며 헤매지 않는다.
 *
 * 프레임은 유실 가능하다 — 마지막 프레임만 그리면 되고, 유실이 실행에 영향을 주지
 * 않는다 (FR-047b).
 */

export type MirrorPhase = "manipulation" | "observation" | "paused" | "terminated";

export interface MirrorViewProps {
  /** base64 JPEG. 아직 한 장도 못 받았으면 null. */
  frame: string | null;
  phase: MirrorPhase;
  /** 미러가 중단된 사유. 있으면 프레임 대신 이 사유를 보여준다 (FR-047e). */
  stoppedReason?: string | null;
  /** 1fps 스크린샷으로 강등된 사유 (research R3 폴백). */
  degradedReason?: string | null;
  /** 현재 표시 중인 탭. 여러 탭일 때 무엇을 보고 있는지 알려 준다 (FR-030f). */
  tabIndex?: number;
}

export function MirrorView({
  frame,
  phase,
  stoppedReason = null,
  degradedReason = null,
  tabIndex,
}: MirrorViewProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0, flex: 1 }}>
      <PhaseNotice phase={phase} tabIndex={tabIndex} />

      {degradedReason !== null && (
        <div
          className="row"
          style={{ gap: 8, padding: "6px 14px", background: "var(--surface-soft)" }}
        >
          <span className="badge warn mono">1 FPS</span>
          <span className="muted">{degradedReason}</span>
        </div>
      )}

      <div
        style={{
          flex: 1,
          display: "grid",
          placeItems: "center",
          background: "var(--paper-alt)",
          overflow: "hidden",
          minHeight: 0,
        }}
      >
        {stoppedReason !== null ? (
          <p className="muted" style={{ textAlign: "center", padding: 24 }}>
            {stoppedReason}
          </p>
        ) : frame !== null ? (
          <img
            src={`data:image/jpeg;base64,${frame}`}
            alt="대상 브라우저 화면 (읽기 전용)"
            /* FR-047a — 입력을 대상 브라우저로 전달하지 않는다. 포인터를 아예 받지 않는다. */
            style={{
              maxWidth: "100%",
              maxHeight: "100%",
              pointerEvents: "none",
              userSelect: "none",
            }}
            draggable={false}
          />
        ) : (
          <p className="muted" style={{ textAlign: "center", padding: 24 }}>
            {emptyMessage(phase)}
          </p>
        )}
      </div>
    </div>
  );
}

/** 국면별 안내. 어디서 조작해야 하는지를 매번 분명히 한다 (FR-023b). */
function PhaseNotice({ phase, tabIndex }: { phase: MirrorPhase; tabIndex?: number }) {
  const tabSuffix = tabIndex !== undefined && tabIndex > 0 ? ` (탭 ${tabIndex})` : "";

  if (phase === "manipulation") {
    return (
      <div
        className="row"
        style={{ gap: 8, padding: "10px 14px", background: "var(--warn-tint)" }}
      >
        <strong>실제 브라우저 창에서 조작 중{tabSuffix}</strong>
        <span className="muted">이 영역은 관찰용이며 조작 대상이 아닙니다.</span>
      </div>
    );
  }

  if (phase === "paused") {
    return (
      <div
        className="row"
        style={{ gap: 8, padding: "10px 14px", background: "var(--surface)" }}
      >
        <strong>일시정지{tabSuffix}</strong>
        <span className="muted">
          브라우저 세션과 화면 상태를 그대로 유지하고 있습니다.
        </span>
      </div>
    );
  }

  if (phase === "terminated") {
    return null;
  }

  return (
    <div
      className="row"
      style={{ gap: 8, padding: "10px 14px", background: "var(--surface)" }}
    >
      <span className="badge mono">읽기 전용</span>
      <span className="muted">실행 중인 화면을 관찰합니다{tabSuffix}.</span>
    </div>
  );
}

function emptyMessage(phase: MirrorPhase): string {
  // 005 FR-163 (U-24) — **곧 올 것처럼 말하지 않는다.**
  //
  // 기존 문구 "미러 프레임을 기다리고 있습니다" 는 기다리면 온다고 말했지만, 정적
  // 화면에서는 한 장도 오지 않았다(실측 0건). 사용자는 화면을 보며 무한정 기다렸다.
  //
  // 이제는 실제로 온다(마지막 프레임 캐시 + 무프레임 감시). 그래서 이 문구는 짧게만
  // 보이지만, 문구 자체도 사실에 맞춘다 — 대상 브라우저 창이 이미 열려 있다는 사실을
  // 함께 말해 "아무것도 안 뜬다" 는 오해를 막는다.
  switch (phase) {
    case "observation":
      return "대상 화면이 표시되기를 기다리고 있습니다. 대상 브라우저 창은 이미 열려 있습니다.";
    case "manipulation":
      return "실제 브라우저 창에서 조작하세요. 이 영역은 관찰용입니다.";
    case "paused":
      return "일시정지 중입니다. 마지막 화면을 표시합니다.";
    case "terminated":
      return "세션이 종료되어 미러가 중단됐습니다.";
  }
}
