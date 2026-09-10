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
 *
 * ## 2026-09-09 — 토스트가 됐다 (사용자 결정)
 *
 * 두 번의 보고를 거쳤다.
 *
 * 1. 「알림으로 인해 아래 화면들이 내려가는데, 화면이 내려가서 문제」 → 문서 흐름에서
 *    빼내 좌측 영역 위에 겹쳐 띄웠다 (`Workbench` 의 알림 층).
 * 2. 「토스트로 해야지 방해가 안됨. 근거를 보는건 결과화면에서 기록을 보면됨」 →
 *    **스스로 사라진다.**
 *
 * **005 FR-154·FR-158 의 판단을 사용자가 뒤집었다.** 그 조항은 「토스트로 끝내지 않는
 * 이유는 사라지면 근거가 남지 않기 때문이다」였고, 근거는 실측이었다 (U-09). 사용자가
 * 지목한 것은 그 근거가 **다른 곳에도 있다**는 사실이다 — 실행 결말과 실패 사유는 결과
 * 화면의 기록에 남고(`ResultView`), 저장 여부는 저장 조작의 상태가 말한다. 화면 위에
 * 계속 떠 있는 배너가 대신하고 있던 일이 아니다.
 *
 * 사라지는 것을 **컴포넌트가 스스로 기억한다** (`hidden`). 알림은 대부분 상태에서
 * 파생되므로(오류·실패·유실) 바깥에 「지웠다」를 알려도 다음 렌더에서 그대로 돌아온다.
 * 그래서 지운 기록은 여기 있고, **문구가 바뀌면 다시 보인다** — 같은 자리의 새 사실을
 * 지난 것으로 취급하지 않는다.
 *
 * 마우스를 올린 동안에는 세지 않는다. 읽는 중에 사라지는 것이 토스트의 유일한 실패
 * 방식이다.
 *
 * ## 2026-09-10 — 자리는 오른쪽 위, 오류는 닫을 때까지 (사용자 결정)
 *
 * 자리는 뷰포트 오른쪽 위로 고정됐다 (`tokens.css` 의 `.toast-layer`). 국면마다 다른
 * 데서 뜨던 것이 한 자리로 모였다.
 *
 * **오류는 스스로 사라지지 않는다.** 위의 「전부 스스로 사라진다」는 그 뒤로 경고·안내
 * 에만 해당한다 — 근거를 다른 데서 볼 수 있다는 2026-09-09 의 논거가 오류의 「다음
 * 행동」에는 성립하지 않았다. 자세한 것은 `LINGER_MS`.
 */
import { useEffect, useRef, useState } from "react";

import type { ActionId } from "../../lib/actions";
import { ACTION_LABEL } from "../../lib/wording";
import type { Notice } from "./model";

import { Button } from "../../ui/Button";

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

/**
 * 머무는 시간. `null` 이면 **사용자가 닫을 때까지 남는다.**
 *
 * ## 2026-09-10 — 오류는 스스로 사라지지 않는다 (사용자 결정)
 *
 * 「warning 은 일정 시간 뜨고 사라지면 될 것 같고, 에러의 경우 warning 보다 길게라던지
 * 닫기 전까지라던지 정리가 필요하다」.
 *
 * 12초로는 부족하다는 것이 요구의 실체다. 오류 알림은 사유 + 다음 행동 두 줄이고
 * (003 EC-004), 그 「다음 행동」은 **읽고 나서 하는 것**이다 — 읽는 동안이 아니라
 * 수행하는 동안에도 화면에 있어야 한다. 자리를 비켜 준 뒤 사용자가 「뭐라고 했더라」로
 * 돌아오면, 근거를 남기려던 005 FR-154 가 되살아난 것과 같은 상태가 된다.
 *
 * 경고·안내는 반대다. 지나간 사실을 알릴 뿐이고 근거는 결과 화면의 기록에 남는다
 * (2026-09-09 결정). 짧게 뜨고 비켜 준다.
 *
 * 마우스를 올린 동안에는 세지 않는 규칙은 그대로다.
 */
const LINGER_MS: Record<Notice["tone"], number | null> = {
  error: null,
  warn: 7000,
  info: 5000,
};

/**
 * 그 알림을 **같은 알림으로 볼 것인가**.
 *
 * `id` 만으로 기억하면, 같은 자리에 새 사실이 와도(같은 `id` · 다른 문구) 지난 것으로
 * 취급해 사용자가 보지 못한다. 실제로 그럴 수 있는 알림이 있다 — `run-failure` 는 실행이
 * 바뀔 때마다 다른 Step 을 말한다.
 */
