/**
 * 가져오기 미리보기 (014 US2 · FR-015·FR-016·FR-022a·FR-023b·FR-024a).
 *
 * **이 화면이 있는 이유는 확정 전에 아무것도 만들지 않기 위해서다.** 파일을 고르는 순간
 * 만들어 버리면 사용자는 자기가 무엇을 들여왔는지 나중에 알게 되고, 되돌리려면 손으로
 * 지워야 한다.
 *
 * 보여야 하는 넷:
 *
 * 1. **무엇이 만들어지는가** — 그룹 수·초안 수
 * 2. **무엇을 물어야 하는가** — 접두어를 읽어내지 못한 시트 (FR-022a)
 * 3. **무엇이 바뀌는가** — 중복으로 번호가 바뀐 행, 기존 그룹과 이름이 다른 시트
 * 4. **무엇이 빠지는가** — 건너뛸 행과 그 이유·위치
 *
 * 모달로 하지 않은 이유는 시트가 200개까지 올 수 있어서다.
 */
import { useMemo, useState } from "react";

import type { ImportPlanView, ImportResultView, SkippedRow } from "../api/client";
import { ApiError, imports } from "../api/client";
import { Artboard, BrandMark, HeaderBar, HeaderDivider } from "../components/design/Chrome";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

const SKIP_REASON: Record<SkippedRow["reason"], string> = {
  no_title: "「대상기능」 칸이 비어 있음",
  no_columns: "필수 컬럼(TC ID·대상기능)이 없음",
  empty: "빈 행",
};

