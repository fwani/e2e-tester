/**
 * 실행 화면 `/sessions/:sessionId[?from=edit&step=]` (018 §3.3).
 *
 * 세션은 loader 가 읽는다 — 주소만으로 되살아난다. 도착 정보는 `arrival.ts` 머리주석을 본다.
 */
import { useEffect, useState } from "react";
import { useLoaderData, useLocation, useNavigate, useSearchParams } from "react-router";

import type { SessionView } from "../../api/client";
import { paths } from "../../lib/paths";
import { SessionScreen } from "../../pages/SessionScreen";
import { useAppActions } from "../actions";
import { hasCommands, readArrival, withoutCommands } from "../arrival";

export function SessionRoute() {
  const session = useLoaderData() as SessionView;
  /*
    **세션마다 새로 그린다.** 같은 라우트 안에서 세션이 바뀌면(편집 세션에서 「고치기」로 새 세션을 열 때)
    React 는 컴포넌트를 재사용한다. 그러면 첫 렌더에 꺼낸 도착 정보와 `SessionScreen` 의 내부 상태가
    **옛 세션의 것**으로 남는다 — `SessionScreen` 은 `initial` 을 `useState` 초기값으로만 읽는다.
  */
  return <SessionBody key={session.session_id} session={session} />;
}

function SessionBody({ session }: { session: SessionView }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const actions = useAppActions();

  /*
    **명령은 첫 렌더에 꺼낸다.** 수행은 세션이 도착점에 멈춘 뒤라서, 그 전에 기록을 지우면 prop 이 먼저
    사라진다. 꺼낸 값은 이 컴포넌트가 사는 동안 상태에 남고, 기록에서는 곧바로 지운다 (§3.3).
  */
  const [arrival] = useState(() => readArrival(location.state));
  useEffect(() => {
    if (hasCommands(location.state)) {
      void navigate(location, { replace: true, state: withoutCommands(location.state) });
    }
    // 첫 렌더에만 — 꺼낸 명령은 이미 `arrival` 에 있다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 006 FR-204 — 편집에서 출발한 세션은 그 화면으로 돌아온다. 돌아갈 곳은 주소에 있다. */
  const fromEdit = search.get("from") === "edit";
  const backStep = search.get("step");

  return (
    <SessionScreen
      initial={session}
      aiInstruction={arrival.aiInstruction}
      /* 초안 출처는 세션 응답이 나른다 — 새로 고쳐도 남는다 (014 수렴 2회차). */
      draft={session.draft ?? null}
      /* 009 FR-291 — 목표 자리에 도착하면 기록을 켠다 */
      recordOnArrival={arrival.recordOnArrival}
      /* 011 FR-374a — 목표 자리에 도착하면 지시문을 수행한다 */
      instructionOnArrival={arrival.instructionOnArrival}
      /*
        006 FR-204 — 편집 화면에서 출발한 세션은 그 화면으로 돌아온다. 편집 화면은 마운트마다
        `GET /definition` 을 다시 읽으므로 세션에서 저장한 내용이 반영된 상태로 보인다.

        **세션 화면을 벗어나는 이동은 모두 교체(`replace`)다.** 실행 화면은 거쳐 가는 자리다 — 옛 `App`
        도 이 주소를 되살리지 못해 결과·목록·편집에서 뒤로 가면 세션이 아니라 그 전 화면(목록·편집)으로
        갔다. **밀어 넣으면(push) 안 되는 이유**: 뒤로가기가 세션 주소로 돌아오고, loader 가 세션을
        다시 읽어(여전히 끝난 상태) `SessionScreen` 의 `jumpedToResult` 가 새로 시작해 결과로 다시
        튕긴다 — 뒤로가기가 통째로 막힌다(리뷰 재현). 새 세션을 여는 이동(`actions.openBrowserAt`)은
        예외다 — 그것은 세션 화면을 **벗어나는** 것이 아니라 다음 세션으로 **들어가는** 것이다.
      */
      onFinished={() =>
        void navigate(
          fromEdit && session.test_id ? paths.edit(session.test_id, backStep) : paths.list(),
          { replace: true },
        )
      }
      onShowResult={(testId, stepId) =>
        void navigate(paths.result(testId, stepId ?? null), { replace: true })
      }
      /*
        2026-09-10 사용자 결정 — 실행이 끝나면 결과 국면으로 스스로 넘어간다.

        **편집에서 출발한 세션은 예외다.** 그 세션이 돌아갈 곳은 편집 화면이고
        (006 FR-204), 결과로 튕기면 사용자는 고치던 자리를 잃는다. 그 판단 근거인
        `fromEdit`(주소의 `from=edit`)은 여기에만 있으므로 여기서 정한다.
      */
      autoShowResult={!fromEdit}
      /*
        2026-09-09 사용자 보고 — 「실행 후 에러가 났을 때 고치는 방법이 없음」.

        실패한 실행 화면에서 곧바로 편집으로 간다. 세션을 버리는 일은 `SessionScreen`
        이 먼저 한다 — 살아 있는 세션이 그 테스트를 잡고 있으면 편집이 잠긴다
        (006 FR-206). 편집 화면은 마운트마다 정의를 다시 읽으므로 저장한 내용이
        반영된 상태로 열린다.
      */
      /*
        2026-09-09 사용자 결정 — 「직전 스텝까지의 세션을 제공하던지 해서, 이어서
        편집이 가능해야함」.

        **새 화면을 만들지 않는다.** 목적지는 009 FR-291 이 이미 만든 것이다 —
        그 자리 전까지 재생한 뒤 멈추고 직접 조작 기록을 켠 세션(`openBrowserAt`).
        거기서는 요소를 다시 집을 수도 있고(살아 있는 페이지가 있다) 값·순서·삭제도
        고칠 수 있다(일시정지 국면). 끝내면 `paths.session` 의 `back` 으로 편집 화면에 닿는다.

        **편집 화면을 먼저 띄우고 거기서 다시 옮기지 않는다.** 한 번의 「고치기」
        안에서 껍데기가 두 번 바뀌면 사용자는 자기가 어디 있는지 놓친다 (S-14).

        자리를 모르면(지목도 실패도 없다) 편집 화면으로 간다 — 재생할 목표가 없다.
      */
      onEditStep={(testId, stepId, stepIndex) => {
        if (stepIndex < 0) {
          // 같은 이유로 교체 — 편집으로 곧장 가는 것도 세션 화면을 벗어나는 이동이다.
          void navigate(paths.edit(testId, stepId), { replace: true });
          return;
        }
        actions.openBrowserAt(testId, stepIndex, stepId, null);
      }}
      onRerun={(testId, fromStepIndex) => actions.startRun(testId, fromStepIndex)}
    />
  );
}
