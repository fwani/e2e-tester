# Data Model: 022 — 예산 소진을 막힘과 갈라 말한다

**Created**: 2026-09-28

이 기능은 **저장되는 데이터를 만들지 않는다.** Step DSL, 테스트 파일, 프로젝트 구조를
건드리지 않으므로 마이그레이션이 없고 기존 자산과의 호환 문제가 없다.

다루는 것은 세션이 살아 있는 동안의 메모리 상태뿐이다.

---

## 1. 막힘의 종류 — `BlockedKind`

`backend/src/itb/authoring/tools.py`

| 값 | 뜻 | 사람이 알려 줄 것 | 이어가면 |
|---|---|---|---|
| `needs_input` | 사람이 알려 주면 풀린다 (기본값) | **있다** | 알려 준 것을 반영해 진행 |
| `product_mismatch` | 제품이 지시문과 다르게 동작한다 (020) | 없다 | **같은 결과** — 제품이 여전히 그렇다 |
| `budget_exhausted` | **예산이 떨어졌다** ← 더함 | 없다 | **진행된다** — 예산이 새로 생겼다 |

**축은 「왜 막혔는가」다.** `AiChoice`(사람이 무엇을 할 수 있는가)와 다른 축이며,
020 이 정한 이 축을 그대로 쓴다.

### 판정 규칙

`budget_exhausted` 는 **제품이 센 값**으로만 판정한다.

| 사건 | 판정 |
|---|---|
| 도구 호출 총 상한 도달 (`MAX_TOOL_CALLS`) | `budget_exhausted` |
| 드라이버 turn 상한 도달 (`DriverTurnLimitError`) | `budget_exhausted` |
| 같은 요소 연속 실패 상한 도달 | **아니다** — 그 경로가 막힌 것 (FR-002) |
| 모델이 `report_blocked` 로 신고 | **아니다** — 어떤 문구로 신고하든 (FR-003) |

마지막 줄이 중요하다. 모델의 말이 판정에 끼어들면, 모델이 「예산이 없다」고 말하는 것만
으로 사용자가 다른 화면을 보게 된다.

### 기본값

`DEFAULT_BLOCKED_KIND = needs_input` — 그대로 둔다. 인식하지 못한 값이 답변 칸을 **여는**
쪽으로 떨어지는 것이 반대 방향보다 덜 해롭다는 기존 판단을 유지한다.

---

## 2. 시도 추적 — `AttemptLimits`

`backend/src/itb/authoring/tools.py`

| 필드 | 뜻 | 예산을 새로 줄 때 |
|---|---|---|
| `max_calls` | 한 시도의 호출 상한 (40) | 그대로 |
| `calls` | **이번 시도**의 호출 수 | **0 으로** |
| `total_calls` ← 더함 | **이 지시에 쓴 누적** 호출 수 | **남는다** |
| `steps_at_attempt_start` ← 더함 | 이번 시도 시작 시점의 Step 수 | **현재 Step 수로 갱신** |
| `max_element_failures` | 같은 요소 연속 실패 상한 (3) | 그대로 |
| `failures_by_element` · `last_failed_element` | 연속 실패 추적 | 비운다 |
| `exceeded_reason` | 상한 도달 사유. `None` 이 아니면 루프를 끊는다 | 비운다 |

### 왜 누적을 여기 두는가

`record_call()` 이 도구 호출의 **유일한 통과 지점**이다. 두 계수를 같은 자리에 두면
어긋날 수 없다. 세는 주체가 둘이면 어긋난다는 판단은 이 저장소에 이미 두 번 적혀 있다
(`AuthoringAgent._count`, `MAX_INSTRUCTION_CHARS`).

### `reset()` → `reset_attempt()`

하는 일이 「전부 되돌린다」에서 **「이번 시도의 예산만 되돌린다」**로 좁아졌다. 누적은
되돌리지 않으므로 이름이 그 사실을 말해야 한다.

호출부 네 곳이 모두 같은 뜻으로 부르고 있어 기계적 치환이다.

| 호출부 | 왜 부르나 |
|---|---|
| `AuthoringAgent.chat` | 대화 한 차례마다 새 예산 |
| `AuthoringAgent.resume_with_answer` | 답을 받아 이어갈 때 |
| `AuthoringAgent.resume_after_takeover` | 사람이 이어받은 뒤 재개할 때 |
| `sessions._start_agent_note` | `retry`·`skip` 으로 이어갈 때 |

