/**
 * 알림(토스트) — 흐름을 차지하지 않고 잠깐 떠서 사실 하나를 말한다. 017 Phase 10 · T099.
 *
 * 출처: shadcn base/toast @ shadcn 4.21.x (style base-nova) · `@base-ui/react` 1.8.x — 구조(Provider ·
 * Portal · Viewport · Root · 관리자)와 `data-slot` 을 가져오고, 클래스는 정본 `.notice.float.toast` ·
 * `.toast-layer` 로 옮겼다. 원본의 `bg-popover`·`shadow-lg`·`rounded-lg`·`focus-visible:ring-[3px]` ·
 * 전환·아이콘은 남지 않는다.
 *
 * ## 무엇을 대신하는가
 *
 * 017 까지 알림은 손으로 만든 네 조각이었다 — `ui/Notice` 의 `Toast`·`ToastLayer`·`TOAST_LAYER_CLASSES`,
 * `components/Toast` 의 포털 층, `ui/useToastDismiss` 의 5초·밀어내기, `workbench/NoticeStack` 의 타이머.
 * 이 부품 하나가 그 넷을 갖는다 (research R6 개정).
 *
 * ## 자리 — **아래**다 (N-02)
 *
 * 017 의 자리는 오른쪽 **위**였고, 작업 화면에서 그 자리는 Step 패널의 머리 줄과 첫 행들이다. 순회가
 * 그것을 실제로 잡았다(`covered button{전부 고르기} by div{먼저 저장해야…}`). 그래서 아래로 내린다.
 * 최종 자리(오른쪽 아래 · 아래 가운데)는 **순회가 판정한다** — layout-contract-v3 L2.
 *
 * ## 공급자가 없으면 스스로 갖는다
 *
 * 앱은 뿌리에 `<Toaster>` 하나를 둔다. 그러면 알림이 **한 층·한 상한**으로 모인다. 그런데 검사는
 * 화면을 단독으로 그리고(`render(<TestList …/>)`), 그때도 알림은 보여야 한다 — 지금 테스트 13개가
 * 그 위에 서 있다. 공급자가 위에 없으면 알림이 **자기 공급자와 층을 갖는다.** 모양·퇴장·자리의 정의는
 * 이 파일 하나에 있으므로 「부품 정의는 하나」(FR-003)는 지켜진다.
 */
import { Toast as ToastPrimitive } from "@base-ui/react/toast";
import { createContext, useContext, useEffect, useRef } from "react";
import type { ComponentProps, ReactNode } from "react";
import { createPortal } from "react-dom";

import { Button } from "./Button";
import { cn } from "./cn";
import { NOTICE_TINT } from "./Notice";
import type { NoticeTone } from "./Notice";
import { Tooltip } from "./Tooltip";

/** 머무는 시간. 뜻에 따라 다르지 않다 (2026-09-11 사용자 결정). */
export const TOAST_LINGER_MS = 5000;

/** 동시에 보이는 수. 넘친 것은 `data-limited` 를 받아 화면을 잠식하지 않는다 (FR-034). */
export const TOAST_LIMIT = 3;