export function ImportPreview({
  plan,
  onCancel,
  onDone,
}: {
  plan: ImportPlanView;
  /** 취소 — **아무것도 만들어지지 않은 상태로** 돌아간다 (FR-016). */
  onCancel: () => void;
  onDone: (result: ImportResultView) => void;
}) {
  const [prefixes, setPrefixes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const asking = useMemo(() => plan.sheets.filter((s) => s.needs_prefix), [plan.sheets]);
  const answered = asking.filter((s) => (prefixes[s.sheet_name] ?? "").trim() !== "").length;

  /*
    확정하면 늘어날 초안 수. 접두어를 답한 시트의 행이 더해진다 — 서버의 draft_count 는
    접두어가 정해진 시트만 세므로(SC-005), 화면도 같은 규칙으로 더해야 수가 맞는다.
  */
  const willCreate =
    plan.draft_count +
    asking
      .filter((s) => (prefixes[s.sheet_name] ?? "").trim() !== "")
      .reduce((sum, s) => sum + s.row_count, 0);

  const overCapacity = willCreate > plan.capacity.available;

  const confirm = () => {
    setError(null);
    setBusy(true);
    void imports
      .commit(plan.plan_id, prefixes)
      .then(onDone)
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  return (
    <Artboard width={1000} minHeight={700}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <span className="subtitle">엑셀에서 가져오기</span>
        <div className="spacer" />
        <span className="why mono">{plan.file_name}</span>
      </HeaderBar>

      <div style={{ padding: "20px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
        <ErrorNotice error={error} />

        {/* ── 무엇이 만들어지는가 ─────────────────────────────────────── */}
        <div data-import-summary className="tint-run" style={{ padding: "12px 14px" }}>
          <div className="strong-sm">
            그룹 {plan.group_count}개, 테스트 초안 {willCreate}건을 만듭니다.
          </div>
          <div className="why" style={{ marginTop: 4 }}>
            초안은 아직 테스트가 아닙니다. 하나씩 골라 AI 녹화로 완성하면 테스트가 됩니다.
          </div>
          {overCapacity && (
            <div className="why" style={{ marginTop: 6 }} data-capacity-warning>
              이 프로젝트에 남은 번호는 {plan.capacity.available}개입니다. 가져올 행을 줄이거나
              프로젝트를 나누세요.
            </div>
          )}
        </div>

        {plan.warnings.length > 0 && (
          <div data-import-warnings className="tint-warn" style={{ padding: "12px 14px" }}>
            {plan.warnings.map((w) => (
              <div key={w} className="why">
                {w}
              </div>
            ))}
          </div>
        )}

        {/* ── 시트별 ──────────────────────────────────────────────────── */}
        <div>
          <div className="strong-sm" style={{ marginBottom: 8 }}>
            시트 {plan.sheets.length}개
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>시트</th>
                <th style={{ textAlign: "left", padding: "6px 8px", width: 160 }}>그룹 접두어</th>
                <th style={{ textAlign: "right", padding: "6px 8px", width: 80 }}>행</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>메모</th>
              </tr>
            </thead>
            <tbody>
              {plan.sheets.map((sheet) => (
                <tr key={sheet.sheet_name} data-sheet-row={sheet.sheet_name}>
                  <td style={{ padding: "6px 8px" }}>{sheet.sheet_name}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {sheet.needs_prefix ? (
                      /*
                        접두어를 읽어내지 못한 시트 (FR-022a). **시스템이 만들어내지
                        않는다** — 한글 시트 이름에서 뽑은 접두어는 사용자가 예측할 수
                        없다. 비워 두면 그 시트를 건너뛴다 (FR-022b).
                      */
                      <input
                        data-prefix-input={sheet.sheet_name}
                        aria-label={`${sheet.sheet_name} 그룹 접두어`}
                        placeholder="예: USER (비우면 건너뜀)"
                        maxLength={8}
                        value={prefixes[sheet.sheet_name] ?? ""}
                        onChange={(e) =>
                          setPrefixes((prev) => ({
                            ...prev,
                            [sheet.sheet_name]: e.target.value.toUpperCase(),
                          }))
                        }
                        style={{ width: "100%" }}
                      />
                    ) : (
                      <span className="mono">{sheet.prefix}</span>
                    )}
                  </td>
                  <td style={{ padding: "6px 8px", textAlign: "right" }}>{sheet.row_count}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {sheet.name_differs && (
                      <div className="why" data-name-differs={sheet.sheet_name}>
                        이미 있는 그룹 「{sheet.existing_group_name}」을 씁니다. 그룹 이름은
                        바꾸지 않습니다.
                      </div>
                    )}
                    {sheet.renumbered.length > 0 && (
                      <details data-renumbered={sheet.sheet_name}>
                        <summary className="why" style={{ cursor: "pointer" }}>
                          번호가 바뀐 행 {sheet.renumbered.length}건
                        </summary>
                        {sheet.renumbered.map((r) => (
                          <div key={`${r.row}-${r.from}`} className="why mono">
                            {r.row}행: {r.from} → {r.to}
                          </div>
                        ))}
                      </details>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ── 무엇이 빠지는가 ─────────────────────────────────────────── */}
        {plan.skipped.length > 0 && (
          <details data-skipped-rows open>
            <summary className="strong-sm" style={{ cursor: "pointer" }}>
              건너뛸 행 {plan.skipped.length}건
            </summary>
            <div style={{ marginTop: 6 }}>
              {plan.skipped.map((s) => (
                <div key={`${s.sheet_name}-${s.row}`} className="why">
                  {s.sheet_name} {s.row}행 — {SKIP_REASON[s.reason]}
                </div>
              ))}
            </div>
          </details>
        )}

        {/* ── 확정 ─────────────────────────────────────────────────────── */}
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button
            className="btn primary"
            data-action="import.confirm"
            disabled={busy || overCapacity}
            onClick={confirm}
          >
            {busy ? "가져오는 중…" : "가져오기"}
          </button>
          <button className="btn" data-action="import.cancel" disabled={busy} onClick={onCancel}>
            취소
          </button>
          {asking.length > 0 && (
            <span className="why">
              접두어를 물어야 하는 시트 {asking.length}개 중 {answered}개 답했습니다. 비워 둔
              시트는 건너뜁니다.
            </span>
          )}
        </div>
      </div>
    </Artboard>
  );
}

/**
 * 파일을 골라 미리보기를 여는 버튼.
 *
 * `accept` 를 붙이는 이유는 사용자가 `.xls`·`.csv` 를 골랐다가 서버에서 거절당하는 왕복을
 * 줄이려는 것이다. **거절 자체를 없애지는 않는다** — 확장자만 바꾼 파일이 있고, 형식 판정은
 * 서버가 내용으로 한다.
 */
export function ImportFilePicker({
  label,
  onPlan,
  onError,
  disabled = false,
}: {
  label: string;
  onPlan: (plan: ImportPlanView) => void;
  onError: (error: ErrorInfo) => void;
  disabled?: boolean;
}) {
  const [busy, setBusy] = useState(false);

  return (
    <label className={`btn${disabled || busy ? " disabled" : ""}`} style={{ cursor: "pointer" }}>
      {busy ? "읽는 중…" : label}
      <input
        type="file"
        accept=".xlsx"
        data-import-file
        disabled={disabled || busy}
        style={{ display: "none" }}
        onChange={(event) => {
          const file = event.target.files?.[0];
          // 값을 비워 둔다 — 같은 파일을 다시 고를 수 있어야 한다.
          event.target.value = "";
          if (!file) return;
          setBusy(true);
          void imports
            .preview(file)
            .then(onPlan)
            .catch((exc: unknown) =>
              onError(exc instanceof ApiError ? describeError(exc) : describeError(exc)),
            )
            .finally(() => setBusy(false));
        }}
      />
    </label>
  );
}
