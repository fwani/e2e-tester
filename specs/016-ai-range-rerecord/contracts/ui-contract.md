# UI Contract — 016 편집 중 AI 구간 재녹화

**Date**: 2026-09-11 | 기준 계약: `specs/011-authoring-ux-repair/contracts/ui-contract.md` ·
`frontend/src/lib/actions.ts` · `frontend/src/lib/capabilities.ts`

**델타 문서다.** 조작 4개가 늘고 2개가 개칭되며, 국면표에 4행이 추가된다.

---

## 1. 조작 목록 — 42 → 46

### 1-1. 추가 4개 (전부 `ai` 묶음)

| 식별자 | 이름 | 자리 | 무엇을 하는가 |
|---|---|---|---|
| `ai.rerecord` | AI 로 다시 만들기 | 조작 팔레트 | 고른 구간으로 재녹화 세션을 시작한다. **누르면 브라우저가 열린다** |
| `ai.chat` | AI 에게 말하기 | 대화 패널 | 대화 한 차례를 보낸다 |
| `ai.rerecordCommit` | 확정 | 재녹화 띠 | 옛 구간을 지우고 교체를 끝낸다 |
| `ai.rerecordDiscard` | 버리기 | 재녹화 띠 | 새로 만든 것을 지우고 도착점으로 되맞춘다 |

`AI_ACTIONS` 가 3 → 7 이 된다.

**`ai.rerecord` 는 브라우저를 연다는 것을 이름 옆에서 미리 말한다.** 009 가
`browser.openAt` 에서 세운 규칙이고, R6 이 「채팅은 세션 안에서만 산다」를 결정하면서
이 표시가 필수가 됐다 — 사용자는 요약 하나 물으려다 브라우저가 뜨는 것을 예상할 수
있어야 한다.

### 1-2. 개칭 2개 (`step` 묶음, 수는 그대로)

| 지금 | 바뀐 뒤 | 왜 |
|---|---|---|
| `step.toggleDeleteTarget` | `step.toggleSelection` | 016 이 같은 체크를 **재녹화 구간 지정**에도 쓴다. 이름이 삭제 전용이면 거짓이 된다 |
| `step.selectAllDeleteTargets` | `step.selectAll` | 같은 이유 |

**개칭에는 전례가 있다.** 009 가 `step.reorder → step.moveUp` 으로 했고, 그 근거가
「이전 이름은 두 방향을 뜻하는 것처럼 읽히면서 실제로는 위로만 옮겼다」였다. 여기도 같다 —
체크의 뜻이 하나에서 둘로 늘었으므로 이름이 뜻을 따라가야 한다.

**개칭은 조작이 아니다.** `step.deleteSelected`·`step.deleteAfter` 는 이름을 바꾸지
않는다. 그것들은 실제로 삭제만 한다.

### 1-3. 새 조작을 만들지 **않은** 것

| 안 만든 것 | 대신 쓰는 것 | 왜 |
|---|---|---|
| 구간 지정 | `step.toggleSelection` (개칭) | 체크 칸을 둘로 만들면 사용자가 어느 쪽에 체크할지 판단해야 한다 |
| 재녹화 중 편집 | 기존 `step.update`·`step.delete` 등 | `paused` 국면의 편집 조작이 그대로 성립한다 |
| 재녹화 중지 | 기존 `run.stop` | 세션을 끝내는 조작은 하나여야 한다 (FR-031a) |

---

## 2. 국면표 델타 — 4행 × 10열

셀 기호: `ON` 활성 · `off(사유, 해소)` 비활성 · `na(근거)` 해당 없음 · `cond(키)` 조건부.
`N1` 이미 충족 · `N2` 대상 없음 · `N3` 세션 없음. `C2` 브라우저 살아 있음 ·
`C7` 정의 편집 가능 · `C11` AI 막힘.

