/**
 * 가드 G-D — 대응표와 코드가 **어긋나지 않는가.** 015 T012.
 *
 * `contracts/class-migration.md` 는 의미 클래스 109개가 각각 어디로 갔는지를 담는다.
 * 전환이 여러 커밋에 걸치므로 진행 상태를 담을 자리가 필요하고, 남은 클래스를 세는 것만
 * 으로는 *어디로 갔는지*를 알 수 없다 (SC-009 「미상 0건」).
 *
 * 이 검사가 막는 것은 **표와 코드가 따로 노는 것**이다. 표만 「완료」로 고치고 코드를
 * 안 옮기거나, 코드를 옮기고 표를 안 고치거나. 둘 다 나중에 「다 옮겼다」를 확인할 수
 * 없게 만든다.
 */
import { describe, expect, it } from "vitest";

import migrationDoc from "../../specs/015-tailwind-css-migration/contracts/class-migration.md?raw";

import { canonClasses, classNameGroups, derivedClasses } from "./helpers/tailwind";

interface Row {
  readonly cls: string;
  readonly done: boolean;
}

/** 표에서 `| `.btn` | 82 | T015 | ui/Button | 미착수 |` 형태의 행을 읽는다. */
function rows(): Row[] {
  const out: Row[] = [];
  for (const line of migrationDoc.split("\n")) {
    const m = /^\|\s*`\.([a-zA-Z][a-zA-Z0-9_-]*)`\s*\|(?:[^|]*\|){3}\s*([^|]*?)\s*\|/.exec(line);
    if (m === null) continue;
    out.push({ cls: m[1] as string, done: (m[2] as string).trim() === "완료" });
  }
  return out;
}

describe("G-D — 대응표와 코드가 일치한다", () => {
  const table = rows();
  const canon = canonClasses();

  it("표를 읽는다 (검사가 헛돌지 않는다)", () => {
    // 표 형식이 바뀌어 0행을 읽으면 아래 검사가 전부 통과한다 — 아무것도 막지 못한다.
    expect(table.length, "class-migration.md 에서 행을 하나도 읽지 못했다 — 표 형식이 바뀌었다").toBeGreaterThan(100);
  });

  it("표에 없는 의미 클래스가 없다 — 미상 0건 (SC-009)", () => {
    const listed = new Set(table.map((r) => r.cls));
    const unlisted = Array.from(canon).filter((c) => !listed.has(c)).sort();
    expect(
      unlisted,
      "정본에 있는데 대응표에 없는 클래스다. 어디로 갈지 정해지지 않았다.\n" +
        unlisted.map((c) => `  .${c}`).join("\n"),
    ).toEqual([]);
  });

  it("「완료」로 적힌 클래스를 화면 코드가 더는 쓰지 않는다", () => {
    // 「완료」의 정의는 T016 이 정정했다 (contracts/class-migration.md).
    // 정본 구획(자동 추출)의 클래스는 지울 수 없고 지우는 것이 옳지도 않다 — 그것은
    // 확정 디자인의 기록이자 L1 대조의 기준이다. 사라져야 하는 것은 **화면의 사용**이다.
    const used = new Set<string>();
    for (const g of classNameGroups()) for (const n of g.names) used.add(n);
    const still = table.filter((r) => r.done && used.has(r.cls)).map((r) => `  .${r.cls}`);
    expect(
      still,
      "표는 「완료」인데 화면 코드가 아직 그 클래스를 쓴다.\n" + still.join("\n"),
    ).toEqual([]);
  });

  it("파생 구획의 「완료」 클래스는 정의도 삭제됐다", () => {
    // 파생 구획은 손으로 쓴 것이다. 화면이 쓰지 않으면 남길 이유가 없다.
    // 부품만 만들고 옛 정의를 남기면 두 체계가 공존한 채 굳는다 — 007 「전사」 실패의 형태.
    const derived = derivedClasses();
    const lying = table.filter((r) => r.done && derived.has(r.cls)).map((r) => `  .${r.cls}`);
    expect(
      lying,
      "표는 「완료」인데 파생 구획에 정의가 남아 있다.\n" + lying.join("\n"),
    ).toEqual([]);
  });

  it("파생 구획에서 사라진 클래스는 표에 「완료」로 적혀 있다", () => {
    const silent = table
      .filter((r) => !r.done && !canon.has(r.cls))
      .map((r) => `  .${r.cls}`);
    expect(
      silent,
      "정본에서 사라졌는데 표가 「완료」가 아니다. 표를 갱신하지 않았다.\n" +
        "표가 진행 상태의 유일한 기록이므로, 어긋나면 무엇이 남았는지 알 수 없다.\n" +
        silent.join("\n"),
    ).toEqual([]);
  });
});
