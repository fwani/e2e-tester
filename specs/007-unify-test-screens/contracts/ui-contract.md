# UI 계약 — 통합 작업 화면과 국면별 조작 권한

**기능**: 007 · 요구사항 FR-217 ~ FR-255
**성격**: 이 문서는 **계약**이다. 화면은 여기 적힌 것만 따르고, 여기 없는 판단을 화면에서
하지 않는다. REST 계약이 서버와 클라이언트 사이의 약속이듯 이것은 요구사항과 화면 사이의
약속이다.

> **UC-000 — 표가 정본이다.**
> 조작이 어느 국면에서 어떤 상태인지는 §3 의 표가 정한다. 컴포넌트가 스스로 판단하지 않는다.
> 표와 코드가 다르면 **코드를 고친다.** 단 하나의 예외는 UC-401 이다 — 현재 쓸 수 있는
> 조작이 표에서 「해당 없음」이면 그것은 표의 오류이며 표를 고친다 (FR-247).

---

## 1. 화면 문법

### 1-1. 3층 구조

일곱 국면 전부가 같다 (FR-217·FR-218c). 층의 구성·순서·개수는 국면에 따라 바뀌지 않는다.

```
┌──────────────────────────────────────────────────────────────┐  1440 (최소 기준 폭)
│ ① 헤더                                            flex 0 0 60px │
│    제품 표시 · 구분선 · 경로(테스트 식별) · 국면 알약           │
├──────────────────────────────────────────────────────────────┤
│ ② 국면 띠                                         flex 0 0 74px │
│    국면 표시 → 테스트 이름 → 결말 요약 → 그 국면의 주요 조작    │
├──────────────────────────────────────────────────────────────┤
│    알림(Notice) — 있을 때만. 국면 띠 아래에 쌓인다              │
├────────────────────────────────────┬─────────────────────────┤
│ ③ 좌: 대상 앱 영역                  │ ③ 우: Step 목록          │
│    미러 / 산출물 / 브라우저 열기      │    flex 0 0 460px       │
│    남는 폭 전부 (FR-218a)           │    StepPanelHeader 50px │
│  ──────────────────────────────────  │    + Step 행 (단일 구현) │
│    국면 보조 영역                    │                         │
│    최소 170px · 없으면 자리 없음      │                         │
└────────────────────────────────────┴─────────────────────────┘
        Step 상세 — 우측에서 겹치는 640px 패널 (모든 국면 동일)
```

### 1-2. 치수의 근거

**모든 값은 확정 디자인에서 기계적으로 추출했다.** 새로 정한 값은 §1-4 에만 있다.

| 항목 | 값 | 근거 |
|---|---|---|
| 헤더 높이 | 60px | `Main` · `RunnerPaused` · `Takeover` · `AiRecord` · `RunResult` 5종 공통 |
| 국면 띠 높이 | 74px | 같은 5종 공통 |
| Step 패널 폭 | 460px | `Main` · `RunnerPaused` · `Takeover` 3종 공통 |
| 국면 보조 최소 높이 | 170px | 세션 4종 공통 (`flex: 0 0 170px`) |
| Step 상세 폭 | 640px | `StepInspector.dc.html` 기준 폭 |
| 최소 기준 폭 | 1440px | 6종 공통 |
| 영역 구분선 | 3px solid `#14130F` | 002 §3 — 확정 디자인 67회 |
| 화면 배경 | `#EFEBE0` | 002 §3 |

### 1-3. 좁은 창

최소 기준 폭 1440px 보다 좁으면 **재배치하지 않고 스크롤한다** (DC-011 유지 · FR-218).
넓으면 **좌측 대상 앱 영역만** 늘어난다 (FR-218a). Step 패널 460px 은 고정이다.

### 1-4. 새로 정하는 값 — 승인 대상

`research.md` R8 의 A1~A5. 승인 전에는 초안이며 대조 기준이 아니다 (FR-254c).

---

## 2. 조작 목록

**이 목록이 FR-247(조작 손실 0건)의 검사 대상이다.** `출처` 는 지금 그 조작을 제공하는
파일이며, 통합 후 그 파일이 사라져도 조작은 남아야 한다.

### 2-1. 실행·세션 (10)

