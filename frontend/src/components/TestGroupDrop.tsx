/**
 * 끌어 놓기로 그룹에 넣기 — 표적 띠. 028 FR-013~FR-026 · contracts/ui-contract.md UC-028-02.
 *
 * ## 왜 끌기 중에만 보이는가
 *
 * 013 의 **SC-627** 은 「그룹을 쓰지 않는 사용자에게 자리를 뺏지 않는다」다. 그래서 목록은
 * 그룹 소제목 없이 한 줄로 그리고 그룹은 선택칸으로만 거른다. 상시 드롭 표적을 깔면 그
 * 결정이 무너진다.
 *
 * 이 띠는 `dragstart` 와 함께 나타나고 `drop`·`dragend` 와 함께 사라진다. **끌지 않는
 * 사용자의 화면은 028 이전과 글자 하나 다르지 않다** (FR-014 · SC-005).
 *
 * ## 왜 라이브러리를 쓰지 않는가
 *
 * 필요한 것은 「행을 끌어 표적에 놓기」 하나다 — 순서 바꾸기도, 중첩도, 가상 목록도 없다
 * (research R5). 키보드 경로는 선택 띠의 「그룹으로 옮기기」가 이미 갖고 있고 028 이 그
 * 구멍도 막는다 (FR-027·FR-028). 런타임 의존성을 하나 더할 이유가 없다.
 */
import { useState } from "react";

import type { GroupSummary } from "../api/client";
import { Button } from "../ui/Button";

/** 「그룹에서 빼기」가 쓰는 접두어. 그룹 없는 테스트의 것이다. */
export const UNGROUPED = "TC";

/** 「새 그룹으로」 표적이 돌려주는 값. 접두어가 아니므로 접두어 자리에 쓰이지 않는다. */
export const NEW_GROUP = "__new__";

export type DropTarget = string | typeof NEW_GROUP;

export function GroupDropBar({
  groups,
  busy,
  count,
  onDrop,
}: {
  /** 정의된 그룹 전부 — **테스트가 0개인 것도 표적이 된다** (FR-015). */
  groups: GroupSummary[];
  busy: boolean;
  /** 지금 끌고 있는 테스트 수. 사용자가 무엇을 옮기는지 알아야 한다. */
  count: number;
  onDrop: (target: DropTarget) => void;
}) {
  const [over, setOver] = useState<DropTarget | null>(null);
  const named = groups.filter((g) => g.name !== null && g.prefix !== UNGROUPED);
  const hasGroups = named.length > 0;

  const target = (key: DropTarget, label: string, hint?: string) => (
    <Button
      key={key}
      /*
        **원시 `<button>` 을 쓰지 않는다** (017 G-G · 예산 0).

        올라와 있는 표적은 `primary` 로 바뀐다 (FR-016). 모양을 `layout` 으로 넘기지
        않는 것은 017 의 규칙이다 — 모양이 필요하면 `variant` 를 쓴다. 두 갈래로 충분해
        `Button` 에 새 갈래를 늘리지 않는다.
      */
      variant={over === key ? "primary" : "quiet"}
      size="sm"
      layout="whitespace-nowrap shrink-0"
      type="button"
      data-drop-target={key}
      data-drop-over={over === key ? "" : undefined}
      disabled={busy}
      /*
        표적은 **끌기에 딸린 것이다.** 포인터를 쓰지 않는 사용자가 여기까지 와야 할 이유가
        없고(FR-028), 탭 순서에 끼면 목록을 훑는 길만 길어진다. 같은 일을 하는 길은 선택
        띠에 있다 (UC-028-07).
      */
      tabIndex={-1}
      onDragEnter={(e) => {
        e.preventDefault();
        setOver(key);
      }}
      onDragOver={(e) => {
        // 이것이 없으면 브라우저가 놓기를 거절한다 — `drop` 이 아예 오지 않는다.
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
      }}
      onDragLeave={() => setOver((prev) => (prev === key ? null : prev))}
      onDrop={(e) => {
        e.preventDefault();
        setOver(null);
        onDrop(key);
      }}
      title={hint}
    >
      {label}
    </Button>
  );

  return (
    <div
      data-group-drop-bar
      role="group"
      aria-label="끌어서 그룹에 넣기"
      className="bg-panel border border-hair rounded-base flex items-center gap-[8px] py-s2 px-s3 mb-[10px] overflow-x-auto sticky top-0 z-10"
    >
      <span className="font-sans text-[13px] font-semibold leading-none whitespace-nowrap shrink-0 text-ink-2">
        {count}개를 어디에 놓을까요?
      </span>
      {named.map((g) => target(g.prefix, g.name as string))}
      {hasGroups && target(UNGROUPED, "그룹에서 빼기", "그룹 없음(TC)으로 되돌립니다")}
      {/*
        **그룹이 0개여도 이것은 나온다** (FR-024). 그룹을 하나도 만들지 못한 사용자가
        목록에서 막히던 자리가 여기다 — 028 이전에는 끌 곳도, 고를 칸도 없었다.
      */}
      {target(NEW_GROUP, "+ 새 그룹으로")}
    </div>
  );
}

/**
 * 「새 그룹으로」에 놓은 뒤 이름과 접두어를 받는다 (UC-028-05).
 *
 * **013 의 「+ 그룹」과 같은 두 칸, 같은 규칙, 같은 안내를 쓴다** — 그래서 새 입력 부품을
 * 만들지 않고 `TestGroupBar` 의 것을 그대로 빌린다. 두 자리에서 접두어를 받는데 규칙
 * 안내가 다르면, 사용자는 두 기능이 다른 규칙을 갖는다고 읽는다.
 */
export function NewGroupDropPrompt({
  count,
  form,
}: {
  count: number;
  /** `TestGroupBar` 의 만들기 칸. 호출자가 넘겨 준다 — 규칙이 한 자리에 있게. */
  form: React.ReactNode;
}) {
  return (
    <div
      data-new-group-drop
      role="status"
      className="bg-warn-t border border-warn-line rounded-base font-sans text-[14px] leading-[1.4] font-normal flex items-center gap-[10px] py-s2 px-s3 mb-[10px] flex-wrap"
    >
      <span className="font-sans text-[14px] font-semibold leading-none whitespace-nowrap">
        테스트 {count}개를 넣을 그룹을 만듭니다
      </span>
      {/* 취소는 빌려 온 만들기 칸이 이미 갖고 있다 — 두 개를 그리지 않는다. */}
      {form}
    </div>
  );
}
