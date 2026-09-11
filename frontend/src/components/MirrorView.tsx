/**
 * 대상 브라우저 미러 (T088 · 010 T027·T036·T045·T075). FR-047·FR-023b·FR-314~FR-320.
 *
 * ## 이 파일의 머리말이 010 에서 뒤집힌 자리
 *
 * 001 은 여기에 이렇게 적었다 — 「이 영역은 조작 대상이 아니다 (FR-047a). 사용자 입력을
 * 대상 브라우저로 전달하는 경로를 두지 않는다. **클릭·키 입력을 받아 전달하는 코드가 이
 * 파일에 없다는 것이 요구사항의 구현이다.**」
 *
 * 010 이 그 문장을 개정한다. 코드가 없다는 것으로 지키던 성질을 **국면이 지킨다.**
 *
 * - 조작 국면(직접 녹화·사람 인수·일시정지)에서는 이 영역이 조작을 받는다 (FR-314).
 * - 관찰 국면(실행 중·AI 수행 중)에서는 종전과 같이 전달하지 않는다 (FR-315).
 * - **그 판정을 이 컴포넌트가 하지 않는다** (FR-316). `controllable` 을 props 로 받는다.
 *   국면 × 조작 권한표(`lib/capabilities.ts`)가 정하고, 여기는 결과만 그린다. 컴포넌트가
 *   스스로 국면을 보면 표 밖에 판정이 하나 더 생기고, 둘이 갈리는 날 화면은 켤 수 있다고
 *   그리고 서버는 거절한다.
 *
 * **조작을 받는 상태인지가 화면에서 구분되어야 한다** (FR-319). 사용자가 클릭해 보고 나서
 * 알게 되어서는 안 된다 — 테두리와 상단 안내가 그 구분이다.
 *
 * 프레임은 유실 가능하다 — 마지막 프레임만 그리면 되고, 유실이 실행에 영향을 주지
 * 않는다 (FR-047b).
 */

import { useCallback, useRef, useState, type KeyboardEvent, type PointerEvent, type WheelEvent } from "react";

import type { CapabilityState } from "../lib/capabilities";
import {
  MIRROR_DEGRADED_WARNING,
  MIRROR_FOCUS_HINT,
  MIRROR_KEYS_GO_TO_TARGET,
  mirrorEmptyMessage,
  mirrorNotice,
  type ControlSurface,
  type MirrorNoticePhase,
} from "../lib/wording";
import { ImeBridge, isComposingKey } from "./mirror/ImeBridge";
import type { FrameGeometry, InputEvent } from "./mirror/useMirrorInput";
import {
  buttonNameOf,
  modifiersOf,
  pointerEventOf,
  wheelEventOf,
} from "./mirror/useMirrorInput";

import { Button } from "../ui/Button";
import { Chip } from "../ui/Chip";
/**
 * 미리보기의 국면 (005 재점검 U-04-b).
 *
 * `pausing`·`finished` 를 더한 이유는 이 둘이 `paused` 로 뭉개져 있었기 때문이다 —
 * 전이 중에도, 실행이 끝난 뒤에도 오버레이가 「일시정지」를 단정했고 같은 화면의
 * 배지는 「일시정지 중…」·「실행 종료」라고 말했다. 값이 없으면 화면이 구분할 수 없다.
 *
 * 문구는 `wording.ts` 가 소유한다 (005 T107 · 006 T084 · 010 T037).
 */
export type MirrorPhase = MirrorNoticePhase;

