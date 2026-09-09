/**
 * 미러 좌표 변환 (010 T031·T032 · FR-330~FR-333 · SC-512 · research R3).
 *
 * **이 파일이 SC-512 의 자동 검증이다** — 미러에서 클릭한 요소가 의도한 요소인 비율이
 * 100% 이고, 그것이 밀집 UI(인접 요소 간격 4픽셀 이하)에서도 성립해야 한다.
 *
 * 순수 함수를 재는 이유는 둘이다.
 *
 * 1. **브라우저 없이 잰다.** 컴포넌트를 그려서 재면 이 검증이 jsdom 의 레이아웃 한계에
 *    묶이고, 그러면 배율이 비정수인 축소 프레임을 재현할 수 없다.
 * 2. **실측을 그대로 옮긴다.** research R3 은 뷰포트 1600×1200 을 1067×800 으로 축소한
 *    실제 프레임에서 12px 밀집 요소 3개를 3/3 맞혔다. 그 수치를 여기 그대로 둔다 —
 *    변환식을 고칠 때 무엇을 재현해야 하는지가 코드에 남는다.
 */
import { describe, expect, it } from "vitest";

import {
  createMoveThrottle,
  modifiersOf,
  toTargetPoint,
  type DisplayBox,
  type FrameGeometry,
} from "../src/components/mirror/useMirrorInput";

/**
 * research R3 측정 2 의 실제 조건.
 *
 * 뷰포트 1600×1200 을 `maxWidth 1280 / maxHeight 800` 으로 요청했더니 실제 프레임은
 * **1067×800** 이 됐다 (높이 제약이 먼저 걸린다). 배율은 `1.4995 × 1.5` 로 정수가 아니다.
 *
 * **여기에 1280·800 이 나오지 않는 것이 요점이다** (FR-331). 상한을 배율 계산에 쓰면
 * 틀리고, 그 틀림은 밀집 UI 에서만 드러난다.
 */
const FRAME: FrameGeometry = { width: 1600, height: 1200, pageScale: 1, offsetTop: 0 };

/** 프레임을 표시 크기 그대로 그린 경우 — 축소 프레임 1067×800 이 그대로 보인다. */
const BOX: DisplayBox = {
  naturalWidth: 1067,
  naturalHeight: 800,
  clientWidth: 1067,
  clientHeight: 800,
  left: 0,
  top: 0,
};

/** 표시 좌표를 그 프레임 안에서 계산한다 — 대상 좌표를 표시 좌표로 줄인 값. */
function displayOf(targetX: number, targetY: number, box = BOX, frame = FRAME) {
  return {
    clientX: box.left + (targetX * box.clientWidth) / frame.width,
    clientY: box.top + (targetY * box.clientHeight) / frame.height,
  };
}

