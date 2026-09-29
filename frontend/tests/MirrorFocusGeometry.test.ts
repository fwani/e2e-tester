/**
 * AI 가 만진 자리의 좌표 변환 (024 T016·T017 · FR-012·FR-017·FR-019).
 *
 * ## 왜 라운드트립을 재는가
 *
 * **변환식은 자기 자신과만 맞으면 어떤 단위 검증이든 통과한다.** 정변환이 통째로
 * 틀려도, 그 틀린 식으로 기대값을 적으면 초록색이 된다. 좌표가 한 칸 어긋난 것은 눈으로
 * 잘 안 보이므로 사람도 잡지 못한다.
 *
 * 그래서 재는 것은 「정변환이 이 값을 준다」가 아니라 **「정변환과 역변환이 서로의
 * 역이다」**이다. 역변환은 이미 실제 클릭으로 검증된 식이므로(SC-512, 밀집 요소 3/3),
 * 그것과 짝이 맞으면 정변환도 맞다.
 *
 * 두 식이 **같은 파일**에 있는 이유가 이것이다 (024 research R3). 떨어뜨려 두면 한쪽만
 * 고쳐지는 날이 오고, 그때 사용자가 클릭한 자리와 제품이 그린 자리가 갈린다.
 *
 * ## 조건은 `MirrorInput.test.ts` 와 같은 것을 쓴다
 *
 * 배율이 비정수인 축소 프레임(1.4995 × 1.5). 정수 배율에서만 재면 나눗셈이 어긋나는
 * 경우를 통째로 놓친다.
 */
import { describe, expect, it } from "vitest";

import {
  toDisplayRect,
  toTargetPoint,
  type DisplayBox,
  type FrameGeometry,
} from "../src/components/mirror/useMirrorInput";

/** research R3 측정 2 — 뷰포트 1600×1200 을 1067×800 으로 축소한 실제 프레임. */
const FRAME: FrameGeometry = { width: 1600, height: 1200, pageScale: 1, offsetTop: 0 };

const BOX: DisplayBox = {
  naturalWidth: 1067,
  naturalHeight: 800,
  clientWidth: 1067,
  clientHeight: 800,
  left: 0,
  top: 0,
};

/** 창이 더 좁아 프레임이 한 번 더 줄어든 경우 — 배율이 두 겹으로 쌓인다. */
const SHRUNK: DisplayBox = { ...BOX, clientWidth: 800, clientHeight: 600 };

describe("정변환과 역변환은 서로의 역이다 (T016)", () => {
  const cases: Array<{ name: string; box: DisplayBox }> = [
    { name: "프레임을 그대로 그린 경우", box: BOX },
    { name: "창이 좁아 한 번 더 줄어든 경우", box: SHRUNK },
  ];

  for (const { name, box } of cases) {
    it(`${name} — 자리의 좌상단을 되돌리면 제자리다`, () => {
      // 대상 화면의 작은 요소 하나. 12픽셀은 research R3 이 3/3 맞힌 밀집 요소 크기다.
      const target = { x: 612, y: 448, width: 12, height: 12 };

      const placed = toDisplayRect(target, box, FRAME);
      expect(placed).not.toBeNull();

      // 표시 좌표는 이미지 기준이므로, 되돌릴 때 이미지의 위치를 더해 준다.
      const back = toTargetPoint(
        { clientX: box.left + placed!.left, clientY: box.top + placed!.top },
        box,
        FRAME,
      );
      expect(back).not.toBeNull();
      // 반올림이 양쪽에서 한 번씩 일어난다. 2픽셀이 그 상한이다.
      expect(Math.abs(back!.x - target.x)).toBeLessThanOrEqual(2);
      expect(Math.abs(back!.y - target.y)).toBeLessThanOrEqual(2);
    });

    it(`${name} — 자리의 크기도 같은 배율을 탄다`, () => {
      const placed = toDisplayRect({ x: 0, y: 0, width: 160, height: 120 }, box, FRAME);
      expect(placed).not.toBeNull();
      // 표시 폭 대 대상 폭의 비가 세로에서도 같아야 한다 — 한쪽만 배율을 타면 테두리가
      // 요소보다 납작하거나 길쭉해진다.
      expect(placed!.width / 160).toBeCloseTo(box.clientWidth / FRAME.width, 5);
      expect(placed!.height / 120).toBeCloseTo(box.clientHeight / FRAME.height, 5);
    });
  }

  it("배율이 1 이면 자리가 그대로 나온다", () => {
    const box: DisplayBox = {
      naturalWidth: 1280,
      naturalHeight: 800,
      clientWidth: 1280,
      clientHeight: 800,
      left: 0,
      top: 0,
    };
    const frame: FrameGeometry = { width: 1280, height: 800, pageScale: 1, offsetTop: 0 };
    expect(toDisplayRect({ x: 471, y: 243, width: 338, height: 39 }, box, frame)).toEqual({
      left: 471,
      top: 243,
      width: 338,
      height: 39,
    });
  });

  it("상단 오프셋은 세로에만 붙는다 — 역변환과 같다", () => {
    const frame: FrameGeometry = { width: 1280, height: 800, pageScale: 1, offsetTop: 40 };
    const box: DisplayBox = {
      naturalWidth: 1280,
      naturalHeight: 800,
      clientWidth: 1280,
      clientHeight: 800,
      left: 0,
      top: 0,
    };
    const placed = toDisplayRect({ x: 100, y: 140, width: 20, height: 20 }, box, frame);
    expect(placed).toEqual({ left: 100, top: 100, width: 20, height: 20 });
  });
});

