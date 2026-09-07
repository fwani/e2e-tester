/**
 * 테스트 목록. **`docs/design/TestList.dc.html`(1440×760) 전사.** DC-001~DC-008.
 *
 * 인라인 style 값을 확정 디자인에서 그대로 옮겼다. 축약·토큰 치환·"더 나은" 간격으로
 * 바꾸지 않았다 — 그것이 002 라운드가 고치는 결함이다.
 *
 * 동작은 001 그대로다: FR-002~FR-007 (상태 배지·ID·이름·Step 수·작성 배지·마지막
 * 실행·검색·집계·이름 변경·삭제). **삭제는 되돌릴 수 없으므로 확인을 받는다** — 확인은
 * 브라우저 `confirm` 이 아니라 행 안에서 받는다. 어느 테스트를 지우는지 눈으로 보면서
 * 결정하게 한다.
 *
 * 확정 디자인이 정의하지 않은 상태(로딩·빈 목록·정의 오류·삭제 확인)는
 * `design-conformance/undefined-states.md` 에 근거와 함께 기록했다 (DC-009).
 */
import { useEffect, useMemo, useState } from "react";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { tests, type SessionView, type TestListRow, type TestListResponse } from "../api/client";
import { Artboard, BrandMark, HeaderBar, HeaderDivider } from "../components/design/Chrome";
import { stepLabel } from "../lib/wording";