describe("좌표 역변환 (FR-330 · research R3)", () => {
  it("축소된 프레임에서 왕복이 의도한 좌표를 낸다", () => {
    // research R3 측정 2 가 쓴 지점.
    const point = toTargetPoint(displayOf(1430, 1115), BOX, FRAME);
    expect(point).not.toBeNull();
    expect(point!.x).toBe(1430);
    expect(point!.y).toBe(1115);
  });

  it("**밀집 요소 3개를 각각 맞힌다** (SC-512 · research R3 측정 3)", () => {
    /*
      12px 짜리 요소 3개를 나란히 둔다. 배율이 1.4995 이므로 표시 좌표에서 이 셋은
      8픽셀 간격이다 — 반올림이 한 칸만 틀려도 옆 요소가 눌린다.

      명세가 요구하는 것은 「인접 요소 간격 4픽셀 이하」를 포함한 집합에서 100% 다.
    */
    const widgets = [
      { name: "첫째", from: 100, to: 112 },
      { name: "둘째", from: 112, to: 124 },
      { name: "셋째", from: 124, to: 136 },
    ];

    for (const widget of widgets) {
      const center = (widget.from + widget.to) / 2;
      const point = toTargetPoint(displayOf(center, 400), BOX, FRAME);
      expect(point, `${widget.name} 의 좌표가 나오지 않았다`).not.toBeNull();
      expect(
        point!.x >= widget.from && point!.x < widget.to,
        `${widget.name}(${widget.from}~${widget.to}) 를 눌렀는데 ${point!.x} 가 나왔다`,
      ).toBe(true);
    }
  });

  it("표시 영역이 프레임보다 작아도 성립한다", () => {
    /*
      화면이 좁아 프레임이 더 줄어 보이는 경우다. 배율이 두 번 걸리므로(프레임 축소 ×
      표시 축소) 여기서 틀리면 좁은 창에서만 좌표가 어긋난다 — 재현하기 어려운 결함이다.
    */
    const shrunk: DisplayBox = { ...BOX, clientWidth: 533, clientHeight: 400 };
    const point = toTargetPoint(displayOf(800, 600, shrunk), shrunk, FRAME);
    expect(point).not.toBeNull();
    expect(Math.abs(point!.x - 800)).toBeLessThanOrEqual(2);
    expect(Math.abs(point!.y - 600)).toBeLessThanOrEqual(2);
  });

  it("표시 영역이 화면 안쪽에 있어도 성립한다 (offset 을 뺀다)", () => {
    const offset: DisplayBox = { ...BOX, left: 240, top: 96 };
    const point = toTargetPoint(displayOf(400, 300, offset), offset, FRAME);
    expect(point).not.toBeNull();
    expect(point!.x).toBe(400);
    expect(point!.y).toBe(300);
  });

  it("**상수 1280·800 을 쓰지 않는다** (FR-331)", () => {
    /*
      요청 상한을 배율 계산에 쓰면 여기서 틀린다. 실제 프레임(1067×800)과 요청
      상한(1280×800)이 가로에서 다르므로, 상한을 쓰면 x 가 약 1.2배 어긋난다.

      코드를 읽어 확인하는 대신 **결과로** 확인한다 — 계산이 어디서 오든 결과가 맞으면
      된다.
    */
    const point = toTargetPoint(displayOf(1500, 100), BOX, FRAME);
    expect(point!.x).toBe(1500);
    expect(point!.x).not.toBeCloseTo((1500 * 1067) / 1280, 0);
  });

  it("페이지 배율과 상단 오프셋을 변환에 포함한다 (FR-331)", () => {
    /*
      실측 환경에서는 각각 1 과 0 이었다. 그 값이 아닌 환경에서만 좌표가 어긋나고
      원인이 드러나지 않는 것을 막기 위해 **값과 무관하게 변환에 넣는다.**
    */
    const scaled: FrameGeometry = { width: 1600, height: 1200, pageScale: 2, offsetTop: 64 };
    const point = toTargetPoint({ clientX: 400, clientY: 300 }, BOX, scaled);
    expect(point).not.toBeNull();
    // 배율 2 → 페이지 좌표는 절반, 오프셋 64 → y 에 더해진다.
    expect(point!.x).toBe(Math.round((400 * (1600 / 1067)) / 2));
    expect(point!.y).toBe(Math.round((300 * (1200 / 800)) / 2 + 64));
  });

  it("쓸 수 없는 배율은 1 로 붙는다 — 0 으로 나누지 않는다", () => {
    const broken: FrameGeometry = { width: 1600, height: 1200, pageScale: 0 };
    const point = toTargetPoint(displayOf(800, 600), BOX, broken);
    expect(point).not.toBeNull();
    expect(Number.isFinite(point!.x)).toBe(true);
    expect(point!.x).toBe(800);
  });
});

describe("전달하지 않는 경우 (T032 · FR-333·FR-341)", () => {
  it("프레임 이미지가 아직 그려지지 않았으면 좌표를 내지 않는다 (FR-333)", () => {
    /*
      `naturalWidth` 가 0 이면 이미지가 아직 디코드되지 않았다. 그 상태의 배율은 무의미
      하고, 무엇을 클릭하는지 볼 수 없는 상태에서 좌표를 보내면 그것은 조작이 아니라
      추측이다.
    */
    const undecoded: DisplayBox = { ...BOX, naturalWidth: 0, naturalHeight: 0 };
    expect(toTargetPoint({ clientX: 10, clientY: 10 }, undecoded, FRAME)).toBeNull();
  });

  it("표시 크기가 0 이면 좌표를 내지 않는다", () => {
    const hidden: DisplayBox = { ...BOX, clientWidth: 0, clientHeight: 0 };
    expect(toTargetPoint({ clientX: 10, clientY: 10 }, hidden, FRAME)).toBeNull();
  });

  it("표시 영역 **밖은 거절한다. 안으로 밀어 넣지 않는다** (FR-341)", () => {
    /*
      밀어 넣으면 사용자가 누르지 않은 요소가 눌리고, 그 클릭이 Step 으로 저장된다.
      무엇이 잘못됐는지는 어디에도 나타나지 않는다. 서버도 같은 이유로 거절한다.
    */
    expect(toTargetPoint({ clientX: -1, clientY: 10 }, BOX, FRAME)).toBeNull();
    expect(toTargetPoint({ clientX: 10, clientY: -1 }, BOX, FRAME)).toBeNull();
    expect(toTargetPoint({ clientX: 1068, clientY: 10 }, BOX, FRAME)).toBeNull();
    expect(toTargetPoint({ clientX: 10, clientY: 801 }, BOX, FRAME)).toBeNull();
  });

  it("경계값은 화면 안이다 — 가장자리를 누를 수 있어야 한다", () => {
    expect(toTargetPoint({ clientX: 0, clientY: 0 }, BOX, FRAME)).not.toBeNull();
    expect(toTargetPoint({ clientX: 1067, clientY: 800 }, BOX, FRAME)).not.toBeNull();
  });

  it("수치가 아닌 좌표는 내보내지 않는다", () => {
    /*
      `NaN` 은 모든 범위 비교를 거짓으로 만들어 화면 밖 검사를 **그대로 통과한다.**
      막지 않으면 `NaN` 이 채널로 나가고 서버가 거절한다 — 사용자가 읽을 필요 없는
      거절 사유가 하나 늘어난다.
    */
    expect(toTargetPoint({ clientX: NaN, clientY: 10 }, BOX, FRAME)).toBeNull();
    expect(
      toTargetPoint({ clientX: 10, clientY: undefined as unknown as number }, BOX, FRAME),
    ).toBeNull();
  });

  it("프레임 크기가 0 이면 좌표를 내지 않는다", () => {
    expect(
      toTargetPoint({ clientX: 10, clientY: 10 }, BOX, { width: 0, height: 0 }),
    ).toBeNull();
  });
});

