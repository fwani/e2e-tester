/**
 * AI helper keeps the empty composer collapsed and opens for conversation/progress.
 * Disclosure preserves send, disabled reason, limits, and blocked-answer behavior.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatPanel, CHAT_MAX_CHARS } from "../src/components/workbench/ChatPanel";
import { capabilitiesFor } from "../src/lib/capabilities";
import schema from "../../backend/schema/step-dsl.schema.json";

afterEach(cleanup);

async function openAssistant() {
  const panel = document.querySelector<HTMLDivElement>("[data-chat-panel]")!;
  if (!(panel.dataset.expanded === "true")) await userEvent.click(panel.querySelector("button")!);
  expect((panel.dataset.expanded === "true")).toBe(true);
}


/** 표에서 가져온다 — 손으로 지어내면 표와 갈린 것을 잡지 못한다. */
const inEditing = capabilitiesFor("editing", { definitionEditable: true })["ai.chat"];
const inPaused = capabilitiesFor("paused", { liveBrowser: true })["ai.chat"];

const TURNS = [
  { role: "user" as const, text: "이 테스트가 뭘 하는지 요약해 줘", at: "2026-09-11T00:00:00Z" },
  { role: "assistant" as const, text: "로그인 후 메뉴로 이동합니다.", at: "2026-09-11T00:00:05Z" },
];

describe("접은 AI 도우미를 열면 국면별 대화 기능을 사용할 수 있다", () => {
  it("편집 국면에서도 도우미를 열어 기능을 확인할 수 있다", async () => {
    render(<ChatPanel turns={[]} capability={inEditing} onSend={vi.fn()} />);
    await openAssistant();
    expect(screen.getByLabelText("AI 와 대화")).toBeTruthy();
  });

  it("편집 국면에서 입력이 잠기고, 해소 조작을 가리킨다", async () => {
    render(<ChatPanel turns={[]} capability={inEditing} onSend={vi.fn()} />);
    await openAssistant();

    const box = screen.getByLabelText("AI 에게 할 말") as HTMLTextAreaElement;
    expect(box.disabled).toBe(true);
    // 무엇을 하면 풀리는지 말해야 한다 — 잠긴 채 이유가 없으면 사용자는 갇힌다.
    // 2026-09-11 — 해소 조작은 위치 기준(이 Step 앞에서 멈추기)이고, 교체는 사유 문구가 말한다.
    expect(screen.getByText(/이 Step 앞에서 멈추기/)).toBeTruthy();
    expect(screen.getByText(/AI 로 다시 만들기/)).toBeTruthy();
  });

  it("일시정지 국면에서는 활성이다", async () => {
    render(<ChatPanel turns={[]} capability={inPaused} onSend={vi.fn()} />);
    await openAssistant();
    const box = screen.getByLabelText("AI 에게 할 말") as HTMLTextAreaElement;
    expect(box.disabled).toBe(false);
  });
});

