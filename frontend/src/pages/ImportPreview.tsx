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
import { useState } from "react";

import type {
  ImportDecisions,
  ImportPlanView,
  ImportResultView,
  SheetPlanView,
  SkippedRow,
} from "../api/client";
import { ApiError, imports } from "../api/client";
import { Artboard, BrandMark, HeaderBar, HeaderDivider } from "../components/design/Chrome";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import { Toast } from "../components/Toast";
import type { ErrorInfo } from "../components/ErrorNotice";

import { Button } from "../ui/Button";

/** 컬럼 7개. 순서는 서버의 `ORDER` 와 같다 — 화면이 다른 순서를 쓰면 사용자가 헷갈린다. */
const ALL_COLUMNS = [
  "TC ID",
  "대상기능",
  "테스트항목",
  "수행자",
  "수행 절차",
  "기대 결과",
  "결과",
] as const;

/** 이 둘이 없으면 초안을 만들 수 없다 (FR-017). 서버의 `REQUIRED` 와 같아야 한다. */
const REQUIRED_COLUMNS = ["TC ID", "대상기능"] as const;

const SKIP_REASON: Record<SkippedRow["reason"], string> = {
  no_title: "「대상기능」 칸이 비어 있음",
  no_columns: "필수 컬럼(TC ID·대상기능)이 없음",
  empty: "빈 행",
};

