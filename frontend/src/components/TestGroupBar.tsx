import { useState } from "react";

import type { GroupSummary } from "../api/client";

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
}: {
  groups: GroupSummary[];
  active: string | null;
  busy: boolean;
  onPick: (prefix: string | null) => void;
  onCreate: (prefix: string, name: string) => void;
}) {
  const [adding, setAdding] = useState(false);

  // 그룹이 하나도 없고 만드는 중도 아니면 자리를 차지하지 않는다.
  const realGroups = groups.filter((g) => g.prefix !== "TC");
  if (realGroups.length === 0 && !adding) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <button className="navlink" onClick={() => setAdding(true)} disabled={busy}>
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
      style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}
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
      <div className="spacer" />
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
        <button className="navlink" onClick={() => setAdding(true)} disabled={busy}>
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
    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
      <input
        aria-label="그룹 이름"
        placeholder="사용자관리 테스트"
        value={name}
        autoFocus
        disabled={busy}
        onChange={(e) => setName(e.target.value)}
        style={{ margin: 0, width: 180 }}
      />
      <input
        aria-label="그룹 접두어"
        placeholder="USER"
        value={prefix}
        disabled={busy}
        onChange={(e) => setPrefix(e.target.value)}
        style={{ margin: 0, width: 90 }}
      />
      <span className="why">테스트 식별자에 들어갑니다 (예: {cleanPrefix || "USER"}-001)</span>
      {prefix.trim() !== "" && !prefixOk && (
        <span className="line fail-ink">
          {cleanPrefix === "TC"
            ? "TC 는 그룹 없는 테스트가 씁니다."
            : "영문 대문자·숫자 1~8자, 첫 글자는 영문입니다."}
        </span>
      )}
      <button
        className="btn sm"
        disabled={busy || !ready}
        onClick={() => onSubmit(cleanPrefix, name.trim())}
      >
        만들기
      </button>
      <button className="navlink" onClick={onCancel} disabled={busy}>
        취소
      </button>
    </div>
  );
}
