/**
 * T027 — 화면 면 검증이 낸 실패를 고정한다 (003 AP-003 · AP-032).
 *
 * 실브라우저 계층(`backend/tests/abnormal/test_ui_surface.py`)이 이 두 결함을 잡았다.
 * 여기서 한 번 더 보는 이유는 **빠르기** 다 — 실브라우저는 제품 서버와 화면을 둘 다
 * 띄우므로 한 번 돌리는 데 1분이 넘는다. 화면 하나를 고칠 때마다 그것을 기다리면
 * 사람이 검증을 건너뛰게 된다.
 *
 * 두 계층은 서로를 대체하지 않는다. 실브라우저는 "실제로 그렇게 보이는가" 를 보고,
 * 이 검증은 "그 조건이 코드에 남아 있는가" 를 본다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectSetup } from "../../src/pages/ProjectSetup";

// `?raw` 로 원문을 읽는다 — `error-notice.test.tsx` 와 같은 방식이다. 세션 화면을 통째로
// 그리려면 실시간 통로와 미러까지 흉내 내야 하고, 그러면 이 검증이 무엇을 재는지 흐려진다.
// 실제로 그렇게 보이는가는 실브라우저 계층(AS-037)이 본다.
const SESSION_SCREEN_SOURCE = (
  import.meta.glob("../../src/pages/SessionScreen.tsx", {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>
)["../../src/pages/SessionScreen.tsx"];

function stubFetch(routes: Record<string, unknown>) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const key = Object.keys(routes).find((k) => url.startsWith(k));
    const body = key === undefined ? null : routes[key];
    return Promise.resolve({
      ok: body !== null,
      status: body === null ? 404 : 200,
      text: () => Promise.resolve(body === null ? "" : JSON.stringify(body)),
    } as Response);
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", stubFetch({ "/api/project/list": { projects: [], warning: null } }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("막힌 조작은 왜 막혔는지 말한다 (AP-003)", () => {
  it("프로젝트 만들기가 눌리지 않는 이유를 화면에 쓴다", async () => {
    render(<ProjectSetup onOpened={() => undefined} />);

    fireEvent.click(await screen.findByRole("button", { name: /새 프로젝트 만들기/ }));

    // `jest-dom` 을 두지 않은 저장소라 속성을 직접 본다 (다른 검증들과 같은 방식).
    const submit = screen.getByRole("button", { name: /만들기/ }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);

    // **비어 있는 것이 무엇인지 그 자리에서 말한다.** 이 안내가 없으면 사용자는 눌리지
    // 않는 버튼과 마주 앉아 무엇이 빠졌는지 짐작해야 한다.
    // 라벨에도 같은 문구가 있으므로 **안내 자리 하나만** 읽는다. 화면 어딘가에
    // 그 낱말이 있다는 사실이 아니라, 사유 자리가 그것을 말하는지가 판정 대상이다.
    const blockers = () => document.getElementById("create-blockers")?.textContent ?? "";
    expect(blockers()).toMatch(/아직 만들 수 없습니다/);
    expect(blockers()).toMatch(/프로젝트 이름/);

    // 이름만 채우면 남은 하나를 말한다 — "다 채우세요" 로 뭉개지 않는다.
    fireEvent.change(screen.getByLabelText("프로젝트 이름"), {
      target: { value: "데이터 플랫폼" },
    });
    expect(blockers()).toMatch(/기본 시작 URL/);
    expect(blockers()).not.toMatch(/프로젝트 이름/);

    fireEvent.change(screen.getByLabelText("기본 시작 URL"), {
      target: { value: "https://example.internal/login" },
    });
    expect(blockers()).toMatch(/만들 준비가 되었습니다/);
    expect((screen.getByRole("button", { name: /만들기/ }) as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it("사유 안내를 버튼이 가리킨다 — 화면 읽기 도구가 둘을 잇는다", async () => {
    render(<ProjectSetup onOpened={() => undefined} />);
    fireEvent.click(await screen.findByRole("button", { name: /새 프로젝트 만들기/ }));

    const submit = screen.getByRole("button", { name: /만들기/ });
    const described = submit.getAttribute("aria-describedby");
    expect(described).toBeTruthy();
    expect(document.getElementById(described as string)?.textContent).toMatch(
      /아직 만들 수 없습니다/,
    );
  });
});

describe("AI 실패 사유는 화면을 떠나지 않는다 (AP-032 · DR-020)", () => {
  it("세션 화면이 AI 화면을 그리지 않는 상태에서도 사유를 내보낸다", async () => {
    // 이 조건을 코드에서 확인한다. AI 수행이 실패하면 세션이 검토를 위해 `paused` 로
    // 옮겨가고, 그러면 AI 화면이 선택되지 않는다. 사유가 그 화면에서만 그려지면
    // 사용자에게는 "아무 일도 일어나지 않음" 으로 보인다 — 001 이 그랬고 002 가 고쳤지만
    // 구멍이 `paused` 로 옮겨졌을 뿐이다.
    const source = SESSION_SCREEN_SOURCE;
    expect(source).toMatch(/aiError !== null && !showsAiScreen/);
    expect(source).toMatch(/const showsAiScreen = isAiSession && !isPaused && !isTakeover/);
  });
});
