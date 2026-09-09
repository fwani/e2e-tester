/**
 * 만들기 국면 (007 T120 · US6 · FR-258·FR-258a·FR-259·FR-260 · SC-011).
 *
 * 1회차는 만들기를 통합 대상에서 뺐다 (FR-217a). 그 결과 한 번의 「테스트를 만든다」
 * 안에서 껍데기가 두 번 바뀌었다 — `CreateTest`(1000px 가운데 정렬) → `AiCompose`(1440
 * 이지만 3층 구조 아님) → 통합 화면 (spec S-14). 그리고 Step 목록의 자리가 없어서
 * 조작이 어디에 쌓이는지는 시작한 뒤에야 보였다 (S-15).
 *
 * 여기서 재는 것은 넷이다.
 *
 * 1. 껍데기가 다른 국면과 같다 (FR-258)
 * 2. Step 이 0개여도 목록의 자리가 있다 (FR-260 · S-15)
 * 3. 방법 2택이 있고 **테스트 이름과 「빈 테스트」는 없다** (FR-258a)
 * 4. 시작을 거는 조작이 비활성일 때 이유가 붙는다 (FR-234 · 조건 C14·C15)
 *
 * 3번이 회귀 방지의 요점이다. 설계 초안이 「테스트 이름」과 「빈 테스트」를 그렸고, 둘
 * 다 지금 제품에 없는 조작이다 (research R11). 초안을 근거로 만들면 이 기능이 「새 조작을
 * 만들지 않는다」를 어긴다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ComposeView } from "../src/pages/ComposeView";
import { BASE_WIDTH } from "../src/components/workbench/Workbench";
import { splitFor } from "../src/lib/layout";

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

describe("껍데기가 다른 국면과 같다 (FR-258 · SC-011)", () => {
  it("3층 구조를 쓴다 — 헤더 · 국면 띠 · 본문", () => {
    show();
    expect(el("[data-phase-pill]"), "국면 표시").not.toBeNull();
    expect(el("[data-workbench-target]"), "③-a 대상 앱 슬롯").not.toBeNull();
    expect(el("[data-workbench-work]"), "③-b 국면 작업 영역").not.toBeNull();
    expect(el("[data-workbench-step-panel]"), "Step 목록").not.toBeNull();
  });

  it("기준 폭이 다른 국면과 같다 — 1000px 가운데 정렬 본문이 사라졌다 (S-14)", () => {
    show();
    // `Workbench` 의 `Artboard` 를 지나므로 폭이 국면마다 다를 수 없다
    expect(BASE_WIDTH).toBe(1440);
    expect(document.body.innerHTML).not.toContain("1000px");
  });

  it("국면 표시는 하나뿐이다 (FR-219)", () => {
    show();
    expect(document.querySelectorAll("[data-phase-pill]")).toHaveLength(1);
  });

  it("결말 요약 자리는 비어 있다 — 없는 결말을 지어내지 않는다", () => {
    show();
    expect(document.querySelectorAll("[data-run-summary]").length).toBeLessThanOrEqual(1);
  });
});

describe("세로 배분 — 작업 영역이 주 자리다 (FR-256·FR-257)", () => {
  it("③-b 가 남는 높이 전부를 갖고 ③-a 는 최소 높이만 갖는다", () => {
    show();
    const split = splitFor("composing");
    expect(split.workArea.kind).toBe("fill");
    expect(split.targetSlot.kind).toBe("fixed");
    expect(el("[data-workbench-work]")!.dataset.slotSize).toBe("fill");
    expect(el("[data-workbench-target]")!.dataset.slotSize).toBe("fixed");
  });

  it("대상 앱 슬롯이 사라지지 않고 왜 비었는지 말한다 (FR-244·FR-245·FR-261)", () => {
    show();
    const slot = el("[data-workbench-target]")!;
    expect(slot).not.toBeNull();
    // 「아직 시작하지 않음」과 「수집되지 않음」은 다른 다음 행동을 요구한다 (005 FR-173)
    expect(el('[data-target-empty="not_started"]')).not.toBeNull();
  });
});

describe("Step 목록은 0개여도 자리를 지킨다 (FR-260 · S-15)", () => {
  it("목록의 자리가 있고 행은 없다", () => {
    show();
    expect(el("[data-workbench-step-panel]")).not.toBeNull();
    expect(el("[data-step-row]")).toBeNull();
  });

  it("조작이 어디에 쌓이는지 시작하기 전에 말한다", () => {
    show();
    expect(screen.getByText(/시작하면 조작 하나가 행 하나로 여기 쌓입니다/)).toBeTruthy();
  });

  it("Step 패널 바닥의 조작 블록이 같은 자리에 있다 (FR-235)", () => {
    show();
    // 여덟 국면에서 같은 자리다. 쓸 수 있는 것이 없어도 자리는 남는다 (FR-234)
    expect(el("[data-workbench-step-footer]")).not.toBeNull();
  });
});

describe("조작을 더하지 않는다 (FR-258a · research R11)", () => {
  it("방법은 둘이다 — 직접 녹화 · AI로 만들기", () => {
    show();
    expect(document.querySelectorAll("[data-compose-mode]")).toHaveLength(2);
    expect(el('[data-compose-mode="record"]')).not.toBeNull();
    expect(el('[data-compose-mode="ai"]')).not.toBeNull();
  });

  /**
   * **설계 초안이 그린 두 조작이 구현에 들어오지 않았는지 센다** (research R11).
   *
   * 초안은 「테스트 이름」 입력과 「빈 테스트」 방법 카드를 그렸다. 둘 다 지금 제품에
   * 없고, 열면 이 기능이 「새 조작을 만들지 않는다」를 어긴다.
   *
   * 이름 칸은 **있고 잠겨 있다.** 감추지 않는 것이 FR-234 이고, 이름을 이 국면에서
   * 정할 수 있게 만들지 않는 것이 FR-258a 다. 둘은 함께 성립한다 —
   * 「자리는 남기고 이유를 붙인다」.
   *
   * 감추면 「만들기에는 이름이 없는 것」으로 읽히고, 열면 새 조작이 된다.
   */
  it("테스트 이름은 자리만 있고 잠겨 있다 — 이유가 붙는다", () => {
    show();
    const name = screen.getByLabelText("테스트 이름") as HTMLInputElement;
    expect(name.disabled).toBe(true);
    expect(screen.getByText(/저장할 때 이름을 정합니다/)).toBeTruthy();
  });

  it("「빈 테스트」 방법이 없다", () => {
    show();
    expect(screen.queryByText(/빈 테스트/)).toBeNull();
    expect(el('[data-compose-mode="empty"]')).toBeNull();
  });

  it("시작 URL 은 하나의 자리를 갖는다 (FR-235)", () => {
    show();
    expect(document.querySelectorAll('[data-action="test.setStartUrl"]')).toHaveLength(1);
  });
});

