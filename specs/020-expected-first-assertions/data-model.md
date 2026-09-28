# Phase 1 데이터 모델 — 020 기대 동작 기준 검증

**대상 명세**: [spec.md](./spec.md) · **근거**: [research.md](./research.md)

이 기능은 **새 엔티티를 거의 만들지 않는다.** 기존 세 모델에 필드를 더하고, 판정을 순수
함수로 추가한다.

---

## 1. `AuthoringMismatch` — 작성 시점 어긋남 (신규)

**위치**: `backend/src/itb/domain/assertion.py`

**뜻**: 「이 검증은 만들어질 때 통과하지 않았다」와 **그때 화면이 어땠는지**.

| 필드 | 형 | 제약 | 뜻 |
|---|---|---|---|
| `observed` | `str` | 1~4000자 | 작성 시점 실패 설명. 실행기가 만든 문장을 스크러빙한 것 (R2) |
| `truncated` | `bool` | 기본 `false` | `observed` 가 상한에서 잘렸는가 (FR-008) |
| `recorded_at` | `datetime` | — | 언제 기록됐는가. 「얼마나 오래된 결함 후보인가」를 사람이 판단할 근거 |

**기대값은 여기에 없다.** `AssertionStep.assertion.value` 가 유일한 출처다 (R1).

**검증 규칙**:
- `observed` 는 비어 있을 수 없다. 빈 문자열이면 「화면이 비어 있었다」로 오독된다 — 적을
  것이 없는 상황은 어긋남이 아니라 **대상 없음**이며 Step 자체가 만들어지지 않는다 (R4).
- `model_config`: `extra="forbid"`, `json_schema_serialization_defaults_required=True` —
  도메인의 다른 모델과 같다.

---

## 2. `AssertionStep.mismatch` — 필드 추가

**위치**: `backend/src/itb/domain/step.py`

```
class AssertionStep(_StepBase):
    type: Literal[StepType.ASSERTION] = StepType.ASSERTION
    assertion: Assertion
    mismatch: AuthoringMismatch | None = None      # ← 추가
```

| 값 | 뜻 |
|---|---|
| `None` | 작성 시점에 통과했다. **020 이전에 저장된 모든 정의가 여기 해당한다** — 그 정의들은 통과할 때만 기록됐기 때문이다 |
| 있음 | 결함 후보 |

**불변식**:

- **I-1**: 실행기(`StepExecutor`)는 이 필드를 읽지 않는다. 검증 판정은 `assertion` 만으로
  결정된다 (FR-012 · 헌법 원칙 I).
- **I-2**: 생성기(`playwright_gen`)는 이 필드를 읽지 않는다 (FR-016 · 헌법 원칙 V).
- **I-3**: 작성 주체와 무관하다. 사람이 만든 검증도 이 필드를 가질 수 있다 (FR-011).
- **I-4**: 다른 Step 종류에는 없다. 「어긋난 클릭 Step」은 존재할 수 없다 (R1).

I-1·I-2 는 **검사로 고정한다** — 소스에서 `mismatch` 참조를 전수 확인하는 방식으로,
`summary.py` 의 `ALLOWED_VALUE_READS` 와 같은 선례를 따른다.

---

## 3. `AssertionClass` · `StepResult.assertion_class` — 실행 결과 분류 (신규)

**위치**: `backend/src/itb/domain/run_result.py`

```
class AssertionClass(StrEnum):
    KNOWN_DEFECT = "known_defect"   # 작성 시점에도 실패했다
    REGRESSION   = "regression"     # 작성 시점에는 통과했다
    RESOLVED     = "resolved"       # 작성 시점에 어긋났는데 이번엔 통과했다
```

```
class StepResult(BaseModel):
    ...
    assertion_class: AssertionClass | None = None      # ← 추가
```

**판정표** (순수 함수 `classify_assertion(step, result)`):

| Step 종류 | `step.mismatch` | `result.outcome` | 분류 |
|---|---|---|---|
| assertion | 있음 | `FAIL` | `KNOWN_DEFECT` |
| assertion | 없음 | `FAIL` | `REGRESSION` |
| assertion | 있음 | `PASS` | `RESOLVED` |
| assertion | 없음 | `PASS` | `None` — 말할 것이 없다 |
| assertion | — | `SKIPPED`·`NOT_RUN` | `None` — 실행되지 않았다 |
| 그 외 | — | — | `None` |

