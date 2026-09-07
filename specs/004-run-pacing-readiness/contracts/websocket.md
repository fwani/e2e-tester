# Contract: WebSocket 이벤트 (004 라운드 변경분)

**Feature**: `specs/004-run-pacing-readiness` | **Date**: 2026-09-07

001 의 `contracts/websocket.md` 를 **확장한다.** 기존 이벤트의 이름과 페이로드는 바뀌지
않는다. 이벤트 하나가 추가되고, 기존 이벤트 하나에 필드가 는다.

---

## 1. `pacing_changed` (신규)

실행 속도가 바뀌었다. 여러 화면이 같은 세션을 볼 때 서로 동기화되게 한다.

```json
{
  "type": "pacing_changed",
  "pacing": "slow",
  "delay_ms": 1500,
  "auto_pause": false,
  "preference_saved": true
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `pacing` | `"fast" \| "normal" \| "slow" \| "step"` | 새 속도 |
| `delay_ms` | `int` | 그 속도의 Step 간 간격 |
| `auto_pause` | `bool` | 매 Step 경계에서 자동 일시정지하는가 |
| `preference_saved` | `bool` | 취향 파일에 남겼는가 |

**왜 `delay_ms` 와 `auto_pause` 를 함께 싣는가**: 화면이 대응표를 따로 들고 있으면 서버와
갈린다 (data-model §1 불변식). 값을 함께 보내면 대응표가 서버 한 곳에만 남는다.

**`preference_saved: false`**: 속도는 바뀌었지만 취향 파일에 남기지 못했다. 화면은 이
경우 "다음 실행에는 유지되지 않습니다" 를 알린다. 실행을 막지 않는다.

**발행 시점**: `POST /api/sessions/{id}/pacing` 처리 직후. 세션 생성 시에는 발행하지
않는다 — `SessionView` 응답에 이미 들어 있다.

---

## 2. `step_finished` 확장 (기존 수정)

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `element_wait_ms` | `int` | 0 | 요소가 나타나기를 기다린 시간 (FR-114) |

```json
{
  "type": "step_finished",
  "step_id": "step-03",
  "index": 2,
  "outcome": "pass",
  "duration_ms": 2340,
  "element_wait_ms": 2089,
  "resolved_candidate": "role"
}
```

기존 필드는 그대로다. 이 값이 있으면 실행 중에도 "이 Step 이 왜 오래 걸렸는지" 가 보인다.

---

## 3. `step_failed` 확장 (기존 수정)

페이로드 형태는 바뀌지 않는다. `error` 필드의 `code` 에 값 둘이 늘어난다
(→ [error-contract.md](./error-contract.md)).

```json
{
  "type": "step_failed",
  "step_id": "step-03",
  "index": 2,
  "error_message": "요소를 찾을 수 없습니다. 10000ms 동안 기다렸습니다. …",
  "locator_attempts": [ … ],
  "tab_wait_ms": 0,
  "element_wait_ms": 10000,
  "error": {
    "code": "ELEMENT_NOT_READY",
    "category": "blocked",
    "message": "요소를 찾을 수 없습니다. …",
    "next_action": "대기 예산을 늘리거나 실행 속도를 낮춰 화면을 확인하세요.",
    "detail": {}
  }
}
```

`error_message` 는 001·002 의 화면과 검증이 읽는 이름이라 그대로 둔다 (003 이 세운 규칙).

---

## 4. Step 간 간격 동안 발행되는 이벤트

**없다.** 간격 동안 새 이벤트를 만들지 않는다.

**왜**: 마지막으로 발행된 이벤트가 `step_finished` 이므로, 화면은 자연히 방금 끝난 Step 과
그 결과를 보여주는 상태로 머문다 — FR-107 이 요구하는 것이 정확히 그것이다. 별도의
"쉬는 중" 이벤트를 만들면 화면이 처리할 상태가 하나 늘고, 얻는 것이 없다.

**`한 스텝씩` 의 경우**: 자동 일시정지가 기존 `state_changed`(`state: "paused"`)를
발행한다. 새 이벤트가 필요 없다 (research R7).

---

## 5. 하위 호환

| 소비자 | 영향 |
|---|---|
| `pacing_changed` 를 모르는 화면 | 알 수 없는 이벤트를 무시하면 동작. 다른 창에서 바꾼 속도가 반영되지 않을 뿐 |
| `element_wait_ms` 를 모르는 화면 | 무시하면 동작 |
| 신규 오류 코드를 모르는 화면 | `category` 와 `message` 는 그대로 읽힌다. `code` 별 분기가 없으면 기본 처리로 떨어진다 |

**기존 이벤트를 제거하거나 이름을 바꾸지 않는다.** 001·002·003 의 계약 테스트
(`tests/contract/test_ws_events.py`)가 그대로 통과해야 한다.
