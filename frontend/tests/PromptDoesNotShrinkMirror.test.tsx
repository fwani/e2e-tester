/**
 * 2026-09-09 사용자 보고 — **파일 업로드 후에 미러 화면이 작아진다.**
 *
 * 원인은 한 줄이었다. `BrowserFrame` 의 본문 컨테이너에 `flexDirection` 이 없어 기본값
 * `row` 였고, 그 자리에는 브라우저 요구 패널과 미러가 **함께** 들어온다
 * (`SessionScreen` 의 `mirror`). 그래서 파일 선택 요구가 뜨는 순간 패널이 미러 위가
 * 아니라 왼쪽 옆에 서서 자기 콘텐츠 폭을 가져갔다.
 *
 * `SessionScreen` 의 그 자리 주석은 010 FR-338·FR-339 를 근거로 「브라우저 요구를 **미러
 * 바로 위에** 둔다」라고 적고 있었다 — 의도는 처음부터 세로였고 한 줄이 어긋나 있었다.
 *
 * **왜 검사가 못 잡았나.** `BrowserPrompt.test.tsx` 는 패널을 단독으로 `render` 해 내용만
 * 봤다. 껍데기 안에 넣은 배치를 아무도 재지 않았으므로, 방향이 뒤집혀도 초록이었다.
 * 이 파일이 그 자리를 잰다.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { BrowserFrame } from "../src/components/design/BrowserFrame";

afterEach(cleanup);

describe("브라우저 요구는 미러 위에 쌓인다 — 옆에 서지 않는다", () => {
  function body(): HTMLElement {
    /*
      본문 컨테이너를 찾는 법: 머리 띠(`.pane-hd`)의 **다음 형제**다. 클래스나 순번으로
      찾으면 껍데기가 바뀔 때 검사가 조용히 다른 것을 재게 된다.
    */
    // 015 — `.pane-hd` 가 유틸리티로 해체돼 셀렉터로 찾을 수 없다. 자리 표식을 붙였다.
    const head = document.querySelector("[data-frame-head]");
    expect(head, "브라우저 껍데기의 머리 띠가 없다").not.toBeNull();
    const next = head!.nextElementSibling as HTMLElement | null;
    expect(next, "머리 띠 다음에 본문 컨테이너가 없다").not.toBeNull();
    return next!;
  }

  /**
   * 본문이 쌓이는 방향 — **인라인과 클래스 두 표기를 모두 읽는다** (015).
   *
   * 이 검사가 묻는 것은 「패널이 미러 옆에 서지 않는가」다. 가로로 서면 패널이 자기
   * 콘텐츠 폭을 가져가고 미러가 눌린다 — 그것이 사용자가 본 화면이다. 표기가 바뀌어도
   * 그 질문은 그대로다.
   */
  function stack(el: HTMLElement): string {
    if (el.style.flexDirection !== "") return el.style.flexDirection;
    if (/\bflex-col\b/.test(el.className)) return "column";
    if (/\bflex-row\b/.test(el.className)) return "row";
    return "";
  }

  it("본문이 세로로 쌓인다 (flexDirection: column)", () => {
    render(
      <BrowserFrame url="https://x.test/" badge={{ label: "MIRROR", tone: "" }}>
        <div data-testid="prompt">요구 패널</div>
        <div data-testid="mirror">미러</div>
      </BrowserFrame>,
    );
    /*
      **`row` 가 기본값이므로 빈 값도 실패로 본다.** `expect(...).not.toBe("row")` 로
      두면 값이 비었을 때 통과하는데, 비어 있다는 것이 바로 이 결함의 형태였다.
    */
    expect(stack(body()), "본문이 가로로 선다 — 패널이 미러 폭을 가져간다").toBe("column");
  });

  it("요구 패널이 뜬 동안에도 미러가 폭을 잃지 않는다", () => {
    /*
      세로로 쌓이면 두 자녀는 **같은 폭**을 받는다. 가로로 서면 패널이 자기 콘텐츠 폭을
      가져가고 미러는 남은 폭으로 눌린다 — 그것이 사용자가 본 화면이다.

      jsdom 은 실제 배치를 계산하지 않으므로 폭을 재는 대신 **배치 규칙**을 잰다. 규칙이
      맞으면 폭은 브라우저가 맞춘다.
    */
    render(
      <BrowserFrame url="https://x.test/" badge={{ label: "MIRROR", tone: "" }}>
        <div data-testid="prompt">파일을 고르세요</div>
        <div data-testid="mirror">미러</div>
      </BrowserFrame>,
    );
    const container = body();
    expect(container.style.display !== "" ? container.style.display : container.className)
      .toMatch(/flex/);
    expect(stack(container), "본문이 가로로 선다 — 패널이 미러 폭을 가져간다").toBe("column");
    // 두 자녀가 같은 컨테이너에 있다 — 패널이 미러 밖으로 나가 있지 않다.
    expect(container.querySelector('[data-testid="prompt"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="mirror"]')).not.toBeNull();
  });

  it("높이를 잃지 않는다 — minHeight 0 이 남아 있다", () => {
    // `column` 으로 바꾸면서 `minHeight: 0` 을 잃으면 미러가 세로로 넘쳐 잘린다.
    render(
      <BrowserFrame url="https://x.test/" badge={{ label: "MIRROR", tone: "" }}>
        <div>미러</div>
      </BrowserFrame>,
    );
    // 015 — 클래스로 바뀌었다. `min-h-0` 이 `minHeight: 0` 과 같은 뜻이다.
    const el = body();
    expect(
      el.style.minHeight !== "" ? el.style.minHeight : /\bmin-h-0\b/.test(el.className) ? "0" : "없음",
      "minHeight 0 을 잃으면 미러가 세로로 넘쳐 잘린다",
    ).toBe("0");
  });
});
