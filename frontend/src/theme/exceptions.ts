/**
 * 예외 등록부 — 시각 언어 정본을 벗어나야 하는 값의 **유일한** 등록처. 008 T005.
 *
 * 등록되지 않은 예외는 존재할 수 없다. 가드(`tests/VisualLanguage.test.tsx`)가 이 파일을
 * 읽어 등록된 것만 통과시키므로, 여기 없는 이탈은 검사가 잡는다 (FR-267 · C-11~C-14).
 *
 * ## 왜 코드로 두는가
 *
 * 예외를 문서에 적으면 검사가 읽을 수 없고, 검사가 읽지 못하는 규칙은 지켜지지 않는다 —
 * 그것이 002 라운드가 만든 형태였다. 여기 두면 (1) 검사가 강제하고, (2) 리뷰에 걸리고,
 * (3) `reason` 이 타입 수준에서 필수다.
 *
 * ## 죽은 예외
 *
 * 등록됐으나 해당 파일에서 실제로 쓰이지 않는 항목은 가드가 보고한다 (G-6). 예외가
 * 관성으로 쌓여 규칙을 갉아먹는 것을 막는다.
 */

/** 어느 축의 예외인가. `contracts/visual-language.md` §4 의 축 이름과 같다. */
export type ExceptionAxis = "color" | "inline-style" | "class-name" | "token";

export interface VisualLanguageException {
  /** 저장소 기준 경로. 디렉터리를 가리키면 그 아래 전부에 적용된다. */
  readonly file: string;
  /** 허용할 값 또는 속성 이름. 정규식 문자열이며 줄 전체가 아니라 발견된 값에 맞춘다. */
  readonly pattern: string;
  readonly axis: ExceptionAxis;
  /**
   * **왜 정본으로 표현할 수 없는가.** 빈 문자열은 등록으로 인정되지 않는다.
   *
   * "지금은 시간이 없다" 는 사유가 아니다. 정본이 그 형태를 갖지 못하는 구조적 이유를
   * 적는다. 그런 이유가 없으면 예외가 아니라 아직 안 옮긴 것이다.
   */
  readonly reason: string;
  /** 근거 요구사항 번호. 있으면 적는다. */
  readonly requirement?: string;
}

/**
 * 등록된 예외 전부. **하나뿐이다.**
 *
 * 33개 화면을 옮기는 동안 화면 코드 쪽에서는 예외가 하나도 필요하지 않았다. 처음에는
 * 껍데기의 경계선을 등록해 뒀다 — 층의 구분은 배치 계약(007 `ui-contract` §1-2 ·
 * `lib/layout.ts`)의 관할이라고 봤기 때문이다. 실제로 옮겨 보니 **경계선은 배치가 아니라
 * 시각 언어**였고 정본의 `.hdr`·`.phase`·`.steps` 가 이미 갖고 있었다. 배치 계약이 실제로
 * 정하는 것은 `flex`·`minWidth` 같은 자리의 크기이며 그것들은 애초에 이 가드의 대상이
 * 아니다. 가드의 「죽은 예외」 검사가 그 사실을 알려 줬다 (G-6).
 *
 * 남은 하나는 **정본 쪽**이다 (`token` 축). 확정 디자인의 아트보드는 화면당 한 상태만
 * 그리므로 「겹침이 열린 상태의 뒤 배경」이 어디에도 없다 — 값이 아니라 상태가 정의되지
 * 않은 것이며, 그것이 DC-009 가 다루는 종류다.
 *
 * 이 수가 늘어나면 정본이 실제 화면을 감당하지 못한다는 신호이므로, 예외를 더하기 전에
 * 확정 디자인에 그 형태가 있는지 먼저 본다 (FR-266).
 */
