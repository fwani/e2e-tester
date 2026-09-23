/**
 * 값 인계 화면 (019 T070 · US3).
 *
 * 이 파일이 지키는 것은 셋이다.
 *
 * 1. **어디에 쓰이는지 함께 보인다.** 이름만으로는 무엇을 넣을지 모른다 (FR-040).
 * 2. **저장 위치가 구분된다.** 민감한 것은 봉인, 아닌 것은 정의 (FR-048).
 * 3. **목록이 누르기 전에 알린다.** 실행을 눌러 409 를 받고서야 아는 것과는 다르다 (FR-044).
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ShareImportDone } from "../src/pages/ShareImport";
import { TestList } from "../src/pages/TestList";

const SECRET = {
  name: "SECRET_LOGIN_PW",
  sensitive: true,
  declared: true,
  usages: [
    { test_id: "TC-007", step_id: "step-02", step_label: "비밀번호 입력", field: "value" },
  ],
  already_stored: false,
  env_provided: false,
  blocks_run: true,
};

const PLAIN = {
  name: "LOGIN_ID",
  sensitive: false,
  declared: false,
  usages: [{ test_id: "TC-007", step_id: "step-01", step_label: "아이디 입력", field: "value" }],
  already_stored: null,
  env_provided: false,
  blocks_run: false,
};

const REPORT = {
  project_root: "/tmp/p",
  project_name: "받은 프로젝트",
  project_renamed_from: null,
  created_tests: [
    { target_id: "TC-007", source_id: "TC-001", name: "로그인", group_prefix: "TC" },
  ],
  renumbered: [],
  created_groups: [],
  skipped: [],
  required_values: [SECRET, PLAIN],
  repaired_variables: [],
  notices: [],
};

const LISTING = (missing: string[]) => ({
  counts: { total: 1, pass: 0, fail: 0 },
  groups: [],
  tests: [
    {
      id: "TC-001",
      name: "로그인",
      step_count: 2,
      authoring_mode: "record",
      outcome: null,
      last_run_at: null,
      failure_summary: null,
      group_prefix: "TC",
      missing_secrets: missing,
    },
  ],
  problems: [],
});

function stubList(missing: string[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.startsWith("/api/groups") ? { groups: [] } : LISTING(missing);
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers(),
        text: () => Promise.resolve(JSON.stringify(body)),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response);
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("가져온 뒤 채워야 할 값", () => {
  const mount = () =>
    render(
      <ShareImportDone report={REPORT} values={{}} onChange={() => {}} />,
    );

  it("어느 테스트의 어느 스텝에서 쓰이는지 보여 준다", () => {
    mount();
    const table = screen.getByTestId("share-import-values");
    expect(table.textContent).toContain("TC-007");
    expect(table.textContent).toContain("비밀번호 입력");
  });

  it("민감한 것과 아닌 것의 저장 위치를 구분한다", () => {
    mount();
    const table = screen.getByTestId("share-import-values");
    expect(table.textContent).toContain("봉인 저장");
    expect(table.textContent).toContain("테스트 정의");
  });

  it("채워야 실행된다는 사실을 민감 값에만 붙인다", () => {
    mount();
    const rows = screen.getByTestId("share-import-values").textContent ?? "";
    // 민감 값 줄에만 붙는다 — 빈 비민감 값은 막지 않는다 (FR-044).
    expect(rows.split("LOGIN_ID")[0]).toContain("채워야 실행됩니다");
  });

  it("비민감 값은 그 자리에서 입력할 수 있다", () => {
    mount();
    expect(screen.getByTestId("share-import-value-LOGIN_ID")).toBeTruthy();
    // 민감 값은 이 화면에서 입력받지 않는다 — 봉인 경로가 따로 있다.
    expect(screen.queryByTestId("share-import-value-SECRET_LOGIN_PW")).toBeNull();
  });

  it("민감 값을 채우러 갈 경로를 안내한다", () => {
    mount();
    const link = screen.getByRole("link", { name: "민감 값 채우러 가기" });
    expect(link.getAttribute("href")).toBe("/secrets");
  });

  it("입력한 값이 화면에 평문으로 되돌아오지 않는다", () => {
    // 민감 값은 애초에 이 화면이 받지 않으므로 되돌아올 자리가 없다 (FR-043).
    mount();
    expect(screen.queryByDisplayValue(/비밀번호/)).toBeNull();
  });
});

describe("목록의 값 필요 표시", () => {
  const mount = () =>
    render(
      <TestList
        projectName="받은 프로젝트"
        onCreate={() => {}}
        onRun={() => {}}
        pendingRunId={null}
        onOpenResult={() => {}}
        activeSessions={[]}
      />,
    );

  it("값이 비면 누르기 전에 알린다", async () => {
    stubList(["SECRET_LOGIN_PW"]);
    mount();
    const badge = await screen.findByTestId("needs-values-TC-001");
    expect(badge.textContent).toContain("값 필요");
    expect(badge.textContent).toContain("SECRET_LOGIN_PW");
  });

  it("값이 차 있으면 표시하지 않는다", async () => {
    stubList([]);
    mount();
    await screen.findByText("로그인");
    expect(screen.queryByTestId("needs-values-TC-001")).toBeNull();
  });
});
