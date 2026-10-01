/**
 * 028 — 접두어 규칙은 화면과 서버가 **한 벌**로 쓴다. spec FR-001~FR-007.
 *
 * 사용자가 `IT-PM`·`IT-DM` 으로 그룹을 나누려다 막혔다. 화면이 「영문 대문자·숫자
 * 1~8자」로 거절했기 때문이다.
 *
 * 이 파일이 지키는 것은 둘이다.
 *
 * 1. **하이픈 접두어를 받는다** — 사용자가 문서에서 쓰던 식별 체계를 그대로 옮길 수 있다.
 * 2. **규칙이 생성물에서 온다** — 이 파일 안에 정규식 리터럴이 없다. 예전에는
 *    `TestGroupBar` 가 서버 규칙을 손으로 복제하고 있었고, 두 벌이 우연히 같았기 때문에
 *    드러나지 않았다 (헌법 Cross-language schema duty).
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { TestGroupBar } from "../src/components/TestGroupBar";
import { CONSTRAINTS, satisfies } from "../src/types/generated/constraints";

const PREFIX_RULE = "project/TestGroup/prefix" as const;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ─── 규칙 자체 (FR-001 ~ FR-004) ────────────────────────────────────────────

describe("생성된 접두어 규칙", () => {
  it.each(["IT-PM", "IT-DM", "USER", "A-B-C", "TC"])("「%s」을 받는다", (prefix) => {
    expect(satisfies(PREFIX_RULE, prefix)).toBe(true);
  });

  it.each([
    ["IT-", "하이픈으로 끝난다"],
    ["-PM", "하이픈으로 시작한다"],
    ["IT--PM", "하이픈이 연달아 온다"],
    ["it-pm", "소문자다"],
    ["IT-001", "숫자만의 마디 — 식별자의 번호와 구분되지 않는다"],
    ["ABCDEFGHIJKLM", "13자 — 상한을 넘는다"],
  ])("「%s」을 거절한다 (%s)", (prefix) => {
    expect(satisfies(PREFIX_RULE, prefix)).toBe(false);
  });

  it("길이 상한이 서버와 같은 값에서 온다", () => {
    // 이 수를 여기에 적는 것이 아니라, 생성물에 실려 온 것을 확인한다.
    expect(CONSTRAINTS[PREFIX_RULE].maxLength).toBe(12);
  });
});

// ─── 규칙이 한 벌인가 (FR-007 · 헌법) ───────────────────────────────────────

describe("규칙의 출처", () => {
  it("화면 부품 안에 접두어 정규식 리터럴이 없다", () => {
    /*
      **이것이 이 파일에서 가장 중요한 단언이다.**

      규칙이 맞는지는 위에서 봤다. 여기서 보는 것은 **규칙이 어디서 왔는가**다. 값이
      우연히 같아도 두 벌이면 다음 변경에서 갈린다 — 028 이 고친 결함이 정확히 그것이다.

      주석 안의 옛 정규식은 「예전에는 이랬다」는 기록이므로 주석을 걷어내고 본다.
    */
    const source = readFileSync(
      join(__dirname, "..", "src/components/TestGroupBar.tsx"),
      "utf8",
    );
    const code = source
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"))
      .join("\n");

    expect(code).not.toMatch(/\[A-Z\]/);
    expect(code).toContain("satisfies(");
  });
});

// ─── 화면에서 (FR-006) ──────────────────────────────────────────────────────

function openNewGroupForm() {
  render(
    <TestGroupBar
      groups={[]}
      active={null}
      busy={false}
      onPick={() => undefined}
      onCreate={() => undefined}
      onRename={() => undefined}
      onRemove={() => undefined}
    />,
  );
}

describe("그룹 만들기 칸", () => {
  it("IT-PM 을 넣으면 만들 수 있다 (FR-001)", async () => {
    const made: { prefix: string; name: string }[] = [];
    render(
      <TestGroupBar
        groups={[]}
        active={null}
        busy={false}
        onPick={() => undefined}
        onCreate={(prefix, name) => made.push({ prefix, name })}
        onRename={() => undefined}
        onRemove={() => undefined}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "그룹 관리" }));
    await user.click(screen.getByRole("button", { name: "+ 그룹" }));
    await user.type(screen.getByRole("textbox", { name: "그룹 이름" }), "프로젝트 관리");
    await user.type(screen.getByRole("textbox", { name: "그룹 접두어" }), "IT-PM");

    const make = screen.getByRole("button", { name: "만들기" });
    expect((make as HTMLButtonElement).disabled).toBe(false);
    await user.click(make);

    expect(made).toEqual([{ prefix: "IT-PM", name: "프로젝트 관리" }]);
  });

  it("잘못된 접두어는 그 자리에서 이유를 말한다 (FR-006)", async () => {
    openNewGroupForm();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "그룹 관리" }));
    await user.click(screen.getByRole("button", { name: "+ 그룹" }));
    await user.type(screen.getByRole("textbox", { name: "그룹 접두어" }), "IT--PM");

    // 문구가 **하이픈을 쓸 수 있다는 사실**을 담아야 한다. 「영문 대문자·숫자 1~8자」는
    // 이제 거짓이고, 그것만 읽은 사용자는 IT-PM 을 시도조차 하지 않는다.
    const notice = await screen.findByText(/하이픈으로 잇습니다/);
    expect(notice.textContent).toContain("IT-PM");
    expect((screen.getByRole("button", { name: "만들기" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });
});
