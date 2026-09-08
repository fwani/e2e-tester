/**
 * 후보 6단 우선순위 표 (T142). FR-019·FR-019a·FR-020.
 *
 * **표시 상태는 저장 데이터에서 파생한다.** 저장하지 않는다 (data-model §6) — 저장하면
 * 후보를 다시 수집했을 때 표시가 옛것을 가리킬 수 있다.
 *
 * 파생 규칙의 권위 정의는 `backend/src/itb/locator/display.py` 다. 여기 있는 것은 그
 * 규칙의 화면용 사본이며, 같은 판정 사례를 `frontend/tests/LocatorPriorityTable.test.tsx`
 * 와 `backend/tests/unit/test_candidate_display.py` 가 각각 고정한다. 실행에 쓰이는
 * 후보 선택은 이 파일과 무관하다 — 그것은 `choose_strategy` 한 곳에서만 나온다.
 */
import type { TargetLocator } from "../types/generated/step";

type Status = "verified" | "ambiguous" | "unverified" | "not_collected";

interface Row {
  kind: string;
  label: string;
  value: string | null;
  status: Status | null;
}

/** FR-018 의 우선순위. 이 순서가 화면 표기의 근거다. */
const PRIORITY = ["test_id", "role", "label", "text", "stable_attr", "css"] as const;

const KIND_LABELS: Record<string, string | undefined> = {
  test_id: "test id",
  role: "role + 이름",
  label: "label",
  text: "보이는 텍스트",
  stable_attr: "고정 속성",
  css: "CSS 경로",
};

type Kind = (typeof PRIORITY)[number];

function rowsOf(t: TargetLocator): Row[] {
  const raw: Record<Kind, { value: string | null; status: Status | null }> = {
    test_id: { value: t.test_id?.value ?? null, status: (t.test_id?.status as Status) ?? null },
    role:
      t.role && t.accessible_name
        ? {
            value: `${t.role} "${t.accessible_name}"`,
            status: (t.role_status as Status) ?? "not_collected",
          }
        : { value: null, status: null },
    label: { value: t.label?.value ?? null, status: (t.label?.status as Status) ?? null },
    text: { value: t.text?.value ?? null, status: (t.text?.status as Status) ?? null },
    stable_attr: t.stable_attr
      ? {
          value: `${t.stable_attr.name}="${t.stable_attr.value}"`,
          status: t.stable_attr.status as Status,
        }
      : { value: null, status: null },
    css: { value: t.css?.value ?? null, status: (t.css?.status as Status) ?? null },
  };
  return PRIORITY.map((kind) => ({
    kind,
    label: KIND_LABELS[kind] ?? kind,
    value: raw[kind].value,
    status: raw[kind].status,
  }));
}

/**
 * 표시 상태를 파생한다 (FR-019a).
 *
 * `verified` 후보만 사용 가능하다. 첫 번째가 `사용 중`, 그다음이 `대체 N`, CSS 는 `최후`.
 * `ambiguous` 는 사용 **불가**임을 명시한다 — 값이 있으니 쓰일 것처럼 보이면 오해한다.
 */
export function displayStates(target: TargetLocator): Record<string, string> {
  let usableSeen = 0;
  const out: Record<string, string> = {};
  for (const row of rowsOf(target)) {
    if (row.status === null || row.status === "not_collected") {
      out[row.kind] = "수집되지 않음";
      continue;
    }
    if (row.status === "ambiguous") {
      out[row.kind] = "모호(사용 불가)";
      continue;
    }
    if (row.status === "unverified") {
      out[row.kind] = "검증 실패";
      continue;
    }
    if (usableSeen === 0) out[row.kind] = "사용 중";
    else if (row.kind === "css") out[row.kind] = "최후";
    else out[row.kind] = `대체 ${usableSeen}`;
    usableSeen += 1;
  }
  return out;
}

function tone(state: string): string {
  if (state === "사용 중") return "pass";
  if (state.startsWith("대체")) return "";
  if (state === "최후") return "warn";
  if (state === "모호(사용 불가)" || state === "검증 실패") return "fail";
  return "";
}

export interface LocatorPriorityTableProps {
  target: TargetLocator;
  title?: string;
  busy?: boolean;
  /** 다시 집기 (FR-020). 없으면 버튼을 그리지 않는다. */
  onRepick?: () => void;
  /** 다시 집기 대기 중인가. 브라우저에서 클릭을 기다리는 상태다. */
  repicking?: boolean;
}

export function LocatorPriorityTable({
  target,
  title = "대상 요소",
  busy = false,
  onRepick,
  repicking = false,
}: LocatorPriorityTableProps) {
  const states = displayStates(target);
  const rows = rowsOf(target);
  const usable = rows.filter((r) => r.status === "verified").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div className="row" style={{ gap: 8 }}>
        <strong className="lbl">{title}</strong>
        <span className={`chip ${usable >= 2 ? "pass" : "warn"}`}>
          사용 가능 후보 {usable}
        </span>
        <span className="spacer" />
        {onRepick && (
          <button className="btn sm" disabled={busy || repicking} onClick={onRepick}>
            {repicking ? "브라우저에서 클릭 대기 중…" : "다시 집기"}
          </button>
        )}
      </div>

      {repicking && (
        <p className="why" style={{ margin: 0 }}>
          실제 브라우저 창에서 대상 요소를 클릭하세요. 그 클릭은 Step 으로 기록되지
          않습니다.
        </p>
      )}

      {/*
        008 — 형태는 정본의 `.table` 이 갖는다. 지금 쓰이는 줄과 최후 수단(CSS)을 옅은
        바탕으로 구분하는 규칙은 그대로다 — **순서 자체가 정보**이므로(원칙 IV) 어느
        줄이 쓰이는지 표에서 바로 읽혀야 한다.
      */}
      <table className="table pane">
        <thead>
          <tr>
            <th style={{ width: 20 }} />
            <th style={{ width: 118 }} />
            <th />
            <th style={{ width: 118 }} />
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const state = states[row.kind] ?? "수집되지 않음";
            const inUse = state === "사용 중";
            const last = i === rows.length - 1;
            const missing = row.value === null;
            return (
              <tr
                key={row.kind}
                className={inUse ? "in-use" : last ? "last-resort" : undefined}
              >
                <td className="num" style={{ padding: "0 0 0 14px" }}>
                  {i + 1}
                </td>
                <td className={missing ? "dim" : "strong-sm"}>{row.label}</td>
                <td className={`mono${missing ? " dim" : ""}`} style={{ wordBreak: "break-all" }}>
                  {row.value ?? "수집되지 않음"}
                </td>
                <td style={{ padding: "0 14px 0 0", textAlign: "right" }}>
                  {!missing && <span className={`chip ${tone(state)}`}>{state}</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
