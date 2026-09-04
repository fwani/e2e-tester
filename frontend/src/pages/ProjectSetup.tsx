/**
 * 프로젝트 선택 화면. DR-001 ~ DR-009.
 *
 * **확정 디자인에 대응 화면이 없다** — 8종 artboard 어디에도 프로젝트 선택이 없다.
 * 따라서 1:1 대조 의무가 적용되지 않고(DC-010), 대신 8화면의 시각 언어를 따른다:
 * 직각 모서리, 3px 잉크 테두리, 하드 오프셋 그림자, `#EFEBE0` 배경.
 *
 * **경로를 타이핑하는 입력란이 없다** (DR-001·SC-102). 이전 판은 절대 경로를 손으로
 * 넣게 했는데, 서버가 어느 경로에서 실행 중인지 사용자는 알 방법이 없어 사실상 아무도
 * 올바른 값을 넣을 수 없었다. 그것이 이 라운드 최상위 결함이다 (research R4).
 *
 * 사용자가 위치를 지정하는 길은 "기존 프로젝트 열기" 하나뿐이고, 그때는 폴더 선택기로
 * 자기 파일을 찾는다 (DR-005).
 */
import { useCallback, useEffect, useState } from "react";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import {
  fs,
  project,
  type DirectoryEntry,
  type ProjectListItem,
  type ProjectView,
} from "../api/client";

type Mode =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "browse" }
  /** 만들어진 위치를 알린 뒤 들어간다 (DR-006) — 사용자가 위치를 정하지 않았으므로
   *  어디에 생겼는지 모른 채 넘어가면 다음에 그것을 찾을 수 없다. */
  | { kind: "created"; project: ProjectView };

const ink = "#14130F";
const paper = "#FFFDF6";
const surface = "#EFEBE0";
const muted = "#6B675C";
const dim = "#9A968A";
const accent = "#F5D000";
const fail = "#D9502F";

const display = "'Black Han Sans', 'Arial Black', Impact, sans-serif";
const mono = "'IBM Plex Mono', ui-monospace, monospace";

/** 확정 디자인의 섹션 라벨 — 작은 대문자 모노에 넓은 자간. */
function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        font: `600 12px/1 ${mono}`,
        letterSpacing: "0.14em",
        color: muted,
      }}
    >
      {children}
    </div>
  );
}

