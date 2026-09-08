# Phase 1 — 데이터 모델

**기능**: 007 네 화면을 하나로

이 기능은 **저장 형식을 바꾸지 않는다** (FR-250). Step DSL·정의 파일·결과 파일·세션 상태의
스키마는 그대로다. 여기서 정의하는 것은 **화면 안에서만 사는 표시 모델**이다.

권위 정의는 여전히 `backend/src/itb/domain/*.py` 이고, 아래 타입은 그것에서 생성된
`frontend/src/types/generated/*` 를 **소비한다.** 새 저장 개념을 만들지 않는다.

---

## 1. 국면 (Phase)

한 테스트를 놓고 사용자가 지금 있는 위치. **일곱** 이다.

```ts
type Phase =
  | "recording"      // 녹화 — 사람이 대상 앱을 조작해 Step 을 만든다
  | "ai_authoring"   // AI 작성 — AI 가 지시문대로 Step 을 만든다
  | "takeover"       // 사람이 직접 조작 — AI 가 막힌 자리를 사람이 이어받는다
  | "running"        // 실행 중 — 저장된 테스트를 재생한다
  | "paused"         // 일시정지 / 검토 — 세션이 멈춰 있고 편집·저장을 받는다
  | "result"         // 결과보기 — 끝난 실행의 결말과 산출물
  | "editing";       // 편집 — 세션 없이 정의를 고친다
```

### 국면 판정 규칙

**국면은 계산되는 값이며 저장되지 않는다.** 판정은 한 곳에서만 한다.

| 국면 | 판정 |
|---|---|
| `running` | 세션이 있고 `state` 가 실행 중 |
| `paused` | 세션이 있고 `state ∈ {paused, review, lost}` |
| `takeover` | 세션이 있고 `state ∈ {takeover_recording, ai_blocked}` |
| `ai_authoring` | 세션이 있고 `authoring_mode === "ai"` 이며 위 셋이 아니다 |
| `recording` | 세션이 있고 `state === "recording"` (또는 `authoring_mode === "record"` 의 작성 세션) |
| `result` | 세션이 없고 결과를 보고 있다 |
| `editing` | 세션이 없고 정의를 보고 있다 |

**AI 세션 판정은 `authoring_mode` 로 한다 — `state` 가 아니다.** 001 DR-020 이 세운 규칙이고,
상태가 바뀌어도 AI 실패 사유가 유지되는 근거다. 007 이 이것을 흔들면 001 research R2 의
결함이 되살아난다 (FR-253).

**우선순위가 있는 이유**: `takeover_recording` 은 AI 세션의 상태이면서 사람이 조작하는
국면이다. 한 세션이 두 조건을 동시에 만족하므로 순서가 필요하다 — 위 표의 위에서 아래 순서로
판정하며, 그 순서는 현재 `SessionScreen` 의 분기 순서(`isPaused` → `isTakeover` →
`showsAiScreen`)와 같은 결론을 낸다.

---

## 2. 통합 화면 모델 (WorkbenchModel)

국면 어댑터가 만들고 `Workbench` 가 소비하는 **유일한 입력**이다.

```ts
interface WorkbenchModel {
  phase: Phase;
  testId: string | null;          // 아직 저장되지 않은 작성 세션은 null
  testName: string;               // 초안이면 「TC-nnn 초안」 형태 (005 FR-134·U-03)

  phaseBar: PhaseBar;             // 층② — 74px 띠
  target: TargetView;             // 층③ 좌측 위
  aside: PhaseAside | null;       // 층③ 좌측 아래. null 이면 자리를 차지하지 않는다
  steps: WorkbenchStep[];         // 층③ 우측 460px
  focusedStepId: string | null;   // 국면을 넘어 유지된다 (FR-239)
  detail: StepDetail | null;      // 겹침 640px. focusedStepId 가 있을 때만

  capabilities: CapabilityMap;    // 조작 → 상태. 화면이 읽는 유일한 근거 (FR-233)
  notices: Notice[];              // 배너·경고. 국면 띠 아래에 쌓인다
}
```

