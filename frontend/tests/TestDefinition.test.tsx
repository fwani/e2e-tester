/**
 * 편집 화면 (T169 · 006 T024·T057·T069·T070·T079). FR-016·FR-019 · 006 US1·US3·US4·US5.
 *
 * **실행하지 않고 볼 수 있는가**가 이 화면의 존재 이유였고, 006 이 그것을 편집까지
 * 연장했다. 그래서 이 파일은 세션을 만들지 않고 `GET /api/tests/{id}/definition` 하나로
 * 편집·저장이 되는지를 본다 (FR-182 · SC-302).
 */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EditView } from "../src/pages/EditView";

const verified = (value: string) => ({ value, status: "verified" });

const TEST = {
  dsl_version: 1,
  id: "TC-001",
  name: "로그인",
  authoring_mode: "ai",
  start_url: "https://example.internal/login",
  browser: "chromium",
  ai_instruction: "로그인해서 프로젝트 화면으로 가",
  variables: [{ name: "LOGIN_PASSWORD", value: null, sensitive: true }],
  steps: [
    {
      id: "step-01",
      type: "fill",
      label: "비밀번호 입력",
      author: "ai",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      value: "{{LOGIN_PASSWORD}}",
      target: {
        tag: "input",
        test_id: null,
        role: null,
        accessible_name: null,
        role_status: null,
        label: verified("비밀번호"),
        text: null,
        stable_attr: null,
        css: verified("input#password"),
      },
    },
    {
      id: "step-02",
      type: "click",
      label: "로그인 클릭",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      target: {
        tag: "button",
        test_id: verified("login-submit"),
        role: null,
        accessible_name: null,
        role_status: null,
        label: null,
        text: null,
        stable_attr: null,
        css: verified("button#submit"),
      },
    },
  ],
  created_at: "2026-09-03T00:00:00Z",
  updated_at: "2026-09-03T00:00:00Z",
};

const LOCKED = [
  { field: "steps[].target", reason: "live_browser_required" },
  { field: "steps[].type", reason: "delete_and_insert_instead" },
  { field: "ai_instruction", reason: "record_only" },
];

function view(overrides: Record<string, unknown> = {}) {
  return {
    test: TEST,
    revision: "rev-1",
    editable: true,
    blocked_by: null,
    blocking_session_id: null,
    locked_fields: LOCKED,
    warnings: [],
    ...overrides,
  };
}