| 국면 | `ai.rerecord` | `ai.chat` | `ai.rerecordCommit` | `ai.rerecordDiscard` |
|---|---|---|---|---|
| **composing** | `na(N2)` 고칠 테스트가 없다 | `na(N2)` | `na(N2)` | `na(N2)` |
| **recording** | `na(N1)` 이미 만드는 중 | `off(NEEDS_PAUSE, run.pause)` | `na(N2)` | `na(N2)` |
| **ai_authoring** | `off(AI_RUNNING, run.stop)` | `off(AI_RUNNING, run.pause)` | `off(AI_RUNNING, run.pause)` | `off(AI_RUNNING, run.pause)` |
| **takeover** | `off(AI_RUNNING, run.stop)` | `off(USE_BLOCKED_ANSWER, ai.chooseBlocked)` | `off(NEEDS_PAUSE, run.resume)` | `off(NEEDS_PAUSE, run.resume)` |
| **running** | `off(RUNNING_NO_EDIT, run.pause)` | `off(RUNNING_NO_EDIT, run.pause)` | `off(RUNNING_NO_EDIT, run.pause)` | `off(RUNNING_NO_EDIT, run.pause)` |
| **paused** | `off(ALREADY_IN_SESSION)` | **`ON`** | `cond(C16)` | `cond(C17)` |
| **review** | `off(NEEDS_BROWSER, run.all)` | `off(NEEDS_BROWSER, run.all)` | `na(N3)` 브라우저가 없다 | `na(N3)` |
| **finished** | `off(RUN_FINISHED_NO_EDIT, save)` | `off(RUN_FINISHED_NO_EDIT, save)` | `na(N2)` | `na(N2)` |
| **result** | `off(RESULT_NO_EDIT, nav.editStep)` | `off(RESULT_NO_EDIT, nav.editStep)` | `na(N2)` | `na(N2)` |
| **editing** | **`cond(C7)`** | `off(NEEDS_SESSION, ai.rerecord)` | `na(N3)` | `na(N3)` |

### 새 조건 2개

| 키 | 사실 | 뜻 |
|---|---|---|
| `C16` | `canCommitRerecord` | 트랜잭션이 있고 만든 Step 이 1개 이상이다 (불변식 10) |
| `C17` | `hasRerecord` | 트랜잭션이 있고 아직 끝나지 않았다 |

**둘 다 서버가 판정한다.** `SessionView.rerecord.can_commit` 이 `C16` 의 사실이고,
`rerecord !== null` 이 `C17` 이다. 화면이 조건을 복제하면 서버와 갈린다 — 005 U-01 이
그 형태였다.

### 새 비활성 사유 2개

| 키 | 문구 |
|---|---|
| `ALREADY_IN_SESSION` | 이미 세션이 열려 있습니다. 이 세션 안에서 대화로 진행하세요 |
| `NEEDS_SESSION` | AI 와 대화하려면 먼저 「AI 로 다시 만들기」로 시작하세요 |
| `USE_BLOCKED_ANSWER` | AI 가 막혀 있습니다. 위의 답변 칸에 알려 주세요 |

**`USE_BLOCKED_ANSWER` 가 왜 필요한가**: 초안은 takeover 국면의 `ai.chat` 을
`cond(C11)`(막힘일 때 활성)로 뒀다. 그것은 **답변 입구를 둘로 만드는 것**이고, 바로 아래
§3-1 이 금지하는 것(「막힘은 대화 패널이 그리지 않는다」)과 같은 문서 안에서 충돌했다.
API 계약도 채팅 게이트를 `paused` 하나로 정한다 (api-contract §2-1). 답변 입구는 기존
`ai.chooseBlocked` 하나이고, 대화 패널은 그리로 **가리킨다.**

### 이 표에서 읽어야 할 두 가지

1. **`editing` 행의 `ai.rerecord` 가 `cond(C7)` 이다.** `ON` 이 아닌 이유는 009 T063 이
   고친 결함 때문이다 — 다른 세션이 그 테스트를 잡고 있으면 서버가 `409` 로 거절하는데,
   화면이 활성으로 그리면 눌린 뒤에 거절된다. `step.recordStart`·`step.addNaturalLanguage`
   가 같은 자리에서 같은 판정을 받는다.

