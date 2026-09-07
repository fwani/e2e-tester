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
import { isRunning } from "../lib/sessionState";
import {
  EDIT_ENTRY_LABEL,
  outcomeChip,
  outcomeLabel,
  outcomeTone,
  stepLabel,
} from "../lib/wording";
import type { Outcome } from "../types/generated/run-result";


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
  /**
   * 실행 요청이 진행 중인 테스트 ID (005 FR-127·FR-129).
   *
   * 그 행의 「실행」이 비활성이 되고 「준비 중…」으로 바뀐다. 브라우저를 띄우는 약 1초
   * 동안 화면이 침묵해 사용자가 다시 눌렀고, 그것이 세션 중복이 됐다 (U-11 → U-06).
   */
  pendingRunId?: string | null;
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
  /**
   * 세션 상태를 다시 읽는다 (005 FR-169 · U-17).
   *
   * 배너가 스스로 갱신되지 않아 끝난 실행이 계속 "실행 중" 으로 남았다. 주기 갱신은
   * 부모가 걸고, 이 버튼은 그것이 실패하는 환경의 탈출구다.
   */
  onRefreshSessions?: () => void;
}

export function TestList({
  projectName = "프로젝트",
  onCreate,
  onOpenResult,
  onRun,
  pendingRunId = null,
  onOpenDefinition,
  onOpenSecrets,
  onOpenKeys,
  activeSessions = [],
  onRefreshSessions,
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
            onRefresh={onRefreshSessions}
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
              runPending={pendingRunId === row.id}
              /*
                005 FR-168 (U-16) — 지금 돌고 있다는 사실이 **행에도** 보인다.

                실행 중 새로고침하면 목록으로 떨어지는데, 상단 배너는 "실행 중" 을
                알려도 그 행의 상태 칩은 **이전 실행의 FAIL** 이었고 버튼도 이전
                결과를 가리켰다. 회수 장치는 있었지만 행이 거짓을 말했다.
              */
              liveSession={activeSessions.find((s) => s.test_id === row.id) ?? null}
              onOpenSession={onResumeSession}
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
  runPending = false,
  liveSession = null,
  onOpenSession,
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
  /** 이 테스트의 실행 요청이 진행 중인가 (005 FR-127·FR-129). */
  runPending?: boolean;
  /** 이 테스트로 지금 돌고 있는 세션 (005 FR-168). 없으면 `null`. */
  liveSession?: SessionView | null;
  onOpenSession?: (session: SessionView) => void;
}) {
  const failed = row.outcome === "fail";
  /** 열어 볼 결과가 있는가 (005 FR-130). 결말 종류와 무관하다 — U-13 이 이것이었다. */
  const hasResult = row.outcome != null || row.last_run_at != null;

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
        {/*
          005 FR-169 (재점검 N-02) — 칩은 세션의 **상태**를 본다.

          이전에는 세션의 **존재**를 봤다(`liveSession !== null`). 실행이 끝나도 세션은
          `failed`·`review` 로 등록에 남으므로 행은 영원히 `RUNNING` 이었고, 같은 화면의
          배너는 「실패」로 갱신됐다 — 배너와 행이 다른 말을 했다.
        */}
        <OutcomeChip
          outcome={row.outcome}
          running={liveSession !== null && isRunning(liveSession.state)}
        />
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
        {liveSession !== null && isRunning(liveSession.state)
          ? "실행 중"
          : relativeTime(row.last_run_at)}
      </div>

      {/*
        005 FR-130 — 「실행」은 **항상** 두고, 결과가 있으면 「결과 보기」도 함께 둔다.
        (U-12·U-13)

        이전에는 한 자리에 둘 중 하나만 뒀다. 실패한 테스트는 「결과 보기」로 바뀌어
        목록에서 다시 실행할 수 없었고(U-12), 통과한 테스트는 「실행」뿐이라 그 실행의
        결과에 도달할 길이 아예 없었다(U-13) — 결과 화면이 실패 전용 화면이 되어 있었다.
      */}
      <div style={{ width: "196px", display: "flex", justifyContent: "flex-end", gap: "8px", position: "relative" }}>
        {/* 005 FR-168 — 실행 중이면 그 사실과 복귀 수단이 먼저 온다. */}
        {liveSession !== null && (
          <button
            onClick={() => onOpenSession?.(liveSession)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              height: "44px",
              padding: "0 12px",
              border: "3px solid #14130F",
              background: "#F5D000",
              color: "#14130F",
              boxShadow: "4px 4px 0 #14130F",
              font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            실행 화면 보기
          </button>
        )}
        {/*
          005 FR-130·FR-169 — **돌고 있는 동안만** 결과를 감춘다.

          이전 조건은 세션이 열려 있으면 결과 버튼을 지웠다. 중지한 뒤 목록으로 나오면
          세션은 `review` 로 남으므로, 방금 남은 결과에 목록에서 도달할 길이 없었다 —
          U-13(결과에 도달할 길이 없다)이 다른 자리에서 되살아난 형태다.
        */}
        {hasResult && (liveSession === null || !isRunning(liveSession.state)) && (
          <button
            onClick={onOpenResult}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              height: "44px",
              padding: "0 12px",
              border: "3px solid #14130F",
              background: failed ? "#F5D000" : "#FFFDF6",
              color: "#14130F",
              boxShadow: "4px 4px 0 #14130F",
              font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            결과 보기
          </button>
        )}
        <button
          onClick={onRun}
          disabled={runPending}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "7px",
            height: "44px",
            padding: "0 12px",
            border: "3px solid #14130F",
            background: runPending ? "#EDEAE0" : "#FFFDF6",
            color: "#14130F",
            boxShadow: runPending ? "none" : "4px 4px 0 #14130F",
            font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            cursor: runPending ? "progress" : "pointer",
          }}
        >
          {!runPending && (
            <svg width="13" height="13" viewBox="0 0 16 16">
              <path d="M4 2l10 6-10 6z" fill="currentColor" />
            </svg>
          )}
          {/* 005 FR-129 — 클릭 직후 0.3초 안에 화면이 변한다. 이전에는 0.8~1.2초간
              완전히 그대로여서 사용자가 다시 눌렀다 (U-11 → U-06). */}
          {runPending ? "준비 중…" : "실행"}
        </button>

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
            {/*
              006 FR-175 — 「정의 보기」를 **「편집」으로 대체한다.** 보기만 하는 별도
              항목을 남기면 사용자는 다시 "고치려면 어디로 가지" 를 묻게 되고, 그것이
              006 이 없앤 E-01·E-03 이다. 편집 화면은 저장하지 않으면 아무것도 바꾸지
              않으므로 보기 위해 들어가도 안전하다.
            */}
            {onOpenDefinition && (
              <button className="ghost" onClick={onOpenDefinition} style={{ justifyContent: "flex-start" }}>
                {EDIT_ENTRY_LABEL}
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

const CHIP_COLOR: Record<string, string> = {
  success: "#2E9455",
  danger: "#D9502F",
  neutral: "#6B675C",
  warn: "#B8860B",
  unknown: "#9A968A",
};

/**
 * 목록 행의 결말 칩 (005 FR-141).
 *
 * **네 결말을 전부 다룬다.** `outcome === "pass" ? 초록 : 붉은` 이분법은 사용자가 누른
 * 중지를 실패 색으로, 부분 성공도 실패 색으로 칠했다.
 *
 * 실행 중인 테스트에는 `RUNNING` 을 보여준다 (FR-168) — 이전 실행의 결말을 그대로
 * 두면 지금 돌고 있다는 사실이 행에서 사라진다 (U-16).
 */
function OutcomeChip({
  outcome,
  running = false,
}: {
  outcome: Outcome | null;
  running?: boolean;
}) {
  if (running) {
    return (
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          height: "28px",
          padding: "0 10px",
          background: "#F5D000",
          color: "#14130F",
          border: "2px solid #14130F",
          font: "700 12px/1 'IBM Plex Mono', ui-monospace, monospace",
          letterSpacing: "0.06em",
        }}
      >
        RUNNING
      </div>
    );
  }
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
        background: CHIP_COLOR[outcomeTone(outcome)],
        color: "#FFFDF6",
        border: "2px solid #14130F",
        font: "700 12px/1 'IBM Plex Mono', ui-monospace, monospace",
        letterSpacing: "0.06em",
      }}
      // 색만으로 구분하지 않는다 — 스크린리더에는 한국어 문장을 준다.
      title={outcomeLabel(outcome)}
    >
      {outcomeChip(outcome)}
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
  onRefresh,
}: {
  sessions: SessionView[];
  onResume?: (session: SessionView) => void;
  onDiscard?: (sessionId: string) => void;
  /** 세션 상태를 다시 읽는다 (005 FR-169 · U-17). */
  onRefresh?: () => void;
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
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <strong style={{ font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif" }}>
          진행 중인 세션이 있습니다
        </strong>
        <div style={{ flex: 1 }} />
        {/*
          005 FR-169 (U-17) — 배너가 실제 상태를 따라간다.

          리포트는 실행이 끝난 뒤 25초를 더 기다려도 배너가 "실행 중" 으로 남아 있는
          것을 봤다. 새로고침해야 바뀌었다. 짧은 주기로 다시 읽는 것과 손으로 새로
          고치는 수단을 함께 둔다 — 주기 갱신이 실패하는 환경에서도 사용자가 막히지
          않아야 한다.
        */}
        {onRefresh && (
          <button className="ghost" onClick={onRefresh} aria-label="세션 상태 새로 고침">
            새로 고침
          </button>
        )}
      </div>
      {sessions.map((s) => {
        /**
         * 005 FR-159 (U-10) — **저장된 세션은 "사라진다" 고 말하지 않는다.**
         *
         * 리포트는 저장에 성공해 TC-001 이 목록에 있는데도 정리 버튼이 "Step 6개가
         * 사라집니다. 정말 버릴까요?" 를 띄우는 것을 봤다. 저장 확인 표시가 없는
         * 상태(U-09)에서 그 문장을 만나면 "저장이 안 된 건가?" 하고 손을 멈춘다.
         */
        const saved = s.saved_at != null;
        /*
          005 FR-170 (U-06) — 같은 테스트의 세션이 여럿일 때 **구분할 정보**를 준다.

          연타로 세션이 둘 만들어졌을 때 목록에 구분 불가능한 배너가 두 줄로 떴다.
          어느 것이 어느 실행인지 알 수 없어 사용자는 아무거나 골라야 했다.

          세션 짧은 ID 를 쓴다 — 시작 시각은 세션 뷰에 없고, 짧은 ID 로도 두 줄을
          가릴 수 있다. 사용자에게 보이는 오류 문구에 식별자를 넣지 않는 규칙
          (FR-135)은 **오류 문구**에 대한 것이며, 여기는 사용자가 골라야 하는
          목록이므로 구분자가 필요하다.
        */
        const shortId = s.session_id.slice(0, 6);
        const duplicated = sessions.filter((o) => o.test_id === s.test_id).length > 1;
        const label =
          `${s.state_label} · Step ${s.steps.length}개` +
          (s.test_id ? ` · ${s.test_id}` : "") +
          (duplicated ? ` · #${shortId}` : "") +
          (s.has_unsaved_changes ? " · 저장되지 않음" : saved ? " · 저장됨" : "");
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
                <span style={{ color: saved ? "#6B675C" : "#A83A22" }}>
                  {saved
                    ? `${s.test_id ?? "테스트"} 로 저장돼 있습니다. 이 작업 창만 닫습니다.`
                    : `Step ${s.steps.length}개가 사라집니다. 정말 버릴까요?`}
                </span>
                <button
                  className={saved ? "secondary" : "danger"}
                  onClick={() => onDiscard?.(s.session_id)}
                >
                  {saved ? "닫기" : "버리기"}
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
                    {/* 저장된 세션에는 파괴적으로 읽히는 이름을 쓰지 않는다 (FR-159). */}
                    {saved ? "닫기" : "중지하고 버리기"}
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