describe("쓸 수 없는 조작에 이유가 붙는다 (FR-234)", () => {
  it("방법을 고르기 전에도 지시문 자리가 있고 이유가 붙는다 (조건 C15)", () => {
    show();
    const box = screen.getByLabelText("자연어 지시") as HTMLTextAreaElement;
    // 감추면 「AI 로 만들 때 지시문을 쓴다」를 고른 뒤에야 알게 된다
    expect(box).toBeTruthy();
    expect(box.disabled).toBe(true);
    expect(screen.getByText(/「AI로 만들기」를 고르면 쓸 수 있습니다/)).toBeTruthy();
  });

  it("AI 를 고르면 지시문을 쓸 수 있다", () => {
    show();
    pickAi();
    expect((screen.getByLabelText("자연어 지시") as HTMLTextAreaElement).disabled).toBe(false);
  });

  it("지시문이 비면 AI 시작이 잠기고 이유가 붙는다 (조건 C14)", () => {
    show();
    pickAi();
    expect(act("ai.start").disabled).toBe(true);
    expect(screen.getByText(/지시문을 쓰면 시작할 수 있습니다/)).toBeTruthy();
  });

  it("Step 조작은 감추지 않고 이유와 해소 방법을 갖는다 (FR-260)", () => {
    show();
    expect(el('[data-disabled-reason="step.addAssertion"]')).not.toBeNull();
    expect(screen.getAllByText(/아직 시작하지 않았습니다/).length).toBeGreaterThan(0);
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