export const VISUAL_LANGUAGE_EXCEPTIONS: readonly VisualLanguageException[] = [
  {
    file: "frontend/src/theme/tokens.css",
    pattern: "^rgba\\(20, 23, 28, 0\\.(28|45)\\)$",
    axis: "token",
    reason:
      "겹치는 판 뒤를 덮는 막. 확정 디자인의 아트보드는 화면당 **한 상태**만 그리므로 " +
      "겹침이 열린 상태의 뒤 배경이 어디에도 없다 — 값이 아니라 상태가 정의되지 않았다 " +
      "(DC-009). 새 색이 아니라 --ink(#14171C)를 투명도로 낮춘 것이며, 그 사실이 " +
      "값에 드러나도록 다른 색을 섞지 않았다. 0.28 은 겹침 640, 0.45 는 화면 전체를 " +
      "덮는 확인 판이다 — 덮는 면적이 클수록 짙게 한다.",
    requirement: "DC-009 · FR-266",
  },
  {
    file: "frontend/src/pages/TestList.tsx",
    pattern:
      "^(gridTemplateColumns|position|top|left|zIndex|visibility|display|flexDirection|gap|padding|width|minWidth|height|minHeight|paddingTop|paddingBottom)$",
    axis: "inline-style",
    reason:
      "세 자리가 **렌더 시점에야 값이 정해진다.** (1) 행 메뉴는 누른 행의 화면 좌표에 " +
      "맞춰 뜬다 — `menuPos` 는 `getBoundingClientRect()` 로 잰 값이고, 자리를 재기 " +
      "전에는 그리지 않는다(그리면 왼쪽 위에서 제자리로 튄다). (2) 표 머리와 행의 " +
      "격자 열은 **같은 상수**를 써야 하고(FR-273 · V-08) 두 곳에 적으면 어긋난다 — " +
      "값을 복제하지 않으려고 상수 참조를 남긴다. (3) 행은 이름 변경·삭제 확인이 " +
      "**안에서 펼쳐질 때만** 높이를 늘린다 — 펼침 여부는 렌더 시점의 상태다.",
    requirement: "015 FR-005 · FR-273 · 013 UC-013-01",
  },
  {
    file: "frontend/src/components/workbench/ActionPalette.tsx",
    pattern: "^(minHeight|height)$",
    axis: "inline-style",
    reason:
      "공통 입력 속성(`common.style`)을 펼친 위에 높이만 덧쓴다. 여러 줄 입력은 48px, " +
      "한 줄은 40px 이며 나머지 속성은 `common` 이 정한다. 펼침(`...common.style`)을 " +
      "클래스로 바꾸려면 `common` 을 쓰는 모든 자리를 함께 옮겨야 하고, 그것은 이 " +
      "기능의 범위를 넘는 구조 변경이다.",
    requirement: "015 FR-005",
  },
  {
    file: "frontend/src/components/design/Chrome.tsx",
    pattern: "^(width|minWidth|height|minHeight|display|flexDirection)$",
    axis: "inline-style",
    reason:
      "아트보드 껍데기의 크기는 **호출부가 정한다** — 화면마다 기준 폭이 다르고 " +
      "(1000·1440), 늘어나는지(`grow`)·화면 높이를 채우는지(`fill`)도 호출부의 " +
      "판단이다. `width={1440} grow` 처럼 값이 props 로 들어오므로 Tailwind 가 " +
      "스캔할 수 있는 정적 클래스로 만들 수 없다. 값을 지어내는 것이 아니라 받아서 " +
      "쓰는 자리라 FR-003 과도 어긋나지 않는다.",
    requirement: "015 FR-005 · 007 FR-218a",
  },
  {
    file: "frontend/src/components/MirrorView.tsx",
    pattern: "^outline-none$",
    axis: "class-name",
    reason:
      "한글 입력을 받는 **보이지 않는** 칸이다 (정본 `.ime-capture`). 미러 위에 겹쳐 " +
      "`opacity:0` · `pointer-events:none` 으로 놓이며, 클릭·끌기·휠은 그대로 뒤의 " +
      "화면으로 간다. 초점은 이 칸이 받지만 **사용자가 보는 초점 자리는 미러 자체**이고, " +
      "여기에 링을 그리면 화면 전체를 두르는 사각형이 뜬다 — 어디에 있는지를 알려주는 " +
      "것이 아니라 가리는 표시가 된다. 정본이 `outline:none` 으로 정한 것을 그대로 " +
      "옮긴 것이며, 015 가 새로 지운 것이 아니다.",
    requirement: "015 FR-010 · SC-008",
  },
];

/** `reason` 이 비어 있으면 등록이 아니다 (EX-1). 가드와 이 모듈 양쪽이 쓴다. */
export function isRegistered(exception: VisualLanguageException): boolean {
  return exception.reason.trim().length > 0;
}
