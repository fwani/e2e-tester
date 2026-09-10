/**
 * 2026-09-10 사용자 결정 — **모든 알림은 토스트다.**
 *
 * 「테스트 목록에서 알림이 한줄 생겨서 테스트 목록 테이블이 아래로 내려가버린다.
 * 본 프로젝트의 모든 알림은 토스트로 변경하라」.
 *
 * 같은 결함이 세 번 보고됐다 — `Workbench`(2026-09-09), `App` 의 오류 배너(2026-09-10),
 * 그리고 목록의 내보내기·진행 중 세션 알림. 화면마다 손으로 고쳤기 때문에 남은 자리가
 * 계속 나왔다.
 *
 * 여기서 지키는 것은 **자리** 하나다. 알림은 문서 흐름에 없다 — 즉 층
 * (`[data-toast-layer]`) 안에 있고, 화면 내용의 자손이 아니다. 그것이 「아래로
 * 내려가버린다」를 구조적으로 불가능하게 만드는 성질이다.
 *
 * 층이 **하나**라는 것도 함께 잰다. 화면마다 층을 만들면 둘이 동시에 뜰 때 겹친다.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Toast } from "../src/components/Toast";
import { ImportDoneNotice } from "../src/pages/ImportPreview";
import { TestList } from "../src/pages/TestList";
import type { ImportResultView } from "../src/api/client";

const EMPTY_LISTING = { counts: { total: 0, pass: 0, fail: 0 }, groups: [], tests: [], problems: [] };

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.startsWith("/api/drafts")
        ? { drafts: [], problems: [] }
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

/** 층을 검사 사이에 남기지 않는다 — 모듈이 만든 것이라 `cleanup()` 이 지우지 않는다. */
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  document.querySelectorAll("[data-toast-layer]").forEach((el) => el.remove());
});

const layer = () => document.querySelector("[data-toast-layer]");

describe("토스트 층", () => {
  it("알림은 층 안에 있고 화면 내용의 자손이 아니다", () => {
    const { container } = render(<Toast mark="data-probe">내려받았습니다</Toast>);

    const toast = document.querySelector("[data-probe]");
    expect(toast, "토스트가 없다").not.toBeNull();
    expect(layer()!.contains(toast!), "토스트가 층 밖에 있다").toBe(true);
    // 문서 흐름에 없다는 것 — 화면이 그린 나무의 자손이 아니다.
    expect(container.contains(toast!), "토스트가 화면 내용 안에 있다").toBe(false);
  });

  it("층은 하나다 — 여럿이 동시에 떠도", () => {
    render(
      <>
        <Toast mark="data-a">하나</Toast>
        <Toast mark="data-b">둘</Toast>
      </>,
    );
    expect(document.querySelectorAll("[data-toast-layer]").length).toBe(1);
    expect(layer()!.querySelectorAll(".toast").length).toBe(2);
  });

  it("층은 정본의 자리를 쓴다", () => {
    render(<Toast>무엇이든</Toast>);
    expect(layer()!.className).toContain("toast-layer");
  });

  it("오류는 낭독기에게 alert 이고 닫는 길이 있다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast tone="error" mark="data-err" onDismiss={onDismiss}>
        실패했습니다
      </Toast>,
    );
    const toast = document.querySelector("[data-err]") as HTMLElement;
    expect(toast.getAttribute("role")).toBe("alert");
    expect(toast.className).toContain("tint-fail");
    screen.getByRole("button", { name: "알림 닫기" }).click();
    expect(onDismiss).toHaveBeenCalled();
  });

  it("닫는 길이 없으면 닫기를 그리지 않는다 — 지금 돌고 있다는 상태가 그렇다", () => {
    render(<Toast mark="data-live">돌고 있습니다</Toast>);
    expect(screen.queryByRole("button", { name: "알림 닫기" })).toBeNull();
  });
});

describe("실제 알림들이 토스트다", () => {
  it("진행 중 세션 알림 — 목록을 밀어내지 않는다", async () => {
    stubFetch();
    const { container } = render(
      <TestList
        projectName="통합"
        onCreate={() => {}}
        onRun={() => {}}
        pendingRunId={null}
        onOpenResult={() => {}}
        activeSessions={[
          {
            session_id: "s1",
            test_id: "USER-001",
            state: "replaying",
            state_label: "실행 중",
            steps: [],
          } as never,
        ]}
        onResumeSession={() => {}}
      />,
    );

    await waitFor(() => expect(document.querySelector("[data-open-session]")).not.toBeNull());
    const notice = document.querySelector("[data-open-session]")!;
    expect(layer()!.contains(notice)).toBe(true);
    expect(container.contains(notice), "알림이 목록 안에 있어 아래를 밀어낸다").toBe(false);
  });

  it("가져오기 완료 알림", () => {
    const result = {
      created_groups: ["USER"],
      drafts: [{ draft_id: "d1" }],
      skipped: [],
      skipped_sheets: [],
      ignored_sheets: [],
      renumbered: [],
    } as unknown as ImportResultView;

    const { container } = render(<ImportDoneNotice result={result} onDismiss={() => {}} />);
    const notice = document.querySelector("[data-import-done]")!;
    expect(notice).not.toBeNull();
    expect(layer()!.contains(notice)).toBe(true);
    expect(container.contains(notice)).toBe(false);
  });
});
