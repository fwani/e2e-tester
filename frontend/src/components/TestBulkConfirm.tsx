import {
  NO_TEST_DELETE_SELECTION,
  TESTS_DELETE_REVERTIBLE,
  TESTS_RESTORE_HINT,
  deleteTestsConfirm,
} from "../lib/wording";
import type { TrashedTest } from "../api/client";

/**
 * 테스트 복수 삭제 확인 — **목록 바로 아래에서** 묻는다 (013 FR-430 · UC-013-04).
 *
 * ## 왜 `BulkDeleteConfirm` 을 쓰지 않는가
 *
 * 011 의 그 부품은 `deleteManyConfirm(indices)` 로 **Step 번호의 범위**를 말한다. 테스트는
 * **순서 없는 집합**이라 `index` 가 없고 「범위」가 성립하지 않는다 — 부르려면 가짜 인덱스를
 * 만들어 넣어야 한다.
 *
 * 그것이 007 이 없앤 결함의 거울상이다. 007 은 「같은 것을 보는 자리가 둘」을 없앴는데,
 * 여기서 억지로 한 부품에 넣는 것은 **다른 것을 한 자리에 욱여넣는** 반대 방향의 실수이고
 * 결과는 같다: 한쪽을 고치면 다른 쪽이 깨진다 (013 research R7).
 *
 * **관용어는 그대로 잇는다** — 겹침 대화상자를 쓰지 않고 목록 바로 아래에서 묻는다. 대상이
 * 화면에서 사라지면 무엇을 지우려던 것인지 다시 확인해야 하기 때문이다.
 */
export function TestBulkConfirm({
  names,
  busy,
  onConfirm,
  onCancel,
}: {
  names: string[];
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      data-test-bulk-confirm
      role="status"
      className="tint-warn line"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 12px",
        marginBottom: 10,
      }}
    >
      <span className="strong-sm">{deleteTestsConfirm(names)}</span>
      {/* 012 가 프로젝트 삭제에서 정한 것과 같다 — 되돌릴 수 있다는 사실을 확인 시점에
          말한다. 011 의 `BULK_DELETE_IRREVERSIBLE` 과 정반대 자리다. */}
      <span className="why">{TESTS_DELETE_REVERTIBLE}</span>
      <div className="spacer" />
      {/* 돌아가기가 기본이다 — 포커스를 여기에 둔다. */}
      <button className="btn sm" onClick={onCancel} disabled={busy} autoFocus>
        돌아가기
      </button>
      <button
        data-test-bulk-confirm-run
        className="btn sm danger"
        onClick={onConfirm}
        disabled={busy}
      >
        지우기
      </button>
    </div>
  );
}

/**
 * 무엇을 어디로 옮겼는지 (013 FR-437a·FR-437b · UC-013-05).
 *
 * **자동으로 사라지지 않는다.** 사라지면 되돌리는 방법이 함께 사라진다 — 012 가 프로젝트
 * 삭제에서 정한 것과 같은 규칙이다. 경로는 `mono` 로, 잘리지 않게 표시한다.
 */
export function TrashedTestsNotice({
  trashed,
  onDismiss,
}: {
  trashed: TrashedTest[];
  onDismiss: () => void;
}) {
  return (
    <div
      data-trashed-notice
      role="status"
      className="tint-warn"
      style={{ padding: "10px 12px", marginBottom: 10 }}
    >
      <div className="strong-sm">
        {trashed.length === 1
          ? `「${trashed[0]!.name}」을(를) 휴지통으로 옮겼습니다.`
          : `${trashed.length}개를 휴지통으로 옮겼습니다.`}
      </div>
      {/*
        기본은 **펼친 상태**다 (UC-013-05). 접어 두면 사용자가 되돌리는 방법을 못 본 채
        알림을 닫는다. 여러 개일 때 길어지므로 접을 수 있게만 해 둔다.
      */}
      <details open style={{ marginTop: 6 }}>
        <summary className="why" style={{ cursor: "pointer" }}>
          옮긴 자리 {trashed.length}곳
        </summary>
        {trashed.map((t) => (
          <div
            key={t.id}
            className="why mono"
            style={{ marginTop: 2, wordBreak: "break-all" }}
          >
            {t.trashed_to}
          </div>
        ))}
      </details>
      <div className="why" style={{ marginTop: 6 }}>
        {TESTS_RESTORE_HINT}
      </div>
      <button className="navlink" onClick={onDismiss} style={{ marginTop: 6 }}>
        확인했습니다
      </button>
    </div>
  );
}

/**
 * 고른 것들에 대한 조작 띠 (013 FR-427·FR-428 · UC-013-02).
 *
 * **고른 것이 0개면 이 띠를 그리지 않는다** — 늘 떠 있으면 복수 삭제를 쓰지 않는 사용자에게
 * 자리를 뺏는다 (SC-627). 그래서 「왜 못 누르는가」를 말할 대상도 없다: 조작 자체가 없다.
 */
export function TestSelectionBar({
  selectedCount,
  visibleCount,
  allVisibleSelected,
  busy,
  onSelectAllVisible,
  onClear,
  onDelete,
  extra,
}: {
  selectedCount: number;
  visibleCount: number;
  allVisibleSelected: boolean;
  busy: boolean;
  onSelectAllVisible: () => void;
  onClear: () => void;
  onDelete: () => void;
  /** 그룹 이동 등, 같은 선택을 쓰는 다른 조작 (013 US3). */
  extra?: React.ReactNode;
}) {
  return (
    <div
      data-test-selection-bar
      className="tint-warn line"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 12px",
        marginBottom: 10,
      }}
    >
      <span className="strong-sm">{selectedCount}개 선택됨</span>
      {/*
        **대상은 지금 화면에 보이는 것뿐이다** (FR-428 · SC-625). 걸러진 것까지 고르면
        사용자가 보지 못한 테스트가 삭제 대상이 된다.
      */}
      <button
        className="navlink"
        onClick={allVisibleSelected ? onClear : onSelectAllVisible}
        disabled={busy || visibleCount === 0}
      >
        {allVisibleSelected ? "선택 해제" : `보이는 것 전부 선택 (${visibleCount})`}
      </button>
      <div className="spacer" />
      {extra}
      <button
        data-test-bulk-delete
        className="btn sm danger"
        onClick={onDelete}
        disabled={busy}
        title={selectedCount === 0 ? NO_TEST_DELETE_SELECTION : undefined}
      >
        선택한 항목 삭제
      </button>
    </div>
  );
}
