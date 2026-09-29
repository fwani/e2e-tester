/**
 * AI 가 만진 요소의 자리 (024 US1·US2 · FR-012·FR-013·FR-020·FR-022).
 *
 * ## 이 컴포넌트는 아무것도 판정하지 않는다
 *
 * 어느 탭을 보고 있는지, 프레임이 있는지, 수명이 지났는지, 좌표를 어떻게 옮기는지 —
 * **전부 바깥에서 끝난다.** 여기가 받는 것은 이미 표시 좌표로 옮겨진 자리 하나뿐이고,
 * 받으면 그린다.
 *
 * 010 이 미러의 조작 가능 여부에 대해 세운 규칙과 같다 (FR-316) — 컴포넌트가 스스로
 * 국면을 보면 판정이 두 곳에 생기고, 둘이 갈리는 날 화면은 그릴 수 있다고 그리고
 * 좌표는 틀린다.
 *
 * ## 포인터를 받지 않는다
 *
 * `pointer-events: none` 이 **요구사항의 구현이다** (FR-020). 일시정지·직접 녹화·사람
 * 인수 국면에서 사용자는 미러를 직접 조작하고, 그때 테두리가 덮인 자리를 클릭하면 그
 * 클릭은 `<img>` 로 내려가야 한다. 여기가 먹으면 사용자는 클릭했는데 아무 일도 일어나지
 * 않는 것을 보게 된다 — SC-516 이 0건으로 두려는 상태다.
 *
 * ## 색을 만들지 않는다
 *
 * 정본의 `run`·`fail` 을 쓴다 (FR-022 · contracts/visual-language.md). 「지금 살아
 * 움직이는 것」과 「실패한 것」의 색이 이미 시각 언어에 있으므로 새로 만들 이유가 없다.
 */

import type { DisplayRect } from "./useMirrorInput";

export interface FocusMarkView {
  /** 이미지 표시 영역 기준의 자리. 바깥에서 이미 변환됐다 */
  rect: DisplayRect;
  /** 조작이 성공했는가 (FR-008). 「수행 중」은 없다 — 024 research R2 */
  status: "done" | "failed";
  /** Step 의 이름표. 보조기술이 읽을 이름이 된다 (FR-009) */
  label: string;
}

export function FocusOverlay({ mark }: { mark: FocusMarkView | null }) {
  if (mark === null) return null;
  const failed = mark.status === "failed";
  return (
    <div
      data-focus-mark={mark.status}
      /*
        **보조기술에는 숨긴다.** 같은 사실이 진행 문구(`ai_progress`)로 이미 읽히고,
        여기서 또 읽으면 한 동작이 두 번 안내된다. 이 표시는 화면을 **보는** 사용자가
        말과 자리를 잇게 해 주는 것이고, 문구가 없어지는 것이 아니다 (FR-023).
      */
      aria-hidden="true"
      style={{
        position: "absolute",
        left: `${mark.rect.left}px`,
        top: `${mark.rect.top}px`,
        width: `${mark.rect.width}px`,
        height: `${mark.rect.height}px`,
      }}
      /*
        `pointer-events-none` 은 장식이 아니라 요구사항이다 (머리말). 지우면 조작
        국면에서 클릭이 조용히 사라진다.

        테두리를 **바깥으로 그린다** (`outline`). `border` 로 그리면 요소의 경계선이
        자리 안쪽을 덮어, 작은 요소에서는 요소 자체가 테두리에 가려진다.
      */
      className={
        failed
          ? "pointer-events-none rounded-chip outline outline-2 outline-fail bg-fail-t/30"
          : "pointer-events-none rounded-chip outline outline-2 outline-run bg-run-t/25"
      }
    />
  );
}
