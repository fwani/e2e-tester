/**
 * 편집 경고 배너 (T104). FR-040b.
 *
 * `edit_warning` 이벤트와 편집 응답의 `edit_warnings` 가 같은 목록이므로 표시도 한
 * 컴포넌트에서 한다. 두 곳에서 그리면 같은 경고가 두 번 보인다.
 *
 * **경고는 사용자가 무엇을 해야 하는지까지 말한다.** "적용되지 않았다"만 알리면 사용자는
 * 무엇이 잘못됐는지는 알지만 어떻게 되돌리는지는 모른다 — FR-040d 가 정한 수단(직접 동작
 * 추가·이 Step부터 실행)을 함께 안내한다.
 */

export interface EditWarningBannerProps {
  warnings: string[];
  /** 닫기. 경고는 사용자가 인지하면 사라져도 되는 정보다. */
  onDismiss?: () => void;
}

export function EditWarningBanner({ warnings, onDismiss }: EditWarningBannerProps) {
  if (warnings.length === 0) return null;

  return (
    <div
      role="status"
      style={{
        border: "3px solid var(--warn)",
        background: "var(--warn-tint)",
        padding: "10px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div className="row" style={{ gap: 8 }}>
        <strong style={{ fontSize: 13 }}>
          ⚠ 이 편집은 현재 화면 상태에 적용되지 않았습니다
        </strong>
        <span className="spacer" />
        {onDismiss && (
          <button className="ghost" onClick={onDismiss} aria-label="경고 닫기">
            닫기
          </button>
        )}
      </div>
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12.5, lineHeight: 1.6 }}>
        {warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
      <p className="muted" style={{ margin: 0, fontSize: 12 }}>
        화면을 원하는 상태로 만드는 방법: <strong>직접 동작 추가</strong>로 조작하거나,
        <strong> 이 Step부터 실행</strong>으로 원하는 지점부터 다시 밟습니다.
      </p>
    </div>
  );
}
