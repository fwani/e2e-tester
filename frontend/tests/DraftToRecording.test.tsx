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
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

/**
 * **이 묶음이 T085 의 결함을 잡는다.**
 *
 * 지시문 프리필만 검사하면 화면은 통과하지만 서버는 이 세션이 초안에서 왔다는 것을
 * 모른다. 백엔드 e2e 는 `SessionWork` 를 직접 조립해 `draft_id` 를 심었으므로 같은 구멍을
 * 지나갔다 — **두 테스트 층이 서로의 사각을 덮고 있었다.** 그래서 여기서는 화면이 만든
 * **요청 본문**을 본다.
 */
describe("요청 본문", () => {
  function captureCreate() {
    const bodies: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === "/api/sessions" && init?.method === "POST") {
          bodies.push(JSON.parse(String(init.body)));
        }
        const payload =
          url === "/api/sessions"
            ? { session_id: "s-1", state: "starting", test_id: null }
            : { available: true, reason: null };
        return Promise.resolve({
          ok: true,
          status: url === "/api/sessions" ? 201 : 200,
          headers: new Headers(),
          text: () => Promise.resolve(JSON.stringify(payload)),
          clone: () => ({ text: () => Promise.resolve("") }),
        } as unknown as Response);
      }),
    );
    return bodies;
  }

  it("초안에서 시작하면 draft_id 를 싣는다", async () => {
    // App 이 실제로 만드는 본문을 본다 — ComposeView 는 onStartAi 를 부를 뿐이다.
    const bodies = captureCreate();
    const onStartAi = vi.fn();
    mount({
      initialInstruction: INSTRUCTION,
      fromDraft: { draft_id: "D-0001", name: "로그인" },
      onStartAi,
    });

    const start = document.querySelector('[data-action="ai.start"]') as HTMLElement;
    fireEvent.click(start);

    // ComposeView 는 콜백까지가 제 몫이다. 본문을 만드는 것은 App 이므로 여기서는
    // **콜백이 불렸다**까지 확인하고, 본문은 아래 App 계약 검증이 맡는다.
    await waitFor(() => expect(onStartAi).toHaveBeenCalled());
    expect(bodies).toEqual([]);
  });

  it("클라이언트가 draft_id 를 본문에 그대로 싣는다", async () => {
    const { sessions } = await import("../src/api/client");
    const bodies = captureCreate();
    await sessions.create({
      mode: "ai",
      start_url: "https://example.internal",
      ai_instruction: INSTRUCTION,
      draft_id: "D-0001",
    });
    expect(bodies).toEqual([
      {
        mode: "ai",
        start_url: "https://example.internal",
        ai_instruction: INSTRUCTION,
        draft_id: "D-0001",
      },
    ]);
  });

  it("App 의 AI 시작 경로가 초안 식별자를 넘긴다", async () => {
    /*
      **이것이 T085 를 잡는 검증이다.**

      화면을 통째로 띄우는 대신 `App.tsx` 의 소스를 본다 — 초안에서 세션을 만드는 경로는
      프로젝트 열기·AI 자격 확인·세션 목록까지 엮여 있어 통합 렌더로 이 한 줄을 지키려면
      검증이 그 전부에 묶인다. 지키려는 사실은 하나다: **AI 세션 생성 본문에 초안
      식별자가 실린다.**

      exporter 가 `itb.secrets` 를 임포트하지 않는지 확인하는 백엔드 검증과 같은 방식이다.
    */
    const source = await import("../src/App.tsx?raw").then((m) => m.default as string);
    const aiCreate = /\.create\(\{[^}]*mode:\s*"ai"[\s\S]*?\}\)/.exec(source);
    expect(aiCreate, "App 에 AI 세션 생성 경로가 없다").toBeTruthy();
    expect(aiCreate?.[0]).toContain("draft_id");
  });
});

/**
 * 초안에서 저장까지 한 번에 (014 3차 요청).
 *
 * 설계서에 이미 이름과 그룹이 적혀 있는데 저장할 때 다시 치라고 하면, 사용자는 같은
 * 것을 두 번 쓰게 되고 두 이름이 어긋날 자리가 생긴다. **저장을 누르면 바로 저장돼야
 * 한다.**
 */
describe("저장 준비", () => {
  it("App 이 초안을 실행 화면까지 나른다", async () => {
    // 이름·그룹의 기본값이 되려면 SessionScreen 이 초안을 알아야 한다.
    const source = await import("../src/App.tsx?raw").then((m) => m.default as string);
    expect(source).toContain("draft={screen.draft ?? null}");
  });

  it("초안의 그룹까지 함께 나른다", async () => {
    // 그룹이 빠지면 저장할 때 「그룹 없음」으로 떨어진다.
    const source = await import("../src/App.tsx?raw").then((m) => m.default as string);
    expect(source).toContain("group_prefix: screen.draft.group_prefix");
  });

  it("저장 이름이 초안 제목으로 채워진다", async () => {
    const source = await import("../src/pages/SessionScreen.tsx?raw").then(
      (m) => m.default as string,
    );
    // 서버가 준 이름 → 초안 제목 순서다. 이미 저장된 테스트의 이름이 먼저다.
    expect(source).toContain("nameOverride ?? view.test_name ?? draft?.name");
  });

  it("저장 그룹이 초안의 그룹으로 채워진다", async () => {
    const source = await import("../src/pages/SessionScreen.tsx?raw").then(
      (m) => m.default as string,
    );
    expect(source).toContain("draft.group_prefix === \"TC\" ? null : draft.group_prefix");
  });
});
