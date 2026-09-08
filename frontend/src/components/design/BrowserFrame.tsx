/**
 * 대상 앱을 감싸는 껍데기. 확정 디자인의 ③-a 자리다.
 *
 * ## 2026-09-08 (008) — 어두운 껍데기를 버렸다
 *
 * v1 은 이 자리를 **잉크 판**으로 그렸다 — 검정 바탕에 회색 아이콘, `#2A303A` 주소 칸.
 * 실제 브라우저처럼 보이게 하려던 것인데, 확정 디자인은 정반대로 간다: 30px 옅은 우물
 * 띠 + 종이 주소 칸 + 상태 표식 하나다.
 *
 * **이유가 있다.** 이 안에 들어오는 것은 사용자의 앱이고 그 앱은 자기 색을 갖는다.
 * 껍데기가 어두우면 두 색 체계가 화면에서 부딪히고, 무엇이 제품이고 무엇이 대상인지
 * 경계가 흐려진다. 껍데기를 종이로 낮추면 대상 앱이 그 자리의 주인공이 된다.
 *
 * 확정 디자인 안의 `#1F2A37`·`#2563EB` 같은 색은 **미러되는 예시 앱의 색**이지 ITB 의
 * 시각 언어가 아니다. 정본에 들이지 않는다 (FR-266).
 */
import type { ReactNode } from "react";

/**
 * 지금 이 미러가 무엇인지 (읽기 전용 · 녹화 중 · 일시정지 …).
 *
 * 색을 직접 받지 않고 **뜻**을 받는다. 색을 받으면 부르는 쪽마다 다른 색을 넣게 되고,
 * 실제로 그렇게 돼서 `SessionScreen` 이 여섯 가지 배경색을 손으로 정하고 있었다.
 */
export interface ModeBadge {
  label: string;
  /** 정본의 `.chip` 변형. 빈 값이면 중립이다. */
  tone: "" | "pass" | "fail" | "warn" | "run" | "ai";
}

/** 주소 칸 왼쪽의 점 셋. 실제 브라우저를 뜻하는 관용 표기이며 조작이 아니다. */
function WindowDots() {
  return (
    <div style={{ display: "flex", gap: 4 }} aria-hidden>
      {[0, 1, 2].map((i) => (
        <span key={i} className="dot" />
      ))}
    </div>
  );
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
      className="pane"
      style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}
    >
      <div
        className="pane-hd"
        style={{ flex: "0 0 30px", display: "flex", alignItems: "center", gap: 8, padding: "0 10px" }}
      >
        <WindowDots />
        <div className="addr">{url}</div>
        <span className={`chip ${badge.tone}`.trimEnd()}>{badge.label}</span>
      </div>
      <div style={{ flex: 1, minHeight: 0, display: "flex" }}>{children}</div>
    </div>
  );
}
