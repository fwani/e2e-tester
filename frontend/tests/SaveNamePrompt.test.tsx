/**
 * 011 T009 — **이름이 있는 테스트에는 이름을 다시 묻지 않는다** (UC-011-4·5·6 · FR-362~FR-366).
 *
 * ## 사용자 보고
 *
 * > 「편집에서 스텝을 수정하고나서 저장을 하게 되면 이름을 다시 지정하게 하는데 이상함」
 *
 * ## 무엇이 틀렸었나
 *
 * 판정에 쓰이던 값이 **다른 사실**이었다. `view.saved_at` 은 「이 **세션에서** 저장한
 * 시각」이고, 물어야 할 것은 「이 **테스트에** 이름이 이미 있는가」다. 저장된 테스트를
 * 열어 브라우저를 띄운 세션은 첫 저장 전까지 `saved_at === null` 이므로, 이름이 멀쩡히
 * 있는데도 라벨이 「저장」이 되고 빈 이름칸을 채워야 저장이 열렸다.
 *
 * 후자는 세션 응답에 이미 있다 — `test_id`. 011 이 `test_name` 을 함께 실어 화면이
 * 이름을 **알고** 있게 한다 (그 전에는 국면 띠가 이름 자리에 「TC-001」을 그렸다).
 *
 * ## 이 파일이 재는 것
 *
 * 조합표다 — `test_id` 유무 × (저장 라벨 · 이름칸 유무 · 저장 가능 여부). 한 경우만
 * 재면 반대쪽이 조용히 깨진다.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionScreen } from "../src/pages/SessionScreen";
import { SAVE_NEEDS_NAME } from "../src/lib/wording";
import { sessionView } from "./helpers/workbench";

/** 구독을 가로챈다 — `SessionScreen` 은 마운트하면서 실시간 통로를 연다. */
vi.mock("../src/api/ws", () => ({
  subscribeSessionEvents: () => ({ stop: () => undefined, reconnect: () => undefined }),
}));

/**
 * **바깥 컴포넌트를 그린다.**
 *
 * 이름 상태(`nameOverride`)와 확인 대화상자(`confirmingLeave`)는 `SessionScreen` 이 갖고
 * `SessionWorkbench` 는 표시만 한다 — 007 이 나눈 소유와 표시의 경계다. 안쪽만 그리면
 * 「서버가 준 이름을 기본값으로 쓴다」는 판단이 검사 밖에 남아, 이 파일이 재려는 바로
 * 그 결함을 놓친다.
 */
function renderPaused(overrides: Parameters<typeof sessionView>[0] = {}) {
  const view = sessionView({
    state: "paused",
    has_unsaved_changes: true,
    ...overrides,
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(view), { status: 200 })),
  );
  /*
    `onRerun` 을 준다 — 없으면 `rerun()` 이 첫 줄에서 돌아가고 확인이 열리지 않는다.
    실제 화면(`App`)은 항상 넘긴다.
  */
  return render(
    <SessionScreen
      initial={view}
      onFinished={() => undefined}
      onRerun={() => undefined}
    />,
  );
}

function saveButton(): HTMLElement {
  const el = document.querySelector('[data-action="save"]');
  expect(el, "저장 조작이 화면에 없다").not.toBeNull();
  return el as HTMLElement;
}

function nameField(): HTMLElement | null {
  return document.querySelector('[data-action="test.rename"]') as HTMLElement | null;
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 200 })));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("UC-011-4 — 판정 기준은 `test_id` 의 유무다", () => {
  it("이름이 없는 테스트: 라벨이 「저장」이고 이름을 묻는다", async () => {
    renderPaused({ test_id: null, test_name: null });
    expect(saveButton().textContent).toContain("저장");
    expect(saveButton().textContent).not.toContain("변경 저장");
    expect(nameField(), "이름칸이 없다 — 처음 저장은 이름을 정하는 일이다").not.toBeNull();
  });

  it("이름이 있는 테스트: 라벨이 「변경 저장」이다", async () => {
    renderPaused({ test_id: "TC-001", test_name: "로그인 흐름" });
    expect(saveButton().textContent).toContain("변경 저장");
  });

  /**
   * 이 검사가 보고를 직접 잰다. **아무것도 입력하지 않은 채** 저장이 눌릴 수 있어야 한다.
   *
   * 이전에는 `saveName` 이 빈 문자열로 시작해 `SAVE_NEEDS_NAME` 이 걸렸고, 사용자는
   * 「이름을 바꾸려는 것이 아닌데 왜 묻는가」를 판단해야 했다.
   */
  it("이름이 있는 테스트: 아무것도 입력하지 않아도 저장이 활성이다 (FR-362)", async () => {
    renderPaused({ test_id: "TC-001", test_name: "로그인 흐름" });
    const btn = saveButton() as HTMLButtonElement;
    expect(btn.disabled, "이름을 다시 요구하고 있다").toBe(false);
    expect(
      document.body.textContent,
      `"${SAVE_NEEDS_NAME}" 가 이름이 있는 테스트에 붙어 있다`,
    ).not.toContain(SAVE_NEEDS_NAME);
  });

  it("이름이 있는 테스트: 이름칸에 그 이름이 이미 들어 있다", async () => {
    renderPaused({ test_id: "TC-001", test_name: "로그인 흐름" });
    const field = nameField() as HTMLInputElement | null;
    expect(field).not.toBeNull();
    expect(field!.value, "이름칸이 비어 있다 — 사용자가 다시 쳐야 한다").toBe("로그인 흐름");
  });
});

