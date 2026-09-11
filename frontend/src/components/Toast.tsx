/**
 * 토스트 — **문서 흐름을 차지하지 않는 알림** (2026-09-10 사용자 결정).
 *
 * ## 왜 이것이 필요한가
 *
 * 「테스트 목록에서 알림이 한 줄 생겨서 테스트 목록 테이블이 아래로 내려가버린다.
 * 본 프로젝트의 모든 알림은 토스트로 변경하라」.
 *
 * 같은 결함이 세 번 보고됐다. 2026-09-09 에 `Workbench` 가, 2026-09-10 에 `App` 의
 * 오류 배너가 각각 고쳐졌지만 **화면마다 손으로 고쳤기 때문에** 남은 자리가 계속
 * 나왔다 — 목록의 내보내기 알림·진행 중 세션 띠·가져오기 완료 알림, 그리고 11개
 * 화면의 `<ErrorNotice>` 가 전부 문서 흐름 안에 있었다.
 *
 * 이 통로가 그 되풀이를 끝낸다. 알림을 그리는 화면은 **자리를 고르지 않는다.**
 *
 * ## 자리는 하나다
 *
 * 층은 `.toast-layer` 하나이고 뷰포트 오른쪽 위에 고정돼 있다 (`tokens.css`).
 * 화면마다 층을 따로 만들면 둘이 동시에 뜰 때 겹친다 — `App` 의 오류와 목록의
 * 내보내기 알림은 실제로 함께 뜰 수 있다. 그래서 층은 **모듈 하나가 소유하고**
 * 모든 토스트가 그리로 들어간다. 층은 `flex-direction:column` 이므로 쌓인다.
 *
 * 층을 `App` 이 그리게 하지 않고 여기서 필요할 때 만드는 이유는, 화면을 낱개로
 * 렌더하는 검사에서도 토스트가 보여야 하기 때문이다 (`App` 없이 `TestList` 만 그리는
 * 검사가 여럿이다).
 */
import type { ReactNode } from "react";
import { createPortal } from "react-dom";

import { Button } from "../ui/Button";
import { Toast as UiToast, TOAST_LAYER_CLASSES } from "../ui/Notice";
import type { NoticeTone } from "../ui/Notice";

/** 알림의 뜻 → 정본의 옅은 바탕. `NoticeStack` 의 `TONE` 과 같은 값이다. */
export type ToastTone = "error" | "warn" | "info" | "plain";

/** 결말 어휘 → `ui/Notice` 의 `tone`. 정본의 `.tint-*` 가 여기로 왔다 (015 T073). */
const TINT: Record<ToastTone, NoticeTone> = {
  error: "fail",
  warn: "warn",
  info: "run",
  plain: "default",
};

/** 층을 찾는 표식. 클래스가 아니라 속성으로 찾는다 — 형태는 정본이 정한다. */
const LAYER_ATTR = "data-toast-layer";

/**
 * 하나뿐인 알림 층. 없으면 만든다.
 *
 * 층 자체는 `pointer-events:none` 이라 비어 있을 때 아래를 막지 않는다
 * (`tokens.css` 의 `.toast-layer`).
 */
function toastLayer(): HTMLElement {
  const found = document.querySelector<HTMLElement>(`[${LAYER_ATTR}]`);
  if (found !== null) return found;

  const made = document.createElement("div");
  made.setAttribute(LAYER_ATTR, "");
  // 015 T073 — 정본 `.toast-layer` 가 `ui/Notice` 로 왔다. **자리를 두 곳에서 정하지
  // 않는다** — 포털 대상은 명령형으로 만들 수밖에 없으므로 상수를 꺼내 쓴다.
  made.className = TOAST_LAYER_CLASSES;
  document.body.appendChild(made);
  return made;
}

export interface ToastProps {
  /** 무엇인지. 바탕색만 정하고 문장을 대신하지 않는다. */
  tone?: ToastTone;
  /**
   * 닫는 길. `undefined` 면 닫기 버튼을 그리지 않는다.
   *
   * **오류에는 반드시 준다.** 오류는 스스로 사라지지 않으므로 (`NoticeStack` 의
   * `LINGER_MS`), 닫기가 없으면 화면에 영원히 남는다.
   */
  onDismiss?: () => void;
  /** 검사와 실측이 이 토스트를 집을 표식 (`data-export-notice` 등). */
  mark?: string;
  /**
   * 낭독기가 이것을 어떻게 다루는가. 오류는 `alert`, 나머지는 `status` 다
   * (`NoticeStack` 과 같은 규칙 — 같은 성격의 알림이 다른 role 을 갖지 않는다).
   */
  role?: "alert" | "status";
  children: ReactNode;
}

/**
 * 알림 하나를 토스트 층에 띄운다.
 *
 * 부르는 쪽은 조건부로 그리기만 하면 된다 — `{error !== null && <Toast …>}`.
 * 사라지는 것은 상태를 가진 쪽이 정한다 (여기는 자리와 형태만 맡는다).
 */
export function Toast({ tone = "plain", onDismiss, mark, role, children }: ToastProps) {
  const tint = TINT[tone];
  const speak = role ?? (tone === "error" ? "alert" : "status");

  return createPortal(
    <UiToast tone={tint} role={speak} {...(mark === undefined ? {} : { [mark]: "" })}>
      <div className="flex-1 min-w-0">{children}</div>
      {onDismiss !== undefined && (
        <Button size="sm" variant="quiet" aria-label="알림 닫기" onClick={onDismiss}>
          닫기
        </Button>
      )}
    </UiToast>,
    toastLayer(),
  );
}
