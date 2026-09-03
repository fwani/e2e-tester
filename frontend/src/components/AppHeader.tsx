/** 공용 헤더. 8화면 공통 요소 (TEST BUILDER 로고 + 경로 + 상태 배지). */
import type { ReactNode } from "react";

export function AppHeader({
  breadcrumb,
  status,
  actions,
}: {
  breadcrumb: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header
      className="row"
      style={{
        gap: 12,
        padding: "10px 16px",
        background: "var(--ink)",
        color: "var(--paper)",
        borderBottom: "1px solid var(--ink)",
      }}
    >
      <span style={{ fontFamily: "var(--font-display)", letterSpacing: "0.02em" }}>
        TEST BUILDER
      </span>
      <span style={{ color: "var(--dim)" }}>{breadcrumb}</span>
      <span className="spacer" />
      {status}
      {actions}
    </header>
  );
}
