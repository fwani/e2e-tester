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

import { Toast } from "../src/ui/Toast";
import { ImportDoneNotice } from "../src/pages/ImportPreview";
import { TestList } from "../src/pages/TestList";
import type { ImportResultView } from "../src/api/client";
import { TOAST_VIEWPORT_CLASSES } from "../src/ui/Toast";

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
    // 015 — 알림을 **정본 클래스가 아니라 `data-tone`** 으로 센다. 묻는 것은 그대로:
    // 층이 하나이고 그 안에 알림 둘이 있는가.
    expect(layer()!.querySelectorAll("[data-tone]").length).toBe(2);
  });

  it("층은 정본의 자리를 쓴다", () => {
    render(<Toast>무엇이든</Toast>);
    expect(layer()!.className, "층이 정본의 자리를 쓰지 않는다").toBe(TOAST_VIEWPORT_CLASSES);
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
    // 「오류임이 형태에 있는가」를 **의도**로 묻는다. 유틸리티 조합을 읽으면 색 하나만
    // 바꿔도 검사가 깨지고, 정작 물어야 할 것은 사라진다 (LC-4 ②).
    expect(toast.getAttribute("data-tone"), "오류 형태가 아니다").toBe("fail");
    screen.getByRole("button", { name: "알림 닫기" }).click();
    expect(onDismiss).toHaveBeenCalled();
  });

  it("닫는 길이 없으면 닫기를 그리지 않는다 — 지금 돌고 있다는 상태가 그렇다", () => {
    render(<Toast mark="data-live">돌고 있습니다</Toast>);
    expect(screen.queryByRole("button", { name: "알림 닫기" })).toBeNull();
  });
});

describe("실제 알림들이 토스트다", () => {
  /*
    017 B-02 — **판정 방법을 바꿨다.** 이 자리는 「진행 중 세션 알림이 토스트 층에 있고 목록 안에
    없다」를 봤다. 그 토스트가 흐름 안 세션 띠(`ActiveSessionsBanner`, UX U-05)와 **같은 사실**을
    말하며 띠의 조작을 덮었고, 두 곳이 같은 복귀 조작을 가졌다. 017 이 토스트를 지우고 띠를 남겼다
    (research R6 ⑤ · 2026-09-10 「모든 알림은 토스트」 결정과의 긴장을 거기 적었다).

    그래서 묻는 것은 이렇게 바뀐다: 진행 중 세션이라는 사실을 **한 자리가** 말하고, 복귀 조작이
    **하나**다. 「토스트 층에 사실이 되풀이되지 않는다」를 함께 본다. 이 경우를 지우지 않고 남기는
    이유는, 토스트가 다시 들어오면 B-02 가 되살아나기 때문이다.
  */
  it("진행 중 세션은 흐름 안 띠 하나가 말한다 — 같은 사실의 토스트와 복귀 조작 둘이 없다 (017 B-02)", async () => {
    stubFetch();
    render(
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

    await waitFor(() => expect(document.querySelector("[data-active-sessions]")).not.toBeNull());
    expect(document.querySelector("[data-open-session]"), "같은 사실을 말하는 세션 토스트가 되살아났다").toBeNull();
    expect(layer()?.textContent ?? "", "토스트 층이 진행 중 세션을 되풀이한다").not.toContain("USER-001");
    expect(screen.getAllByRole("button", { name: "이어서 보기" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "실행 화면 보기" }), "복귀 조작이 화면에 둘이다").toBeNull();
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
