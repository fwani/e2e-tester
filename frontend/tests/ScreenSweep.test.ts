/**
 * 화면 깨짐 순회 보고서가 **낡지 않았고, 깨짐이 남지 않았는가.** 017 T017
 * (contracts/screen-sweep.md SW-8 · FR-025 · FR-026 · SC-001~SC-003).
 *
 * ## 왜 보고서를 검사가 다시 보는가
 *
 * 순회는 제품 서버·개발 서버·chromium 을 띄워야 한다 (`scripts/screen_sweep.py`). 단위 검사에서
 * 매번 돌릴 수 없으므로 **결과를 저장소에 남기고** 여기서 판정한다 — L2 의 `BeforeAfterParity` 와
 * 같은 규약이다. 화면 코드가 바뀌면 보고서는 낡으므로 소스 digest 로 그것을 잡는다.
 *
 * ## L2 와 무엇이 다른가
 *
 * L2 는 「전환 전과 같은가」다. 전환 전 화면이 이미 깨져 있으면 그 깨짐까지 같다고 통과시킨다 —
 * B-01(알림이 국면 띠를 덮는다)이 그 경우였다. 순회는 판정 규칙(SW-6)으로 「그 자체로 깨지지
 * 않았는가」를 본다. 둘 다 초록이어야 끝이다.
 *
 * ## 알려진 깨짐 등록부
 *
 * 전환 전 실측의 B-01~B-11 은 고치기 전까지 순회에 **검출된다.** 그것을 실패로 두면 017 내내
 * 빨갛고, 빨강이 「무언가 새로 깨짐」을 뜻하지 않게 된다. 그래서 순회 스크립트가 알려진 깨짐을
 * 따로 모은다. 대신 두 방향 다 막는다:
 *
 * - 등록부에 없는 검출 → 실패 (새 깨짐)
 * - 등록부에 있는데 더는 검출되지 않는 항목 → 실패 (고쳐졌으니 등록부에서 지워라)
 *
 * 그래서 「고쳤다」는 코드 커밋이 아니라 **이 보고서에서 사라진 것**이다 (data-model §9).
 */
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..");
const REPORT = join(ROOT, "tests", "sweep-report.json");

interface Finding {
  readonly where: string;
  readonly kind: string;
  readonly element: string;
  readonly detail: string;
}

interface Report {
  readonly digest: string;
  readonly viewports: string[];
  readonly screens: string[];
  readonly unreached: { screen: string; why: string }[];
  readonly counts: Record<string, number>;
  readonly known: string[];
  readonly staleKnown: string[];
  readonly unreachedRuns: Record<string, string>;
  readonly unallowed: Finding[];
  readonly pending: (Finding & { id: string })[];
  readonly allowed: (Finding & { reason: string })[];
}

/** 순회해야 하는 화면 — contracts/screen-sweep.md SW-5. 여기서 빠지면 「덜 잰 보고서」가 통과한다. */
const REQUIRED_SCREENS = [
  "project-list",
  "project-create",
  "test-list",
  "test-list-selected",
  "test-list-bulk-confirm",
  "test-list-row-menu",
  "test-list-session",
  "test-create",
  "secrets",
  "keys",
  "result-pass",
  "result-fail",
  "edit",
  "edit-long-name",
  "edit-step-detail",
  "edit-delete-confirm",
  "runner-record",
  "runner-disconnected",
];

/** 순회해야 하는 폭 — SW-4. */
const REQUIRED_VIEWPORTS = ["1280x800", "1440x900", "1920x1080", "2560x1440"];

/** `scripts/design_compare_ba.py` 의 `source_digest` 와 **같은 규약**이다 (`BeforeAfterParity` 와 같다). */
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

const RERUN = "  backend/.venv/bin/python scripts/screen_sweep.py";