export interface MirrorViewProps {
  /** base64 JPEG. 아직 한 장도 못 받았으면 null. */
  frame: string | null;
  phase: MirrorPhase;
  /** 미러가 중단된 사유. 있으면 프레임 대신 이 사유를 보여준다 (FR-047e). */
  stoppedReason?: string | null;
  /** 1fps 스크린샷으로 강등된 사유 (research R3 폴백). */
  degradedReason?: string | null;
  /** 현재 표시 중인 탭. 여러 탭일 때 무엇을 보고 있는지 알려 준다 (FR-030f). */
  tabIndex?: number;
  /* ─── 010 미러 조작 ─────────────────────────────────────────────────── */
  /**
   * 「미러에서 조작하기」의 권한표 판정 (FR-316).
   *
   * **이 컴포넌트는 스스로 국면을 보지 않는다.** 표가 준 결과를 그대로 쓴다.
   * 주지 않으면 조작을 받지 않는다 — 모르는 것을 조작 가능으로 그리지 않는다.
   */
  control?: CapabilityState;
  /** 지금 조작이 어디서 이루어지는가 (data-model §6). 기본은 미러다 */
  surface?: ControlSurface;
  /** 지금 프레임이 실어 온 좌표 변환의 근거. 없으면 좌표를 보내지 않는다 (FR-333) */
  geometry?: FrameGeometry | null;
  /** 조작 사건 하나를 채널로 보낸다. 성공 응답을 기다리지 않는다 */
  onInput?: (event: InputEvent) => void;
  /**
   * 조작을 시도했지만 지금은 전달되지 않는다 (SC-516).
   *
   * 조용히 아무 일도 일어나지 않는 것을 막는다 — 사용자가 클릭했다는 사실을 화면이
   * 받아 이유를 말한다.
   */
  onBlockedAttempt?: (reason: string) => void;
  /** 실제 창으로 전환한다 (FR-353). **사용자가 누를 때만 일어난다** */
  onUseWindow?: () => void;
  /** 「실제 창에서 조작하기」의 권한표 판정 */
  useWindowCapability?: CapabilityState;
}