/**
 * 층의 자리 — **왼쪽 아래, 바닥에서 88px**. 바꾸는 곳은 이 상수 하나다 (layout-contract-v3 L2).
 *
 * ## 자리는 **재서** 정했다 (2026-09-16 · 계약 T-2 「기본값부터 놓고 순회로 잰다」)
 *
 * 모서리를 하나 고쳐 순회를 돌리는 데 6분인데, 눈대중으로 고른 셋이 저마다 **다른 폭에서 다른
 * 조작을** 덮었다 — 작업 화면은 뷰포트의 **네 가장자리가 모두 조작**이기 때문이다(오른쪽 Step 패널 ·
 * 아래 AI 대화 칸 · 위 국면 띠). 그래서 알림을 그리지 않고 사각형만 계산해 후보 전부를 한 번에 쟀다
 * (화면 7 × 폭 4 · 순회와 같은 **가운데 점** 판정 · `scratchpad/probe_toast_spots.py`).
 *
 * | 자리 | 덮는 조작 |
 * |---|---|
 * | 오른쪽 **아래** (부품 기본값) | **60** — 1280 의 Step 패널 바닥 · 넓은 창의 「AI 지시문」 · 「기록 멈추기」 |
 * | 오른쪽 **위** (017 자리) | **58** — Step 패널 머리 줄의 「전부 고르기」 등 · **N-02** |
 * | 아래 가운데 | **10** — 1440·1920 의 「AI 에게 말하기」 |
 * | 위 가운데 | **7** |
 * | **왼쪽 아래** (지금) | **0** — 바닥에서 64px 이상일 때 |
 *
 * **눈대중으로 고른 두 자리가 실측에서 가장 나빴다.** 「기본값이니 오른쪽 아래」가 60 이고,
 * 아무도 말하지 않은 왼쪽 아래가 0 이다 — 자리는 고를 것이 아니라 잴 것이다.
 *
 * **88px 인 이유**: 바닥에서 16~48px 는 Step 상세 판의 「저장」을 덮고(1440), 64·88·120px 는 모두
 * 깨끗하다. 그 **띠의 가운데**를 잡았다 — 가장자리를 잡으면 배치가 조금만 움직여도 다시 덮는다.
 * 아래 가운데는 **64px 한 점에서만** 깨끗했다(48·88 은 덮는다). 1280 에서 Step 행과 행 **사이**를
 * 지나가는 우연이라 쓰지 않았다 — 목록이 스크롤되면 사라질 「깨끗함」이다.
 *
 * 88px 에 맞는 정본 토큰은 없다 — 정본 간격 눈금은 `--s-6: 32px` 에서 끝난다. 같은 상수의
 * `z-[60]`·`w-[min(…)]` 과 같은 자리의 임의값이고, 값의 근거는 위 실측이다.
 *
 * **잰 것은 알림 하나다.** 셋이 쌓이면 위로 자라므로 그 위는 사람이 본다 (quickstart H-9).
 *
 * 층은 포인터를 통과시키고 알림만 받는다 — 비어 있을 때 아래를 막지 않는다 (015 그대로).
 */
export const TOAST_VIEWPORT_CLASSES =
  "fixed bottom-[88px] left-s4 z-[60] w-[min(420px,calc(100vw-32px))] " +
  "flex flex-col gap-s2 " +
  "pointer-events-none [&>*]:pointer-events-auto";

/** 알림 하나의 모양. 정본 `.notice.float.toast` — 높이를 못 박지 않고 최소 높이만 지킨다. */
/*
  원본의 `outline-none` 은 **가져오지 않는다** (G-F 가 잡았다). 층과 알림은 초점을 받을 수 있고
  (Base UI 는 F6 으로 층에 초점을 준다), 정본에서 초점은 전역 윤곽선이 말한다 (S-14).
*/
const TOAST_CARD_CLASSES =
  "flex-none min-h-notice flex items-start gap-s2 px-s3 py-s2 " +
  "font-sans text-[12px] leading-none font-normal border rounded-chip shadow-e2";

/**
 * 화면이 말하는 뜻. **정본 바탕 이름이 아니다** — 화면은 「오류·경고·알림」으로 말하고 옮기는 일은
 * 부품이 한다 (015 의 층 나누기 · 옛 `components/Toast` 와 같은 어휘라 호출부가 바뀌지 않는다).
 */
export type ToastTone = "error" | "warn" | "info" | "plain";

/** 뜻 → 정본 `.tint-*`. 값은 `ui/Notice` 의 표에서 온다 — 표를 두 벌 두지 않는다. */
const TINT: Record<ToastTone, NoticeTone> = {
  error: "fail",
  warn: "warn",
  info: "run",
  plain: "default",
};

/** 알림에 실어 보내는 것. 문구가 아니라 **그릴 것**을 싣는다 — 화면이 버튼·링크를 넣기 때문이다. */
interface ToastData {
  readonly tone: ToastTone;
  readonly node: ReactNode;
  readonly mark?: string;
  readonly attrs?: Readonly<Record<string, string>>;
  readonly role: "alert" | "status";
  readonly dismiss?: () => void;
}

type ToastObject = ComponentProps<typeof ToastPrimitive.Root>["toast"];

