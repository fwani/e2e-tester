# REST API Contract

**기반**: FastAPI. 모든 본문은 JSON. 모든 경로는 `/api` 접두사.
**바인딩**: 로컬 인터페이스 전용, 인증 없음 (FR-088a).
**검증**: 모든 요청 본문은 Pydantic 모델로 검증한다 (FR-085). 검증 실패는 `422`.

오류 응답 공통 형태 (권위 정의: [003 오류 계약](../../003-error-path-hardening/contracts/error-contract.md)):

```json
{ "error": {
    "code": "STEP_LIST_EMPTY",
    "category": "blocked",
    "message": "Step이 없어 저장할 수 없습니다.",
    "next_action": "브라우저에서 동작을 기록하거나 Step을 추가한 뒤 다시 저장하세요.",
    "detail": {} } }
```

| 필드 | 설명 |
|------|------|
| `code` | 오류 식별자. 이름·값은 개명하지 않는다 |
| `category` | `blocked`(제품이 규칙대로 거절) 또는 `broken`(제품이 처리하지 못함). **호출부가 정하지 않는다** — `code` 에서 대응표로 자동 결정된다 |
| `message` | 사람이 읽는 이유. 그대로 화면에 보여줄 수 있다 |
| `next_action` | 사용자가 지금 할 수 있는 일. 비어 있을 수 없다 |
| `detail` | 기계가 읽는 부가 정보 (기본 `{}`) |

`message`·`next_action`·`detail` 어디에도 내부 파일 경로, 호출 스택, 비밀 값, 사용자 입력
원본이 들어가지 않는다. 처리되지 않은 오류는 `INTERNAL_ERROR`·`broken` 으로 나온다 —
정상 거부와 코드만으로 구별된다.

실시간 통로(WebSocket)로 전달되는 오류도 **같은 본문**을 싣는다. 봉투만 다르다.

---

## 프로젝트

| 메서드 | 경로 | 설명 | 요구사항 |
|--------|------|------|----------|
| `GET` | `/api/project` | 현재 열린 프로젝트 메타 | FR-001 |
| `POST` | `/api/project/create` | 디렉터리에 새 프로젝트 생성. `.gitignore` 자동 작성 | FR-001, FR-088b |
| `POST` | `/api/project/open` | 기존 프로젝트 디렉터리 열기 | FR-001 |

`POST /api/project/create` 요청:

```json
{ "path": "/Users/me/tests/dataplatform",
  "name": "데이터 플랫폼",
  "default_start_url": "https://example.internal/login",
  "test_id_attribute": "data-testid" }
```

`path` 는 절대 경로여야 하고, 존재하는 디렉터리여야 한다. 경로 탐색 문자를 거절한다.

---

## 테스트

| 메서드 | 경로 | 설명 | 요구사항 |
|--------|------|------|----------|
| `GET` | `/api/tests` | 목록. 상태·ID·이름·Step 수·작성 방식·마지막 실행·실패 요약 | FR-002, FR-005 |
| `GET` | `/api/tests?q=` | 이름 또는 ID 검색 | FR-003 |
| `GET` | `/api/tests/{id}` | 정의 전문 (Step 목록 포함) | FR-016 |
| `PATCH` | `/api/tests/{id}` | 이름 변경 | FR-007 |
| `DELETE` | `/api/tests/{id}` | 삭제. 되돌릴 수 없음 — 클라이언트가 확인을 받는다 | FR-007 |
| `GET` | `/api/tests/{id}/result` | 최근 실행 결과 (RunResult) | FR-050~FR-054 |
| `GET` | `/api/tests/{id}/result/artifacts/{kind}` | `screenshot` \| `console` \| `network` | FR-052, FR-053 |

`GET /api/tests` 응답에 목록 화면이 필요한 집계를 함께 넣는다 (FR-004):