describe("이동 전송량 억제 (FR-336)", () => {
  it("간격 안의 이동은 미루고, 지난 이동은 보낸다", () => {
    const throttle = createMoveThrottle(40);
    const move = (x: number) => ({ kind: "pointer.move", tab: 0, x, y: 0 });

    expect(throttle.offer(move(1), 1000)).not.toBeNull();
    expect(throttle.offer(move(2), 1010)).toBeNull();
    expect(throttle.offer(move(3), 1020)).toBeNull();
    expect(throttle.offer(move(4), 1050)).toMatchObject({ x: 4 });
  });

  it("**마지막 위치는 반드시 보낸다** — 버리지 않고 미룬다", () => {
    /*
      마우스 올리기로 열리는 메뉴는 포인터가 **머무는 위치**로 판정된다. 마지막 이동을
      버리면 메뉴가 열리지 않고, 사용자에게는 「호버가 안 먹는다」로 보인다.
    */
    const throttle = createMoveThrottle(40);
    const move = (x: number) => ({ kind: "pointer.move", tab: 0, x, y: 0 });

    throttle.offer(move(1), 1000);
    throttle.offer(move(2), 1005);
    throttle.offer(move(9), 1010);

    expect(throttle.flush(1015)).toMatchObject({ x: 9 });
    // 흘린 뒤에는 남은 것이 없다.
    expect(throttle.flush(1020)).toBeNull();
  });
});

describe("수정자 비트 (FR-341)", () => {
  it("서버가 아는 네 비트만 만든다", () => {
    expect(modifiersOf({ altKey: false, ctrlKey: false, metaKey: false, shiftKey: false })).toBe(0);
    expect(modifiersOf({ altKey: true, ctrlKey: false, metaKey: false, shiftKey: false })).toBe(1);
    expect(modifiersOf({ altKey: false, ctrlKey: true, metaKey: false, shiftKey: false })).toBe(2);
    expect(modifiersOf({ altKey: false, ctrlKey: false, metaKey: true, shiftKey: false })).toBe(4);
    expect(modifiersOf({ altKey: false, ctrlKey: false, metaKey: false, shiftKey: true })).toBe(8);
    expect(modifiersOf({ altKey: true, ctrlKey: true, metaKey: true, shiftKey: true })).toBe(15);
  });
});

/* ─── 국면별 조작 가능성 (T040·T056 · FR-315·SC-516) ────────────────────────
 *
 * **화면이 아니라 표가 정한다** (FR-316 · research R9). 그래서 여기서 재는 것은 표다 —
 * 표가 옳으면 `MirrorView` 는 그 결과를 그대로 따른다 (`MirrorView.test.tsx` 가 그
 * 따름을 잰다).
 */

import { capabilitiesFor } from "../src/lib/capabilities";
import { PHASES, type Phase } from "../src/lib/phase";

/** 미러가 정상인 상태 — 국면만으로 갈리는지 보려면 런타임 사정을 전부 참으로 둔다. */
const HEALTHY = {
  mirrorFrameSeen: true,
  mirrorLive: true,
  controlChannelOpen: true,
  controlSurfaceIsMirror: true,
};