| id | 라벨(현행) | 출처 |
|---|---|---|
| `run.all` | 처음부터 실행 | `RunResult.onRunAll` · `TestDefinition.onRun` |
| `run.from` | Step nn 부터 실행 (새 세션) | `RunResult.onRunFrom` · `TestDefinition.onRun(index)` |
| `run.fromHere` | Step nn 부터 이어 실행 (열린 세션 안) | `RunnerPaused.onRunFrom` → `sessions.runFrom` |
| `run.pause` | 일시정지 | `Runner.onPause` · `AiRecord.onPause` |
| `run.resume` | 계속하기 / AI 에게 돌려주기 | `RunnerPaused.onResume` · `Takeover.onResume` |
| `run.resumeSkipFailure` | 실패 건너뛰고 계속 | `RunnerPaused.onResumeSkippingFailure` |
| `run.stop` | 중지 / 닫기 / 나가기 | 세션 4화면 전부 |
| `run.pacing` | 실행 속도 | `SessionScreen` 의 `PacingControl` |
| `browser.openAt` | 브라우저 열어 Step nn 에서 멈추기 | `TestDefinition.onOpenBrowserAt` |
| `session.open` | 실행 중인 세션 보기 | `TestDefinition.onOpenSession` · `App` 의 거절 배너 |

### 2-2. Step 작성 (4)

| id | 라벨(현행) | 출처 |
|---|---|---|
| `step.recordStart` | 직접 조작으로 Step 추가 | `RunnerPaused.onRecordActionsStart` · `Runner.onAddStep` |
| `step.recordStop` | 기록 멈추기 | `RunnerPaused.onRecordActionsStop` · `Takeover.onStopRecording` |
| `step.addNaturalLanguage` | 자연어로 Step 추가 | `RunnerPaused.onNaturalLanguage` |
| `step.addAssertion` | 검증 추가 | `RunnerPaused.onAddAssertion` |

### 2-3. Step 편집 (6)

| id | 라벨(현행) | 출처 |
|---|---|---|
| `step.select` | Step 지목 | `Runner`·`RunnerPaused`·`Takeover`.`onSelectStep` · `RunResult.onEditStep` · `TestDefinition` 내부 |
| `step.update` | 표시 이름 · 값 · 대기 시간 수정 | `StepInspector.onSave` · `TestDefinition` 의 `StepEditFields` |
| `step.markSensitive` | 민감 지정 | `StepInspector` 의 `InlineSecretInput` |
| `step.repick` | 요소 다시 집기 | `StepInspector.onRepick` |
| `step.delete` | Step 삭제 | `RunnerPaused.onDeleteStep` · `TestDefinition` 의 삭제 |
| `step.reorder` | 순서 변경 | `RunnerPaused.onToggleReorder`·`onApplyReorder` · `TestDefinition` 의 ↑↓ |

### 2-4. 테스트 속성·저장 (5)

| id | 라벨(현행) | 출처 |
|---|---|---|
| `test.rename` | 테스트 이름 | `TestDefinition` 의 `set_name` · `RunnerPaused`·`AiRecord`.`onSaveNameChange` |
| `test.setStartUrl` | 시작 주소 | `TestDefinition` 의 `set_start_url` |
| `save` | 저장 / 변경 저장 | `RunnerPaused.onSave` · `AiRecord.onSave` · `TestDefinition` 의 저장 |
| `save.overwriteStale` | 그래도 덮어쓰기 | `TestDefinition` 의 외부 변경 충돌 |
| `edits.revert` | 변경 전부 되돌리기 | `TestDefinition` 의 `setOps([])` |

### 2-5. AI (3)

| id | 라벨(현행) | 출처 |
|---|---|---|
| `ai.compose` | 지시문 쓰기·고치기 | `AiCompose` · `AiRecord.onInstructionChange` |
| `ai.start` | AI 시작 | `AiRecord.onStart` |
| `ai.chooseBlocked` | 막힌 자리 선택지 고르기 | `Takeover.onChoose` |

### 2-6. 결과·이동 (5)

| id | 라벨(현행) | 출처 |
|---|---|---|
| `artifact.select` | 산출물 종류 고르기 | `RunResult` 의 `TABS` |
| `result.show` | 결과 보기 | `RunnerPaused.onShowResult` |
| `nav.editStep` | 이 Step 고치기 | `RunResult.onEditStep` |
| `nav.back` | 목록으로 / 나가기 | `RunResult.onBack` · `TestDefinition.onBack` · `RunnerPaused.onShowList` |
| `tab.select` | 탭 고르기 | `SessionScreen` 의 `TabStrip` (FR-030a) |

**합계 33.** 지금 7개 화면에 흩어져 있고, 같은 일이 다른 이름으로 여러 곳에 있다 — Step
지목이 `onSelectStep`(3곳) · `onEditStep`(2곳) · 내부 상태(1곳)로 셋이다.

