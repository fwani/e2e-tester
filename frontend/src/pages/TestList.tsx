/**
 * 테스트 목록 (T064). `TestList.dc.html` 이식.
 *
 * FR-002~FR-006: 상태 배지·ID·이름·Step 수·작성 배지·마지막 실행·검색·집계.
 * FR-005: 실패한 테스트는 실패 Step 번호와 메시지 요약을 인라인으로 보여준다.
 */
import { useEffect, useMemo, useState } from "react";

import { ApiError, tests, type TestListResponse } from "../api/client";
import { AuthoringBadge, OutcomeBadge } from "../components/Badges";

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
  onCreate: () => void;
  onOpenResult: (testId: string) => void;
  onRun: (testId: string) => void;
}

export function TestList({ onCreate, onOpenResult, onRun }: TestListProps) {
  const [data, setData] = useState<TestListResponse | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reload = async (q: string) => {
    try {
      setData(await tests.list(q.trim() || undefined));
      setError(null);
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : String(exc));
    }
  };

  useEffect(() => {
    void reload(query);
    // 검색어가 바뀔 때마다 다시 조회한다. 로컬 도구이므로 디바운스 없이도 충분하다.
  }, [query]);

  const counts = useMemo(
    () => data?.counts ?? { total: 0, pass: 0, fail: 0 },
    [data],
  );

  return (
    <main style={{ maxWidth: 1080, margin: "24px auto", padding: "0 16px" }}>
      <div className="row">
        <div>
          <div className="dim mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
            INTEGRATION TESTS
          </div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 24, margin: 0 }}>
            테스트
          </h1>
        </div>
        <span className="spacer" />
        <button onClick={onCreate}>+ 테스트 만들기</button>
      </div>

      <div className="row" style={{ marginTop: 16, gap: 16 }}>
        <input
          aria-label="테스트 검색"
          placeholder="테스트 이름 또는 ID 검색"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ maxWidth: 320 }}
        />
        <div className="row" style={{ gap: 12 }}>
          <span className="muted">
            전체 <strong>{counts.total}</strong>
          </span>
          <span style={{ color: "var(--pass)" }}>
            PASS <strong>{counts.pass}</strong>
          </span>
          <span style={{ color: "var(--fail)" }}>
            FAIL <strong>{counts.fail}</strong>
          </span>
        </div>
      </div>

      {error !== null && (
        <p style={{ color: "var(--fail-dark)", whiteSpace: "pre-wrap" }}>{error}</p>
      )}

      {data !== null && data.problems.length > 0 && (
        <div
          className="card"
          style={{ marginTop: 12, background: "var(--warn-tint)", borderColor: "var(--warn)" }}
        >
          <strong>읽을 수 없는 정의 파일 {data.problems.length}건</strong>
          {data.problems.map((p) => (
            <pre key={p} className="mono" style={{ whiteSpace: "pre-wrap", margin: "8px 0 0" }}>
              {p}
            </pre>
          ))}
        </div>
      )}

      <div className="card" style={{ marginTop: 16, padding: 0, overflow: "hidden" }}>
        <div
          className="row"
          style={{
            gap: 12,
            padding: "8px 14px",
            background: "var(--surface)",
            fontSize: 11,
            color: "var(--muted)",
            fontWeight: 600,
          }}
        >
          <span style={{ width: 70 }}>상태</span>
          <span style={{ width: 70 }}>ID</span>
          <span className="spacer">이름</span>
          <span style={{ width: 50 }}>STEP</span>
          <span style={{ width: 80 }}>작성</span>
          <span style={{ width: 90 }}>마지막 실행</span>
          <span style={{ width: 96 }} />
        </div>

        {data !== null && data.tests.length === 0 && (
          <div style={{ padding: 32, textAlign: "center", color: "var(--muted)" }}>
            {query.trim() === ""
              ? "아직 테스트가 없습니다. 「테스트 만들기」로 시작하세요."
              : `"${query}" 와 일치하는 테스트가 없습니다.`}
          </div>
        )}

        {data?.tests.map((row) => (
          <div
            key={row.id}
            className="row"
            style={{ gap: 12, padding: "12px 14px", borderTop: "1px solid var(--border)" }}
          >
            <span style={{ width: 70 }}>
              <OutcomeBadge outcome={row.outcome} />
            </span>
            <span className="mono" style={{ width: 70 }}>
              {row.id}
            </span>
            <span className="spacer">
              <div>{row.name}</div>
              {row.failure_summary !== null && (
                <div className="mono" style={{ fontSize: 12, color: "var(--fail-dark)" }}>
                  step {String(row.failure_summary.step_index).padStart(2, "0")} ·{" "}
                  {row.failure_summary.message}
                </div>
              )}
            </span>
            <span className="mono dim" style={{ width: 50 }}>
              {row.step_count}
            </span>
            <span style={{ width: 80 }}>
              <AuthoringBadge mode={row.authoring_mode} />
            </span>
            <span className="dim" style={{ width: 90 }}>
              {relativeTime(row.last_run_at)}
            </span>
            <span style={{ width: 96 }}>
              {row.outcome === "fail" ? (
                <button className="secondary" onClick={() => onOpenResult(row.id)}>
                  결과 보기
                </button>
              ) : (
                <button className="secondary" onClick={() => onRun(row.id)}>
                  ▶ 실행
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </main>
  );
}