### 2-1. 국면 띠 (PhaseBar)

```ts
interface PhaseBar {
  /** 국면 표시. 화면에 하나뿐이다 (FR-219) */
  phaseLabel: string;             // 「실행 중」 「일시정지」 「결과」 「편집」 …
  phaseTone: OutcomeTone;         // 색 역할. 색은 보조이며 라벨이 항상 함께 있다
  /** 결말 요약. 화면에 하나뿐이다 (FR-218d · 005 FR-140) */
  runSummary: string | null;
  /** 진행 표시. 실행 중 국면의 `step 04 / 05` 자리 */
  progressLabel: string | null;
}
```

`runSummary` 는 `lib/wording.ts` 의 `runSummary()` 가 만든다. 국면마다 다시 조립하지
않는다 — 지금 결과 화면과 세션 화면이 같은 문장을 각자 만들어 나란히 그린 것이 005 U-19 였다.

### 2-2. 대상 앱 슬롯 (③-a · TargetView)

자리는 고정, **내용은 국면이, 높이도 국면이** 정한다 (FR-244 · FR-256). 높이는 이 타입이
아니라 §2-6 의 배분표가 갖는다 — 내용과 크기를 같은 값에 담으면 어댑터가 크기를 정하게 되고,
그것이 S-12 의 형태다.

```ts
type TargetView =
  | { kind: "mirror"; currentUrl: string; phase: MirrorPhase; tabs: TabsView | null }
  | { kind: "artifacts"; selected: ArtifactKind; available: ArtifactKind[] }
  | { kind: "open_browser"; stepIndex: number | null; blockedReason: string | null }
  | { kind: "empty"; reason: EmptyReason };

/** 왜 비었는지 구별한다 (FR-245 · 005 FR-173) */
type EmptyReason = "not_started" | "not_collected" | "session_lost" | "not_supported";
```

`kind: "empty"` 가 별도 값인 이유는 "아직 시작하지 않음" 과 "수집하지 않음" 과 "세션 유실"
이 사용자에게 서로 다른 다음 행동을 요구하기 때문이다. 지금 결과 화면의 빈 산출물 탭이
"(기록 없음)" 한 줄이었던 것이 005 U-22 다.

### 2-3. 국면 작업 영역 (③-b · WorkAreaView)

③-a 대상 앱 슬롯 **아래**. 그 국면에서 사용자가 **실제로 하는 일**의 유일한 자리
(FR-218e · FR-218e-1).

> **이름이 「국면 보조 영역」에서 바뀐 이유** (FR-218e-1). 1회차의 이름은 이 자리가 담는
> 것을 보조로 규정했고, 그 규정이 편집 폼 전체를 42px 띠에 넣는 판단으로 이어졌다 (S-12).
> 이름은 판단을 유도한다.

```ts
type WorkAreaView =
  | { kind: "compose_form"; startUrl: string; mode: ComposeMode | null;
      instruction: string; error: ErrorInfo | null }
  | { kind: "ai_progress"; instruction: string; messages: string[];
      error: ErrorInfo | null; blocked: AiBlockedState | null }
  | { kind: "takeover_guide"; recording: boolean; blocked: AiBlockedState | null }
  | { kind: "paused_tools"; assertionDraft: AssertionDraft | null; reordering: boolean }
  | { kind: "run_progress"; label: string; pacing: ReactNode | null }
  | { kind: "failure_detail"; step: StepResult; diagnosis: string | null;
      attempts: LocatorAttempt[] | null }
  | { kind: "edit_fields"; pendingCount: number; warnings: string[];
      stale: StaleInfo | null; fields: ReactNode };

/** 만들기 국면의 방법 2택. 「빈 테스트」는 없다 — 제품에 없는 조작이다 (FR-258a) */
type ComposeMode = "record" | "ai";
```

**2회차가 더한 것 셋**:

