/**
 * 공유 파일에서 가져오기 (019 T057 · US2·US3·US5).
 *
 * 이 파일이 지키는 것은 넷이다.
 *
 * 1. **막고 있는 것이 있으면 확정이 잠긴다.** 계획 단계에서 이미 알려 준 사실이므로,
 *    화면이 그것을 무시하면 서버가 409 로 막고 사용자는 이유를 두 번 듣는다.
 * 2. **계획이 낡으면 새 계획으로 갈아 끼운다.** 파일을 다시 고르게 하면 입력이 사라진다.
 * 3. **민감 값을 확정 요청에 싣지 않는다.** 봉인 경로는 하나뿐이다 (C12).
 * 4. **결과가 남은 할 일을 보여 준다.** 「가져왔습니다」만 말하면 받은 사람은 실행이
 *    막힐 때까지 무엇이 빠졌는지 모른다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShareImport } from "../src/pages/ShareImport";

interface Call {
  url: string;
  method: string;
  body: unknown;
}

const VALUE_SECRET = {
  name: "SECRET_LOGIN_PW",
  sensitive: true,
  declared: true,
  usages: [
    { test_id: "TC-001", step_id: "step-02", step_label: "비밀번호 입력", field: "value" },
  ],
  already_stored: false,
  env_provided: false,
  blocks_run: true,
};

const VALUE_PLAIN = {
  name: "LOGIN_ID",
  sensitive: false,
  declared: false,
  usages: [{ test_id: "TC-001", step_id: "step-01", step_label: "아이디 입력", field: "value" }],
  already_stored: null,
  env_provided: false,
  blocks_run: false,
};

const PLAN = {
  plan_id: "plan-1",
  file_name: "team.itbshare.yaml",
  expires_at: "2026-09-23T05:00:00Z",
  target: "new",
  target_project_name: "dev-graphio (2)",
  project_renamed_from: "dev-graphio",
  generator: "itb 0.19.0",
  created_at: "2026-09-23T04:00:00Z",
  groups: [],
  tests: [
    {
      source_id: "TC-001",
      target_id: "TC-007",
      name: "로그인",
      group_prefix: "TC",
      status: "create",
      reason: null,
      renumbered: true,
    },
  ],
  capacity: [],
  required_values: [VALUE_SECRET, VALUE_PLAIN],
  repaired_variables: [{ test_id: "TC-001", name: "LOGIN_ID", sensitive: false }],
  notices: [{ code: "START_URL_CHECK", message: "시작 주소를 확인하세요.", detail: null }],
  blocking: [] as string[],
};

const REPORT = {
  project_root: "/tmp/projects/dev-graphio-2",
  project_name: "dev-graphio (2)",
  project_renamed_from: "dev-graphio",
  created_tests: [
    { target_id: "TC-007", source_id: "TC-001", name: "로그인", group_prefix: "TC" },
  ],
  renumbered: [{ from: "TC-001", to: "TC-007" }],
  created_groups: [],
  skipped: [],
  required_values: [VALUE_SECRET, VALUE_PLAIN],
  repaired_variables: [],
  notices: [],
};

function stub(options: { plan?: unknown; commitStatus?: number; commitBody?: unknown } = {}) {
  const calls: Call[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    let body: unknown = null;
    if (typeof init?.body === "string") body = JSON.parse(init.body);
    calls.push({ url, method: init?.method ?? "GET", body });

    if (url.startsWith("/api/share/import/plan")) {
      return Promise.resolve({
        ok: true,
        status: 201,
        headers: new Headers(),
        text: () => Promise.resolve(JSON.stringify(options.plan ?? PLAN)),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response);
    }

    const status = options.commitStatus ?? 201;
    return Promise.resolve({
      ok: status < 400,
      status,
      headers: new Headers(),
      text: () => Promise.resolve(JSON.stringify(options.commitBody ?? REPORT)),
      clone: () => ({ text: () => Promise.resolve("") }),
    } as unknown as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

const choose = async () => {
  const input = (await screen.findByTestId("share-import-file")) as HTMLInputElement;
  const file = new File(["bundle_version: 1"], "team.itbshare.yaml", { type: "application/yaml" });
  fireEvent.change(input, { target: { files: [file] } });
  await screen.findByTestId("share-import-summary");
};

const commit = () => screen.getByRole("button", { name: /가져오기$/ });

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("공유 파일에서 가져오기", () => {
  it("파일을 고르면 무엇이 들어오는지 보여 준다", async () => {
    stub();
    render(<ShareImport />);
    await choose();
    expect(screen.getByTestId("share-import-summary").textContent).toContain("1건");
  });

  it("바뀔 번호를 강조해 보여 준다", async () => {
    stub();
    render(<ShareImport />);
    await choose();
    const table = screen.getByTestId("share-import-tests");
    expect(table.textContent).toContain("TC-007");
    expect(table.textContent).toContain("번호 변경");
  });

  it("채워야 할 값을 확정 전에 보여 준다", async () => {
    stub();
    render(<ShareImport />);
    await choose();
    const values = screen.getByTestId("share-import-values");
    expect(values.textContent).toContain("SECRET_LOGIN_PW");
    expect(values.textContent).toContain("비밀번호 입력");
    // 저장 위치가 다름을 구분해 보여 준다 (FR-048).
    expect(values.textContent).toContain("봉인 저장");
    expect(values.textContent).toContain("테스트 정의");
  });

  it("선언이 없어 보충한 변수임을 알린다", async () => {
    stub();
    render(<ShareImport />);
    await choose();
    expect(screen.getByTestId("share-import-values").textContent).toContain("보충함");
  });

  it("막고 있는 것이 있으면 확정이 잠긴다", async () => {
    stub({ plan: { ...PLAN, blocking: ["TC 그룹에 자리가 부족합니다."] } });
    render(<ShareImport />);
    await choose();
    expect((commit() as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("share-import-blocking").textContent).toContain("자리가 부족");
  });

  it("민감 값을 확정 요청에 싣지 않는다", async () => {
    const calls = stub();
    render(<ShareImport />);
    await choose();
    fireEvent.click(commit());
    await screen.findByTestId("share-import-done");

    const post = calls.find((c) => c.url === "/api/share/import/commit");
    const sent = (post?.body as { variable_values: Record<string, string> }).variable_values;
    expect(Object.keys(sent)).not.toContain("SECRET_LOGIN_PW");
  });

  it("계획이 낡으면 새 계획으로 갈아 끼운다", async () => {
    const fresh = { ...PLAN, plan_id: "plan-2", tests: [{ ...PLAN.tests[0], target_id: "TC-009" }] };
    stub({
      commitStatus: 409,
      commitBody: {
        error: {
          code: "SHARE_PLAN_STALE",
          message: "그 사이 프로젝트가 바뀌었습니다.",
          detail: { plan: fresh },
        },
      },
    });
    render(<ShareImport />);
    await choose();
    fireEvent.click(commit());

    await waitFor(() => {
      expect(screen.getByTestId("share-import-tests").textContent).toContain("TC-009");
    });
    // 파일 고르기로 되돌아가지 않는다 — 사용자가 한 입력이 사라지면 안 된다.
    expect(screen.queryByTestId("share-import-file")).toBeNull();
  });

  it("끝나면 남은 할 일을 보여 준다", async () => {
    stub();
    render(<ShareImport />);
    await choose();
    fireEvent.click(commit());

    const done = await screen.findByTestId("share-import-done");
    expect(done.textContent).toContain("1건");
    expect(screen.getByTestId("share-import-renumbered").textContent).toContain("TC-001 → TC-007");
    expect(screen.getByText(/민감 값은 묶음에 들어 있지 않습니다/)).toBeTruthy();
  });

  it("열린 프로젝트가 없으면 대상 선택을 보이지 않는다", async () => {
    stub();
    render(<ShareImport hasOpenProject={false} />);
    expect(screen.queryByTestId("share-import-target")).toBeNull();
  });

  it("열린 프로젝트가 있으면 이 프로젝트로 더할 수 있다", async () => {
    stub();
    render(<ShareImport hasOpenProject />);
    const select = (await screen.findByTestId("share-import-target")) as HTMLSelectElement;
    expect(select.value).toBe("current");
  });
});