export function MirrorView({
  frame,
  phase,
  stoppedReason = null,
  degradedReason = null,
  tabIndex,
  control,
  surface = "mirror",
  geometry = null,
  onInput,
  onBlockedAttempt,
  onUseWindow,
  useWindowCapability,
}: MirrorViewProps) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  /**
   * 조합을 받는 요소 (FR-320 · T045).
   *
   * **미러 영역 자체가 초점을 갖는다.** 숨은 입력칸을 따로 두면 초점이 둘로 갈리고
   * 「지금 키가 어디로 가는가」가 화면에서 불분명해진다.
   *
   * 상태로 두는 이유는 `ImeBridge` 가 이 요소에 청취자를 붙여야 하기 때문이다 — `ref`
   * 로 두면 요소가 생겼을 때 브리지가 다시 붙지 않는다.
   */
  const [surfaceEl, setSurfaceEl] = useState<HTMLDivElement | null>(null);
  /**
   * 조합이 실제로 일어나는 요소 (FR-325~FR-327).
   *
   * **미러 영역은 `<div>` 라 IME 가 붙지 않는다.** 브라우저는 편집 가능한 요소에만
   * 조합을 건다 — `<input>`·`<textarea>`·`contenteditable`. 편집 불가 요소에 초점이
   * 있으면 `compositionstart` 자체가 오지 않고, 한글은 자모가 낱개 `keydown` 으로
   * 떨어진다. 그 자모를 서버가 한 글자씩 넣으므로 대상 화면에 「ㅈㅜㅁㅜㄴ」이 남는다 —
   * research R2 가 버리려던 바로 그 결과이며, 실제 사용자 보고가 그것이었다.
   *
   * 그래서 조합만 받는 **투명한 `<textarea>`** 를 미러 면 안에 둔다. 포인터는 받지
   * 않으므로(`pointerEvents: "none"`) 클릭은 그대로 화면으로 가고, 초점만 이쪽이
   * 갖는다. 미러 영역 **안**에 있으므로 초점 표시(`:focus-within`)와 「키가 어디로
   * 가는가」의 답은 여전히 미러 영역 하나다 — FR-320 이 금지한 「초점이 둘로 갈리는」
   * 상태가 되지 않는다.
   *
   * 화면에 글자가 남지 않는다. 조합이 끝나면 값을 비운다 (`clearIme`).
   */
  const imeRef = useRef<HTMLTextAreaElement | null>(null);
  /** 미러가 지금 키 입력을 받는가 (FR-320). 화면이 그 사실을 말해야 한다 */
  const [focused, setFocused] = useState(false);
  /**
   * 미러가 초점을 가져간다 (FR-320). **조합 요소로 준다** — 그래야 IME 가 붙는다.
   *
   * 조합 요소가 아직 없으면 미러 면이 받는다. 초점이 아무 데도 없는 것보다는 낫고,
   * 그 상태에서도 영문·숫자 키는 그대로 전달된다.
   */
  const takeFocus = () => {
    if (imeRef.current !== null) imeRef.current.focus({ preventScroll: true });
    else surfaceEl?.focus({ preventScroll: true });
  };
  /**
   * 조합 요소를 비운다. 확정된 글자는 **대상 브라우저**에 들어갔고 여기 남을 이유가 없다.
   *
   * 비우지 않으면 다음 조합의 `compositionupdate` 가 앞 글자를 포함한 문자열을 싣고,
   * `imeSetComposition` 이 이미 확정된 글자를 다시 조합 상태로 만든다.
   */
  const clearIme = () => {
    if (imeRef.current !== null) imeRef.current.value = "";
  };
  /**
   * 조작을 받는가. **표가 정한다** (FR-316).
   *
   * `enabled` 가 아니면 받지 않는다. `not_applicable` 은 그 국면의 조작이 아니라는 뜻
   * 이므로 역시 받지 않는다.
   */
  const controllable = control?.kind === "enabled" && surface === "mirror" && frame !== null;
  /** 왜 지금 조작할 수 없는가. 표가 이유를 갖고 있으면 그것을 쓴다 (SC-516). */
  const blockedReason =
    control === undefined
      ? "이 화면은 조작을 받도록 준비되지 않았습니다."
      : control.kind === "disabled"
        ? control.reason
        : control.kind === "not_applicable"
          ? control.note
          : surface !== "mirror"
            ? "지금은 실제 브라우저 창에서 조작하고 있습니다."
            : "대상 화면을 아직 받지 못했습니다.";

  const emit = (event: InputEvent | null) => {
    if (event === null || onInput === undefined) return;
    onInput(event);
  };
  /** `ImeBridge` 에 넘길 통로. 참조가 매번 바뀌면 브리지가 매번 다시 붙는다. */
  const emitStable = useCallback(
    (event: InputEvent) => onInput?.(event),
    [onInput],
  );

  const context = { imageRef, frame: geometry, tab: tabIndex ?? 0 };
  /**
   * 조작을 받지 않는 상태에서의 클릭. **조용히 버리지 않는다** (SC-516 · FR-315).
   *
   * 사용자가 클릭했는데 아무 일도 일어나지 않으면 그것은 제품이 고장난 것으로 읽힌다.
   * 이유를 말하는 것이 이 함수의 전부다.
   */
  const refuse = () => onBlockedAttempt?.(blockedReason);

  const onPointerDown = (event: PointerEvent<HTMLImageElement>) => {
    if (!controllable) return refuse();
    // 미러가 초점을 가져간다 (FR-320) — 이후 키 입력이 대상 브라우저로 간다.
    takeFocus();
    /*
      **포인터를 붙잡는다** (010 T089 · FR-318).

      붙잡지 않으면 누른 채 미러 밖으로 끌고 나가 놓았을 때 `pointerup` 이 이 요소로
      오지 않는다. 그러면 대상 페이지는 **누른 상태로 남는다** — 서버가 채널을 닫을 때
      풀어 주지만, 채널이 열려 있는 동안은 그대로다.

      끌어놓기가 미러 영역 안에서만 끝난다고 가정할 수 없다. 목록에서 끌어 화면 밖으로
      빼는 조작은 흔하고, 그때 사용자는 미러 밖에서 손을 뗀다.
    */
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // 캡처를 못 잡아도 조작은 전달한다. 미러 안에서 끝나는 끌어놓기는 그대로 동작하고,
      // 밖으로 나가는 경우는 아래 `pointercancel`·채널 닫힘이 받는다.
    }
    emit(pointerEventOf("pointer.down", nativeOf(event), context));
  };

  const onPointerUp = (event: PointerEvent<HTMLImageElement>) => {
    if (!controllable) return;
    releaseCapture(event);
    emit(pointerEventOf("pointer.up", nativeOf(event), context));
  };
  /**
   * 브라우저가 포인터를 거둬 갔다 (010 T089 · FR-318).
   *
   * 창이 가려지거나 다른 제스처가 시작되면 `pointerup` 없이 `pointercancel` 이 온다.
   * **그때도 놓아야 한다** — 놓지 않으면 대상 페이지가 누른 상태로 남는다.
   *
   * 좌표는 마지막으로 알려진 위치를 쓴다. 취소 사건의 좌표는 의미가 없을 수 있지만,
   * 놓는 위치보다 **놓는다는 사실**이 중요하다.
   */
  const onPointerCancel = (event: PointerEvent<HTMLImageElement>) => {
    if (!controllable) return;
    releaseCapture(event);
    emit(pointerEventOf("pointer.up", nativeOf(event), context));
  };

  const releaseCapture = (event: PointerEvent<HTMLImageElement>) => {
    try {
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    } catch {
      // 이미 놓였거나 캡처한 적이 없다. 어느 쪽이든 할 일이 없다.
    }
  };

  const onPointerMove = (event: PointerEvent<HTMLImageElement>) => {
    if (!controllable) return;
    emit(pointerEventOf("pointer.move", nativeOf(event), context));
  };

  const onWheel = (event: WheelEvent<HTMLImageElement>) => {
    if (!controllable) return refuse();
    emit(
      wheelEventOf(
        {
          clientX: event.clientX,
          clientY: event.clientY,
          deltaX: event.deltaX,
          deltaY: event.deltaY,
          altKey: event.altKey,
          ctrlKey: event.ctrlKey,
          metaKey: event.metaKey,
          shiftKey: event.shiftKey,
        },
        context,
      ),
    );
  };
  /**
   * 키 입력 (FR-320 · T042).
   *
   * **초점이 이 영역에 있을 때만 대상으로 간다.** 없으면 제품 화면의 단축키가 받는다.
   * 어느 쪽이 받는 상태인지는 테두리와 안내 문구가 말한다 — 그러지 않으면 사용자는
   * 자기 키가 어디로 갔는지 모른 채 두 번 누른다.
   *
   * 조합 중(`isComposing`)에는 보내지 않는다. 조합은 `ImeBridge` 가 맡는다 (FR-327).
   */
  const onKey = (event: KeyboardEvent<HTMLDivElement>, kind: "key.down" | "key.up") => {
    if (!controllable) return;
    // 조합 중의 키는 로컬 IME 가 소비한다. 대상에도 보내면 같은 자모가 두 번 들어가고,
    // 그 결과는 사용자가 본 화면과 다르다 (FR-326 · `ImeBridge` 와 같은 판정).
    if (isComposingKey(event.nativeEvent)) return;
    event.preventDefault();
    emit({
      kind,
      tab: tabIndex ?? 0,
      key: event.key,
      code: event.code,
      modifiers: modifiersOf(event),
    });
  };

  return (
    /*
      `minWidth: 0` — 2026-09-09. `flex: 1` 만으로는 flex 항목의 최소 폭이 콘텐츠 폭이라,
      옆에 무엇이 서면 미러가 줄어드는 대신 부모(`.pane` 의 `overflow: hidden`)에서
      잘린다. 잘리는 것과 줄어드는 것은 사용자에게 다르게 보이고, 잘리면 대상 화면의
      오른쪽이 조용히 사라진다.
    */
    <div className="flex flex-col min-h-0 min-w-0 flex-1">
      {/*
        FR-325~FR-327 — 한글 조합을 대상 브라우저로 옮긴다. 아무것도 그리지 않는다.
        조합의 주인은 미러 영역 자체이고, 이 컴포넌트는 그 영역의 조합 사건을 채널로
        옮기기만 한다.
      */}
      <ImeBridge
        target={surfaceEl}
        active={controllable}
        tab={tabIndex ?? 0}
        onInput={emitStable}
      />
      <PhaseNotice phase={phase} tabIndex={tabIndex} surface={surface} />

      {degradedReason !== null && (
        <div className="flex items-center bg-sunken-2 gap-s2 py-[6px] px-[14px]">
          <Chip tone="warn">1 FPS</Chip>
          <span className="text-ink-2">{degradedReason}</span>
          {/*
            FR-345 — **왜 그것이 조작에 문제인지**를 말한다. 강등 사유(`degradedReason`)는
            서버가 보낸 「무엇이 일어났는가」이고, 이 문장은 「그것이 지금 조작에 어떤
            뜻인가」다. 둘은 다른 사실이며, 뒤엣것이 없으면 사용자는 1 FPS 라는 말을 읽고도
            자기 클릭이 왜 빗나갔는지 알 수 없다.
          */}
          {controllable && <span className="font-sans text-[11px] leading-[1.4] text-ink-3">{MIRROR_DEGRADED_WARNING}</span>}
          {/*
            FR-345·FR-353a — 강등 상태에서 **조작은 막지 않되** 정확하지 않을 수 있다는
            사실과 전환 수단을 **같은 자리에** 둔다. 사실만 말하고 수단을 다른 곳에 두면
            사용자는 읽은 자리에서 할 수 있는 일이 없다.
          */}
          {useWindowCapability !== undefined && (
            <UseWindowAction
              capability={useWindowCapability}
              onUseWindow={onUseWindow}
              compact
            />
          )}
        </div>
      )}

      <div
        className="bg-sunken-2 flex-1 grid place-items-center overflow-hidden min-h-0"
      >
        {stoppedReason !== null ? (
          <p className="text-ink-2 text-center p-s5">
            {stoppedReason}
          </p>
        ) : frame !== null ? (
          /*
            조작을 받는 자리를 `data-action` 으로 표시한다 (ui-contract §4-1).
            **조작마다 자리가 하나**이고, 그 자리가 여기다 — 미러 영역 자체가 「미러에서
            조작하기」의 집이다. 버튼이 아니라 영역인 것이 이 조작의 성질이다.
          */
          /*
            FR-319 — **조작을 받는 상태가 눈으로 구분되어야 한다.** 사용자가 클릭해 보고
            나서 알게 되어서는 안 된다.

            색과 테두리를 여기 적지 않고 정본의 `tint-run` 을 쓴다 (008 FR-263 ·
            contracts/visual-language.md C-1). 「지금 살아 움직이는 것」의 색이 이미
            정본에 있으므로 새 시각 언어를 만들 이유가 없다.

            조작 가능일 때 `tabIndex={0}` 이므로 정본의 `:focus-visible` 초점 링이
            그대로 붙는다 — 초점이 어디 있는지(FR-320)를 정본이 말한다.
          */
          <div
            ref={setSurfaceEl}
            data-action="mirror.control"
            data-controllable={controllable ? "true" : "false"}
            data-key-target={controllable && focused ? "mirror" : "product"}
            aria-disabled={controllable ? undefined : "true"}
            tabIndex={controllable ? 0 : -1}
            className={`${controllable ? "bg-run-t border border-run rounded-base" : undefined} gap-s2 py-[10px] px-[14px]`}
            onKeyDown={(event) => onKey(event, "key.down")}
            onKeyUp={(event) => onKey(event, "key.up")}
            /*
              `onFocus`/`onBlur` 는 React 에서 `focusin`/`focusout` 이므로 **안쪽 조합
              요소의 초점도 여기로 올라온다.** 미러 면과 조합 요소 사이를 오가는 것은
              초점이 떠난 것이 아니므로, 나가는 곳이 아직 미러 면 안이면 무시한다 —
              그러지 않으면 클릭할 때마다 안내 문구가 깜빡인다.
            */
            onFocus={(event) => {
              setFocused(true);
              // Tab 으로 들어온 초점은 미러 면 자체에 앉는다. 조합 요소로 넘겨야 IME 가
              // 붙는다 — 넘기지 않으면 키보드만 쓰는 사용자에게 자모분리가 그대로 남는다.
              if (event.target === event.currentTarget) takeFocus();
            }}
            onBlur={(event) => {
              const next = event.relatedTarget as Node | null;
              if (next !== null && event.currentTarget.contains(next)) return;
              setFocused(false);
            }}
          >
            {/*
              FR-325~FR-327 — **조합이 실제로 일어나는 자리.** 위 `imeRef` 주석이 왜
              필요한지를 적어 두었다: `<div>` 에는 IME 가 붙지 않아 한글이 자모로 쪼개진다.

              `aria-hidden` 이 아니다 — 초점을 갖는 요소를 보조기술에서 숨기면 초점이
              어디 있는지 말할 수 없게 된다. 대신 `tabIndex={-1}` 로 Tab 순서에서 빼고
              (Tab 은 미러 면 자체가 받는다), 이름은 미러 면과 같은 것을 쓴다.
            */}
            <textarea
              ref={imeRef}
              tabIndex={-1}
              aria-label="대상 브라우저 입력"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              /*
                조합이 끝나면 비운다. 조합 중(`isComposing`)에는 건드리지 않는다 —
                그때 값을 지우면 브라우저가 조합을 취소한다.
              */
              onInput={(event) => {
                if ((event.nativeEvent as globalThis.InputEvent).isComposing) return;
                event.currentTarget.value = "";
              }}
              onCompositionEnd={clearIme}
              /*
                보이지 않고 포인터도 받지 않는다 — 클릭·끌기·휠은 그대로 화면(`<img>`)
                으로 간다. 형태는 정본의 `.ime-capture` 가 갖는다 (C-7).
              */
              className="absolute inset-0 w-full h-full p-0 m-0 opacity-0 border-none outline-none resize-none overflow-hidden pointer-events-none caret-transparent"
            />
            <img
              ref={imageRef}
              src={`data:image/jpeg;base64,${frame}`}
              alt={
                controllable
                  ? "대상 브라우저 화면 (조작 가능)"
                  : "대상 브라우저 화면 (읽기 전용)"
              }
              /*
                010 FR-316 — **포인터를 받을지는 국면이 정한다.**

                001 은 여기를 `"none"` 으로 못박고 그것을 FR-047a 의 구현이라고 적었다.
                지키던 성질(관찰 국면에서 전달하지 않는다)은 유지되고, 판정만 표로 옮겼다.

                받지 않는 상태에서도 `"auto"` 인 이유는 SC-516 이다 — 포인터를 아예 끄면
                클릭이 이 컴포넌트에 닿지 않고, 사용자는 왜 안 되는지 들을 자리가 없다.
                전달하지 않는 것과 이유를 말하지 않는 것은 다르다.
              */
              className={`max-w-full max-h-full pointer-events-auto select-none ${controllable ? "cursor-default" : "cursor-not-allowed"}`}
              draggable={false}
              onPointerDown={onPointerDown}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerCancel}
              onPointerMove={onPointerMove}
              onWheel={onWheel}
              onContextMenu={(event) => event.preventDefault()}
            />
          </div>
        ) : (
          <div
            data-action="mirror.control"
            data-controllable="false"
            aria-disabled="true"
            className="p-s5"
          >
            <p className="text-ink-2 text-center">
              {mirrorEmptyMessage(phase, surface)}
            </p>
          </div>
        )}
      </div>

      <div className="flex items-center gap-s2 py-[6px] px-[14px]">
        {/*
          FR-234·SC-516 — **조작을 받지 않는 모든 상태에서 이유가 같은 자리에 있다.**

          표가 「안 된다」고 한 경우만 붙이면 부족하다. 표는 「된다」고 했는데 프레임이
          아직 없거나 창에서 조작 중인 경우가 남고, 그 상태에서 사용자는 클릭했는데
          아무 일도 일어나지 않는 것을 본다 — SC-516 이 0건으로 두려는 상태다.
          `blockedReason` 이 그 네 경우를 한 문장으로 모은다.
        */}
        {!controllable && (
          <span className="font-sans text-[11px] leading-[1.4] text-ink-3" data-disabled-reason="mirror.control">
            {blockedReason}
          </span>
        )}
        {controllable && (
          <span className="text-ink-2">
            {focused ? MIRROR_KEYS_GO_TO_TARGET : MIRROR_FOCUS_HINT}
          </span>
        )}
        {useWindowCapability !== undefined && degradedReason === null && (
          <UseWindowAction capability={useWindowCapability} onUseWindow={onUseWindow} />
        )}
      </div>
    </div>
  );
}
/**
 * 「실제 창에서 조작하기」 (FR-349·FR-353 · US5).
 *
 * **폴백이고, 사용자가 누를 때만 일어난다.** 제품이 상황을 판단해 자동으로 창을 열지
 * 않는다 — 요청하지 않은 창은 그 자체로 조작 위치를 잃게 만들고, 화면 없는 환경에서는
 * 자동 전환이 실패한다.
 */