```json
{ "counts": { "total": 4, "pass": 3, "fail": 1 },
  "tests": [
    { "id": "TC-003", "name": "데이터 업로드", "step_count": 5,
      "authoring_mode": "record", "outcome": "fail",
      "last_run_at": "2026-09-03T01:12:00Z",
      "failure_summary": { "step_index": 5, "message": "\"저장\" 버튼을 찾을 수 없습니다." } }
  ] }
```

`GET /api/tests/{id}/result/artifacts/{kind}` 는 `trace` 를 받으면 `501` 을 반환한다 —
`TRACE` 탭은 MVP 미지원이며 비활성으로 표시된다 (spec 디자인 차이 1).

---

## 세션 (작성 및 실행)

| 메서드 | 경로 | 설명 | 요구사항 |
|--------|------|------|----------|
| `POST` | `/api/sessions` | 세션 시작 | FR-023, FR-045, FR-060 |
| `GET` | `/api/sessions/{sid}` | 상태 조회 (WebSocket 재연결 시 동기화용) | — |
| `POST` | `/api/sessions/{sid}/pause` | 일시정지 | FR-031 |
| `POST` | `/api/sessions/{sid}/resume` | 계속하기 | FR-038 |
| `POST` | `/api/sessions/{sid}/run-from` | `{ "step_index": n }` — 이 Step부터 | FR-039, FR-055 |
| `POST` | `/api/sessions/{sid}/stop` | 중지. 저장 여부는 클라이언트가 확인 후 `save` 호출 | FR-042 |
| `POST` | `/api/sessions/{sid}/save` | `{ "name": "..." }` — 테스트로 저장 | FR-028, FR-029 |

`POST /api/sessions` 요청:

```json
{ "mode": "record",            // record | replay | ai
  "test_id": null,             // replay 이면 필수
  "start_url": "https://example.internal/login",
  "ai_instruction": null }     // ai 이면 필수
```

이미 그 테스트에 활성 세션이 있으면 `409 SESSION_ALREADY_ACTIVE` (FR-043).

### 일시정지 중 편집 (모두 `PAUSED` 상태에서만 허용, 아니면 `409 NOT_PAUSED`)

| 메서드 | 경로 | 설명 | 요구사항 |
|--------|------|------|----------|
| `POST` | `/api/sessions/{sid}/steps` | Step 삽입 (`at` 생략 시 일시정지 위치) | FR-035 |
| `PATCH` | `/api/sessions/{sid}/steps/{step_id}` | 표시 이름·입력값·타임아웃·검증 조건 수정 | FR-035 |
| `DELETE` | `/api/sessions/{sid}/steps/{step_id}` | 삭제 | FR-035 |
| `POST` | `/api/sessions/{sid}/steps:reorder` | `{ "order": ["step-03", ...] }` | FR-035 |
| `POST` | `/api/sessions/{sid}/steps/{step_id}/repick` | "다시 집기" 시작 — 브라우저에서 요소 재지정 대기 | FR-020 |
| `POST` | `/api/sessions/{sid}/assertions` | 검증 Step 추가 (4종 중 하나) | FR-037, FR-013a |
| `POST` | `/api/sessions/{sid}/record-actions:start` | 직접 동작 추가 시작 — 실제 창 전면 배치 | FR-036, FR-023a |
| `POST` | `/api/sessions/{sid}/record-actions:stop` | 직접 동작 추가 종료 | FR-036 |
| `POST` | `/api/sessions/{sid}/ai-step` | `{ "instruction": "..." }` 자연어 Step 추가 | FR-078~FR-081 |

**이미 실행된 Step 편집에 대한 계약** (FR-040a~d): 요청은 **성공한다**. 응답에 경고를 실어 보낸다.

```json
{ "steps": [ ... ],
  "edit_warnings": [
    "step-03 은 이미 실행된 Step입니다. 이 편집은 현재 브라우저 화면에 적용되지 않았습니다." ] }
```

서버는 브라우저에 어떤 명령도 보내지 않는다. 화면 정상화는 사용자 몫이다.

### AI 실패 시 선택 (`AI_BLOCKED` 상태에서만)

