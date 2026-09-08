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

import { mirrorEmptyMessage, mirrorNotice, type MirrorNoticePhase } from "../lib/wording";

/**
 * 미리보기의 국면 (005 재점검 U-04-b).
 *
 * `pausing`·`finished` 를 더한 이유는 이 둘이 `paused` 로 뭉개져 있었기 때문이다 —
 * 전이 중에도, 실행이 끝난 뒤에도 오버레이가 「일시정지」를 단정했고 같은 화면의
 * 배지는 「일시정지 중…」·「실행 종료」라고 말했다. 값이 없으면 화면이 구분할 수 없다.
 *
 * 문구는 `wording.ts` 가 소유한다 (005 T107 · 006 T084).
 */
export type MirrorPhase = MirrorNoticePhase;

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
          className="row sunken"
          style={{ gap: 8, padding: "6px 14px" }}
        >
          <span className="chip warn mono">1 FPS</span>
          <span className="muted">{degradedReason}</span>
        </div>
      )}

      <div
        className="sunken"
        style={{ flex: 1, display: "grid", placeItems: "center", overflow: "hidden", minHeight: 0 }}
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
            {mirrorEmptyMessage(phase)}
          </p>
        )}
      </div>
    </div>
  );
}

/** 국면별 안내. 어디서 조작해야 하는지를 매번 분명히 한다 (FR-023b). */
function PhaseNotice({ phase, tabIndex }: { phase: MirrorPhase; tabIndex?: number }) {
  const notice = mirrorNotice(phase);
  if (notice === null) return null;

  const tabSuffix = tabIndex !== undefined && tabIndex > 0 ? ` (탭 ${tabIndex})` : "";
  // 관찰 국면만 상태 이름을 칩으로 쓴다 — 확정 디자인의 「읽기 전용」 배지다.
  const asBadge = phase === "observation";

  return (
    <div
      className={`row${phase === "manipulation" ? " tint-warn" : ""}`}
      style={{ gap: 8, padding: "10px 14px" }}
    >
      {asBadge ? (
        <span className="chip mono">{notice.title}</span>
      ) : (
        <strong>
          {notice.title}
          {tabSuffix}
        </strong>
      )}
      <span className="muted">
        {notice.detail}
        {asBadge ? `${tabSuffix}.` : ""}
      </span>
    </div>
  );
}
