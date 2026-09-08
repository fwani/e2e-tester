# Phase 1 — 데이터 모델: Step 조작 흐름

**기능**: `009-step-editing-flow` | **작성**: 2026-09-08

**새 Step 종류를 만들지 않는다.** 이 기능이 더하는 것은 「사람이 손으로 만들 수 있는
Step 을 서술하는 방법」과 「그것을 목록에 넣는 편집 연산」이다. 만들어지는 것은 기존
`NavigateStep`·`CloseTabStep`·`AssertionStep` 이며, 실행·생성기·내보내기는 이미 그 셋을
다룬다 (헌법 원칙 I·V).

---

## 1. `InsertableKind` — 손으로 만들 수 있는 종류 (FR-286)

**위치**: `backend/src/itb/domain/manual_step.py` (신규) — **유일한 정본**

| 값 | 만드는 Step | 요소 지목 | 근거 |
|---|---|---|---|
| `navigate` | `NavigateStep(url=…)` | 없음 | 주소만 있으면 성립한다 |
| `close_tab` | `CloseTabStep(tab=…)` | 없음 | 대상은 공통 `tab` 필드가 가리킨다 |
| `assert_url` | `AssertionStep(assertion.kind=url)` | **금지** | `Assertion` 검증기가 `url` 에 `target` 을 두는 것을 이미 거절한다 |
| `assert_text` | `AssertionStep(assertion.kind=text, target=None)` | 없음 | `target` 이 없으면 화면 전체 텍스트를 본다 |

**이 목록에 없는 종류는 이 경로로 만들 수 없다** (FR-287) — `click`·`fill`·`select`·
`hover`·`drag`, 그리고 `assertion` 의 `visible`·`hidden`(대상 필수)과 대상이 있는 `text`.
막는 방식은 런타임 검사가 아니라 **판별 유니온**이다: 요청 모델에 그 종류가 없다.

**Step 종류가 늘 때**: 이 열거형과 아래 `ManualStepSpec` 만 고친다. 프론트엔드는 생성된
타입으로 받으므로 자동으로 따라온다 — 손으로 고치는 목록이 두 벌이 되지 않는다.

---

## 2. `ManualStepSpec` — 손으로 넣을 Step 의 서술 (신규)

**위치**: `backend/src/itb/domain/manual_step.py` · 판별 유니온, 판별자는 `kind`

| 필드 | 종류 | 검증 |
|---|---|---|
| `kind` | 넷 중 하나 | 판별자 |
| `label` | `str \| None` | 1~200자. 생략하면 서버가 만든다 (R6) |
| `tab` | `int` | `>= 0`, 기본 0 |
| `timeout_ms` | `int \| None` | 1~60000. 생략하면 Step 기본값 |
| `url` | `str` | `navigate`·`assert_url` 에만 있고 **필수**. 1~2000자 |
| `value` | `str` | `assert_text` 에만 있고 **필수**. 0~4000자 |
| `match` | `equals \| contains` | `assert_url`·`assert_text`. 기본 `equals` |

**규칙**

1. **`model_config = ConfigDict(extra="forbid")`** — 다른 계약 모델과 같다. `target` 을
   실어 보내는 경로를 만들지 않는다.
2. **평문 민감 값을 받는 필드가 없다.** `value` 는 기대 텍스트이며 `{{NAME}}` 참조를 쓸 수
   있다. 실제 비밀 값은 비밀 값 엔드포인트만 다룬다 (원칙: 조직 보안 요구 · FR-212).
3. **id 를 받지 않는다.** 서버가 `allocate_step_id` 로 만든다 (R6).
4. **`author` 를 받지 않는다.** 손으로 넣은 것은 `human` 이며 서버가 정한다. `author` 는
   실행 방식을 바꾸지 않는다 (원칙 I).

**파생 함수** — `build_step(spec: ManualStepSpec, step_id: str) -> Step`. 순수 함수이며
domain 안에 있다. 라벨 파생 규칙:

| 종류 | 기본 라벨 |
|---|---|
| `navigate` | `주소로 이동 — {url}` |
| `close_tab` | `탭 {tab} 닫기` |
| `assert_url` | `주소 검증 — {url}` |
| `assert_text` | `화면 텍스트 검증 — {value}` |

라벨은 200자로 자른다. 값이 길면 뒤를 생략하고 생략했음을 표시한다.

---

## 3. `InsertStepOp` — 세션 없는 편집 연산 (FR-285·FR-288)

**위치**: `backend/src/itb/api/routes/tests.py` 의 `EditOp` 유니온에 추가

```
op: "insert"
at: int          # 0 ≤ at ≤ len(steps). 그 위치 앞에 들어간다
spec: ManualStepSpec
```

**적용**: `_apply_edits` 가 `build_step(spec, allocate_step_id(steps))` 로 Step 을 만들고
`itb.execution.step_edits.insert_step(steps, 0, step, at)` 를 부른다 — 다른 연산과 같은
방식이며 **전부 또는 전무**다.

**경고** (막지 않는다 · FR-312): 삽입이 선행 상태를 깰 수 있는 경우를 경고로 남긴다.
지금 `_reorder_warning` 이 「주소 이동 Step 이 뒤로 밀렸다」를 보는 것과 같은 얕은 규칙에서
시작한다.

| 상황 | 경고 |
|---|---|
| `close_tab` 의 `tab` 이 현재 정의에서 열리지 않는 번호 | 「그 탭이 열리지 않을 수 있습니다 — 저장 후 실행으로 확인하세요」 |
| `navigate` 를 목록 중간에 넣었다 | `_reorder_warning` 과 같은 문장을 재사용한다 |

