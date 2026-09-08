/**
 * 프로젝트 선택 화면. DR-001 ~ DR-009 · SC-101·SC-102.
 *
 * 이 화면을 통과하지 못하면 제품의 나머지 전부에 도달할 수 없다. 이전 판은 절대 경로를
 * 손으로 넣게 했고, 서버의 실행 경로를 사용자가 알 수 없어 아무도 통과하지 못했다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectListItem } from "../src/api/client";
import { ProjectSetup } from "../src/pages/ProjectSetup";

const managed: ProjectListItem = {
  root: "/home/me/.local/share/itb/projects/data-platform",
  name: "데이터 플랫폼",
  last_opened_at: "2026-09-04T02:11:00Z",
  origin: "managed",
  accessible: true,
  unavailable_reason: null,
};

const gone: ProjectListItem = {
  root: "/home/me/elsewhere/moved",
  name: "옮겨진 것",
  last_opened_at: "2026-09-01T00:00:00Z",
  origin: "external",
  accessible: false,
  unavailable_reason: "디렉터리가 없습니다. 옮겨졌거나 삭제된 것으로 보입니다.",
};

/** 응답을 경로별로 흉내 낸다. 실제 계약 형태를 지킨다. */
function stubFetch(routes: Record<string, unknown>, status = 200) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const key = Object.keys(routes).find((k) => url.startsWith(k));
    const body = key === undefined ? null : routes[key];
    return Promise.resolve({
      ok: status < 400,
      status: body === null ? 404 : status,
      text: () => Promise.resolve(body === null ? "" : JSON.stringify(body)),
    } as Response);
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", stubFetch({ "/api/project/list": { projects: [], warning: null } }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ProjectSetup — 경로 입력 제거 (DR-001·SC-102)", () => {
  it("경로를 타이핑하는 입력란이 하나도 없다", async () => {
    render(<ProjectSetup onOpened={() => {}} />);
    await screen.findByText("아직 프로젝트가 없습니다");

    // 이전 판의 라벨. 다시 생기면 SC-102 가 깨진다.
    expect(screen.queryByLabelText(/프로젝트 디렉터리/)).toBeNull();
    expect(screen.queryByText(/절대 경로/)).toBeNull();
    for (const input of Array.from(document.querySelectorAll("input"))) {
      expect(input.getAttribute("placeholder") ?? "").not.toMatch(/^\/|경로/);
    }
  });

  it("새로 만들기 양식에도 위치 입력이 없다", async () => {
    render(<ProjectSetup onOpened={() => {}} />);
    fireEvent.click(await screen.findByText("+ 새 프로젝트 만들기"));

    expect(screen.getByLabelText("프로젝트 이름")).toBeTruthy();
    expect(screen.getByLabelText("기본 시작 URL")).toBeTruthy();
    expect(screen.queryByLabelText(/디렉터리|경로|위치/)).toBeNull();
  });
});

describe("ProjectSetup — 목록 (DR-002·DR-003)", () => {
  it("기존 프로젝트를 이름과 위치로 보여준다", async () => {
    vi.stubGlobal(
      "fetch",
      stubFetch({ "/api/project/list": { projects: [managed], warning: null } }),
    );
    render(<ProjectSetup onOpened={() => {}} />);

    expect(await screen.findByText("데이터 플랫폼")).toBeTruthy();
    expect(screen.getByText(managed.root)).toBeTruthy();
    expect(screen.getByText("열기")).toBeTruthy();
  });

  it("항목을 고르면 경로 입력 없이 열린다", async () => {
    const opened = vi.fn();
    vi.stubGlobal(
      "fetch",
      stubFetch({
        "/api/project/list": { projects: [managed], warning: null },
        "/api/project/open": { root: managed.root, name: managed.name },
      }),
    );
    render(<ProjectSetup onOpened={opened} />);

    fireEvent.click(await screen.findByText("열기"));

    await waitFor(() => expect(opened).toHaveBeenCalledOnce());
  });

  it("프로젝트가 없으면 두 갈래를 제시한다", async () => {
    render(<ProjectSetup onOpened={() => {}} />);

    expect(await screen.findByText("+ 새 프로젝트 만들기")).toBeTruthy();
    expect(screen.getByText("기존 프로젝트 열기")).toBeTruthy();
  });
});

