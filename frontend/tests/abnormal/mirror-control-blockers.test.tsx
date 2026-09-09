/**
 * 조작할 수 없는 **모든** 상황에서 사유가 화면에 있다 (010 T081 · SC-516).
 *
 * > SC-516: 미러에서 조작할 수 없는 상황(관찰 국면·강등·끊김·세션 종료) 전부에서
 * > 사용자가 이유를 화면에서 읽을 수 있다. **조용히 아무 일도 일어나지 않는 경우가 0건**
 * > 이다.
 *
 * ## 왜 전수인가
 *
 * 한 상황을 빠뜨리면 그 상황에서만 조용히 실패한다. 그리고 조용한 실패는 **재현하기
 * 전까지 아무도 모른다** — 사용자는 제품이 고장난 것으로 읽고 클릭을 반복한다.
 *
 * 그래서 목록을 눈으로 세지 않고 **표에서 만든다.** 국면은 `PHASES` 에서, 런타임 사정은
 * 아래 `RUNTIME_BLOCKERS` 에서 온다. 국면을 더하면 이 파일이 자동으로 그것을 센다.
 *
 * ## 무엇이 「사유가 있다」인가
 *
 * 셋을 모두 만족해야 한다.
 *
 * 1. 조작이 **꺼져 있다** — 켜 두고 클릭을 무시하면 사용자는 클릭해 보고 나서 안다
 *    (FR-319 가 금지한다).
 * 2. **사유가 비어 있지 않다** (FR-234).
 * 3. 그 사유가 **화면에 실제로 그려진다** — 표에만 있고 화면에 없으면 사용자에게는 없다.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MirrorView } from "../../src/components/MirrorView";
import { capabilitiesFor, type CapabilityFacts } from "../../src/lib/capabilities";
import { PHASES, type Phase } from "../../src/lib/phase";

/** 미러가 정상인 상태. 국면만으로 갈리는 경우를 보려면 나머지를 참으로 둔다. */
const HEALTHY: CapabilityFacts = {
  mirrorFrameSeen: true,
  mirrorLive: true,
  controlChannelOpen: true,
  controlSurfaceIsMirror: true,
};

/**
 * 국면과 무관한 사정 (contracts/mirror-control.md §1 런타임 덮어쓰기).
 *
 * **국면 열에 적지 않는 이유**가 여기 있다 — 국면마다 표에 적으면 한 국면이 빠지고,
 * 빠진 국면에서 화면은 쓸 수 없는 조작을 활성으로 그린다 (research R9).
 */
const RUNTIME_BLOCKERS: { name: string; facts: CapabilityFacts }[] = [
  { name: "프레임 없음 (FR-333)", facts: { ...HEALTHY, mirrorFrameSeen: false } },
  { name: "프레임 끊김 (FR-346)", facts: { ...HEALTHY, mirrorLive: false } },
  { name: "조작 통로 미접속", facts: { ...HEALTHY, controlChannelOpen: false } },
  { name: "실제 창에서 조작 중 (FR-350)", facts: { ...HEALTHY, controlSurfaceIsMirror: false } },
  { name: "세션 유실 (FR-347)", facts: { ...HEALTHY, sessionLost: true } },
  { name: "아무것도 모름", facts: {} },
];

/** 조작 국면 — 여기서는 켜져 있어야 한다 (FR-314). */
const CONTROL_PHASES: Phase[] = ["recording", "takeover", "paused"];