/** 요청을 기록하는 가짜 서버. 저장 응답은 새 `revision` 을 준다 (계약 §2). */
function stubFetch(
  first: Record<string, unknown> = view(),
  onSave?: (body: unknown) => Response,
) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      calls.push({ url: String(url), method, body });
      if (method === "PUT") {
        if (onSave) return onSave(body);
        return new Response(
          JSON.stringify({ ...view(), revision: "rev-2" }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify(first), { status: 200 });
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

async function renderScreen(props: Record<string, unknown> = {}) {
  render(<EditView testId="TC-001" onBack={() => undefined} {...props} />);
  await waitFor(() => expect(screen.getByText("비밀번호 입력")).toBeTruthy());
}

/**
 * 조작 식별자로 버튼을 집는다 — 해소 방법 링크와 부딪히지 않는다.
 *
 * 007 통합 뒤 Step 을 대상으로 하는 조작은 **행마다 붙어 있지 않고** Step 패널 바닥
 * 한 자리에 있다 (FR-235). 그래서 "그 Step 을 고른 뒤 그 조작을 누른다" 가 된다 —
 * 일곱 국면에서 같은 방식이다 (FR-227).
 */
const action = (id: string) =>
  document.querySelector(`button[data-action="${id}"]`) as HTMLButtonElement;

/** 그 Step 의 **행**을 고른다. 상세 겹침에도 같은 이름이 있으므로 행으로 좁힌다. */
function selectStep(stepId: string) {
  const row = document.querySelector(`[data-step-row="${stepId}"] button`) as HTMLButtonElement;
  act(() => row.click());
}

/** Step 02(「로그인 클릭」)를 고르고 지운다. */
function deleteSecondStep() {
  selectStep("step-02");
  act(() => action("step.delete").click());
}

describe("편집 화면 — 브라우저 없이 (US1)", () => {
  beforeEach(() => stubFetch());

  it("세션을 만들지 않고 정의를 그린다 (FR-016·FR-182)", async () => {
    const calls = stubFetch();
    await renderScreen();

    expect(screen.getByText("로그인 클릭")).toBeTruthy();
    // 세션 엔드포인트를 부르지 않았다 — 편집도 실행 없이 되어야 한다 (SC-302).
    expect(calls.every((c) => !c.url.includes("/api/sessions"))).toBe(true);
    expect(calls.some((c) => c.url.includes("/definition"))).toBe(true);
  });

  it("민감 값을 표시하지 않고 참조만 보여 준다 (FR-082·FR-212)", async () => {
    await renderScreen();
    expect(screen.getByText("{{LOGIN_PASSWORD}}")).toBeTruthy();
    expect(screen.getByText(/값은 표시되지 않습니다/)).toBeTruthy();
  });

  it("민감 참조 값 칸은 읽기 전용이고 이유를 밝힌다 (FR-213)", async () => {
    await renderScreen();
    selectStep("step-01");
    await waitFor(() => expect(screen.getByLabelText("Step 입력값")).toBeTruthy());

    const input = screen.getByLabelText("Step 입력값") as HTMLInputElement;
    expect(input.disabled).toBe(true);
    expect(screen.getByText(/「비밀 값」 화면에서 바꾸세요/)).toBeTruthy();
  });

  it("지시문을 '실행 대상이 아님' 과 함께 보여 준다 (FR-063·FR-064)", async () => {
    await renderScreen();
    // 지시문의 집은 `ai.compose` 조작 칸이다 (FR-235). 읽기 전용인 **이유**가 그 자리에서
    // 「기록일 뿐」이라고 말한다 — 「끝난 실행이라 못 고친다」로 뭉개면 사용자는 언젠가
    // 고칠 수 있는 것으로 읽는다.
    const field = screen.getByLabelText("AI 지시문") as HTMLTextAreaElement;
    expect(field.disabled).toBe(true);
    expect(
      document.querySelector("[data-disabled-reason='ai.compose']")?.textContent,
    ).toMatch(/실행 대상이 아닙니다/);
  });

  it("Step 을 고르면 후보 우선순위 표를 보여 준다 (FR-019)", async () => {
    await renderScreen();
    selectStep("step-02");
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());
    expect(screen.getByText("사용 중")).toBeTruthy();
  });

  it("결과 화면에서 지목한 Step 을 처음부터 펼친다 (FR-056·FR-180)", async () => {
    render(
      <EditView testId="TC-001" focusStepId="step-02" onBack={() => undefined} />,
    );
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());
  });
});