describe("ProjectSetup — 접근 불가 항목 (DR-009)", () => {
  it("조용히 빼지 않고 사유와 함께 표시한다", async () => {
    vi.stubGlobal("fetch", stubFetch({ "/api/project/list": { projects: [gone], warning: null } }));
    render(<ProjectSetup onOpened={() => {}} />);

    expect(await screen.findByText("옮겨진 것")).toBeTruthy();
    expect(screen.getByText("열 수 없음")).toBeTruthy();
    expect(screen.getByText(gone.unavailable_reason!)).toBeTruthy();
  });

  it("치우기가 자산 삭제가 아님을 밝힌다", async () => {
    vi.stubGlobal("fetch", stubFetch({ "/api/project/list": { projects: [gone], warning: null } }));
    render(<ProjectSetup onOpened={() => {}} />);

    const button = await screen.findByText("목록에서 치우기");
    expect(button.getAttribute("title")).toContain("디스크의 파일은 지우지 않습니다");
  });
});

describe("ProjectSetup — 만든 위치 알림 (DR-006)", () => {
  it("만들고 나면 어디에 만들어졌는지 보여준 뒤 들어간다", async () => {
    const opened = vi.fn();
    vi.stubGlobal(
      "fetch",
      stubFetch({
        "/api/project/list": { projects: [], warning: null },
        "/api/project/create": { root: managed.root, name: "새 프로젝트" },
      }),
    );
    render(<ProjectSetup onOpened={opened} />);

    fireEvent.click(await screen.findByText("+ 새 프로젝트 만들기"));
    fireEvent.change(screen.getByLabelText("프로젝트 이름"), { target: { value: "새 프로젝트" } });
    fireEvent.change(screen.getByLabelText("기본 시작 URL"), {
      target: { value: "https://example.internal/login" },
    });
    fireEvent.click(screen.getByText("만들기 →"));

    // 위치를 사용자가 정하지 않았으므로, 모른 채 넘어가면 다음에 찾을 수 없다.
    expect(await screen.findByText(managed.root)).toBeTruthy();
    expect(opened).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("시작하기 →"));
    await waitFor(() => expect(opened).toHaveBeenCalledOnce());
  });
});

describe("ProjectSetup — 폴더 선택기 (DR-005)", () => {
  it("홈 하위를 탐색하고 프로젝트인 항목을 구분한다", async () => {
    vi.stubGlobal(
      "fetch",
      stubFetch({
        "/api/project/list": { projects: [], warning: null },
        "/api/fs/browse": {
          path: "/home/me",
          parent: null,
          entries: [
            { name: "work", path: "/home/me/work", is_project: false },
            { name: "proj", path: "/home/me/proj", is_project: true },
          ],
        },
      }),
    );
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByText("기존 프로젝트 열기"));

    expect(await screen.findByText("📁 work")).toBeTruthy();
    expect(screen.getByText("📁 proj")).toBeTruthy();
    // "프로젝트" 는 화면 제목에도 있다. 항목에 붙은 상태 표식을 본다.
    // 008 — 정본의 이름은 `.chip` 이다. 같은 형태에 이름이 둘이면(`.badge`) 어느 쪽이
    // 기준인지 화면이 말하지 못한다 (FR-264 · C-4). 단언 대상은 그대로다.
    const chip = screen.getAllByText("프로젝트").find((el) => el.classList.contains("chip"));
    expect(chip).toBeTruthy();
  });

  it("홈 최상위에서는 위로 올라가는 수단이 없다", async () => {
    vi.stubGlobal(
      "fetch",
      stubFetch({
        "/api/project/list": { projects: [], warning: null },
        "/api/fs/browse": { path: "/home/me", parent: null, entries: [] },
      }),
    );
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByText("기존 프로젝트 열기"));
    await screen.findByText("이 폴더 열기");

    expect(screen.queryByText("↑ 상위 폴더")).toBeNull();
  });
});

describe("ProjectSetup — 오류 표시 (DR-008)", () => {
  it("목록을 못 불러와도 새로 만들기는 살아 있다", async () => {
    vi.stubGlobal("fetch", stubFetch({}, 500));
    render(<ProjectSetup onOpened={() => {}} />);

    expect(await screen.findByText("+ 새 프로젝트 만들기")).toBeTruthy();
  });

  it("레지스트리 경고를 사용자에게 전달한다", async () => {
    vi.stubGlobal(
      "fetch",
      stubFetch({
        "/api/project/list": { projects: [], warning: "목록 파일의 형식을 알 수 없습니다." },
      }),
    );
    render(<ProjectSetup onOpened={() => {}} />);

    expect(await screen.findByText("목록 파일의 형식을 알 수 없습니다.")).toBeTruthy();
  });
});
