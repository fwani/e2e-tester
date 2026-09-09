import { deleteManyConfirm } from "../../lib/wording";
import type { WorkbenchStep } from "./model";

/**
 * 복수 삭제 확인 — **목록 바로 아래에서** 묻는다 (011 FR-384 · UC-011-18).
 *
 * 문구에 **개수와 범위를 둘 다** 담는다. 개수만 있으면 「11개」가 어느 11개인지 알 수 없고,
 * 범위만 있으면 그 사이에서 고르지 않은 것이 몇 개인지 알 수 없다. 「이 뒤 전부」는 연속
 * 구간이라 둘이 일치하지만, 체크로 고른 것은 띄어져 있을 수 있어 **다른 사실**이다.
 *
 * 겹침 대화상자를 쓰지 않는 것은 행 삭제 확인(`ConfirmDelete`)과 같은 근거다 —
 * 대상이 화면에서 사라지면 무엇을 지우려던 것인지 다시 확인해야 한다.
 *
 * **구현이 하나다.** 세션(일시정지·검토)과 편집이 같은 확인을 쓴다 — 두 벌이면 한쪽의
 * 문구가 개수만 말하거나 범위만 말하게 되고, 그것이 007 이 없앤 「같은 것을 보는 자리가
 * 둘」의 형태다.
 */
export function BulkDeleteConfirm({
  targets,
  steps,
  busy,
  onConfirm,
  onCancel,
}: {
  targets: string[];
  steps: WorkbenchStep[];
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const indices = steps.filter((s) => targets.includes(s.id)).map((s) => s.index);
  return (
    <div
      data-bulk-delete-confirm
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
      <span className="strong-sm">{deleteManyConfirm(indices)}</span>
      <div className="spacer" />
      <button className="btn sm" onClick={onCancel} disabled={busy}>
        돌아가기
      </button>
      <button
        data-bulk-delete-confirm-run
        className="btn sm danger"
        onClick={onConfirm}
        disabled={busy}
      >
        지우기
      </button>
    </div>
  );
}
