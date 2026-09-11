/**
 * 조작 식별자 42개 (007 T008 · contracts/ui-contract.md §2 · 009 계약 §1 · 010 §1 · 011 §1).
 *
 * 010 이 미러 조작 둘을 더했다 — 「미러에서 조작하기」·「실제 창으로 전환하기」.
 * 011 이 복수 삭제 넷을 더했다 — 행 체크·전부 고르기·고른 것 지우기·이 뒤 전부 지우기.
 *
 * **이 목록이 FR-247 의 검사 대상이다** — 통합으로 사라지는 조작이 있어서는 안 된다.
 * 지금 조작은 7개 화면의 props 로 흩어져 있고, 같은 일이 다른 이름으로 여러 곳에 있다.
 * Step 지목이 `onSelectStep`(3곳) · `onEditStep`(2곳) · 내부 상태(1곳)로 셋이었다.
 *
 * 타입으로 고정하는 이유는 오타를 컴파일에서 잡기 위해서다. 권한표의 키와 화면이 묻는
 * 키가 문자열로 갈리면, 화면은 "없는 조작" 을 물어 `undefined` 를 받고 조용히 아무것도
 * 그리지 않는다 — 감춰진 조작이 되고 FR-234 위반이다.
 */

/** 실행·세션 (11) */
export const RUN_ACTIONS = [
  /** 처음부터 실행 (새 세션) */
  "run.all",
  /** Step nn 부터 실행 (새 세션) */
  "run.from",
  /** Step nn 부터 이어 실행 (열린 세션 안에서) */
  "run.fromHere",
  /** 일시정지 */
  "run.pause",
  /** 계속하기 / AI 에게 돌려주기 */
  "run.resume",
  /** 실패 건너뛰고 계속 */
  "run.resumeSkipFailure",
  /** 중지 / 닫기 / 나가기 */
  "run.stop",
  /** 실행 속도 */
  "run.pacing",
  /**
   * 브라우저 열어 Step nn **앞에서** 멈추기.
   *
   * 009 에서 뜻이 넓어졌다 — 도착하면 **직접 조작 녹화가 켜진다** (FR-291·FR-295).
   * 「브라우저에서 지목해 추가」를 별도 조작으로 만들지 않았다: 도착지가 같은 두 버튼을
   * 나란히 두면 사용자는 차이를 확인하느라 멈춘다 (006 E-03 · 009 research R3).
   */
  "browser.openAt",
  /** 실행 중인 세션 보기 */
  "session.open",
  /**
   * 녹화 시작 — 세션을 **녹화 모드로 만든다** (2회차 · FR-258b · UC-401).
   *
   * `step.recordStart`(직접 조작으로 Step 추가)와 **다른 조작이다.** 그것은 이미 열린
   * 세션 안에서 기록을 켜고, 이것은 세션 자체를 만든다.
   *
   * 1회차 목록(33개)에 없었다. 만들기를 범위에서 뺐기 때문이며(FR-217a), 그때도 제품에는
   * `CreateTest.onRecord` 로 있었다. UC-401 은 이런 경우 **표가 틀렸다**고 정한다 —
   * 목록에 올리는 것은 새 조작을 만드는 일이 아니라 계약의 누락을 채우는 일이다.
   */
  "record.start",
] as const;

/** Step 작성 (5) */
export const AUTHORING_ACTIONS = [
  "step.recordStart",
  "step.recordStop",
  "step.addNaturalLanguage",
  "step.addAssertion",
  /**
   * 직접 입력으로 Step 추가 — **브라우저 없이** (009 FR-285).
   *
   * 위 넷과 갈리는 유일한 조작이다. 넷은 전부 살아 있는 브라우저를 전제하는데(관찰 M-01),
   * 요소를 지목하지 않는 Step 종류(주소 이동·탭 닫기·주소 검증·화면 텍스트 검증)에는
   * 그 전제가 필요 없다. 그래서 편집 국면에서 이것만 `NEEDS_BROWSER` 로 잠기지 않는다
   * (FR-307 · 계약 §2-1).
   */
  "step.insertManual",
] as const;