**집계** (순수 함수 `counts_by_class(steps)`): 분류별 건수를 돌려준다. **저장하지 않는다** —
파생값을 저장하면 원본과 어긋날 자리가 생긴다 (R7, `attempted_of` 와 같은 판단).

**`Outcome` 은 값을 늘리지 않는다** (FR-021).

> **2026-09-28 구현 중 정정.** 「`decide_outcome` 은 변경되지 않는다」는 틀렸다 —
> 정합성 점검 F1 이 3번 규칙의 조건을 좁히게 했다 (FR-039). **우선순위의 순서는
> 그대로**이고 값도 늘지 않는다. 자세한 것은 §8.

---

## 4. `BlockedKind` — 막힘 사유 종류 (신규)

**위치**: `backend/src/itb/authoring/tools.py`

> **2026-09-28 구현 중 정정.** 계획은 `blocked.py` 였다(`AiChoice` 옆이 자연스럽다).
> **임포트 방향이 그것을 막는다** — `blocked` → `agent` → `tools` 이므로 `tools` 가
> `blocked` 를 가져오면 순환이 된다. 값이 **만들어지는 곳**이 `report_blocked` 라는
> 점에서 `tools.py` 도 맞는 자리다. `blocked.py` 는 그것을 화면으로 나르기만 한다.

```
class BlockedKind(StrEnum):
    NEEDS_INPUT      = "needs_input"       # 기본 — 현행 전부
    PRODUCT_MISMATCH = "product_mismatch"  # 제품이 지시문과 다르게 동작한다
```

**전파 경로**:

```
report_blocked(reason, question, kind)
  → BrowserToolbox.blocked_kind
  → AgentOutcome.blocked_kind
  → ai_blocked 이벤트의 kind 필드
  → BlockedView.kind (세션 뷰)          ← 구현 중 추가
  → 화면: PRODUCT_MISMATCH 이면 답변 칸을 열지 않는다
```

> **2026-09-28 구현 중 추가 — 세션 뷰에도 실어야 한다.** 이벤트에만 두면 새로고침
> 뒤에 사라지고, 그러면 답할 수 없는 질문에 대해 답변 칸이 **다시 열린다.**
> `BlockedView` 가 존재하는 이유(이벤트는 그 순간 붙어 있던 화면에게만 간다)가
> 여기에도 그대로 걸린다.

**불변식**:

- **I-5**: `kind == PRODUCT_MISMATCH` 이면 `question` 은 버려진다 (FR-024). 도구 쪽에서
  버린다 — 모델이 규칙을 어겨도 화면에 답변 칸이 열리지 않아야 한다.
- **I-6**: 기본값이 `NEEDS_INPUT` 이므로 기존 막힘 보고의 동작이 변하지 않는다 (FR-025).
- **I-7**: 인식하지 못한 값은 `NEEDS_INPUT` 으로 떨어진다. 오타가 조용히 답변 칸을
  막으면 사용자는 이유를 모른 채 이어갈 방법을 잃는다 — 반대 방향의 오작동(질문이
  필요 없는데 칸이 열림)이 덜 해롭다.

---

## 5. 상태 전이 — 하나의 검증이 겪는 일생

```
        작성
          │
    ┌─────┴─────┐
  통과        어긋남
    │           │
mismatch=None  mismatch 기록
    │           │
    └─────┬─────┘
          │  저장 · 공유 · 내보내기 (값 보존)
          │
        재실행
          │
    ┌─────┼─────────┬──────────┐
  PASS   FAIL      PASS       FAIL
 (없음)  (없음)    (있음)     (있음)
    │      │         │          │
  None  REGRESSION RESOLVED  KNOWN_DEFECT
                     │
              사람이 표시를 걷어냄 (FR-027)
                     │
              mismatch=None — 이후 실패는 REGRESSION
```