| 메서드 | 경로 | 본문 | 요구사항 |
|--------|------|------|----------|
| `POST` | `/api/sessions/{sid}/ai-choice` | `{ "choice": "takeover" }` 직접 수행 | FR-071 |
| | | `{ "choice": "retry" }` AI에게 다시 | FR-072 |
| | | `{ "choice": "skip" }` 건너뛰기 | FR-073 |
| | | `{ "choice": "abort" }` 종료 | FR-074 |

### 탭 (FR-030)

| 메서드 | 경로 | 설명 | 요구사항 |
|--------|------|------|----------|
| `GET` | `/api/sessions/{sid}/tabs` | 열린 탭 목록 (`tab_index`, 제목, URL, 닫힘 여부) | FR-030f |
| `POST` | `/api/sessions/{sid}/mirror-tab` | `{ "tab_index": n }` 미러 표시 탭 변경 | FR-030f, FR-047c |

---

## 비밀 값과 키

**복호화된 값을 반환하는 엔드포인트는 없다.**

| 메서드 | 경로 | 설명 | 요구사항 |
|--------|------|------|----------|
| `GET` | `/api/keys/status` | 키 존재 여부, 공개키 지문, 암호구 보호 여부 | FR-089a, FR-089e |
| `POST` | `/api/keys/generate` | 키 쌍 생성. 이미 있으면 `409` | FR-089a |
| `DELETE` | `/api/keys` | `{ "confirm": "DELETE" }` — 키 쌍 삭제. 봉인된 값도 함께 비운다. 키가 없으면 `404` | FR-089a |
| `POST` | `/api/keys/regenerate` | `{ "confirm": "DELETE", "passphrase": null }` — 지우고 새로 만든다 (`201`) | FR-089a |
| `GET` | `/api/secrets` | **변수 이름 목록과 존재 여부만** | FR-089c |
| `PUT` | `/api/secrets/{name}` | `{ "value": "..." }` — 즉시 공개키로 암호화해 저장. 값은 응답에 없다 | FR-089b |
| `DELETE` | `/api/secrets/{name}` | 암호문 삭제 | — |

`GET /api/secrets` 응답:

```json
{ "public_key_fingerprint": "SHA256:a1b2c3...",
  "fingerprint_matches_key": true,
  "names": [ { "name": "LOGIN_PASSWORD", "present": true } ] }
```

`fingerprint_matches_key` 가 `false` 면 공개키가 교체된 상태다. 클라이언트는 재입력이 필요함을 알린다
(spec 엣지 케이스).

`PUT /api/secrets/{name}` 은 비밀키를 요구하지 않는다 (FR-089b) — 이것이 비대칭 방식을 택한 실질적 이득이다.

`DELETE /api/keys` 와 `POST /api/keys/regenerate` 응답:

```json
{ "status": { "private_key_present": false, "...": "..." },
  "purged_secret_count": 2,
  "project_open": true }
```

두 조작은 **되돌릴 수 없다.** 확인 문구 `DELETE` 가 정확히 오지 않으면 `400 DEFINITION_INVALID` 로
거절한다. 성공하면 열린 프로젝트의 암호문과 **기록된 공개키 지문까지** 비운다 — 지문을 남기면
새 키로도 값을 넣을 수 없는 상태가 된다. `project_open` 이 `false` 면 비울 대상을 몰라 키만 지웠다는 뜻이다.

### 암호구로 잠긴 비밀키 (FR-089e-3)

봉인은 공개키만으로 되지만 **재실행·AI 작성은 비밀키를 연다.** 암호구로 잠근 키는 요청 맥락에서
열 수 없으므로, 백엔드 프로세스의 환경 변수 `ITB_KEY_PASSPHRASE` 로 암호구를 공급한다. 공급하지
않으면 세션은 시작되지만 민감 변수를 실제로 요구하는 Step 이 **"잠겨 있다"** 는 사유와 함께 실패한다
(FR-089f). "키가 없다" 와 구분해서 보고한다 — 조치가 다르다.