| 값 | 왜 | 요구사항 |
|---|---|---|
| `compose_form` | 만들기가 여덟째 국면이 되었다 | FR-258 |
| `failure_detail.attempts` | 시도한 locator 기록이 겹침 상세에만 있어 결과 국면의 답이 두 자리로 갈렸다 (S-13) | FR-262 |
| `run_progress` | 실행 중·녹화 국면의 42px 띠를 이 타입 안으로 들인다. 1회차는 어댑터가 `noticesExtra` 로 우회해 넣었고, 그래서 배분표에 잡히지 않았다 | FR-256 |

`edit_summary` → `edit_fields` 로 이름을 바꾼다. 요약이 아니라 편집면이 이 자리의 주 내용
이기 때문이다 (FR-257).

**`error` 와 `blocked` 는 국면 상태와 무관하게 그린다** (FR-218f · FR-253). 값이 있으면
보인다 — 접힘·탭·겹침 뒤에 두지 않는다. 001 research R2 가 규명한 결함이 정확히 "실패를
그리는 유일한 컴포넌트가 조건 뒤에 숨은 것" 이었다.

### 2-4. Step 행 (WorkbenchStep)

**단일 구현이 그리는 단일 모델** (FR-221·FR-222).

```ts
interface WorkbenchStep {
  id: string;                     // 정의의 Step.id = 결과의 step_id (runner.py:398)
  index: number;                  // 0-based. 표시는 stepNumber() 가 1-based 로 (FR-224)
  step: Step | null;              // 정의에서. 결과 국면에서 매칭 실패면 null (R3)
  label: string;                  // 결과 국면은 결과의 label, 그 외는 step.label
  outcome: StepOutcome;           // 아래 확장 참조
  durationMs: number | null;      // 결과·실행에서. 그 외 null → 자리를 비운다 (FR-223)
  isPausedHere: boolean;          // 일시정지 위치 (FR-034)
}
```

**`StepOutcome` 확장** — `recorded` 를 더한다 (R4).

```ts
type StepOutcome =
  | "pass" | "fail" | "running" | "pending" | "skipped" | "not_run"
  | "recorded";                   // 기록됨 — 작성 국면. 통과가 아니다 (FR-225)
```

행 안의 칸 순서는 **국면과 무관하게 고정**이다 (FR-222).

```
[번호 26px] [이름 + 동작 칩 + 탭 배지 + 대상 요약 + 값] [소요 시간] [결말 표식 24px]
```

`step === null` 인 행은 동작 칩·탭 배지·대상 요약·값 칸이 비고, **다른 칸이 그 자리로
당겨지지 않는다** (FR-223).

### 2-5. Step 상세 (StepDetail)

겹침 640px. 모든 국면에서 같은 자리·같은 구성 (FR-230).

```ts
interface StepDetail {
  step: Step | null;              // 정의에서
  index: number;
  /** 그 실행에서 실제로 시도한 locator. 결과 국면에만 있다 */
  attempts: LocatorAttempt[] | null;
  /** 정의가 가진 후보와 그 적용 순서. 순서는 제품 전역 고정 (Principle IV) */
  candidates: TargetLocator | null;
  dropCandidates: TargetLocator | null;   // drag 는 대상이 둘이다
  repickWaiting: RepickSlot | null;
  failure: { code: ErrorCode | null; message: string | null } | null;
}
```

`attempts` 와 `candidates` 를 **둘 다** 두는 이유: 결과 국면에서 사용자가 알아야 하는 것은
"정의에 무엇이 있는가" 가 아니라 "그때 무엇을 시도했고 왜 못 찾았는가" 다. 편집 국면에서는
반대다. 한 칸에 뭉개면 국면에 따라 같은 자리가 다른 뜻을 갖게 된다.

---

### 2-6. 세로 배분 (VerticalSplit)

③ 좌측 두 자리가 남는 높이를 나누는 방식. **국면이 정하고, 표가 소유한다** (FR-256 ·
research R9).