**걷어내기는 일반 Step 편집이다** (FR-029, 2026-09-28 사용자 결정). `mismatch` 를 `None`
으로 만드는 것이며, `AuthoringMismatch` 기록도 함께 사라진다. 별도 되돌리기를 두지 않는다.

**제품이 자동으로 걷어내지 않는다** (FR-028). `RESOLVED` 분류는 **알림**이지 동작이 아니다.

---

## 6. 저장 형식에 미치는 영향

| 파일 | 변화 | 호환 |
|---|---|---|
| 테스트 정의 (`Test`) | 검증 Step 에 `mismatch` 가 붙을 수 있다 | 옛 파일은 `None` 으로 읽힌다 (필드 기본값) |
| 실행 결과 (`.runs/<id>/result.json`) | `StepResult.assertion_class` 가 붙는다 | 옛 결과 파일은 `None` 으로 읽힌다 |
| 공유 번들 | 모델 왕복이므로 자동 보존 (R9) | 020 이전 번들은 필드 없음 → `None` |
| 엑셀 | 영향 없음 — Step DSL 왕복이 아니다 (R9) | — |
| Playwright 내보내기 | 변화 없음 — 생성기가 읽지 않는다 (I-2) | — |

**생성 스키마** (R10): `backend/schema/step.schema.json`, `backend/schema/run-result.schema.json`
재생성 → `frontend/src/types/generated/{step,run-result}.d.ts`.


---

## 7. 구현 중 드러난 것 — `null` 과 `undefined` (2026-09-28)

**화면 쪽에서 둘을 같게 다뤄야 한다.**

생성된 TypeScript 는 새 필드를 **필수**로 표기한다 (`json_schema_serialization_defaults_required=True`
의 결과). 그런데 020 이전 서버가 보낸 Step 과 옛 결과 파일에는 칸 자체가 없고, 그때
값은 `null` 이 아니라 `undefined` 다. `!== null` 만 보는 코드는 **없는 기록을 그리려다
터진다.**

실제로 `InsertViaBrowser` 검증 2건이 그렇게 깨져서 잡혔다 — 타입이 필수라고 말하는데
런타임 값은 없는, 타입 검사가 잡지 못하는 종류의 어긋남이다.

| 자리 | 규칙 |
|---|---|
| `StepDetail` · `StepList` | `step.mismatch ?? null` 로 좁힌다 |
| `countAssertionClasses` | `!= null` (느슨한 비교)로 둘 다 거른다 |
| `ClassifiedStepResult` | 칸을 **선택**으로 선언한다 — 옛 데이터의 모양이 그렇다 |

옛 모양을 재현하는 회귀 검증이 백엔드(`test_share_preserves_mismatch.py` 의 파일에서
칸 지우기)와 프론트엔드(`MismatchDisplay.test.tsx` · `AssertionMismatch.test.tsx`)
양쪽에 있다.

## 8. 구현 중 넓어진 것 — 건너뛰기와 재개 가드 (2026-09-28)

`decide_outcome` 한 곳을 고치면 될 줄 알았던 FR-039 가 **셋**이 됐다. 근거는
[baseline.md](./baseline.md) 에 있다 — `clear_failed_steps` 가 결과의 **모든** `FAIL` 을
`SKIPPED` 로 바꾸므로, 결말 판정에 닿기도 전에 회귀의 증거가 지워진다.

| 고친 것 | 020 이전 | 020 이후 |
|---|---|---|
| `clear_failed_steps` → `skip_blocking_failure` | 모든 `FAIL` 을 건너뜀으로 | **멈춘 자리 하나만** |
| 재개 가드 (`has_failed_step`) → `blocking_failure_index` | 「실패가 있는가」 | **「멈춘 자리가 있는가」** |
| `decide_outcome` | 건너뛰기면 무조건 `PARTIAL_PASS` | 건너뛰지 않은 실패가 남으면 `FAIL` |

앞의 둘은 **020 이전 동작을 정확히 보존한다.** 그때는 `FAIL` 이 하나뿐이었고 그것이 곧
멈춘 자리였으므로, 「멈춘 자리 하나」와 「모든 `FAIL`」이 같은 것을 가리켰다.
