/**
 * 껍데기 — 확정 디자인 18장이 **똑같이** 그리는 층. DC-003·DC-007.
 *
 * ## 2026-09-08 (008) — 전사에서 소비로
 *
 * 이전 판의 머리말은 이렇게 적혀 있었다: "인라인 style 값은 dc.html 에서 그대로 옮겼다.
 * 토큰으로 치환하지 않는다 — 치환하면 확정 디자인과 1:1 대조가 불가능해진다."
 *
 * **그 판단이 틀렸다.** 1:1 대조는 값을 베껴야 성립하는 것이 아니라, 값이 **한 곳에서
 * 오면** 자동으로 성립한다. 베끼는 쪽을 택한 결과 v1→v2 전환에서 기하는 옮겨졌으나
 * 색과 구조는 v1 이 남았고, 대조표 509칸은 한 칸도 채워지지 않았다.
 *
 * 이제 형태는 `theme/tokens.css` 의 정본에서 오고 여기는 그것을 `className` 으로 쓴다.
 * 대조는 L1(정본 ↔ 디자인)과 L2(코드 ↔ 정본)가 기계로 한다
 * (`specs/008-visual-language/contracts/design-conformance.md`).
 *
 * ## 남는 인라인은 배치뿐이다
 *
 * `display`·`flex`·`gap`·`width`·`padding` 은 007 배치 계약의 관할이다. 색·서체·테두리·
 * 모서리·그림자는 여기 없다 (`contracts/visual-language.md` §2).
 */
import type { ReactNode } from "react";

/**
 * 헤더 왼쪽의 제품 표시. 18장 전부에서 동일하다.
 *
 * 008 에서 문구가 「TEST BUILDER」에서 **「ITB」**로 바뀌었다. 확정 디자인이 그렇게 그리며,
 * 헤더가 56px 로 내려온 만큼 표시도 26px 사각형 + 15px 글자로 줄었다. 코드가 디자인과
 * 다르면 코드를 고친다 (spec Assumptions).
 */
export function BrandMark() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
      <div className="brand">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="2" y="2" width="12" height="12" rx="1.5" />
          <path d="M5 8.2l2 2 4-4.4" />
        </svg>
      </div>
      <div className="brand-name">ITB</div>
    </div>
  );
}

/** 헤더 안에서 블록을 가르는 세로 막대. 18장 전부에서 동일하다. */
export function HeaderDivider() {
  return <div className="divider" />;
}

/** 헤더 층. 높이 56 — `ui-contract.md` §1-2 의 값이다. */
export function HeaderBar({ children }: { children: ReactNode }) {
  return <div className="hdr">{children}</div>;
}

/**
 * 아트보드 껍데기.
 *
 * 확정 디자인은 고정 폭(1440px)이다. 창이 그보다 좁으면 **기준 폭을 유지하고 스크롤한다**
 * — 임의로 재배치하지 않는다 (DC-011).
 *
 * 배경을 여기서 칠하지 않는다. 정본의 `body` 가 이미 `var(--bg)` 를 갖고, 아트보드는
 * 그것을 그대로 보인다 — 같은 값을 두 곳에 두지 않는다 (C-1).
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
   * 확정 디자인은 고정 폭이고 그것이 DC-011 의 전제다. 007 의 통합 화면만 이 값을 켠다 —
   * 껍데기(헤더 구성·영역 배치·최소 기준 폭)는 고정하고 **좌측 대상 앱 영역만** 남는 폭을
   * 가져간다. 좁은 창 정책은 그대로다: 재배치하지 않고 스크롤한다.
   */
  grow?: boolean;
  children: ReactNode;
}) {
  return (
    <div style={{ overflowX: "auto", minHeight: "100vh" }}>
      <div
        style={{
          ...(grow ? { minWidth: `${width}px`, width: "100%" } : { width: `${width}px` }),
          ...(height !== undefined ? { height: `${height}px` } : {}),
          ...(minHeight !== undefined ? { minHeight: `${minHeight}px` } : {}),
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </div>
    </div>
  );
}

/** 통합 작업 화면의 경로 표시 — 「테스트 / TC-001」. */
export function Breadcrumb({ testId }: { testId: string }) {
  return (
    <div className="row muted" style={{ gap: "8px" }}>
      <span className="lbl">테스트</span>
      <span className="pill mono">{testId}</span>
    </div>
  );
}
