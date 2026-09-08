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
      className="tint-fail"
      style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}
    >
      <div className="row" style={{ gap: 8 }}>
        <strong className="strong-sm fail-ink">브라우저 세션이 유실됐습니다</strong>
        <span className="spacer" />
        {onClose && (
          <button className="btn sm quiet" onClick={onClose}>
            닫기
          </button>
        )}
      </div>

      <p className="line" style={{ margin: 0, whiteSpace: "pre-wrap" }}>
        {reason}
      </p>

      <p className="line" style={{ margin: 0 }}>
        {hasSteps ? (
          <>
            기록된 Step <strong>{stepCount}개</strong>는 보존됐습니다. 저장하거나 처음부터
            다시 실행할 수 있습니다.
          </>
        ) : (
          <>기록된 Step 이 없어 저장할 것이 없습니다. 처음부터 다시 시작하세요.</>
        )}
      </p>

      <p className="why" style={{ margin: 0 }}>
        이어서 실행과 Step 편집은 브라우저가 없어 할 수 없습니다.
      </p>

      <div className="row" style={{ gap: 8 }}>
        {hasSteps && onSave && (
          <button disabled={busy} onClick={onSave}>
            지금까지 저장
          </button>
        )}
        {onRunFromStart && (
          <button className="secondary" disabled={busy} onClick={onRunFromStart}>
            처음부터 실행
          </button>
        )}
      </div>
    </div>
  );
}
