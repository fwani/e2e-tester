import {
  TESTS_DELETE_REVERTIBLE,
  TESTS_RESTORE_HINT,
  deleteTestsConfirm,
} from "../lib/wording";
import type { TrashedTest } from "../api/client";

import { Button } from "../ui/Button";
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
      className="bg-warn-t border border-warn-line rounded-base font-sans text-[13px] leading-[1.4] flex items-center gap-[10px] py-s2 px-s3 mb-[10px]"
    >
      <span className="strong-sm">{deleteTestsConfirm(names)}</span>
      {/* 012 가 프로젝트 삭제에서 정한 것과 같다 — 되돌릴 수 있다는 사실을 확인 시점에
          말한다. 011 의 `BULK_DELETE_IRREVERSIBLE` 과 정반대 자리다. */}
      <span className="why">{TESTS_DELETE_REVERTIBLE}</span>
      <div className="spacer" />
      {/* 돌아가기가 기본이다 — 포커스를 여기에 둔다. */}
      <Button size="sm" onClick={onCancel} disabled={busy} autoFocus>
        돌아가기
      </Button>
      <Button
        data-test-bulk-confirm-run
        size="sm" variant="danger"
        onClick={onConfirm}
        disabled={busy} >
        지우기
      </Button>
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
      className="bg-warn-t border border-warn-line rounded-base py-[10px] px-s3 mb-[10px]"
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
      <details open className="mt-[6px]">
        <summary className="font-sans text-[11px] leading-[1.4] text-ink-3 cursor-pointer">
          옮긴 자리 {trashed.length}곳
        </summary>
        {trashed.map((t) => (
          <div
            key={t.id}
            className="font-sans text-[11px] leading-[1.4] text-ink-3 font-mono mt-[2px] break-all"
          >
            {t.trashed_to}
          </div>
        ))}
      </details>
      <div className="font-sans text-[11px] leading-[1.4] text-ink-3 mt-[6px]">
        {TESTS_RESTORE_HINT}
      </div>
      <button className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken mt-[6px]" onClick={onDismiss}>
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
      className="bg-warn-t border border-warn-line rounded-base font-sans text-[13px] leading-[1.4] flex items-center gap-[10px] py-s2 px-s3 mb-[10px]"
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
      {/*
        「왜 못 누르는가」를 말할 자리가 없다 — **이 띠는 고른 것이 1개 이상일 때만
        그려지기 때문이다** (UC-013-02 · SC-627). 0개일 때의 안내를 여기에 두면 닿을 수
        없는 가지가 된다.
      */}
      <Button data-test-bulk-delete size="sm" variant="danger" onClick={onDelete} disabled={busy}>
        선택한 항목 삭제
      </Button>
    </div>
  );
}
/**
 * 번호 정리 확인 (2026-09-10 사용자 보고 2번).
 *
 * **삭제와 같은 무게로 묻는다.** 식별자는 사용자가 git 에 커밋해 보관하는 자산의
 * 이름이고 (헌법 원칙 V), 이 조작은 그것을 여러 개 한꺼번에 바꾼다. 되돌리는 조작은
 * 없다 — 다시 정리해도 옛 번호로 돌아가지 않는다. 그 사실을 확인 시점에 말한다.
 *
 * **걸러 보기와 무관하다는 것을 여기서 말한다.** 조작이 목록 조작 줄에 있으므로 「지금
 * 보이는 것만」으로 읽힐 수 있는데, 실제 대상은 프로젝트 전체다.
 *
 * 관용어는 복수 삭제와 같다 — 겹침 대화상자를 쓰지 않고 목록 바로 위에서 묻는다.
 */
export function RenumberConfirm({
  total,
  busy,
  onConfirm,
  onCancel,
}: {
  total: number;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      data-renumber-confirm
      role="status"
      className="bg-warn-t border border-warn-line rounded-base font-sans text-[13px] leading-[1.4] flex items-center gap-[10px] py-s2 px-s3 mb-[10px]"
    >
      <span className="strong-sm">
        테스트 {total}개의 번호를 001부터 다시 붙일까요?
      </span>
      <span className="why">
        그룹 접두어와 순서는 그대로입니다. 지금 보이는 것만이 아니라 프로젝트 전체가
        대상이며, 되돌리는 조작은 없습니다.
      </span>
      <div className="spacer" />
      {/* 돌아가기가 기본이다 — 포커스를 여기에 둔다. */}
      <Button size="sm" onClick={onCancel} disabled={busy} autoFocus>
        돌아가기
      </Button>
      <Button
        data-renumber-confirm-run
        size="sm" variant="danger"
        onClick={onConfirm}
        disabled={busy} >
        번호 정리
      </Button>
    </div>
  );
}
/**
 * 번호 정리 결과 (2026-09-10 사용자 보고 2번).
 *
 * **자동으로 사라지지 않는다.** 어느 식별자가 어디로 갔는지는 사용자가 자기 저장소·
 * 문서·CI 설정에서 찾아 고쳐야 하는 정보다 — 토스트로 흘려 보내면 그 일을 할 수 없다
 * (`TrashedTestsNotice` 가 옮긴 자리를 남기는 것과 같은 이유다).
 */
export function RenumberedNotice({
  result,
  onDismiss,
}: {
  result: { renumbered: { from_id: string; to_id: string; name: string }[]; unchanged: number };
  onDismiss: () => void;
}) {
  const changed = result.renumbered.length;
  return (
    <div
      data-renumbered-notice
      role="status"
      className={`${changed === 0 ? "bg-warn-t border border-warn-line rounded-base" : "bg-run-t border border-run rounded-base"} py-[10px] px-s3 mb-[10px]`}
    >
      <div className="strong-sm">
        {changed === 0
          ? `번호는 이미 정리되어 있었습니다 (${result.unchanged}개).`
          : `${changed}개의 번호를 바꿨습니다. ${result.unchanged}개는 제자리였습니다.`}
      </div>
      {changed > 0 && (
        <details open className="mt-[6px]">
          <summary className="font-sans text-[11px] leading-[1.4] text-ink-3 cursor-pointer">
            바뀐 식별자 {changed}건
          </summary>
          {result.renumbered.map((m) => (
            <div key={m.from_id} className="font-sans text-[11px] leading-[1.4] text-ink-3 font-mono mt-[2px]">
              {m.from_id} → {m.to_id} · {m.name}
            </div>
          ))}
        </details>
      )}
      {changed > 0 && (
        <div className="font-sans text-[11px] leading-[1.4] text-ink-3 mt-[6px]">
          정의 파일과 실행 산출물이 함께 옮겨졌습니다. 저장소에 옛 식별자를 적어 둔 곳이
          있으면 함께 고치세요.
        </div>
      )}
      <button className="h-[28px] inline-flex items-center px-[10px] border-0 rounded-base hover:bg-sunken mt-[6px]" onClick={onDismiss}>
        확인했습니다
      </button>
    </div>
  );
}
