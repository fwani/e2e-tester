# API 계약 — 026

016 의 `contracts/api-contract.md` 와 **같은 모양**이다. 다른 자리만 굵게 적는다.

---

## §1 세션 시작 — `POST /api/sessions`

```jsonc
{
  "test_id": "t-0001",
  "mode": "step_edit",          // 새 모드
  "step_edit_step_id": "step-03" // 고칠 Step 하나
}
```

### 거절 조건

| 조건 | 코드 | 문장 |
|---|---|---|
| `mode="step_edit"` 인데 `step_edit_step_id` 가 없다 | `DEFINITION_INVALID` | 고칠 Step 을 지정하세요. |
| 그 id 가 정의에 없다 | `DEFINITION_INVALID` | `step-03` 을 찾을 수 없습니다. |
| `test_id` 가 없다 | `DEFINITION_INVALID` | 저장된 테스트가 필요합니다. |
| 다른 세션이 그 테스트를 잡고 있다 | 기존 규칙 그대로 | 기존 문장 그대로 |

**여럿을 보낼 길이 없다.** 필드가 배열이 아니다 (data-model §4).

### 시작 순서 — **이 순서가 계약이다**

016 §1 과 같다. 원칙 II 때문이다.

1. 러너를 도착점까지 돌린다 — **이 구간에 에이전트 태스크가 없다**
2. 러너가 멈춘다
3. 그제서야 에이전트를 만든다 (첫 대화 턴에서)

도착점 = 대상 Step 의 시작 시점 순번. 대상이 첫 Step 이면 **실행 없이 시작 주소만 연다**
(FR-008).

도착점에 닿지 못하면 **세션을 열지 않는다.** 어느 Step 에서 왜 실패했는지 돌려준다
(FR-007).

---

## §2 확정 — `POST /api/sessions/{id}/step-edit/commit`

| | |
|---|---|
| 조건 | 열려 있는 Step 수정이 있다 |
| 하는 일 | 트랜잭션을 닫는다. **Step 을 지우지 않는다** |
| 응답 | `SessionView` |
| 이벤트 | `step_edit_changed` (`step_edit: null`) |

**브라우저를 요구하지 않는다** (FR-023). 정의만 고치는 편집이므로 검토 국면에서도 된다 —
016 FR-026a 와 같은 판단이다.

**만든 것이 없어도 확정된다** (research R5). 016 의 `NothingCreatedError` 에 대응하는
거절이 **없다.**

| 거절 | 코드 |
|---|---|
| 열려 있는 수정이 없다 | `CONFLICT` |
| 이미 끝났다 | `CONFLICT` |

---

## §3 버리기 — `POST /api/sessions/{id}/step-edit/discard`

| | |
|---|---|
| 하는 일 | ① 이번에 만든 Step 을 지우고 ② 대상을 원본으로 되돌린다 — **하나의 결과로** |
| 그다음 | 화면을 도착점으로 되맞춘다 (FR-025) |
| 이벤트 | `step_edit_changed` (`null`), 실패 시 `step_edit_realign_failed` |

**세션을 끝내지 않는다** (FR-026). 끝내는 조작은 기존 「중지」다.

되맞춤 중에는 **언어모델이 호출되지 않는다** (FR-027). 016 의 `_return_to_start()` →
`_realign_to_arrival()` 을 그대로 쓴다.

### `step_edit_realign_failed` 페이로드

```jsonc
{
  "failed_step_id": null,
  "reason": "TimeoutError: ...",
  "definition_reverted": true   // 정의는 이미 되돌아갔다
}
```

**두 사실을 함께 말한다** (FR-028). 하나만 말하면 사용자는 무엇을 믿어야 할지 모른다.

---

## §4 세션 조회에 실리는 것

`SessionView` 에 `step_edit` 이 더해진다.

```jsonc
{
  "step_edit": {
    "target_id": "step-03",
    "target_index": 2,
    "created_count": 1,
    "can_commit": true
  }
}
```

`rerecord` 와 **동시에 차 있지 않다.** 둘 다 `null` 인 것이 보통 상태다.

---

## §5 바뀌지 않는 것

- `POST /api/sessions/{id}/rerecord/commit` · `/discard` — 016 그대로 (FR-030)
- 대화 통로 (`/chat`) — 016 그대로. 새 입력 자리를 만들지 않는다 (FR-010)
- 막힘 처리 · 인수 · 중지 — 전부 그대로
- 저장 (`PUT /api/tests/{id}`) — 확정되지 않은 수정은 여기 닿지 않는다
