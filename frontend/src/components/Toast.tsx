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
import { useToastDismiss } from "../ui/useToastDismiss";

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
   * 닫는 길. `undefined` 면 **세 퇴장이 전부 없다** — 닫기 단추도, 밀어내기도,
   * 5초 뒤 사라짐도. 닫을 곳이 없는데 사라지면 상태만 남고 알림이 없어진다.
   *
   * 진행 중 상태를 알리는 토스트만 이것을 비운다 (「돌고 있습니다」). 나머지는 준다.
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
 *
 * ## 2026-09-11 — 퇴장은 이 부품의 것이다 (사용자 결정)
 *
 * 이전에는 「사라지는 것은 상태를 가진 쪽이 정한다」였고, 그래서 **아무도 정하지
 * 않았다** — 11개 화면이 `onDismiss` 만 주고 시간은 주지 않았으므로 오류 토스트는
 * 손으로 닫을 때까지 떠 있었다. 그것이 「toast 가 계속 떠있음」의 실체다.
 *
 * 자리를 한 곳으로 모은 것과 같은 이유로 **퇴장도 한 곳으로 모은다**. 화면은 「이
 * 알림이 있는가」만 말하고, 5초·밀어내기·`×` 는 `useToastDismiss` 가 맡는다.
 */
export function Toast({ tone = "plain", onDismiss, mark, role, children }: ToastProps) {
  const tint = TINT[tone];
  const speak = role ?? (tone === "error" ? "alert" : "status");
  const exit = useToastDismiss(onDismiss);

  return createPortal(
    <UiToast
      tone={tint}
      role={speak}
      style={exit.style}
      {...exit.handlers}
      {...(mark === undefined ? {} : { [mark]: "" })}
    >
      <div className="flex-1 min-w-0">{children}</div>
      {onDismiss !== undefined && <DismissButton onClick={onDismiss} />}
    </UiToast>,
    toastLayer(),
  );
}

/**
 * `×`. 2026-09-11 사용자 결정 — 「x 가 가능해야함」.
 *
 * 글자 「닫기」였다. 토스트는 뜻을 말하는 한두 줄이고, 그 옆의 낱말 하나가 문장만큼
 * 무겁게 보였다. 맥의 알림과 같은 개념으로 자리를 잡은 이상 (2026-09-10) 닫는 것도
 * 같은 모양이다 — 눈에 띄지 않는 `×`.
 *
 * **이름은 남는다.** `aria-label="알림 닫기"` 가 낭독기가 듣는 것이고, 검사도 이것으로
 * 집는다 — 모양이 글자에서 기호로 바뀌어도 「닫는 길이 있는가」라는 질문은 그대로다.
 */
export function DismissButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      size="icon"
      variant="ghost"
      aria-label="알림 닫기"
      title="닫기"
      onClick={onClick}
      layout="shrink-0"
    >
      ×
    </Button>
  );
}