/**
 * 위에 `<Toaster>` 가 있는가. 없으면 알림이 스스로 공급자를 갖는다 (머리주석).
 *
 * ## 모듈 관리자(`createToastManager`)를 쓰지 않는 이유 (2026-09-16 실측)
 *
 * 바깥에서 만든 관리자는 **그 순간 듣고 있는 쪽에게만 전달하고 쌓아 두지 않는다**
 * (`createToastManager` 는 `Set<listener>` 에 즉시 `emit` 한다). 공급자는 `useEffect` 에서 구독하는데
 * React 는 **자식 효과를 부모 효과보다 먼저** 돌린다 — 알림이 등록되는 순간 듣는 쪽이 아직 없어
 * 그대로 버려졌다(층이 비었다). 그래서 공급자 안에서 **훅으로 받은 관리자**에 등록한다. 그것은
 * 저장소에 바로 쓰므로 구독 시점과 무관하다.
 */
const InToaster = createContext(false);
const DockedToasts = createContext(false);

/**
 * 알림 하나를 관리자에 **등록**하고, 사라질 때 거둔다.
 *
 * 화면은 조건부로 그리기만 한다 — `{error !== null && <Toast …>}`. 그 선언을 이 자리가 명령형
 * 등록으로 옮긴다. 내용이 바뀌면 같은 알림을 고친다(`update`) — 새 알림으로 쌓지 않는다.
 */
function Register({
  data,
  dismissible,
  priority,
}: {
  data: ToastData;
  dismissible: boolean;
  priority: "low" | "high";
}) {
  const api = ToastPrimitive.useToastManager();
  const id = useRef<string | null>(null);
  const latest = useRef(data);
  latest.current = data;

  useEffect(() => {
    id.current = api.add({
      data: latest.current,
      priority,
      // 닫을 길이 없는 알림은 사라지지도 않는다 — 상태만 남고 알림이 없어지지 않게 (015 규율).
      timeout: dismissible ? undefined : 0,
      onClose: () => latest.current.dismiss?.(),
    });
    return () => {
      if (id.current !== null) api.close(id.current);
      id.current = null;
    };
    // 등록은 한 번이다. 내용 갱신은 아래 효과가 맡는다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (id.current !== null) api.update(id.current, { data });
    // `api` 는 공급자마다 안정적이다. 내용이 바뀔 때만 고친다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  return null;
}

/** 관리자가 들고 있는 알림들을 층에 그린다. */
function ToastList() {
  const { toasts } = ToastPrimitive.useToastManager();
  return (
    <>
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} />
      ))}
    </>
  );
}

