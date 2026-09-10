/**
 * 실시간 연결 끊김 안내 (UX U-01 후속).
 *
 * 워크스루에서 사용자가 겪은 것: 실제 브라우저에서 5개를 조작했는데 화면은 끝까지
 * "아직 기록된 Step 이 없습니다" 였다. **서버에는 5개가 다 기록돼 있었다.** 화면에는
 * 연결이 끊겼다는 표시도, 재연결 수단도, 아무 경고도 없었다 — 조용히 실패했다.
 *
 * 프록시 설정(`vite.config.ts` 의 `ws`)은 고쳤지만 **조용히 실패하는 구조 자체**는
 * 그대로였다. 이 배너가 그것을 막는다.
 *
 * 문구가 반드시 말해야 하는 것은 **기록이 계속되고 있다**는 사실이다. 그 말이 없으면
 * 사용자는 지금까지 한 조작이 날아간 줄 알고 처음부터 다시 한다.
 */

import { Button } from "../ui/Button";

export interface LiveConnectionBannerProps {
  /** 즉시 재연결. 자동 재시도를 기다리지 않는다. */
  onReconnect?: () => void;
}

export function LiveConnectionBanner({ onReconnect }: LiveConnectionBannerProps) {
  return (
    <div
      role="status"
      className="tint-warn"
      style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 12 }}
    >
      <span style={{ flex: 1 }}>
        <strong>실시간 연결이 끊겼습니다.</strong> 조작한 내용은 서버에 계속 기록되고
        있습니다 — 화면만 멈춰 있습니다. 자동으로 다시 연결하는 중입니다.
      </span>
      {onReconnect && (
        <Button size="sm" onClick={onReconnect}>
          지금 다시 연결
        </Button>
      )}
    </div>
  );
}