function fingerprint(n: Notice): string {
  return `${n.id}::${n.message}::${n.nextAction ?? ""}`;
}

export function NoticeStack({ notices, onAct, onDismiss }: NoticeStackProps) {
  /** 스스로 사라진 것들. 문구가 바뀌면 지문이 달라져 다시 보인다 */
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  /** 마우스가 올라와 있는 동안에는 세지 않는다 */
  const [held, setHeld] = useState(false);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const shown = notices.filter((n) => !hidden.has(fingerprint(n)));

  useEffect(() => {
    if (held) {
      for (const t of timers.current.values()) clearTimeout(t);
      timers.current.clear();
      return;
    }
    for (const n of shown) {
      const key = fingerprint(n);
      if (timers.current.has(key)) continue;
      const linger = LINGER_MS[n.tone];
      // 닫기 전까지 남는 알림에는 타이머를 걸지 않는다 (오류).
      if (linger === null) continue;
      timers.current.set(
        key,
        setTimeout(() => {
          timers.current.delete(key);
          setHidden((prev) => new Set(prev).add(key));
          /*
            바깥에도 알린다. 스스로 지울 수 있는 알림(`notice`·`auto-transition`)은
            그 상태를 비워야 다음 사실이 같은 자리에 올 수 있다 — 여기서만 기억하면
            바깥 상태는 지난 알림을 계속 들고 있게 된다.
          */
          onDismiss?.(n.id);
        }, linger),
      );
    }
    // 목록에서 빠진 알림의 타이머는 걷는다.
    const live = new Set(shown.map(fingerprint));
    for (const [key, t] of timers.current) {
      if (!live.has(key)) {
        clearTimeout(t);
        timers.current.delete(key);
      }
    }
    // `onDismiss` 는 매 렌더 새 함수일 수 있다 — 의존성에 넣으면 타이머가 매번 다시 선다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [held, shown.map(fingerprint).join("|")]);

  // 마운트가 끝나면 남은 타이머를 걷는다.
  useEffect(() => {
    const map = timers.current;
    return () => {
      for (const t of map.values()) clearTimeout(t);
      map.clear();
    };
  }, []);

  if (shown.length === 0) return null;
  return (
    <div
      data-workbench-notices
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      style={{ display: "flex", flexDirection: "column", gap: 8 }}
    >
      {shown.map((n) => (
        <div
          key={n.id}
          role={n.role}
          data-notice={n.id}
          /*
            `float` — 이 묶음은 문서 흐름이 아니라 좌측 영역 위에 떠 있다 (2026-09-09 ·
            `Workbench` 의 알림 층). 형태는 정본이 갖는다 (`tokens.css` 의 `.notice.float`).
          */
          className={`notice float ${TONE[n.tone]}`.trimEnd()}
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
            <Button
              size="sm"
              data-notice-action={n.action.actionId}
              onClick={() => onAct?.(n.action!.actionId)} >
              {n.action.label || ACTION_LABEL[n.action.actionId]}
            </Button>
          )}
          {/*
            **닫기는 모든 알림에 있다** (2026-09-09).

            이전에는 `dismissible` 인 것만 가졌다. 그 구별의 근거는 「지우면 근거가
            사라지는 알림이 있다」였는데, 경고·안내는 스스로 사라지고 오류는 이 버튼이
            유일한 퇴장이므로 (2026-09-10) 그 구별은 남아 있어도
            사용자에게는 「어떤 것은 손으로 지울 수 있고 어떤 것은 못 지운다」로만 보인다.
            먼저 읽고 치우는 길을 막을 이유가 없다.

            `dismissible` 은 모델에 남는다 — 값이 아직 다른 뜻을 갖는다(자동으로 걷히기
            전에도 지울 수 있는가)기보다, 지우는 순간 **바깥 상태까지 비울 대상**인지를
            구별한다. 그 판정은 `onDismiss` 를 받는 화면이 이미 갖고 있다.
          */}
          <Button
            size="sm" variant="quiet"
            aria-label="알림 닫기"
            onClick={() => {
              setHidden((prev) => new Set(prev).add(fingerprint(n)));
              onDismiss?.(n.id);
            }} >
            닫기
          </Button>
        </div>
      ))}
    </div>
  );
}