```ts
type SlotSize =
  /** 남는 높이 전부 */
  | { kind: "fill" }
  /** 내용에 맞는 높이 (최소 42px) */
  | { kind: "content" }
  /** 정해진 높이 */
  | { kind: "fixed"; px: number };

interface VerticalSplit {
  targetSlot: SlotSize;   // ③-a
  workArea: SlotSize;     // ③-b
}

/** `Record<Phase, …>` 이므로 국면을 더하면 컴파일러가 배분을 요구한다 */
const VERTICAL_SPLIT: Record<Phase, VerticalSplit>;
```

| 국면 | ③-a | ③-b | 근거 |
|---|---|---|---|
| `composing` | `fixed 118` | `fill` | 아직 열지 않았다는 사실만 필요하다. 하는 일은 시작 조건 입력이다 (FR-258) |
| `recording` | `fill` | `content` | 미러를 보면서 조작한다. ③-b 는 42px 안내 띠 (B9) |
| `ai_authoring` | `fill` | `content` | 미러 + 지시문·진행·차단. 차단 시 내용이 늘어난다 (B10) |
| `takeover` | `fill` | `content` | 녹화와 같다 |
| `running` | `fill` | `content` | 미러 + 진행 한 줄·실행 속도 |
| `paused` | `fill` | `content` | 미러를 보면서 고친다. 검증 추가 폼이 펼쳐지면 늘어난다 |
| `result` | `fill` | `fixed 424` | 산출물이 남는 높이. ③-b 는 사유 + locator 4행이 스크롤 없이 들어가는 높이 (B4) |
| `editing` | `fixed 118` | `fill` | 브라우저 여는 조작만 필요하다. 하는 일은 Step 편집이다 (FR-261) |

**불변식 둘 — 한 국면에서 두 자리가 동시에 `fill` 일 수 없고, 동시에 `content` 일 수도
없다.** 앞은 그 국면의 주 작업이 어느 자리인지 화면이 말하지 못하게 하고, 뒤는 남는 높이를
어디로도 보내지 않는다. 검사가 둘 다 센다 (SC-010 · UC-100).

**주 자리 선언 — `PRIMARY_SLOT: Record<Phase, "target" | "work">`.** 검사가 「주 작업」을
알 방법이 필요하다 (`analyze` A1). 배분표와 같은 파일에 두고, 크기가 큰 쪽이 이 선언과
일치하는지 센다.

`content` 의 최소 42px 은 1회차 값을 그대로 쓴다 (`RunnerPaused`·`Takeover` 의 국면 안내
띠). `fixed 118` 은 46px 버튼 + 상하 여백이며 승인 대상이다 (B1).

**이 표는 표시 컴포넌트가 읽지 않는다.** `Workbench` 가 국면으로 조회해 두 자리에 `flex`
값으로 내려 준다 — `TargetPane`·작업 영역은 자기 크기를 모른다. 1회차에는 둘이 각자
하드코딩했고 그것이 S-12 였다.

---

## 3. 조작 권한 (Capability)

```ts
/** 조작 하나의 식별자. 목록은 contracts/ui-contract.md §2 가 정본 */
type ActionId = string;

type CapabilityState =
  /** 쓸 수 있다 */
  | { kind: "enabled" }
  /** 쓸 수 없다 — 같은 자리에 비활성으로 남기고 이유를 붙인다 (FR-234) */
  | { kind: "disabled"; reason: string; remedy: Remedy | null }
  /** 이 국면의 조작이 아니다 — 그리지 않는다 (research R5) */
  | { kind: "not_applicable" };

/** 쓸 수 있게 하는 방법. 안내가 화면에 없는 조작을 지시하지 않게 한다 (006 E-03) */
interface Remedy {
  label: string;
  action: ActionId;               // 이 화면에 실제로 있는 조작만 가리킨다
}

type CapabilityMap = Record<ActionId, CapabilityState>;
```

### 판정의 두 층

```
기본 표 (국면 × 조작)          →  runtime 덮어쓰기            →  최종 CapabilityState
capabilities.ts 의 정적 데이터      실행 요청 진행 중 / Step 0개
                                    / 저장할 변경 없음 / 잠긴 항목
```