/** Step 편집 (11) */
export const STEP_ACTIONS = [
  "step.select",
  "step.update",
  "step.markSensitive",
  "step.repick",
  "step.delete",
  /*
   * ─── 복수 삭제 (011 FR-380~FR-385 · 계약 §5) ────────────────────────────
   *
   * `step.delete`(행 하나)를 **대체하지 않는다.** 한 개를 지우는 데 체크하고 팔레트로
   * 내려가는 것은 지금보다 나쁘다 (research R9).
   *
   * 넷으로 갈라 둔 이유는 자리가 다르기 때문이다 — 앞의 둘은 목록 안(행·머리)에 살고
   * 뒤의 둘은 팔레트에 산다. 하나로 뭉개면 「한 조작에 한 자리」를 셀 수 없다 (FR-235).
   */
  /**
   * 이 행을 고른 것에 넣고 뺀다 — **지목과 다른 조작이다** (FR-380a).
   *
   * 행 본문을 누르는 것은 `step.select`(상세 열기)이고, 이것은 칸 0 의 체크 칸이다.
   * 같은 누름에 두 뜻을 주면 사용자는 상세를 보려다 대상을 만든다.
   *
   * **016 에서 `step.toggleDeleteTarget` 에서 개칭했다.** 같은 체크를 016 의 구간
   * 재녹화가 **대상 구간 지정**에도 쓴다 (FR-015). 이름이 삭제 전용이면 거짓이 되고,
   * 체크 칸을 둘로 만들면 사용자가 어느 쪽에 체크할지 판단해야 한다.
   *
   * 개칭에는 전례가 있다 — 009 가 `step.reorder → step.moveUp` 으로 했고 근거가
   * 같았다: 이름이 실제 뜻을 따라가야 한다. **조작 수는 늘지 않는다.**
   */
  "step.toggleSelection",
  /**
   * 목록 전체를 고르고 한 번에 푼다 (FR-380c). 자리는 Step 패널 머리.
   *
   * 016 에서 `step.selectAllDeleteTargets` 에서 개칭했다 (위와 같은 이유).
   */
  "step.selectAll",
  /** 고른 것 전부 지우기 (FR-382). 부분 적용을 남기지 않는다 (FR-388) */
  "step.deleteSelected",
  /**
   * 지목한 Step **다음** 전부 지우기 (FR-383).
   *
   * 실사용에서 가장 잦은 정리다 — 「여기부터 다시 녹화했으니 뒤의 옛 Step 은 필요 없다」.
   * **서버 개념이 아니다** — 화면이 지목 이후의 Step id 를 모아 기존 삭제 경로에 싣는다.
   * 서버에 범위를 넣으면 「그 사이 목록이 바뀌면 무엇을 지우는가」가 양쪽에 생긴다
   * (research R5).
   */
  "step.deleteAfter",
  /**
   * 위로 옮기기 — **009 에서 `step.reorder` 를 개칭했다.**
   *
   * 이전 이름은 별도 「순서 변경」 패널을 가리켰다. 그 패널이 없어지므로(FR-301) 이름이
   * 실제 동작(한 칸 위로)과 같아야 한다. 개칭이 개명 이상인 이유: 이전 이름은 두 방향을
   * 뜻하는 것처럼 읽히면서 실제로는 위로만 옮겼다 (관찰 M-05).
   */
  "step.moveUp",
  /** 아래로 옮기기 — 지금 없는 방향 (FR-299). n칸 옮기는 데 n회면 된다 */
  "step.moveDown",
] as const;

/** 테스트 속성·저장 (5) */
export const TEST_ACTIONS = [
  "test.rename",
  "test.setStartUrl",
  "save",
  "save.overwriteStale",
  "edits.revert",
] as const;

