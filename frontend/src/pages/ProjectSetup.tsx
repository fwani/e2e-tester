/**
 * 프로젝트 선택 화면. DR-001 ~ DR-009.
 *
 * **확정 디자인에 대응 화면이 없다** — 8종 artboard 어디에도 프로젝트 선택이 없다.
 * 따라서 1:1 대조 의무가 적용되지 않고(DC-010), 대신 8화면의 시각 언어를 따른다:
 * 직각 모서리, 3px 잉크 테두리, 하드 오프셋 그림자, `#F2F4F7` 배경.
 *
 * **경로를 타이핑하는 입력란이 없다** (DR-001·SC-102). 이전 판은 절대 경로를 손으로
 * 넣게 했는데, 서버가 어느 경로에서 실행 중인지 사용자는 알 방법이 없어 사실상 아무도
 * 올바른 값을 넣을 수 없었다. 그것이 이 라운드 최상위 결함이다 (research R4).
 *
 * 사용자가 위치를 지정하는 길은 "기존 프로젝트 열기" 하나뿐이고, 그때는 폴더 선택기로
 * 자기 파일을 찾는다 (DR-005).
 */
import { useCallback, useEffect, useState } from "react";
import { BrandMark, HeaderBar } from "../components/design/Chrome";
import { ErrorNotice, describeError } from "../components/ErrorNotice";
import { ImportFilePicker, ImportPreview } from "./ImportPreview";
import type { ErrorInfo } from "../components/ErrorNotice";

import {
  fs,
  imports,
  project,
  type DirectoryEntry,
  type CreateProjectImportResult,
  type ImportPlanView,
  type ProjectListItem,
  type ProjectSummary,
  type ProjectView,
  type TrashProjectResponse,
} from "../api/client";

type Mode =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "browse" }
  /** 만들어진 위치를 알린 뒤 들어간다 (DR-006) — 사용자가 위치를 정하지 않았으므로
   *  어디에 생겼는지 모른 채 넘어가면 다음에 그것을 찾을 수 없다. */
  | { kind: "created"; project: ProjectView }
  /**
   * 엑셀에서 새 프로젝트를 만들며 가져온다 (014 FR-014a·b).
   *
   * 파일에는 프로젝트 이름·시작 URL·저장 위치가 없으므로 그것을 받아야 한다 (FR-014b).
   * **만들기 양식을 새로 만들지 않고 `CreateForm` 을 그대로 쓴다** — 받는 것이 같으므로
   * 두 벌로 두면 한쪽만 고쳐지는 날이 온다.
   */
  | { kind: "import"; plan: ImportPlanView }
  /**
   * 이름·시작 URL 을 받은 뒤 미리보기로 간다 (014 FR-014a·FR-015).
   *
   * **미리보기를 건너뛰지 않는다.** 예전에는 요약 배너만 보여 주고 바로 만들었고,
   * 그래서 접두어를 물어야 하는 시트와 열을 짝지어야 하는 시트가 **묻지도 않고 조용히
   * 건너뛰어졌다** (수렴 T089).
   */
  | {
      kind: "import-preview";
      plan: ImportPlanView;
      form: { name: string; default_start_url: string; test_id_attribute: string };
    };

/** 구획 라벨 — 정본의 `.lbl` 이다. 이름만 확정 디자인의 관용어를 쓴다. */
function Eyebrow({ children }: { children: React.ReactNode }) {
  return <div className="lbl">{children}</div>;
}