export function ImportPreview({
  plan,
  onCancel,
  onDone,
  commit,
  confirmLabel = "가져오기",
}: {
  plan: ImportPlanView;
  /** 취소 — **아무것도 만들어지지 않은 상태로** 돌아간다 (FR-016). */
  onCancel: () => void;
  onDone: (result: ImportResultView) => void;
  /**
   * 확정하는 방법. 없으면 열린 프로젝트로 가져온다.
   *
   * 새 프로젝트를 만들며 가져오는 경로가 **같은 미리보기를 쓰게** 하려고 주입받는다 —
   * 두 벌로 두면 한쪽만 고쳐지고, 실제로 그랬다: 새 프로젝트 경로는 요약 배너만 보여
   * 접두어도 컬럼도 물을 자리가 없었다 (수렴 T089).
   */
  commit?: (decisions: ImportDecisions) => Promise<ImportResultView>;
  confirmLabel?: string;
}) {
  const [prefixes, setPrefixes] = useState<Record<string, string>>({});
  /** 시트마다 가져올지 (FR-020a). **기본은 가져오기다** — 빠진 것은 켜진 것으로 본다. */
  const [included, setIncluded] = useState<Record<string, boolean>>({});
  /** 시트별 컬럼 짝짓기 (FR-020e). 자동 판정을 이긴다. */
  const [columns, setColumns] = useState<Record<string, Record<string, number>>>({});
  /** 시트별 머리글 행 (FR-020i). 서버가 찾아낸 것이 기본값이고 사용자가 고친다. */
  const [headerRows, setHeaderRows] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const isOn = (sheet: SheetPlanView) => included[sheet.sheet_name] ?? sheet.included;
  const headerRowOf = (sheet: SheetPlanView) =>
    headerRows[sheet.sheet_name] ?? sheet.header_row ?? sheet.sample[0]?.row ?? 1;

  /**
   * 이 시트의 열 이름들.
   *
   * **사용자가 고른 머리글 행에서 읽는다.** 서버가 준 `headers` 는 서버가 고른 행 기준이라,
   * 화면에서 행을 바꾸면 그것과 어긋난다 — 사용자가 방금 고른 행의 값이 선택지에 나와야
   * 자기가 무엇을 짝짓는지 알 수 있다.
   */
  const headersOf = (sheet: SheetPlanView): string[] => {
    const picked = sheet.sample.find((r) => r.row === headerRowOf(sheet));
    if (!picked) return sheet.headers;
    return picked.cells.map((c, i) => c || `(${i + 1}번째 열)`);
  };

  /**
   * 이 시트의 컬럼 짝짓기 — 사용자가 고친 것이 있으면 그것, 없으면 서버가 찾은 것.
   *
   * **머리글 행을 바꿨으면 서버의 판정을 버린다.** 그 판정은 서버가 고른 행의 열 이름을
   * 보고 내린 것이라, 다른 행을 머리글로 삼는 순간 맞을 이유가 없다. 남겨 두면 화면이
   * 「이미 짝지어졌다」고 말하면서 엉뚱한 열을 가리킨다.
   */
  const columnsOf = (sheet: SheetPlanView): Record<string, number> => {
    const moved = headerRowOf(sheet) !== sheet.header_row;
    return { ...(moved ? {} : sheet.column_index), ...(columns[sheet.sheet_name] ?? {}) };
  };

  /** 지금 짝짓기로 이 시트가 쓸 수 있는가 (FR-020g). */
  const usable = (sheet: SheetPlanView) => {
    const map = columnsOf(sheet);
    return REQUIRED_COLUMNS.every((c) => (map[c] ?? -1) >= 0);
  };

  const live = plan.sheets.filter((s) => isOn(s) && usable(s));
  const asking = live.filter((s) => s.needs_prefix);
  const answered = asking.filter((s) => (prefixes[s.sheet_name] ?? "").trim() !== "").length;
  const needMapping = plan.sheets.filter((s) => isOn(s) && !usable(s));
  const nothingChosen = plan.sheets.every((s) => !isOn(s));
  const onCount = plan.sheets.filter((s) => isOn(s)).length;

  /*
    확정하면 늘어날 초안 수.

    **서버의 draft_count 와 같은 규칙으로 센다** (SC-005) — 켜져 있고, 컬럼이 갖춰졌고,
    접두어가 정해진 시트의 행만. 규칙이 어긋나면 미리보기가 예고한 수와 결과가 달라진다.
  */
  /**
   * 이 시트가 만들 초안 수.
   *
   * **서버가 못 읽은 시트는 `row_count` 가 0이다** — 필수 컬럼이 없으면 행을 만들지
   * 않기 때문이다. 사용자가 화면에서 짝지으면 그 시트는 살아나지만 `row_count` 는
   * 여전히 0이라, 그대로 쓰면 「0건을 만듭니다」라고 해 놓고 40건을 만든다 (수렴 2회차).
   * 그때는 `total_rows`(머리글을 뺀 실제 행 수)가 옳다.
   */
  const willMake = (sheet: SheetPlanView) =>
    sheet.missing_required.length > 0 || headerRowOf(sheet) !== sheet.header_row
      ? sheet.total_rows
      : sheet.row_count;

  const counted = live.filter(
    (s) => !s.needs_prefix || (prefixes[s.sheet_name] ?? "").trim() !== "",
  );
  const willCreate = counted.reduce((sum, s) => sum + willMake(s), 0);

  /**
   * 만들어질 그룹 수. **선택을 반영한다** (FR-020b).
   *
   * 서버의 `group_count` 는 미리보기 시점의 값이라, 사용자가 시트를 끄면 어긋난다 —
   * 「그룹 3개」라고 해 놓고 1개를 만들게 된다 (수렴 2회차).
   */
  const liveGroups = new Set(
    counted
      .map((s) => s.prefix ?? (prefixes[s.sheet_name] ?? "").trim().toUpperCase())
      .filter((p) => p && p !== "TC"),
  ).size;

  /*
    수용량은 **그룹마다** 본다 (FR-039d). 번호를 그룹마다 세므로 「프로젝트에 남은
    번호」라는 총량은 없다 — 총량으로 비교하면 그룹 둘이 600건씩인 파일에서 넘치지도
    않았는데 확정을 막는다 (수렴 2회차).
  */
  const byGroup = new Map<string, number>();
  for (const s of counted) {
    const prefix = s.prefix ?? (prefixes[s.sheet_name] ?? "").trim().toUpperCase();
    if (prefix) byGroup.set(prefix, (byGroup.get(prefix) ?? 0) + willMake(s));
  }
  const roomOf = (prefix: string) =>
    plan.capacity.groups.find((g) => g.prefix === prefix)?.available ?? plan.capacity.available;
  const tooFull = [...byGroup.entries()].filter(([prefix, n]) => n > roomOf(prefix));
  const overCapacity = tooFull.length > 0;

  const confirm = () => {
    setError(null);
    setBusy(true);
    const decisions: ImportDecisions = {
      prefixes,
      sheets: included,
      columns,
      header_rows: headerRows,
    };
    void (commit ? commit(decisions) : imports.commit(plan.plan_id, decisions))
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
        {error !== null && (
          <Toast tone="error" onDismiss={() => setError(null)}>
            <ErrorNotice error={error} />
          </Toast>
        )}

        {/* ── 무엇이 만들어지는가 ─────────────────────────────────────── */}
        <div data-import-summary className="tint-run" style={{ padding: "12px 14px" }}>
          <div className="strong-sm">
            그룹 {liveGroups}개, 테스트 초안 {willCreate}건을 만듭니다.
          </div>
          <div className="why" style={{ marginTop: 4 }}>
            초안은 아직 테스트가 아닙니다. 하나씩 골라 AI 녹화로 완성하면 테스트가 됩니다.
          </div>
          {/*
            수용량은 **그룹마다** 넘친다 (FR-039d). 그런데 문구는 「이 프로젝트에 남은
            번호」라는 총량을 말했다 — 판정과 설명이 어긋나 있었고, 사용자는 어느 그룹의
            어느 행을 덜어야 하는지 알 수 없었다. 넘친 그룹과 그 그룹의 남은 칸을
            **그룹마다** 말한다.
          */}
          {overCapacity && (
            <div className="why fail-ink" style={{ marginTop: 6 }} data-capacity-warning>
              {tooFull.map(([prefix, n]) => (
                <div key={prefix}>
                  그룹 「{prefix}」에 {n}건을 넣으려 하지만 남은 번호는 {roomOf(prefix)}개입니다.
                </div>
              ))}
              <div style={{ marginTop: 4 }}>
                그 그룹의 시트를 끄거나, 프로젝트를 나누세요.
              </div>
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
          <div className="row" style={{ marginBottom: 8, gap: 10 }}>
            <h2 className="strong-sm" style={{ margin: 0 }}>
              시트 {plan.sheets.length}개
            </h2>
            <span className="why" data-sheet-on-count>
              {onCount}개 켜짐
            </span>
            <div className="spacer" />
            {/*
              **한 번에 켜고 끈다.** 이 화면은 시트 200개를 받을 수 있다(이 파일 머리말).
              행마다 체크 상자만 두면 「이 시트 하나만 가져오기」에 199번의 클릭이 든다 —
              가장 흔한 두 뜻(전부·하나만)이 가장 비싼 조작이었다.
            */}
            <Button
              size="sm"
              data-action="import.all-on"
              disabled={busy || onCount === plan.sheets.length}
              onClick={() =>
                setIncluded(Object.fromEntries(plan.sheets.map((s) => [s.sheet_name, true])))
              } >
              전체 켜기
            </Button>
            <Button
              size="sm"
              data-action="import.all-off"
              disabled={busy || onCount === 0}
              onClick={() =>
                setIncluded(Object.fromEntries(plan.sheets.map((s) => [s.sheet_name, false])))
              } >
              전체 끄기
            </Button>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            {/*
              `scope` 를 붙인다 — 없으면 화면 낭독기가 칸을 읽을 때 어느 열인지 말할 수
              없고, 「가져오기 / USER / 40」 같은 값만 흐른다.
            */}
            <thead className="grid-head">
              <tr>
                <th scope="col" style={{ padding: "6px 8px", width: 44 }}>가져오기</th>
                <th scope="col" style={{ padding: "6px 8px" }}>시트</th>
                <th scope="col" style={{ padding: "6px 8px", width: 160 }}>그룹 접두어</th>
                <th scope="col" style={{ padding: "6px 8px", width: 80 }}>행</th>
                <th scope="col" style={{ padding: "6px 8px" }}>메모</th>
              </tr>
            </thead>
            <tbody>
              {plan.sheets.map((sheet) => (
                <tr
                  key={sheet.sheet_name}
                  data-sheet-row={sheet.sheet_name}
                  className={isOn(sheet) ? undefined : "dim"}
                >
                  <td style={{ padding: "6px 8px" }}>
                    {/*
                      가져올 시트를 고른다 (FR-020a). **기본은 켜짐**이다 — 사용자가 파일을
                      넣은 뜻은 「가져오겠다」이고, 빼는 것이 예외다.

                      끄는 것과 접두어를 못 정해 건너뛰는 것은 **다른 사실**이라 결과에서도
                      구별해 보고한다 (FR-020c).
                    */}
                    <input
                      type="checkbox"
                      data-sheet-include={sheet.sheet_name}
                      aria-label={`${sheet.sheet_name} 가져오기`}
                      checked={isOn(sheet)}
                      onChange={(e) =>
                        setIncluded((prev) => ({
                          ...prev,
                          [sheet.sheet_name]: e.target.checked,
                        }))
                      }
                    />
                  </td>
                  <td style={{ padding: "6px 8px" }}>{sheet.sheet_name}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {!isOn(sheet) ? (
                      <span className="why">가져오지 않음</span>
                    ) : !usable(sheet) ? (
                      <span className="why">아래에서 열을 짝지어 주세요</span>
                    ) : sheet.needs_prefix ? (
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
                  <td style={{ padding: "6px 8px", textAlign: "right" }}>
                    {usable(sheet) ? sheet.row_count : sheet.total_rows}
                  </td>
                  <td style={{ padding: "6px 8px" }}>
                    {/*
                      필수 컬럼을 못 찾은 시트 (FR-020g).

                      **버리지 않고 짝지을 기회를 준다.** 별칭 목록은 우리가 아는 표기만
                      담고 있어서, 사용자가 화면에서 보고 있는 열을 우리가 못 알아보는
                      경우가 반드시 생긴다. 그때 시트를 통째로 버리면 그 열이 눈앞에
                      있는데도 쓸 수 없다.
                    */}
                    {isOn(sheet) && !usable(sheet) && (
                      <div data-needs-mapping={sheet.sheet_name}>
                        <div className="why" style={{ marginBottom: 4 }}>
                          찾지 못한 컬럼: {sheet.missing_required.join(", ")} · 이 시트에{" "}
                          {sheet.total_rows}건이 기다립니다.
                        </div>
                      </div>
                    )}
                    {/*
                      표가 어디서 시작하는지 짚는다 (FR-020i·j · 2차 요청).

                      설계서는 위에 제목·작성일·범례를 두는 일이 흔하다. 첫 행을 머리글로
                      못박으면 그런 파일은 필수 컬럼을 영영 찾지 못하고, 사용자는 화면에서
                      열을 보고 있는데도 쓸 수 없다.

                      **앞부분을 그대로 보여 주고 고르게 한다** — 행 번호만 묻는 것보다
                      눈으로 짚는 편이 틀릴 여지가 적다.
                    */}
                    {isOn(sheet) && sheet.sample.length > 0 && (
                      <details data-header-row-picker={sheet.sheet_name} open={!usable(sheet)}>
                        <summary className="why" style={{ cursor: "pointer" }}>
                          머리글 행: {headerRowOf(sheet)}행
                        </summary>
                        {/*
                          글자 크기는 정본이 정한다 (시각 언어 G-2). 표본 표의 글자는
                          `.why` 가 이미 작게 그리므로 인라인으로 다시 선언하지 않는다.
                        */}
                        <table style={{ marginTop: 6, borderCollapse: "collapse" }}>
                          <tbody>
                            {sheet.sample.map((sampleRow) => (
                              <tr key={sampleRow.row}>
                                <td style={{ padding: "2px 6px" }}>
                                  <label className="row" style={{ gap: 4 }}>
                                    <input
                                      type="radio"
                                      name={`header-row-${sheet.sheet_name}`}
                                      data-header-row={`${sheet.sheet_name}:${sampleRow.row}`}
                                      aria-label={`${sheet.sheet_name} 의 ${sampleRow.row}행을 머리글로`}
                                      checked={headerRowOf(sheet) === sampleRow.row}
                                      onChange={() =>
                                        setHeaderRows((prev) => ({
                                          ...prev,
                                          [sheet.sheet_name]: sampleRow.row,
                                        }))
                                      }
                                    />
                                    <span className="why mono">{sampleRow.row}</span>
                                  </label>
                                </td>
                                {sampleRow.cells.slice(0, 8).map((cell, i) => (
                                  <td
                                    key={i}
                                    className={
                                      headerRowOf(sheet) === sampleRow.row ? "strong-sm" : "why"
                                    }
                                    style={{
                                      padding: "2px 6px",
                                      maxWidth: 140,
                                      overflow: "hidden",
                                      textOverflow: "ellipsis",
                                      whiteSpace: "nowrap",
                                    }}
                                  >
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </details>
                    )}
                    {isOn(sheet) && (
                      <details data-column-mapping={sheet.sheet_name} open={!usable(sheet)}>
                        <summary className="why" style={{ cursor: "pointer" }}>
                          열 짝짓기
                        </summary>
                        <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                          {ALL_COLUMNS.map((column) => (
                            <label
                              key={column}
                              className="row"
                              style={{ gap: 6, alignItems: "center" }}
                            >
                              <span className="why" style={{ minWidth: 76 }}>
                                {column}
                                {REQUIRED_COLUMNS.includes(
                                  column as (typeof REQUIRED_COLUMNS)[number],
                                ) && " *"}
                              </span>
                              <select
                                data-column-select={`${sheet.sheet_name}:${column}`}
                                aria-label={`${sheet.sheet_name} 의 ${column} 열`}
                                value={String(columnsOf(sheet)[column] ?? -1)}
                                onChange={(e) =>
                                  setColumns((prev) => ({
                                    ...prev,
                                    [sheet.sheet_name]: {
                                      ...(prev[sheet.sheet_name] ?? {}),
                                      [column]: Number(e.target.value),
                                    },
                                  }))
                                }
                                style={{ margin: 0 }}
                              >
                                <option value="-1">쓰지 않음</option>
                                {headersOf(sheet).map((label, pos) => (
                                  <option key={`${label}-${pos}`} value={String(pos)}>
                                    {label}
                                  </option>
                                ))}
                              </select>
                            </label>
                          ))}
                        </div>
                      </details>
                    )}
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
        {/*
          **많으면 접어 둔다.** 시트 200개를 받는 화면이므로 건너뛸 행이 수백 건일 수
          있고, 그때 펼친 목록이 확정 버튼을 화면 밖으로 밀어낸다. 20건까지는 펼쳐
          둔다 — 그 규모에서는 전부 읽는 것이 사용자가 하려는 일이다.
        */}
        {plan.skipped.length > 0 && (
          <details data-skipped-rows open={plan.skipped.length <= 20}>
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

        {/*
          ── 확정 ───────────────────────────────────────────────────────────

          **띠가 화면 아래에 붙어 따라온다** (`.commit-bar`). 시트가 200개면 이 자리가
          스크롤 수천 픽셀 아래로 밀리고, 시트 하나를 고친 사용자는 확정하려고 목록
          끝까지 내려가야 했다. 되돌릴 길(취소)이 멀어지는 것도 같은 문제다.
        */}
        <div
          className="commit-bar row"
          style={{ gap: 8, marginTop: 8, padding: "10px 0", flexWrap: "wrap" }}
        >
          <Button
            variant="primary"
            data-action="import.confirm"
            aria-busy={busy}
            disabled={busy || overCapacity || nothingChosen}
            onClick={confirm} >
            {busy ? "가져오는 중…" : confirmLabel}
          </Button>
          <Button data-action="import.cancel" disabled={busy} onClick={onCancel}>
            취소
          </Button>
          {/* 전부 끄면 만들 것이 없다 (FR-020d). 막고, 왜 막혔는지 말한다. */}
          {nothingChosen && (
            <span className="why fail-ink" data-nothing-chosen>
              가져올 시트를 하나도 고르지 않았습니다.
            </span>
          )}
          {!nothingChosen && needMapping.length > 0 && (
            <span className="why" data-needs-mapping-count>
              열을 짝지어야 하는 시트 {needMapping.length}개가 있습니다. 그대로 두면
              건너뜁니다.
            </span>
          )}
          {!nothingChosen && asking.length > 0 && (
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
  small = false,
}: {
  label: string;
  onPlan: (plan: ImportPlanView) => void;
  onError: (error: ErrorInfo) => void;
  disabled?: boolean;
  /**
   * 이웃과 같은 크기로 맞춘다 (`.btn.sm` — 높이 26·12px).
   *
   * **조작의 크기는 자리가 정한다.** 이 컴포넌트는 언제나 전체 크기 `.btn` 이었고,
   * 목록 툴바의 이웃은 전부 `.btn sm` 이다 — 「엑셀에서 가져오기」만 혼자 커서
   * 더 중요한 조작처럼 보였다. 크기는 위계를 말하므로 이웃과 어긋나면 거짓말이 된다.
   */
  small?: boolean;
}) {
  const [busy, setBusy] = useState(false);

  const off = disabled || busy;

  return (
    /*
      **`<label>` 이 조작이고 초점은 안쪽 칸에 있다.**

      이전 판은 칸을 `display:none` 으로 감췄다. 그러면 칸이 Tab 순서에서 사라지고
      `<label>` 은 원래 초점을 받지 않으므로, 이 조작에 **키보드로 도달할 수 없었다** —
      「엑셀에서 가져오기」와 「엑셀에서 새 프로젝트」 둘 다 그 상태였다. 이 도구는
      키보드로 도는 도구다 (`tokens.css` 의 `:focus-visible` 주석).

      `.file-input` 은 보이지 않게만 하고 초점은 남긴다. 링은 라벨이 그린다
      (`.btn.file:focus-within`). `<input type=file>` 은 초점을 받은 상태에서
      Space·Enter 로 열리므로, 마우스 없이 같은 일을 할 수 있다.
    */
    <label
      className={`btn file${small ? " sm" : ""}${off ? " disabled" : ""}`}
      aria-disabled={off}
    >
      {busy ? "읽는 중…" : label}
      <input
        type="file"
        accept=".xlsx"
        data-import-file
        disabled={off}
        className="file-input"
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

/**
 * 가져오기 완료 알림 (014 FR-018a · 수렴 T088).
 *
 * **미리보기에서만 보이면 확정하는 순간 사라진다.** 무엇이 빠졌는지 다시 확인할 길이
 * 없어, 사용자는 설계서와 제품을 눈으로 대조해야 한다.
 *
 * 「내가 뺀 시트」와 「제품이 못 읽은 시트」를 나눠 말한다 (FR-020c) — 뭉치면 사용자가
 * 둘을 구별할 수 없고, 자기가 뺀 것까지 문제로 읽는다.
 */
export function ImportDoneNotice({
  result,
  onDismiss,
}: {
  result: ImportResultView;
  onDismiss: () => void;
}) {
  const groups = result.created_groups.length;
  const drafts = result.drafts.length;
  const noise =
    result.skipped.length + result.skipped_sheets.length + result.renumbered.length;

  return (
    <Toast mark="data-import-done" tone={noise > 0 ? "warn" : "info"} onDismiss={onDismiss}>
      <div className="strong-sm">
        그룹 {groups}개, 테스트 초안 {drafts}건을 만들었습니다.
      </div>

      {result.ignored_sheets.length > 0 && (
        <div className="why" style={{ marginTop: 4 }} data-ignored-sheets>
          가져오지 않기로 한 시트: {result.ignored_sheets.join(", ")}
        </div>
      )}

      {result.skipped_sheets.length > 0 && (
        <div className="why" style={{ marginTop: 4 }} data-skipped-sheets>
          읽지 못해 건너뛴 시트:{" "}
          {result.skipped_sheets
            .map((s) => `${s.sheet_name}(${SHEET_SKIP_REASON[s.reason] ?? s.reason})`)
            .join(", ")}
        </div>
      )}

      {result.renumbered.length > 0 && (
        <details style={{ marginTop: 6 }} data-done-renumbered>
          <summary className="why" style={{ cursor: "pointer" }}>
            번호가 바뀐 행 {result.renumbered.length}건
          </summary>
          {result.renumbered.map((r) => (
            <div key={`${r.row}-${r.from}`} className="why mono">
              {r.row}행: {r.from} → {r.to}
            </div>
          ))}
        </details>
      )}

      {result.skipped.length > 0 && (
        <details style={{ marginTop: 6 }} data-done-skipped>
          <summary className="why" style={{ cursor: "pointer" }}>
            건너뛴 행 {result.skipped.length}건
          </summary>
          {result.skipped.map((s) => (
            <div key={`${s.sheet_name}-${s.row}`} className="why">
              {s.sheet_name} {s.row}행 — {SKIP_REASON[s.reason]}
            </div>
          ))}
        </details>
      )}

    </Toast>
  );
}

const SHEET_SKIP_REASON: Record<string, string> = {
  no_prefix: "그룹 접두어를 정하지 않음",
  no_columns: "필수 컬럼을 짝짓지 않음",
};