### 진전 판정

```
진전 있음 = (현재 Step 수 > steps_at_attempt_start)
```

`steps_at_attempt_start` 가 **없으면**(첫 시도) 진전 없음을 판정하지 않는다 — 비교할
직전 값이 없다. 「진전이 없다」와 「아직 비교할 것이 없다」는 다른 사실이다.

---

## 3. 루프 결말 — `AgentOutcome`

`backend/src/itb/authoring/agent.py`

| 필드 | 지금 | 이 기능에서 |
|---|---|---|
| `status` | 결말 종류 | 그대로 |
| `reason` · `attempted` · `question` | 왜·무엇을 하다·무엇을 묻는가 | 그대로 |
| `blocked_kind` | 왜 막혔는가 | **`budget_exhausted` 가 실릴 수 있다** |
| `step_count` | 확정된 Step 수 | 그대로 |
| `tool_calls` | 이번 시도의 호출 수 | **소비자가 생긴다** (지금은 아무도 읽지 않는다) |
| `total_tool_calls` ← 더함 | 누적 호출 수 | 화면 표시용 |
| `made_progress` ← 더함 | 직전 시도 이후 Step 이 늘었는가 (`None` = 판정 불가) | 화면 표시용 |

**`AgentOutcome` 은 상태를 소유하지 않는다.** 판정 시점의 값을 실을 뿐이며, 이는
`step_count`·`tool_calls` 가 이미 하는 일과 같다. 상태의 소유자는 `AttemptLimits` 다.

`made_progress` 가 3값(`True`/`False`/`None`)인 이유는 「진전 없음」과 「판정할 수 없음」이
다른 사실이기 때문이다. 화면은 `False` 일 때만 안내를 그린다.

---

## 4. 막힘 정보의 외부 모양 — `BlockedView` · `ai_blocked`

계약은 [contracts/blocked-view.md](./contracts/blocked-view.md) 에 있다. 여기서는 데이터
관점만 적는다.

**같은 값이 두 통로로 나간다.**

| 통로 | 언제 | 왜 둘 다 필요한가 |
|---|---|---|
| `ai_blocked` 이벤트 | 막히는 순간 | 붙어 있는 화면에 즉시 |
| `BlockedView` (세션 조회) | 화면이 물을 때마다 | **새로 고쳐 돌아온 화면**을 복원 (FR-022) |

두 통로가 **같은 자리에서 읽는다** — `w.last_blocked`(`AgentOutcome`). 그래서 갈릴 수
없다. 이 구조는 이미 존재하며 이 기능은 필드만 더한다.

---

## 5. 생명주기

```
지시문 하나
 ├─ 시도 1        calls 0→40, total_calls 0→40, steps_at_attempt_start=0
 │   └─ 상한 도달 → blocked_kind=budget_exhausted, made_progress=None (첫 시도)
 ├─ 이어가기      reset_attempt(): calls→0, total_calls 유지(40), steps_at_attempt_start=현재
 ├─ 시도 2        calls 0→40, total_calls 40→80
 │   └─ 상한 도달 → made_progress = (지금 Step 수 > 시도 2 시작 시 Step 수)
 └─ 새 지시문     total_calls 0 으로 — 이어가기는 같은 지시의 연장, 새 지시는 다른 일
```

**새 지시에서 누적이 0 으로 돌아가는 자리**가 어디인지가 구현의 관건이다. `chat` 과
`run` 이 갈라져 있으므로(전자는 대화, 후자는 지시) 그 구분을 쓸 수 있는지 tasks 에서
확인한다.

---

## 6. 저장·실행·내보내기에 대한 영향

| 대상 | 영향 |
|---|---|
| Step DSL | **없음** — 이 기능은 Step 을 만들지도 바꾸지도 않는다 |
| 저장된 테스트 파일 | **없음** — 마이그레이션 없음 |
| 실행 경로 | **없음** — 작성 경로 전용 (헌법 원칙 II) |
| Playwright 내보내기 | **없음** — 원칙 V 의 설계 의무에 닿지 않는다 |
| 공유 묶음 | **없음** |
