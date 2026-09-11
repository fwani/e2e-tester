/**
 * 세션 유실 안내 (T149). FR-041·FR-041c.
 *
 * **무엇이 보존됐고 지금 무엇을 할 수 있는지**를 말한다. "세션이 유실됐습니다" 만 알리면
 * 사용자는 작업이 사라진 줄 알고 처음부터 다시 시작한다 — 실제로는 Step 이 남아 있다.
 *
 * 허용되는 행동은 **저장과 처음부터 재실행뿐이다** (FR-041c). 이어서 실행과 편집은
 * 불가하므로 버튼을 회색으로 두지 않고 **아예 보여 주지 않는다** — 회색 버튼은 "곧 될
 * 것" 처럼 읽힌다.
 */

import { Button } from "../ui/Button";

export interface SessionLostBannerProps {
  reason: string;
  /** 보존된 Step 수. 0이면 저장할 것이 없다. */
  stepCount: number;
  busy?: boolean;
  onSave?: () => void;
  onRunFromStart?: () => void;
  onClose?: () => void;
}

export function SessionLostBanner({
  reason,
  stepCount,
  busy = false,
  onSave,
  onRunFromStart,
  onClose,
}: SessionLostBannerProps) {
  const hasSteps = stepCount > 0;

  return (
    <div
      role="alert"
      className="bg-fail-t border border-fail-line rounded-base p-[14px] flex flex-col gap-[10px]"
    >
      <div className="flex items-center gap-s2">
        <strong className="font-sans text-[13px] font-semibold leading-none text-fail">브라우저 세션이 유실됐습니다</strong>
        <span className="flex-1" />
        {onClose && (
          <Button size="sm" variant="quiet" onClick={onClose}>
            닫기
          </Button>
        )}
      </div>

      <p className="font-sans text-[13px] leading-[1.4] m-0 whitespace-pre-wrap">
        {reason}
      </p>

      <p className="font-sans text-[13px] leading-[1.4] m-0">
        {hasSteps ? (
          <>
            기록된 Step <strong>{stepCount}개</strong>는 보존됐습니다. 저장하거나 처음부터
            다시 실행할 수 있습니다.
          </>
        ) : (
          <>기록된 Step 이 없어 저장할 것이 없습니다. 처음부터 다시 시작하세요.</>
        )}
      </p>

      <p className="font-sans text-[11px] leading-[1.4] text-ink-3 m-0">
        이어서 실행과 Step 편집은 브라우저가 없어 할 수 없습니다.
      </p>

      <div className="flex items-center gap-s2">
        {hasSteps && onSave && (
          <button disabled={busy} onClick={onSave}>
            지금까지 저장
          </button>
        )}
        {onRunFromStart && (
          <Button disabled={busy} onClick={onRunFromStart}>
            처음부터 실행
          </Button>
        )}
      </div>
    </div>
  );
}
