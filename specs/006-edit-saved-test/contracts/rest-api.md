# Contract: REST API (006 라운드 변경분)

**Feature**: `specs/006-edit-saved-test` | **Date**: 2026-09-07

001 의 [`contracts/rest-api.md`](../../001-interactive-ai-test-builder/contracts/rest-api.md),
004·005 의 변경분을 **확장한다.** 신규 엔드포인트 2개, 기존 엔드포인트에 필드 1개, 오류 코드
1개가 늘어난다. **기존 엔드포인트의 응답 형태는 바뀌지 않으므로 기존 클라이언트는 그대로
동작한다.**

**이 계약의 불변식** (원칙 II — 재생 경로 언어모델 금지):
아래 두 엔드포인트는 작성(authoring) 계층을 부르지 않는다. 자연어 Step 추가는 지금처럼
`POST /api/sessions/{id}/ai-step` 에만 남는다.

---

## 1. `GET /api/tests/{test_id}/definition` — 편집을 위한 정의 조회 (신규)

기존 `GET /api/tests/{test_id}` 는 그대로 남는다(응답이 `Test` 다). 편집 화면은 저장 충돌
감지와 편집 가능 여부를 함께 알아야 하므로 감싼 응답을 쓴다.

**브라우저를 만들지 않는다.** 대상 앱이 떠 있지 않아도 200 이다 (FR-182).

### 200

```json
{
  "test": { "…": "저장된 Test 그대로 (기존 모델, 변경 없음)" },
  "revision": "3f9a1c2d7e40b118",
  "editable": true,
  "blocked_by": null,
  "blocking_session_id": null,
  "locked_fields": [
    { "field": "steps[].target", "reason": "live_browser_required" },
    { "field": "steps[].type", "reason": "delete_and_insert_instead" },
    { "field": "ai_instruction", "reason": "record_only" },
    { "field": "steps[].author", "reason": "record_only" }
  ]
}
```

- `revision` — 정의 파일 내용의 SHA-256 앞 16자. 저장 요청이 이 값을 되돌려 보낸다
- `locked_fields[].reason` — 화면이 쓰는 **문구 키**다. 문장을 서버가 정하지 않는다.
  `live_browser_required` 만 「브라우저 열기」 경로를 함께 보여준다 (FR-191·FR-202)

### 실행 중일 때도 200 이다

편집 화면은 열리고, **읽기 전용**으로 그려진다 (FR-206). 화면을 못 열게 하면 사용자는 무엇이
실행 중인지도 볼 수 없다.

```json
{
  "test": { "…": "…" },
  "revision": "3f9a1c2d7e40b118",
  "editable": false,
  "blocked_by": "running",
  "blocking_session_id": "<세션 ID>",
  "locked_fields": [ "…" ]
}
```

`blocking_session_id` 는 화면이 「실행 중인 세션 보기」 버튼을 만들기 위한 것이다. 사용자에게
보이는 문장에는 세션 식별자를 넣지 않는다 (005 FR-135).

### 오류

| 상황 | 상태 | 코드 |
|---|---|---|
| 프로젝트 미개방 | 400 | `PROJECT_NOT_OPEN` |
| 없는 테스트 | 404 | `TEST_NOT_FOUND` |
| 정의 파일이 스키마 위반 | 400 | `DEFINITION_INVALID` — 어느 파일 어느 지점이 왜 잘못됐는지 `message` 에 담는다 (FR-196 · Edge Case) |

---

## 2. `PUT /api/tests/{test_id}/definition` — 편집 저장 (신규)

**요청은 편집 결과가 아니라 편집 연산 목록이다** (research R3). 서버가 저장된 정의를 읽어
`itb.execution.step_edits` 로 연산을 적용한다 — 편집 규칙의 구현이 한 곳에만 있게 하기 위한
계약이다.

### 요청