describe("변경 건수와 되돌리기 (FR-188~FR-190)", () => {
  it("변경할 때마다 건수가 늘고, 같은 Step 의 연속 편집은 하나로 센다", async () => {
    stubFetch();
    await renderScreen();
    selectStep("step-01");
    await waitFor(() => expect(screen.getByLabelText("Step 표시 이름")).toBeTruthy());

    const label = screen.getByLabelText("Step 표시 이름");
    fireEvent.change(label, { target: { value: "비번" } });
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());

    // 같은 Step 을 한 번 더 고쳐도 1건이다 — 사용자가 센 것과 맞아야 한다.
    fireEvent.change(label, { target: { value: "비번 입력" } });
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());

    // 같은 Step 의 다른 필드도 그 Step 의 한 연산으로 합쳐진다 — 여전히 1건이다.
    const timeout = screen.getByLabelText("Step 대기 시간 (ms)");
    fireEvent.change(timeout, { target: { value: "30000" } });
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());

    // 다른 종류의 변경은 따로 센다.
    const name = screen.getByLabelText("테스트 이름");
    fireEvent.change(name, { target: { value: "로그인 흐름" } });
    await waitFor(() => expect(screen.getByText("변경 저장 (2건)")).toBeTruthy());
  });

  it("변경이 없으면 저장 버튼이 비활성이다 (FR-195)", async () => {
    stubFetch();
    await renderScreen();
    const save = screen.getByText("변경 저장") as HTMLButtonElement;
    expect(save.disabled).toBe(true);
  });

  it("개별 되돌리기가 건수를 줄인다 (FR-190)", async () => {
    stubFetch();
    await renderScreen();

    deleteSecondStep();
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    // 삭제는 미리보기에도 반영된다.
    expect(document.querySelector('[data-step-row="step-02"]')).toBeNull();

    act(() => action("edits.revert").click());
    await waitFor(() =>
      expect(document.querySelector('[data-step-row="step-02"]')).not.toBeNull(),
    );
    expect((screen.getByText("변경 저장") as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("저장 (FR-193·FR-194)", () => {
  it("연산 목록을 보내고, 성공을 화면을 옮기지 않고 알린다", async () => {
    const calls = stubFetch();
    await renderScreen();

    deleteSecondStep();
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());

    await waitFor(() => expect(screen.getByText(/저장했습니다 · 로그인/)).toBeTruthy());

    const put = calls.find((c) => c.method === "PUT");
    expect(put).toBeTruthy();
    // **편집 결과가 아니라 연산 목록을 보낸다** (research R3).
    expect(put?.body).toEqual({
      revision: "rev-1",
      edits: [{ op: "delete", step_id: "step-02" }],
    });
    // 화면이 그대로다 — 목록으로 튀지 않는다.
    expect(screen.getByText("비밀번호 입력")).toBeTruthy();
  });

  it("저장 뒤 응답의 새 revision 을 쓴다 — 다시 조회하지 않는다", async () => {
    const calls = stubFetch();
    await renderScreen();

    deleteSecondStep();
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());
    await waitFor(() => expect(screen.getByText(/저장했습니다/)).toBeTruthy());

    deleteSecondStep();
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());
    await waitFor(() => {
      const puts = calls.filter((c) => c.method === "PUT");
      expect(puts).toHaveLength(2);
      expect((puts[1]?.body as { revision: string }).revision).toBe("rev-2");
    });
  });

  it("저장 뒤 그 자리에서 다시 실행을 걸 수 있다 (US2)", async () => {
    stubFetch();
    const onRun = vi.fn();
    render(
      <EditView
        testId="TC-001"
        focusStepId="step-02"
        onRun={onRun}
        onBack={() => undefined}
      />,
    );
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());

    const label = screen.getByLabelText("Step 표시 이름");
    fireEvent.change(label, { target: { value: "로그인" } });
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());
    await waitFor(() => expect(screen.getByText(/저장했습니다/)).toBeTruthy());

    expect(screen.getByText("Step 02부터 실행")).toBeTruthy();
    act(() => screen.getByText("Step 02부터 실행").click());
    expect(onRun).toHaveBeenCalledWith("TC-001", 1);
  });
});

describe("브라우저가 필요한 편집 (US3 · FR-202·FR-203)", () => {
  it("이유와 가는 길을 같은 자리에 준다 — 회색 버튼만 두지 않는다", async () => {
    stubFetch();
    const onOpenBrowserAt = vi.fn();
    await renderScreen({ onOpenBrowserAt });
    selectStep("step-02");
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());

    expect(
      screen.getByText(/살아 있는 화면에서만 다시 집을 수 있습니다/),
    ).toBeTruthy();
    // 「가는 길」 버튼은 **대상 앱 영역**에 하나 있다 (T079 · FR-244).
    act(() => action("browser.openAt").click());
    // 세션이 끝난 뒤 이 Step 으로 돌아오기 위해 id 도 함께 넘긴다 (FR-204).
    expect(onOpenBrowserAt).toHaveBeenCalledWith("TC-001", 1, "step-02");
  });

  it("저장하지 않은 변경이 있으면 먼저 저장한 뒤 세션을 연다 (FR-203)", async () => {
    const calls = stubFetch();
    const onOpenBrowserAt = vi.fn();
    await renderScreen({ onOpenBrowserAt });
    selectStep("step-02");
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());

    const label = screen.getByLabelText("Step 표시 이름");
    fireEvent.change(label, { target: { value: "로그인" } });
    await waitFor(() => expect(screen.getByText("저장하고 열기")).toBeTruthy());
    expect(screen.getByText(/먼저 저장해야 합니다/)).toBeTruthy();

    act(() => screen.getByText("저장하고 열기").click());
    await waitFor(() =>
      expect(onOpenBrowserAt).toHaveBeenCalledWith("TC-001", 1, "step-02"),
    );
    // 저장이 먼저 나갔다 — 두 경로가 같은 Step 을 다르게 들고 있지 않다.
    expect(calls.some((c) => c.method === "PUT")).toBe(true);
  });
});