---

## 3. 권한표

**기호**

| 기호 | 뜻 | 화면이 하는 일 |
|---|---|---|
| ● | 가능 | 그린다. 누를 수 있다 |
| ○ | 비활성 | **같은 자리에 그린다.** 누를 수 없고, 이유와 해소 방법이 붙는다 (FR-234) |
| ◐ | 런타임 조건 | 표 아래 조건이 정한다. 조건이 거짓이면 ○ 이고 이유가 붙는다 |
| – | 해당 없음 | 그리지 않는다. **§4-2 의 근거가 있어야 쓸 수 있다** |

**국면 약칭**: REC 녹화 · AI 작성 · TKO 사람이 직접 조작 · RUN 실행 중 ·
PAU 일시정지/검토 · RES 결과보기 · EDT 편집

### 3-1. 실행·세션

| 조작 | REC | AI | TKO | RUN | PAU | RES | EDT |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `run.all` | – | – | – | ○ | ◐ C1 | ● | ● |
| `run.from` | – | – | – | ○ | ◐ C1 | ● | ● |
| `run.fromHere` | – | – | – | – | ◐ C2 | – | – |
| `run.pause` | ● | ● | – | ● | – | – | – |
| `run.resume` | – | – | ● | – | ◐ C2 | – | – |
| `run.resumeSkipFailure` | – | – | – | – | ◐ C3 | – | – |
| `run.stop` | ● | ● | ● | ● | ● | – | – |
| `run.pacing` | ● | ● | ◐ C4 | ● | ◐ C2 | – | – |
| `browser.openAt` | – | – | – | – | – | ○ | ● |
| `session.open` | – | – | – | – | – | ◐ C5 | ◐ C5 |

### 3-2. Step 작성

| 조작 | REC | AI | TKO | RUN | PAU | RES | EDT |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `step.recordStart` | – | ○ | ● | ○ | ◐ C2 | ○ | ○ |
| `step.recordStop` | ● | – | ◐ C6 | – | ◐ C6 | – | – |
| `step.addNaturalLanguage` | ○ | ○ | ○ | ○ | ◐ C2 | ○ | ○ |
| `step.addAssertion` | ○ | ○ | ○ | ○ | ◐ C2 | ○ | ○ |

### 3-3. Step 편집

| 조작 | REC | AI | TKO | RUN | PAU | RES | EDT |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `step.select` | ● | ● | ● | ● | ● | ● | ● |
| `step.update` | ○ | ○ | ○ | ○ | ● | ○ | ◐ C7 |
| `step.markSensitive` | ○ | ○ | ○ | ○ | ● | ○ | ◐ C7 |
| `step.repick` | ○ | ○ | ● | ○ | ◐ C2 | ○ | ○ |
| `step.delete` | ○ | ○ | ○ | ○ | ● | ○ | ◐ C7 |
| `step.reorder` | ○ | ○ | ○ | ○ | ● | ○ | ◐ C7 |

### 3-4. 테스트 속성·저장·AI·이동

| 조작 | REC | AI | TKO | RUN | PAU | RES | EDT |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `test.rename` | ● | ● | ● | ○ | ● | ○ | ◐ C7 |
| `test.setStartUrl` | – | – | – | ○ | ○ | ○ | ◐ C7 |
| `save` | ◐ C8 | ◐ C8 | ◐ C8 | ○ | ◐ C8 | – | ◐ C9 |
| `save.overwriteStale` | – | – | – | – | – | – | ◐ C10 |
| `edits.revert` | – | – | – | – | – | – | ◐ C9 |
| `ai.compose` | – | ○ | ○ | – | – | ○ | ○ |
| `ai.start` | – | ○ | – | – | – | – | – |
| `ai.chooseBlocked` | – | – | ◐ C11 | – | – | – | – |
| `artifact.select` | – | – | – | – | – | ● | – |
| `result.show` | – | – | – | – | ◐ C12 | – | ◐ C13 |
| `nav.editStep` | – | – | – | – | – | ● | – |
| `nav.back` | ● | ● | ● | ● | ● | ● | ● |
| `tab.select` | ● | ● | ● | ● | ◐ C2 | – | – |

### 3-5. 런타임 조건