두 층 모두 **한 함수**를 지난다. 덮어쓰기를 화면에 흩으면 한 화면이 빠뜨리고, 빠진 화면에서
연타하면 브라우저가 둘 뜬다 (005 U-06).

`Remedy.action` 이 **이 화면에 실제로 있는 조작만** 가리키게 하는 것은 006 E-03 의 수정이다 —
"실행을 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로 가는 버튼을 주지 않은 것.

---

## 4. 알림 (Notice)

국면 띠 아래에 쌓인다. 지금 배너가 화면마다 다른 자리에 있는 것을 하나로 모은다.

```ts
interface Notice {
  id: string;
  tone: "error" | "warn" | "info";
  role: "alert" | "status" | "note";      // 접근성. 지금 각 화면이 개별로 정한다
  message: string;
  nextAction: string | null;              // 003 EC-004 — 다음 행동이 붙는다
  action: { label: string; actionId: ActionId } | null;
  dismissible: boolean;
}
```

007 이 통합해야 하는 기존 배너: 연결 끊김 · 세션 유실 · 실행 거절(409) · 편집 잠김 ·
외부 변경 충돌 · 저장하지 않은 변경 · 부분 실행 진단 · 정의 파일 오류 ·
**결과 이후 정의 변경**(R3 이 새로 만드는 것).

`nextAction` 이 별도 칸인 이유는 003 EC-004 다 — 문자열로 뭉개면 "대상 앱에 연결할 수
없습니다" 뒤에 와야 하는 "떠 있는지 확인하세요" 가 사라진다.

---

## 5. 맥락 (WorkbenchLocation)

주소에 남고 새로 고침에서 복원되는 값 (FR-240).

```ts
interface WorkbenchLocation {
  phase: Phase;
  testId: string | null;
  stepId: string | null;          // 지목한 Step (006 FR-181)
  sessionId: string | null;       // 세션 국면에만
}
```

**세션 국면은 주소만으로 복원하지 않는다.** 005 가 정한 규칙이며 이유는 죽은 세션 화면을
그릴 수 있기 때문이다. 새로 고침하면 목록으로 가고, 살아 있는 세션은 목록의 세션 배너가
되찾는다 (005 FR-168). 007 은 이 규칙을 유지하되 **`stepId` 는 잃지 않는다** — 세션 국면의
지목 Step 은 세션 복귀 시 함께 복원된다.

`result` · `editing` 국면은 주소만으로 완전히 복원된다 (지금도 그렇다).

**`composing` 국면은 국면만 남긴다** (2회차 · research R12). `testId` 도 `stepId` 도 없고,
입력 중인 시작 주소·지시문·고른 방법은 주소에 싣지 않는다 — 새로 고침으로 되살릴 대상이
아니다. 옛 이름 `create` · `ai-compose` 로 들어온 주소는 `composing` 으로 정규화한다.

---

## 6. 무엇을 만들지 않는가

- **새 저장 개념** — 국면·권한·모델은 전부 계산되는 값이다. 파일에 쓰지 않는다.
- **Step DSL 필드 추가** — `recorded` 는 화면 표시 값이며 DSL 의 값이 아니다 (FR-250).
- **전역 상태 저장소** — 소유는 국면 어댑터에 있고, 모델은 그 아래로만 흐른다 (R2).
- **브라우저 저장소에 초안 보관** — 006 research R8 이 이미 배제했다. 정의 파일이 유일한
  진실이다.
- **만들기 국면의 테스트 이름 · 「빈 테스트」 방법** — 현재 제품에 없는 조작이다. 이름은
  저장 시점(일시정지 국면)에 정한다 (FR-258a · research R11).
- **배분값을 어댑터가 넘기는 통로** — `WorkbenchModel` 에 세로 배분을 싣지 않는다. 어댑터가
  넷이므로 판단이 넷으로 흩어지고, 하나가 빠지면 그 국면에서만 역전이 되살아난다 (R9).