describe("저장하지 않은 변경 보호 (US4 · FR-208)", () => {
  it("변경이 있으면 이탈 시 건수를 밝힌 확인을 거친다", async () => {
    stubFetch();
    const onBack = vi.fn();
    render(<EditView testId="TC-001" onBack={onBack} />);
    await waitFor(() => expect(screen.getByText("비밀번호 입력")).toBeTruthy());

    deleteSecondStep();
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());

    act(() => action("nav.back").click());
    expect(onBack).not.toHaveBeenCalled();
    expect(screen.getByText("저장하지 않은 변경 1건이 있습니다")).toBeTruthy();

    act(() => screen.getByText("버리고 나가기").click());
    expect(onBack).toHaveBeenCalled();
  });

  it("변경이 없으면 확인 없이 바로 나간다 — 물어볼 것이 없을 때 묻지 않는다", async () => {
    stubFetch();
    const onBack = vi.fn();
    render(<EditView testId="TC-001" onBack={onBack} />);
    await waitFor(() => expect(screen.getByText("비밀번호 입력")).toBeTruthy());

    act(() => action("nav.back").click());
    expect(onBack).toHaveBeenCalled();
    expect(screen.queryByText(/저장하지 않은 변경/)).toBeNull();
  });
});

describe("외부 변경 충돌 (US4 · FR-209)", () => {
  it("두 선택을 주고 각각 무엇을 버리는지 라벨에 적는다", async () => {
    stubFetch(view(), () =>
      new Response(
        JSON.stringify({
          error: {
            code: "DEFINITION_STALE",
            category: "blocked",
            message: "이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.",
            next_action: "다시 읽거나 덮어쓸지 고르세요.",
            detail: { revision: "rev-outside" },
          },
        }),
        { status: 409 },
      ),
    );
    await renderScreen();

    deleteSecondStep();
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());

    await waitFor(() =>
      expect(screen.getByText(/편집을 시작한 뒤에 바뀌었습니다/)).toBeTruthy(),
    );
    expect(screen.getByText("바뀐 내용으로 다시 읽기 (내 편집 1건을 버립니다)")).toBeTruthy();
    expect(screen.getByText("내 편집으로 덮어쓰기 (파일의 변경을 버립니다)")).toBeTruthy();
  });
});

describe("실행 중이면 읽기 전용 (US5 · FR-206)", () => {
  it("화면은 열리고, 컨트롤을 감추지 않고 비활성으로 두고 이유를 붙인다", async () => {
    stubFetch(
      view({
        editable: false,
        blocked_by: "running",
        blocking_session_id: "s-1",
      }),
    );
    const onOpenSession = vi.fn();
    await renderScreen({ onOpenSession });

    /*
      **이유는 두 층으로 온다.** 화면 위의 알림이 한 번 말하고, 잠긴 조작마다 그 자리에서
      다시 말한다 (FR-234). 둘 다 있어야 사용자가 "왜 이 버튼이 안 눌리지" 에 답을
      찾는다 — 알림만 있으면 어떤 조작이 막혔는지 모르고, 이유만 있으면 화면 전체가
      왜 이런지 모른다.
    */
    expect(screen.getAllByText("실행 중이어서 편집할 수 없습니다").length).toBeGreaterThan(0);
    expect(action("session.open")).not.toBeNull();
    expect(document.querySelector("[data-notice='not-editable']")).not.toBeNull();
    // 감추지 않았다 — 비활성이다.
    selectStep("step-02");
    expect(action("step.delete").disabled).toBe(true);
    expect((screen.getByLabelText("테스트 이름") as HTMLInputElement).disabled).toBe(
      true,
    );

    // 그 실행으로 가는 길은 **헤더에 하나** 있다 (FR-235). 알림은 그것을 가리키기만 한다.
    act(() => action("session.open").click());
    expect(onOpenSession).toHaveBeenCalledWith("s-1");
  });
});
