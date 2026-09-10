/**
 * 초안에서 녹화로 (014 T067 · US3 · FR-030·FR-031).
 *
 * 지키는 것은 둘이다.
 *
 * 1. **지시문 칸이 미리 채워져 있고, 고칠 수 있다.** 빈 칸으로 열리면 사용자는 초안이
 *    비어 있는 줄 알고, 고칠 수 없으면 초안을 지우고 처음부터 쓰게 된다.
 * 2. **새 화면이 아니다.** 기존 「테스트 만들기 → AI」와 같은 화면으로 들어간다 —
 *    원칙 I 이 막으려는 두 번째 작성 경로를 만들지 않는다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ProjectView } from "../src/api/client";
import { ComposeView } from "../src/pages/ComposeView";

const PROJECT: ProjectView = {
  root: "/tmp/p",
  name: "통합",
  default_start_url: "https://example.internal/login",
  browser: "chromium",
  test_id_attribute: "data-testid",
  max_tabs: 10,
  gitignore_present: true,
  secrets_file_present: false,
};

const INSTRUCTION = [
  "제목: 로그인",
  "",
  "설명: 올바른 자격 증명으로 로그인되는지 확인한다",
  "",
  "수행자: 관리자 역할로 수행한다.",
  "",
  "수행 절차:",
  "1. 로그인 화면을 연다",
].join("\n");

function stub(available = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers(),
        text: () => Promise.resolve(JSON.stringify({ available, reason: null })),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response),
    ),
  );
}

function mount(over: Partial<Parameters<typeof ComposeView>[0]> = {}) {
  const props = {
    project: PROJECT,
    onCancel: vi.fn(),
    onRecord: vi.fn(),
    onStartAi: vi.fn(),
    ...over,
  };
  render(<ComposeView {...props} />);
  return props;
}

const instructionBox = () =>
  document.querySelector("textarea") as HTMLTextAreaElement | null;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("초안 없이 들어오면", () => {
  it("지시문 칸이 비어 있다", () => {
    stub();
    mount();
    expect(instructionBox()?.value ?? "").toBe("");
  });

  it("초안 안내가 없다", () => {
    stub();
    const { container } = render(
      <ComposeView
        project={PROJECT}
        onCancel={() => {}}
        onRecord={() => {}}
        onStartAi={() => {}}
      />,
    );
    expect(container.querySelector("[data-from-draft]")).toBeNull();
  });
});

describe("초안에서 들어오면", () => {
  it("지시문이 미리 채워져 있다", () => {
    stub();
    mount({
      initialInstruction: INSTRUCTION,
      fromDraft: { draft_id: "D-0001", name: "로그인" },
    });
    expect(instructionBox()?.value).toBe(INSTRUCTION);
  });

  it("어느 초안에서 왔는지 말한다", () => {
    stub();
    const { container } = render(
      <ComposeView
        project={PROJECT}
        onCancel={() => {}}
        onRecord={() => {}}
        onStartAi={() => {}}
        initialInstruction={INSTRUCTION}
        fromDraft={{ draft_id: "D-0001", name: "로그인" }}
      />,
    );
    expect(container.querySelector('[data-from-draft="D-0001"]')).toBeTruthy();
    expect(screen.getByText(/초안 「로그인」에서 시작합니다/)).toBeTruthy();
  });

  it("저장하면 초안이 사라진다고 미리 알린다", () => {
    stub();
    mount({
      initialInstruction: INSTRUCTION,
      fromDraft: { draft_id: "D-0001", name: "로그인" },
    });
    expect(screen.getByText(/저장하면 이 초안은 사라집니다/)).toBeTruthy();
  });

  it("지시문을 고칠 수 있다", () => {
    // 값이 아니라 **초기값**이다. 고칠 수 없으면 사용자는 초안을 지우고 처음부터 쓴다.
    stub();
    mount({
      initialInstruction: INSTRUCTION,
      fromDraft: { draft_id: "D-0001", name: "로그인" },
    });
    const box = instructionBox();
    expect(box).toBeTruthy();
    expect(box?.readOnly).toBe(false);
    expect(box?.disabled).toBe(false);
  });

  it("모든 칸이 지시문에 담겨 있다", () => {
    stub();
    mount({
      initialInstruction: INSTRUCTION,
      fromDraft: { draft_id: "D-0001", name: "로그인" },
    });
    const value = instructionBox()?.value ?? "";
    expect(value).toContain("제목: 로그인");
    expect(value).toContain("올바른 자격 증명으로 로그인되는지 확인한다");
    expect(value).toContain("관리자 역할로 수행한다.");
    expect(value).toContain("1. 로그인 화면을 연다");
  });

  it("같은 화면이다 — 녹화 갈래도 그대로 있다", () => {
    // 새 작성 경로를 만들지 않았다는 것이 화면에서도 보여야 한다 (원칙 I).
    // 초안에서 왔다고 해서 「직접 녹화」가 사라지지 않는다.
    stub();
    const { container } = render(
      <ComposeView
        project={PROJECT}
        onCancel={() => {}}
        onRecord={() => {}}
        onStartAi={() => {}}
        initialInstruction={INSTRUCTION}
        fromDraft={{ draft_id: "D-0001", name: "로그인" }}
      />,
    );
    expect(container.querySelector('[data-action="record.start"]')).toBeTruthy();
    expect(container.querySelector('[data-action="ai.start"]')).toBeTruthy();
  });
});