export function ProjectSetup({ onOpened }: { onOpened: (p: ProjectView) => void }) {
  const [mode, setMode] = useState<Mode>({ kind: "list" });
  const [projects, setProjects] = useState<ProjectListItem[] | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => {
    void project
      .list()
      .then((r) => {
        setProjects(r.projects);
        setWarning(r.warning);
      })
      .catch((exc: unknown) => {
        // 목록을 못 불러와도 새로 만들기는 되어야 한다 — 여기서 막히면 끝이다.
        setProjects([]);
        setError(describeError(exc));
      });
  }, []);

  useEffect(reload, [reload]);

  const run = async (action: () => Promise<ProjectView>) => {
    setBusy(true);
    setError(null);
    try {
      onOpened(await action());
    } catch (exc) {
      setError(describeError(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: surface, display: "flex", flexDirection: "column" }}>
      <header
        style={{
          flex: "0 0 60px",
          borderBottom: `3px solid ${ink}`,
          background: paper,
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "0 24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 34,
              height: 34,
              background: ink,
              color: accent,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20">
              <rect x="2.5" y="2.5" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.5" />
              <circle cx="10" cy="10" r="3.5" fill="currentColor" />
            </svg>
          </div>
          <div style={{ fontFamily: display, fontSize: 19, letterSpacing: "0.01em" }}>TEST BUILDER</div>
        </div>
      </header>

      <main style={{ flex: 1, padding: "30px 40px 40px", maxWidth: 960, width: "100%", margin: "0 auto" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 24 }}>
          <Eyebrow>PROJECT</Eyebrow>
          <div style={{ fontFamily: display, fontSize: 40, lineHeight: 1, letterSpacing: "-0.01em" }}>
            프로젝트
          </div>
        </div>

        {warning !== null && <Notice tone="warn">{warning}</Notice>}
        {error !== null && <ErrorNotice error={error} />}

        {mode.kind === "list" && (
          <ProjectList
            projects={projects}
            busy={busy}
            onOpen={(root) => void run(() => project.open(root))}
            onForget={(root) => {
              void project.forget(root).then(reload).catch(() => reload());
            }}
            onCreate={() => setMode({ kind: "create" })}
            onBrowse={() => setMode({ kind: "browse" })}
          />
        )}

        {mode.kind === "create" && (
          <CreateForm
            busy={busy}
            onCancel={() => setMode({ kind: "list" })}
            onSubmit={(body) => {
              setBusy(true);
              setError(null);
              void project
                .create(body)
                .then((p) => setMode({ kind: "created", project: p }))
                .catch((exc: unknown) =>
                  setError(describeError(exc)),
                )
                .finally(() => setBusy(false));
            }}
          />
        )}

        {mode.kind === "created" && (
          <CreatedNotice project={mode.project} onContinue={() => onOpened(mode.project)} />
        )}

        {mode.kind === "browse" && (
          <FolderPicker
            busy={busy}
            onCancel={() => setMode({ kind: "list" })}
            onPick={(path) => void run(() => project.open(path))}
          />
        )}
      </main>
    </div>
  );
}

// ─── 목록 (DR-002·DR-003·DR-004·DR-009) ─────────────────────────────────────

function ProjectList({
  projects,
  busy,
  onOpen,
  onForget,
  onCreate,
  onBrowse,
}: {
  projects: ProjectListItem[] | null;
  busy: boolean;
  onOpen: (root: string) => void;
  onForget: (root: string) => void;
  onCreate: () => void;
  onBrowse: () => void;
}) {
  if (projects === null) {
    // 확정 디자인이 로딩 상태를 정의하지 않는다 — undefined-states.md 에 기록했다.
    return <p style={{ color: dim }}>프로젝트를 찾는 중…</p>;
  }

  return (
    <>
      <div style={{ display: "flex", gap: 12, marginBottom: 22 }}>
        <button onClick={onCreate} disabled={busy}>
          + 새 프로젝트 만들기
        </button>
        <button className="secondary" onClick={onBrowse} disabled={busy}>
          기존 프로젝트 열기
        </button>
      </div>

      {projects.length === 0 ? (
        <div
          style={{
            border: `3px solid ${ink}`,
            background: paper,
            padding: 28,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 16 }}>아직 프로젝트가 없습니다</div>
          <div style={{ color: muted }}>
            새 프로젝트를 만들면 이 도구가 관리하는 위치에 저장되고, 다음에 열 때 여기 목록에
            바로 나타납니다. 다른 곳에 있는 프로젝트는 「기존 프로젝트 열기」로 찾아 여세요.
          </div>
        </div>
      ) : (
        <div style={{ border: `3px solid ${ink}`, background: paper }}>
          {projects.map((p, i) => (
            <ProjectRow
              key={p.root}
              item={p}
              first={i === 0}
              busy={busy}
              onOpen={() => onOpen(p.root)}
              onForget={() => onForget(p.root)}
            />
          ))}
        </div>
      )}
    </>
  );
}

function ProjectRow({
  item,
  first,
  busy,
  onOpen,
  onForget,
}: {
  item: ProjectListItem;
  first: boolean;
  busy: boolean;
  onOpen: () => void;
  onForget: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "16px 18px",
        borderTop: first ? "none" : `2px solid ${ink}`,
        opacity: item.accessible ? 1 : 0.72,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontWeight: 600, fontSize: 16 }}>{item.name}</span>
          {item.origin === "external" && <span className="badge">외부 위치</span>}
          {!item.accessible && (
            <span className="badge fail">열 수 없음</span>
          )}
        </div>
        <div
          style={{
            font: `400 12px/1.5 ${mono}`,
            color: dim,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={item.root}
        >
          {item.root}
        </div>
        {!item.accessible && item.unavailable_reason !== null && (
          <div style={{ color: fail, fontSize: 13, marginTop: 4 }}>{item.unavailable_reason}</div>
        )}
      </div>

      {item.accessible ? (
        <button className="secondary" onClick={onOpen} disabled={busy}>
          열기
        </button>
      ) : (
        <button
          className="ghost"
          onClick={onForget}
          disabled={busy}
          // 목록 정리와 자산 삭제는 다른 조작이다 (DR-009). 오해할 여지를 없앤다.
          title="목록에서만 치웁니다. 디스크의 파일은 지우지 않습니다."
        >
          목록에서 치우기
        </button>
      )}
    </div>
  );
}

// ─── 새로 만들기 (DR-001·DR-006) ────────────────────────────────────────────

function CreateForm({
  busy,
  onCancel,
  onSubmit,
}: {
  busy: boolean;
  onCancel: () => void;
  onSubmit: (body: { name: string; default_start_url: string; test_id_attribute: string }) => void;
}) {
  const [name, setName] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [testIdAttr, setTestIdAttr] = useState("data-testid");

  const urlLooksValid = /^https?:\/\//.test(startUrl.trim());
  const ready = name.trim() !== "" && urlLooksValid;
  /** 무엇이 빠져 있는가. 「만들기」가 눌리지 않는 이유를 그대로 화면에 쓴다 (003 AP-003). */
  const missing = [
    ...(name.trim() === "" ? ["프로젝트 이름"] : []),
    ...(urlLooksValid ? [] : ["http:// 또는 https:// 로 시작하는 기본 시작 URL"]),
  ];

  return (
    <div style={{ border: `3px solid ${ink}`, background: paper, padding: 24, boxShadow: `5px 5px 0 ${ink}` }}>
      <Eyebrow>NEW PROJECT</Eyebrow>

      <p style={{ color: muted, marginTop: 10 }}>
        저장 위치는 도구가 정합니다. 만들고 나면 어디에 만들어졌는지 알려 드립니다. 테스트
        정의는 그 안의 <code>tests/</code> 에 평문 YAML 로 저장되어 그대로 버전 관리에 넣을 수
        있습니다.
      </p>

      <label htmlFor="name">프로젝트 이름</label>
      <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />

      <label htmlFor="url">기본 시작 URL</label>
      <input
        id="url"
        value={startUrl}
        onChange={(e) => setStartUrl(e.target.value)}
        placeholder="https://example.internal/login"
      />
      {startUrl.trim() !== "" && !urlLooksValid && (
        <p style={{ color: fail, fontSize: 13, marginTop: 6 }}>
          http:// 또는 https:// 로 시작해야 합니다.
        </p>
      )}

      <label htmlFor="attr">testId 속성명</label>
      <input id="attr" value={testIdAttr} onChange={(e) => setTestIdAttr(e.target.value)} />
      <p style={{ color: dim, fontSize: 12, marginTop: 6 }}>
        대상 앱이 쓰는 속성명입니다. <code>data-test</code>, <code>data-cy</code> 를 쓰는 앱도
        흔합니다. 요소를 찾는 최우선 기준이 됩니다.
      </p>

      {/*
        003 AP-003 — **왜 지금 안 되는지 말한다.** 이 안내가 없어서 「만들기」가 눌리지
        않는 이유가 화면에 없었고, 사용자는 무엇이 빠졌는지 눌러 봐도 알 수 없었다.
        키 관리 화면이 암호구 규칙을 제출 전에 알리는 것과 같은 방식이다 (DR-029).
      */}
      <p
        id="create-blockers"
        style={{ margin: "16px 0 0", fontSize: 12.5, color: ready ? muted : fail }}
      >
        {ready
          ? "만들 준비가 되었습니다."
          : `아직 만들 수 없습니다 — ${missing.join(", ")}을 채우세요.`}
      </p>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 20 }}>
        <button className="secondary" onClick={onCancel} disabled={busy}>
          취소
        </button>
        <button
          aria-describedby="create-blockers"
          disabled={busy || !ready}
          onClick={() =>
            onSubmit({
              name: name.trim(),
              default_start_url: startUrl.trim(),
              test_id_attribute: testIdAttr.trim() || "data-testid",
            })
          }
        >
          만들기 →
        </button>
      </div>
    </div>
  );
}