describe("그릴 수 없는 자리는 null 이다 (T017)", () => {
  const good = { x: 10, y: 10, width: 20, height: 20 };

  it("크기가 0 이하면 그릴 자리가 없다", () => {
    expect(toDisplayRect({ ...good, width: 0 }, BOX, FRAME)).toBeNull();
    expect(toDisplayRect({ ...good, height: -5 }, BOX, FRAME)).toBeNull();
  });

  it("좌표가 수치가 아니면 그리지 않는다", () => {
    // NaN 은 모든 범위 비교를 거짓으로 만들어 검사를 그대로 통과한다 — 막지 않으면
    // 화면 전체를 덮거나 사라진 테두리가 그려진다.
    expect(toDisplayRect({ ...good, x: Number.NaN }, BOX, FRAME)).toBeNull();
    expect(toDisplayRect({ ...good, height: Number.POSITIVE_INFINITY }, BOX, FRAME)).toBeNull();
  });

  it("프레임 크기가 0 이면 변환할 근거가 없다", () => {
    expect(toDisplayRect(good, BOX, { ...FRAME, width: 0 })).toBeNull();
    expect(toDisplayRect(good, BOX, { ...FRAME, height: 0 })).toBeNull();
  });

  it("이미지가 아직 그려지지 않았으면 변환하지 않는다", () => {
    // jsdom 은 이미지를 해독하지 않아 자연 크기가 0 이다. 실제 화면에서도 첫 프레임이
    // 붙기 전에 같은 상태가 된다.
    expect(toDisplayRect(good, { ...BOX, naturalWidth: 0 }, FRAME)).toBeNull();
    expect(toDisplayRect(good, { ...BOX, clientHeight: 0 }, FRAME)).toBeNull();
  });
});

describe("화면 밖의 자리 (T047 · FR-019)", () => {
  it("표시 영역과 겹치는 부분이 없으면 그리지 않는다", () => {
    // 스크롤 아래에 있는 요소. 실측에서 뷰포트 높이 800 인 화면의 요소가 y=2008 로 왔다.
    expect(toDisplayRect({ x: 100, y: 2008, width: 80, height: 30 }, BOX, FRAME)).toBeNull();
    // 위로 지나간 요소.
    expect(toDisplayRect({ x: 100, y: -200, width: 80, height: 30 }, BOX, FRAME)).toBeNull();
    // 가로로 벗어난 경우.
    expect(toDisplayRect({ x: 3000, y: 100, width: 80, height: 30 }, BOX, FRAME)).toBeNull();
  });

  it("일부만 벗어나면 그대로 준다 — 잘라 내거나 밀어 넣지 않는다", () => {
    // 가장자리에 걸친 요소. 보이는 부분은 사실이므로 그린다. 화면 안으로 밀어 넣으면
    // 사용자가 엉뚱한 요소를 조작 대상으로 읽는다.
    const placed = toDisplayRect({ x: -20, y: 100, width: 80, height: 30 }, BOX, FRAME);
    expect(placed).not.toBeNull();
    expect(placed!.left).toBeLessThan(0);
    expect(placed!.left + placed!.width).toBeGreaterThan(0);
  });
});
