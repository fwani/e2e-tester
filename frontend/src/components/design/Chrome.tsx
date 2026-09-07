/**
 * 확정 디자인 8종에 **바이트 단위로 동일하게** 나타나는 조각들. DC-003·DC-007.
 *
 * 여기 있는 것만 공유한다. `scripts/dc_to_jsx.py` 로 8개 파일을 변환한 뒤 앞 20줄의
 * 해시를 비교해 실제로 같은 것만 골랐다 — 비슷해 보인다고 묶지 않았다. 미리 추상화하면
 * 그 층에서 다시 해석이 일어나고, 그것이 002 라운드의 원인이다.
 *
 * 인라인 style 값은 dc.html 에서 그대로 옮겼다. 토큰으로 치환하지 않는다 — 치환하면
 * 확정 디자인과 1:1 대조가 불가능해진다 (contracts/design-conformance.md §2).
 */
import type { ReactNode } from "react";

/** 헤더 왼쪽의 로고 블록. 8종 전부에서 동일하다. */
export function BrandMark() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <div
        style={{
          width: "34px",
          height: "34px",
          background: "#14130F",
          color: "#F5D000",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="20" height="20" viewBox="0 0 20 20">
          <rect x="2.5" y="2.5" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.5" />
          <circle cx="10" cy="10" r="3.5" fill="currentColor" />
        </svg>
      </div>
      <div
        style={{
          fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
          fontSize: "19px",
          letterSpacing: "0.01em",
        }}
      >
        TEST BUILDER
      </div>
    </div>
  );
}

/** 로고와 그다음 블록 사이의 세로 막대. 8종 전부에서 동일하다. */
export function HeaderDivider() {
  return <div style={{ width: "3px", height: "32px", background: "#14130F" }} />;
}

/** 60px 헤더 껍데기. 8종 전부에서 동일하다. */
export function HeaderBar({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        flex: "0 0 60px",
        borderBottom: "3px solid #14130F",
        background: "#FFFDF6",
        display: "flex",
        alignItems: "center",
        gap: "18px",
        padding: "0 24px",
      }}
    >
      {children}
    </div>
  );
}

/**
 * 아트보드 껍데기.
 *
 * 확정 디자인은 고정 폭(1440px 등)이다. 창이 그보다 좁으면 **기준 폭을 유지하고
 * 스크롤한다** — 임의로 재배치하지 않는다 (DC-011).
 */
export function Artboard({
  width,
  minHeight,
  height,
  grow = false,
  children,
}: {
  width: number;
  minHeight?: number;
  height?: number;
  /**
   * 창이 기준 폭보다 **넓을 때** 늘어나는가 (007 FR-218a).
   *
   * 확정 디자인 8종은 고정 폭이고 그것이 DC-011 의 전제다. 007 의 통합 화면만 이 값을
   * 켠다 — 껍데기(헤더 구성·영역 배치·최소 기준 폭)는 고정하고 **좌측 대상 앱 영역만**
   * 남는 폭을 가져간다. 좁은 창 정책은 그대로다: 재배치하지 않고 스크롤한다.
   *
   * 이 값이 켜진 화면은 승인 대상 A3 에 걸려 있다
   * (`specs/007-unify-test-screens/design-conformance/undefined-states.md`).
   */
  grow?: boolean;
  children: ReactNode;
}) {
  return (
    <div style={{ overflowX: "auto", background: "#EFEBE0", minHeight: "100vh" }}>
      <div
        style={{
          ...(grow
            ? { minWidth: `${width}px`, width: "100%" }
            : { width: `${width}px` }),
          ...(height !== undefined ? { height: `${height}px` } : {}),
          ...(minHeight !== undefined ? { minHeight: `${minHeight}px` } : {}),
          background: "#EFEBE0",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </div>
    </div>
  );
}

/** 러너 계열 5종(Main·RunnerPaused·Takeover·RunResult·AiRecord)의 경로 표시. */
export function Breadcrumb({ testId }: { testId: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        font: "500 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
        color: "#6B675C",
      }}
    >
      테스트
      <span style={{ color: "#14130F" }}>/</span>
      <span
        style={{
          color: "#14130F",
          fontWeight: "600",
          fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
        }}
      >
        {testId}
      </span>
    </div>
  );
}

/**
 * 헤더 오른쪽의 상태 알약. 화면마다 색과 문구가 다르지만 형태는 같다.
 *
 * `Main.dc.html` 은 `RUNNING` 을 잉크 배경 + 노랑 글자로, `RunnerPaused.dc.html` 은
 * `PAUSED` 를 노랑 배경 + 잉크 글자로 그린다. 그 차이를 props 로 받는다.
 */
export function StatusPill({
  background,
  color,
  border = "3px solid #14130F",
  children,
}: {
  background: string;
  color: string;
  border?: string;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        height: "40px",
        padding: "0 14px",
        border,
        background,
        color,
        font: "700 13px/1 'IBM Plex Mono', ui-monospace, monospace",
        letterSpacing: "0.08em",
      }}
    >
      {children}
    </div>
  );
}

/** 상태 알약 안의 점. `Main.dc.html` 의 `tb-live` 클래스를 그대로 쓴다. */
export function LiveDot({ className }: { className?: string }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" className={className}>
      <circle cx="6" cy="6" r="5" fill="currentColor" />
    </svg>
  );
}
