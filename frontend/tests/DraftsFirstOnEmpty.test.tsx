/**
 * 2026-09-10 UI/UX 점검 — **들여온 초안이 첫 화면에서 보이는가.**
 *
 * 014 는 초안 구획을 첫 사용자 화면에서도 그리기로 정했다 (`DraftList.tsx` 머리말).
 * 그런데 자리가 **첫 사용자 안내 아래**였다. 그 안내는 `flex:1` 로 화면을 가득 채우므로,
 * 설계서에서 스무 건을 들여온 사용자가 보는 것은 「아직 테스트가 없습니다」와 시작하는
 * 세 갈래뿐이고 자기가 방금 들여온 스무 건은 스크롤 밖에 있었다 — FR-035 가 막으려던
 * 것이 그대로 남아 있었다.
 *
 * 여기서 지키는 것은 **자리와 문구** 둘이다.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";

const EMPTY_LISTING = {
  counts: { total: 0, pass: 0, fail: 0 },
  groups: [],
  tests: [],
  problems: [],
};

const draft = (id: string, name: string) => ({
  draft_id: id,
  name,
  description: null,
  actor: null,
  group_prefix: "USER",
  desired_test_id: `USER-00${id.slice(-1)}`,
  desired_id_available: true,
  source: { file_name: "설계서.xlsx", sheet_name: "회원", row: 4 },
  created_at: "2026-09-10T09:00:00Z",
});

function stub(drafts: ReturnType<typeof draft>[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.startsWith("/api/drafts")
        ? { drafts, problems: [] }
        : url.startsWith("/api/groups")
          ? { groups: [] }
          : url.startsWith("/api/ai/availability")
            ? { available: false, reason: null }
            : EMPTY_LISTING;
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

function mount() {
  return render(
    <TestList
      projectName="통합"
      onCreate={() => {}}
      onRun={() => {}}
      pendingRunId={null}
      onOpenResult={() => {}}
      activeSessions={[]}
      onRecordDraft={() => {}}
      onImportPlan={() => {}}
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("테스트 0개 · 초안 있음", () => {
  it("초안 구획이 첫 사용자 안내보다 **위에** 온다", async () => {
    stub([draft("D-1", "로그인"), draft("D-2", "회원가입")]);
    mount();
    const section = await waitFor(() => {
      const el = document.querySelector("[data-draft-section]");
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });
    const hero = screen.getByText("아직 테스트가 없습니다");
    /*
      `DOCUMENT_POSITION_FOLLOWING` — 초안 구획을 기준으로 안내가 **뒤에** 있다.
      자리를 눈으로 확인할 수 없는 검사이므로 문서 순서로 못박는다.
    */
    expect(section.compareDocumentPosition(hero) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("한 번만 그린다 — 같은 구획이 두 번 나오면 둘이 다른 것인지 확인해야 한다", async () => {
    stub([draft("D-1", "로그인")]);
    mount();
    await waitFor(() =>
      expect(document.querySelectorAll("[data-draft-section]").length).toBe(1),
    );
  });

  it("안내 문구가 초안을 가리킨다 — 「말로 적으면 됩니다」는 이 사용자에게 맞지 않는다", async () => {
    stub([draft("D-1", "로그인"), draft("D-2", "회원가입")]);
    mount();
    expect(await screen.findByText(/위의 초안 2건을 녹화하면 테스트가 됩니다/)).toBeTruthy();
  });

  it("이미 들여온 사용자에게 「엑셀에서 가져오기」를 다시 앞세우지 않는다", async () => {
    stub([draft("D-1", "로그인")]);
    mount();
    await screen.findByText(/위의 초안 1건/);
    // 길은 남는다 — 접힌 자리에 있다.
    expect(screen.getByText("엑셀 파일을 더 넣기")).toBeTruthy();
    expect(screen.queryByText("이미 쓰던 설계서가 있나요?")).toBeNull();
  });
});

describe("테스트 0개 · 초안 없음 — 맨 처음 온 사용자", () => {
  it("원래 문구가 그대로다", async () => {
    stub([]);
    mount();
    expect(await screen.findByText(/브라우저를 직접 조작하거나, 할 일을 말로 적으면 됩니다/)).toBeTruthy();
  });

  it("「엑셀에서 가져오기」 갈래가 펼쳐져 있다", async () => {
    stub([]);
    mount();
    expect(await screen.findByText("이미 쓰던 설계서가 있나요?")).toBeTruthy();
  });

  it("초안 구획을 그리지 않는다 — 없는 것에 자리를 주지 않는다", async () => {
    stub([]);
    mount();
    await screen.findByText("이미 쓰던 설계서가 있나요?");
    expect(document.querySelector("[data-draft-section]")).toBeNull();
  });
});