describe("국면 × 미러 조작 (contracts/mirror-control.md §1)", () => {
  it("조작 국면 셋에서 켜진다 (FR-314)", () => {
    for (const phase of ["recording", "takeover", "paused"] as Phase[]) {
      const state = capabilitiesFor(phase, HEALTHY)["mirror.control"];
      expect(state.kind, `${phase} 에서 미러 조작이 ${state.kind} 다`).toBe("enabled");
    }
  });

  it("관찰 국면에서 꺼지고 **이유가 있다** (FR-315 · SC-516)", () => {
    /*
      러너·AI 가 전진하는 중에 사람 조작이 끼어들면 같은 Step 이 두 번 돈다.

      감추지 않고 이유를 붙이는 것이 요점이다 — 조용히 아무 일도 일어나지 않는 경우가
      0건이어야 한다.
    */
    for (const phase of ["running", "ai_authoring"] as Phase[]) {
      const state = capabilitiesFor(phase, HEALTHY)["mirror.control"];
      expect(state.kind, `${phase} 에서 미러 조작이 켜져 있다`).toBe("disabled");
      if (state.kind === "disabled") {
        expect(state.reason.length, `${phase} 의 비활성 사유가 비어 있다`).toBeGreaterThan(0);
      }
    }
  });

  it("실행 중에는 **일시정지가 해소 방법이다** (US3)", () => {
    const state = capabilitiesFor("running", HEALTHY)["mirror.control"];
    expect(state.kind).toBe("disabled");
    if (state.kind === "disabled") {
      expect(state.remedy?.action).toBe("run.pause");
    }
  });

  it("여덟 국면 전부가 두 조작에 답을 갖는다 (FR-234)", () => {
    for (const phase of PHASES) {
      const caps = capabilitiesFor(phase, HEALTHY);
      expect(caps["mirror.control"], `${phase} × mirror.control 이 비어 있다`).toBeDefined();
      expect(caps["mirror.useWindow"], `${phase} × mirror.useWindow 가 비어 있다`).toBeDefined();
    }
  });
});

describe("런타임 덮어쓰기 O10~O13 (contracts §1 · T032)", () => {
  const cases: { name: string; facts: Record<string, boolean>; hint: RegExp }[] = [
    {
      name: "프레임을 한 장도 못 받았다 (O10 · FR-333)",
      facts: { ...HEALTHY, mirrorFrameSeen: false },
      hint: /아직 받지 못했습니다/,
    },
    {
      name: "프레임이 끊겼다 (O11 · FR-346)",
      facts: { ...HEALTHY, mirrorLive: false },
      hint: /표시가 멈춘 것입니다/,
    },
    {
      name: "조작 통로가 붙지 않았다 (O12)",
      facts: { ...HEALTHY, controlChannelOpen: false },
      hint: /통로가 준비되지 않았습니다/,
    },
    {
      name: "실제 창에서 조작 중이다 (O13 · FR-350)",
      facts: { ...HEALTHY, controlSurfaceIsMirror: false },
      hint: /실제 브라우저 창에서 조작하고 있습니다/,
    },
  ];

  for (const { name, facts, hint } of cases) {
    it(`${name} — 꺼지고 사유가 있다`, () => {
      const state = capabilitiesFor("recording", facts)["mirror.control"];
      expect(state.kind).toBe("disabled");
      if (state.kind === "disabled") expect(state.reason).toMatch(hint);
    });
  }

  it("**넷 다 실제 창 전환을 막지 않는다** (FR-353a)", () => {
    /*
      막히는 상황일수록 실제 창으로 내려가는 수단이 살아 있어야 한다. 그것이 이 기능의
      안전망이고, 그 수단까지 잠그면 막힌 사용자에게 남는 것이 없다.
    */
    for (const { name, facts } of cases) {
      const state = capabilitiesFor("recording", facts)["mirror.useWindow"];
      expect(state.kind, `${name} 에서 실제 창 전환까지 잠갔다`).toBe("enabled");
    }
  });

  it("모르는 사정은 **거짓으로 읽힌다** — 모르는 것을 활성으로 그리지 않는다", () => {
    /*
      `CapabilityFacts` 의 규칙이다. 이름을 참인 방향으로 지은 이유가 여기 있다 —
      `mirrorNoFrame` 이라 지었다면 `undefined` 가 「프레임이 있다」로 읽힌다.
    */
    const state = capabilitiesFor("recording", {})["mirror.control"];
    expect(state.kind).toBe("disabled");
  });
});
