/**
 * 초안 목록 (014 T066 · US3 · FR-027·FR-029·FR-035).
 *
 * 이 영역이 지켜야 하는 것은 셋이다.
 *
 * 1. **몇 건 남았는지 말한다** (FR-035). 설계서에서 스무 건을 들여온 사용자에게 필요한
 *    것은 목록이 아니라 다음에 무엇을 할지다.
 * 2. **희망 번호를 못 받을 수 있다는 것을 미리 알린다** (FR-032). 조용히 다른 번호를
 *    주면 사용자는 자기 설계서와 제품이 어긋난 것을 나중에 발견한다.
 * 3. **삭제는 되돌릴 수 없으므로 그 자리에서 한 번 더 묻는다.**
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DraftRow } from "../src/api/client";
import { DraftSection } from "../src/pages/DraftList";

function stub() {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), method: init?.method ?? "GET" });
      return Promise.resolve({
        ok: true,
        status: 204,
        headers: new Headers(),
        text: () => Promise.resolve(""),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response);
    }),
  );
  return calls;
}

const draft = (over: Partial<DraftRow> = {}): DraftRow => ({
  draft_id: "D-0001",
  name: "로그인",
  description: "자격 증명 확인",
  actor: "관리자",
  group_prefix: "USER",
  desired_test_id: "USER-003",
  desired_id_available: true,
  source: { file_name: "설계서.xlsx", sheet_name: "회원", row: 4 },
  created_at: "2026-09-10T09:00:00Z",
  ...over,
});

function mount(drafts: DraftRow[], over: Partial<Parameters<typeof DraftSection>[0]> = {}) {
  const props = {
    drafts,
    problems: [],
    busy: false,
    onRecord: vi.fn(),
    onChanged: vi.fn(),
    onError: vi.fn(),
    ...over,
  };
  render(<DraftSection {...props} />);
  return props;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("초안이 없을 때", () => {
  it("영역 자체를 그리지 않는다", () => {
    stub();
    const { container } = render(
      <DraftSection
        drafts={[]}
        problems={[]}
        busy={false}
        onRecord={() => {}}
        onChanged={() => {}}
        onError={() => {}}
      />,
    );
    expect(container.querySelector("[data-draft-section]")).toBeNull();
  });

  it("읽지 못한 파일이 있으면 그것만이라도 알린다", () => {
    stub();
    const { container } = render(
      <DraftSection
        drafts={[]}
        problems={["D-0002 를 읽을 수 없습니다"]}
        busy={false}
        onRecord={() => {}}
        onChanged={() => {}}
        onError={() => {}}
      />,
    );
    expect(container.querySelector("[data-draft-section]")).toBeTruthy();
    expect(screen.getByText(/읽을 수 없습니다/)).toBeTruthy();
  });
});

describe("몇 건 남았는가", () => {
  it("건수를 보여준다", () => {
    stub();
    mount([draft(), draft({ draft_id: "D-0002", name: "로그아웃" })]);
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("초안이 무엇인지 말한다", () => {
    stub();
    mount([draft()]);
    expect(screen.getByText(/하나씩 녹화하면 테스트가 됩니다/)).toBeTruthy();
  });
});

describe("행의 내용", () => {
  it("희망 번호와 제목을 보여준다", () => {
    stub();
    mount([draft()]);
    expect(screen.getByText("USER-003")).toBeTruthy();
    expect(screen.getByText("로그인")).toBeTruthy();
  });

  it("설명과 수행자를 보여준다", () => {
    stub();
    mount([draft()]);
    expect(screen.getByText("자격 증명 확인")).toBeTruthy();
    expect(screen.getByText("관리자")).toBeTruthy();
  });

  it("출처를 파일·시트·행으로 말한다", () => {
    stub();
    mount([draft()]);
    expect(screen.getByText(/설계서\.xlsx · 회원 4행/)).toBeTruthy();
  });

  it("희망 번호가 없으면 자리를 비워 둔다", () => {
    stub();
    mount([draft({ desired_test_id: null })]);
    expect(screen.getByText("—")).toBeTruthy();
  });
});

describe("희망 번호를 못 받을 때", () => {
  it("미리 알린다", () => {
    stub();
    mount([draft({ desired_id_available: false })]);
    expect(screen.getByText(/저장할 때 다른 번호를 받습니다/)).toBeTruthy();
  });

  it("막지는 않는다", () => {
    // 초안은 번호를 예약하지 않는다 (FR-032). 예고일 뿐이다.
    stub();
    mount([draft({ desired_id_available: false })]);
    const button = screen.getByRole("button", { name: "녹화 시작" }) as HTMLButtonElement;
    expect(button.disabled).toBe(false);
  });

  it("받을 수 있으면 그 말을 하지 않는다", () => {
    stub();
    mount([draft({ desired_id_available: true })]);
    expect(screen.queryByText(/다른 번호를 받습니다/)).toBeNull();
  });
});

describe("녹화 시작", () => {
  it("고른 초안을 넘긴다", () => {
    stub();
    const props = mount([draft()]);
    fireEvent.click(screen.getByRole("button", { name: "녹화 시작" }));
    expect(props.onRecord).toHaveBeenCalledWith(expect.objectContaining({ draft_id: "D-0001" }));
  });

  it("진행 중이면 누를 수 없다", () => {
    stub();
    mount([draft()], { busy: true });
    const button = screen.getByRole("button", { name: "녹화 시작" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });
});

describe("삭제", () => {
  it("확인 전에는 요청이 나가지 않는다", () => {
    const calls = stub();
    mount([draft()]);
    fireEvent.click(screen.getByRole("button", { name: "지우기" }));
    expect(calls).toEqual([]);
    expect(screen.getByText("지울까요?")).toBeTruthy();
  });

  it("확인하면 지운다", async () => {
    const calls = stub();
    const props = mount([draft()]);
    fireEvent.click(screen.getByRole("button", { name: "지우기" }));
    fireEvent.click(screen.getByRole("button", { name: "지우기" }));
    await waitFor(() => {
      expect(calls).toEqual([{ url: "/api/drafts/D-0001", method: "DELETE" }]);
    });
    await waitFor(() => expect(props.onChanged).toHaveBeenCalled());
  });

  it("그대로를 고르면 요청이 나가지 않는다", () => {
    const calls = stub();
    mount([draft()]);
    fireEvent.click(screen.getByRole("button", { name: "지우기" }));
    fireEvent.click(screen.getByRole("button", { name: "그대로" }));
    expect(calls).toEqual([]);
    expect(screen.queryByText("지울까요?")).toBeNull();
  });

  it("확인은 그 행에만 걸린다", () => {
    stub();
    const { container } = render(
      <DraftSection
        drafts={[draft(), draft({ draft_id: "D-0002", name: "둘째" })]}
        problems={[]}
        busy={false}
        onRecord={() => {}}
        onChanged={() => {}}
        onError={() => {}}
      />,
    );
    const first = container.querySelector('[data-draft-row="D-0001"]') as HTMLElement;
    fireEvent.click(first.querySelector('[data-action="draft.delete"]') as HTMLElement);

    const second = container.querySelector('[data-draft-row="D-0002"]') as HTMLElement;
    expect(second.querySelector('[data-action="draft.record"]')).toBeTruthy();
    expect(second.textContent).not.toContain("지울까요?");
  });
});
