/**
 * 가드 G-F — 부품의 **모습**이 정본이다. 017 T014 (contracts/guards.md G-F).
 *
 * ## 왜 G-B 로는 부족한가
 *
 * 017 은 shadcn/ui 원본을 이식한다. 원본의 정본 밖 모습은 두 종류로 들어온다.
 *
 * 1. **테마 이름**(`rounded-md`·`shadow-xs`·`text-sm`·`bg-primary`) — 테마 이름공간을 비워
 *    **생성되지 않게** 했으므로 G-B(클래스 실재)가 잡는다 (research R4 · 스파이크 S1).
 * 2. **정적 유틸리티**(`disabled:opacity-50`·`focus-visible:ring-[3px]`·`transition-all`·
 *    `dark:bg-input/30`) — 테마와 무관하게 생성되므로 **G-B 를 통과한다.** 이 가드가 그 자리다.
 *
 * 둘째 종류가 들어오면 화면은 멀쩡해 보인다. 비활성 버튼이 점선이 아니라 흐려지고, 초점이
 * 전역 윤곽선 대신 흐린 링으로 그려지고, 열고 닫힐 때 움직인다 — 사용자 결정 1(모습은 정본)이
 * 조용히 깨진다.
 *
 * ## 무엇을 보는가
 *
 * `src/ui/**` 의 클래스(리터럴 · `cva` · `cn` 조합 — 공용 스캐너)와 가져오기 문장. 화면 코드는
 * 보지 않는다 — 화면이 모양을 입히는 것은 G-G(원시 요소)와 015 규율(`layout` 은 배치만)의 관할이다.
 *
 * ## 정당한 예외
 *
 * 정본이 스스로 흐림을 쓰는 자리가 있다 — Step 행 체크 칸의 비활성(`.srow-check input:disabled
 * { opacity: .4 }`, 015 state-styles S-13). 그런 자리는 `theme/exceptions.ts` 에 `class-name` 축으로
 * **이유와 함께** 등록한다. `FocusRing` 과 같은 등록부를 쓴다.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { basename, join } from "node:path";

import { describe, expect, it } from "vitest";

import { VISUAL_LANGUAGE_EXCEPTIONS } from "../src/theme/exceptions";

import { classNameGroups, composedClassGroups, splitVariant, withoutComments } from "./helpers/tailwind";

const ROOT = join(__dirname, "..");

/** 부품 파일. 스파이크 잔재(`__spike_*`)는 부품이 아니다 — 남아 있으면 T086 이 지운다. */
const UI_FILES = execFileSync("find", ["src/ui", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
  .trim()
  .split("\n")
  .filter((f) => f !== "" && !basename(f).startsWith("__spike"));

/*
  동작 층 부품과 **그 갈래** — contracts/ui-parts.md §1.

  017 은 전부 `radix-ui` 였다. Phase 10 이 갈래를 Base UI 로 옮기는 중이라 **한 파일씩** 건너간다.
  그래서 목록을 둘로 두고 **파일마다 자기 갈래를 실제로 가져오는지** 본다 — 묻는 것은 그대로다:
  「동작을 손으로 다시 짜지 않고 부품에 기대는가」. 한쪽으로 뭉뚱그리면 옮기는 동안 그 질문이 사라진다.

  T107 이 끝나면 `RADIX_PARTS` 가 비고 `radix-ui` 의존성 자체가 사라진다.
*/
const BASE_PARTS = new Set([
  "Dialog.tsx",
  "AlertDialog.tsx",
  "OverlayPane.tsx",
  "DropdownMenu.tsx",
  "Tabs.tsx",
  "ToggleGroup.tsx",
  "Tooltip.tsx",
]);
/*
  **비었다** (T106). 마지막 참조였던 `Button` 의 `asChild`(radix `Slot`)는 **쓰는 호출부가 하나도 없어**
  통로째 지웠다 — `render` 가 그 몫을 한다. T107 이 `radix-ui` 패키지를 지우면 이 목록은 영영 빈다.
  목록을 지우지 않고 **빈 채로 두는** 이유: 아래 두 검사가 「자기 갈래를 실제로 가져오는가」를 파일마다
  묻는 구조이고, 빈 목록이면 「radix 를 가져오는 부품이 하나도 없어야 한다」가 그대로 성립하기 때문이다.
*/
const RADIX_PARTS = new Set<string>([]);
/** 동작 층 부품 전부 — 갈래와 무관하게 **있어야** 한다 (T077). */
const BEHAVIOR_PARTS = new Set([...BASE_PARTS, ...RADIX_PARTS]);

/** 비활성을 **점선**으로 말해야 하는 조작 부품 (FR-006 · FR-014). 파일이 없어도 요구한다 (T077). */
const DASHED_DISABLED = ["Button.tsx", "Input.tsx", "Textarea.tsx", "NativeSelect.tsx"];

interface Rule {
  readonly id: string;
  readonly test: (variant: string, utility: string) => boolean;
  readonly why: string;
}

const RULES: readonly Rule[] = [
  {
    id: "비활성 흐림",
    test: (v, u) => /(?:^|:)(?:disabled|aria-disabled|data-\[disabled\]|has-\[[^\]]*disabled[^\]]*\]|\[[^\]]*:disabled\])(?::|$)/.test(v) && /^opacity-/.test(u),
    why: "비활성은 흐림이 아니라 자리를 지키는 점선이다 (정본 `.btn.off` · FR-006)",
  },
  {
    id: "비활성 포인터 차단",
    test: (v, u) => /disabled/.test(v) && u === "pointer-events-none",
    why: "사유를 담은 title 이 뜨지 않는다 (006 ui-contract §2 · FR-014)",
  },
  {
    id: "링",
    test: (_v, u) => /^ring(?:-|$)/.test(u),
    why: "초점은 전역 `:focus-visible` 윤곽선이 그린다 (015 S-14)",
  },
  {
    id: "윤곽선 지우기",
    test: (_v, u) => /^outline-(?:none|hidden|0)$/.test(u),
    why: "초점 표시가 사라진다 (FR-015 · `FocusRing` 과 같은 규칙)",
  },
  {
    id: "움직임",
    test: (_v, u) => /^(?:transition|animate|duration|ease|delay)(?:-|$)/.test(u),
    why: "정본에 움직임 언어가 없다 (FR-010)",
  },
  {
    id: "다크",
    test: (v) => /(?:^|:)dark(?::|$)/.test(v),
    why: "다크 모드는 범위 밖이다 (spec Assumptions)",
  },
  {
    id: "사용자 정의 상태 변종",
    test: (v) => /(?:^|:)data-(?:open|closed|checked|unchecked|active|inactive|horizontal|vertical|disabled|selected|highlighted|placeholder)(?::|$)/.test(v),
    why: "등록하지 않은 변종이다 — `data-[state=open]:` 처럼 표준 형태로 쓴다 (ui-parts §2)",
  },
];