| # | 조건 | 거짓일 때의 이유 · 해소 방법 |
|---|---|---|
| C1 | 그 세션이 **끝났다** (`review`·`lost`·실행 완료) | 「실행 중인 세션이 열려 있습니다」 → `run.stop` |
| C2 | 브라우저 세션이 **살아 있다** (`paused`, `review`·`lost` 아님) | 「브라우저가 닫혔습니다」 → `run.all` 또는 `browser.openAt` |
| C3 | 살아 있고 **실패한 Step 이 있다** | 「건너뛸 실패가 없습니다」 · 해소 방법 없음 |
| C4 | 사람이 조작하는 동안 속도 설정이 적용되는가 | **이행 순서 3에서 현재 동작과 대조해 확정한다** (UC-401) |
| C5 | 이 테스트를 **막고 있는 세션이 있다** | 「실행 중인 세션이 없습니다」 · 해소 방법 없음 |
| C6 | 지금 **기록 중이다** | 「기록 중이 아닙니다」 → `step.recordStart` |
| C7 | 정의가 **편집 가능하다** (`editable`, 잠긴 항목 아님) | 006 FR-206 의 문구 → `session.open` |
| C8 | Step 이 **1개 이상이다** | 「Step 이 없으면 저장할 수 없습니다」 (006 FR-197) |
| C9 | 저장할 **변경이 1건 이상이다** | 「바꾼 것이 없습니다」 · 해소 방법 없음 |
| C10 | 외부 변경 **충돌이 감지됐다** | 「충돌이 없습니다」 · 해소 방법 없음 |
| C11 | AI 가 **막혀 선택지를 제시했다** (`ai_blocked`) | 「고를 선택지가 없습니다」 · 해소 방법 없음 |
| C12 | `testId` 가 있고 그 실행이 **끝났다** | 「실행이 끝나면 볼 수 있습니다」 · 해소 방법 없음 |
| C13 | 그 테스트에 **결과가 있다** | 「아직 실행한 적이 없습니다」 → `run.all` |

### 3-6. 전 국면 덮어쓰기

표와 조건보다 **먼저** 적용된다. 하나라도 걸리면 그 조작은 ○ 다.

| # | 덮어쓰기 | 대상 조작 | 이유 문구 |
|---|---|---|---|
| O1 | 실행 요청이 **진행 중**이다 (`pendingRun !== null`) | `run.all` `run.from` `browser.openAt` | 「실행을 준비하는 중…」 (005 FR-127·FR-129) |
| O2 | 명령이 **진행 중**이다 (`busy`) | 세션 명령 전부 | 「요청을 보내는 중…」 |
| O3 | 세션이 **유실**됐다 (`lost`) | 브라우저를 요구하는 조작 전부 | 「브라우저 세션이 유실됐습니다」 → `run.all` |
| O4 | Step 이 **0개**다 | `save` `run.all` `run.from` `step.*` | 「Step 이 없습니다」 |

**O1 이 표에 없고 덮어쓰기인 이유**: 국면과 무관한 사정이다. 국면마다 표에 적으면 한 국면이
빠지고, 빠진 국면에서 연타하면 브라우저 창이 둘 뜬다 — 005 U-06 이 그 형태였다(실측 5회
클릭에 201 이 2건).

---

## 4. 판정 규칙

### 4-1. 「비활성」의 의무 (FR-234)

○ 인 조작은 다음 셋을 **모두** 갖는다.

1. **같은 자리에 그린다.** 감추지 않는다 — 감추면 사용자는 자기가 잘못 들어온 줄 안다.
2. **이유를 붙인다.** 왜 지금 안 되는지.
3. **해소 방법을 붙인다** — 있을 때만. 해소 방법은 **이 화면에 실제로 있는 조작**을
   가리켜야 한다.

3번이 006 E-03 의 수정이다. "실행을 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로
가는 버튼을 주지 않은 것이 그 결함이었다. `Remedy.action` 이 `ActionId` 타입인 이유가
이것이다 — 자유 문장이면 같은 결함이 다시 들어온다.

### 4-2. 「해당 없음」을 쓸 수 있는 경우 (닫힌 목록)

– 는 아래 셋 중 하나에 해당할 때만 쓴다. 그 외에는 ○ 다.

| 근거 | 뜻 | 예 |
|---|---|---|
| N1 이미 충족됨 | 그 조작의 목적이 이 국면에서 이미 이루어져 있다 | 세션 국면의 `browser.openAt` — 브라우저가 이미 열려 있다 |
| N2 대상이 없음 | 그 조작이 다룰 대상이 이 국면에 존재하지 않는다 | 작성 국면의 `run.all` — 저장된 테스트가 아직 없다 |
| N3 세션이 없음 | 세션 명령인데 이 국면에는 세션이 없다 | `RES`·`EDT` 의 `run.stop`·`run.pause` |

