/**
 * 2026-09-10 UI/UX 점검 — **엑셀 통로(014)의 조작에 손이 닿는가.**
 *
 * 이 파일이 지키는 것은 넷이다. 넷 다 「기능은 있는데 쓸 수 없다」에 해당한다.
 *
 * 1. **파일 선택을 키보드로 쓸 수 있다.** `<label class=btn>` + `display:none` 인
 *    `<input type=file>` 짝은 Tab 순서에 아무 것도 남기지 않는다 — 라벨은 초점을 받지
 *    않고 감춘 칸은 초점 대상이 아니다. 마우스 없는 사용자에게 이 조작은 **없는 것**과
 *    같았다.
 * 2. **200개를 한 번에 켜고 끈다.** 미리보기는 시트 200개를 받는다. 체크 상자만
 *    두면 「이 시트 하나만」이 199번의 클릭이다.
 * 3. **수용량 경고가 어느 그룹인지 말한다.** 판정은 그룹마다인데 문구는 프로젝트
 *    총량을 말했다 — 사용자는 무엇을 덜어야 하는지 알 수 없었다.
 * 4. **확정 자리가 따라온다.** 시트가 많으면 확정·취소가 스크롤 아래로 사라졌다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ImportPlanView, SheetPlanView } from "../src/api/client";
import { ImportFilePicker, ImportPreview } from "../src/pages/ImportPreview";

const sheet = (over: Partial<SheetPlanView> = {}): SheetPlanView => ({
  sheet_name: "회원",
  prefix: "USER",
  prefix_source: "from_rows",
  needs_prefix: false,
  group_name: "회원",
  existing_group_name: null,
  name_differs: false,
  row_count: 2,
  renumbered: [],
  headers: ["TC ID", "대상기능"],
  column_index: { "TC ID": 0, 대상기능: 1 },
  missing_required: [],
  included: true,
  total_rows: 2,
  header_row: 1,
  sample: [
    { row: 1, cells: ["TC ID", "대상기능"] },
    { row: 2, cells: ["USER-001", "로그인"] },
  ],
  ...over,
});

const plan = (over: Partial<ImportPlanView> = {}): ImportPlanView => ({
  plan_id: "pl_test",
  file_name: "설계서.xlsx",
  expires_at: "2026-09-10T10:00:00Z",
  draft_count: 2,
  group_count: 1,
  sheets: [sheet()],
  skipped: [],
  capacity: {
    needed: 2,
    available: 900,
    ok: true,
    groups: [{ prefix: "USER", needed: 2, available: 900, ok: true }],
  },
  warnings: [],
  ...over,
});

afterEach(cleanup);

describe("파일 선택 — 마우스 없이 쓸 수 있는가", () => {
  it("파일 칸을 `display:none` 으로 감추지 않는다 — 그러면 Tab 순서에서 사라진다", () => {
    render(<ImportFilePicker label="엑셀에서 가져오기" onPlan={() => {}} onError={() => {}} />);
    const input = document.querySelector("[data-import-file]") as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.style.display).toBe("");
    expect(input.className).toContain("file-input");
  });

  it("초점을 받을 수 있다", () => {
    render(<ImportFilePicker label="엑셀에서 가져오기" onPlan={() => {}} onError={() => {}} />);
    const input = document.querySelector("[data-import-file]") as HTMLInputElement;
    input.focus();
    expect(document.activeElement).toBe(input);
  });

  it("초점 링은 라벨이 그린다 — 안쪽 칸이 보이지 않으므로", () => {
    render(<ImportFilePicker label="엑셀에서 가져오기" onPlan={() => {}} onError={() => {}} />);
    const label = document.querySelector("label.btn") as HTMLLabelElement;
    expect(label.className).toContain("file");
  });

  it("쓸 수 없을 때 그 사실이 형태와 표식에 함께 있다", () => {
    render(
      <ImportFilePicker label="엑셀에서 가져오기" disabled onPlan={() => {}} onError={() => {}} />,
    );
    const label = document.querySelector("label.btn") as HTMLLabelElement;
    expect(label.className).toContain("disabled");
    expect(label.getAttribute("aria-disabled")).toBe("true");
    expect((document.querySelector("[data-import-file]") as HTMLInputElement).disabled).toBe(true);
  });
});

describe("시트 200개 — 한 번에 켜고 끈다", () => {
  const many = plan({
    sheets: [sheet(), sheet({ sheet_name: "데이터", prefix: "DATA" })],
    capacity: {
      needed: 4,
      available: 900,
      ok: true,
      groups: [
        { prefix: "USER", needed: 2, available: 900, ok: true },
        { prefix: "DATA", needed: 2, available: 900, ok: true },
      ],
    },
  });

  it("몇 개가 켜져 있는지 말한다", () => {
    render(<ImportPreview plan={many} onCancel={() => {}} onDone={() => {}} />);
    expect(document.querySelector("[data-sheet-on-count]")?.textContent).toContain("2개 켜짐");
  });

  it("전체 끄기가 전부 끈다 — 그러면 확정이 막히고 왜인지 말한다", () => {
    render(<ImportPreview plan={many} onCancel={() => {}} onDone={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "전체 끄기" }));
    expect(document.querySelector("[data-nothing-chosen]")).not.toBeNull();
    expect((screen.getByRole("button", { name: "가져오기" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("전체 켜기가 되돌린다", () => {
    render(<ImportPreview plan={many} onCancel={() => {}} onDone={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "전체 끄기" }));
    fireEvent.click(screen.getByRole("button", { name: "전체 켜기" }));
    expect(document.querySelector("[data-sheet-on-count]")?.textContent).toContain("2개 켜짐");
    expect((screen.getByRole("button", { name: "가져오기" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it("이미 전부 켜져 있으면 「전체 켜기」를 누를 수 없다 — 아무 일도 하지 않는 조작을 남기지 않는다", () => {
    render(<ImportPreview plan={many} onCancel={() => {}} onDone={() => {}} />);
    expect((screen.getByRole("button", { name: "전체 켜기" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });
});

describe("수용량 경고 — 어느 그룹이 넘쳤는지 말한다", () => {
  const full = plan({
    sheets: [sheet({ row_count: 40, total_rows: 40 })],
    capacity: {
      needed: 40,
      available: 5,
      ok: false,
      groups: [{ prefix: "USER", needed: 40, available: 5, ok: false }],
    },
  });

  it("그룹 이름과 그 그룹의 남은 칸을 함께 말한다", () => {
    render(<ImportPreview plan={full} onCancel={() => {}} onDone={() => {}} />);
    const warn = document.querySelector("[data-capacity-warning]") as HTMLElement;
    expect(warn.textContent).toContain("USER");
    expect(warn.textContent).toContain("40건");
    expect(warn.textContent).toContain("5개");
  });

  it("확정을 막는다", () => {
    render(<ImportPreview plan={full} onCancel={() => {}} onDone={() => {}} />);
    expect((screen.getByRole("button", { name: "가져오기" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });
});

describe("확정 자리", () => {
  it("화면 아래에 붙어 따라온다 — 시트가 많아도 확정과 취소에 손이 닿는다", () => {
    render(<ImportPreview plan={plan()} onCancel={() => {}} onDone={() => {}} />);
    const bar = screen.getByRole("button", { name: "가져오기" }).parentElement as HTMLElement;
    expect(bar.className).toContain("commit-bar");
  });
});

describe("표 머리", () => {
  it("`scope` 를 붙인다 — 없으면 낭독기가 어느 열인지 말할 수 없다", () => {
    render(<ImportPreview plan={plan()} onCancel={() => {}} onDone={() => {}} />);
    const heads = [...document.querySelectorAll("thead.grid-head th")];
    expect(heads.length).toBeGreaterThan(0);
    expect(heads.every((h) => h.getAttribute("scope") === "col")).toBe(true);
  });
});

describe("내보내기 — 파일이 실제로 저장되는가", () => {
  it("`revokeObjectURL` 을 click 과 같은 태스크에서 부르지 않는다", async () => {
    /*
      바로 회수하면 내려받기가 시작되기 전에 URL 이 사라진다 — 화면은
      「내려받았습니다」라고 말하고 파일은 없다. 조용한 실패라 사용자가 원인을 알 길이
      없으므로 검사로 못박는다.
    */
    const { saveBlob } = await import("../src/api/client");
    const revoke = vi.fn();
    const created: string[] = [];
    vi.stubGlobal("URL", {
      createObjectURL: () => {
        created.push("blob:x");
        return "blob:x";
      },
      revokeObjectURL: revoke,
    });
    vi.useFakeTimers();
    /* jsdom 은 `<a>` 클릭을 이동으로 다뤄 「Not implemented: navigation」을 낸다.
       재는 것은 회수 시점이므로 클릭 자체는 비워 둔다. */
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    try {
      saveBlob(new Blob(["x"]), "설계서.xlsx");
      expect(created).toEqual(["blob:x"]);
      expect(revoke).not.toHaveBeenCalled();
      vi.runAllTimers();
      expect(revoke).toHaveBeenCalledWith("blob:x");
    } finally {
      click.mockRestore();
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });
});