describe("화면 깨짐 순회 — 조작이 덮이지 않고 넘치거나 끊기지 않는다 (017 SC-001~SC-003)", () => {
  const report: Report | null = existsSync(REPORT) ? (JSON.parse(readFileSync(REPORT, "utf8")) as Report) : null;

  it("보고서가 있다", () => {
    expect(report, `순회 보고서가 없다. 저장소 뿌리에서 돌린다:\n${RERUN}`).not.toBeNull();
  });

  it("보고서가 낡지 않았다 — 지금 화면 코드로 잰 것이다", () => {
    expect(
      sourceDigest(),
      `순회 보고서가 낡았다. 화면 코드가 바뀐 뒤 순회를 다시 돌리지 않았다.\n${RERUN}\n` +
        "이 상태에서는 「깨짐 0」이 지금 화면에 대한 말이 아니다.",
    ).toBe(report?.digest);
  });

  it("무엇을 순회했는지가 남아 있다 — 화면과 폭이 줄지 않았다 (SW-4 · SW-5)", () => {
    // 범위가 줄면 「깨짐 0」은 쉬워진다. `--only` 로 좁혀 돌린 결과는 스크립트가 보고서를 쓰지 않는다.
    const screens = new Set(report?.screens ?? []);
    expect(REQUIRED_SCREENS.filter((s) => !screens.has(s)), "순회하지 않은 화면").toEqual([]);
    expect(REQUIRED_VIEWPORTS.filter((v) => !(report?.viewports ?? []).includes(v)), "순회하지 않은 폭").toEqual([]);
    // 닿지 못하는 화면은 **이유와 함께** 적혀 있어야 한다 — 사람 판정으로 넘긴 자리다 (quickstart H-7).
    expect((report?.unreached ?? []).every((u) => u.why.trim() !== ""), "닿지 못한 화면에 이유가 없다").toBe(true);
  });

  it("닿으려던 화면에 전부 닿았다 — 같은 화면을 두 번 잰 것이 아니다", () => {
    expect(
      report?.unreachedRuns ?? {},
      "조작이나 「닿았다는 증거」가 실패했다. 그 화면은 잰 것이 아니다 (SW-5).",
    ).toEqual({});
  });

  it("등록되지 않은 검출이 없다 — 새로 깨진 곳이 없다", () => {
    const rows = (report?.unallowed ?? []).map((f) => `  [${f.where}] ${f.kind} ${f.element} ${f.detail}`);
    expect(
      rows,
      "화면이 깨졌다. 캡처는 .sweep/shots/ 에 있다. 고치거나, 깨짐이 아니라면 scripts/screen_sweep.py 의\n" +
        "ALLOWED 에 **이유와 함께** 등록한다 (SW-7).\n" +
        rows.join("\n"),
    ).toEqual([]);
  });

  it("고쳐진 깨짐이 알려진 깨짐 등록부에 남아 있지 않다", () => {
    expect(
      report?.staleKnown ?? [],
      "이 항목은 더 이상 검출되지 않는다 — 고쳐졌으면 scripts/screen_sweep.py 의 KNOWN 에서 지운다.\n" +
        "지우지 않으면 같은 깨짐이 다시 들어와도 「알려진 깨짐」으로 조용히 넘어간다.",
    ).toEqual([]);
  });

  it("허용된 검출에는 전부 이유가 있다", () => {
    const empty = (report?.allowed ?? []).filter((a) => (a.reason ?? "").trim() === "");
    expect(empty, "이유 없이 허용된 검출이 있다").toEqual([]);
  });

  it("알려진 깨짐이 하나도 남지 않았다 — 전환 전 실측의 B-01~B-11 을 전부 고쳤다 (T078 · SC-001~SC-003)", () => {
    /*
      017 동안에는 「남은 것이 전환 전 실측의 것뿐인가」만 물었다 — 고치는 중이었기 때문이다. 전환이 끝났으므로 **비어 있어야
      한다.** 등록부 기능(`scripts/screen_sweep.py` 의 KNOWN)은 남긴다: 다음에 전환 전 실측을 다시 뜨는 일이 생기면 쓴다.
      그러나 여기에 항목이 들어오면 이 검사가 실패한다 — 새 깨짐은 등록부가 아니라 고칠 대상이다.
    */
    const rows = (report?.pending ?? []).map((p) => `  ${p.id} [${p.where}] ${p.kind} ${p.element}`);
    expect(rows, "알려진 깨짐이 남아 있다:\n" + rows.join("\n")).toEqual([]);
    expect(report?.known ?? [], "알려진 깨짐 등록부가 비어 있지 않다 — scripts/screen_sweep.py 의 KNOWN").toEqual([]);
  });
});
