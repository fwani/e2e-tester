/**
 * L1 대조 가드 — 정본 시트가 확정 디자인 시트와 **같은 값을 그리는가.** 008 T007.
 *
 * 실제 측정은 `scripts/design_render.py --compare` 가 한다. chromium 으로 두 시트를 같은
 * 마크업에 적용해 `getComputedStyle` 을 읽고 `tests/l1-report.json` 에 남긴다. 이 검사는
 * 그 보고서를 판정한다.
 *
 *     backend/.venv/bin/python scripts/design_render.py --compare
 *
 * ## 왜 검사가 직접 재지 않는가
 *
 * jsdom 은 **레이아웃을 계산하지 않는다.** `.btn` 의 높이를 32px 로 알려주지 못하므로
 * 여기서 재면 잰 것이 아니다. 실제 브라우저가 필요하고, 그것은 이미 backend 가 가진
 * playwright 다 — 새 의존성을 들이지 않았다.
 *
 * ## 낡은 보고서로 통과할 수 없다
 *
 * 보고서는 입력의 digest 를 함께 담는다. 정본이 바뀌었는데 다시 재지 않으면 digest 가
 * 어긋나고 이 검사가 실패한다. 확정 디자인 쪽 변경은 `scripts/design_baseline.py` 가
 * 먼저 멈춘다 (FR-280 · DC-D) — 양쪽에서 조인다.
 */
import { describe, expect, it } from "vitest";

import tokens from "../src/theme/tokens.css?raw";
import reportJson from "./l1-report.json";

/**
 * 보고서가 「불일치 0건」일 때 JSON 의 배열이 `never[]` 로 좁혀져 항목을 읽을 수 없다.
 * 형태를 명시해 **불일치가 생겼을 때의 메시지가 컴파일되도록** 둔다 — 그 메시지가
 * 실제로 필요한 순간에 타입 오류로 막히면 안 된다.
 */
interface L1Mismatch {
  form: string;
  prop: string;
  expected: string;
  observed: string;
}
const report = reportJson as {
  canonDigest: string;
  designDigest: string;
  forms: number;
  props: number;
  compared: number;
  mismatches: L1Mismatch[];
};

/** SHA-256 앞 16자리. `scripts/design_render.py` 의 `digest()` 와 같은 규칙이다. */
async function digest(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 16);
}

describe("L1 — 정본 시트 ↔ 확정 디자인 시트", () => {
  it("보고서가 현재 정본을 잰 것이다 (낡은 보고서로 통과할 수 없다)", async () => {
    expect(
      await digest(tokens),
      "tokens.css 가 바뀌었는데 L1 을 다시 재지 않았다.\n" +
        "  backend/.venv/bin/python scripts/design_render.py --compare",
    ).toBe(report.canonDigest);
  });

  it("계산값 불일치가 0건이다", () => {
    const lines = report.mismatches
      .map((m) => `  .${m.form} ${m.prop}: 기준 ${m.expected} ≠ 관측 ${m.observed}`)
      .join("\n");
    expect(report.mismatches.length, `정본이 확정 디자인과 다르다:\n${lines}`).toBe(0);
  });

  it("빈 대조가 통과로 보이지 않는다 — 형태와 속성을 실제로 쟀다", () => {
    // 측정이 0칸이면 「불일치 0건」은 아무것도 뜻하지 않는다. 002 가 CSS 임포트를 빈
    // 값으로 바꿔 단언이 빈 문자열을 상대로 통과하던 것과 같은 함정이다.
    expect(report.forms).toBeGreaterThanOrEqual(25);
    expect(report.props).toBeGreaterThanOrEqual(20);
    expect(report.compared).toBe(report.forms * report.props);
  });
});
