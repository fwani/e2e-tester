import { useState } from "react";

import type { GroupSummary } from "../api/client";

import { Button } from "../ui/Button";

/**
 * 목록 위 그룹 띠 (013 FR-440·FR-441 · UC-013-06).
 *
 * **그룹이 하나도 없으면 그리지 않는다** (SC-627). 그룹을 쓰지 않는 사용자의 목록은 이
 * 기능 이전과 같은 모습이어야 한다 — 새 구획을 강요하지 않는다.
 *
 * 개수는 **걸러 보기 전** 값이다. 한 그룹만 보고 있어도 다른 그룹의 개수를 보고 그리로
 * 갈 수 있어야 한다 (contracts/api-contract.md §1).
 */
export function TestGroupBar({
  groups,
  active,
  busy,
  onPick,
  onCreate,
  onRename,
  onRemove,
}: {
  groups: GroupSummary[];
  active: string | null;
  busy: boolean;
  onPick: (prefix: string | null) => void;
  onCreate: (prefix: string, name: string) => void;
  onRename: (prefix: string, name: string) => void;
  onRemove: (prefix: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<{ prefix: string; name: string } | null>(null);
  const [removing, setRemoving] = useState<GroupSummary | null>(null);

  // 그룹이 하나도 없고 만드는 중도 아니면 자리를 차지하지 않는다.
  const realGroups = groups.filter((g) => g.prefix !== "TC");
  if (realGroups.length === 0 && !adding) {
    return (
      <div className="flex justify-end mb-s2">
        <button className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken" onClick={() => setAdding(true)} disabled={busy}>
          + 그룹
        </button>
      </div>
    );
  }

  const total = groups.reduce((n, g) => n + g.count, 0);

  return (
    <div
      data-test-group-bar
      role="group"
      aria-label="그룹으로 거르기"
      className="flex items-center gap-s2 mb-s2 flex-wrap"
    >
      <button
        className={active === null ? "chip sel" : "chip"}
        aria-pressed={active === null}
        onClick={() => onPick(null)}
        disabled={busy}
      >
        전체 {total}
      </button>
      {groups.map((g) => (
        <button
          key={g.prefix}
          className={active === g.prefix ? "chip sel" : "chip"}
          aria-pressed={active === g.prefix}
          data-group-chip={g.prefix}
          onClick={() => onPick(g.prefix)}
          disabled={busy}
          // 정의가 없는 접두어는 이름을 지어내지 않는다 — 접두어가 곧 이름이다.
          title={g.name ?? `${g.prefix} — 그룹 정의가 없습니다`}
        >
          {g.name ?? (g.prefix === "TC" ? "그룹 없음" : g.prefix)} {g.count}
        </button>
      ))}
      {/*
        그룹 조작은 **그 그룹을 고른 상태에서만** 나온다. 칩마다 조작을 달면 띠가
        빽빽해지고, 사용자가 어느 그룹을 건드리는지도 흐려진다. 정의가 없는 접두어와
        「그룹 없음」에는 고칠 대상이 없으므로 그리지 않는다.
      */}
      {active !== null &&
        active !== "TC" &&
        editing === null &&
        removing === null &&
        groups.some((g) => g.prefix === active && g.name !== null) && (
          <>
            <button
              className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken"
              disabled={busy}
              onClick={() =>
                setEditing({
                  prefix: active,
                  name: groups.find((g) => g.prefix === active)?.name ?? "",
                })
              }
            >
              이름 바꾸기
            </button>
            <button
              className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken"
              disabled={busy}
              onClick={() =>
                setRemoving(groups.find((g) => g.prefix === active) ?? null)
              }
            >
              그룹 없애기
            </button>
          </>
        )}
      {editing !== null && (
        <input
          aria-label="그룹 이름 바꾸기"
          value={editing.name}
          autoFocus
          disabled={busy}
          onChange={(e) => setEditing({ prefix: editing.prefix, name: e.target.value })}
          onKeyDown={(e) => {
            if (e.key === "Enter" && editing.name.trim() !== "") {
              onRename(editing.prefix, editing.name.trim());
              setEditing(null);
            }
            if (e.key === "Escape") setEditing(null);
          }}
          onBlur={() => setEditing(null)}
          className="m-0 w-[180px]"
        />
      )}
      <div className="flex-1" />
      {removing !== null && (
        <ConfirmDisband
          group={removing}
          busy={busy}
          onCancel={() => setRemoving(null)}
          onConfirm={() => {
            onRemove(removing.prefix);
            setRemoving(null);
          }}
        />
      )}
      {adding ? (
        <NewGroupForm
          busy={busy}
          onCancel={() => setAdding(false)}
          onSubmit={(prefix, name) => {
            onCreate(prefix, name);
            setAdding(false);
          }}
        />
      ) : (
        <button className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken" onClick={() => setAdding(true)} disabled={busy}>
          + 그룹
        </button>
      )}
    </div>
  );
}

/**
 * 그룹 만들기 — **두 칸이다** (013 FR-444d · UC-013-08).
 *
 * 이름은 사람이 읽는 것(「사용자관리 테스트」)이고 접두어는 식별자에 들어가는 짧은 값
 * (`USER`)이다. 이름에서 자동으로 뽑지 않는 이유는 이름이 한글일 수 있기 때문이다 —
 * 그대로 쓰면 식별자가 길어지고, 로마자로 바꾸면 사용자가 예측하지 못하는 값이 나온다.
 *
 * 그래서 **접두어 칸이 왜 필요한지 그 자리에서 말한다.** 말하지 않으면 사용자는 이름을
 * 두 번 적는 칸으로 읽는다.
 */
function NewGroupForm({
  busy,
  onCancel,
  onSubmit,
}: {
  busy: boolean;
  onCancel: () => void;
  onSubmit: (prefix: string, name: string) => void;
}) {
  const [name, setName] = useState("");
  const [prefix, setPrefix] = useState("");

  const cleanPrefix = prefix.trim().toUpperCase();
  const prefixOk = /^[A-Z][A-Z0-9]{0,7}$/.test(cleanPrefix) && cleanPrefix !== "TC";
  const ready = name.trim() !== "" && prefixOk;

  return (
    <div className="flex items-center gap-[6px] flex-wrap">
      <input
        aria-label="그룹 이름"
        placeholder="사용자관리 테스트"
        value={name}
        autoFocus
        disabled={busy}
        onChange={(e) => setName(e.target.value)}
        className="m-0 w-[180px]"
      />
      <input
        aria-label="그룹 접두어"
        placeholder="USER"
        value={prefix}
        disabled={busy}
        onChange={(e) => setPrefix(e.target.value)}
        className="m-0 w-[90px]"
      />
      <span className="font-sans text-[11px] leading-[1.4] text-ink-3">테스트 식별자에 들어갑니다 (예: {cleanPrefix || "USER"}-001)</span>
      {prefix.trim() !== "" && !prefixOk && (
        <span className="font-sans text-[13px] leading-[1.4] text-fail">
          {cleanPrefix === "TC"
            ? "TC 는 그룹 없는 테스트가 씁니다."
            : "영문 대문자·숫자 1~8자, 첫 글자는 영문입니다."}
        </span>
      )}
      <Button
        size="sm"
        disabled={busy || !ready}
        onClick={() => onSubmit(cleanPrefix, name.trim())} >
        만들기
      </Button>
      <button className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken" onClick={onCancel} disabled={busy}>
        취소
      </button>
    </div>
  );
}


/**
 * 그룹 해체 확인 (013 FR-451 · UC-013-08).
 *
 * **이름 변경에는 확인이 없고 여기에만 있다.** 그것만이 자산을 움직이기 때문이다 —
 * 그 안의 테스트들의 파일 이름과 산출물 디렉터리가 바뀐다. 이름 변경은 프로젝트 파일
 * 한 줄이라 되돌리면 그만이다.
 *
 * 문구가 **「지워지지 않습니다」를 반드시 말한다.** 「없애기」라는 말을 듣고 사용자가
 * 가장 먼저 걱정하는 것이 그것이다.
 */
function ConfirmDisband({
  group,
  busy,
  onCancel,
  onConfirm,
}: {
  group: GroupSummary;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <span
      data-group-disband-confirm
      role="status"
      className="bg-warn-t border border-warn-line rounded-base font-sans text-[13px] leading-[1.4] inline-flex items-center gap-s2 py-s1 px-s2"
    >
      <span className="font-sans text-[13px] font-semibold leading-none">
        「{group.name ?? group.prefix}」을(를) 없앨까요? 테스트 {group.count}개가 그룹 없음으로
        돌아가고 식별자가 TC-### 로 바뀝니다 · 지워지지 않습니다
      </span>
      <Button size="sm" onClick={onCancel} disabled={busy} autoFocus>
        돌아가기
      </Button>
      <Button size="sm" variant="danger" onClick={onConfirm} disabled={busy}>
        없애기
      </Button>
    </span>
  );
}
