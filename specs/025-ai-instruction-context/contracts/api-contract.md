# API 계약 — 지시문 정제와 작업 계획 (025)

**Date**: 2026-09-29 | **Spec**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md)

기존 경로를 바꾸지 않는 것이 이 계약의 기본 원칙이다. 새 엔드포인트 하나가 늘고, 세션 생성
요청에 선택 항목 하나가 는다. **둘 다 없어도 지금과 같이 동작한다** (FR-012).

---

## §1. 지시문 정제 — `POST /api/instruction/refine`

세션과 무관한 자리에 둔다. 브라우저가 뜨기 전에 불리고, 결과를 사용자가 확인한 뒤에야 세션이
만들어진다 (research R7).

### 요청

```json
{
  "instruction": "관리자 계정으로 로그인한 후 …"
}
```

| 필드 | 형 | 규칙 |
|---|---|---|
| `instruction` | `string` | 필수. 1자 이상 8000자 이하 (`MAX_INSTRUCTION_CHARS` 와 같은 출처) |

### 응답 200 — 정제 성공

```json
{
  "refined": true,
  "plan": {
    "constraints": [
      { "text": "기존 등록된 데이터는 검증에 사용하지 않는다", "scope": "global", "item_id": null },
      { "text": "연결 주소는 {{menu_url_create}} 를 쓴다", "scope": "item", "item_id": "i4" }
    ],
    "items": [
      { "id": "i1", "order": 1, "text": "관리자 계정으로 로그인한다", "status": "pending", "skip_reason": null },
      { "id": "i2", "order": 2, "text": "운영 관리 > 메뉴관리로 이동한다", "status": "pending", "skip_reason": null }
    ],
    "source": "refined"
  },
  "notes": ["자격 증명 2건을 변수 참조로 바꿨습니다."]
}
```

| 필드 | 설명 |
|---|---|
| `refined` | 정제가 성공했는가 |
| `plan` | 정제 결과. 데이터 모델 §1 |
| `notes` | 사용자에게 알릴 것. 자격 증명 치환 같은 **뜻이 바뀐 자리**를 반드시 싣는다 |

### 응답 200 — 정제 실패

**오류로 돌려주지 않는다.** 정제 실패는 작성을 막는 사건이 아니다 (FR-020).

```json
{
  "refined": false,
  "plan": null,
  "notes": ["지시문을 정제하지 못했습니다. 원문 그대로 진행할 수 있습니다."]
}
```

화면은 이 응답을 받으면 원문으로 진행하는 길을 연다. 사용자가 다시 시도할 수도 있다.

### 응답 400

요청 검증 실패만 400 이다 — 빈 지시문, 길이 초과. 정제 자체의 실패는 위의 200 이다.

### 이 엔드포인트가 세션을 만들지 않는 이유

정제와 세션 생성이 한 호출이면, 정제 결과를 본 사용자가 고치려 할 때 이미 브라우저가 떠
있다. 되돌리는 조작이 필요해지고, 그 조작은 「시작했다가 취소한 세션」이라는 상태를 만든다.
두 호출로 갈라 두면 그 상태 자체가 생기지 않는다.

---

## §2. 세션 생성 — `POST /api/sessions` (기존 경로에 선택 항목 추가)

### 요청에 더해지는 것

```json
{
  "mode": "ai",
  "ai_instruction": "…원문…",
  "work_plan": { "constraints": [...], "items": [...], "source": "refined" }
}
```

| 필드 | 형 | 규칙 |
|---|---|---|
| `work_plan` | `object \| null` | 선택. `mode == "ai"` 에서만 쓰인다. 없으면 지금과 같이 동작한다 |

**`ai_instruction` 은 계속 필수다.** 계획이 있어도 원문을 함께 보낸다 — 정제 기록의 절반이고
(데이터 모델 §5), 계획이 뜻을 바꿨을 때 대조할 것이 필요하다.

**`mode != "ai"` 에 `work_plan` 이 오면 거절한다.** 400 · `DEFINITION_INVALID`. 조용히
무시하면 사용자는 계획이 쓰이고 있다고 믿는다.

**항목 수 상한은 200 이다.** 그보다 많으면 400. 매 턴 주입되는 값이므로 상한 없이 받으면
예산 축약이 상시로 일어나 계획이 늘 부분만 보인다.

---

## §3. 작업 계획 조회 — `GET /api/sessions/{session_id}/plan`

화면이 진척을 그리기 위한 것 (FR-028).

### 응답 200

```json
{
  "plan": {
    "constraints": [...],
    "items": [
      { "id": "i1", "order": 1, "text": "관리자 계정으로 로그인한다", "status": "done", "skip_reason": null },
      { "id": "i2", "order": 2, "text": "…", "status": "pending", "skip_reason": null }
    ],
    "source": "refined"
  },
  "remaining": 3
}
```

계획이 없는 세션이면 `plan: null`, `remaining: 0`.

---

## §4. 계획 항목 수정 — `PATCH /api/sessions/{session_id}/plan/items/{item_id}`

사용자가 상태를 되돌리는 자리 (데이터 모델 §2 의 상태 전이).

```json
{ "status": "pending" }
```

- 사용자는 어느 상태로든 옮길 수 있다. `skipped` 로 옮기려면 `skip_reason` 이 필요하다.
- 없는 항목이면 404 · `PLAN_ITEM_NOT_FOUND`.
- 계획이 없는 세션이면 409 · `PLAN_ABSENT`.

---

## §5. 이벤트 — `plan_progress`

항목 상태가 바뀔 때 세션 이벤트로 흘린다. 화면이 폴링하지 않게 하기 위한 것이다.

```json
{
  "type": "plan_progress",
  "item_id": "i3",
  "status": "done",
  "remaining": 2
}
```

**작성 주체별로 이벤트를 나누지 않는다.** AI 가 표시한 것과 사람이 되돌린 것이 같은 통로로
온다 — 016 FR-039 가 편집 이벤트에서 정한 것과 같은 판단이다. 통로가 둘이면 한쪽만 그리는
자리가 생긴다.

---

## §6. 완료 보고에 더해지는 것

지시 수행이 끝났을 때 발행되는 `ai_finished` 에 남은 항목이 실린다 (FR-028).

```json
{
  "type": "ai_finished",
  "step_count": 12,
  "remaining_items": [
    { "order": 7, "text": "삭제 확인창에서 취소를 선택한다" }
  ]
}
```

`remaining_items` 가 비어 있지 않은데 AI 가 「끝냈다」고 말하는 상태가 성립한다. 그것이
사용자에게 보여야 하는 사실이다 — 완료 보고가 남은 일을 덮으면 안 된다.

계획이 없는 세션에서는 이 필드가 빈 배열이다.

---

## §7. 무엇을 바꾸지 않는가

| 기존 경로 | 이 기능의 영향 |
|---|---|
| `POST /api/sessions` (`mode: "record"`) | 없음 |
| `POST /api/sessions` (`mode: "ai"`, `work_plan` 없이) | 없음 — 지금과 같이 동작한다 |
| `POST /api/sessions/{id}/chat` | 없음. 대화로 준 지시가 계획에 항목으로 더해지는 것은 서버 안의 일이다 (FR-029) |
| 자연어 Step 추가 (US6) | 없음 |
| 구간 재녹화 (016) | 없음. 재녹화 세션은 계획 없이 시작한다 |
| 저장·실행·내보내기 | 없음 (FR-035) |
