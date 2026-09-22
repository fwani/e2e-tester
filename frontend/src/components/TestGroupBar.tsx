import { ToolPanel } from "../ui/ToolPanel";
import { useState } from "react";

import type { GroupSummary } from "../api/client";

import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { NativeSelect, NativeSelectOption } from "../ui/NativeSelect";

/** 그룹 선택은 한 칸으로, 생성·변경·해체는 필요할 때 펼친다. */
const ALL = "__all__";

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

  const realGroups = groups.filter((g) => g.prefix !== "TC");
  const total = groups.reduce((n, g) => n + g.count, 0);
  const picked = groups.find((g) => g.prefix === active);

  return (
    <div className="library-group-control" data-test-group-bar={realGroups.length > 0 ? "" : undefined}>
      {realGroups.length > 0 && (
        <NativeSelect
          aria-label="그룹으로 거르기"
          value={active ?? ALL}
          disabled={busy}
          onChange={(event) => {
            const next = event.target.value;
            onPick(next === ALL ? null : next);
            setEditing(null);
            setRemoving(null);
          }}
        >
          <NativeSelectOption value={ALL}>모든 그룹 · {total}</NativeSelectOption>
          {groups.map((g) => (
            <NativeSelectOption key={g.prefix} value={g.prefix}>
              {g.name ?? (g.prefix === "TC" ? "그룹 없음" : g.prefix)} · {g.count}
            </NativeSelectOption>
          ))}
        </NativeSelect>
      )}
      <ToolPanel label="그룹 관리">
        <div className="library-group-panel">
          <div className="library-group-actions">
            <Button variant="nav" onClick={() => { setAdding(true); setEditing(null); setRemoving(null); }} disabled={busy}>
              + 그룹
            </Button>
            {picked !== undefined && picked.prefix !== "TC" && picked.name !== null && (
              <>
                <Button variant="nav" disabled={busy} onClick={() => { setEditing({ prefix: picked.prefix, name: picked.name ?? "" }); setAdding(false); setRemoving(null); }}>
                  이름 바꾸기
                </Button>
                <Button variant="nav" disabled={busy} onClick={() => { setRemoving(picked); setAdding(false); setEditing(null); }}>
                  그룹 없애기
                </Button>
              </>
            )}
          </div>
          {active === null && realGroups.length > 0 && !adding && (
            <p>그룹을 선택하면 이름을 바꾸거나 없앨 수 있습니다.</p>
          )}
          {editing !== null && (
            <Input
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
              layout="m-0 w-[180px]"
            />
          )}
          {removing !== null && (
            <ConfirmDisband
              group={removing}
              busy={busy}
              onCancel={() => setRemoving(null)}
              onConfirm={() => { onRemove(removing.prefix); setRemoving(null); }}
            />
          )}
          {adding && (
            <NewGroupForm
              busy={busy}
              onCancel={() => setAdding(false)}
              onSubmit={(prefix, name) => { onCreate(prefix, name); setAdding(false); }}
            />
          )}
        </div>
      </ToolPanel>
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
      <Input
        aria-label="그룹 이름"
        placeholder="사용자관리 테스트"
        value={name}
        autoFocus
        disabled={busy}
        onChange={(e) => setName(e.target.value)}
        layout="m-0 w-[180px]"
      />
      <Input
        aria-label="그룹 접두어"
        placeholder="USER"
        value={prefix}
        disabled={busy}
        onChange={(e) => setPrefix(e.target.value)}
        layout="m-0 w-[90px]"
      />
      <span className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3">테스트 식별자에 들어갑니다 (예: {cleanPrefix || "USER"}-001)</span>
      {prefix.trim() !== "" && !prefixOk && (
        <span className="font-sans text-[14px] leading-[1.4] font-normal text-fail">
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
      <Button variant="nav" onClick={onCancel} disabled={busy}>
        취소
      </Button>
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
      className="bg-warn-t border border-warn-line rounded-base font-sans text-[14px] leading-[1.4] font-normal inline-flex items-center gap-s2 py-s1 px-s2"
    >
      <span className="font-sans text-[14px] font-semibold leading-none">
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
