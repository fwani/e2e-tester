/**
 * 조합 중 입력을 조작 채널로 흘린다 (010 T044~T046 · FR-325~FR-329 · research R2).
 *
 * ## 왜 별도 통로인가
 *
 * 한글은 조합이 필요하다 — 자음과 모음이 합쳐지는 과정이 있고, 그 과정은 **사용자의 기계
 * 에 있는 IME** 가 한다. 대상 브라우저에는 IME 가 없으므로 자모를 그대로 보내면
 * 「ㅈㅜㅁㅜㄴ」이 된다 (research R2 가 버린 대안 1).
 *
 * 그래서 로컬 IME 의 조합 상태를 **그대로 대상에 옮긴다.** `compositionupdate` 의 중간
 * 문자열을 `ime.compose` 로, 확정을 `ime.commit` 으로 보낸다. 서버는 각각
 * `Input.imeSetComposition` 과 `Input.insertText` 로 바꾼다.
 *
 * ## 왜 중간 상태까지 보내는가 (FR-327)
 *
 * 확정된 문자열만 보내는 편이 단순하다. 그러나 그러면 **대상 화면이 실제 사용자와 다르게
 * 반응한다** — 자동완성·실시간 검색·입력 길이 검사는 글자 하나하나에 반응하는데, 확정만
 * 보내면 그 화면들이 마지막에 한 번만 반응한다. 사용자가 그 대가를 명시적으로 거부했고,
 * 실측이 그것을 가능하게 했다 (조합 8회 + 확정 1회에 총 26.7ms · 키당 3.3ms).
 *
 * ## 왜 응답을 기다리지 않는가 (FR-327a)
 *
 * 다음 키가 앞 키의 전달 완료를 기다리는 구조여서는 안 된다. 채널은 성공 응답을 보내지
 * 않고(contracts §5 불변식 5), 이 컴포넌트는 보내고 즉시 돌아온다. **중간 상태가 일부
 * 유실되어도 확정된 문자열은 정확하다** (FR-327b) — 확정은 `ime.commit` 하나가 전체
 * 문자열을 싣기 때문이다. 중간 상태는 화면 반응을 위한 것이고, 값의 근거가 아니다.
 *
 * ## 조합 중인 값은 Step 이 되지 않는다 (FR-326·FR-327c)
 *
 * 그것은 이 컴포넌트가 아니라 **리코더가 지킨다.** 대상 페이지의 리코더는
 * `compositionstart`/`compositionend` 로 `composing` 을 관리하고 조합 중인 `input` 을
 * 무시한다 (M-10). 조합 중 값이 입력 요소에 들어가 있는 것과 그것이 Step 이 되는 것은
 * 별개다.
 */

import { useEffect, useRef } from "react";

import type { InputEvent } from "./useMirrorInput";

export interface ImeBridgeProps {
  /** 조합을 받을 대상. 미러 영역의 초점 요소다 */
  target: HTMLElement | null;
  /** 지금 조작을 받는가. 아니면 아무것도 보내지 않는다 (FR-315) */
  active: boolean;
  /** 조작 대상 탭 */
  tab: number;
  /** 사건 하나를 채널로 보낸다. **성공을 기다리지 않는다** (FR-327a) */
  onInput: (event: InputEvent) => void;
}

