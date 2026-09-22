/**
 * 세션을 여는 **유일한 경로** (018 design §3.5 · 005 T021 · FR-125·FR-127·FR-129).
 *
 * 옛 `App.tsx` 의 네 함수를 옮겼다. 달라진 것은 마지막 걸음뿐이다 — 화면 상태를 바꾸던 것이 이제 주소로
 * 옮긴다. `pendingRun` 을 여기 한 곳에 두는 이유는 그대로다: 화면마다 두면 한 화면이 빠뜨리고, 그 화면에서
 * 연타하면 브라우저 창이 둘 뜬다 (U-06 — 실측 5회 클릭에 201 이 2건이었다).
 */
import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { sessions } from "../api/client";
import { describeError } from "../components/ErrorNotice";
import { paths } from "../lib/paths";
import { useAppStore } from "./appStore";
import { arrivalState } from "./arrival";

export interface AppActions {
  /**
   * 실행 요청이 진행 중인 테스트 ID (005 FR-127·FR-129).
   *
   * `null` 이 아니면 어느 실행 버튼도 눌리지 않는다. 브라우저를 띄우는 데 약 1초가 걸리는데 그 동안
   * 화면이 아무 말도 하지 않아 사용자가 다시 눌렀고(U-11), 그것이 세션 중복으로 직결됐다(U-06).
   */
  readonly pendingRun: string | null;
  startRun(testId: string, fromStepIndex?: number): void;
  openBrowserAt(testId: string, stepIndex: number, stepId: string | null, instruction: string | null): void;
  openRerecord(testId: string, stepIds: string[]): void;
  openSession(sessionId: string): void;
  /**
   * 만들기 국면이 세션을 만드는 중인가 (005 U-06 과 같은 결함).
   *
   * `pendingRun` 이 **저장된 테스트의 실행**을 막는 것과 같은 일을, 아직 테스트가 없는 만들기
   * 국면에서 한다. 여기에는 막을 테스트 ID 가 없으므로 별도의 플래그다.
   *
   * 없는 동안 사용자 보고 — 「녹화 시작 준비가 오래 걸리는데 버튼이 계속 눌려서 중복이 난다」.
   * 브라우저를 띄우는 데 1초 남짓 걸리고, 그 사이의 클릭이 그대로 세션 생성 요청이 됐다. 표의
   * O2(`busy`)가 막을 조건인데 이 화면이 사실을 넘기지 않았다.
   */
  readonly composeBusy: boolean;
  /** 만들기 잠금을 건다. 이미 걸려 있으면 `false` — 그 요청은 버린다. */
  lockCompose(): boolean;
  unlockCompose(): void;
}

const AppActionsContext = createContext<AppActions | null>(null);

export function useAppActions(): AppActions {
  const actions = useContext(AppActionsContext);
  if (actions === null) throw new Error("AppActionsProvider 안에서만 쓸 수 있습니다.");
  return actions;
}

