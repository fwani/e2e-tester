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
import { Pill } from "../../ui/Chip";

/**
 * 헤더 왼쪽의 제품 표시. 18장 전부에서 동일하다.
 *
 * 008 에서 문구가 「TEST BUILDER」에서 **「ITB」**로 바뀌었다. 확정 디자인이 그렇게 그리며,
 * 헤더가 56px 로 내려온 만큼 표시도 26px 사각형 + 15px 글자로 줄었다. 코드가 디자인과
 * 다르면 코드를 고친다 (spec Assumptions).
 */
export function BrandMark() {
  return (
    <div className="flex items-center gap-[9px]">
      <div className="w-[26px] h-[26px] bg-ink text-panel rounded-base flex items-center justify-center flex-none">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="2" y="2" width="12" height="12" rx="1.5" />
          <path d="M5 8.2l2 2 4-4.4" />
        </svg>
      </div>
      <div className="font-sans text-[15px] font-bold leading-none tracking-[-0.01em]">ITB</div>
    </div>
  );
}

/** 헤더 안에서 블록을 가르는 세로 막대. 18장 전부에서 동일하다. */
export function HeaderDivider() {
  return <div className="w-px h-[20px] bg-hair-2 flex-none" />;
}

/** 헤더 층. 높이 56 — `ui-contract.md` §1-2 의 값이다. */
export function HeaderBar({ children }: { children: ReactNode }) {
  // 정본 `.hdr` 은 `flex: 0 0 56px` — 기준 크기가 56px 이다. `flex-none`(=`0 0 auto`)
  // 은 기준을 내용에서 가져오므로 같은 뜻이 아니다 (L2 대조가 잡았다).
  // `data-shell` — 이 문서에 머리띠가 있다는 사실 (017 layout-contract-v3 L2 · screen-sweep SW-6).
  return (
    <div
      data-shell="header"
      className="grow-0 shrink-0 basis-header h-header flex items-center gap-[14px] px-s4 bg-panel border-b border-hair"
    >
      {children}
    </div>
  );
}

/**
 * 아트보드 껍데기 — **데이터 화면의 정책** (017 layout-contract-v3 L3 · B-10 · B-11).
 *
 * 확정 디자인은 기준 폭(1440px)이다. 017 전에는 두 갈래였다 — 목록·가져오기는 고정 폭으로 **왼쪽에 붙어** 넓은 창에서
 * 오른쪽이 비었고(B-10), 작업 화면만 `grow` 로 늘어났다. 그리고 머리띠가 가로 스크롤 영역 **안**에 있어, 1280 창에서
 * 오른쪽 끝 조작에 자동 초점이 가 스크롤이 160px 움직이면 머리띠가 창 밖으로 밀려났다(B-11).
 *
 * 이제 정책이 하나다 (2026-09-14 사용자 결정 「창 폭을 채운다」).
 *
 * | 창 | 본문 | 머리띠 |
 * |---|---|---|
 * | 기준 폭보다 넓다 | 창 폭을 채운다 — 늘어난 폭은 가변 칸(목록 이름 칸 · 대상 앱 영역)이 가져간다 | 창 폭 |
 * | 기준 폭보다 좁다 | 기준 폭을 지키고 **본문만** 가로로 스크롤한다 (DC-011 — 임의로 재배치하지 않는다) | 창 폭 · 스크롤 영역 밖 |
 *
 * 폼 화면(프로젝트 · 비밀 값 · 키 관리)은 이것을 쓰지 않는다 — 읽기 폭으로 가운데 서는 `main` 이 그 화면들의 정책이다
 * (L3 `form` · 순회 SW-6 이 가운데를 잰다).
 *
 * ## 요소 구조 — 바깥 두 겹은 017 전과 같은 자리다
 *
 * 뿌리와 세로 배치 상자는 전과 같고, 그 안에 스크롤 영역과 본문 상자가 한 겹씩 더해졌다. 더해진 둘에 `data-slot` 을
 * 둔다 — L2 대조(`scripts/design_compare_ba.py`)가 이 둘을 경로에서 **건너뛰어** 본문 요소가 전환 전 경로로 짝지어진다.
 * 표시가 없으면 화면 전체가 「짝 없음」이 되어 대조가 아무것도 재지 못한다.
 *
 * 배경을 여기서 칠하지 않는다. 정본의 `body` 가 이미 `var(--bg)` 를 갖고, 아트보드는 그것을 그대로 보인다 (C-1).
 */
export function Artboard({
  width,
  minHeight,
  fill = false,
  header,
  children,
}: {
  /** 기준 폭. 창이 이보다 좁으면 본문이 이 폭을 지키고 가로로 스크롤한다. */
  width: number;
  minHeight?: number;
  /**
   * 창 높이에 **맞춘다** — 내용이 늘어도 아트보드가 늘어나지 않는다.
   *
   * ## 왜 필요한가
   *
   * `minHeight` 만 두면 아트보드는 내용만큼 늘어난다. 안쪽에 `overflowY: auto` 인
   * 스크롤 영역이 있어도 소용이 없다 — 부모가 무한히 늘어나면 그 영역도 함께 늘어나
   * 스크롤할 것이 남지 않는다. 그래서 Step 이 쌓일수록 **페이지 전체가 길어지고**,
   * 헤더·국면 띠·미러가 위로 밀려 올라간다.
   *
   * ## 왜 `minHeight` 를 지우지 않는가
   *
   * 둘은 다른 상황을 맡는다. 창이 기준 높이보다 **크면** `height` 가 이겨 아트보드가
   * 창에 맞고 안쪽이 스크롤한다. 창이 기준보다 **작으면** `minHeight` 가 이겨 아트보드가
   * 기준 높이를 지키고 페이지가 스크롤한다 — 좁은 창에서 재배치하지 않고 스크롤한다는
   * 기존 정책과 같은 판단이다. 층이 눌려 읽을 수 없게 되는 것보다 스크롤이 낫다.
   *
   * `100dvh` 는 주소 표시줄이 접히는 브라우저에서 창의 **실제** 높이다.
   */
  fill?: boolean;
  /** 머리띠(`HeaderBar`). **가로 스크롤 영역 밖**에 서서 늘 창 폭에 맞는다 (B-11). */
  header?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-h-[100vh]" data-slot="artboard">
      <div
        style={{
          ...(fill ? { height: "100dvh" } : {}),
          ...(minHeight !== undefined ? { minHeight: `${minHeight}px` } : {}),
          display: "flex",
          flexDirection: "column",
        }}
      >
        {header}
        {/*
          본문만 가로로 스크롤한다. 창 높이에 맞추는 화면(`fill`)은 이 영역이 남은 높이로 묶여야 안쪽 목록이
          스크롤하고, 그렇지 않은 화면은 내용 높이를 그대로 가져가 페이지가 스크롤한다.
        */}
        <div
          data-slot="artboard-scroll"
          className={fill ? "overflow-x-auto flex-1 min-h-0 flex flex-col" : "overflow-x-auto flex-auto flex flex-col"}
        >
          <div
            data-slot="artboard-body"
            className={fill ? "flex-1 min-h-0" : "flex-auto"}
            style={{ minWidth: `${width}px`, width: "100%", display: "flex", flexDirection: "column" }}
          >
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

/** 통합 작업 화면의 경로 표시 — 「테스트 / TC-001」. */
export function Breadcrumb({ testId }: { testId: string }) {
  return (
    <div className="flex items-center text-ink-2 gap-s2">
      <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3">테스트</span>
      <Pill>{testId}</Pill>
    </div>
  );
}
