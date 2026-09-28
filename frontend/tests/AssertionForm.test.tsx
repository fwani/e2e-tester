/**
 * 검증 추가 폼 (021 T038 · FR-020·FR-026 · US3).
 *
 * 어휘가 늘어난 것을 **고르는 사람이 실제로 쓸 수 있는가**를 본다. `wording` 쪽 어휘
 * 완전성은 `AssertionSummary.test.tsx` 가 따로 세우므로, 여기서는 폼의 동작만 본다 —
 * 무엇이 보이고 사라지는가, 무엇이 서버로 가는가.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssertionForm } from "../src/components/AssertionForm";
import { ASSERTION_KIND_LABEL, MATCH_MODE_LABEL } from "../src/lib/wording";

function setup() {
  const onSubmit = vi.fn();
  render(<AssertionForm onSubmit={onSubmit} />);
  return { onSubmit };
}

function pickKind(kind: keyof typeof ASSERTION_KIND_LABEL) {
  fireEvent.click(screen.getByRole("radio", { name: new RegExp(ASSERTION_KIND_LABEL[kind]) }));
}

describe("여섯 종류를 고를 수 있다 (FR-020)", () => {
  it("상태 검증 둘이 목록에 있다", () => {
    setup();
    expect(screen.getByText(ASSERTION_KIND_LABEL.enabled)).toBeTruthy();
    expect(screen.getByText(ASSERTION_KIND_LABEL.disabled)).toBeTruthy();
  });

  it("범위 외 기능을 비활성 항목으로 보여 주지 않는다", () => {
    // 없는 기능을 회색으로 보여 주는 것은 「곧 생긴다」는 약속처럼 읽힌다.
    setup();
    for (const label of ["체크", "읽기 전용", "개수"]) {
      expect(screen.queryByText(new RegExp(label))).toBeNull();
    }
  });
});

describe("값을 쓰지 않는 종류에서는 값 칸이 사라진다", () => {
  it("상태 검증을 고르면 비교 값과 비교 방식이 함께 사라진다", () => {
    setup();
    expect(screen.queryByLabelText(/비교 값/)).toBeTruthy();

    pickKind("disabled");

    // 비워 두면 「적어도 되는가」를 사용자가 다시 판단해야 하고, 서버는 값을 받으면
    // 거절한다. 보이지 않는 편이 정직하다.
    expect(screen.queryByLabelText(/비교 값/)).toBeNull();
    expect(screen.queryByText(MATCH_MODE_LABEL.not_contains)).toBeNull();
  });

  it("텍스트로 돌아오면 다시 나타난다", () => {
    setup();
    pickKind("disabled");
    pickKind("text");
    expect(screen.queryByLabelText(/비교 값/)).toBeTruthy();
  });
});

describe("부정 비교의 안내 (FR-026)", () => {
  it("긍정 비교에서는 보이지 않는다", () => {
    setup();
    pickKind("text");
    expect(screen.queryByTestId("negated-match-note")).toBeNull();
  });

  it("부정 비교를 고르면 나타난다", () => {
    setup();
    pickKind("text");
    fireEvent.click(screen.getByRole("radio", { name: MATCH_MODE_LABEL.not_contains }));
    expect(screen.getByTestId("negated-match-note")).toBeTruthy();
  });
});

describe("서버로 보내는 것", () => {
  it("상태 검증은 값도 부정 비교도 싣지 않는다", () => {
    const { onSubmit } = setup();
    pickKind("disabled");
    fireEvent.change(screen.getByLabelText(/대상 요소/), {
      target: { value: "[data-testid=delete-auto]" },
    });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const body = onSubmit.mock.calls[0][0];
    expect(body.kind).toBe("disabled");
    expect(body.value).toBeNull();
    expect(body.match).toBe("equals");
  });

  it("부정 텍스트 검증은 값과 비교 방식을 함께 싣는다", () => {
    const { onSubmit } = setup();
    pickKind("text");
    fireEvent.change(screen.getByLabelText(/비교 값/), { target: { value: "오류" } });
    fireEvent.click(screen.getByRole("radio", { name: MATCH_MODE_LABEL.not_contains }));
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    const body = onSubmit.mock.calls[0][0];
    expect(body).toMatchObject({ kind: "text", value: "오류", match: "not_contains" });
  });
});
