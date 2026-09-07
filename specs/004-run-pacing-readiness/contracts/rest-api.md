# Contract: REST API (004 라운드 변경분)

**Feature**: `specs/004-run-pacing-readiness` | **Date**: 2026-09-07

001 의 `contracts/rest-api.md` 를 **확장한다.** 기존 엔드포인트의 형태는 바뀌지 않으며,
요청에 선택 필드 하나가 늘고 엔드포인트 셋이 추가된다. 기존 클라이언트는 새 필드를 보내지
않아도 동작한다.

---

## 1. 세션 생성 — 속도 지정 (기존 수정)

`POST /api/sessions`

### 요청 본문 (추가 필드)

| 필드 | 타입 | 필수 | 기본 | 설명 |
|---|---|---|---|---|
| `pacing` | `"fast" \| "normal" \| "slow" \| "step"` | 아니오 | 저장된 취향 → 없으면 `"normal"` | 이 세션의 실행 속도 |

```json
{
  "mode": "replay",
  "test_id": "TC-001",
  "pacing": "slow"
}
```

**기본값 해석 순서** (FR-109):

1. 요청에 `pacing` 이 있으면 그 값
2. 없으면 `~/.config/itb/preferences.json` 의 `run_pacing`
3. 파일이 없거나 읽지 못하면 `"normal"`

무인 실행(CI)은 `"fast"` 를 **명시한다.** 저장된 취향이 무인 경로를 느리게 만들지 않게 하는
유일한 방법이다.

### 오류

| 상황 | 상태 | 코드 |
|---|---|---|
| `pacing` 이 열거형 밖 | 422 | `DEFINITION_INVALID` |

임의의 밀리초 값은 받지 않는다. 단계를 제한하는 것이 목적이다 (data-model §1).

---

## 2. 실행 중 속도 변경 (신규)

`POST /api/sessions/{session_id}/pacing`

실행 중에도 호출할 수 있다. **진행 중인 Step 을 끊지 않으며 다음 Step 경계부터
적용된다** (FR-103).

### 요청

```json
{ "pacing": "slow" }
```

### 응답 `200`

`SessionView` 를 그대로 돌려준다 (001 형태 + 아래 §4 의 추가 필드).

### 동작 규칙

- 브라우저에 **아무 명령도 보내지 않는다** (원칙 III 계열).
- 이 호출은 취향 파일에도 기록한다 — FR-109 의 "다음 실행에서 마지막 선택이 기본값" 이
  성립하려면 실행 중 변경도 반영돼야 한다.
- 취향 파일 쓰기가 실패해도 **이 호출은 성공한다.** 세션의 속도는 이미 바뀌었고, 취향을
  못 남긴 것 때문에 실행을 방해하지 않는다. 실패는 `pacing_changed` 이벤트의
  `preference_saved: false` 로 알린다.

### 오류

| 상황 | 상태 | 코드 |
|---|---|---|
| 세션 없음 | 404 | `SESSION_NOT_FOUND` |
| 세션이 종료 상태 | 409 | `INVALID_TRANSITION` |
| `pacing` 이 열거형 밖 | 422 | `DEFINITION_INVALID` |

**세션 유실(`LOST`) 상태에서는?** 409 `SESSION_LOST`. 유실 후에는 저장과 처음부터
재실행만 허용된다는 기존 불변식(state_machine 불변식 5)을 따른다.

---

## 3. 사용자 취향 (신규)

### `GET /api/preferences`

```json
{
  "run_pacing": "normal",
  "warning": null
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `run_pacing` | `"fast" \| "normal" \| "slow" \| "step"` | 저장된 속도 |
| `warning` | `string \| null` | 파일을 읽지 못한 사유. **조회 자체는 실패하지 않는다** |

**`warning` 이 있는 경우**: `run_pacing` 은 기본값 `"normal"` 이다. 취향을 못 읽었다고
첫 화면이 안 열리면 사용자는 아무것도 할 수 없다 — `GET /api/project` 목록이 레지스트리
읽기 실패를 경고로만 처리하는 것과 같은 판단이다.

### `PUT /api/preferences`

```json
{ "run_pacing": "slow" }
```

응답은 `GET` 과 같은 형태.

| 상황 | 상태 | 코드 |
|---|---|---|
| `run_pacing` 이 열거형 밖 | 422 | `DEFINITION_INVALID` |
| 파일을 쓰지 못함 | 500 | `INTERNAL_ERROR` |

**쓰기는 원자적이다** — `storage/atomic.py` 를 재사용한다. 부분 기록된 파일을 남기지
않는다.

**담기는 것은 취향뿐이다.** 자격 증명·경로·프로젝트 식별자를 이 엔드포인트로 저장할 수
없다 (조직 보안 요건, data-model §5).

---

## 4. SessionView 확장 (기존 수정)

| 필드 | 타입 | 설명 |
|---|---|---|
| `pacing` | `"fast" \| "normal" \| "slow" \| "step"` | 이 세션의 현재 속도 |

**왜 필요한가**: WebSocket 재연결 시 전체 상태를 동기화하는 것이 `SessionView` 의 목적이다.
속도가 빠지면 재연결 후 화면의 속도 표시가 세션과 어긋난다.

**화면이 이 값으로 하는 일**: `state == "paused"` 일 때 문구를 가른다 —
`pacing == "step"` 이면 "한 스텝씩 — 다음 Step 을 기다립니다", 아니면 "일시정지됨".
상태가 같고 의미가 다른 두 경우를 구별하는 유일한 근거다 (research R7).

---

## 5. 실행 결과 확장 (기존 수정)

`GET /api/tests/{test_id}/runs/{run_id}` 의 `steps[]` 항목에 필드 하나가 는다.

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `element_wait_ms` | `int` | 0 | 요소가 나타나기를 기다린 시간 (FR-114) |

기존 필드는 이름도 의미도 바뀌지 않는다. `tab_wait_ms` 와 나란히 놓인다.

**불변식**: `tab_wait_ms + element_wait_ms <= duration_ms`. Step 간 간격은 **포함되지
않는다** (FR-105).

---

## 6. 하위 호환

| 소비자 | 영향 |
|---|---|
| `pacing` 을 안 보내는 클라이언트 | 저장된 취향 또는 `"normal"` 로 동작. 현재보다 느려진다 — 의도된 기본값 변경 (research R8) |
| `pacing` 필드를 모르는 클라이언트 | `SessionView` 의 새 필드를 무시하면 동작. 단, `paused` 문구 구별을 못 한다 |
| `element_wait_ms` 를 모르는 결과 화면 | 무시하면 동작. 대기 시간을 못 보여줄 뿐이다 |
| 기존 실행 결과 파일 | `element_wait_ms` 가 없다. 기본값 0 으로 읽힌다 |

**기본값이 `fast` 가 아닌 것이 유일한 파괴적 변경이다.** 이 기능의 존재 이유가 "사람이 못
따라간다" 이므로 기본이 현재 동작이면 아무것도 달라지지 않는다. 한 번의 선택으로 `fast` 가
유지된다 (FR-109).