describe("UC-011-6 — 이름을 비우면 저장을 거절하고 그 자리에서 말한다", () => {
  it("이름이 있는 테스트에서 이름을 지우면 저장이 잠기고 이유가 붙는다 (FR-366)", async () => {
    const user = userEvent.setup();
    renderPaused({ test_id: "TC-001", test_name: "로그인 흐름" });
    const field = nameField() as HTMLInputElement;
    await user.clear(field);
    await waitFor(() => {
      expect((saveButton() as HTMLButtonElement).disabled).toBe(true);
    });
    expect(document.body.textContent).toContain(SAVE_NEEDS_NAME);
  });

  it("공백만 남겨도 거절한다", async () => {
    const user = userEvent.setup();
    renderPaused({ test_id: "TC-001", test_name: "로그인 흐름" });
    const field = nameField() as HTMLInputElement;
    await user.clear(field);
    await user.type(field, "   ");
    await waitFor(() => {
      expect((saveButton() as HTMLButtonElement).disabled).toBe(true);
    });
  });
});

describe("UC-011-5 — 확인 대화상자의 이름칸은 조건부다", () => {
  /**
   * 나가기·다시 실행 확인은 이름칸을 **무조건** 그렸다. 이름이 있는 테스트에서는 그 칸이
   * 「지금 이름을 정하라」로 읽히고, 잘못 채우면 이름이 바뀐다.
   */
  /**
   * **검토 국면에서 잰다.** 일시정지의 `run.stop` 은 「중지」이고 화면을 떠나지 않는다
   * (DR-010) — 나가기 확인이 걸리는 것은 브라우저 없이 저장 가능한 상태
   * (`review`·끝난 실행)의 「닫기」다 (`onStop` 의 분기).
   */
  async function openLeaveConfirm(view: Parameters<typeof sessionView>[0]) {
    const user = userEvent.setup();
    renderPaused({ state: "review", ...view });
    const stop = await waitFor(() => {
      const el = document.querySelector('[data-action="run.stop"]') as HTMLButtonElement | null;
      expect(el, "나가기 조작이 없다").not.toBeNull();
      return el!;
    });
    await user.click(stop);
    await waitFor(() => {
      expect(screen.queryByText(/저장하지 않은 기록이 있습니다/)).not.toBeNull();
    });
  }

  it("이름이 있는 테스트: 나가기 확인에 이름칸이 없다", async () => {
    await openLeaveConfirm({ test_id: "TC-001", test_name: "로그인 흐름" });
    expect(
      document.querySelector("#leave-save-name"),
      "이름이 있는데 확인 대화상자가 이름을 묻는다 (UC-011-5)",
    ).toBeNull();
  });

  it("이름이 없는 테스트: 나가기 확인에 이름칸이 있다", async () => {
    await openLeaveConfirm({ test_id: null, test_name: null });
    expect(
      document.querySelector("#leave-save-name"),
      "이름이 없는데 확인 대화상자가 이름을 묻지 않는다 — 저장할 수 없게 된다",
    ).not.toBeNull();
  });

  /**
   * **다시 실행 확인도 같은 규칙이다** (011 converge T068).
   *
   * 1회차에서는 나가기만 검증했다. 두 대화상자가 같은 규칙을 쓰는데 한쪽만 재면, 다른
   * 쪽이 조용히 갈릴 수 있다 — 011 이전에 둘 다 이름칸을 무조건 그린 것도 같은 형태였다.
   *
   * 「처음부터 실행」은 저장하지 않은 기록이 있으면 확인을 받는다 (`rerun`).
   */
  async function openRerunConfirm(view: Parameters<typeof sessionView>[0]) {
    const user = userEvent.setup();
    renderPaused({ state: "review", has_unsaved_changes: true, ...view });
    const run = await waitFor(() => {
      const el = document.querySelector('button[data-action="run.all"]') as HTMLButtonElement | null;
      expect(el, "「처음부터 실행」이 없다").not.toBeNull();
      return el!;
    });
    await user.click(run);
    await waitFor(() => {
      expect(screen.queryByText(/저장하지 않은 기록이 있습니다/)).not.toBeNull();
    });
  }

  it("다시 실행 확인은 이름을 묻지 않는다", async () => {
    await openRerunConfirm({ test_id: "TC-001", test_name: "로그인 흐름" });
    expect(
      document.querySelector("#rerun-save-name"),
      "다시 실행 확인이 이름을 묻는다 (UC-011-5)",
    ).toBeNull();
    // 저장 경로는 그대로 열려 있어야 한다 — 물음만 없앤 것이지 저장을 없앤 것이 아니다.
    expect(screen.getByRole("button", { name: "저장하고 실행" })).toBeTruthy();
  });

  /**
   * **이름 없는 테스트는 이 확인에 닿지 못한다.**
   *
   * `rerun()` 이 `testId === null` 이면 먼저 돌아간다 — 「처음부터 실행」은 저장된 정의로
   * 새 세션을 여는 조작이라 정의가 없으면 할 일이 없다. 그 조작은 `RUN_NEEDS_SAVE` 로
   * 잠겨 있다 (2026-09-09 사용자 보고).
   *
   * 011 이 이름칸을 조건부로 만들자 그 가지가 **한 번도 참이 되지 않는다**는 것이
   * 드러났고, 그래서 아예 걷었다. 이 검사는 그 전제가 유지되는지 본다 — 전제가 깨지면
   * 이름 없이 저장하는 경로가 생긴다.
   */
  it("이름 없는 테스트에서는 「처음부터 실행」이 잠겨 있다 — 확인에 닿지 못한다", async () => {
    renderPaused({ state: "review", has_unsaved_changes: true, test_id: null, test_name: null });
    const run = await waitFor(() => {
      const el = document.querySelector('button[data-action="run.all"]') as HTMLButtonElement | null;
      expect(el).not.toBeNull();
      return el!;
    });
    expect(run.disabled, "저장되지 않은 세션에서 실행이 열려 있다").toBe(true);
  });
});