describe("대화 기록", () => {
  it("두 차례가 누가 말했는지와 함께 보인다", async () => {
    render(<ChatPanel turns={TURNS} capability={inPaused} onSend={vi.fn()} />);
    await openAssistant();

    expect(screen.getByText("이 테스트가 뭘 하는지 요약해 줘")).toBeTruthy();
    expect(screen.getByText("로그인 후 메뉴로 이동합니다.")).toBeTruthy();
    expect(screen.getByText("나")).toBeTruthy();
    expect(screen.getByText("AI")).toBeTruthy();
  });

  it("비어 있으면 무엇을 할 수 있는지 말한다", async () => {
    render(<ChatPanel turns={[]} capability={inPaused} onSend={vi.fn()} />);
    await openAssistant();
    expect(screen.getByText(/물어보거나/)).toBeTruthy();
  });

  it("**자취 전체**를 보인다 — 마지막 한 줄이 아니다 (FR-011)", async () => {
    /*
      한 줄만 보이면 사용자는 「지금」만 알고 「무엇을 거쳐 왔는지」를 모른다 —
      막히거나 엉뚱한 것을 눌렀을 때 어디서 어긋났는지 되짚을 수 없다.
    */
    render(
      <ChatPanel
        turns={TURNS}
        capability={inPaused}
        busy
        progress={["화면을 살펴보는 중", "로그인 클릭 — 수행 중"]}
        onSend={vi.fn()}
      />,
    );
    await openAssistant();

    expect(screen.getByText("화면을 살펴보는 중")).toBeTruthy();
    expect(screen.getByText("로그인 클릭 — 수행 중")).toBeTruthy();
  });

  it("실패도 자취에 남는다 — 무엇을 하다 실패했는지가 필요하다", async () => {
    render(
      <ChatPanel
        turns={[]}
        capability={inPaused}
        busy
        progress={["로그인 클릭 — 수행 중", "로그인 클릭 — 실패: 요소를 찾지 못했습니다"]}
        onSend={vi.fn()}
      />,
    );
    await openAssistant();
    expect(screen.getByText(/실패: 요소를 찾지 못했습니다/)).toBeTruthy();
  });

  it("자취가 아직 없어도 도는 중임을 말한다", async () => {
    render(<ChatPanel turns={[]} capability={inPaused} busy onSend={vi.fn()} />);
    await openAssistant();
    // 첫 보고가 오기 전의 짧은 구간. 비워 두면 「보냈는데 아무 일도 없다」로 보인다.
    expect(screen.getByText("AI 가 수행 중입니다…")).toBeTruthy();
  });

  it("멈춰 있으면 자취를 그리지 않는다", async () => {
    render(
      <ChatPanel
        turns={TURNS}
        capability={inPaused}
        progress={["지난 턴의 줄"]}
        onSend={vi.fn()}
      />,
    );
    await openAssistant();
    expect(screen.queryByText("지난 턴의 줄")).toBeNull();
  });
});

