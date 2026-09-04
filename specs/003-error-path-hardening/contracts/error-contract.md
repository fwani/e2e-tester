# Contract: 오류 계약 (003 라운드 변경분)

**Feature**: `specs/003-error-path-hardening` | **Date**: 2026-09-04

001 의 `contracts/rest-api.md` 가 정의한 오류 형태를 **확장한다.** 봉투는 그대로이고 본문에
필드 둘이 는다. 기존 소비자는 새 필드를 무시해도 동작한다 (RG-102).

---

## 1. 응답 형태

### 001 이 정의한 것 (유지)

```json
{ "error": { "code": "STEP_LIST_EMPTY", "message": "Step이 없어 저장할 수 없습니다.", "detail": {} } }
```

### 003 이후

```json
{
  "error": {
    "code": "STEP_LIST_EMPTY",
    "category": "blocked",
    "message": "Step이 없어 저장할 수 없습니다.",
    "next_action": "브라우저에서 동작을 기록하거나 Step을 추가한 뒤 다시 저장하세요.",
    "detail": {}
  }
}
```

| 필드 | 상태 | 규칙 |
|---|---|---|
| `code` | 기존 | 값 집합에 `INTERNAL_ERROR` 가 추가된다. 기존 23개는 이름·값 모두 유지 |
| `message` | 기존 | 그대로 화면에 보여줄 수 있어야 한다 |
| `detail` | 기존 | 기계가 읽는 부가 정보. 자유 형식 |
| `category` | **신규** | `"blocked"` 또는 `"broken"`. **`code` 로부터 대응표를 통해 결정된다** — 호출부가 직접 넣지 않는다 |
| `next_action` | **신규** | 사용자가 지금 할 수 있는 일. 빈 문자열 금지 |

### 권위 정의와 생성

| 위치 | 역할 |
|---|---|
| `backend/src/itb/domain/error.py` | **유일한 권위 정의**. `ErrorCode`, `Category`, `CATEGORY` 대응표, `ErrorBody`, `ErrorResponse` |
| `backend/schema/error-response.schema.json` | 내보낸 JSON Schema (`python -m itb.schema.export`) |
| `frontend/src/types/generated/error-response.d.ts` | 생성된 TypeScript 타입 (`npm run gen:types`) |
| `frontend/src/api/client.ts` | 생성된 타입을 임포트한다. **손으로 쓴 `ErrorCode` union 을 지운다** |

드리프트는 기존 CI schema-drift 잡이 잡는다. 새 장치를 만들지 않는다 (EC-006).

---

## 2. 분류 규칙

| 분류 | 뜻 | HTTP 상태 | `next_action` 의 성격 |
|---|---|---|---|
| `blocked` | 제품이 규칙에 따라 의도적으로 거절했다 | 주로 4xx. 외부 실패를 옮길 때는 5xx 일 수 있다 | 사용자가 고칠 구체적 방법 |
| `broken` | 제품이 처리하지 못했다 | 주로 5xx | 작업 보존 여부 + 무엇을 남겨 보고할지 |

**상태 코드로 분류를 유추하지 않는다.** `category` 를 읽는다 (EC-002). 둘은 일대일이 아니다.

판단이 서지 않는 오류는 `broken` 이다 — 제품이 스스로를 설명하지 못한 것이므로.

### 코드 → 분류 대응표

`data-model.md §1.3` 이 전체 표를 담는다. 규칙 둘:

1. 모든 `ErrorCode` 가 정확히 하나의 분류를 가진다. 빠지면 검증이 실패한다
2. 하나의 코드가 두 분류에 걸치지 않는다. 걸치면 코드를 나눈다 — `INTERNAL_ERROR` 를 새로 만드는 이유가 이것이다

---

## 3. 금지 사항

| 금지 | 요구사항 |
|---|---|
| 처리되지 않은 오류에 `blocked` 코드를 쓰는 것 (현재 `DEFINITION_INVALID` 재사용) | EC-003 |
| `message`·`next_action`·`detail` 에 내부 파일 경로·호출 스택을 넣는 것 | EC-005 |
| 어느 필드에든 비밀 값을 넣는 것 (화면·로그·저장된 결과 포함) | EC-005 |
| `next_action` 을 비우거나 생략하는 것 | EC-004 |
| 실패한 조작을 성공 응답으로 돌려주는 것 | EC-007 |
| `api/errors.py` 를 거치지 않고 오류를 만들어 내보내는 것 | RG-104-3 |
| 화면이 오류를 공용 통로를 거치지 않고 직접 그리는 것 | RG-104-4 |

---

## 4. 실시간 통로 (EC-008)

진행 상황을 밀어 주는 연결로 오류를 보낼 때도 **같은 `ErrorBody`** 를 싣는다. 이벤트 봉투만
다르다.

```json
{ "type": "error", "error": { "code": "...", "category": "...", "message": "...", "next_action": "...", "detail": {} } }
```

화면은 요청 응답으로 온 오류와 실시간 통로로 온 오류를 **같은 통로**로 표시한다.

---

## 5. 화면 쪽 계약

- 오류 표시는 공용 통로 하나를 지난다. 각 화면이 `message` 를 직접 그리지 않는다
- 공용 통로는 **무엇이 잘못됐는지(`message`)와 다음 행동(`next_action`)을 함께** 보여준다. 하나만 보여주면 판정축 ②를 통과하지 못한다
- `category` 가 `broken` 인 오류는 사용자가 고칠 수 있는 것처럼 보이게 하지 않는다
- 응답이 계약 형태가 아닐 때(연결 실패 등)도 화면은 같은 통로로 표시한다. `code` 는 알 수 없는 값이 되지만 `next_action` 은 있어야 한다

---

## 6. 호환성

| 대상 | 영향 |
|---|---|
| 001·002 의 기존 검증 | 없음. 봉투와 기존 3필드가 그대로다 |
| `ErrorCode` 를 참조하는 기존 코드 | 없음. 이름·값 유지. `api/errors.py` 가 도메인 모델을 다시 내보내 임포트 경로도 유지한다 |
| 요청 검증 실패(422) 응답 | 같은 규칙을 따른다. `category` 는 `blocked` |
| 새 필드를 모르는 소비자 | 무시하면 된다. 필수 필드가 사라지지 않는다 |