// ─── 만들어진 위치 알림 (DR-006) ────────────────────────────────────────────

function CreatedNotice({
  project: p,
  onContinue,
}: {
  project: ProjectView;
  onContinue: () => void;
}) {
  return (
    <div style={{ border: `3px solid ${ink}`, background: paper, padding: 24, boxShadow: `5px 5px 0 ${accent}` }}>
      <Eyebrow>PROJECT CREATED</Eyebrow>

      <div style={{ fontFamily: display, fontSize: 28, marginTop: 10 }}>{p.name}</div>

      <p style={{ color: muted, marginTop: 12 }}>
        아래 위치에 만들었습니다. 다음에 도구를 열면 이 프로젝트가 목록에 바로 나타납니다.
      </p>

      <div
        style={{
          font: `400 13px/1.6 ${mono}`,
          border: `2px solid ${ink}`,
          background: surface,
          padding: "10px 12px",
          marginTop: 10,
          wordBreak: "break-all",
        }}
      >
        {p.root}
      </div>

      <p style={{ color: dim, fontSize: 12, marginTop: 10 }}>
        테스트 정의는 이 폴더의 <code>tests/</code> 에 평문 YAML 로 저장됩니다. 비밀 값과 실행
        산출물은 <code>.gitignore</code> 로 제외됩니다.
      </p>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
        <button onClick={onContinue}>시작하기 →</button>
      </div>
    </div>
  );
}

