# Contract: 오류 계약 (004 라운드 변경분)

**Feature**: `specs/004-run-pacing-readiness` | **Date**: 2026-09-07

003 의 [오류 계약](../../003-error-path-hardening/contracts/error-contract.md)을
**확장한다.** 봉투도 필드도 바뀌지 않는다. `code` 값이 둘 늘어난다.

---

## 1. 추가되는 코드

| 코드 | `category` | 언제 | `next_action` |
|---|---|---|---|
| `ELEMENT_NOT_READY` | `blocked` | 대기 예산 안에 어느 후보도 정확히 1개를 매칭하지 못했다 | 대기 예산을 늘리거나 실행 속도를 낮춰 화면을 확인하세요. |
| `ELEMENT_AMBIGUOUS` | `blocked` | 대기 예산 안에 여러 요소만 매칭됐다 | Step 상세에서 요소를 다시 집으세요. |

둘 다 `blocked` 인 것은 의도적이다 — 두 경우 모두 **사용자가 할 일이 있다.** `category` 는
"내가 고칠 수 있는가" 에만 답하며(003 EC-001), 무엇을 할지는 `code` 와 `next_action` 이
말한다.

---

## 2. 기존 `STEP_FAILED` 와의 경계 (FR-120·FR-123)

요소 탐색 실패는 이제 셋으로 갈린다.

```
사용할 수 있는 후보가 애초에 하나도 없다   → STEP_FAILED        정의 문제
예산 안에 아무도 1개를 매칭하지 못했다      → ELEMENT_NOT_READY   화면이 느린 문제
예산 안에 여러 개만 매칭했다               → ELEMENT_AMBIGUOUS   정의가 낡은 문제
```

**FR-123 이 요구하는 것**: 문구를 해석하지 않고 `code` 만으로 갈려야 한다. 위 표가 그
보장이다 — 화면은 `code` 로 분기하고 `message` 를 파싱하지 않는다.

**`STEP_FAILED` 에 남는 것**: `ordered_strategies()` 가 빈 목록을 돌려준 경우. 모든 후보가
미수집·모호·검증 실패 상태라 시도할 것이 없다. 이것은 기다려도 달라지지 않는 문제이며,
지금도 같은 코드로 나가고 있다.

---

## 3. 응답 예시

### `ELEMENT_NOT_READY`

```json
{
  "error": {
    "code": "ELEMENT_NOT_READY",
    "category": "blocked",
    "message": "요소를 찾을 수 없습니다. 10000ms 동안 모든 식별 후보를 다시 확인했습니다. 시도한 식별 정보: testId=order-row, role=button name='주문 상세'",
    "next_action": "대상 화면이 느릴 수 있습니다. 실행 속도를 '느림'으로 낮춰 화면을 확인하거나, Step 상세에서 대기 시간을 늘린 뒤 다시 실행하세요.",
    "detail": {}
  }
}
```

**메시지가 반드시 담아야 하는 것** (FR-121):
- 실제 기다린 시간
- 시도한 후보 목록 (`locator_attempts` 가 구조화된 형태로도 함께 나간다)

### `ELEMENT_AMBIGUOUS`

```json
{
  "error": {
    "code": "ELEMENT_AMBIGUOUS",
    "category": "blocked",
    "message": "요소가 여러 개 매칭되어 어느 것을 조작할지 결정할 수 없습니다. text='주문 상세' 가 3개를 매칭합니다.",
    "next_action": "화면이 바뀌어 이 식별 정보가 더 이상 하나를 가리키지 않습니다. Step 상세에서 요소를 다시 집으세요.",
    "detail": {}
  }
}
```

**왜 하나를 골라 진행하지 않는가**: 자동으로 첫 번째를 고르면 잘못된 요소에 대해 테스트가
**통과할 수 있다.** 이 코드베이스가 스스로 "실패보다 나쁜 결과" 라고 부르는 상황이다
(`locator_runtime.py` 모듈 독스트링, `CandidateStatus.AMBIGUOUS` 주석). 실측으로 현재
코드가 그렇게 동작함을 확인했다 (research R2).

---

## 4. 마스킹

기존 규칙을 그대로 따른다. 오류 메시지는 `Scrubber` 를 지나며, 복호화된 민감 값이
들어가지 않는다. 식별 후보 값(`text=…`)은 화면에서 읽은 것이지 사용자가 입력한 비밀값이
아니므로 마스킹 대상이 아니다 — 단, 비밀 변수가 채워진 입력란을 대상으로 하는 Step 의
메시지는 기존과 같이 스크러버를 거친다.

---

## 5. 하위 호환

| 소비자 | 영향 |
|---|---|
| `code` 로 분기하지 않고 `category` 만 쓰는 화면 | 영향 없음. 둘 다 `blocked` |
| `code` 목록을 손으로 복제한 화면 | 없다 — 003 이 스키마 생성 파이프라인으로 대체했다 (`itb.schema.export` → `error-response.schema.json` → TypeScript) |
| 기존 계약 테스트 | 통과. 코드 추가는 기존 코드의 형태를 바꾸지 않는다 |

**생성 파이프라인을 갱신해야 한다**: `backend/schema/error-response.schema.json` 과
`frontend/src/types/generated/error-response.d.ts` 를 다시 내보낸다. 손으로 고치지 않는다
(헌법 Cross-language schema duty).