const FORBIDDEN_IMPORT: readonly { re: RegExp; why: string }[] = [
  { re: /from\s+["']lucide-react["']/, why: "아이콘 묶음을 들이지 않는다 — 글자 기호를 쓴다 (FR-010)" },
  { re: /from\s+["']tailwind-merge["']/, why: "병합기를 들이지 않는다 — `ui/cn` (research R5)" },
  { re: /from\s+["']cn["']/, why: "npm `cn` 은 병합기를 품는다 — `ui/cn` (research R5)" },
  { re: /tw-animate-css/, why: "움직임 언어가 없다 (FR-010)" },
];

/*
  출처 줄. **갈래(registry base)를 적는 형식을 받도록 넓혔다** (2026-09-16 · Phase 10).

  017 은 `new-york-v4` 하나만 받았는데, 그것은 shadcn 의 **Radix 갈래** 이름이었다. shadcn 이 2026-07
  부터 Base UI 를 기본 갈래로 쓰므로 출처에 갈래가 드러나야 한다 — 017 의 출처 줄은 갈래를 적지 않아
  Radix 갈래를 옮긴 사실이 문서에 남지 않았다 (contracts/ui-parts.md §0-2).

  **넓히기만 한다**: 옛 형식은 그대로 받는다. 아직 이식하지 않은 부품이 그 형식이고, 가드를 좁혀
  통과시키지 않는다는 규칙(guards.md)이 이 방향이다.
*/
const PROVENANCE =
  /^\s*\*\s*출처:\s*(?:015\b|shadcn (?:new-york-v4|base)\/[a-z-]+ @ shadcn \d+\.\d+\.[\dx]+)/m;

function excused(file: string, name: string): boolean {
  return VISUAL_LANGUAGE_EXCEPTIONS.some(
    (e) => e.axis === "class-name" && `frontend/${file}`.startsWith(e.file) && new RegExp(e.pattern).test(name),
  );
}

function uiClassViolations(): string[] {
  const out = new Set<string>();
  const groups = [...classNameGroups(), ...composedClassGroups()].filter(
    (g) => g.file.startsWith("src/ui/") && !basename(g.file).startsWith("__spike"),
  );
  for (const g of groups) {
    for (const name of g.names) {
      const { variant, utility } = splitVariant(name);
      for (const rule of RULES) {
        if (rule.test(variant, utility) && !excused(g.file, name)) {
          out.add(`  ${g.file}:${g.line}  ${name}  — ${rule.id}: ${rule.why}`);
        }
      }
    }
  }
  return [...out].sort();
}

describe("G-F — 부품의 모습이 정본이다 (017)", () => {
  it("검사가 헛돌지 않는다 — 부품 파일과 그 클래스를 읽는다", () => {
    expect(UI_FILES.length, "src/ui 에서 부품 파일을 찾지 못했다").toBeGreaterThanOrEqual(7);
    const groups = [...classNameGroups(), ...composedClassGroups()].filter((g) => g.file.startsWith("src/ui/"));
    expect(groups.length, "부품의 클래스를 하나도 읽지 못했다").toBeGreaterThan(20);
    // 규칙이 대표 표기를 실제로 잡는가 — 아무것도 못 잡는 규칙은 규칙이 아니다.
    const hits = (name: string): string[] => {
      const { variant, utility } = splitVariant(name);
      return RULES.filter((r) => r.test(variant, utility)).map((r) => r.id);
    };
    expect(hits("disabled:opacity-50")).toContain("비활성 흐림");
    expect(hits("has-[select:disabled]:opacity-50")).toContain("비활성 흐림");
    expect(hits("disabled:pointer-events-none")).toContain("비활성 포인터 차단");
    expect(hits("focus-visible:ring-[3px]")).toContain("링");
    expect(hits("focus-visible:outline-hidden")).toContain("윤곽선 지우기");
    expect(hits("transition-[color,box-shadow]")).toContain("움직임");
    expect(hits("data-[state=open]:animate-in")).toContain("움직임");
    expect(hits("dark:bg-panel")).toContain("다크");
    expect(hits("data-open:bg-sunken")).toContain("사용자 정의 상태 변종");
    // 정상 표기는 조용해야 한다.
    expect(hits("disabled:border-dashed")).toEqual([]);
    expect(hits("data-[state=open]:bg-sunken-2")).toEqual([]);
    expect(hits("rounded-base")).toEqual([]);
  });

  it("부품이 정본 밖 모습(흐림 비활성·링·윤곽선 지우기·움직임·다크·사용자 정의 변종)을 쓰지 않는다", () => {
    const bad = uiClassViolations();
    expect(
      bad,
      "shadcn 원본의 기본 모습이 부품에 남아 있다. 이 클래스들은 테마와 무관하게 생성되므로 G-B 를\n" +
        "통과하지만 화면을 정본에서 벗어나게 한다. contracts/ui-parts.md §2 대응표대로 옮긴다.\n" +
        "정본이 스스로 그 형태를 쓰는 자리라면 theme/exceptions.ts 에 class-name 축으로 이유와 함께 등록한다.\n" +
        bad.join("\n"),
    ).toEqual([]);
  });

  it("들이지 않기로 한 의존성을 가져오지 않는다", () => {
    const bad: string[] = [];
    for (const rel of UI_FILES) {
      const txt = withoutComments(readFileSync(join(ROOT, rel), "utf8"));
      for (const f of FORBIDDEN_IMPORT) if (f.re.test(txt)) bad.push(`  ${rel} — ${f.why}`);
    }
    expect(bad, bad.join("\n")).toEqual([]);
  });

  it("동작 층 부품이 전부 있고 `radix-ui` 에 기댄다 — 파일이 없어도 요구한다 (T077)", () => {
    /*
      017 전환 중에는 「파일이 생긴 뒤부터 요구한다」였다 — 부품을 하나씩 만들었기 때문이다. 전환이 끝났으므로
      ui-parts.md §1 의 `behavior = radix` 부품은 **있어야** 하고, 실제로 `radix-ui` 를 가져와야 한다. 파일을 지우거나
      동작 층을 손으로 다시 짜면(수제 포털 · 수제 초점 가두기) 여기서 실패한다.
    */
    const names = new Set(UI_FILES.map((f) => basename(f)));
    const missing = [...BEHAVIOR_PARTS].filter((name) => !names.has(name));
    expect(missing, "동작 층 부품 파일이 없다 — contracts/ui-parts.md §1").toEqual([]);
    const source = (name: string) => withoutComments(readFileSync(join(ROOT, "src/ui", name), "utf8"));
    const handmade = [...BEHAVIOR_PARTS].filter((name) => {
      const txt = source(name);
      const wants = BASE_PARTS.has(name) ? /from\s+["']@base-ui\/react/ : /from\s+["']radix-ui["']/;
      return !wants.test(txt);
    });
    expect(
      handmade,
      "동작 층 부품이 **자기 갈래**를 가져오지 않는다 — 동작을 손으로 다시 짰거나 갈래 목록이 낡았다.\n" +
        "Base UI 로 옮겼다면 위 `BASE_PARTS` 로 옮겨 적는다 (contracts/ui-parts.md §1).",
    ).toEqual([]);
  });

  it("`radix-ui` 는 동작 층 부품만 가져온다", () => {
    const bad = UI_FILES.filter((rel) => {
      const txt = withoutComments(readFileSync(join(ROOT, rel), "utf8"));
      return /from\s+["']radix-ui["']/.test(txt) && !RADIX_PARTS.has(basename(rel));
    });
    expect(
      bad,
      "이 부품은 contracts/ui-parts.md §1 에서 behavior 가 radix 가 아니다 — 네이티브로 두기로 했다 (research R2).\n" +
        bad.join("\n"),
    ).toEqual([]);
  });

  it("조작 부품은 비활성을 점선으로 말한다", () => {
    // T077 — 파일이 없어도 요구한다. 조작 부품이 사라지면 화면이 다시 원시 요소나 수제 조합으로 돌아간다.
    const missing = DASHED_DISABLED.filter((name) => !UI_FILES.some((f) => basename(f) === name));
    expect(missing, "조작 부품 파일이 없다").toEqual([]);
    const bad = DASHED_DISABLED.filter((name) => {
      const txt = readFileSync(join(ROOT, "src/ui", name), "utf8");
      return !/(?:^|[\s"'`])(?:[\w-]+:)*(?:disabled|has-\[[^\]]*:disabled\]):border-dashed/.test(txt);
    });
    expect(bad, `비활성 점선이 없다: ${bad.join(", ")} (정본 button:disabled · FR-006)`).toEqual([]);
  });

  it("부품 파일은 출처를 적는다", () => {
    const bad = UI_FILES.filter((rel) => !PROVENANCE.test(readFileSync(join(ROOT, rel), "utf8")));
    expect(
      bad,
      "파일 머리 주석에 ` * 출처: shadcn base/<항목> @ shadcn 4.21.x`(갈래를 적는다) 또는\n" +
        "` * 출처: shadcn new-york-v4/<항목> @ shadcn 4.21.0`(옛 갈래) 또는 ` * 출처: 015` 줄이 없다.\n" +
        "원본을 되짚을 수 없으면 대응표를 따랐는지 확인할 수 없다 (contracts/ui-parts.md §0).\n" +
        bad.join("\n"),
    ).toEqual([]);
  });
});