```json
{
  "revision": "3f9a1c2d7e40b118",
  "edits": [
    { "op": "update", "step_id": "step-02", "value": "operator" },
    { "op": "update", "step_id": "step-05", "timeout_ms": 30000, "label": "대시보드 열기" },
    { "op": "delete", "step_id": "step-07" },
    { "op": "reorder", "order": ["step-01", "step-03", "step-02", "step-04", "step-05", "step-06"] },
    { "op": "set_name", "name": "로그인 후 대시보드" },
    { "op": "set_start_url", "url": "http://127.0.0.1:4400/login.html" },
    { "op": "set_assertion_value", "step_id": "step-06", "value": "환영합니다" }
  ]
}
```

- `extra="forbid"`. 알 수 없는 필드는 거절한다 (FR-211)
- `edits` 는 1건 이상. 빈 목록은 400 — 저장할 것이 없는 저장은 없다 (FR-195 의 서버 쪽 짝)
- `update` 는 `label`·`value`·`timeout_ms`·`tab` 중 최소 하나
- **locator 관련 필드가 이 모델에 없다.** 구조적으로 후보를 손댈 수 없다 (원칙 IV, R6)
- **평문 민감 값을 받는 필드가 없다.** `value` 에는 참조 문자열이 들어올 수 있을 뿐이다 (R10)

### 적용

목록 순서대로 적용한다. **하나라도 실패하면 전부 적용하지 않고 파일도 쓰지 않는다.**
`step_edits` 는 `current_step_index = 0` 으로 부르므로 "이미 실행된 구간" 경고가 생기지 않는다.

### 200

```json
{
  "test": { "…": "저장된 새 Test" },
  "revision": "8b21d0f4a7c93e55",
  "editable": true,
  "blocked_by": null,
  "blocking_session_id": null,
  "locked_fields": [ "…" ],
  "warnings": [
    "{{API_TOKEN}} 을 참조하지만 그 변수의 값이 정의되지 않았습니다. 실행하면 빈 값이 채워집니다."
  ]
}
```

응답은 `GET` 과 같은 형태에 `warnings` 가 붙는다. **`revision` 이 새 값으로 바뀐다** — 화면은
이것을 받아 다음 저장에 쓴다. 다시 조회하지 않는다.

`warnings` 는 저장을 막지 않는 것들이다 (FR-216 · 순서 변경 경고). 막는 것은 오류로 낸다.

### 오류

| # | 상황 | 상태 | 코드 | 비고 |
|---|---|---|---|---|
| V1 | 요청 형태 위반 | 400 | `DEFINITION_INVALID` | |
| V2 | `revision` 불일치 | 409 | `DEFINITION_STALE` **(신규 코드)** | `detail` 에 현재 `test` 와 `revision` 을 함께 준다 — 화면이 다시 조회하지 않고 사용자에게 두 선택(덮어쓰기·다시 읽기)을 줄 수 있다 (FR-209) |
| V3 | 그 테스트가 실행 중 | 409 | `SESSION_ALREADY_ACTIVE` | `detail.session_id` 포함. 005 와 같은 형태 (FR-207) |
| V4 | 알 수 없는 `step_id` | 404 | `TEST_NOT_FOUND` 아님 → `DEFINITION_INVALID` | Step 은 테스트의 일부이므로 테스트를 못 찾은 것과 구분한다 |
| V4 | 값을 갖지 않는 Step 종류에 `value` | 400 | `DEFINITION_INVALID` | `ValueNotSupportedError` 의 문장을 그대로 옮긴다 |
| V4 | `reorder` 목록이 현재 집합과 불일치 | 400 | `DEFINITION_INVALID` | 부분 적용하지 않는다 |
| V5 | 적용 결과가 Step 0개 | 400 | `STEP_LIST_EMPTY` | 기존 코드 재사용 (FR-197) |
| V6 | 민감 참조를 평문으로 교체 시도 | 400 | `DEFINITION_INVALID` | `next_action` 으로 비밀 값 화면을 가리킨다 (FR-213) |
| V7 | `Test` 모델 검증 실패 | 400 | `DEFINITION_INVALID` | |
| — | 파일 쓰기 실패 | 500 | `STORAGE_WRITE_FAILED` | 조용히 넘기지 않는다 (FR-198) |

