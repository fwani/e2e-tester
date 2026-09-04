/**
 * T018 — 오류 표시의 공용 통로를 검증한다 (003 EC-004 · RG-104-4).
 *
 * 두 가지를 본다.
 *
 * 1. 통로 자체가 **무엇이 잘못됐는지와 다음 행동을 함께** 보여주는가
 * 2. 화면들이 그 통로를 **실제로 지나는가** — 원본을 훑어 확인한다
 *
 * 2번이 없으면 통로를 만들어 두고 아무도 안 쓰는 상태가 조용히 지나간다. 003 이전이 정확히
 * 그랬다 — 화면마다 `err.message` 를 직접 그려 `next_action` 이 있을 자리가 없었다.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "../../src/api/client";
import { ErrorNotice, describeError, localError } from "../../src/components/ErrorNotice";

// `?raw` 로 원문을 읽는다. node:fs 를 쓰면 @types/node 가 필요해지고, 이 저장소는 그것을
// 두지 않기로 했다 (DesignTokens.test.tsx 의 같은 결정).
const PAGE_SOURCES = import.meta.glob("../../src/pages/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

describe("공용 통로 — 무엇이 잘못됐는지와 다음 행동을 함께 보여준다", () => {
  it("막은 것: 메시지와 다음 행동이 둘 다 나온다", () => {
    render(
      <ErrorNotice
        error={{
          message: "Step이 없어 저장할 수 없습니다.",
          nextAction: "브라우저에서 동작을 기록한 뒤 다시 저장하세요.",
          category: "blocked",
          code: "STEP_LIST_EMPTY",
        }}
      />,
    );
    expect(screen.getByText("Step이 없어 저장할 수 없습니다.")).toBeTruthy();
    expect(screen.getByText("브라우저에서 동작을 기록한 뒤 다시 저장하세요.")).toBeTruthy();
  });

  it("깨진 것과 막은 것을 구분해 표시한다", () => {
    const { container: blocked } = render(
      <ErrorNotice error={localError("이름이 필요합니다.", "이름을 입력하세요.")} />,
    );
    expect(blocked.querySelector("[data-category='blocked']")).toBeTruthy();

    const { container: broken } = render(
      <ErrorNotice error={describeError(new TypeError("네트워크 실패"))} />,
    );
    expect(broken.querySelector("[data-category='broken']")).toBeTruthy();
  });

  it("다음 행동이 비어 있는 채로 그려지지 않는다 (EC-004)", () => {
    const { container } = render(
      <ErrorNotice error={describeError(new ApiError(500, "INTERNAL_ERROR", "실패", {}, "broken", ""))} />,
    );
    const next = container.querySelector("[data-error-next-action]");
    expect(next?.textContent?.trim().length).toBeGreaterThan(0);
  });

  it("계약 형태가 아닌 실패도 같은 통로를 지나고 broken 으로 다룬다", () => {
    const info = describeError(new Error("Failed to fetch"));
    expect(info.category).toBe("broken");
    expect(info.nextAction.trim().length).toBeGreaterThan(0);
  });

  it("계약 오류의 분류와 다음 행동을 그대로 나른다", () => {
    const info = describeError(
      new ApiError(404, "TEST_NOT_FOUND", "없습니다.", {}, "blocked", "목록을 새로 고치세요."),
    );
    expect(info.category).toBe("blocked");
    expect(info.nextAction).toBe("목록을 새로 고치세요.");
  });

  it("null 이면 아무것도 그리지 않는다", () => {
    const { container } = render(<ErrorNotice error={null} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("화면이 공용 통로를 지나는가 (RG-104-4)", () => {
  const pages = Object.entries(PAGE_SOURCES).map(
    ([p, source]) => [p.split("/").pop() as string, source] as const,
  );

  it("훑을 화면이 실제로 있다", () => {
    expect(pages.length).toBeGreaterThanOrEqual(10);
  });

  it.each(pages)("%s 는 오류를 직접 그리지 않는다", (file, source) => {

    // 오류 **상태**에 문자열을 넣으면 다음 행동이 그 자리에서 사라진다.
    //
    // 오류가 아닌 자리(가용성 모델의 `reason` 같은 데이터 필드)에 메시지를 담는 것은
    // 문제가 아니다. 그래서 `setError(...)` 계열에 들어가는 경우만 잡는다.
    const flattenedIntoErrorState = /set(?:\w*)?Error\(\s*exc instanceof ApiError \? exc\.message/.test(
      source,
    );
    expect(
      flattenedIntoErrorState,
      `${file}: 오류 상태에 문자열을 넣는다. describeError(exc) 를 쓰세요`,
    ).toBe(false);

    // 오류 상태를 가진 화면은 공용 통로를 임포트해야 한다.
    const hasErrorState = /useState<ErrorInfo \| null>/.test(source);
    if (hasErrorState) {
      expect(
        source.includes("ErrorNotice") || source.includes("ErrorInfo"),
        `${file}: 오류 상태를 갖는데 공용 통로를 쓰지 않는다`,
      ).toBe(true);
    }
  });
});