`EditOp` 유니온이 커지므로 `_apply_edits` 의 분기는 `isinstance` 사슬을 유지한다 — 그
함수의 규칙(연산은 `step_edits` 가 한다)은 바뀌지 않는다.

---

## 4. 세션 삽입 요청 (FR-290)

**위치**: `backend/src/itb/api/routes/steps.py`

```
POST /api/sessions/{session_id}/steps:manual
body: { at: int | null, spec: ManualStepSpec }
```

`at` 을 생략하면 **일시정지 위치**다 — 기존 `InsertStepRequest` 와 같은 규칙
(`step_edits._clamp`). `require_paused` 를 지나고, 응답은 기존 `StepsResponse` 다.

**브라우저에 아무 명령도 보내지 않는다** — `_apply_edit` 의 규칙이 그대로 적용된다.
손으로 넣은 Step 은 아직 수행되지 않은 정의이므로 실행 위치를 밀지 않는다.

---

## 5. `SessionView.pause_before_index` (FR-293·FR-294)

**위치**: `backend/src/itb/api/routes/sessions.py` 의 `SessionView`

```
pause_before_index: int | None = None
```

**뜻**: **아직 도달하지 않은** 목표 지점. 도달하면 `None` 이 된다 (러너가 지운다).

| 도출 | 화면이 말하는 것 |
|---|---|
| 값이 있고 상태가 실행 중 | 「Step nn 앞에서 멈춥니다」 + 현재 위치 |
| 값이 없고 상태가 일시정지 | 도착했다. 지금 문구 그대로 |
| 값이 있고 실패한 Step 이 있다 | 「Step nn 에 도달하기 전에 실패했습니다」 |

`RunnerTask` 에 읽기 전용 접근자를 더해 `view_of(work)` 가 읽는다. 러너가 없으면 `None`
이다. 재연결 시 이 값이 실려 오므로 화면을 다시 그려도 목표가 사라지지 않는다 (005 U-18 의
교훈 · R5).

---

## 6. 국면 × 조작 표 (FR-305)

**위치**: `frontend/src/lib/actions.ts` · `frontend/src/lib/capabilities.ts` ·
`frontend/src/lib/wording.ts`

조작 34개 → **36개**. 표의 칸은 8 × 36 = **288**.

| 변화 | id | 라벨 |
|---|---|---|
| 추가 | `step.insertManual` | 직접 입력으로 Step 추가 |
| 추가 | `step.moveDown` | 아래로 옮기기 |
| 개칭 | `step.reorder` → `step.moveUp` | 위로 옮기기 |
| 뜻 확장 | `browser.openAt` | 브라우저 열어 이 Step 앞에서 멈추기 |

국면별 셀은 [contracts/step-editing.md](./contracts/step-editing.md) §2 가 정본이다.

**런타임 덮어쓰기**: `step.insertManual` 과 `step.moveDown` 은 기존 `step.reorder` 가
들어 있던 덮어쓰기 목록을 그대로 따른다 — `O2`(busy) · `O3`(sessionLost, 세션 경로만) ·
`O4`(hasSteps 거짓) · `O6`(pausing). 새 덮어쓰기 키를 만들지 않는다.

- `O4` 는 「Step 이 없다」일 때 걸리는 부정 조건이다. `step.insertManual` 은 **여기에 넣지
  않는다** — Step 이 0개일 때야말로 넣을 수 있어야 한다 (008 FR-260 과 같은 판단).
- `step.moveUp`·`step.moveDown` 은 `O4` 에 들어간다. 옮길 것이 없으면 뜻이 없다.

**행 단위 좁히기**: 첫 행의 위로 · 마지막 행의 아래로는 표가 아니라 **화면이 아는 사실**로
비활성이 된다 (FR-300). `EditView` 의 `narrowByPick` 과 같은 형태이며, 화면이 국면을
판정하는 것이 아니라 표의 결과를 좁히는 것이다.

---

## 7. 정본 시각 언어 (FR-304·FR-313)

**위치**: `frontend/src/theme/tokens.css` · `docs/design/008-visual-language/`

| 항목 | 지금 | 바뀜 |
|---|---|---|
| `.srow` 격자 | `26px 1fr 58px 20px` | `26px 1fr 58px 20px auto` |
| `.srow` 높이 | 52px | **바뀌지 않는다** |
| 신규 클래스 | — | `.srow-ops` (행 조작 묶음) · `.btn.icon` 계열 재사용 |

행 조작 아이콘은 20px 이며 조작 높이 26px(작은 자리)의 정본 값을 따른다. 새 색·새 치수를
만들지 않는다 — 008 이 정한 토큰만 쓴다.

**흐름의 방향이 정해져 있다.** `dc.html 의 <style>`(18장 동일) → `extract_canon.py` →
`tokens.css`. `tokens.css` 를 먼저 고치면 다음 추출에서 되돌아간다. 절차는
[contracts/step-editing.md](./contracts/step-editing.md) §6 이 정본이다.

---

## 8. 불변식

1. **삽입은 `insert_step` 한 곳을 지난다.** 세 입구(정의 편집 · 세션 직접 입력 · 기존
   완성 Step 삽입)가 같은 규칙을 쓴다.
2. **요소 지목을 요구하는 Step 은 손으로 만들어지지 않는다.** 요청 모델에 그 종류가 없다.
3. **손으로 넣은 Step 의 `author` 는 `human` 이고 실행 방식을 바꾸지 않는다** (원칙 I).
4. **저장 전 삽입은 파일을 건드리지 않는다.** 저장은 `revision` 확인을 지난다 (006).
5. **실행 중에는 어떤 입구로도 삽입·순서 변경·삭제가 되지 않는다** (`require_paused`).
6. **새 Step 종류가 생기지 않으므로 내보내기 가능성이 유지된다** (원칙 V).