### `DEFINITION_STALE` 응답 예

```json
{
  "code": "DEFINITION_STALE",
  "message": "이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.",
  "category": "blocked",
  "next_action": "바뀐 내용을 확인한 뒤 다시 읽거나 내 편집으로 덮어쓸지 고르세요.",
  "detail": {
    "test_id": "TC-001",
    "revision": "c40e9b7712a5d83f",
    "test": { "…": "현재 저장된 정의" }
  }
}
```

**덮어쓰기 방법**: 사용자가 덮어쓰기를 고르면 화면은 `detail.revision` 을 실어 같은 요청을
다시 보낸다. 서버에 "강제" 플래그를 두지 않는다 — 플래그는 습관이 되고, 습관이 되면 감지가
무의미해진다.

---

## 3. `POST /api/sessions` — `pause_before_index` 필드 추가

`mode: "replay"` 에서만 쓴다. 다른 모드와 함께 오면 400.

```json
{ "mode": "replay", "test_id": "TC-001", "pause_before_index": 5 }
```

- 러너는 인덱스 0..4 를 실행한 뒤, **인덱스 5 의 Step 을 실행하기 전에** 기존 `PAUSED` 상태로
  들어간다 (FR-200)
- 범위: `0 <= pause_before_index < len(steps)`. 벗어나면 400 `DEFINITION_INVALID`
- `0` 이면 아무 Step 도 실행하지 않고 시작 주소만 열린 상태에서 멈춘다
- 생략하거나 `null` 이면 **지금과 완전히 같다.** 기존 클라이언트에 영향 없음
- 새 상태를 만들지 않는다 — 004 의 `한 스텝씩` 과 같은 경계에서 같은 `PAUSED` 로 들어간다
  (R7). 도달한 뒤에는 기존 일시정지 편집 계약(`/api/sessions/{id}/steps*`)이 그대로 적용된다
  (FR-205)

**동시 실행 규칙은 그대로다**: 같은 `test_id` 로 살아 있는 세션이 있으면 409
`SESSION_ALREADY_ACTIVE` (005 FR-128).

---

## 4. 신규 오류 코드

| 코드 | 뜻 | 상태 |
|---|---|---|
| `DEFINITION_STALE` | 편집을 시작한 뒤 정의 파일이 외부에서 바뀌었다 | 409 |

`DEFINITION_INVALID`(스키마 위반)와 갈라 두는 이유는 **사용자가 할 일이 다르기 때문**이다.
`DEFINITION_INVALID` 는 내 편집이 잘못된 것이고, `DEFINITION_STALE` 은 내 편집은 멀쩡한데
바탕이 바뀐 것이다. 같은 코드로 내보내면 사용자는 멀쩡한 편집을 고치려 들고, 고칠 것이 없어
헤맨다 — `ELEMENT_NOT_READY` 를 `STEP_FAILED` 와 갈라 둔 것과 같은 판단이다.

---

## 5. 바뀌지 않는 것 (명시)

| 엔드포인트 | 확인 |
|---|---|
| `GET /api/tests/{test_id}` | 응답은 `Test` 그대로. 편집 화면은 `/definition` 을 쓰지만 이 경로를 없애지 않는다 |
| `PATCH /api/tests/{test_id}` | 이름 변경 전용으로 그대로 둔다. 여기에 편집을 실으면 기존 호출자의 계약이 흔들린다 |
| `/api/sessions/{id}/steps*` 전부 | 세션 편집 계약 그대로. `PAUSED` 게이트도 그대로 |
| `POST /api/sessions/{id}/save` | 세션의 저장 경로 그대로. 정의 저장과 같은 `repo.write_test()` 로 수렴한다 |
| `/api/secrets/*` | 민감 값은 계속 이쪽에서만 다룬다 (R10) |