// ─── 폴더 선택기 (DR-005) ───────────────────────────────────────────────────
//
// 브라우저는 임의 절대 경로를 줄 수 없다. 서버가 홈 하위 디렉터리를 그려 준다.
// 목록에는 디렉터리만 온다 — 파일 이름은 서버가 보내지 않는다.

function FolderPicker({
  busy,
  onCancel,
  onPick,
}: {
  busy: boolean;
  onCancel: () => void;
  onPick: (path: string) => void;
}) {
  const [here, setHere] = useState<string | null>(null);
  const [parent, setParent] = useState<string | null>(null);
  const [entries, setEntries] = useState<DirectoryEntry[] | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);

  const go = useCallback((path?: string) => {
    setError(null);
    void fs
      .browse(path)
      .then((r) => {
        setHere(r.path);
        setParent(r.parent);
        setEntries(r.entries);
      })
      .catch((exc: unknown) => setError(describeError(exc)));
  }, []);

  useEffect(() => go(), [go]);

  return (
    <div style={{ border: `3px solid ${ink}`, background: paper, boxShadow: `5px 5px 0 ${ink}` }}>
      <div style={{ padding: "18px 20px", borderBottom: `3px solid ${ink}` }}>
        <Eyebrow>OPEN EXISTING</Eyebrow>
        <div style={{ font: `400 13px/1.6 ${mono}`, color: muted, marginTop: 8, wordBreak: "break-all" }}>
          {here ?? "…"}
        </div>
      </div>

      {error !== null && <ErrorNotice error={error} />}

      <div style={{ maxHeight: 360, overflowY: "auto" }}>
        {parent !== null && (
          <button
            className="ghost"
            onClick={() => go(parent)}
            style={{ width: "100%", height: 44, justifyContent: "flex-start", textAlign: "left", padding: "0 20px" }}
          >
            ↑ 상위 폴더
          </button>
        )}

        {entries === null && <p style={{ padding: "16px 20px", color: dim }}>불러오는 중…</p>}

        {entries !== null && entries.length === 0 && (
          <p style={{ padding: "16px 20px", color: dim }}>이 폴더에는 하위 폴더가 없습니다.</p>
        )}

        {entries?.map((e) => (
          <div
            key={e.path}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 20px",
              borderTop: `2px solid ${ink}`,
            }}
          >
            <button
              className="ghost"
              onClick={() => go(e.path)}
              style={{ flex: 1, justifyContent: "flex-start", textAlign: "left", padding: 0, height: 32 }}
            >
              📁 {e.name}
            </button>
            {e.is_project && <span className="badge">프로젝트</span>}
            {e.is_project && (
              <button className="secondary" disabled={busy} onClick={() => onPick(e.path)}>
                열기
              </button>
            )}
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          padding: "16px 20px",
          borderTop: `3px solid ${ink}`,
        }}
      >
        <span style={{ color: dim, fontSize: 12 }}>
          「프로젝트」 표시가 붙은 폴더만 열 수 있습니다.
        </span>
        <div style={{ display: "flex", gap: 12 }}>
          <button className="secondary" onClick={onCancel} disabled={busy}>
            취소
          </button>
          {here !== null && (
            <button disabled={busy} onClick={() => onPick(here)}>
              이 폴더 열기
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── 알림 ───────────────────────────────────────────────────────────────────

function Notice({ tone, children }: { tone: "warn" | "fail"; children: React.ReactNode }) {
  return (
    <div
      style={{
        border: `3px solid ${ink}`,
        background: tone === "fail" ? "#FBEEEA" : "#FFF9D6",
        color: tone === "fail" ? "#A83A22" : ink,
        padding: "12px 16px",
        marginBottom: 18,
        whiteSpace: "pre-wrap",
      }}
      role={tone === "fail" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
