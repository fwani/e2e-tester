/**
 * 테스트 목록. **`docs/design/008-visual-language/TestList.dc.html`·`EmptyList.dc.html`
 * (1440×900) 기준.** DC-001~DC-009.
 *
 * ## 2026-09-08 (008) — 전사에서 소비로
 *
 * 이전 판의 머리말은 "인라인 style 값을 확정 디자인에서 그대로 옮겼다 … 토큰 치환으로
 * 바꾸지 않는다" 였다. 그 방침이 결함이 됐다 — 이 파일 하나에 색 리터럴 90개와 시각 언어
 * 인라인 선언 141개가 쌓였고, 표 머리는 검정 바탕, 행 조작은 셋 다 잉크 채움, 결말은
 * 실패만 배경색이었다. 확정 디자인은 그중 어느 것도 그렇게 그리지 않는다.
 *
 * 이제 형태는 `theme/tokens.css` 정본에서 오고 여기는 `className` 으로 쓴다. 남는 인라인은
 * 배치(격자·폭·여백)뿐이다 (`contracts/visual-language.md` §2).
 *
 * ## 동작은 그대로다
 *
 * 001 FR-002~FR-007 (상태 표식·ID·이름·Step 수·작성 표식·마지막 실행·검색·집계·이름 변경·
 * 삭제) · 005 FR-127~FR-170 (실행 준비 표시·결과 도달·살아 있는 세션) · 006 FR-175 (편집
 * 진입). **삭제는 되돌릴 수 없으므로 행 안에서 확인을 받는다** — 어느 테스트를 지우는지
 * 눈으로 보면서 결정하게 한다.
 *
 * ## 008 이 더한 것
 *
 * 확정 디자인에 있는데 코드에 없던 둘이다 (FR-272 · DC-007).
 * - **결말 필터 4종** 전체·통과·실패·미실행. 이전에는 개수만 보여주고 거르지 못했다
 * - **정렬** 「최근 실행 순」
 *
 * 둘 다 **화면 안에서 계산한다.** 백엔드 `list_tests` 는 `q` 만 받고(research R7), 응답 행이
 * 이미 `outcome`·`last_run_at` 을 담는다. 이 기능은 백엔드를 건드리지 않는다.
 *
 * 확정 디자인이 정의했으나 만들지 않은 것은 `conformance/undefined-states.md` 에 사유와
 * 함께 적었다 — 바닥 띠의 「전체 실행」이며, 여러 테스트를 잇달아 돌리는 것은 화면 작업이
 * 아니라 실행 기능이라 이 기능의 범위 밖이다.
 */
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import {
  ai,
  ApiError,
  drafts as draftsApi,
  excel,
  groups as groupsApi,
  saveBlob,
  tests,
  type AiAvailability,
  type SessionView,
  type TestListRow,
  type TestGroup,
  type TestListResponse,
  type DraftRow,
  type ImportPlanView,
  type TrashedTest,
} from "../api/client";
import { TestGroupBar } from "../components/TestGroupBar";
import { DraftSection } from "./DraftList";
import { ImportFilePicker } from "./ImportPreview";
import {
  TestBulkConfirm,
  TestSelectionBar,
  RenumberConfirm,
  RenumberedNotice,
  TrashedTestsNotice,
} from "../components/TestBulkConfirm";
import { ErrorNotice, describeError, localError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";
import { Artboard, BrandMark, HeaderBar, HeaderDivider } from "../components/design/Chrome";
import { isRunning } from "../lib/sessionState";
import { EDIT_ENTRY_LABEL, outcomeChip, outcomeLabel, stepLabel } from "../lib/wording";
import { chipClass, rowClass } from "../theme/tone";
import type { Outcome } from "../types/generated/run-result";

/** 목록 격자. 표 머리와 행이 **같은 값을 쓴다** — 다르면 정렬이 값에 따라 흔들린다 (FR-273). */
const GRID = "28px 96px 82px 1fr 64px 92px 150px 168px";
/** 맨 앞 28px 이 체크 칸이다 (013 FR-426 · UC-013-01).

    **행 누름(열기)과 갈라 둔다.** 두 동작을 한 자리에 두면 열려던 사용자가 삭제 대상을
    고른다 — 011 이 Step 목록에서 정한 규칙이다. */

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

/** 결말 필터. 확정 디자인이 그리는 넷이며 그 이상 늘리지 않는다 (FR-272). */
type OutcomeFilter = "all" | "pass" | "fail" | "none";

/** 개수 옆의 잉크. 확정 디자인은 통과·실패 개수에만 상태 색을 쓴다. */
const FILTER_INK: Record<OutcomeFilter, string> = {
  all: "",
  pass: "pass-ink",
  fail: "fail-ink",
  none: "dim",
};

const FILTER_LABEL: Record<OutcomeFilter, string> = {
  all: "전체",
  pass: "통과",
  fail: "실패",
  none: "미실행",
};

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
  /** 프로젝트 선택 화면으로 간다. 없으면 그 길을 그리지 않는다 */
  onOpenProjects?: () => void;
  /**
   * 살아 있는 세션. 새로고침으로 화면만 잃은 녹화·실행을 되찾는 길이다 (UX U-05).
   * 서버에는 Step 과 브라우저가 그대로 있는데 화면이 그것을 말하지 않으면 사용자는
   * 새 녹화를 시작하고, 앞의 기록은 영영 못 찾는다.
   */
  /**
   * 엑셀에서 가져오기 미리보기를 연다 (014 US2). 없으면 그 길을 그리지 않는다.
   *
   * 이 화면이 미리보기를 직접 그리지 않는 이유는 시트가 200개까지 올 수 있어
   * 목록 안에 담기지 않기 때문이다.
   */
  onImportPlan?: (plan: ImportPlanView) => void;
  /** 초안에서 AI 작성 세션을 시작한다 (014 US3). */
  onRecordDraft?: (draft: DraftRow) => void;
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
  onOpenProjects,
  onImportPlan,
  onRecordDraft,
  activeSessions = [],
  onRefreshSessions,
  onResumeSession,
  onDiscardSession,
}: TestListProps) {
  const [data, setData] = useState<TestListResponse | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<OutcomeFilter>("all");
  const [recentFirst, setRecentFirst] = useState(true);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exported, setExported] = useState<{ filename: string; warnings: number } | null>(null);
  const [draftRows, setDraftRows] = useState<DraftRow[]>([]);
  const [draftProblems, setDraftProblems] = useState<string[]>([]);
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  /**
   * 삭제·이동 대상으로 고른 것 (013 · data-model §5).
   *
   * **화면에만 있고 저장하지 않는다.** 새로 고치면 비어 있는 것이 맞다 — 잃어도 막히지
   * 않는 정보만 화면에 둔다.
   */
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmingBulk, setConfirmingBulk] = useState(false);
  /** 방금 옮긴 것들. **자동으로 사라지지 않는다** (FR-437b · UC-013-05). */
  const [trashed, setTrashed] = useState<TrashedTest[] | null>(null);
  /**
   * 번호 정리 (2026-09-10 사용자 보고 2번).
   *
   * **확인을 받는다.** 식별자는 사용자가 git 에 커밋해 보관하는 자산의 이름이고
   * (헌법 원칙 V), 이 조작은 그 이름을 여러 개 한꺼번에 바꾼다. 삭제와 같은 무게로 다룬다.
   */
  const [confirmingRenumber, setConfirmingRenumber] = useState(false);
  /** 방금 바뀐 번호. 삭제 결과와 같은 이유로 **자동으로 사라지지 않는다.** */
  const [renumbered, setRenumbered] = useState<
    { renumbered: { from_id: string; to_id: string; name: string }[]; unchanged: number } | null
  >(null);
  /** 고른 그룹의 접두어. `null` 이면 전체 (013 FR-441). */
  const [groupFilter, setGroupFilter] = useState<string | null>(null);
  /**
   * **정의된 그룹 전부** — 테스트가 0개인 것도 포함한다 (013 converge T061).
   *
   * 목록 응답(`data.groups`)은 테스트가 **있는** 그룹만 싣는다 (FR-450 — 소제목이
   * 목록을 어지럽히지 않아야 한다). 그것을 띠의 근거로 쓰면 **테스트를 전부 옮긴 그룹이
   * 띠에서 사라져 고를 수도, 이름을 고칠 수도, 없앨 수도 없다.**
   *
   * 두 응답의 규칙을 합치지 않는다 — 어지럽히지 않는 것은 **소제목** 이야기이고, 띠는
   * **고르는 자리**라 비어 있어도 있어야 한다 (contracts/api-contract.md §5).
   */
  const [definedGroups, setDefinedGroups] = useState<TestGroup[]>([]);

  const reload = async (q: string, group: string | null = groupFilter) => {
    try {
      // 그룹은 **서버에서** 거른다 (013 FR-441). 화면에서 거르면 그룹 개수와 목록이
      // 갈릴 수 있다 — 개수는 걸러 보기 전 값이어야 하기 때문이다.
      setData(await tests.list(q.trim() || undefined, group ?? undefined));
      setError(null);
    } catch (exc) {
      setError(describeError(exc));
    }
  };

  /**
   * 조작 하나를 걸고 목록을 다시 읽는다.
   *
   * **결과를 돌려준다** (2026-09-10). 이전에는 `await fn()` 의 값을 버렸고, 그래서
   * `.then((res) => …)` 로 완료 표시를 세우던 **한 개 삭제가 아무것도 그리지 않았다** —
   * `res` 가 언제나 `undefined` 였기 때문이다. 여러 개 삭제는 `act` 를 지나지 않아
   * 표시가 떴으므로, 「한 개와 여러 개의 결과가 같다」(SC-632)가 조용히 깨져 있었다.
   */
  const act = async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      const result = await fn();
      await Promise.all([reload(query), reloadGroups()]);
      return result;
    } catch (exc) {
      setError(describeError(exc));
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  /**
   * 삭제 결과를 화면에 세운다 — **옮긴 것과 이미 없던 것을 갈라서** (2026-09-10).
   *
   * `trashed_to === null` 은 「요청 시점에 이미 없어서 옮길 것이 없었다」다 (013 FR-436).
   * 그것을 옮긴 것과 같이 다루면 화면은 **옮기지 않은 것을 옮겼다고 말하고**, 「옮긴
   * 자리」 칸에 빈 값을 그린다. 다른 창에서 이미 지운 뒤 이 창에서 지운 사용자가 정확히
   * 그것을 본다 (003 AS-046 · 조용한 성공 EC-007).
   *
   * 없던 것을 **오류로 만들지는 않는다** — 사용자가 원한 결과는 이미 이루어져 있다.
   * 사실만 말하고 다음 행동(목록이 이미 갱신됐다)을 붙인다.
   */
  const showDeleteOutcome = (deleted: TrashedTest[]) => {
    const moved = deleted.filter((t) => t.trashed_to !== null);
    const missing = deleted.filter((t) => t.trashed_to === null);
    setTrashed(moved.length > 0 ? moved : null);
    setError(
      missing.length === 0
        ? null
        : localError(
            missing.length === 1
              ? `「${missing[0]!.name}」은(는) 이미 지워져 있어 옮기지 않았습니다.`
              : `${missing.length}개는 이미 지워져 있어 옮기지 않았습니다.`,
            "다른 창이나 편집기에서 먼저 지운 것으로 보입니다. 목록은 방금 갱신했습니다.",
          ),
    );
  };

  /**
   * 번호를 `001` 부터 다시 붙인다 (2026-09-10 사용자 보고 2번).
   *
   * 결과를 **띄우고 지우지 않는다** — 어느 식별자가 어디로 갔는지가 사용자가 자기
   * 저장소에서 찾아야 할 정보다.
   */
  const runRenumber = () => {
    setConfirmingRenumber(false);
    setBusy(true);
    setError(null);
    void tests
      .renumber()
      .then(async (result) => {
        setRenumbered(result);
        // 고른 것은 옛 식별자를 가리킨다 — 그대로 두면 없는 것을 지우려 든다.
        setSelected(new Set());
        await Promise.all([reload(query), reloadGroups()]);
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  /**
   * 초안 목록 (014 US3).
   *
   * 실패해도 삼킨다 — 그룹과 같은 판단이다. 초안을 못 불러와도 테스트 목록은 그려야
   * 한다. 첫 화면이 막히면 아무것도 못 한다.
   */
  const reloadDrafts = async () => {
    try {
      const body = await draftsApi.list();
      setDraftRows(body.drafts ?? []);
      setDraftProblems(body.problems ?? []);
    } catch {
      setDraftRows([]);
      setDraftProblems([]);
    }
  };

  const reloadGroups = async () => {
    try {
      // `?? []` 가 없으면 응답이 어긋났을 때 **목록 화면 전체가 깨진다.** 그룹은
      // 선택 사항인데 그것 때문에 아무것도 못 하게 되어서는 안 된다.
      setDefinedGroups((await groupsApi.list()).groups ?? []);
    } catch {
      // 그룹을 못 불러와도 목록은 그려야 한다 — 첫 화면이 막히면 아무것도 못 한다.
      setDefinedGroups([]);
    }
  };

  useEffect(() => {
    void reload(query, groupFilter);
    void reloadGroups();
    void reloadDrafts();
    // 검색어·그룹이 바뀔 때마다 다시 조회한다. 로컬 도구이므로 디바운스 없이도 충분하다.
  }, [query, groupFilter]);

  const all = useMemo(() => data?.tests ?? [], [data]);

  /**
   * 결말별 개수. **거르기 전 전체**를 센다 — 필터가 자기 개수를 0으로 만들면 돌아올 길이
   * 사라진다.
   */
  const counts = useMemo(
    () => ({
      all: all.length,
      pass: all.filter((t) => t.outcome === "pass").length,
      fail: all.filter((t) => t.outcome === "fail").length,
      none: all.filter((t) => t.outcome === null).length,
    }),
    [all],
  );

  /**
   * 화면 안에서 거르고 정렬한다 (research R7).
   *
   * 검색(`q`)만 서버를 다시 부른다. 둘이 다른 층에서 작동한다는 사실은 화면 동작에
   * 드러나지 않는다 — 사용자는 둘 다 즉시 반영되는 것으로 본다.
   */
  const rows = useMemo(() => {
    const kept =
      filter === "all"
        ? all
        : filter === "none"
          ? all.filter((t) => t.outcome === null)
          : all.filter((t) => t.outcome === filter);
    if (!recentFirst) return kept;
    return [...kept].sort((a, b) => {
      // 한 번도 돌리지 않은 것은 뒤로. 시각이 없는 것끼리는 순서를 바꾸지 않는다.
      const at = a.last_run_at === null ? -Infinity : new Date(a.last_run_at).getTime();
      const bt = b.last_run_at === null ? -Infinity : new Date(b.last_run_at).getTime();
      return bt - at;
    });
  }, [all, filter, recentFirst]);

  /**
   * **보이는 것만 고를 수 있다** (013 FR-429 · UC-013-03 · SC-625).
   *
   * 검색어나 걸러 보기가 바뀌어 어떤 행이 화면에서 사라지면 그 행은 선택에서도 빠진다.
   * 보이지 않는 것이 선택에 남으면 사용자는 **무엇을 지웠는지 볼 수 없는 삭제**를 하게 된다.
   *
   * 선택 자체를 지우지 않고 **읽을 때 거른다** — 검색어를 되돌리면 고른 것이 돌아오는
   * 편이 사용자의 기대에 맞고, 대상이 되는 것은 언제나 이 값이라 안전하다.
   */
  const effectiveSelection = useMemo(
    () => rows.filter((r) => selected.has(r.id)).map((r) => r.id),
    [rows, selected],
  );
  const selectedNames = useMemo(
    () => rows.filter((r) => selected.has(r.id)).map((r) => r.name),
    [rows, selected],
  );
  const allVisibleSelected =
    rows.length > 0 && rows.every((r) => selected.has(r.id));

  /**
   * 목록을 **그룹별로 묶는다** (013 FR-440 · UC-013-06).
   *
   * 한 그룹만 골라 본 상태에서는 묶지 않는다 — 소제목이 하나뿐이면 자리만 차지한다.
   * 그룹이 아예 없는 프로젝트에서도 묶지 않는다: **이 기능 이전과 같은 모습이어야
   * 한다** (SC-627).
   *
   * 「그룹 없음」은 **마지막에 온다.** 이름이 있는 묶음을 먼저 보여주는 것이 목록을
   * 훑는 순서에 맞는다.
   */
  const grouped = useMemo(() => {
    const definedGroups = (data?.groups ?? []).filter((g) => g.prefix !== "TC");
    if (definedGroups.length === 0 || groupFilter !== null) return null;

    const byPrefix = new Map<string, TestListRow[]>();
    for (const r of rows) {
      const bucket = byPrefix.get(r.group_prefix);
      if (bucket) bucket.push(r);
      else byPrefix.set(r.group_prefix, [r]);
    }
    const nameOf = new Map((data?.groups ?? []).map((g) => [g.prefix, g.name]));
    const sections = [...byPrefix.entries()]
      .map(([prefix, items]) => ({
        prefix,
        // 정의가 없는 접두어는 이름을 지어내지 않는다 — 접두어가 곧 이름이다.
        label: nameOf.get(prefix) ?? (prefix === "TC" ? "그룹 없음" : prefix),
        items,
      }))
      .sort((a, b) => {
        if (a.prefix === "TC") return 1;
        if (b.prefix === "TC") return -1;
        return a.label.localeCompare(b.label, "ko");
      });
    return sections;
  }, [rows, data, groupFilter]);

  const mergedGroups = useMemo(() => {
    const fromList = data?.groups ?? [];
    const seen = new Set(fromList.map((g) => g.prefix));
    const empties = definedGroups
      .filter((g) => !seen.has(g.prefix))
      .map((g) => ({ prefix: g.prefix, name: g.name, count: 0 }));
    return [...fromList, ...empties].sort((a, b) => {
      // 「그룹 없음」은 마지막에 온다 — 이름이 있는 묶음을 먼저 보여준다.
      if (a.prefix === "TC") return 1;
      if (b.prefix === "TC") return -1;
      return (a.name ?? a.prefix).localeCompare(b.name ?? b.prefix, "ko");
    });
  }, [data, definedGroups]);

  const totalSteps = useMemo(() => all.reduce((s, t) => s + t.step_count, 0), [all]);

  /** 고른 것들을 휴지통으로 (013 FR-432). 확인을 거친 뒤에만 부른다. */
  const runBulkDelete = () => {
    const ids = effectiveSelection;
    if (ids.length === 0) return;
    setBusy(true);
    setError(null);
    void tests
      .deleteMany(ids)
      .then(async (res) => {
        setSelected(new Set());
        setConfirmingBulk(false);
        // **목록을 먼저 읽는다.** `reload` 는 성공하면 `setError(null)` 로 지난 오류를
        // 걷는데, 결과 표시를 그 앞에 세우면 방금 세운 「이미 지워져 있었습니다」가
        // 같은 틱에 지워진다.
        await reload(query);
        showDeleteOutcome(res.deleted);
      })
      .catch((exc: unknown) => {
        // **선택을 비우지 않는다** (UC-013-07). 다시 고르게 만들면 실행을 멈추고
        // 돌아온 뜻이 없어진다.
        setError(describeError(exc));
        setConfirmingBulk(false);
      })
      .finally(() => setBusy(false));
  };
  const lastRun = useMemo(() => {
    const times = all.map((t) => t.last_run_at).filter((t): t is string => t !== null);
    if (times.length === 0) return null;
    return times.reduce((a, b) => (new Date(a).getTime() > new Date(b).getTime() ? a : b));
  }, [all]);

  /**
   * 테스트가 하나도 없는 첫 사용자 화면 — `EmptyList.dc.html` 이 기준이다.
   *
   * **걸러 본 결과가 0건인 것은 「빈 프로젝트」가 아니다.** 검색어는 처음부터 그렇게
   * 다뤘고(`query.trim() === ""`), 013 이 더한 그룹 걸러 보기에도 같은 이유가 그대로
   * 적용된다 — 그것을 빠뜨리면 **테스트가 0개인 그룹을 고르는 순간 화면이 첫 사용자
   * 안내로 바뀌고 그룹 띠까지 사라져**, 사용자가 돌아올 길을 잃는다 (converge T061).
   */
  const isEmptyProject =
    data !== null && all.length === 0 && query.trim() === "" && groupFilter === null;

  const liveOf = (testId: string) => activeSessions.find((s) => s.test_id === testId) ?? null;
  /**
   * 화면 맨 위 알림이 가리키는 세션. **돌고 있는 것을 먼저** 고르되, 끝난 세션도 남긴다.
   *
   * 005 FR-168 은 「칩과 복귀는 다른 요구사항」이라고 못박았다 — 세션이 `review` 로 끝나
   * 행의 표식이 결말로 돌아가도 그 작업 창으로 돌아갈 길은 남아야 한다. 그것을 running
   * 에만 걸면 중지 직후 복귀 수단이 사라진다 (007 재점검 N-02 가 잡은 형태).
   */
  const openSession = activeSessions.find((s) => isRunning(s.state)) ?? activeSessions[0] ?? null;

  return (
    <Artboard width={1440} minHeight={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <div className="row">
          <span className="lbl">프로젝트</span>
          <span className="pill">{projectName}</span>
          {/*
            **프로젝트 목록으로 가는 길** (사용자 보고 · 2026-09-09 — 「프로젝트 목록으로
            가는 방법이 없다」).

            프로젝트 선택 화면은 처음부터 있었지만 **`project.current()` 가 실패할 때만**
            그리로 갔다. 즉 한 번 프로젝트를 열면 다른 프로젝트로 갈 길이 화면 어디에도
            없었다 — 서버를 다시 띄우는 것 말고는 방법이 없는 상태였다.

            자리를 프로젝트 이름 **바로 옆**에 둔다. 「어느 프로젝트인가」를 읽는 자리가
            「다른 것으로 간다」를 찾는 자리다. 형태는 오른쪽의 다른 진입점들과 같은
            `navlink` 다 — 확정 디자인에 없는 화면으로 가는 길은 눈에 띄지 않게 둔다
            (DC-010).
          */}
          {onOpenProjects && (
            <button className="navlink" onClick={onOpenProjects}>
              바꾸기
            </button>
          )}
        </div>
        <div className="spacer" />
        {/* 확정 디자인에 없는 화면들의 진입점. 눈에 띄지 않게 둔다 (DC-010). */}
        {onOpenSecrets && (
          <button className="navlink" onClick={onOpenSecrets}>
            비밀 값
          </button>
        )}
        {onOpenKeys && (
          <button className="navlink" onClick={onOpenKeys}>
            키 관리
          </button>
        )}
        <HeaderDivider />
        {/*
          008 FR-269 — **잉크 채움은 이 화면에 하나뿐이다.** 이전에는 행마다 「실행」·
          「결과 보기」·「실행 화면 보기」가 전부 잉크로 채워져 있어서 무엇이 주 동작인지
          화면이 말하지 못했다. 채움은 여기 하나이고 나머지는 중립이다.
        */}
        <button className="btn primary" onClick={onCreate}>
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.9">
            <path d="M7 2.4v9.2M2.4 7h9.2" />
          </svg>
          테스트 만들기
        </button>
      </HeaderBar>

      {/*
        005 FR-168 (U-16) — 지금 돌고 있다는 사실이 목록 맨 위에 온다. 실행 중 새로고침하면
        목록으로 떨어지는데, 그 사실과 복귀 수단이 없으면 사용자는 새 실행을 시작한다.
      */}
      {openSession !== null && (
        <div
          className={`notice ${isRunning(openSession.state) ? "tint-run" : "tint-warn"}`}
          role="status"
          data-open-session
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <circle cx="8" cy="8" r="4.5" fill="currentColor" />
          </svg>
          <span>
            <b>{openSession.test_id ?? "테스트"}</b> · {openSession.state_label} · Step{" "}
            {openSession.steps.length}개
          </span>
          <div className="spacer" />
          {onResumeSession && (
            <button className="btn sm" onClick={() => onResumeSession(openSession)}>
              실행 화면 보기
            </button>
          )}
        </div>
      )}

      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          padding: "14px 16px",
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

        {error !== null && (
          <div className="tint-fail" style={{ padding: "8px 14px", whiteSpace: "pre-wrap" }} role="alert">
            <ErrorNotice error={error} />
          </div>
        )}

        {data !== null && data.problems.length > 0 && (
          <div className="tint-warn" style={{ padding: "8px 14px" }} role="status">
            <strong>읽지 못한 정의 파일이 있습니다.</strong>
            <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
              {data.problems.map((p) => (
                <li key={p} className="num">
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ─── 조작 줄 — 검색 · 결말 필터 · 정렬 ─────────────────────────── */}
        <div className="row" style={{ gap: "10px" }}>
          <div className={`field${isEmptyProject ? " off" : ""}`} style={{ flex: 1, maxWidth: "520px" }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7">
              <circle cx="7" cy="7" r="4.6" />
              <path d="M10.6 10.6L14 14" />
            </svg>
            <input
              aria-label="테스트 검색"
              placeholder={
                isEmptyProject ? "검색할 테스트가 아직 없습니다" : "이름 · ID · Step 안의 locator 로 검색"
              }
              value={query}
              disabled={isEmptyProject}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          {!isEmptyProject && (
            <>
              {/*
                008 FR-272 — 확정 디자인이 정의한 결말 필터 넷. 이전에는 개수만 보여주고
                거르지 못했다. 개수는 **거르기 전 전체**를 세므로 필터가 자기 자신을
                0으로 만들어 돌아올 길을 없애지 않는다.
              */}
              <div className="row" style={{ gap: "6px" }} role="group" aria-label="결말로 거르기">
                {(["all", "pass", "fail", "none"] as const).map((key) => (
                  <button
                    key={key}
                    className={`btn sm${filter === key ? " primary" : ""}`}
                    aria-pressed={filter === key}
                    onClick={() => setFilter(key)}
                  >
                    {FILTER_LABEL[key]}
                    <span className={`num ${FILTER_INK[key]}`}>{counts[key]}</span>
                  </button>
                ))}
              </div>

              <div className="spacer" />

              <button
                className="btn sm"
                aria-pressed={recentFirst}
                onClick={() => setRecentFirst((v) => !v)}
              >
                {recentFirst ? "최근 실행 순" : "저장된 순"}
              </button>

              {/*
                번호 정리 (2026-09-10 사용자 보고 2번 — 「번호를 일괄적으로 맞추거나
                재조정하는 방법이 있으면 좋겠다」).

                자리가 정렬 옆인 이유는 **둘 다 목록을 읽는 방식에 대한 조작**이기
                때문이다. 실행·삭제 같은 대상 조작이 아니다.

                **걸러 보기와 무관하다.** 프로젝트 전체의 번호를 다시 붙이므로, 지금
                보이는 것만 대상으로 오해되지 않게 확인 단계가 그 사실을 말한다.
              */}
              <button
                className="btn sm"
                data-action="tests.renumber"
                disabled={busy || counts.all === 0}
                onClick={() => {
                  setRenumbered(null);
                  setConfirmingRenumber(true);
                }}
              >
                번호 정리
              </button>

              {/*
                엑셀로 내보내기 (014 US1 · FR-001).

                자리가 「번호 정리」 옆인 이유는 둘 다 **프로젝트 전체에 대한 조작**이기
                때문이다. 걸러 보기와 무관하게 전부 나간다.

                `btn primary` 를 쓰지 않는다 — 이 화면의 잉크 채움은 「테스트 만들기」
                하나뿐이다 (이 파일 헤더바 주석).

                「Playwright 로 내보내기」(릴리스 게이트 RG-1)와 **다른 것**이다.
                그쪽은 아직 없고, 이름이 섞이지 않게 「엑셀로」를 앞에 둔다.
              */}
              <button
                className="btn sm"
                data-action="tests.export-excel"
                disabled={busy || exporting}
                onClick={() => {
                  setError(null);
                  setExported(null);
                  setExporting(true);
                  void excel
                    .exportProject()
                    .then(({ blob, filename, warnings }) => {
                      saveBlob(blob, filename);
                      setExported({ filename, warnings });
                    })
                    .catch((exc: unknown) => setError(describeError(exc)))
                    .finally(() => setExporting(false));
                }}
              >
                {exporting ? "내보내는 중…" : "엑셀로 내보내기"}
              </button>

              {/* 엑셀에서 가져오기 (014 US2). 내보내기 옆에 두어 두 방향이 한자리에 있다. */}
              {onImportPlan !== undefined && (
                <ImportFilePicker
                  label="엑셀에서 가져오기"
                  disabled={busy}
                  onPlan={onImportPlan}
                  onError={setError}
                />
              )}
            </>
          )}
        </div>

        {/* ─── 그룹 띠 (013 UC-013-06) ──────────────────────────────────── */}
        {!isEmptyProject && (
          <TestGroupBar
            /*
              **정의된 그룹 ∪ 실제로 테스트가 있는 접두어.** 앞쪽이 빈 그룹을 살리고,
              뒤쪽이 「그룹 없음」과 정의가 없는 접두어를 살린다. 어느 한쪽만으로는
              띠에서 사라지는 것이 생긴다.
            */
            groups={mergedGroups}
            active={groupFilter}
            busy={busy}
            onPick={(prefix) => {
              // 걸러 보기가 바뀌면 보이지 않게 된 것은 선택에서도 빠진다 (FR-429).
              // 선택은 `effectiveSelection` 이 읽을 때 거르므로 여기서 비우지 않는다.
              setGroupFilter(prefix);
            }}
            onCreate={(prefix, name) =>
              void act(() => groupsApi.create(prefix, name))
            }
            onRename={(prefix, name) => void act(() => groupsApi.rename(prefix, name))}
            onRemove={(prefix) =>
              void act(() => groupsApi.remove(prefix)).then(() => {
                // 없어진 그룹을 계속 보고 있으면 빈 목록이 그려진다.
                if (groupFilter === prefix) setGroupFilter(null);
              })
            }
          />
        )}

        {/* ─── 선택·확인·완료 (013 UC-013-02·04·05) ─────────────────────── */}
        {!isEmptyProject && trashed !== null && (
          <TrashedTestsNotice trashed={trashed} onDismiss={() => setTrashed(null)} />
        )}
        {!isEmptyProject && confirmingRenumber && (
          <RenumberConfirm
            total={data?.counts.total ?? 0}
            busy={busy}
            onConfirm={runRenumber}
            onCancel={() => setConfirmingRenumber(false)}
          />
        )}
        {!isEmptyProject && renumbered !== null && (
          <RenumberedNotice result={renumbered} onDismiss={() => setRenumbered(null)} />
        )}
        {/*
          내보내기 결과 (014 FR-008·FR-010·FR-013).

          **경고가 있으면 그 사실을 말한다.** 시트 이름이 바뀌었거나 긴 칸이 잘렸는데
          조용히 성공하면, 사용자는 자기가 쓴 그룹 이름을 파일에서 찾지 못하고 그 이유를
          알 길이 없다.
        */}
        {exported !== null && (
          <div
            data-export-notice
            role="status"
            className={exported.warnings > 0 ? "tint-warn" : "tint-run"}
            style={{ padding: "10px 12px", marginBottom: 10 }}
          >
            <div className="strong-sm">{exported.filename} 을 내려받았습니다.</div>
            {exported.warnings > 0 && (
              <div className="why" style={{ marginTop: 4 }}>
                시트 이름이 바뀌었거나 긴 칸이 잘린 곳이 {exported.warnings}건 있습니다.
              </div>
            )}
            <button className="btn sm" style={{ marginTop: 8 }} onClick={() => setExported(null)}>
              확인
            </button>
          </div>
        )}
        {!isEmptyProject && confirmingBulk && (
          <TestBulkConfirm
            names={selectedNames}
            busy={busy}
            onConfirm={runBulkDelete}
            onCancel={() => setConfirmingBulk(false)}
          />
        )}
        {/* 고른 것이 0개면 띠 자체를 그리지 않는다 — 쓰지 않는 사용자에게 자리를
            뺏지 않는다 (SC-627). */}
        {!isEmptyProject && !confirmingBulk && effectiveSelection.length > 0 && (
          <TestSelectionBar
            selectedCount={effectiveSelection.length}
            visibleCount={rows.length}
            allVisibleSelected={allVisibleSelected}
            busy={busy}
            onSelectAllVisible={() => setSelected(new Set(rows.map((r) => r.id)))}
            onClear={() => setSelected(new Set())}
            onDelete={() => setConfirmingBulk(true)}
            extra={
              // 그룹이 하나도 없으면 옮길 곳이 없다 — 그리지 않는다 (SC-627).
              (data?.groups ?? []).some((g) => g.prefix !== "TC") ? (
                <select
                  aria-label="그룹으로 옮기기"
                  disabled={busy}
                  value=""
                  onChange={(e) => {
                    const to = e.target.value;
                    if (to === "") return;
                    void act(() => tests.move(effectiveSelection, to)).then(() =>
                      setSelected(new Set()),
                    );
                  }}
                  style={{ margin: 0 }}
                >
                  <option value="">그룹으로 옮기기…</option>
                  {(data?.groups ?? [])
                    .filter((g) => g.name !== null)
                    .map((g) => (
                      <option key={g.prefix} value={g.prefix}>
                        {g.name}
                      </option>
                    ))}
                  <option value="TC">그룹에서 빼기</option>
                </select>
              ) : undefined
            }
          />
        )}

        {/* ─── 목록 ──────────────────────────────────────────────────────── */}
        {isEmptyProject ? (
          <EmptyProject
            onCreate={onCreate}
            onOpenKeys={onOpenKeys}
            onImportPlan={onImportPlan}
            onError={setError}
          />
        ) : (
          <div className="pane" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div
              className="thead"
              style={{
                flex: "0 0 34px",
                display: "grid",
                gridTemplateColumns: GRID,
                gap: "12px",
                alignItems: "center",
                padding: "0 14px 0 17px",
              }}
            >
              <div>
                <input
                  type="checkbox"
                  aria-label="보이는 테스트 전부 선택"
                  checked={allVisibleSelected}
                  disabled={busy || rows.length === 0}
                  onChange={() =>
                    setSelected(
                      allVisibleSelected ? new Set() : new Set(rows.map((r) => r.id)),
                    )
                  }
                />
              </div>
              <div className="lbl">마지막 결과</div>
              <div className="lbl">ID</div>
              <div className="lbl">이름</div>
              <div className="lbl" style={{ textAlign: "right" }}>
                STEP
              </div>
              <div className="lbl">작성</div>
              <div className="lbl">마지막 실행</div>
              <div />
            </div>

            <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
              {/* 확정 디자인은 행이 있는 상태만 그린다. 아래 둘은 undefined-states.md 에
                  기록했고 정본의 형태만으로 그린다 (DC-009). */}
              {data === null && (
                <div className="why" style={{ padding: "24px 17px" }}>
                  불러오는 중…
                </div>
              )}

              {data !== null && rows.length === 0 && (
                <div className="muted" style={{ padding: "24px 17px" }}>
                  {query.trim() !== ""
                    ? `"${query}" 에 해당하는 테스트가 없습니다.`
                    : `${FILTER_LABEL[filter]}인 테스트가 없습니다.`}
                </div>
              )}

              {/*
                그룹이 있으면 소제목으로 묶고, 없으면 지금까지처럼 평평하게 그린다
                (013 FR-440 · SC-627). **행을 그리는 코드는 하나다** — 두 벌로 두면
                묶은 쪽에만 새 조작이 붙는 일이 생긴다.
              */}
              {(grouped ?? [{ prefix: "", label: "", items: rows }]).map((section) => (
                <div key={section.prefix || "__flat__"}>
                  {grouped !== null && (
                    <div
                      className="lbl"
                      data-group-heading={section.prefix}
                      style={{ padding: "10px 17px 4px" }}
                    >
                      {section.label} {section.items.length}
                    </div>
                  )}
                  {section.items.map((row) => (

                    <Row
                      key={row.id}
                      row={row}
                      busy={busy}
                      selected={selected.has(row.id)}
                      onToggleSelected={() =>
                        setSelected((prev) => {
                          const next = new Set(prev);
                          if (next.has(row.id)) next.delete(row.id);
                          else next.add(row.id);
                          return next;
                        })
                      }
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
                        // **한 개와 여러 개의 결과가 같아야 한다** (SC-632). 완료 표시도
                        // 같은 것을 쓴다 — 한쪽만 옮겨진 자리를 알려 주면 사용자는 개수에
                        // 따라 되돌릴 수 있는지가 달라진다고 읽는다.
                        void act(() => tests.remove(row.id))
                          .then((res) => {
                            setConfirmingDelete(null);
                            if (res !== undefined) showDeleteOutcome([res]);
                          })
                      }
                      onToggleMenu={() => setMenuFor(menuFor === row.id ? null : row.id)}
                      /*
                        **여는 것과 닫는 것을 나눈다.** 메뉴는 목록 밖(`document.body`)에
                        떠 있으므로 목록이 스크롤하면 행에서 떨어진다 — 그때 닫아야 한다.
                        그 자리에서 `onToggleMenu` 를 쓰면 한 프레임에 두 번 온 사건이
                        닫았다 다시 여는 일이 생긴다.
                      */
                      onCloseMenu={() => setMenuFor(null)}
                      onRun={() => onRun(row.id)}
                      runPending={pendingRunId === row.id}
                      /*
                        005 FR-168 (U-16) — 지금 돌고 있다는 사실이 **행에도** 보인다.
                        상단 배너만 "실행 중" 을 알리고 행의 표식은 이전 실행의 실패였다.
                      */
                      liveSession={liveOf(row.id)}
                      onOpenResult={() => onOpenResult(row.id)}
                      onOpenDefinition={onOpenDefinition ? () => onOpenDefinition(row.id) : undefined}
                    />
                  ))}
                </div>
              ))}
            </div>

            {/* 바닥 띠 — 프로젝트 전체의 규모와 마지막 실행. */}
            <div
              className="tfoot"
              style={{
                flex: "0 0 40px",
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "0 14px",
              }}
            >
              <span className="why">
                테스트 {counts.all}개 · Step {totalSteps}개 · 마지막 전체 실행{" "}
                {lastRun === null ? "없음" : relativeTime(lastRun)}
              </span>
              <div className="spacer" />
              {/*
                헌법 V — 내보내기는 출시 전까지 갖춰야 하는 약속이고 MVP 에는 없다.
                **감추지 않고 비활성으로 두고 이유를 붙인다** (006 ui-contract §2).
              */}
              <button className="btn sm off" disabled>
                Playwright 로 내보내기
              </button>
              <span className="why">MVP 미지원</span>
            </div>
          </div>
        )}

        {/*
          녹화하지 않은 초안 (014 US3 · FR-027).

          **테스트 목록의 행으로 섞지 않는다.** 초안은 실행할 수 없고 결말이 없어, 같은
          표에 두면 사용자가 행마다 무엇을 할 수 있는지 매번 확인해야 한다.

          첫 사용자 화면(`isEmptyProject`)에서도 그린다 — 엑셀에서 가져오기만 한 프로젝트는
          테스트가 0개이고 초안만 있다. 그때 이 영역을 감추면 사용자가 방금 들여온 것이
          어디로 갔는지 알 수 없다.
        */}
        {onRecordDraft !== undefined && (
          <DraftSection
            drafts={draftRows}
            problems={draftProblems}
            busy={busy}
            onRecord={onRecordDraft}
            onChanged={() => void reloadDrafts()}
            onError={setError}
          />
        )}
      </div>
    </Artboard>
  );
}

/** 떠 있는 행 메뉴의 치수. 여는 자리를 계산할 때 쓴다. */
const MENU_MIN_WIDTH = 160;
/** 단추와 메뉴 사이. 붙여 놓으면 어느 쪽을 눌렀는지 눈으로 갈리지 않는다. */
const MENU_GAP = 2;
/** 창 가장자리와의 최소 간격. 0 이면 메뉴가 화면 끝에 물린다. */
const MENU_EDGE = 8;
/**
 * 떠 있는 메뉴의 겹침 순서.
 *
 * 이 화면에서 가장 높다. 목록 위에 겹치는 것이 메뉴뿐이므로 다른 값과 겨루지 않는다 —
 * 겹침이 문제였던 적은 없고, 문제는 잘림이었다 (`Row` 의 `menuPos` 주석).
 */
const MENU_Z = 40;

// ─── 행 ─────────────────────────────────────────────────────────────────────

function Row({
  row,
  busy,
  selected,
  onToggleSelected,
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
  onCloseMenu,
  onRun,
  onOpenResult,
  onOpenDefinition,
  runPending = false,
  liveSession = null,
}: {
  row: TestListRow;
  busy: boolean;
  /** 삭제·이동 대상으로 골랐는가 (013 FR-426). */
  selected: boolean;
  onToggleSelected: () => void;
  renaming: string | null;
  confirming: boolean;
  menuOpen: boolean;
  onCloseMenu: () => void;
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
  /**
   * 이 테스트로 지금 돌고 있는 세션 (005 FR-168). 없으면 `null`.
   *
   * 행은 이것으로 **표식만** 정한다. 그 세션으로 돌아가는 조작은 화면 맨 위 알림 띠가
   * 갖는다 — 한 화면에 같은 일을 하는 조작을 둘 두지 않는다.
   */
  liveSession?: SessionView | null;
}) {
  const live = liveSession !== null && isRunning(liveSession.state);
  /** 열어 볼 결과가 있는가 (005 FR-130). 결말 종류와 무관하다 — U-13 이 이것이었다. */
  const hasResult = row.outcome != null || row.last_run_at != null;

  const menuAnchor = useRef<HTMLButtonElement | null>(null);
  const menuBox = useRef<HTMLDivElement | null>(null);
  /**
   * 떠 있는 메뉴의 화면 좌표 (사용자 보고 · 2026-09-09 — 「메뉴가 안 보임」).
   *
   * ## 왜 목록 밖으로 내보내는가
   *
   * 메뉴는 행 안에 `position: absolute` 로 있었다. **그 위로 조상 셋이 잘라 낸다** —
   * 목록 스크롤 상자(`overflow: auto`)와 그것을 감싼 `.pane`(`overflow: hidden`), 그리고
   * 바깥 아트보드다. `overflow` 가 `visible` 이 아닌 조상은 자식을 잘라 내고, **`z-index`
   * 로는 거기서 빠져나갈 수 없다.**
   *
   * 실측(1440×900, 40행, 목록을 끝까지 내린 상태): 마지막 행의 메뉴는 `top=844
   * bottom=942` 인데 스크롤 상자가 845 에서 잘라, 그 자리에서 실제로 잡히는 것은 바닥
   * 띠의 「Playwright 로 내보내기」였다. 보고된 화면이 정확히 그것이다.
   *
   * 그래서 `document.body` 로 내보내고 `position: fixed` 로 붙인다. 잘라 낼 조상이
   * 없으므로 어느 행에서 열어도 온전히 보인다.
   *
   * ## 대신 감당하는 것
   *
   * 떠 있으므로 목록이 스크롤해도 따라오지 않는다 — 그때는 **닫는다** (`onCloseMenu`).
   * 행에서 떨어진 채 떠 있는 메뉴는 어느 행의 것인지 말할 수 없다.
   */
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null);
  /**
   * 자리를 잴 때의 단추 위치. 스크롤이 **실제로 행을 움직였는지** 판정하는 기준이다.
   *
   * 스크롤 사건 하나만 보고 닫으면 **메뉴가 열리자마자 닫힌다.** 화면에 반쯤 걸친 행의
   * 단추를 누르면 브라우저가 그것을 보이게 하려고 스스로 스크롤하고, 그 사건이 곧바로
   * 도착하기 때문이다 — 실측에서 마지막 행의 메뉴가 그렇게 사라졌다.
   *
   * 그 스크롤은 자리를 재기 **전에** 끝나 있다. 그래서 「사건이 왔는가」가 아니라
   * 「기준보다 움직였는가」를 묻는다.
   */
  const anchorTop = useRef(0);

  useLayoutEffect(() => {
    if (!menuOpen) {
      setMenuPos(null);
      return;
    }
    const anchor = menuAnchor.current;
    if (anchor === null) return;
    const a = anchor.getBoundingClientRect();
    anchorTop.current = a.top;
    const box = menuBox.current;
    const h = box?.offsetHeight ?? 0;
    const w = box?.offsetWidth ?? MENU_MIN_WIDTH;
    // 아래에 자리가 모자라면 **위로 연다.** 창 밖으로 나가면 잘리던 것과 같은 결과다.
    const below = a.bottom + MENU_GAP;
    const flip = h > 0 && below + h + MENU_EDGE > window.innerHeight;
    setMenuPos({
      top: flip ? Math.max(MENU_EDGE, a.top - MENU_GAP - h) : below,
      // 오른쪽 정렬. 창 왼쪽으로 넘어가지 않게 막는다.
      left: Math.max(MENU_EDGE, a.right - w),
    });
  }, [menuOpen, onOpenDefinition]);

  useEffect(() => {
    if (!menuOpen) return;
    // 목록이 스크롤하거나 창이 바뀌면 메뉴는 제 행에서 떨어진다. 따라가게 만드는 것보다
    // 닫는 편이 낫다 — 따라가더라도 그 행이 스크롤 밖으로 나가면 가리킬 대상이 없다.
    const closeIfMoved = () => {
      const a = menuAnchor.current?.getBoundingClientRect();
      if (a === undefined) return onCloseMenu();
      if (Math.abs(a.top - anchorTop.current) > 1) onCloseMenu();
    };
    const close = () => onCloseMenu();
    // `capture` 여야 목록 **안쪽** 스크롤 상자의 스크롤도 잡는다. 스크롤 사건은 위로
    // 올라오지 않는다.
    window.addEventListener("scroll", closeIfMoved, true);
    window.addEventListener("resize", close);
    return () => {
      window.removeEventListener("scroll", closeIfMoved, true);
      window.removeEventListener("resize", close);
    };
  }, [menuOpen, onCloseMenu]);

  return (
    <div
      /*
        008 FR-271 — 결말을 **왼쪽 3px 표식**으로 말한다.

        이전에는 실패 행에만 옅은 배경을 줬다. 통과와 미실행이 시각적으로 같았고, 색약
        사용자에게는 배경 하나가 유일한 단서였다. 표식은 색과 **위치**를 함께 쓴다.

        어느 표식인지는 `theme/tone.ts` 가 결말 넷 전부에서 정한다 — 화면이
        `outcome === "pass" ? …` 로 가르면 중지가 실패로 보인다 (U-03).
      */
      className={rowClass(row.outcome, live)}
      data-test-row={row.id}
      style={{
        display: "grid",
        gridTemplateColumns: GRID,
        gap: "12px",
        padding: "0 14px",
        // 이름 변경·삭제 확인은 행 안에서 펼쳐지므로 그때만 높이를 늘린다.
        ...(renaming !== null || confirming ? { height: "auto", minHeight: "44px", paddingTop: 8, paddingBottom: 8 } : {}),
      }}
    >
      {/*
        체크 칸은 **행 누름과 갈라 둔다** (013 FR-426 · UC-013-01). 행을 누르는 것은
        열기이고 체크는 삭제·이동 대상 고르기다. 한 자리에 두면 열려던 사용자가 삭제
        대상을 고른다 — 011 이 Step 목록에서 정한 규칙이다.

        `stopPropagation` 이 그 분리를 실제로 만든다: 체크 칸을 눌렀을 때 행의 열기가
        함께 일어나면 갈라 둔 뜻이 없다.
      */}
      <div onClick={(e) => e.stopPropagation()} style={{ display: "flex", alignItems: "center" }}>
        <input
          type="checkbox"
          aria-label={`${row.name} 선택`}
          data-test-select={row.id}
          checked={selected}
          disabled={busy}
          onChange={onToggleSelected}
        />
      </div>

      <div>
        {/*
          005 FR-169 (재점검 N-02) — 표식은 세션의 **상태**를 본다.

          이전에는 세션의 **존재**를 봤다(`liveSession !== null`). 실행이 끝나도 세션은
          `failed`·`review` 로 등록에 남으므로 행은 영원히 「실행 중」이었고, 같은 화면의
          배너는 「실패」로 갱신됐다 — 배너와 행이 다른 말을 했다.
        */}
        <OutcomeChip outcome={row.outcome} running={live} />
      </div>

      <div className="num">{row.id}</div>

      <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: "3px" }}>
        {renaming !== null ? (
          <div className="row" style={{ paddingRight: 12 }}>
            <input
              aria-label="새 이름"
              value={renaming}
              autoFocus
              onChange={(e) => onRenameChange(e.target.value)}
            />
            <button
              className="btn sm primary"
              disabled={busy || renaming.trim() === ""}
              onClick={() => onRenameSubmit(renaming.trim())}
            >
              저장
            </button>
            <button className="btn sm" onClick={onRenameCancel}>
              취소
            </button>
          </div>
        ) : (
          <div className="name">{row.name}</div>
        )}

        {/* FR-005 — 실패한 테스트는 실패 Step 번호와 메시지 요약을 인라인으로 보여준다. */}
        {row.failure_summary !== null && (
          <div className="meta fail-ink" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {stepLabel(row.failure_summary.step_index)} · {row.failure_summary.message}
          </div>
        )}

        {confirming && (
          <div className="row" style={{ paddingTop: 4 }}>
            <span className="num fail-ink">
              「{row.name}」을 지웁니다. 되돌릴 수 없습니다.
            </span>
            <button className="btn sm danger" disabled={busy} onClick={onDeleteConfirm}>
              삭제
            </button>
            <button className="btn sm" onClick={onDeleteCancel}>
              취소
            </button>
          </div>
        )}
      </div>

      <div className="num" style={{ textAlign: "right" }}>
        {row.step_count}
      </div>

      <div>
        <AuthoringChip mode={row.authoring_mode} />
      </div>

      <div className="meta">{live ? "실행 중" : relativeTime(row.last_run_at)}</div>

      {/*
        005 FR-130 — 「실행」은 **항상** 두고, 결과가 있으면 「결과 보기」도 함께 둔다
        (U-12·U-13). 한 자리에 둘 중 하나만 두던 때, 실패한 테스트는 「결과 보기」로
        바뀌어 목록에서 다시 실행할 수 없었고(U-12), 통과한 테스트는 그 실행의 결과에
        도달할 길이 아예 없었다(U-13).

        008 — 셋 다 중립 형태다. 이 화면의 잉크 채움은 헤더의 「테스트 만들기」뿐이다.
      */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px", position: "relative" }}>
        {/*
          008 — 「실행 화면 보기」는 **화면에 하나뿐이다.**

          005 FR-168 은 실행 중 새로고침으로 목록에 떨어졌을 때 돌아갈 수단을 요구했고,
          그때는 행 안에 뒀다. 확정 디자인은 그것을 화면 맨 위 알림 띠에 둔다. 둘 다 두면
          같은 일을 하는 조작이 한 화면에 둘이 되고, 그것이 007 UC-102 가 없앤 형태다.
          돌아갈 수단은 사라지지 않았고 더 눈에 띄는 자리로 옮겼다.
        */}
        {/*
          005 FR-130·FR-169 — **돌고 있는 동안만** 결과를 감춘다. 이전 조건은 세션이 열려
          있으면 결과 버튼을 지웠고, 중지한 뒤 목록으로 나오면 세션이 `review` 로 남아
          방금 남은 결과에 도달할 길이 없었다 (U-13 의 재발).
        */}
        {hasResult && !live && (
          <button className="btn sm" onClick={onOpenResult}>
            결과 보기
          </button>
        )}
        <button className={`btn sm${runPending ? " off" : ""}`} onClick={onRun} disabled={runPending}>
          {!runPending && (
            <svg width="11" height="11" viewBox="0 0 16 16">
              <path d="M4 2l10 6-10 6z" fill="currentColor" />
            </svg>
          )}
          {/* 005 FR-129 — 클릭 직후 0.3초 안에 화면이 변한다. 이전에는 0.8~1.2초간
              완전히 그대로여서 사용자가 다시 눌렀다 (U-11 → U-06). */}
          {runPending ? "준비 중…" : "실행"}
        </button>

        <button
          ref={menuAnchor}
          className="btn sm"
          aria-label={`${row.name} 추가 동작`}
          onClick={onToggleMenu}
          style={{ padding: "0 7px" }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <circle cx="6" cy="2" r="1.1" />
            <circle cx="6" cy="6" r="1.1" />
            <circle cx="6" cy="10" r="1.1" />
          </svg>
        </button>

        {menuOpen &&
          createPortal(
            <div
              ref={menuBox}
              className="pane"
              data-row-menu={row.id}
              style={{
                position: "fixed",
                top: menuPos?.top ?? 0,
                left: menuPos?.left ?? 0,
                zIndex: MENU_Z,
                // 자리를 재기 전에는 그리지 않는다 — 그리면 왼쪽 위에서 제자리로 튄다.
                visibility: menuPos === null ? "hidden" : "visible",
                display: "flex",
                flexDirection: "column",
                minWidth: `${MENU_MIN_WIDTH}px`,
                padding: "4px",
                gap: "2px",
              }}
            >
            {/*
              006 FR-175 — 「정의 보기」를 **「편집」으로 대체한다.** 보기만 하는 별도 항목을
              남기면 사용자는 다시 "고치려면 어디로 가지" 를 묻게 되고, 그것이 006 이 없앤
              E-01·E-03 이다. 편집 화면은 저장하지 않으면 아무것도 바꾸지 않으므로 보기 위해
              들어가도 안전하다.
            */}
            {onOpenDefinition && (
              <button className="navlink" onClick={onOpenDefinition} style={{ justifyContent: "flex-start" }}>
                {EDIT_ENTRY_LABEL}
              </button>
            )}
            <button className="navlink" onClick={onRenameStart} style={{ justifyContent: "flex-start" }}>
              이름
            </button>
              <button className="navlink fail-ink" onClick={onDeleteStart} style={{ justifyContent: "flex-start" }}>
                삭제
              </button>
            </div>,
            document.body,
          )}
      </div>
    </div>
  );
}

// ─── 상태 표식 ──────────────────────────────────────────────────────────────

/**
 * 목록 행의 결말 표식 (005 FR-141).
 *
 * **네 결말을 전부 다룬다.** `outcome === "pass" ? 초록 : 붉은` 이분법은 사용자가 누른
 * 중지를 실패 색으로, 부분 성공도 실패 색으로 칠했다.
 *
 * 실행 중인 테스트에는 「실행 중」을 보여준다 (FR-168) — 이전 실행의 결말을 그대로 두면
 * 지금 돌고 있다는 사실이 행에서 사라진다 (U-16).
 */
function OutcomeChip({ outcome, running = false }: { outcome: Outcome | null; running?: boolean }) {
  if (running) {
    /*
      문구는 `RUNNING` 그대로다. 확정 디자인은 이 표식을 「실행 중」으로 그리지만, 목록
      표식의 어휘는 005 FR-140·U-20 이 `PASS`/`FAIL` 계열로 통일해 둔 것이고 그것을 이
      화면에서만 바꾸면 화면마다 다른 말이 다시 생긴다. 디자인과의 차이는 대조 기록에
      L3-1 로 남기고 어휘 계약과 함께 판정한다 (T070).
    */
    return (
      <span className="chip run">
        <svg width="10" height="10" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="5" fill="currentColor" />
        </svg>
        RUNNING
      </span>
    );
  }
  if (outcome === null) {
    /*
      008 — 「미실행」이라고 **말한다.**

      v1 은 여기에 `—` 를 그렸다. 한 번도 돌리지 않은 테스트가 기본 상태인데, 목록의 첫
      칸이 빈 칸이면 사용자가 처음 보는 것이 "아무것도 없음" 이 된다. 점선 표식은
      「아직 결과가 없다」는 사실 자체를 상태로 보여준다 (Language.dc.html §04).
    */
    return <span className={chipClass(null)}>미실행</span>;
  }
  return (
    // 색만으로 구분하지 않는다 — 표식에는 항상 글자가 있고, 스크린리더에는 한국어 문장을 준다.
    <span className={chipClass(outcome)} title={outcomeLabel(outcome)}>
      {outcomeChip(outcome)}
    </span>
  );
}

function AuthoringChip({ mode }: { mode: "record" | "ai" }) {
  // FR-002a — 테스트를 시작한 방식으로 고정한다. AI 로 시작해 사람이 이어받아도 AI 다.
  if (mode === "ai") return <span className="chip ai">AI</span>;
  return <span className="chip">RECORD</span>;
}

// ─── 확정 디자인이 정의하지 않은 상태 (DC-009) ────────────────────────────

/**
 * 테스트가 하나도 없는 프로젝트 — `EmptyList.dc.html`.
 *
 * 008 이 처음 정의한 화면이다. 이전에는 목록 표 안에 한 줄짜리 안내를 뒀는데, **첫
 * 사용자가 실제로 보는 화면**이 그것이었다. 여기서 두 갈래(녹화·AI)를 나란히 보여주고
 * 각각 무엇이 필요한지 말한다.
 *
 * ## AI 쪽 상태는 **확인해서** 말한다 (001 DR-021)
 *
 * 008 판은 「키 필요」 표식과 「언어모델 키 등록하기」 버튼을 **고정 문구로** 뒀다.
 * 그래서 자격 증명이 이미 있는 환경(`/api/ai/availability` 가 `available: true`)에서도
 * 화면은 키가 없다고 말하고, 이 화면에서 AI 로 시작하는 길이 아예 없었다 — 첫 사용자가
 * 보는 화면이 사실과 반대되는 상태다. `ComposeView` 는 처음부터 이 점검을 했으므로
 * 같은 사실을 두 화면이 다르게 말하고 있었다.
 *
 * 확인 전에는 「키 필요」도 「사용 가능」도 말하지 않는다 — 아직 모르는 것을 단정하면
 * 고정 문구와 같은 결함이 된다.
 */
function EmptyProject({
  onCreate,
  onOpenKeys,
  onImportPlan,
  onError,
}: {
  onCreate: () => void;
  onOpenKeys?: () => void;
  /**
   * 엑셀에서 가져오기 (014 US2).
   *
   * **이 화면에 있어야 한다.** 테스트가 0개인 프로젝트는 설계서를 들여오기에 가장
   * 좋은 상태이고, 목록 조작 띠는 이 화면에서 그려지지 않는다 — 거기에만 두면 가장
   * 필요한 순간에 길이 없다.
   */
  onImportPlan?: (plan: ImportPlanView) => void;
  onError?: (error: ErrorInfo) => void;
}) {
  const [aiReady, setAiReady] = useState<AiAvailability | null>(null);

  useEffect(() => {
    void ai
      .availability()
      .then(setAiReady)
      .catch((exc: unknown) =>
        setAiReady({
          available: false,
          reason: exc instanceof ApiError ? exc.message : String(exc),
        }),
      );
  }, []);

  return (
    <div
      className="pane"
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px",
      }}
    >
      <div
        style={{
          maxWidth: "720px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "22px",
          textAlign: "center",
        }}
      >
        <svg width="52" height="52" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="1.6" className="dim">
          <rect x="4" y="7" width="32" height="7" rx="1.5" />
          <rect x="4" y="17" width="32" height="7" rx="1.5" strokeDasharray="3.4 3" />
          <rect x="4" y="27" width="32" height="7" rx="1.5" strokeDasharray="3.4 3" />
        </svg>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div className="title">아직 테스트가 없습니다</div>
          <div className="note">
            브라우저를 직접 조작하거나, 할 일을 말로 적으면 됩니다.
            <br />
            어느 쪽으로 만들어도 같은 Step 모델로 저장되고, 다시 돌릴 때는 Playwright 가 실행합니다.
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
            width: "100%",
            textAlign: "left",
          }}
        >
          <div className="pane" style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "9px" }}>
            <div className="row">
              <svg width="14" height="14" viewBox="0 0 16 16" className="fail-ink">
                <circle cx="8" cy="8" r="5" fill="currentColor" />
              </svg>
              <div className="subtitle">직접 녹화</div>
            </div>
            <div className="why">브라우저를 직접 조작해서 만듭니다. 키가 필요 없습니다.</div>
            <button className="btn primary" onClick={onCreate} style={{ justifyContent: "center" }}>
              녹화로 시작하기
            </button>
          </div>

          <div className="pane" style={{ padding: "14px", display: "flex", flexDirection: "column", gap: "9px" }}>
            <div className="row">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" className="ai-ink">
                <path d="M8 2v3M8 11v3M2 8h3M11 8h3M4.2 4.2l2 2M9.8 9.8l2 2M11.8 4.2l-2 2M6.2 9.8l-2 2" />
              </svg>
              <div className="subtitle ai-ink">AI 로 만들기</div>
              {/* 확인이 끝난 뒤에만 표식을 붙인다 (DR-021) */}
              {aiReady !== null && (
                <span
                  className={aiReady.available ? "chip ai" : "chip warn"}
                  data-ai-ready={aiReady.available ? "yes" : "no"}
                  style={{ marginLeft: "auto" }}
                >
                  {aiReady.available ? "사용 가능" : "키 필요"}
                </span>
              )}
            </div>
            <div className="why">할 일을 말로 적으면 AI 가 브라우저에서 해봅니다.</div>
            {/*
              쓸 수 없는 조작을 감추지 않는다 (006 ui-contract §2). 쓸 수 있으면
              **막지도 않는다** — 키가 있는데 키 등록으로 보내면 갈 곳이 없다.
            */}
            {aiReady?.available === true ? (
              <button className="btn primary" onClick={onCreate} style={{ justifyContent: "center" }}>
                AI 로 시작하기
              </button>
            ) : (
              <>
                {/* 왜 못 쓰는지 백엔드가 준 문구를 그대로 보여준다 (DR-016) */}
                {aiReady !== null && aiReady.reason !== null && (
                  <div className="why" style={{ whiteSpace: "pre-wrap" }}>
                    {aiReady.reason}
                  </div>
                )}
                <button
                  className="btn off"
                  onClick={onOpenKeys}
                  disabled={aiReady === null || onOpenKeys === undefined}
                  style={{ justifyContent: "center" }}
                >
                  {aiReady === null ? "확인 중…" : "언어모델 키 등록하기"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* 세 번째 갈래 — 이미 쓰던 설계서가 있는 사용자 (014 US2). */}
        {onImportPlan !== undefined && (
          <div className="pane" style={{ padding: "14px", width: "100%", textAlign: "left" }}>
            <div className="subtitle">이미 쓰던 설계서가 있나요?</div>
            <div className="why" style={{ margin: "6px 0 10px" }}>
              엑셀 파일을 넣으면 그룹과 테스트 초안을 만듭니다. 초안은 하나씩 녹화하면
              테스트가 됩니다.
            </div>
            <ImportFilePicker
              label="엑셀에서 가져오기"
              onPlan={onImportPlan}
              onError={(err) => onError?.(err)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

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
      className="tint-warn"
      style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div className="row">
        <strong className="strong-sm">진행 중인 세션이 있습니다</strong>
        <div className="spacer" />
        {/*
          005 FR-169 (U-17) — 배너가 실제 상태를 따라간다.

          리포트는 실행이 끝난 뒤 25초를 더 기다려도 배너가 "실행 중" 으로 남아 있는 것을
          봤다. 새로고침해야 바뀌었다. 짧은 주기로 다시 읽는 것과 손으로 새로 고치는 수단을
          함께 둔다 — 주기 갱신이 실패하는 환경에서도 사용자가 막히지 않아야 한다.
        */}
        {onRefresh && (
          <button className="btn sm" onClick={onRefresh} aria-label="세션 상태 새로 고침">
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

          연타로 세션이 둘 만들어졌을 때 목록에 구분 불가능한 배너가 두 줄로 떴다. 어느
          것이 어느 실행인지 알 수 없어 사용자는 아무거나 골라야 했다.

          세션 짧은 ID 를 쓴다 — 시작 시각은 세션 뷰에 없고, 짧은 ID 로도 두 줄을 가릴 수
          있다. 사용자에게 보이는 오류 문구에 식별자를 넣지 않는 규칙(FR-135)은 **오류
          문구**에 대한 것이며, 여기는 사용자가 골라야 하는 목록이므로 구분자가 필요하다.
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
            className="row"
            style={{ gap: "12px", flexWrap: "wrap" }}
          >
            <span className="line" style={{ flex: 1 }}>{label}</span>
            {asking ? (
              <>
                <span className={saved ? "muted" : "fail-ink"}>
                  {saved
                    ? `${s.test_id ?? "테스트"} 로 저장돼 있습니다. 이 작업 창만 닫습니다.`
                    : `Step ${s.steps.length}개가 사라집니다. 정말 버릴까요?`}
                </span>
                <button
                  className={`btn sm${saved ? "" : " danger"}`}
                  onClick={() => onDiscard?.(s.session_id)}
                >
                  {saved ? "닫기" : "버리기"}
                </button>
                <button className="btn sm" onClick={() => setConfirming(null)}>
                  취소
                </button>
              </>
            ) : (
              <>
                {onResume && (
                  <button className="btn sm primary" onClick={() => onResume(s)}>
                    이어서 보기
                  </button>
                )}
                {onDiscard && (
                  <button className="btn sm" onClick={() => setConfirming(s.session_id)}>
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
