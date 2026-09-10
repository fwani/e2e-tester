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
];

/** `reason` 이 비어 있으면 등록이 아니다 (EX-1). 가드와 이 모듈 양쪽이 쓴다. */
export function isRegistered(exception: VisualLanguageException): boolean {
  return exception.reason.trim().length > 0;
}
