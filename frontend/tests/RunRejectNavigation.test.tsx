/**
 * 실행 거절이 갈 곳을 함께 준다 (005 T024 · FR-126·FR-135 · U-01).
 *
 * 리포트가 "가장 아픈 것" 으로 지목한 왕복이 여기서 끊겼다. 결과 화면에서 재실행을 누르면
 * 409 가 오고, 안내는 **「실행 중인 세션으로 이동한 뒤 중지하세요」** 라고 말했다. 그런데
 * 그 화면에 이동할 수단이 없었다. 사용자는 안내를 읽고도 갈 곳이 없어 멈춘다 —
 * FR-126 이 금지하는 "화면에 없는 조작을 지시하는 안내" 다.
 *
 * 세션 식별자는 **`detail` 로만** 나른다. 사용자에게 보이는 `message`·`next_action` 에
 * 넣으면 화면이 내부 식별자를 읽어 주게 되고, 그것이 U-01 의 다른 절반이었다 (FR-135).
 *
 * 이동 수단은 배너 한 곳에 둔다. 거절은 목록에서도 결과 화면에서도 날 수 있고 배너는 두
 * 화면 **위**에 있다 — 화면마다 두면 한쪽이 빠지고, 빠진 화면에서 같은 결함이 되살아난다.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import { ErrorNotice, describeError } from "../src/components/ErrorNotice";

const ACTIVE_SESSION = "sess-1a2b3c";

/** 서버가 실제로 돌려주는 거절 (contracts/rest-api.md §1). */
function rejection(): ApiError {
  return new ApiError(
    409,
    "SESSION_ALREADY_ACTIVE",
    "TC-002 가 지금 실행 중입니다.",
    { test_id: "TC-002", session_id: ACTIVE_SESSION },
    "blocked",
    "실행 중인 세션으로 이동한 뒤 중지하세요.",
  );
}

describe("거절 본문에서 갈 곳을 꺼낸다 (FR-126)", () => {
  it("`detail.session_id` 가 표시 정보로 넘어온다", () => {
    expect(describeError(rejection()).sessionId).toBe(ACTIVE_SESSION);
  });

  it("사용자 문구에는 세션 식별자가 없다 (FR-135)", () => {
    const info = describeError(rejection());
    expect(info.message).not.toContain(ACTIVE_SESSION);
    expect(info.nextAction).not.toContain(ACTIVE_SESSION);
  });

  it("`detail` 이 없는 오류는 갈 곳이 없다 — 없는 버튼을 만들지 않는다", () => {
    const plain = new ApiError(500, "INTERNAL_ERROR", "서버 오류", {}, "broken", "다시 시도하세요.");
    expect(describeError(plain).sessionId).toBeNull();
  });
});

describe("안내가 지시한 조작이 같은 자리에 있다 (FR-126 · U-01)", () => {
  it("이동 버튼이 배너에 함께 나온다", async () => {
    const onOpen = vi.fn();
    const info = describeError(rejection());
    render(
      <ErrorNotice
        error={info}
        action={{ label: "실행 중인 세션 보기", onClick: () => onOpen(info.sessionId) }}
      />,
    );

    // 사유와 다음 행동이 먼저 있고,
    expect(screen.getByText("TC-002 가 지금 실행 중입니다.")).toBeTruthy();
    expect(screen.getByText("실행 중인 세션으로 이동한 뒤 중지하세요.")).toBeTruthy();

    // 그 행동을 **실제로 할 수 있다.**
    const button = screen.getByRole("button", { name: "실행 중인 세션 보기" });
    await userEvent.click(button);
    expect(onOpen).toHaveBeenCalledWith(ACTIVE_SESSION);
  });

  it("갈 곳이 없는 오류에는 버튼을 붙이지 않는다", () => {
    const { container } = render(
      <ErrorNotice error={describeError(new TypeError("네트워크 실패"))} action={null} />,
    );
    expect(container.querySelector("[data-error-action]")).toBeNull();
  });
});

// ─── 배선 ──────────────────────────────────────────────────────────────────

const APP_SOURCE = (
  import.meta.glob("../src/App.tsx", { query: "?raw", import: "default", eager: true }) as Record<
    string,
    string
  >
)["../src/App.tsx"];

describe("배너가 실제로 그 버튼을 받는다", () => {
  it("`App` 이 `error.sessionId` 로 이동 액션을 만든다", () => {
    expect(APP_SOURCE).toContain("error.sessionId");
    expect(APP_SOURCE).toContain("실행 중인 세션 보기");
  });

  it("이동은 세션을 조회해 실행 화면으로 간다 — 목록으로 튕기지 않는다", () => {
    expect(APP_SOURCE).toMatch(/sessions\s*\n?\s*\.get\(sessionId\)/);
    expect(APP_SOURCE).toContain('setScreen({ name: "runner", session })');
  });
});
