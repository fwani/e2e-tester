/** 만들기 `/tests/new[?draft=]` (018 §3.4). 초안은 loader 가 읽어 온다 (`router.tsx`). */
import { useEffect } from "react";
import { useLoaderData, useNavigate } from "react-router";

import { sessions } from "../../api/client";
import { describeError } from "../../components/ErrorNotice";
import { paths } from "../../lib/paths";
import { ComposeView } from "../../pages/ComposeView";
import { useAppActions } from "../actions";
import { useAppState, useAppStore } from "../appStore";
import { arrivalState } from "../arrival";

/** 초안에서 출발한 만들기 (014 US3 · FR-030·FR-031) — 옛 `Screen` 의 `compose.draft` 와 같은 모양이다. */
export interface ComposeDraft {
  draft_id: string;
  name: string;
  group_prefix: string;
  instruction: string;
}

export function ComposeRoute() {
  const draft = useLoaderData() as ComposeDraft | null;
  const navigate = useNavigate();
  const store = useAppStore();
  const actions = useAppActions();
  const project = useAppState((s) => s.project) ?? null;

  // 지난 시도의 잠금을 들고 들어가지 않는다 — 세션 생성에 실패하고 목록으로 돌아온 뒤 다시 들어오면
  // 버튼이 눌리지 않는 채로 남는다 (옛 `onCreate` 주석).
  useEffect(() => {
    actions.unlockCompose();
    // 들어올 때 한 번만 — `actions` 는 매 렌더 새 객체다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fail = (exc: unknown) => {
    actions.unlockCompose();
    store.setError(describeError(exc));
  };

  return (
    <ComposeView
      // 초안이 바뀌면 입력칸을 새로 채운다 — `initialInstruction` 은 첫 렌더에만 읽힌다.
      key={draft?.draft_id ?? "new"}
      project={project}
      onCancel={() => void navigate(paths.list())}
      /* 014 FR-031 — 초안에서 출발했으면 지시문을 미리 채운다 */
      initialInstruction={draft?.instruction ?? null}
      fromDraft={draft ? { draft_id: draft.draft_id, name: draft.name } : null}
      /*
        **세션 생성 경로를 새로 만들지 않는다** (FR-248 · 005 U-01·U-06).
        아래 두 호출은 1회차에 `CreateTest`·`AiCompose` 가 부르던 것과 같다 —
        화면이 하나로 합쳐졌을 뿐 경로는 그대로다.
      */
      /*
        **진행 중에는 다시 받지 않는다.** 표의 O2 가 버튼을 막지만, 그 판정은 화면이
        사실을 넘겨야 성립한다 — 그리고 화면 단의 `disabled` 만으로는 부족하다
        (키보드 연타·이중 발화). 요청을 내는 자리에서도 한 번 더 잠근다.

        실패하면 다시 풀어 준다. 성공하면 화면이 바뀌므로 풀 자리가 없다 — 그리고
        풀면 안 된다. 돌아오는 길에 잠깐 눌리는 창이 생긴다.
      */
      busy={actions.composeBusy}
      onRecord={(startUrl) => {
        if (!actions.lockCompose()) return;
        void sessions
          .create({
            mode: "record",
            start_url: startUrl,
            /*
              초안에서 손으로 녹화하는 것도 온전한 방법이다 (수렴 2회차). 여기서 빠뜨리면 화면은
              「저장하면 이 초안은 사라집니다」라고 해 놓고 초안을 남긴다 — 안내가 거짓이 된다.
            */
            draft_id: draft?.draft_id ?? null,
          })
          // 저장 이름·그룹의 기본값은 세션 응답의 `draft` 가 나른다 (018 §3.3).
          .then((session) => navigate(paths.session(session.session_id)))
          .catch(fail);
      }}
      onStartAi={(startUrl, aiInstruction) => {
        if (!actions.lockCompose()) return;
        void sessions
          .create({
            mode: "ai",
            start_url: startUrl,
            ai_instruction: aiInstruction,
            /*
              014 FR-030 — **초안에서 왔다는 사실을 서버에 알린다.**

              지시문만 미리 채우고 이것을 빠뜨리면 화면은 그럴듯하게 동작하지만,
              저장할 때 희망 번호를 받지 못하고(FR-032) 설명·수행자가 옮겨지지 않으며
              (FR-026) 초안도 사라지지 않는다(FR-033). 실제로 그런 상태였다 — 백엔드
              e2e 가 SessionWork 를 직접 조립해 이 구멍을 지나갔기 때문이다 (T085).
            */
            draft_id: draft?.draft_id ?? null,
          })
          .then((session) =>
            navigate(paths.session(session.session_id), { state: arrivalState({ aiInstruction }) }),
          )
          .catch(fail);
      }}
    />
  );
}