2. **`editing` 행의 `ai.chat` 이 `off(NEEDS_SESSION)` 이다.** 이것이 R6 의 결정이
   표에 나타난 형태다. 채팅 자리는 편집 화면에도 **보이되** 잠겨 있고, 해소 조작
   (`ai.rerecord`)을 가리킨다. 감추지 않는 이유는 FR-234(감춰진 조작을 만들지 않는다)다.

### 가시성 (`ALWAYS_KEEP` · `visibilityOf`)

| 조작 | 비활성일 때 | 왜 |
|---|---|---|
| `ai.rerecord` | **보인다** (`keep`) | 편집 화면에서 이 기능의 존재를 알 수 있어야 한다 |
| `ai.chat` | **보인다** (`keep`) | 위와 같음. `NEEDS_SESSION` 이 해소 조작을 가리킨다 |
| `ai.rerecordCommit` | `na` 국면에서는 감춤 | 재녹화 중이 아닌 화면에 확정 버튼이 있을 이유가 없다 |
| `ai.rerecordDiscard` | 같음 | 같음 |

---

## 3. 화면 요소

### 3-1. 대화 패널 (`ChatPanel`)

| 요소 | 규칙 |
|---|---|
| 이력 | `chat_turn` 이벤트로 누적. 새로 고치면 `GET /chat` 으로 되찾는다 |
| 입력 | `MAX_INSTRUCTION_CHARS` 상한을 **입력 시점에** 보여준다 (FR-010) |
| 진행 표시 | `ai_progress` 이벤트를 그대로 쓴다 (기존) |
| 중지 | `run.pause` 를 재사용한다. 새 버튼을 만들지 않는다 (FR-011) |
| 언어모델 없음 | `GET /api/ai/availability` 의 `reason` 을 그대로 보여준다 (FR-012). 나머지 편집은 영향 없음 |

**막힘은 대화 패널이 그리지 않는다.** 기존 `ai_blocked` 처리(5선택지)가 그대로 뜬다.
두 곳에서 그리면 사용자는 어느 쪽에 답해야 하는지 모른다.

### 3-2. 재녹화 띠 (`RerecordBar`)

`rerecord !== null` 일 때만 나타난다.

```
┌──────────────────────────────────────────────────────────────┐
│ 교체 중 — Step 5~9 (5개)      새로 만든 것 3개   [확정] [버리기] │
└──────────────────────────────────────────────────────────────┘
```

- `확정` 은 `can_commit` 이 거짓이면 비활성이고, 사유를 말한다 (「먼저 Step 을 만드세요」)
- `버리기` 는 만든 것이 없어도 활성이다 — 그만두는 것은 정상이다

### 3-3. Step 목록의 「교체 대상」 표시

`range_step_ids` 에 든 Step 을 구분해 그린다. **Step 자체에는 아무 표시도 없다**
(불변식 7) — 화면이 세션이 준 id 목록과 대조해 계산한다.

시각 표현은 008 시각 언어의 기존 어휘를 쓴다. 새 색·새 모양을 만들지 않는다.

### 3-4. 되맞춤 실패 안내

`rerecord_realign_failed` 이벤트가 오면 **두 사실을 한 자리에서** 말한다 (불변식 11).

> 새로 만든 Step 을 되돌렸습니다. 다만 화면을 원래 위치로 되돌리지 못했습니다
> (Step 3 에서 실패). 화면과 목록이 어긋나 있으므로 세션을 닫는 것을 권합니다.

---

## 4. 검사에 미치는 영향

| 검사 | 무엇이 바뀌는가 |
|---|---|
| `CapabilityCoverage.test.ts` | 조작 수 42 → 46. 개칭 2건 반영. 새 조건 C16·C17 의 사실 이름 등록 |
| `CapabilityUI.test.tsx` | 새 조작 4개의 **자리**가 화면에 실제로 있는지 (FR-235 한 조작에 한 자리) |
| `ActionPalette` 주석 | `ai.rerecord` 가 팔레트에 산다는 사실 추가 |
| 국면표 행 수 | 국면 10개 × 조작 46개 = 460 셀. 빠진 셀은 타입 오류로 잡힌다 |