function ToastCard({ toast }: { toast: ToastObject }) {
  const data = (toast.data ?? { tone: "plain", node: null }) as ToastData;
  const tint = TINT[data.tone];
  return (
    <ToastPrimitive.Root
      toast={toast}
      /*
        층이 아래 오른쪽에 있으므로 나가는 쪽은 오른쪽과 아래다 (015 의 「나가는 쪽으로만 민다」).

        **닫을 길이 없는 알림은 밀리지도 않는다.** 진행 중 상태를 말하는 알림(「돌고 있습니다」)을
        손으로 치울 수 있게 하면 상태는 그대로인데 알림만 사라진다 — 015 가 같은 이유로 시간과
        닫기 단추를 함께 뺐다. 미는 길만 열어 두면 그 규칙에 구멍이 난다.

        **끄는 것은 빈 배열이다** (2026-09-16 실측). 부품은 `swipeEnabled = 방향.length > 0` 으로
        판정하고, `swipeDirection` 을 **주지 않으면 기본값(`['down','right']`)으로 되돌아간다** —
        `undefined` 는 「끔」이 아니라 「기본」이다. 처음에 `undefined` 를 넘겼다가 닫을 길이 없는
        알림이 밀려 사라졌다.
      */
      swipeDirection={data.dismiss === undefined ? [] : ["right", "down"]}
      className={cn(TOAST_CARD_CLASSES, NOTICE_TINT[tint])}
      /*
        **낭독 역할은 우리가 정한다** (2026-09-16 실측). 부품의 기본은 `role="dialog"` 이고, 높은
        우선순위로 올리면 보이는 알림을 `aria-hidden` 으로 덮은 뒤 **제목·설명 문자열**을 숨은
        `role="alert"` 자리에서 읽는다. 우리 알림은 문구가 아니라 **그릴 것**(버튼·링크가 든 조각)을
        싣기 때문에 그 경로로는 읽을 내용이 비고, 알림 안의 조작도 역할로 찾을 수 없게 된다.
        그래서 낮은 우선순위로 두고 역할만 우리가 얹는다 — 015 부터의 규칙(오류는 `alert`,
        나머지는 `status`)이 그대로 산다.
      */
      role={data.role}
      data-slot="toast"
      // 표식은 **정본 바탕 이름**이다 — 옛 통로가 내보내던 값과 같다 (검사가 이것으로 집는다).
      data-tone={tint}
      {...(data.mark === undefined ? {} : { [data.mark]: "" })}
      {...(data.attrs ?? {})}
    >
      <div className="flex-1 min-w-0">{data.node}</div>
      {data.dismiss !== undefined && (
        <Tooltip content="알림 닫기" side="left">
          {/*
            **`aria-hidden` 을 되돌린다** (2026-09-16 실측). 원본 `Close` 는 층이 펼쳐져 있거나 그 단추에
            초점이 있을 때만 보조기술에 노출한다(`aria-hidden: !expanded && !hasFocus`) — 포인터를 올려야
            보이는 조작이라는 전제다. 이 제품의 규칙은 다르다: **닫는 길은 모든 알림에 있고 이름으로
            찾을 수 있다**(2026-09-09·09-11 사용자 결정 · `ToastDismiss` 가 그 이름으로 집는다).
            부품의 속성 병합은 `[기본값, 우리 속성, 단추 속성]` 순서라 우리 것이 이긴다.
          */}
          <ToastPrimitive.Close
            render={
              <Button
                size="icon"
                variant="ghost"
                aria-label="알림 닫기"
                aria-hidden={false}
                layout="shrink-0"
              />
            }
          >
            ×
          </ToastPrimitive.Close>
        </Tooltip>
      )}
    </ToastPrimitive.Root>
  );
}

/**
 * 알림이 뜨는 자리. **앱 뿌리에 하나** 둔다.
 *
 * `aria-live` 는 층이 갖는다 — 대화상자가 뒤쪽에 거는 `aria-hidden` 이 `aria-live` 요소를 건너뛴다
 * (017 research R6 ③). 그래서 대화상자가 열린 동안 뜬 알림도 낭독된다.
 */
export function Toaster({ children, docked = false }: { children?: ReactNode; docked?: boolean }) {
  return (
    <ToastPrimitive.Provider timeout={TOAST_LINGER_MS} limit={TOAST_LIMIT}>
      <DockedToasts.Provider value={docked}><InToaster.Provider value>{children}</InToaster.Provider></DockedToasts.Provider>
      {!docked && <ToastPrimitive.Portal>
        <ToastPrimitive.Viewport
          className={TOAST_VIEWPORT_CLASSES}
          data-slot="toast-viewport"
          data-toast-layer=""
          aria-live="polite"
        >
          <ToastList />
        </ToastPrimitive.Viewport>
      </ToastPrimitive.Portal>}
    </ToastPrimitive.Provider>
  );
}

/** Workbench notices occupy a dedicated row so they cannot cover Step tools or evidence. */
export function ToastDock() {
  const docked = useContext(DockedToasts);
  if (!docked) return null;
  return <ToastPrimitive.Viewport className="workspace-notice-dock" data-slot="toast-viewport" data-toast-layer="" aria-live="polite"><ToastList /></ToastPrimitive.Viewport>;
}

export interface ToastProps {
  /** 무엇인지. 바탕색만 정하고 문장을 대신하지 않는다. */
  readonly tone?: ToastTone;
  /**
   * 닫는 길. 없으면 **세 퇴장이 전부 없다** — 닫기 단추도, 밀어내기도, 시간도.
   * 진행 중 상태를 알리는 알림만 이것을 비운다 (「돌고 있습니다」).
   */
  readonly onDismiss?: () => void;
  /** 검사와 실측이 이 알림을 집는 표식 (`data-export-notice` 등). 값 없는 속성 하나. */
  readonly mark?: string;
  /**
   * **값이 있는** 표식들 (`data-notice="not-editable"` 등). 옛 통로는 남는 속성을 그대로 알림에
   * 흘려보냈고, 검사·실측이 그 통로로 알림을 집는다 (FR-005). `data-*` 만 받는다.
   */
  readonly attrs?: Readonly<Record<string, string>>;
  /** 낭독 우선순위를 가르는 자리 — 오류는 높다. */
  readonly role?: "alert" | "status";
  readonly children: ReactNode;
}

