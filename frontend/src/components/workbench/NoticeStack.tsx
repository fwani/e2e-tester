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

/**
 * 알림의 뜻 → 정본의 옅은 바탕 (`States.dc.html`).
 *
 * 008 전에는 배경·글자색을 여기서 직접 정했고 `#A32C13`·`#8A6A16` 은 **확정 디자인에
 * 없는 색**이었다. v2 의 알림은 옅은 바탕 + 같은 계열 경계이고 글자는 본문 잉크다 —
 * 문장을 색으로 소리치지 않는다. 무엇인지는 문장이 말한다.
 */
const TONE: Record<Notice["tone"], string> = {
  error: "tint-fail",
  warn: "tint-warn",
  info: "",
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
          className={`notice ${TONE[n.tone]}`.trimEnd()}
          style={{
            flex: "0 0 auto",
            height: "auto",
            minHeight: "var(--h-notice)",
            alignItems: "flex-start",
            padding: "8px 16px",
            gap: 12,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="strong-sm">{n.message}</div>
            {/*
              `nextAction` 이 별도 줄인 이유는 003 EC-004 다 — 문장에 뭉개면 "대상 앱에
              연결할 수 없습니다" 뒤에 와야 하는 "떠 있는지 확인하세요" 가 사라진다.
            */}
            {n.nextAction !== null && (
              <div className="why" style={{ marginTop: 4 }}>
                {n.nextAction}
              </div>
            )}
          </div>
          {n.action !== null && (
            <button
              className="btn sm"
              data-notice-action={n.action.actionId}
              onClick={() => onAct?.(n.action!.actionId)}
            >
              {n.action.label || ACTION_LABEL[n.action.actionId]}
            </button>
          )}
          {n.dismissible && (
            <button className="btn sm quiet" aria-label="알림 닫기" onClick={() => onDismiss?.(n.id)}>
              닫기
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
