/**
 * 작업 화면의 알림 목록 — 화면이 계산한 사실들을 **알림 부품에 넘긴다.** 017 Phase 10 · T101.
 *
 * ## 이 파일이 더는 하지 않는 것
 *
 * 017 까지 이 파일은 자리(층 안)·시간(5초 타이머)·숨김 목록(지문)·밀어내기를 직접 들고 있었다.
 * 그 넷은 이제 `ui/Toast` 와 그 부품이 갖는다 — 층은 앱 뿌리에 하나이고, 머무는 시간과 밀어내기는
 * 부품의 규칙이다 (research R6 개정). 남는 일은 **무엇을 말할지 정하는 것**뿐이다.
 *
 * ## 뜻은 그대로다
 *
 * - 오류는 `alert`, 나머지는 `status` 로 낭독한다 (015 규율 · 같은 성격의 알림이 다른 role 을 갖지 않는다).
 * - `nextAction` 은 **별도 줄**이다 (003 EC-004) — 문장에 뭉개면 「대상 앱에 연결할 수 없습니다」 뒤에
 *   와야 하는 「떠 있는지 확인하세요」가 사라진다.
 * - **닫기는 모든 알림에 있다** (2026-09-09). `dismissible` 은 모델에 남는다 — 지우는 순간 바깥 상태까지
 *   비울 대상인지를 구별하고, 그 판정은 `onDismiss` 를 받는 화면이 갖는다.
 */
import { Button } from "../../ui/Button";
import { Toast } from "../../ui/Toast";
import type { ToastTone } from "../../ui/Toast";
import { ACTION_LABEL } from "../../lib/wording";
import type { ActionId } from "../../lib/actions";
import type { Notice } from "./model";

/** 알림의 뜻 → 화면 어휘. 정본 바탕으로 옮기는 일은 부품이 한다. */
const TONE: Record<Notice["tone"], ToastTone> = {
  error: "error",
  warn: "warn",
  info: "info",
};

export interface NoticeStackProps {
  notices: Notice[];
  onAct?: (action: ActionId) => void;
  onDismiss?: (id: string) => void;
}

export function NoticeStack({ notices, onAct, onDismiss }: NoticeStackProps) {
  return (
    <>
      {notices.map((n) => (
        <Toast
          key={n.id}
          tone={TONE[n.tone]}
          role={n.role === "alert" ? "alert" : "status"}
          // 검사·실측이 알림을 집는 통로 — 옛 묶음이 내보내던 것과 **같은 모양**이다 (FR-005).
          attrs={{ "data-notice": n.id }}
          onDismiss={() => onDismiss?.(n.id)}
        >
          <div className="flex items-start gap-s3">
            <div className="flex-1 min-w-0">
              <div className="font-sans text-[14px] font-semibold leading-none">{n.message}</div>
              {n.nextAction !== null && (
                <div className="font-sans text-[12px] leading-[1.4] font-normal text-ink-3 mt-s1">
                  {n.nextAction}
                </div>
              )}
            </div>
            {n.action !== null && (
              <Button
                size="sm"
                data-notice-action={n.action.actionId}
                onClick={() => onAct?.(n.action!.actionId)}
              >
                {n.action.label || ACTION_LABEL[n.action.actionId]}
              </Button>
            )}
          </div>
        </Toast>
      ))}
    </>
  );
}