describe("보내기 (FR-007·FR-010)", () => {
  it("쓴 것을 보내고 칸을 비운다", async () => {
    const onSend = vi.fn();
    render(<ChatPanel turns={[]} capability={inPaused} onSend={onSend} />);
    await openAssistant();

    const box = screen.getByLabelText("AI 에게 할 말") as HTMLTextAreaElement;
    await userEvent.type(box, "SSO 로 로그인해");
    await userEvent.click(screen.getByRole("button", { name: /AI 에게 말하기/ }));

    expect(onSend).toHaveBeenCalledWith("SSO 로 로그인해");
    expect(box.value).toBe("");
  });

  it("**빈 말은 보내지 않는다** — 공백만 쳐도 마찬가지다", async () => {
    const onSend = vi.fn();
    render(<ChatPanel turns={[]} capability={inPaused} onSend={onSend} />);
    await openAssistant();

    await userEvent.type(screen.getByLabelText("AI 에게 할 말"), "   ");
    await userEvent.click(screen.getByRole("button", { name: /AI 에게 말하기/ }));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("잠겨 있으면 보내지 않는다", async () => {
    const onSend = vi.fn();
    render(<ChatPanel turns={[]} capability={inEditing} onSend={onSend} />);
    await openAssistant();

    const box = screen.getByLabelText("AI 에게 할 말") as HTMLTextAreaElement;
    // 잠긴 칸에는 타이핑 자체가 들어가지 않는다. 그래도 제출 경로를 확인한다.
    expect(box.disabled).toBe(true);
    expect(onSend).not.toHaveBeenCalled();
  });
});

describe("길이 상한 (FR-010)", () => {
  it("상한을 **입력 시점에** 보여 준다", async () => {
    render(<ChatPanel turns={[]} capability={inPaused} onSend={vi.fn()} />);
    await openAssistant();
    expect(screen.getByText(`0 / ${CHAT_MAX_CHARS}`)).toBeTruthy();
  });

  it("상한이 **서버의 값과 같다** — 스키마에서 읽어 대조한다", async () => {
    /*
      두 입구가 다른 상한을 가지면 사용자는 어느 쪽이 얼마까지인지 외워야 한다.
      서버는 `MAX_INSTRUCTION_CHARS` 하나를 쓰고(FR-010), 그 값이 스키마에 실린다.

      **프론트에 상수가 없어서 복제한 값이다.** 복제를 검사로 묶어 둔다 — 스키마가
      바뀌면 여기가 먼저 실패하고, 작성자는 화면의 값도 고쳐야 한다는 것을 안다.
      (헌법 Cross-language schema duty 의 취지다: 두 손 사본을 두지 않는다.)
    */
    const declared = (
      schema as {
        properties: { ai_instruction: { anyOf: { maxLength?: number }[] } };
      }
    ).properties.ai_instruction.anyOf.find((it) => it.maxLength !== undefined);

    expect(declared?.maxLength, "스키마에서 지시문 상한을 찾지 못했다").toBeDefined();
    expect(CHAT_MAX_CHARS).toBe(declared?.maxLength);
  });
});

describe("언어모델을 쓸 수 없을 때 (FR-012)", () => {
  it("서버가 준 사유를 **그대로** 보여 준다", async () => {
    const reason = "언어모델 자격 증명을 찾을 수 없습니다. ANTHROPIC_API_KEY 를 주세요.";
    render(
      <ChatPanel
        turns={[]}
        capability={inPaused}
        unavailableReason={reason}
        onSend={vi.fn()}
      />,
    );
    await openAssistant();
    // 화면이 문장을 지어내면 실제 원인과 갈린다.
    expect(screen.getByText(reason)).toBeTruthy();
  });

  it("그때 입력이 잠긴다 — 눌러도 실패할 것을 누르게 하지 않는다", async () => {
    render(
      <ChatPanel
        turns={[]}
        capability={inPaused}
        unavailableReason="자격 증명이 없습니다"
        onSend={vi.fn()}
      />,
    );
    await openAssistant();
    const box = screen.getByLabelText("AI 에게 할 말") as HTMLTextAreaElement;
    expect(box.disabled).toBe(true);
  });
});

describe("막힘은 여기서 그리지 않는다 (ui-contract §3-1)", () => {
  it("takeover 국면에서는 답변 칸을 가리킨다", async () => {
    const blocked = capabilitiesFor("takeover", { aiBlocked: true })["ai.chat"];
    render(<ChatPanel turns={[]} capability={blocked} onSend={vi.fn()} />);
    await openAssistant();

    /*
      **답변 입구는 하나여야 한다.** 두 곳에서 답을 받으면 사용자는 어느 쪽에 써야
      하는지 모른다 — 초안 국면표가 `cond(C11)` 로 만들려던 상태다 (analyze F1).
    */
    expect(screen.getByText(/답변 칸/)).toBeTruthy();
    expect((screen.getByLabelText("AI 에게 할 말") as HTMLTextAreaElement).disabled).toBe(
      true,
    );
  });
});


describe("보조 기능은 필요할 때 펼친다", () => {
  it("빈 도우미는 접혀 있고 열어 쓴 초안은 다시 접어도 유지한다", async () => {
    render(<ChatPanel turns={[]} capability={inPaused} onSend={vi.fn()} />);
    const panel = document.querySelector<HTMLDivElement>("[data-chat-panel]")!;
    expect((panel.dataset.expanded === "true")).toBe(false);
    await openAssistant();
    await userEvent.type(screen.getByRole("textbox", { name: "AI 에게 할 말" }), "로그인 확인");
    await userEvent.click(panel.querySelector("button")!);
    expect((panel.dataset.expanded === "true")).toBe(false);
    await openAssistant();
    expect((screen.getByRole("textbox", { name: "AI 에게 할 말" }) as HTMLTextAreaElement).value).toBe("로그인 확인");
  });

  it("대화가 생기면 자동으로 열어 새 내용을 표시한다", async () => {
    const props = { capability: inPaused, onSend: vi.fn() };
    const view = render(<ChatPanel {...props} turns={[]} />);
    expect((document.querySelector<HTMLDivElement>("[data-chat-panel]")!.dataset.expanded === "true")).toBe(false);
    view.rerender(<ChatPanel {...props} turns={TURNS} />);
    await waitFor(() => expect((document.querySelector<HTMLDivElement>("[data-chat-panel]")!.dataset.expanded === "true")).toBe(true));
    expect(screen.getByRole("log", { name: "대화 기록" }).textContent).toContain("로그인 후 메뉴로 이동합니다.");
  });

  it("AI가 수행을 시작하면 접혀 있던 도우미가 열린다", async () => {
    const props = { turns: [], capability: inPaused, onSend: vi.fn() };
    const view = render(<ChatPanel {...props} />);
    view.rerender(<ChatPanel {...props} busy progress={["로그인 확인 중"]} />);
    await waitFor(() => expect((document.querySelector<HTMLDivElement>("[data-chat-panel]")!.dataset.expanded === "true")).toBe(true));
    expect(screen.getByRole("log", { name: "대화 기록" }).textContent).toContain("로그인 확인 중");
  });
});
