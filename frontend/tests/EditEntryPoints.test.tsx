/**
 * 006 T047·T048·T053·T057 — 편집 진입점 (US2 · FR-176·FR-178·FR-180 · SC-304).
 *
 * **이 파일이 지키는 것은 이름과 도착지의 일치다.** 006 이 고친 가장 아픈 것이 그것이었다 —
 * 결과 화면의 「Step 06 고치기」가 **읽기 전용 화면**으로 데려갔다 (E-04). 이름이 「고치기」인
 * 컨트롤이 고칠 수 없는 곳으로 가는 것은 단순한 불편이 아니라 거짓 안내다.
 *
 * 화면 하나를 렌더해 문구를 보는 것으로는 이것을 잡을 수 없다. 그래서 `App` 을 통째로
 * 렌더해 **진입점 → 도착 화면**을 실제로 걷는다.
 */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/App";
import { stubServer } from "./helpers/fakeServer";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("편집 진입점 — 이름과 도착지가 일치한다 (SC-304)", () => {
  it("목록 행 메뉴의 「편집」이 편집 가능한 화면으로 데려간다 (FR-175·FR-178)", async () => {
    stubServer();
    render(<App />);
    await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());

    // 017 T056 — Radix 메뉴는 포인터 누름으로 열린다 (`TestListActions` 의 `openMenu` 주석).
    await userEvent.setup().click(screen.getByLabelText("로그인 추가 동작"));
    // T105 — 누름으로 여는 길은 rAF 를 한 번 거친다.
    await screen.findByRole("menu");
    act(() => screen.getByText("편집").click());

    // 도착한 화면에서 실제로 고칠 수 있다 — 저장 컨트롤이 있다.
    await waitFor(() => expect(screen.getByText("변경 저장")).toBeTruthy());
    expect(screen.getByLabelText("테스트 이름")).toBeTruthy();
  });

  it("결과 화면의 「Step 02 고치기」가 그 Step 이 펼쳐진 편집 화면으로 간다 (FR-176·FR-180)", async () => {
    stubServer();
    window.history.replaceState({}, "", "/?screen=result&test=TC-001");
    render(<App />);

    await waitFor(() => expect(screen.getByText("Step 02 고치기")).toBeTruthy());
    act(() => screen.getByText("Step 02 고치기").click());

    // 편집 가능한 화면이고, Step 02 가 지목·펼쳐져 있다.
    await waitFor(() => expect(screen.getByText("변경 저장")).toBeTruthy());
    expect(screen.getByText("dashboard-open")).toBeTruthy();
    expect(screen.getByLabelText("Step 대기 시간 (ms)")).toBeTruthy();
  });

  it("편집 화면에 「정의 보기」 같은 읽기 전용 도착지가 없다 (FR-177)", async () => {
    stubServer();
    render(<App />);
    await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());

    // 017 T056 — Radix 메뉴는 포인터 누름으로 열린다 (`TestListActions` 의 `openMenu` 주석).
    await userEvent.setup().click(screen.getByLabelText("로그인 추가 동작"));
    /*
      **메뉴가 뜬 뒤에 물어야 뜻이 있다** (T105). 누름으로 여는 길은 rAF 를 한 번 거치므로, 기다리지 않고
      「없다」를 물으면 **아직 열리지 않아서** 통과한다 — 그것은 이 검사가 묻는 것(읽기 전용 도착지를 두지
      않는다)이 아니다.
    */
    await screen.findByRole("menu");
    expect(screen.queryByText("정의 보기")).toBeNull();
  });
});

describe("편집 → 저장 → 재실행 한 바퀴 (US2 · SC-303)", () => {
  it("고쳐 저장한 뒤 그 자리에서 「Step 02부터 실행」을 건다", async () => {
    const calls = stubServer();
    window.history.replaceState({}, "", "/?screen=result&test=TC-001");
    render(<App />);

    await waitFor(() => expect(screen.getByText("Step 02 고치기")).toBeTruthy());
    act(() => screen.getByText("Step 02 고치기").click());
    await waitFor(() => expect(screen.getByLabelText("Step 대기 시간 (ms)")).toBeTruthy());

    fireEvent.change(screen.getByLabelText("Step 대기 시간 (ms)"), {
      target: { value: "5000" },
    });
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());
    await waitFor(() => expect(screen.getByText(/저장했습니다/)).toBeTruthy());

    act(() => screen.getByText("Step 02부터 실행").click());

    // 005 가 만든 단일 실행 경로를 지난다 — 세션 생성 1건 + run-from.
    await waitFor(() => {
      const posts = calls.filter((c) => c.url === "/api/sessions" && c.method === "POST");
      expect(posts).toHaveLength(1);
      expect(posts[0]?.body).toEqual({ mode: "replay", test_id: "TC-001" });
      expect(
        calls.some((c) => c.url.includes("/run-from")),
      ).toBe(true);
    });
  });
});

describe("브라우저 편집 세션 (US3 · FR-200·FR-201 · SC-305)", () => {
  it("「브라우저 열어 Step 02 에서 멈추기」가 pause_before_index 로 세션을 만든다", async () => {
    const calls = stubServer();
    window.history.replaceState({}, "", "/?screen=definition&test=TC-001&step=step-02");
    render(<App />);

    await waitFor(() =>
      expect(screen.getByText("브라우저 열어 Step 02 에서 멈추기")).toBeTruthy(),
    );
    act(() => screen.getByText("브라우저 열어 Step 02 에서 멈추기").click());

    await waitFor(() => {
      const posts = calls.filter((c) => c.url === "/api/sessions" && c.method === "POST");
      expect(posts).toHaveLength(1);
      // 사용자가 「일시정지」를 누른 적이 없다 — 서버가 그 지점에서 멈춰 준다.
      expect(posts[0]?.body).toEqual({
        mode: "replay",
        test_id: "TC-001",
        pause_before_index: 1,
      });
    });
    expect(calls.some((c) => c.url.includes("/pause"))).toBe(false);
  });

  it("주소가 지목한 Step 을 새로고침 뒤에도 펼친다 (FR-181)", async () => {
    stubServer();
    window.history.replaceState({}, "", "/?screen=definition&test=TC-001&step=step-02");
    render(<App />);

    await waitFor(() => expect(screen.getByText("dashboard-open")).toBeTruthy());
  });
});