function relativeTime(iso: string | null): string {
  if (iso === null) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "방금";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.round(hours / 24)}일 전`;
}

export interface TestListProps {
  /** 헤더에 표시할 프로젝트 이름. 확정 디자인의 「데이터 플랫폼」 자리다. */
  projectName?: string;
  onCreate: () => void;
  onOpenResult: (testId: string) => void;
  onRun: (testId: string) => void;
  /** 정의 보기 (FR-016). 실행하지 않고 Step 목록·상세를 확인한다. */
  onOpenDefinition?: (testId: string) => void;
  /** 확정 디자인에 없는 화면들로 가는 진입점 (DC-010). */
  onOpenSecrets?: () => void;
  onOpenKeys?: () => void;
  /**
   * 살아 있는 세션. 새로고침으로 화면만 잃은 녹화·실행을 되찾는 길이다 (UX U-05).
   * 서버에는 Step 과 브라우저가 그대로 있는데 화면이 그것을 말하지 않으면 사용자는
   * 새 녹화를 시작하고, 앞의 기록은 영영 못 찾는다.
   */
  activeSessions?: SessionView[];
  onResumeSession?: (session: SessionView) => void;
  onDiscardSession?: (sessionId: string) => void;
}

export function TestList({
  projectName = "프로젝트",
  onCreate,
  onOpenResult,
  onRun,
  onOpenDefinition,
  onOpenSecrets,
  onOpenKeys,
  activeSessions = [],
  onResumeSession,
  onDiscardSession,
}: TestListProps) {
  const [data, setData] = useState<TestListResponse | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = async (q: string) => {
    try {
      setData(await tests.list(q.trim() || undefined));
      setError(null);
    } catch (exc) {
      setError(describeError(exc));
    }
  };

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reload(query);
    } catch (exc) {
      setError(describeError(exc));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void reload(query);
    // 검색어가 바뀔 때마다 다시 조회한다. 로컬 도구이므로 디바운스 없이도 충분하다.
  }, [query]);

  const counts = useMemo(() => data?.counts ?? { total: 0, pass: 0, fail: 0 }, [data]);
  const rows = data?.tests ?? [];

  return (
    <Artboard width={1440} minHeight={760}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            font: "500 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          }}
        >
          <span style={{ color: "#6B675C" }}>프로젝트</span>
          <span
            style={{
              border: "2px solid #14130F",
              background: "#EFEBE0",
              padding: "7px 12px",
              fontWeight: "600",
            }}
          >
            {projectName}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <div
            style={{
              padding: "8px 12px",
              font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              borderBottom: "3px solid #14130F",
            }}
          >
            테스트
          </div>
        </div>
        <div style={{ flex: "1" }} />
        {/* 확정 디자인에 없는 화면들의 진입점. 눈에 띄지 않게 둔다 (DC-010). */}
        {onOpenSecrets && (
          <button className="ghost" onClick={onOpenSecrets}>
            비밀 값
          </button>
        )}
        {onOpenKeys && (
          <button className="ghost" onClick={onOpenKeys}>
            키 관리
          </button>
        )}
        <button
          onClick={onCreate}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "9px",
            height: "44px",
            padding: "0 18px",
            background: "#14130F",
            color: "#F5F2E9",
            border: "3px solid #14130F",
            boxShadow: "5px 5px 0 #F5D000",
            font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M8 3v10M3 8h10" />
          </svg>
          테스트 만들기
        </button>
      </HeaderBar>

      <div
        style={{
          flex: "1",
          display: "flex",
          flexDirection: "column",
          gap: "22px",
          padding: "30px 40px 40px",
        }}
      >
        {activeSessions.length > 0 && (
          <ActiveSessionsBanner
            sessions={activeSessions}
            onResume={onResumeSession}
            onDiscard={onDiscardSession}
          />
        )}
        <div style={{ display: "flex", alignItems: "flex-end", gap: "16px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div
              style={{
                font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace",
                letterSpacing: "0.14em",
                color: "#6B675C",
              }}
            >
              INTEGRATION TESTS
            </div>
            <div
              style={{
                fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
                fontSize: "40px",
                lineHeight: "1",
                letterSpacing: "-0.01em",
              }}
            >
              테스트
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              flex: "1",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              height: "46px",
              padding: "0 14px",
              border: "3px solid #14130F",
              background: "#FFFDF6",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="#6B675C" strokeWidth="2.2">
              <circle cx="7.5" cy="7.5" r="5" />
              <path d="M11.5 11.5L16 16" />
            </svg>
            <input
              aria-label="테스트 검색"
              placeholder="테스트 이름 또는 ID 검색"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{
                flex: 1,
                border: "none",
                background: "transparent",
                padding: 0,
                minHeight: "auto",
                font: "400 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
                outline: "none",
              }}
            />
          </div>
          <div style={{ display: "flex", gap: "0", border: "3px solid #14130F" }}>
            <div
              style={{
                height: "46px",
                padding: "0 16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "#14130F",
                color: "#F5F2E9",
                font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              }}
            >
              전체
              <span style={{ fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}>
                {counts.total}
              </span>
            </div>
            <div
              style={{
                height: "46px",
                padding: "0 16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "#FFFDF6",
                borderLeft: "3px solid #14130F",
                font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              }}
            >
              PASS
              <span style={{ fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: "#2E9455" }}>
                {counts.pass}
              </span>
            </div>
            <div
              style={{
                height: "46px",
                padding: "0 16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "#FFFDF6",
                borderLeft: "3px solid #14130F",
                font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              }}
            >
              FAIL
              <span style={{ fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: "#D9502F" }}>
                {counts.fail}
              </span>
            </div>
          </div>
        </div>

        {error !== null && (
          <div
            style={{
              border: "3px solid #14130F",
              background: "#FBEEEA",
              color: "#A83A22",
              padding: "12px 16px",
              whiteSpace: "pre-wrap",
            }}
            role="alert"
          >
            <ErrorNotice error={error} />
          </div>
        )}

        {data !== null && data.problems.length > 0 && (
          <div
            style={{
              border: "3px solid #14130F",
              background: "#FFF9D6",
              padding: "12px 16px",
            }}
            role="status"
          >
            <strong>읽지 못한 정의 파일이 있습니다.</strong>
            <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
              {data.problems.map((p) => (
                <li key={p} style={{ fontFamily: "'IBM Plex Mono', ui-monospace, monospace", fontSize: 13 }}>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div style={{ border: "3px solid #14130F", background: "#FFFDF6", boxShadow: "7px 7px 0 #14130F" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              height: "44px",
              background: "#14130F",
              color: "#EFEBE0",
              padding: "0 18px",
              font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace",
              letterSpacing: "0.12em",
            }}
          >
            <div style={{ width: "92px" }}>상태</div>
            <div style={{ width: "108px" }}>ID</div>
            <div style={{ flex: "1", minWidth: "0" }}>이름</div>
            <div style={{ width: "74px", textAlign: "right" }}>STEP</div>
            <div style={{ width: "118px", paddingLeft: "24px" }}>작성</div>
            <div style={{ width: "130px" }}>마지막 실행</div>
            <div style={{ width: "132px" }} />
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              height: "46px",
              padding: "0 18px",
              background: "#E4DFD1",
              borderTop: "3px solid #14130F",
              font: "600 13px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              gap: "10px",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#14130F" strokeWidth="2.4">
              <path d="M3.5 5L7 9l3.5-4" />
            </svg>
            Project Tests
            <span style={{ fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
              {counts.total}
            </span>
          </div>

          {/* 확정 디자인은 목록에 항상 행이 있는 상태만 보여준다. 로딩·빈 목록은
              undefined-states.md 에 기록했다 (DC-009). */}
          {data === null && (
            <div style={{ padding: "24px 18px", borderTop: "2px solid #14130F", color: "#9A968A" }}>
              불러오는 중…
            </div>
          )}

          {data !== null && rows.length === 0 && (
            <div style={{ padding: "24px 18px", borderTop: "2px solid #14130F", color: "#6B675C" }}>
              {query.trim() === ""
                ? "아직 테스트가 없습니다. 「테스트 만들기」로 첫 테스트를 만드세요."
                : `"${query}" 에 해당하는 테스트가 없습니다.`}
            </div>
          )}

          {rows.map((row) => (
            <Row
              key={row.id}
              row={row}
              busy={busy}
              renaming={renaming?.id === row.id ? renaming.name : null}
              confirming={confirmingDelete === row.id}
              menuOpen={menuFor === row.id}
              onRenameChange={(name) => setRenaming({ id: row.id, name })}
              onRenameStart={() => {
                setMenuFor(null);
                setRenaming({ id: row.id, name: row.name });
              }}
              onRenameCancel={() => setRenaming(null)}
              onRenameSubmit={(name) =>
                void act(() => tests.rename(row.id, name)).then(() => setRenaming(null))
              }
              onDeleteStart={() => {
                setMenuFor(null);
                setConfirmingDelete(row.id);
              }}
              onDeleteCancel={() => setConfirmingDelete(null)}
              onDeleteConfirm={() =>
                void act(() => tests.remove(row.id)).then(() => setConfirmingDelete(null))
              }
              onToggleMenu={() => setMenuFor(menuFor === row.id ? null : row.id)}
              onRun={() => onRun(row.id)}
              onOpenResult={() => onOpenResult(row.id)}
              onOpenDefinition={onOpenDefinition ? () => onOpenDefinition(row.id) : undefined}
            />
          ))}
        </div>
      </div>
    </Artboard>
  );
}

// ─── 행 ─────────────────────────────────────────────────────────────────────

function Row({
  row,
  busy,
  renaming,
  confirming,
  menuOpen,
  onRenameChange,
  onRenameStart,
  onRenameCancel,
  onRenameSubmit,
  onDeleteStart,
  onDeleteCancel,
  onDeleteConfirm,
  onToggleMenu,
  onRun,
  onOpenResult,
  onOpenDefinition,
}: {
  row: TestListRow;
  busy: boolean;
  renaming: string | null;
  confirming: boolean;
  menuOpen: boolean;
  onRenameChange: (name: string) => void;
  onRenameStart: () => void;
  onRenameCancel: () => void;
  onRenameSubmit: (name: string) => void;
  onDeleteStart: () => void;
  onDeleteCancel: () => void;
  onDeleteConfirm: () => void;
  onToggleMenu: () => void;
  onRun: () => void;
  onOpenResult: () => void;
  onOpenDefinition?: () => void;
}) {
  const failed = row.outcome === "fail";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        minHeight: "74px",
        padding: "0 18px",
        borderTop: "2px solid #14130F",
        // 확정 디자인은 실패 행에 옅은 붉은 배경을 준다.
        ...(failed ? { background: "#FBEEEA" } : {}),
      }}
    >
      <div style={{ width: "92px" }}>
        <OutcomeChip outcome={row.outcome} />
      </div>

      <div style={{ width: "108px", font: "600 14px/1 'IBM Plex Mono', ui-monospace, monospace" }}>
        {row.id}
      </div>

      <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "4px" }}>
        {renaming !== null ? (
          <div style={{ display: "flex", gap: 8, alignItems: "center", paddingRight: 12 }}>
            <input
              aria-label="새 이름"
              value={renaming}
              autoFocus
              onChange={(e) => onRenameChange(e.target.value)}
              style={{ minHeight: 40 }}
            />
            <button disabled={busy || renaming.trim() === ""} onClick={() => onRenameSubmit(renaming.trim())}>
              저장
            </button>
            <button className="secondary" onClick={onRenameCancel}>
              취소
            </button>
          </div>
        ) : (
          <div style={{ font: "600 16px/1.3 'IBM Plex Sans KR', system-ui, sans-serif" }}>{row.name}</div>
        )}

        {/* FR-005 — 실패한 테스트는 실패 Step 번호와 메시지 요약을 인라인으로 보여준다. */}
        {row.failure_summary !== null && (
          <div
            style={{
              font: "400 13px/1.3 'IBM Plex Mono', ui-monospace, monospace",
              color: "#A83A22",
            }}
          >
            {stepLabel(row.failure_summary.step_index)} ·{" "}
            {row.failure_summary.message}
          </div>
        )}

        {confirming && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", paddingTop: 4 }}>
            <span style={{ color: "#A83A22", fontSize: 13 }}>
              「{row.name}」을 지웁니다. 되돌릴 수 없습니다.
            </span>
            <button className="danger" disabled={busy} onClick={onDeleteConfirm}>
              삭제
            </button>
            <button className="secondary" onClick={onDeleteCancel}>
              취소
            </button>
          </div>
        )}
      </div>

      <div
        style={{
          width: "74px",
          textAlign: "right",
          font: "400 14px/1 'IBM Plex Mono', ui-monospace, monospace",
          color: "#6B675C",
        }}
      >
        {row.step_count}
      </div>

      <div style={{ width: "118px", paddingLeft: "24px" }}>
        <AuthoringChip mode={row.authoring_mode} />
      </div>

      <div
        style={{
          width: "130px",
          font: "400 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          color: "#6B675C",
        }}
      >
        {relativeTime(row.last_run_at)}
      </div>

      <div style={{ width: "132px", display: "flex", justifyContent: "flex-end", gap: "8px", position: "relative" }}>
        {failed ? (
          <button
            onClick={onOpenResult}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              height: "44px",
              padding: "0 14px",
              border: "3px solid #14130F",
              background: "#F5D000",
              color: "#14130F",
              boxShadow: "4px 4px 0 #14130F",
              font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            결과 보기
          </button>
        ) : (
          <button
            onClick={onRun}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              height: "44px",
              padding: "0 14px",
              border: "3px solid #14130F",
              background: "#FFFDF6",
              color: "#14130F",
              boxShadow: "4px 4px 0 #14130F",
              font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            <svg width="13" height="13" viewBox="0 0 16 16">
              <path d="M4 2l10 6-10 6z" fill="currentColor" />
            </svg>
            실행
          </button>
        )}

        <button
          aria-label={`${row.name} 추가 동작`}
          onClick={onToggleMenu}
          style={{
            width: "44px",
            height: "44px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "3px solid #14130F",
            background: "#FFFDF6",
            padding: 0,
            boxShadow: "none",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="#14130F">
            <circle cx="8" cy="3" r="1.6" />
            <circle cx="8" cy="8" r="1.6" />
            <circle cx="8" cy="13" r="1.6" />
          </svg>
        </button>

        {menuOpen && (
          <div
            style={{
              position: "absolute",
              top: "48px",
              right: 0,
              zIndex: 5,
              border: "3px solid #14130F",
              background: "#FFFDF6",
              boxShadow: "5px 5px 0 #14130F",
              display: "flex",
              flexDirection: "column",
              minWidth: "160px",
            }}
          >
            {onOpenDefinition && (
              <button className="ghost" onClick={onOpenDefinition} style={{ justifyContent: "flex-start" }}>
                정의 보기
              </button>
            )}
            <button className="ghost" onClick={onRenameStart} style={{ justifyContent: "flex-start" }}>
              이름
            </button>
            <button className="ghost" onClick={onDeleteStart} style={{ justifyContent: "flex-start", color: "#A83A22" }}>
              삭제
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── 확정 디자인의 칩 ───────────────────────────────────────────────────────

function OutcomeChip({ outcome }: { outcome: "pass" | "fail" | null }) {
  if (outcome === null) {
    // 확정 디자인에 "실행한 적 없음" 표현이 없다. undefined-states.md 참조.
    return (
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          height: "28px",
          padding: "0 10px",
          background: "#EFEBE0",
          color: "#6B675C",
          border: "2px solid #14130F",
          font: "700 12px/1 'IBM Plex Mono', ui-monospace, monospace",
          letterSpacing: "0.06em",
        }}
      >
        —
      </div>
    );
  }
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        height: "28px",
        padding: "0 10px",
        background: outcome === "pass" ? "#2E9455" : "#D9502F",
        color: "#FFFDF6",
        border: "2px solid #14130F",
        font: "700 12px/1 'IBM Plex Mono', ui-monospace, monospace",
        letterSpacing: "0.06em",
      }}
    >
      {outcome === "pass" ? "PASS" : "FAIL"}
    </div>
  );
}

function AuthoringChip({ mode }: { mode: "record" | "ai" }) {
  if (mode === "ai") {
    return (
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "7px",
          height: "28px",
          padding: "0 10px",
          border: "2px solid #14130F",
          background: "#F0EBFC",
          font: "600 12px/1 'IBM Plex Sans KR', system-ui, sans-serif",
        }}
      >
        <svg width="12" height="12" viewBox="0 0 18 18" fill="none" stroke="#7C4DDB" strokeWidth="2.4">
          <path d="M9 1.5v4M9 12.5v4M1.5 9h4M12.5 9h4" />
        </svg>
        AI
      </div>
    );
  }
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "7px",
        height: "28px",
        padding: "0 10px",
        border: "2px solid #14130F",
        background: "#FFFDF6",
        font: "600 12px/1 'IBM Plex Sans KR', system-ui, sans-serif",
      }}
    >
      <svg width="12" height="12" viewBox="0 0 12 12">
        <circle cx="6" cy="6" r="4" fill="#D9502F" />
      </svg>
      RECORD
    </div>
  );
}

// ─── 확정 디자인이 정의하지 않은 상태 (DC-009) ────────────────────────────

/**
 * 진행 중 세션 안내 (UX U-05).
 *
 * 무엇이 살아 있고(상태·Step 수·저장 여부) 무엇을 할 수 있는지(이어서 보기·버리기)를
 * 말한다. 버리기는 되돌릴 수 없으므로 행 안에서 한 번 더 묻는다 — 삭제 확인과 같은 방식이다.
 */
function ActiveSessionsBanner({
  sessions,
  onResume,
  onDiscard,
}: {
  sessions: SessionView[];
  onResume?: (session: SessionView) => void;
  onDiscard?: (sessionId: string) => void;
}) {
  const [confirming, setConfirming] = useState<string | null>(null);

  return (
    <div
      role="status"
      data-active-sessions
      style={{
        border: "3px solid #14130F",
        background: "#FFF9D6",
        boxShadow: "5px 5px 0 #14130F",
        padding: "14px 18px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}
    >
      <strong style={{ font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif" }}>
        진행 중인 세션이 있습니다
      </strong>
      {sessions.map((s) => {
        const label =
          `${s.state_label} · Step ${s.steps.length}개` +
          (s.test_id ? ` · ${s.test_id}` : "") +
          (s.has_unsaved_changes ? " · 저장되지 않음" : "");
        const asking = confirming === s.session_id;
        return (
          <div
            key={s.session_id}
            data-session-id={s.session_id}
            style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}
          >
            <span style={{ flex: 1, font: "400 14px/1.4 'IBM Plex Sans KR', system-ui, sans-serif" }}>
              {label}
            </span>
            {asking ? (
              <>
                <span style={{ color: "#A83A22" }}>
                  Step {s.steps.length}개가 사라집니다. 정말 버릴까요?
                </span>
                <button className="danger" onClick={() => onDiscard?.(s.session_id)}>
                  버리기
                </button>
                <button className="ghost" onClick={() => setConfirming(null)}>
                  취소
                </button>
              </>
            ) : (
              <>
                {onResume && <button onClick={() => onResume(s)}>이어서 보기</button>}
                {onDiscard && (
                  <button className="secondary" onClick={() => setConfirming(s.session_id)}>
                    중지하고 버리기
                  </button>
                )}
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