**§3 의 모든 – 은 위 셋 중 하나로 설명될 수 있어야 한다.** 설명되지 않는 – 은 감춘 조작이며
FR-234 위반이다.

### 4-3. 표와 코드가 어긋날 때 (UC-401)

- 표가 ● · ○ 인데 코드에 조작이 없다 → **코드를 고친다**
- 표가 – 인데 **현재 그 국면에서 쓸 수 있는 조작이다** → **표가 틀렸다.** 표를 고친다
  (FR-247 — 통합으로 사라지는 조작이 있어서는 안 된다)
- 이행 순서에서 한 국면을 옮길 때 **그 국면 열 전체를 현재 동작과 대조한다.** 대조 결과를
  커밋 메시지에 남긴다

---

## 5. 문구 규칙

- **모든 라벨·이유·해소 방법 문구는 `frontend/src/lib/wording.ts` 에 둔다.** 컴포넌트에
  문자열 리터럴을 쓰지 않는다. 이미 그 파일이 문구 단일 출처이며 007 은 그 범위를 넓힌다.
- **시작 지점이 라벨에 드러난다** (005 FR-149) — `run.from` 은 「Step 06 부터 실행」이다.
  「실패한 Step 부터 실행」은 어디서 시작하는지 말하지 않아 사용자가 예측할 수 없었다 (U-02).
- **같은 자리의 같은 라벨이 다른 동작을 하지 않는다** (FR-235 · 005 FR-147) —
  `run.stop` 의 라벨은 상황에 따라 「중지」/「중지 중…」/「닫기」/「나가기」로 **바뀐다.**
  라벨이 바뀌는 것이 규칙을 지키는 방법이다.
- **색만으로 구분하지 않는다.** 결말 칩·Step 표식에는 항상 텍스트 라벨이 함께 있다
  (005 FR-141·FR-151).

---

## 6. 회귀 방지 장치

사용자가 명시적으로 요구한 넷. 각각을 막는 **구조**를 적는다 — 주의가 아니라 구조여야 한다.

| 회귀 | 무엇이었나 | 007 이 두는 장치 |
|---|---|---|
| 005 U-01 | 종료된 세션 때문에 결과 화면의 재실행이 **항상 409** | 실행 진입은 `App` 의 `startRun` 한 곳뿐이다. 국면 어댑터는 그것을 호출만 하며 세션을 스스로 만들지 않는다 (FR-248) |
| 005 U-06 | 연타로 브라우저 창이 둘 | `pendingRun` 을 §3-6 O1 **덮어쓰기**로 둔다. 국면별 표에 적지 않으므로 한 국면이 빠질 수 없다 (FR-249) |
| 005 U-21 | 건너뜀과 미실행이 같은 표식 | `StepOutcome` 이 두 값을 따로 갖고, 텍스트 라벨을 병기한다. 단일 Step 행 구현이므로 한 국면만 뭉갤 수 없다 (FR-226) |
| 001 R2 | AI 실패가 조건 뒤에 숨어 화면에 도달 못함 | `PhaseAside.error`·`blocked` 는 **국면 판정과 무관하게** 값이 있으면 그린다. AI 세션 판정은 `authoring_mode` 로 한다 — `state` 가 아니다 (FR-218f·FR-253) |

추가로 007 자신이 만들 수 있는 회귀 하나:

| 회귀 위험 | 장치 |
|---|---|
| 통합 화면이 **또 하나의 구현**이 되어 4벌이 5벌이 된다 | 국면 이행 커밋에 옛 구현 **삭제**를 포함한다. 구현 개수를 세는 테스트를 둔다 (SC-001) |

---

## 7. 접근성

기존 규칙을 유지하고 국면 표시에 확장한다.

- 국면 표시는 텍스트다. 색·아이콘만으로 국면을 알리지 않는다.
- ○ 조작은 `disabled` 이면서 이유가 **접근 가능한 이름 또는 설명**으로 연결된다.
  이유를 시각적으로만 두면 비활성 이유가 도구에 전달되지 않는다.
- 알림의 `role` 은 `Notice.role` 이 정한다 — 오류는 `alert`, 상태는 `status`, 보조 설명은
  `note`. 지금 각 화면이 개별로 정하고 있어 같은 성격의 배너가 다른 role 을 갖는다.
- Step 행은 누를 수 있는 요소가 `button` 역할을 갖는다 (기존 테스트가 `getByRole` 에
  의존한다).
