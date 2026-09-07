/**
 * 알림 (007 T020 · data-model.md §4).
 *
 * 지금 배너는 화면마다 다른 자리에 있다 — `App` 은 화면 위, `SessionScreen` 은 헤더
 * 아래, `RunResult` 는 상단 띠 아래, `TestDefinition` 은 본문 안. 같은 성격의 알림이
 * 국면에 따라 다른 곳에 나타나면 사용자는 그것을 찾아야 한다.
 *
 * 007 은 **국면 띠 바로 아래** 한 자리로 모은다.
 *
 * `nextAction` 이 별도 칸인 이유는 003 EC-004 다 — 문자열로 뭉개면 "대상 앱에 연결할 수
 * 없습니다" 뒤에 와야 하는 "떠 있는지 확인하세요" 가 사라진다.
 *
 * `role` 을 모델이 정하는 이유는 지금 각 화면이 개별로 정해 같은 성격의 배너가 다른
 * role 을 갖기 때문이다 (ui-contract §7).
 */
import type { ActionId } from "../../lib/actions";
import { ACTION_LABEL } from "../../lib/wording";
import type { Notice } from "./model";

const INK = "#14130F";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

const TONE: Record<Notice["tone"], { background: string; color: string }> = {
  error: { background: "#FBEEEA", color: "#A83A22" },
  warn: { background: "#FFF9D6", color: "#8A6A16" },
  info: { background: "#FFFDF6", color: INK },
};

export interface NoticeStackProps {
  notices: Notice[];
  onAct?: (action: ActionId) => void;
  onDismiss?: (id: string) => void;
}

export function NoticeStack({ notices, onAct, onDismiss }: NoticeStackProps) {
  if (notices.length === 0) return null;
  return (
    <div data-workbench-notices>
      {notices.map((n) => (
        <div
          key={n.id}
          role={n.role}
          data-notice={n.id}
          style={{
            borderBottom: `3px solid ${INK}`,
            padding: "12px 24px",
            display: "flex",
            alignItems: "flex-start",
            gap: 12,
            ...TONE[n.tone],
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ font: `600 13.5px/1.5 ${SANS}` }}>{n.message}</div>
            {n.nextAction !== null && (
              <div style={{ font: `400 12.5px/1.5 ${SANS}`, marginTop: 4 }}>{n.nextAction}</div>
            )}
          </div>
          {n.action !== null && (
            <button
              className="secondary"
              data-notice-action={n.action.actionId}
              onClick={() => onAct?.(n.action!.actionId)}
            >
              {n.action.label || ACTION_LABEL[n.action.actionId]}
            </button>
          )}
          {n.dismissible && (
            <button className="ghost" aria-label="알림 닫기" onClick={() => onDismiss?.(n.id)}>
              닫기
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
