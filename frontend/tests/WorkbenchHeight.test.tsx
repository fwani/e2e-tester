/**
 * 작업 화면의 높이는 창에 맞고, Step 목록이 스크롤한다 (사용자 보고 · 2026-09-09).
 *
 * ## 보고된 것
 *
 * > 스텝이 늘어날수록 화면이 길어져서 문제가 있음. 전체 height 는 고정해놓고 태스크는
 * > 스크롤로 처리하는게 좋음.
 *
 * ## 왜 그랬나
 *
 * `Artboard` 가 `minHeight` 만 갖고 있었다. 목록에는 이미 `overflowY: auto` 가 있었지만
 * **부모가 무한히 늘어나면 그 영역도 함께 늘어나** 스크롤할 것이 남지 않는다. 그래서
 * Step 이 쌓일수록 페이지 전체가 길어지고, 헤더·국면 띠·미러가 위로 밀려 올라갔다 —
 * 사용자가 Step 을 볼수록 지금 무엇이 일어나는지를 보지 못하게 된다.
 *
 * ## 이 파일이 재는 것
 *
 * 스크롤은 브라우저의 레이아웃 결과이고 jsdom 은 그것을 계산하지 않는다. 그래서
 * **결과가 아니라 구조**를 잰다 — 높이를 묶는 선언과 스크롤 영역이 제자리에 있는가.
 * 그 둘이 있으면 실제 브라우저에서 스크롤이 성립한다.
 */
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import type { Step } from "../src/types/generated/step";

/** Step 을 넉넉히 만든다 — 화면이 길어지는 조건을 재현한다. */
function manySteps(count: number): Step[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `step-${String(i + 1).padStart(2, "0")}`,
    type: "click",
    label: `버튼 ${i + 1} 클릭`,
    author: "human",
    tab: 0,
    timeout_ms: 10000,
    frame_url: null,
    target: {
      tag: "button",
      test_id: `btn-${i}`,
      role: "button",
      accessible_name: `버튼 ${i + 1}`,
      role_status: "verified",
      label: null,
      text: null,
      stable_attr: null,
      css: { value: `button#b${i}`, status: "verified" },
    },
  })) as unknown as Step[];
}

/** 높이를 창에 묶는 선언이 붙은 요소. `Artboard` 의 안쪽 상자다. */
function boundedBox(): HTMLElement | null {
  for (const el of document.querySelectorAll<HTMLElement>("div")) {
    if (el.style.height === "100dvh") return el;
  }
  return null;
}

/** 세로로 스크롤하는 영역들. */
function scrollAreas(): HTMLElement[] {
  return [...document.querySelectorAll<HTMLElement>("div")].filter(
    (el) => el.style.overflowY === "auto",
  );
}

describe("작업 화면의 높이 (사용자 보고 2026-09-09)", () => {
  it("**Step 이 많아도 화면 높이가 창에 묶인다**", () => {
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ steps: manySteps(60) }) })} />);

    const box = boundedBox();
    expect(
      box,
      "높이를 창에 묶는 선언이 없다 — Step 이 쌓이면 페이지 전체가 길어진다",
    ).not.toBeNull();
  });

  it("Step 이 적을 때와 많을 때의 **높이 선언이 같다**", () => {
    /*
      「내용이 늘면 늘어난다」가 결함이었으므로, 재는 것은 **내용과 무관하게 같은가**다.
      값이 같으면 아트보드는 Step 수를 모른다.
    */
    const { unmount } = render(
      <SessionWorkbench {...sessionProps({ view: sessionView({ steps: manySteps(3) }) })} />,
    );
    const few = boundedBox()?.style.height;
    unmount();

    render(<SessionWorkbench {...sessionProps({ view: sessionView({ steps: manySteps(80) }) })} />);
    const many = boundedBox()?.style.height;

    expect(many).toBe(few);
  });

  it("**목록이 스크롤 영역 안에 있다** — 넘치는 것은 목록이지 화면이 아니다", () => {
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ steps: manySteps(60) }) })} />);

    const areas = scrollAreas();
    expect(areas.length, "세로 스크롤 영역이 하나도 없다").toBeGreaterThan(0);

    // Step 행은 정본의 `.srow` 다. `data-action="step.select"` 는 목록 **패널 전체**의
    // 자리 표시이므로 스크롤 영역보다 바깥에 있다 — 그것으로 재면 늘 실패한다.
    const holdsSteps = areas.some((el) => el.querySelector(".srow") !== null);
    expect(
      holdsSteps,
      "Step 행이 스크롤 영역 밖에 있다 — 목록이 길어지면 화면이 길어진다",
    ).toBe(true);
  });

  it("스크롤 영역이 **자기 높이를 0 으로 줄일 수 있다**", () => {
    /*
      `min-height: 0` 이 없으면 flex 자식은 내용보다 작아지지 않는다 — 스크롤 영역을
      두고도 그것이 내용만큼 늘어나 스크롤이 생기지 않는다. 이 한 줄이 빠지는 것이
      「스크롤이 안 먹는」 가장 흔한 원인이다.
    */
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ steps: manySteps(60) }) })} />);

    const stepArea = scrollAreas().find((el) => el.querySelector(".srow") !== null);
    expect(stepArea).toBeDefined();
    expect(
      stepArea?.style.minHeight,
      "스크롤 영역에 `min-height: 0` 이 없다 — flex 안에서 줄어들지 못한다",
    ).toBe("0");
  });

  it("**창이 기준보다 작으면 최소 높이를 지킨다** — 층이 눌리지 않는다", () => {
    /*
      좁은 창에서 재배치하지 않고 스크롤한다는 기존 정책과 같은 판단이다 (007 FR-218a).
      `minHeight` 를 지우면 작은 창에서 헤더·국면 띠·미러가 눌려 읽을 수 없게 된다.
    */
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ steps: manySteps(60) }) })} />);
    expect(boundedBox()?.style.minHeight).toBe("900px");
  });
});