/** AI (7) — 016 에서 3 → 7 (contracts/ui-contract.md §1-1) */
export const AI_ACTIONS = [
  "ai.compose",
  "ai.start",
  "ai.chooseBlocked",
  /**
   * 「AI 로 다시 만들기」 — 고른 구간으로 재녹화 세션을 시작한다 (016 FR-015·FR-018).
   *
   * **누르면 브라우저가 열린다.** 그 사실을 이름 옆에서 **미리** 말해야 한다 —
   * 009 가 `browser.openAt` 에서 세운 규칙이고, 016 의 R6("채팅은 세션 안에서만
   * 산다")이 결정되면서 이 표시가 필수가 됐다. 사용자가 요약 하나 물으려다 브라우저가
   * 뜨는 것을 예상할 수 있어야 한다.
   *
   * 구간 지정은 `step.toggleSelection` 을 재사용한다 — 새 조작을 만들지 않는다.
   */
  "ai.rerecord",
  /**
   * AI 에게 말하기 — 대화 한 차례를 보낸다 (016 FR-007·FR-009).
   *
   * **세션 안에서만 산다** (R6). 편집 국면에서는 보이되 잠기고 `ai.rerecord` 를
   * 가리킨다 — 감추지 않는 이유는 FR-234(감춰진 조작을 만들지 않는다)다.
   *
   * **막힘 답변과 다른 조작이다.** 막혔을 때는 기존 `ai.chooseBlocked` 가 답을 받는다.
   * 답변 입구를 둘로 만들면 사용자는 어느 쪽에 써야 하는지 모른다 (ui-contract §2).
   */
  "ai.chat",
  /** 확정 — 옛 구간을 지우고 교체를 끝낸다 (016 FR-025·FR-026). 자리는 재녹화 띠 */
  "ai.rerecordCommit",
  /**
   * 버리기 — 새로 만든 것을 지우고 도착점으로 되맞춘다 (016 FR-027·FR-031).
   *
   * **세션을 끝내지 않는다** (FR-031a). 끝내는 조작은 기존 `run.stop` 이고, 둘이 같은
   * 일을 하면 사용자는 누를 때마다 차이를 확인하느라 멈춘다.
   */
  "ai.rerecordDiscard",
] as const;

/**
 * 미러 조작 (2) — 010 FR-316 · contracts/mirror-control.md §1.
 *
 * **조작 가능 여부를 권한표에 넣는 것이 요점이다.** 미러 컴포넌트가 국면을 보고 스스로
 * 판단하면, 표 밖에 국면 판정이 하나 더 생긴다. 기존 표의 설계는 「각 국면 열이 그 국면
 * 화면의 전부」인데(`capabilities.ts` 머리말), 표 밖에 두면 그 성질이 깨진다 (research R9).
 */
export const MIRROR_ACTIONS = [
  /**
   * 미러 영역에서 대상 브라우저를 조작한다 (FR-314).
   *
   * 001 에서는 존재하지 않던 조작이다 — 조작 국면은 실제 브라우저 창에서만 성립했고,
   * 미러는 포인터 이벤트를 아예 받지 않았다 (FR-047a). 010 이 그 결정을 뒤집는다.
   */
  "mirror.control",
  /**
   * 실제 브라우저 창으로 조작 위치를 옮긴다 (FR-349·FR-353).
   *
   * **폴백이며, 사용자가 누를 때만 일어난다.** 제품이 상황을 판단해 자동으로 창을 열지
   * 않는다 — 요청하지 않은 창은 그 자체로 조작 위치를 잃게 만들고, 화면 없는 환경에서는
   * 자동 전환이 실패한다 (FR-353).
   */
  "mirror.useWindow",
] as const;

/** 결과·이동 (5) */
export const NAV_ACTIONS = [
  "artifact.select",
  "result.show",
  "nav.editStep",
  "nav.back",
  "tab.select",
] as const;

export const ACTION_IDS = [
  ...RUN_ACTIONS,
  ...AUTHORING_ACTIONS,
  ...STEP_ACTIONS,
  ...TEST_ACTIONS,
  ...AI_ACTIONS,
  ...MIRROR_ACTIONS,
  ...NAV_ACTIONS,
] as const;

export type ActionId = (typeof ACTION_IDS)[number];

/**
 * 조작이 속한 묶음. 화면이 조작을 어느 자리에 놓을지 정할 때 쓴다.
 *
 * `run` 계열은 국면 띠에, `step` 계열은 Step 목록·상세에, `nav` 계열은 헤더에 산다.
 * 자리를 묶음으로 정하면 "같은 자리의 같은 조작" (FR-235)이 배치 규칙으로 보장된다.
 */
export type ActionGroup = "run" | "authoring" | "step" | "test" | "ai" | "nav";

export const ACTION_GROUP: Record<ActionId, ActionGroup> = {
  ...Object.fromEntries(RUN_ACTIONS.map((a) => [a, "run" as ActionGroup])),
  ...Object.fromEntries(AUTHORING_ACTIONS.map((a) => [a, "authoring" as ActionGroup])),
  ...Object.fromEntries(STEP_ACTIONS.map((a) => [a, "step" as ActionGroup])),
  ...Object.fromEntries(TEST_ACTIONS.map((a) => [a, "test" as ActionGroup])),
  ...Object.fromEntries(AI_ACTIONS.map((a) => [a, "ai" as ActionGroup])),
  ...Object.fromEntries(NAV_ACTIONS.map((a) => [a, "nav" as ActionGroup])),
} as Record<ActionId, ActionGroup>;