/**
 * 조합 중 미러 밖을 클릭했을 때 어떻게 하는가 (명세 Edge Cases · 010 T046).
 *
 * **확정한다. 버리지 않는다.**
 *
 * 사용자는 이미 그 글자를 화면에서 봤다 — 조합 중 상태가 대상 입력 요소에 실시간으로
 * 들어가 있기 때문이다 (FR-327). 그 상태에서 값을 버리면 화면에 보이던 글자가 사라지고,
 * 사용자는 자기가 무엇을 잃었는지 모른다. 확정하면 최소한 **본 것이 남는다.**
 *
 * 운영체제 IME 도 같은 선택을 한다 — 조합 중 다른 창을 클릭하면 조합이 확정된다.
 * 사용자가 이미 아는 동작을 따르는 편이 새 규칙을 만드는 것보다 낫다.
 *
 * 실제 확정은 브라우저가 한다: 초점이 떠나면 `compositionend` 가 발생하고, 아래
 * `onEnd` 가 그것을 `ime.commit` 으로 보낸다. **이 상수는 코드를 바꾸지 않는다** —
 * 결정을 이름으로 남겨, 나중에 「버려야 하는 것 아닌가」를 다시 묻지 않게 한다.
 * `MirrorInput.test.ts` 가 이 값을 읽어 결정이 조용히 뒤집히지 않게 고정한다.
 */
export const COMPOSITION_ON_BLUR = "commit" as const;

/**
 * 조합 사건을 채널로 흘린다.
 *
 * 컴포넌트가 아무것도 그리지 않는 이유는 조합의 주인이 **미러 영역 자체**이기 때문이다.
 * 별도의 숨은 입력칸을 두면 초점이 둘로 갈리고, 「지금 키가 어디로 가는가」가 화면에서
 * 불분명해진다 (FR-320 이 금지하는 상태다).
 */
export function ImeBridge({ target, active, tab, onInput }: ImeBridgeProps) {
  /**
   * 지금 조합 중인가.
   *
   * `ref` 인 이유는 이 값이 **다시 그릴 이유가 아니기** 때문이다. 상태로 두면 조합 중
   * 글자마다 미러가 다시 그려지고, 그것이 타이핑 체감을 해친다 (FR-327a).
   */
  const composing = useRef(false);

  useEffect(() => {
    if (target === null || !active) {
      composing.current = false;
      return;
    }

    const onStart = () => {
      composing.current = true;
    };

    const onUpdate = (event: Event) => {
      const data = (event as CompositionEvent).data ?? "";
      // FR-327 — 조합 중 값을 **그대로** 대상 입력 요소에 넣는다. 자동완성·실시간 검색이
      // 실제 사용자가 창에서 타이핑할 때와 같게 반응해야 한다.
      onInput({
        kind: "ime.compose",
        tab,
        text: data,
        compositionRange: [data.length, data.length],
      });
    };

    const onEnd = (event: Event) => {
      composing.current = false;
      const data = (event as CompositionEvent).data ?? "";
      // 확정은 **전체 문자열 하나**로 보낸다. 중간 상태가 일부 유실되어도 이 한 번이
      // 정확하면 최종 값이 정확하다 (FR-327b).
      onInput({ kind: "ime.commit", tab, text: data });
    };

    target.addEventListener("compositionstart", onStart);
    target.addEventListener("compositionupdate", onUpdate);
    target.addEventListener("compositionend", onEnd);
    return () => {
      target.removeEventListener("compositionstart", onStart);
      target.removeEventListener("compositionupdate", onUpdate);
      target.removeEventListener("compositionend", onEnd);
    };
  }, [target, active, tab, onInput]);

  return null;
}

/**
 * 조합 중인 상태에서 보내지 말아야 할 키인가 (FR-320 · FR-326).
 *
 * 조합 중의 키 입력은 로컬 IME 가 소비한다. 그것을 대상에도 보내면 같은 자모가 두 번
 * 들어가고, 그 결과는 사용자가 본 화면과 다르다.
 *
 * `MirrorView` 의 키 처리와 **같은 판정을 쓴다** — 판정이 두 곳에 있으면 한 곳이 빠진다.
 */
export function isComposingKey(event: { isComposing?: boolean; keyCode?: number }): boolean {
  // `keyCode === 229` 는 「IME 가 처리 중」의 관습적 표식이다. `isComposing` 만 보면
  // 조합의 **첫 키**를 놓친다 — 그 시점에는 아직 조합이 시작되지 않았기 때문이다.
  return event.isComposing === true || event.keyCode === 229;
}
