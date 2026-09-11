/**
 * L2 대조 보고서가 **낡지 않았고, 남은 불일치가 없는가.** 015 T063 (FR-011 · SC-001).
 *
 * ## 왜 보고서를 검사가 다시 보는가
 *
 * 대조 자체는 브라우저가 있어야 한다 — 캐스케이드와 레이어 순서를 실제로 풀어야
 * 하기 때문이다 (`scripts/design_compare_ba.py`). 그것을 단위 검사에서 매번 돌릴 수는
 * 없으므로 **결과를 저장소에 남긴다.**
 *
 * 저장된 결과에는 함정이 하나 있다. **화면 코드가 바뀌어도 보고서는 그대로다.**
 * 「불일치 0」이라고 적힌 낡은 파일이 남아 있으면 아무 검사도 실패하지 않는 채로
 * 회귀가 들어온다. 그래서 보고서에 소스 digest 를 함께 담고 여기서 다시 계산한다 —
 * L1 의 `CanonMatchesDesign` 과 같은 규약이다.
 *
 * ## 무엇을 보는가
 *
 * 1. **낡지 않았는가** — 지금 화면 코드의 digest 가 보고서의 것과 같은가.
 * 2. **무엇을 대조했는가** — 화면 목록과 속성 수가 남아 있는가 (FR-011).
 * 3. **남은 불일치가 없는가** — 의도된 차이로 **이유와 함께** 등록된 것만 남았는가.
 */
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..");
const REPORT = join(ROOT, "tests", "l2-report.json");

interface Report {
  readonly beforeDigest: string;
  readonly afterDigest: string;
  readonly mergeBase: string;
  readonly screens: string[];
  readonly props: number;
  readonly compared: number;
  readonly mismatches: unknown[];
  readonly intended?: { reason?: string }[];
}

/** `design_compare_ba.py` 의 `source_digest` 와 **같은 규약**이어야 한다. */
function sourceDigest(): string {
  const files: string[] = [];
  const walk = (dir: string): void => {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      if (statSync(full).isDirectory()) walk(full);
      else if (/\.(tsx|ts|css)$/.test(name)) files.push(full);
    }
  };
  walk(join(ROOT, "src"));
  files.sort();
  const parts: string[] = [];
  for (const full of files) {
    parts.push(full.slice(ROOT.length + 1));
    parts.push(readFileSync(full, "utf8"));
  }
  return createHash("sha256").update(parts.join("\n")).digest("hex").slice(0, 16);
}

describe("L2 — 전환 전후 화면이 같다 (SC-001)", () => {
  const report = JSON.parse(readFileSync(REPORT, "utf8")) as Report;

  it("보고서가 낡지 않았다 — 지금 화면 코드로 잰 것이다", () => {
    expect(
      sourceDigest(),
      "L2 보고서가 낡았다. 화면 코드가 바뀐 뒤 대조를 다시 돌리지 않았다.\n" +
        "  backend/.venv/bin/python scripts/design_compare_ba.py --compare\n" +
        "이 상태에서는 「불일치 0」이 지금 화면에 대한 말이 아니다.",
    ).toBe(report.afterDigest);
  });

  it("기준이 지금 이력 안의 지점이다 — 떠도는 커밋과 비교한 보고서가 아니다", () => {
    /*
      **브랜치로 판정하지 않는다.** 1회차는 `git merge-base main HEAD` 와 같은지 봤는데,
      기능 브랜치를 main 에 머지하는 순간 그 값이 HEAD 가 되어 **머지가 이 검사를
      깨뜨렸다.** 브랜치는 옮겨 다니고 사라지지만 커밋은 그렇지 않다.

      물어야 할 것은 그대로다: **보고서의 기준이 지금 이력에 실제로 있는 지점인가.**
      조상이 아니면 다른 계보의 커밋과 비교한 것이고, 그 보고서의 「불일치 0」은
      지금 코드가 어디서 출발했는지에 대한 말이 아니다.
    */
    expect(report.mergeBase, "보고서에 기준 커밋이 없다").toMatch(/^[0-9a-f]{40}$/);
    const known = spawnSync("git", ["cat-file", "-e", `${report.mergeBase}^{commit}`], { cwd: ROOT });
    expect(known.status, `기준 커밋 ${report.mergeBase} 가 이 저장소에 없다`).toBe(0);
    const ancestor = spawnSync("git", ["merge-base", "--is-ancestor", report.mergeBase, "HEAD"], { cwd: ROOT });
    expect(
      ancestor.status,
      `기준 커밋 ${report.mergeBase} 가 HEAD 의 조상이 아니다 — 다른 계보와 비교한 보고서다`,
    ).toBe(0);
  });

  it("무엇을 대조했는지가 남아 있다 (FR-011)", () => {
    // **대조 범위가 줄어들면 「불일치 0」은 쉬워진다.** 화면과 속성의 수를 못 박아
    // 조용히 줄어드는 것을 막는다.
    expect(report.screens.length, "대조한 화면이 줄었다").toBeGreaterThanOrEqual(8);
    expect(report.props, "비교한 속성이 줄었다").toBeGreaterThanOrEqual(56);
    expect(report.compared, "대조한 칸이 줄었다").toBeGreaterThan(30000);
  });

  it("의도되지 않은 불일치가 없다", () => {
    expect(
      report.mismatches,
      "전환 전후 화면이 다르다. 각각이 의도된 것인지 판단하고, 의도된 것이라면\n" +
        "`scripts/design_compare_ba.py` 의 `INTENDED` 에 **이유와 함께** 등록한다.\n" +
        "이유 없이 등록할 수 없다 — 그것이 이 목록이 예외가 아니라 판단인 이유다.",
    ).toEqual([]);
  });

  it("의도된 차이에는 전부 이유가 적혀 있다", () => {
    const empty = (report.intended ?? []).filter((x) => (x.reason ?? "").trim() === "");
    expect(empty, "이유 없이 등록된 차이가 있다").toEqual([]);
  });
});
