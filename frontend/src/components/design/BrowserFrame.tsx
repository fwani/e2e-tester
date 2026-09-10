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
    <div className="flex gap-s1" aria-hidden>
      {[0, 1, 2].map((i) => (
        <span key={i} className="w-[8px] h-[8px] rounded-full bg-hair-2" />
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
      className="bg-panel border border-hair rounded-base flex-1 min-h-0 flex flex-col overflow-hidden"
    >
      <div
        data-frame-head
        className="bg-sunken border-b border-hair-2 text-ink-2 flex-[0_0_30px] flex items-center gap-s2 py-0 px-[10px]"
      >
        <WindowDots />
        <div className="flex-1 h-[19px] flex items-center px-s2 bg-panel">{url}</div>
        <span className={`chip ${badge.tone}`.trimEnd()}>{badge.label}</span>
      </div>
      {/*
        2026-09-09 — **`column` 이 빠져 있었다** (사용자 보고: 「파일 업로드 후에 미러
        화면이 작아지는 버그」).

        `flexDirection` 이 없으면 기본값은 `row` 다. 이 자리에 들어오는 것은 브라우저
        요구 패널(`BrowserPromptPanel`) + 미러 둘이고(`SessionScreen` 의 `mirror`),
        `row` 였으므로 요구 패널이 미러 **위**가 아니라 **왼쪽 옆**에 서서 자기 콘텐츠
        폭(제목·설명·파일 선택칸·버튼 둘)을 가져갔다. 그래서 파일 선택 요구가 뜨는
        순간 미러가 가로로 눌렸다.

        `SessionScreen` 의 그 자리 주석은 「브라우저 요구를 **미러 바로 위에** 둔다」
        (010 FR-338·FR-339)라고 적고 있었다 — 의도는 처음부터 세로였고, 이 한 줄이
        그것과 어긋나 있었다.
      */}
      <div className="flex-1 min-h-0 flex flex-col">
        {children}
      </div>
    </div>
  );
}