export function ProjectSetup({
  onOpened,
  onCancel,
  onProjectClosed,
  onProjectRenamed,
}: {
  onOpened: (p: ProjectView) => void;
  /**
   * 열려 있던 프로젝트로 되돌아간다. **첫 화면일 때는 없다** (사용자 보고 · 2026-09-09).
   *
   * 이 화면은 제품의 첫 화면이었고, 그때는 돌아갈 곳이 없으므로 되돌아가는 길도 없었다.
   * 목록에서 이리로 오는 길이 생기면서 **중간 화면**이기도 하게 됐다 — 그 경로로 들어온
   * 사용자는 마음을 바꿀 수 있어야 한다. 없으면 프로젝트를 하나 열어야만 빠져나간다.
   *
   * 있을 때만 그린다. 첫 화면의 모습은 그대로다.
   */
  onCancel?: () => void;
  /**
   * 열려 있던 프로젝트가 삭제로 닫혔다 (012 FR-416).
   *
   * 화면이 스스로 처리할 수 없다 — 열린 프로젝트는 `App` 이 들고 있고, 그것을 비우지
   * 않으면 사용자는 사라진 프로젝트를 가리키는 「돌아가기」를 계속 본다.
   */
  onProjectClosed?: () => void;
  /**
   * 열려 있는 프로젝트의 이름이 바뀌었다 (012 FR-405 · converge T049).
   *
   * **서버는 이미 맞다** — `GET /api/project` 는 파일을 다시 읽는다. 낡은 것은 `App` 이
   * 들고 있는 `ProjectView` 사본이고, 그 값이 목록 화면의 프로젝트 표시로 간다. 올리지
   * 않으면 사용자는 고친 이름이 되돌아간 것을 본다.
   */
  onProjectRenamed?: (root: string, name: string) => void;
}) {
  const [mode, setMode] = useState<Mode>({ kind: "list" });
  /**
   * 방금 옮긴 결과 (012 FR-410·FR-425 · UC-012-04).
   *
   * **자동으로 사라지지 않는다.** 사라지면 되돌리는 방법이 함께 사라진다.
   */
  const [trashed, setTrashed] = useState<TrashProjectResponse | null>(null);
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
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* 제품의 **첫 화면**이다. 껍데기는 다른 화면과 같아야 한다 (FR-217). */}
      <HeaderBar>
        <BrandMark />
        <div className="spacer" />
        {onCancel !== undefined && (
          <button className="navlink" onClick={onCancel}>
            돌아가기
          </button>
        )}
      </HeaderBar>

      <main style={{ flex: 1, padding: "24px 32px 32px", maxWidth: 960, width: "100%", margin: "0 auto" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
          <Eyebrow>PROJECT</Eyebrow>
          <div className="title">프로젝트</div>
        </div>

        {warning !== null && <Notice tone="warn">{warning}</Notice>}
        {error !== null && <ErrorNotice error={error} />}

        {mode.kind === "list" && trashed !== null && (
          <TrashedNotice result={trashed} onDismiss={() => setTrashed(null)} />
        )}

        {mode.kind === "list" && (
          <ProjectList
            projects={projects}
            busy={busy}
            onOpen={(root) => void run(() => project.open(root))}
            onForget={(root) => {
              void project.forget(root).then(reload).catch(() => reload());
            }}
            onRenamed={(updated) => {
              onProjectRenamed?.(updated.root, updated.name);
              // 그 줄만 갈아 끼운다. 목록 전체를 다시 부르면 편집 중이던 다른 줄의
              // 상태가 날아간다 (UC-012-02).
              setProjects((rows) =>
                rows === null
                  ? rows
                  : rows.map((r) => (r.root === updated.root ? updated : r)),
              );
            }}
            onTrashed={(result) => {
              setTrashed(result);
              if (result.was_open) onProjectClosed?.();
              reload();
            }}
            onStaleList={reload}
            onCreate={() => setMode({ kind: "create" })}
            onBrowse={() => setMode({ kind: "browse" })}
            /* 014 — 파일을 읽었을 뿐이다. 프로젝트는 양식을 채운 뒤에 만들어진다 */
            onImportPlan={(plan) => setMode({ kind: "import", plan })}
            onError={setError}
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

        {/*
          엑셀에서 새 프로젝트 (014 FR-014a·b·c).

          만들기 양식을 그대로 쓴다 — 받는 것(이름·시작 URL·testId 속성)이 같다. 다른
          것은 파일 이름을 이름의 기본값으로 제안하는 것과, 무엇이 함께 만들어지는지
          알리는 것뿐이다.
        */}
        {mode.kind === "import" && (
          <CreateForm
            busy={busy}
            defaultName={mode.plan.file_name.replace(/\.[^.]+$/, "")}
            importNote={
              <div
                className="tint-run"
                data-import-note
                style={{ padding: "10px 12px", marginTop: 10 }}
              >
                <div className="strong-sm">
                  {mode.plan.file_name} 에서 그룹 {mode.plan.group_count}개, 테스트 초안{" "}
                  {mode.plan.draft_count}건을 함께 만듭니다.
                </div>
                <div className="why" style={{ marginTop: 4 }}>
                  초안은 아직 테스트가 아닙니다. 만든 뒤 하나씩 녹화하면 테스트가 됩니다.
                </div>
              </div>
            }
            onCancel={() => setMode({ kind: "list" })}
            /*
              양식을 받은 뒤 **미리보기로 간다.** 프로젝트는 미리보기에서 확정할 때
              만들어진다 — 여기서 만들어 두면 사용자가 미리보기에서 취소했을 때
              빈 프로젝트가 남는다.
            */
            onSubmit={(body) =>
              setMode({ kind: "import-preview", plan: mode.plan, form: body })
            }
          />
        )}

        {mode.kind === "import-preview" && (
          <ImportPreview
            plan={mode.plan}
            confirmLabel="프로젝트 만들고 가져오기"
            onCancel={() => setMode({ kind: "import", plan: mode.plan })}
            commit={(decisions) =>
              imports.createProject({
                plan_id: mode.plan.plan_id,
                ...mode.form,
                ...decisions,
              })
            }
            onDone={(result) => {
              const made = result as CreateProjectImportResult;
              setMode({ kind: "created", project: made.project });
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
  onRenamed,
  onTrashed,
  onStaleList,
  onCreate,
  onBrowse,
  onImportPlan,
  onError,
}: {
  projects: ProjectListItem[] | null;
  busy: boolean;
  onOpen: (root: string) => void;
  onForget: (root: string) => void;
  onRenamed: (updated: ProjectListItem) => void;
  onTrashed: (result: TrashProjectResponse) => void;
  /** 목록이 낡았다 — 서버가 모르는 프로젝트라고 답했다 (UC-012-06). */
  onStaleList: () => void;
  onCreate: () => void;
  onBrowse: () => void;
  /**
   * 엑셀 파일에서 새 프로젝트를 만든다 (014 FR-014a).
   *
   * **이 자리에 있어야 한다.** 프로젝트가 아직 없는 사용자가 이미 쓰던 설계서를 들고
   * 오는 경우이고, 열린 프로젝트 안의 진입점만 두면 먼저 빈 프로젝트를 만들어야 한다.
   */
  onImportPlan: (plan: ImportPlanView) => void;
  onError: (error: ErrorInfo) => void;
}) {
  if (projects === null) {
    // 확정 디자인이 로딩 상태를 정의하지 않는다 — undefined-states.md 에 기록했다.
    return <p className="why">프로젝트를 찾는 중…</p>;
  }

  return (
    <>
      <div style={{ display: "flex", gap: 12, marginBottom: 22 }}>
        <button className="btn primary" onClick={onCreate} disabled={busy}>
          + 새 프로젝트 만들기
        </button>
        <button className="btn" onClick={onBrowse} disabled={busy}>
          기존 프로젝트 열기
        </button>
        {/* 세 번째 길 — 이미 쓰던 설계서에서 시작한다 (014 US2). */}
        <ImportFilePicker
          label="엑셀에서 새 프로젝트"
          disabled={busy}
          onPlan={onImportPlan}
          onError={onError}
        />
      </div>

      {projects.length === 0 ? (
        <div
          className="pane"
          style={{ padding: 28, display: "flex", flexDirection: "column", gap: 8 }}
        >
          <div className="subtitle">아직 프로젝트가 없습니다</div>
          <div className="note">
            새 프로젝트를 만들면 이 도구가 관리하는 위치에 저장되고, 다음에 열 때 여기 목록에
            바로 나타납니다. 다른 곳에 있는 프로젝트는 「기존 프로젝트 열기」로 찾아 여세요.
          </div>
        </div>
      ) : (
        <div className="pane">
          {projects.map((p, i) => (
            <ProjectRow
              key={p.root}
              item={p}
              first={i === 0}
              busy={busy}
              onOpen={() => onOpen(p.root)}
              onForget={() => onForget(p.root)}
              onRenamed={onRenamed}
              onTrashed={onTrashed}
              onStaleList={onStaleList}
            />
          ))}
        </div>
      )}
    </>
  );
}

/**
 * 줄이 어떤 상태에 있는가 (012 UC-012-02·UC-012-03).
 *
 * 이름 편집과 삭제 확인이 **같은 자리를 쓴다.** 둘 다 그 줄 안에서 일어나므로 동시에
 * 열릴 수 없고, 하나의 상태로 다루는 것이 두 개의 불리언을 두는 것보다 정확하다 —
 * 두 불리언은 「둘 다 참」이라는 있을 수 없는 상태를 표현할 수 있다.
 */
type RowMode =
  | { kind: "idle" }
  | { kind: "editing"; draft: string }
  | { kind: "confirming"; summary: ProjectSummary | null };

/**
 * 줄 하나. **조작 집합은 줄의 상태가 정한다** (012 UC-012-01 · data-model §3).
 *
 * | `accessible` | 열기 | 이름 변경 | 삭제 | 목록에서 치우기 |
 * |---|---|---|---|---|
 * | `true`  | O | O | O | O |
 * | `false` | X | X | **O** | O |
 *
 * **삭제는 어느 줄에서나 있다** (FR-418 · SC-622 · 사용자 지적 2026-09-10). 최초 판은
 * 「옮길 대상이 없다」는 이유로 접근 불가 줄에서 삭제를 뺐는데, 그것이 **없앨 방법이 없는
 * 줄**을 만들었다 — 목록이 스캔 ∪ 레지스트리이므로 파일은 있는데 읽지 못하는 프로젝트는
 * 「목록에서 치우기」로 빼도 스캔에 다시 걸려 돌아온다.
 *
 * 서버는 처음부터 이 요청을 받을 수 있었다: 옮길 폴더가 있으면 옮기고, 없으면
 * `trashed_to: null` 로 목록에서 빼는 것으로 끝낸다 (FR-420).
 *
 * 이름 변경만 접근 가능 여부를 탄다 — 그쪽은 프로젝트 파일을 **읽고 써야** 한다.
 */
function ProjectRow({
  item,
  first,
  busy,
  onOpen,
  onForget,
  onRenamed,
  onTrashed,
  onStaleList,
}: {
  item: ProjectListItem;
  first: boolean;
  busy: boolean;
  onOpen: () => void;
  onForget: () => void;
  onRenamed: (updated: ProjectListItem) => void;
  onTrashed: (result: TrashProjectResponse) => void;
  onStaleList: () => void;
}) {
  const [mode, setMode] = useState<RowMode>({ kind: "idle" });
  const [rowError, setRowError] = useState<ErrorInfo | null>(null);
  /**
   * 이름 입력이 지금 왜 안 되는가. **서버 오류와 갈라 둔다** — 이쪽은 요청을 보내기
   * 전에 화면이 스스로 아는 것이고, 사용자가 그 자리에서 고칠 수 있다 (UC-012-02).
   */
  const [nameProblem, setNameProblem] = useState<string | null>(null);
  /** 이 줄의 요청이 도는 중인가. 연타로 같은 프로젝트에 두 요청이 겹치지 않게 한다. */
  const [pending, setPending] = useState(false);

  const locked = busy || pending;

  const fail = (exc: unknown) => {
    const info = describeError(exc);
    setRowError(info);
    // 목록이 낡았다 — 서버가 모르는 프로젝트라고 답했으면 화면의 목록이 틀린 것이다.
    if (info.code === "INVALID_PATH" || info.code === "PROJECT_NOT_FOUND") onStaleList();
  };

  const commitRename = (raw: string) => {
    const name = raw.trim();
    // 빈 이름은 요청하기 전에 막는다 (FR-403). 서버도 막지만 사용자는 왜 안 되는지
    // 화면에서 바로 알아야 한다 — 「만들기」가 무엇이 빠졌는지 미리 말하는 것과 같다.
    if (name === "") {
      setNameProblem("프로젝트 이름은 비워 둘 수 없습니다.");
      return;
    }
    if (name === item.name) {
      setMode({ kind: "idle" });
      setRowError(null);
      setNameProblem(null);
      return;
    }
    setPending(true);
    setRowError(null);
    setNameProblem(null);
    void project
      .renameProject(item.root, name)
      .then((updated) => {
        onRenamed(updated);
        setMode({ kind: "idle" });
      })
      .catch(fail)
      .finally(() => setPending(false));
  };

  const openConfirm = () => {
    setRowError(null);
    setNameProblem(null);
    setMode({ kind: "confirming", summary: null });
    // 열 수 없는 줄은 셀 수 없다. 물어봐야 0 이 오므로 아예 묻지 않는다.
    if (!item.accessible) return;
    // 여기서 처음 센다. 목록 조회에 싣지 않는 이유는 목록을 그리려고 프로젝트 N개를
    // 열게 되기 때문이다 (UC-012-03).
    void project
      .summary(item.root)
      .then((summary) =>
        setMode((m) => (m.kind === "confirming" ? { kind: "confirming", summary } : m)),
      )
      .catch(() => {
        /* 수를 못 세도 확인은 계속된다. 이름과 경로로 판단할 수 있다. */
      });
  };

  const confirmTrash = () => {
    setPending(true);
    setRowError(null);
    void project
      .trash(item.root)
      .then((result) => {
        setMode({ kind: "idle" });
        onTrashed(result);
      })
      .catch(fail)
      .finally(() => setPending(false));
  };

  return (
    <div
      className={`${first ? "" : "rule-top "}${item.accessible ? "" : "dim"}`.trim() || undefined}
      style={{ display: "flex", flexDirection: "column", gap: 10, padding: "14px 16px" }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {mode.kind === "editing" ? (
              <input
                aria-label="프로젝트 이름"
                value={mode.draft}
                autoFocus
                disabled={pending}
                onChange={(e) => setMode({ kind: "editing", draft: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename(mode.draft);
                  if (e.key === "Escape") {
                    // 원래 이름으로 되돌리고 **요청하지 않는다**.
                    setMode({ kind: "idle" });
                    setRowError(null);
                    setNameProblem(null);
                  }
                }}
                onBlur={() => {
                  if (!pending) commitRename(mode.draft);
                }}
                style={{ margin: 0, maxWidth: 320 }}
              />
            ) : (
              <span className="subtitle">{item.name}</span>
            )}
            {item.origin === "external" && <span className="chip">외부 위치</span>}
            {!item.accessible && <span className="chip fail">열 수 없음</span>}
          </div>
          {nameProblem !== null && (
            <div className="line fail-ink" style={{ marginTop: 4 }} role="alert">
              {nameProblem}
            </div>
          )}
          <div
            className="why mono"
            style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
            title={item.root}
          >
            {item.root}
          </div>
          {!item.accessible && item.unavailable_reason !== null && (
            <div className="line fail-ink" style={{ marginTop: 4 }}>
              {item.unavailable_reason}
            </div>
          )}
          {!item.accessible && (
            // 왜 이 줄에 이름 변경이 없는지 말한다 (FR-406). 조작을 그냥 빼면 사용자는
            // 자기가 잘못 본 줄 안다. **삭제는 있다** — 없애는 길까지 막으면 이 줄은
            // 목록에서 사라지지 않는다 (FR-418 · SC-622).
            <div className="why" style={{ marginTop: 4 }}>
              열 수 없는 상태여서 이름을 바꿀 수 없습니다. 삭제하거나 목록에서 치울 수 있습니다.
            </div>
          )}
        </div>

        {mode.kind !== "confirming" && (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {mode.kind === "idle" && (
              <>
                {item.accessible && (
                  <>
                    <button className="btn" onClick={onOpen} disabled={locked}>
                      열기
                    </button>
                    <button
                      className="navlink"
                      onClick={() => setMode({ kind: "editing", draft: item.name })}
                      disabled={locked}
                    >
                      이름 바꾸기
                    </button>
                  </>
                )}
                {/* 삭제는 열 수 없는 줄에도 있다 (FR-418 · SC-622). */}
                <button
                  className="navlink"
                  onClick={openConfirm}
                  disabled={locked}
                  title={
                    item.accessible
                      ? "프로젝트 폴더를 휴지통으로 옮깁니다. 파일은 지워지지 않고 되돌릴 수 있습니다."
                      : "폴더가 남아 있으면 휴지통으로 옮기고, 이미 없으면 목록에서만 뺍니다."
                  }
                >
                  삭제
                </button>
              </>
            )}
            <button
              className="navlink"
              onClick={onForget}
              disabled={locked}
              // 삭제와 결과가 다르다. 두 설명 모두 디스크의 파일이 어떻게 되는지
              // 말한다 (FR-423 · UC-012-07).
              title="목록에서만 치웁니다. 디스크의 파일은 지우지 않습니다."
            >
              목록에서 치우기
            </button>
          </div>
        )}
      </div>

      {mode.kind === "confirming" && (
        <ConfirmTrash
          item={item}
          summary={mode.summary}
          pending={pending}
          onCancel={() => setMode({ kind: "idle" })}
          onConfirm={confirmTrash}
        />
      )}

      {rowError !== null && <ErrorNotice error={rowError} />}
    </div>
  );
}

/**
 * 삭제 확인 (012 FR-411·FR-412·FR-424·FR-425 · UC-012-03).
 *
 * **모달이 아니라 그 줄 안이다.** 프로젝트가 여러 개일 때 모달의 "정말 삭제할까요?" 는
 * 대상을 다시 확인시키지 못한다 — 사용자는 자기가 어느 줄을 눌렀는지 기억에 의존해야
 * 한다. 줄 안에서 물으면 이름과 경로가 눈앞에 그대로 있다.
 */
function ConfirmTrash({
  item,
  summary,
  pending,
  onCancel,
  onConfirm,
}: {
  item: ProjectListItem;
  summary: ProjectSummary | null;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="tint-warn" style={{ padding: "12px 14px" }} role="group" aria-label="삭제 확인">
      <div className="subtitle">「{item.name}」을(를) 휴지통으로 옮길까요?</div>
      <div className="why mono" style={{ marginTop: 4 }}>
        {item.root}
      </div>
      {summary !== null && (
        <div className="line" style={{ marginTop: 6 }}>
          저장된 테스트 {summary.test_count}개가 함께 옮겨집니다.
        </div>
      )}
      {item.origin === "external" && (
        // 도구가 만든 자리가 아니다. 사용자가 다른 용도로 쓰고 있을 수 있으므로
        // 그 사실을 알고 결정하게 한다 (FR-424).
        <div className="line" style={{ marginTop: 6 }}>
          이 폴더는 도구 바깥에서 만들어진 위치입니다.
        </div>
      )}
      {!item.accessible && (
        // 무슨 일이 일어날지 미리 말한다 (UC-012-03). 열 수 없는 줄에서는 옮길 것이
        // 없을 수 있고, 그때 결과는 「목록에서 뺐다」다 — 놀라게 하지 않는다.
        <div className="line" style={{ marginTop: 6 }}>
          지금 열 수 없는 상태입니다. 폴더가 남아 있으면 휴지통으로 옮기고, 이미 없으면
          목록에서만 뺍니다.
        </div>
      )}
      <div className="note" style={{ marginTop: 6 }}>
        지우지 않고 휴지통으로 옮깁니다. 옮긴 위치를 알려 드리므로 되돌릴 수 있습니다.
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
        {/* 취소가 기본이다 — 포커스를 여기에 둔다. */}
        <button className="btn" onClick={onCancel} disabled={pending} autoFocus>
          취소
        </button>
        <button className="btn" onClick={onConfirm} disabled={pending}>
          휴지통으로 옮기기
        </button>
      </div>
    </div>
  );
}

/**
 * 무엇을 어디로 옮겼는지 (012 FR-410·FR-425 · UC-012-04).
 *
 * **자동으로 사라지지 않는다.** 사라지면 되돌리는 방법이 함께 사라진다. 경로는 `mono`
 * 로, 잘리지 않게 표시한다 — 이 값이 되돌리는 방법 전부다.
 */
function TrashedNotice({
  result,
  onDismiss,
}: {
  result: TrashProjectResponse;
  onDismiss: () => void;
}) {
  return (
    <div className="tint-warn" style={{ padding: "12px 16px", marginBottom: 18 }} role="status">
      {result.trashed_to === null ? (
        <>
          <div className="subtitle">「{result.name}」을(를) 목록에서 뺐습니다.</div>
          <div className="note" style={{ marginTop: 4 }}>
            폴더가 이미 없어서 옮길 것이 없었습니다.
          </div>
        </>
      ) : (
        <>
          <div className="subtitle">「{result.name}」을(를) 휴지통으로 옮겼습니다.</div>
          {/*
            **출발지와 도착지를 둘 다 남긴다** (SC-616 · converge T050). 되돌리기는 두
            경로가 있어야 성립하는데, 도착지만 보여 주면 "원래 자리" 를 사용자가 알아야
            한다. 관리 위치라면 짐작할 수 있지만 외부 위치 프로젝트는 사용자가 직접 고른
            경로여서 추측이 불가능하다.
          */}
          <div className="lbl" style={{ marginTop: 8 }}>
            옮긴 곳
          </div>
          <div className="why mono" style={{ marginTop: 2, wordBreak: "break-all" }}>
            {result.trashed_to}
          </div>
          <div className="lbl" style={{ marginTop: 8 }}>
            원래 자리
          </div>
          <div className="why mono" style={{ marginTop: 2, wordBreak: "break-all" }}>
            {result.root}
          </div>
          <div className="note" style={{ marginTop: 8 }}>
            되돌리려면 「옮긴 곳」의 폴더를 「원래 자리」로 옮기세요. 도구는 휴지통을 자동으로
            비우지 않습니다.
          </div>
        </>
      )}
      <button className="navlink" onClick={onDismiss} style={{ marginTop: 8 }}>
        확인했습니다
      </button>
    </div>
  );
}

// ─── 새로 만들기 (DR-001·DR-006) ────────────────────────────────────────────

function CreateForm({
  busy,
  onCancel,
  onSubmit,
  defaultName = "",
  importNote,
}: {
  busy: boolean;
  onCancel: () => void;
  onSubmit: (body: { name: string; default_start_url: string; test_id_attribute: string }) => void;
  /**
   * 이름 칸의 기본값 (014 FR-014b).
   *
   * 엑셀에서 만들 때 파일 이름을 제안한다. **고칠 수 있어야 한다** — 파일 이름이 늘
   * 좋은 프로젝트 이름은 아니다. 그래서 값이 아니라 초기값이다.
   */
  defaultName?: string;
  /** 가져오기로 무엇이 함께 만들어지는지 알린다. */
  importNote?: React.ReactNode;
}) {
  const [name, setName] = useState(defaultName);
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
    <div className="pane" style={{ padding: 24 }}>
      <Eyebrow>NEW PROJECT</Eyebrow>

      {importNote}

      <p className="note" style={{ marginTop: 10 }}>
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
        <p className="line fail-ink" style={{ marginTop: 6 }}>
          http:// 또는 https:// 로 시작해야 합니다.
        </p>
      )}

      <label htmlFor="attr">testId 속성명</label>
      <input id="attr" value={testIdAttr} onChange={(e) => setTestIdAttr(e.target.value)} />
      <p className="why" style={{ marginTop: 6 }}>
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
        className={`why ${ready ? "" : "fail-ink"}`.trimEnd()}
        style={{ margin: "16px 0 0" }}
      >
        {ready
          ? "만들 준비가 되었습니다."
          : `아직 만들 수 없습니다 — ${missing.join(", ")}을 채우세요.`}
      </p>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 20 }}>
        <button className="btn" onClick={onCancel} disabled={busy}>
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
    <div className="pane" style={{ padding: 24 }}>
      <Eyebrow>PROJECT CREATED</Eyebrow>

      <div className="title" style={{ marginTop: 10 }}>
        {p.name}
      </div>

      <p className="note" style={{ marginTop: 12 }}>
        아래 위치에 만들었습니다. 다음에 도구를 열면 이 프로젝트가 목록에 바로 나타납니다.
      </p>

      <div className="log sunken" style={{ padding: "10px 12px", marginTop: 10, wordBreak: "break-all" }}>
        {p.root}
      </div>

      <p className="why" style={{ marginTop: 10 }}>
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
    <div className="pane">
      <div className="rule-bottom" style={{ padding: "16px 18px" }}>
        <Eyebrow>OPEN EXISTING</Eyebrow>
        <div className="log muted" style={{ marginTop: 8, wordBreak: "break-all" }}>
          {here ?? "…"}
        </div>
      </div>

      {error !== null && <ErrorNotice error={error} />}

      <div style={{ maxHeight: 360, overflowY: "auto" }}>
        {parent !== null && (
          <button
            className="navlink"
            onClick={() => go(parent)}
            style={{ width: "100%", height: 44, justifyContent: "flex-start", textAlign: "left", padding: "0 20px" }}
          >
            ↑ 상위 폴더
          </button>
        )}

        {entries === null && <p className="why" style={{ padding: "16px 20px" }}>불러오는 중…</p>}

        {entries !== null && entries.length === 0 && (
          <p className="why" style={{ padding: "16px 20px" }}>
            이 폴더에는 하위 폴더가 없습니다.
          </p>
        )}

        {entries?.map((e) => (
          <div
            key={e.path}
            className="rule-top"
            style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 18px" }}
          >
            <button
              className="navlink"
              onClick={() => go(e.path)}
              style={{ flex: 1, justifyContent: "flex-start", textAlign: "left", padding: 0, height: 32 }}
            >
              📁 {e.name}
            </button>
            {e.is_project && <span className="chip">프로젝트</span>}
            {e.is_project && (
              <button className="btn" disabled={busy} onClick={() => onPick(e.path)}>
                열기
              </button>
            )}
          </div>
        ))}
      </div>

      <div
        className="rule-top"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          padding: "16px 18px",
        }}
      >
        <span className="why">
          「프로젝트」 표시가 붙은 폴더만 열 수 있습니다.
        </span>
        <div style={{ display: "flex", gap: 12 }}>
          <button className="btn" onClick={onCancel} disabled={busy}>
            취소
          </button>
          {here !== null && (
            <button className="btn primary" disabled={busy} onClick={() => onPick(here)}>
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
      className={tone === "fail" ? "tint-fail" : "tint-warn"}
      style={{
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