/**
 * 알림 하나를 띄운다. 부르는 쪽은 **조건부로 그리기만** 한다.
 *
 * 자리·퇴장·상한은 이 부품과 `<Toaster>` 가 갖는다 — 화면은 뜻과 내용만 말한다.
 */
export function Toast({ tone = "plain", onDismiss, mark, attrs, role, children }: ToastProps) {
  const inside = useContext(InToaster);
  const data: ToastData = {
    tone,
    node: children,
    mark,
    attrs,
    role: role ?? (tone === "error" ? "alert" : "status"),
    dismiss: onDismiss,
  };
  /*
    **높은 우선순위를 쓰지 않는다** (2026-09-16 실측). 부품은 `priority: "high"` 인 알림의 뿌리를
    `role="alertdialog"` 로 바꾸고 초점이 없는 동안 `aria-hidden` 으로 덮는다 — 낭독은 따로 하되 화면의
    조작은 보조기술에서 감추는 모델이다. 그러면 오류 알림 **안의 조작**(닫기·「실행 중인 세션 보기」)이
    역할로 찾아지지 않고, 그것을 찾는 기존 검사가 무너진다.

    낭독은 층이 이미 맡는다 — 층에 `aria-live="polite"` 가 있고 부품이 그 안에 `role="alert"` 자리를
    따로 둔다. 오류가 조용해지지 않으면서 조작은 그대로 남는다.
  */
  const priority = "low" as const;

  if (inside) {
    return <Register data={data} dismissible={onDismiss !== undefined} priority={priority} />;
  }

  // 공급자가 위에 없다 — 이 알림이 스스로 그린다. 다만 **층은 함께 쓴다** (아래 `sharedLayer`).
  return createPortal(
    <ToastPrimitive.Provider timeout={TOAST_LINGER_MS} limit={TOAST_LIMIT}>
      <ScopedToast data={data} dismissible={onDismiss !== undefined} priority={priority} />
    </ToastPrimitive.Provider>,
    sharedLayer(),
  );
}

/**
 * 공급자가 없을 때 알림들이 함께 쓰는 **하나뿐인 층**.
 *
 * 알림마다 층을 만들면 화면에 층이 여럿 생긴다 — 자리가 하나라는 규칙(FR-034 · `NoticesAreToasts`
 * 「층은 하나다」)이 깨진다. 그래서 층 **요소**는 모듈이 하나만 만들어 두고, 알림은 저마다의 공급자를
 * 그 안으로 보낸다. 자리·낭독·형태는 이 요소가 갖고, 안쪽 뷰포트는 자리를 차지하지 않는다
 * (`display: contents`). 옛 통로(`components/Toast`)가 하던 것과 같은 성질이다.
 */
function sharedLayer(): HTMLElement {
  const found = document.querySelector<HTMLElement>("[data-toast-layer]");
  if (found !== null) return found;

  const made = document.createElement("div");
  made.setAttribute("data-toast-layer", "");
  made.setAttribute("data-slot", "toast-viewport");
  made.setAttribute("aria-live", "polite");
  made.className = TOAST_VIEWPORT_CLASSES;
  document.body.appendChild(made);
  return made;
}

function ScopedToast({
  data,
  dismissible,
  priority,
}: {
  data: ToastData;
  dismissible: boolean;
  priority: "low" | "high";
}) {
  return (
    <>
      <Register data={data} dismissible={dismissible} priority={priority} />
      {/* 층은 `sharedLayer` 가 갖는다 — 여기서는 자리를 차지하지 않고 알림만 그린다. */}
      <ToastPrimitive.Viewport className="contents">
        <ToastList />
      </ToastPrimitive.Viewport>
    </>
  );
}
