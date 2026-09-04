/**
 * 대상 앱을 감싸는 브라우저 껍데기. `Main`·`RunnerPaused`·`Takeover`·`AiRecord` 공통.
 *
 * **안쪽 흰 영역은 대상 앱이지 우리 UI 가 아니다.** 확정 디자인이 그 안에 그려 놓은
 * 화면(프로젝트 목록 등)은 표본이므로 옮기지 않는다 — 옮기면 실제 대상 앱 위에 가짜
 * 화면을 덧그리는 것이 된다. 그 자리는 미러 뷰가 채운다 (001 FR-047).
 *
 * 껍데기(주소줄·탐색 버튼·모드 배지)는 우리 UI 이므로 확정 디자인 그대로 옮긴다.
 */
import type { ReactNode } from "react";

/** 확정 디자인의 뒤로·앞으로·새로고침 아이콘. `d` 를 그대로 옮겼다. */
const NAV_ICONS = [
  "M10 3.5L5.5 8l4.5 4.5",
  "M6 3.5L10.5 8 6 12.5",
  "M13 8a5 5 0 1 1-1.6-3.7M13 1.6v3.2h-3.2",
];

export interface ModeBadge {
  label: string;
  background: string;
  color: string;
}

export function BrowserFrame({
  url,
  badge,
  children,
}: {
  url: string;
  badge: ModeBadge;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        border: "3px solid #14130F",
        background: "#14130F",
        flex: "1",
        minHeight: "0",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          flex: "0 0 46px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "0 12px",
          background: "#14130F",
        }}
      >
        <div style={{ display: "flex", gap: "0", color: "#8E897C" }}>
          {NAV_ICONS.map((d) => (
            <div
              key={d}
              style={{
                width: "44px",
                height: "44px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d={d} />
              </svg>
            </div>
          ))}
        </div>
        <div
          style={{
            flex: "1",
            display: "flex",
            alignItems: "center",
            height: "28px",
            padding: "0 10px",
            background: "#2A2823",
            color: "#C9C4B4",
            font: "400 12px/1 'IBM Plex Mono', ui-monospace, monospace",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {url}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            height: "28px",
            padding: "0 9px",
            background: badge.background,
            color: badge.color,
            font: "700 11px/1 'IBM Plex Mono', ui-monospace, monospace",
            letterSpacing: "0.08em",
          }}
        >
          {badge.label}
        </div>
      </div>
      <div
        style={{
          flex: "1",
          minHeight: "0",
          background: "#FFFFFF",
          display: "flex",
          borderTop: "3px solid #14130F",
        }}
      >
        {children}
      </div>
    </div>
  );
}