function UseWindowAction({
  capability,
  onUseWindow,
  compact = false,
}: {
  capability: CapabilityState;
  onUseWindow?: () => void;
  compact?: boolean;
}) {
  if (capability.kind === "not_applicable") return null;
  /*
    2026-09-09 — 「이 상태의 조작이 아니다」는 그리지 않는다 (`capabilities.ts`).

    **`mirror.control` 과 갈린다.** 그것은 `ALWAYS_KEEP` 이라 미러 위에 사유가 남는다 —
    사용자가 미러를 클릭해 보기 때문이다. 이 버튼은 클릭할 대상이 자기 자신뿐이므로,
    브라우저가 없는 국면(검토·실행 종료)에서는 자리를 접는 것이 맞다.
  */
  if (capability.kind === "disabled" && capability.visibility === "hide") return null;
  const disabled = capability.kind === "disabled";
  return (
 <span className="flex items-center gap-[6px]">
      <Button
        type="button"
        data-action="mirror.useWindow"
        size={compact ? "sm" : "md"}
        disabled={disabled}
        onClick={disabled ? undefined : onUseWindow}
      >
        실제 창에서 조작하기
      </Button>
      {disabled && (
        <span className="font-sans text-[11px] leading-[1.4] text-ink-3" data-disabled-reason="mirror.useWindow">
          {capability.reason}
        </span>
      )}
    </span>
  );
}
/** 국면별 안내. 어디서 조작해야 하는지를 매번 분명히 한다 (FR-023b · FR-350). */
function PhaseNotice({
  phase,
  tabIndex,
  surface,
}: {
  phase: MirrorPhase;
  tabIndex?: number;
  surface: ControlSurface;
}) {
  const notice = mirrorNotice(phase, surface);
  if (notice === null) return null;

  const tabSuffix = tabIndex !== undefined && tabIndex > 0 ? ` (탭 ${tabIndex})` : "";
  // 관찰 국면만 상태 이름을 칩으로 쓴다 — 확정 디자인의 「읽기 전용」 배지다.
  const asBadge = phase === "observation";

  return (
    <div
      className={`flex items-center gap-s2${phase === "manipulation" ? " bg-warn-t border border-warn-line rounded-base" : ""} relative grid place-items-center max-w-full max-h-full`}
    >
      {asBadge ? (
        <Chip>{notice.title}</Chip>
      ) : (
        <strong>
          {notice.title}
          {tabSuffix}
        </strong>
      )}
      <span className="text-ink-2">
        {notice.detail}
        {asBadge ? `${tabSuffix}.` : ""}
      </span>
    </div>
  );
}

function nativeOf(event: PointerEvent<HTMLImageElement>) {
  return {
    clientX: event.clientX,
    clientY: event.clientY,
    button: event.button,
    altKey: event.altKey,
    ctrlKey: event.ctrlKey,
    metaKey: event.metaKey,
    shiftKey: event.shiftKey,
  };
}
/** 버튼 이름 변환을 재수출한다 — 검증이 같은 규칙을 쓴다. */
export { buttonNameOf };
