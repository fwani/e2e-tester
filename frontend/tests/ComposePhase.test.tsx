import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ComposeView } from "../src/pages/ComposeView";

const el = (selector: string) => document.querySelector<HTMLElement>(selector);

function show(overrides: Partial<Parameters<typeof ComposeView>[0]> = {}) {
  return render(
    <ComposeView
      project={null}
      onCancel={vi.fn()}
      onRecord={vi.fn()}
      onStartAi={vi.fn()}
      {...overrides}
    />,
  );
}

const pickAi = () => fireEvent.click(el('[data-compose-mode="ai"]')!);
const pickRecord = () => fireEvent.click(el('[data-compose-mode="record"]')!);

/**
 * 조작을 **`data-action` 으로 지목한다** — 라벨로 찾지 않는다.
 *
 * 라벨은 해소 방법 버튼에도 쓰인다. 비활성 조작마다 「이렇게 하면 됩니다」 버튼이
 * 붙으므로 (006 E-03 · FR-234) 같은 라벨이 여러 자리에 나타나는 것이 **정상**이다 —
 * 편집 국면에도 「브라우저 열어 …」가 4개 있다. 자리가 하나인 것은 `data-action` 이고,
 * 그것을 `CapabilityUI.test.tsx` 의 「한 조작이 두 자리를 갖지 않는다」가 센다.
 */
const act = (id: string) => el(`[data-action="${id}"]`)! as HTMLButtonElement;

afterEach(cleanup);

describe("시작 화면은 선택한 작성 방식에 필요한 기능만 보인다", () => {
  it("빈 작업대와 시작 전 저장·편집 조작을 표시하지 않는다", () => {
    show();
    expect(screen.getByRole("heading", { name: "새 테스트" })).toBeTruthy();
    expect(el("[data-workbench-target]")).toBeNull();
    expect(el("[data-workbench-step-panel]")).toBeNull();
    expect(el('[data-action="save"]')).toBeNull();
    expect(screen.queryByLabelText("테스트 이름")).toBeNull();
  });
  it("직접 녹화가 기본이고 시작 조작은 하나다", () => {
    show();
    expect(el('[data-compose-mode="record"]')?.getAttribute("aria-pressed")).toBe("true");
    expect(act("record.start")).toBeTruthy();
    expect(el('[data-action="ai.start"]')).toBeNull();
    expect(screen.queryByLabelText("자연어 지시")).toBeNull();
  });
  it("AI를 선택하면 지시문과 AI 시작으로 전환한다", () => {
    show(); pickAi();
    expect(screen.getByLabelText("자연어 지시")).toBeTruthy();
    expect(act("ai.start").disabled).toBe(true);
    expect(screen.getByText(/지시문을 쓰면 시작할 수 있습니다/)).toBeTruthy();
    expect(el('[data-action="record.start"]')).toBeNull();
  });
  it("방식을 전환해도 작성한 URL과 지시문을 보존한다", () => {
    show(); pickAi();
    fireEvent.change(screen.getByLabelText("시작 URL"), { target: { value: "https://test.local" } });
    fireEvent.change(screen.getByLabelText("자연어 지시"), { target: { value: "로그인 확인" } });
    pickRecord(); pickAi();
    expect((screen.getByLabelText("자연어 지시") as HTMLTextAreaElement).value).toBe("로그인 확인");
    expect((screen.getByLabelText("시작 URL") as HTMLInputElement).value).toBe("https://test.local");
  });
  it("목록으로 돌아갈 수 있다", () => {
    const onCancel = vi.fn(); show({ onCancel });
    fireEvent.click(act("nav.back")); expect(onCancel).toHaveBeenCalledOnce();
  });
});

describe("시작을 걸면 기존 경로를 그대로 쓴다 (FR-248 · 005 U-01·U-06)", () => {
  it("직접 녹화를 고르고 시작하면 녹화 경로를 부른다", () => {
    const onRecord = vi.fn();
    show({ onRecord });
    fireEvent.change(screen.getByLabelText("시작 URL"), {
      target: { value: "http://t/login.html" },
    });
    pickRecord();
    fireEvent.click(act("record.start"));
    expect(onRecord).toHaveBeenCalledWith("http://t/login.html");
  });

  it("AI 를 고르고 지시문을 쓰면 AI 경로를 부른다 — 중간 화면이 없다 (FR-259)", () => {
    const onStartAi = vi.fn();
    show({ onStartAi });
    fireEvent.change(screen.getByLabelText("시작 URL"), {
      target: { value: "http://t/login.html" },
    });
    pickAi();
    fireEvent.change(screen.getByLabelText("자연어 지시"), {
      target: { value: "로그인한 다음 프로젝트를 만들어" },
    });
    fireEvent.click(act("ai.start"));
    expect(onStartAi).toHaveBeenCalledWith("http://t/login.html", "로그인한 다음 프로젝트를 만들어");
  });

  /**
   * 사용자 보고 — 「녹화 시작 준비가 오래 걸리는데 버튼이 계속 눌려서 중복이 난다」.
   *
   * 005 U-06 과 **같은 결함이 다른 국면에서** 남아 있었다. 표의 O2(`busy`)가 막을
   * 조건인데 `record.start` 가 그 목록에 없었고, 화면도 사실을 넘기지 않았다.
   * 브라우저를 띄우는 데 1초 남짓 걸리고, 그 사이의 클릭이 그대로 세션 생성이 됐다.
   */
  it("세션을 만드는 중에는 녹화 시작이 잠기고 이유가 붙는다 (표 O2)", () => {
    const onRecord = vi.fn();
    show({ onRecord, busy: true });
    fireEvent.change(screen.getByLabelText("시작 URL"), {
      target: { value: "http://t/login.html" },
    });
    pickRecord();

    const button = act("record.start");
    expect(button.disabled).toBe(true);
    // 잠긴 이유를 말하지 않으면 사용자는 제품이 멈춘 것으로 읽는다 (FR-234).
    // 이유는 `aria-describedby` 로 버튼에 묶인다 — 눈으로만 두지 않는다.
    const reason = el('[data-disabled-reason="record.start"]');
    expect(reason?.textContent ?? "").not.toBe("");
    expect(button.getAttribute("aria-describedby")).toBe(reason?.id);

    fireEvent.click(button);
    expect(onRecord).not.toHaveBeenCalled();
  });

  it("시작 URL 형식이 틀리면 세션을 만들지 않고 이유를 말한다", () => {
    const onRecord = vi.fn();
    show({ onRecord });
    fireEvent.change(screen.getByLabelText("시작 URL"), { target: { value: "t/login" } });
    pickRecord();
    fireEvent.click(act("record.start"));
    expect(onRecord).not.toHaveBeenCalled();
    // `ErrorNotice` 는 사유와 다음 행동을 각각 그린다 — 자리가 둘인 것이 정상이다
    expect(
      screen.getAllByText(/http:\/\/ 또는 https:\/\/ 로 시작해야 합니다/).length,
    ).toBeGreaterThan(0);
  });
});