export function AppActionsProvider({ children }: { children: ReactNode }) {
  const store = useAppStore();
  const navigate = useNavigate();
  const [pendingRun, setPendingRun] = useState<string | null>(null);
  const [composeBusy, setComposeBusy] = useState(false);
  /*
    같은 틱 안의 두 번째 클릭을 막는 잠금.

    `composeBusy` 만으로는 부족하다 — 상태는 다시 그려진 뒤에야 보이므로, 한 틱 안에
    두 번 눌리면 **두 콜백이 모두 `false` 를 본다.** 버튼의 `disabled` 도 같은 이유로
    한 박자 늦다. `ref` 는 즉시 바뀌므로 그 창이 없다.
  */
  const composeLock = useRef(false);

  const actions: AppActions = {
    pendingRun,
    composeBusy,

    /**
     * 실행을 거는 **유일한 경로** (005 T021 · FR-125·FR-127·FR-129).
     *
     * 이전에는 결과 화면이 이것을 직접 부르고 실행 화면은 `discard` 후 새로 만드는 다른
     * 경로를 썼다. 같은 이름의 버튼이 두 화면에서 다르게 동작했고, 결과 화면 쪽은 종료된
     * 세션 때문에 **항상 409 로 거부**됐다 (U-01).
     *
     * `pendingRun` 을 여기서 관리하는 이유는 in-flight 가드가 한 곳에 있어야 하기
     * 때문이다. 화면마다 두면 한 화면이 빠뜨리고, 그 화면에서 연타하면 브라우저 창이
     * 둘 뜬다 (U-06 — 실측 5회 클릭에 201 이 2건이었다).
     */
    startRun(testId, fromStepIndex) {
      // 첫 클릭만 받는다. 0.3초 안에 화면이 변해야 하므로(FR-129) 응답을 기다리지 않고
      // 즉시 상태를 세운다 — 버튼은 이 값을 보고 비활성이 된다.
      if (pendingRun !== null) return;
      setPendingRun(testId);
      store.setError(null);
      void sessions
        .create({ mode: "replay", test_id: testId })
        .then(async (session) => {
          // "실패한 Step부터 실행" — 세션을 만든 뒤 곧바로 실행 위치를 옮긴다 (FR-055).
          if (fromStepIndex !== undefined && fromStepIndex > 0) {
            return await sessions.runFrom(session.session_id, fromStepIndex);
          }
          return session;
        })
        .then((session) => navigate(paths.session(session.session_id)))
        .catch((exc: unknown) => store.setError(describeError(exc)))
        // 성공해도 놓는다. 화면이 이미 바뀌었으므로 남겨 두면 그 테스트를 다시 실행할 수
        // 없게 되고, 그것은 고치려던 것과 같은 종류의 막힘이다.
        .finally(() => setPendingRun(null));
    },

    /**
     * 편집을 위해 브라우저를 열고 지정한 Step **직전**에서 멈춘다 (006 FR-200·FR-201).
     *
     * 실행 진입과 **같은 가드**를 지난다 — `pendingRun` 이 세션 중복 생성을 막는다.
     * 여기에 별도 경로를 만들면 편집 쪽에서만 연타로 브라우저가 둘 뜬다 (005 U-06 과
     * 같은 종류의 결함).
     *
     * 도달한 뒤의 편집은 지금의 일시정지 팔레트 그대로다 — 새 편집 UI 를 만들지 않는다
     * (FR-205).
     *
     * `instruction` — 도착하면 수행할 지시문 (011 FR-374a). **같은 함수를 쓴다.** 녹화와
     * 지시문이 다른 경로로 세션을 열면 「도착하면 무엇을 하는가」만 다른 두 벌이 생기고,
     * 그 둘이 갈리는 것이 사용자 보고 3번의 형태다.
     */
    openBrowserAt(testId, stepIndex, stepId, instruction) {
      if (pendingRun !== null) return;
      setPendingRun(testId);
      store.setError(null);
      void sessions
        .create({ mode: "replay", test_id: testId, pause_before_index: stepIndex })
        .then((session) =>
          navigate(
            // 006 FR-204 — 끝나면 출발한 편집 화면으로 돌아온다. 돌아갈 곳은 주소에 싣는다 (018 §3.3).
            paths.session(session.session_id, { stepId }),
            {
              state: arrivalState({
                /*
                  009 FR-291 — 이 조작의 목적이 「그 자리에 Step 을 넣는 것」이므로 도착하면
                  기록이 켜진 상태여야 한다. 이전에는 도착한 뒤 사용자가 팔레트에서 「직접
                  조작으로 Step 추가」를 다시 찾아야 했다 — 그것이 다섯 걸음의 마지막 걸음이다.
                */
                /*
                  011 — 지시문으로 출발했으면 도착해서 그것을 수행한다. 녹화와 **하나만**
                  켜진다: 지시문 수행 중에 기록까지 켜지면 AI 가 만든 Step 과 사용자가 만든
                  Step 이 같은 자리에 섞인다.
                */
                aiInstruction: instruction,
                recordOnArrival: instruction === null,
                /*
                  011 converge — **지시문을 기록으로도 남긴다** (FR-377).

                  `instructionOnArrival` 은 「도착하면 이것을 수행하라」는 **명령**이고 한 번
                  쓰이면 끝난다. `aiInstruction` 은 「무엇을 시켰는가」라는 **기록**이며 화면에
                  계속 남아야 한다 (001 FR-063 · UX U-07 — 보이지 않으면 사용자는 자기가 무엇을
                  시켰는지 잃는다).

                  둘을 갈라 두고 같은 문장을 싣는다. 하나로 합치면 수행이 끝난 뒤 기록도 사라진다.
                */
                instructionOnArrival: instruction,
              }),
            },
          ),
        )
        .catch((exc: unknown) => store.setError(describeError(exc)))
        .finally(() => setPendingRun(null));
    },

    /**
     * 016 — 고른 구간으로 **재녹화 세션**을 연다 (FR-015·FR-018).
     *
     * `openBrowserAt` 과 갈라 둔 이유는 서버에서 **다른 모드**이기 때문이다
     * (`mode=rerecord`). 그쪽은 「한 지점에 도착해 기록을 켠다」이고 이것은 「구간을
     * 교체한다」이며, 도착점 계산·트랜잭션 생성·authoring_mode 가 전부 서버 몫이다
     * (api-contract §1). 같은 함수로 묶으면 인자로 갈래를 판정해야 하고, 그 판정이
     * 화면과 서버 두 곳에 생긴다.
     *
     * **기록을 켜지 않는다.** 재녹화의 지시는 대화로 오므로 `recordOnArrival` 이
     * 거짓이다 — 켜면 AI 가 만든 Step 과 사용자가 만든 Step 이 같은 자리에 섞인다
     * (011 이 `instructionOnArrival` 에서 세운 판단과 같다).
     */
    openRerecord(testId, stepIds) {
      if (pendingRun !== null) return;
      setPendingRun(testId);
      store.setError(null);
      void sessions
        .create({ mode: "rerecord", test_id: testId, rerecord_step_ids: stepIds })
        // 006 FR-204 — 끝나면 출발한 편집 화면으로 돌아온다. 재녹화도 편집의 일이다.
        .then((session) => navigate(paths.session(session.session_id, { stepId: stepIds[0] ?? null })))
        .catch((exc: unknown) => store.setError(describeError(exc)))
        .finally(() => setPendingRun(null));
    },

    /**
     * 거절 안내가 가리킨 세션으로 이동한다 (005 T024 · FR-126).
     *
     * 거절은 목록에서도 결과 화면에서도 날 수 있고 배너는 두 화면 **위**에 있다. 그래서
     * 이동 수단도 여기 한 곳에 둔다 — 화면마다 두면 한쪽이 빠지고, 빠진 화면에서는 안내가
     * 다시 "화면에 없는 조작" 을 지시하게 된다.
     *
     * 세션 조회는 실행 화면의 loader 가 한다. 그 사이에 끝났다면 loader 가 목록으로 옮긴다 (018 §5).
     */
    openSession(sessionId) {
      store.setError(null);
      void navigate(paths.session(sessionId));
    },

    lockCompose() {
      if (composeLock.current) return false;
      composeLock.current = true;
      setComposeBusy(true);
      return true;
    },

    unlockCompose() {
      composeLock.current = false;
      setComposeBusy(false);
    },
  };

  return <AppActionsContext.Provider value={actions}>{children}</AppActionsContext.Provider>;
}