describe("SC-516 — 조작할 수 없는 모든 상황에 사유가 있다", () => {
  it("**국면**: 조작 국면이 아닌 곳은 전부 꺼져 있고 사유를 갖는다", () => {
    const silent: string[] = [];
    for (const phase of PHASES) {
      const state = capabilitiesFor(phase, HEALTHY)["mirror.control"];
      if (CONTROL_PHASES.includes(phase)) {
        expect(state.kind, `${phase} 는 조작 국면인데 꺼져 있다`).toBe("enabled");
        continue;
      }
      if (state.kind === "enabled") {
        silent.push(`${phase}: 조작 국면이 아닌데 켜져 있다`);
      } else if (state.kind === "disabled" && state.reason.trim() === "") {
        silent.push(`${phase}: 꺼져 있는데 사유가 비었다`);
      }
      // `not_applicable` 은 그 국면의 조작이 아니라는 뜻이고, 근거(N1~N3)는
      // `CapabilityCoverage` 가 이미 센다. 여기서 중복해 세지 않는다.
    }
    expect(silent, `조용히 실패하는 국면이 있다:\n${silent.join("\n")}`).toEqual([]);
  });

  it("**런타임 사정**: 여섯 가지 전부 꺼져 있고 사유를 갖는다", () => {
    const silent: string[] = [];
    for (const { name, facts } of RUNTIME_BLOCKERS) {
      const state = capabilitiesFor("recording", facts)["mirror.control"];
      if (state.kind !== "disabled") {
        silent.push(`${name}: ${state.kind} — 꺼져 있어야 한다`);
      } else if (state.reason.trim() === "") {
        silent.push(`${name}: 사유가 비었다`);
      }
    }
    expect(silent, `조용히 실패하는 사정이 있다:\n${silent.join("\n")}`).toEqual([]);
  });

  it("**화면**: 사유가 표에만 있지 않고 실제로 그려진다 (FR-234)", () => {
    /*
      표가 옳아도 화면이 그리지 않으면 사용자에게는 없는 것이다. `CapabilityUI` 가 같은
      질문을 국면 화면 전체에 던지고, 여기서는 미러 하나를 사정마다 확인한다.
    */
    for (const { name, facts } of RUNTIME_BLOCKERS) {
      const caps = capabilitiesFor("recording", facts);
      const { unmount } = render(
        <MirrorView
          frame={facts.mirrorFrameSeen === true ? "AAAABBBB" : null}
          phase="manipulation"
          geometry={{ width: 800, height: 600 }}
          control={caps["mirror.control"]}
          useWindowCapability={caps["mirror.useWindow"]}
          surface={facts.controlSurfaceIsMirror === false ? "window" : "mirror"}
        />,
      );
      const reason = document.querySelector('[data-disabled-reason="mirror.control"]');
      expect(reason, `${name}: 사유가 화면에 없다`).not.toBeNull();
      expect(
        (reason?.textContent ?? "").trim().length,
        `${name}: 사유 자리는 있는데 비어 있다`,
      ).toBeGreaterThan(0);
      unmount();
    }
  });

  it("**미러가 중단된 상태**에서도 사유가 보인다 (FR-347)", () => {
    /*
      세션이 끝나면 프레임 대신 중단 사유를 그린다. 그 화면에서 사용자가 마지막 프레임을
      클릭할 수는 없지만, 왜 조작할 수 없는지는 읽을 수 있어야 한다.
    */
    render(
      <MirrorView
        frame="AAAABBBB"
        phase="terminated"
        stoppedReason="세션을 종료했습니다."
        control={capabilitiesFor("result", HEALTHY)["mirror.control"]}
      />,
    );
    expect(screen.getByText("세션을 종료했습니다.")).toBeDefined();
    expect(screen.queryByAltText(/대상 브라우저 화면/)).toBeNull();
  });

  it("**강등 상태는 막지 않는다** — 사실과 전환 수단을 같은 자리에 둔다 (FR-345·FR-353a)", () => {
    /*
      1 FPS 로도 조작은 전달된다. 막아 버리면 막힌 사용자에게 남는 수단이 없어진다.
      말해야 하는 것은 「지금 조작은 정확하지 않을 수 있다」이고, 그것을 읽은 자리에서
      바로 전환할 수 있어야 한다.
    */
    const caps = capabilitiesFor("recording", HEALTHY);
    expect(caps["mirror.control"].kind).toBe("enabled");

    render(
      <MirrorView
        frame="AAAABBBB"
        phase="manipulation"
        degradedReason="스크린캐스트를 시작할 수 없어 1초에 한 장으로 표시합니다."
        geometry={{ width: 800, height: 600 }}
        control={caps["mirror.control"]}
        useWindowCapability={caps["mirror.useWindow"]}
      />,
    );
    expect(screen.getByText("1 FPS")).toBeDefined();
    expect(screen.getByText(/1초에 한 장으로 표시합니다/)).toBeDefined();
    // 사실을 읽은 **그 자리**에 전환 수단이 있다.
    const degradedRow = screen.getByText("1 FPS").closest(".row");
    expect(
      degradedRow?.querySelector('[data-action="mirror.useWindow"]'),
      "강등 안내 옆에 전환 수단이 없다 (FR-353a)",
    ).not.toBeNull();
  });

  it("**막힌 사정 전부에서 실제 창 전환이 살아 있다** (FR-353a)", () => {
    /*
      막히는 상황일수록 내려갈 길이 열려 있어야 한다. 그것이 이 기능의 안전망이고,
      그 길까지 잠그면 사용자에게 남는 것이 없다.
    */
    const locked: string[] = [];
    for (const { name, facts } of RUNTIME_BLOCKERS) {
      /*
        둘을 제외한다.

        - **「아무것도 모름」**: 세션 자체를 모르는 상태다. 전환을 제안할 근거가 없다.
        - **세션 유실**: 막힌 것이 아니라 **사라진 것이다.** 옮겨 갈 세션이 없으므로
          전환은 뜻을 잃는다. 그때 남는 길은 새로 실행하는 것이고, 권한표의 `remedy` 가
          그것을 가리킨다 (O3).
      */
      if (Object.keys(facts).length === 0 || facts.sessionLost === true) continue;
      const state = capabilitiesFor("recording", facts)["mirror.useWindow"];
      if (state.kind !== "enabled") locked.push(`${name}: ${state.kind}`);
    }
    expect(locked, `막힌 상황에서 전환까지 잠갔다:\n${locked.join("\n")}`).toEqual([]);
  });
});
