# REST API 변경분 — 002 결함 수정 라운드

**기준 계약**: `specs/001-interactive-ai-test-builder/contracts/rest-api.md`

이 문서는 **변경분만** 적는다. 여기 없는 엔드포인트는 001 계약 그대로다.

오류 응답 형태는 001 계약과 같다.

```json
{ "error": { "code": "<ErrorCode>", "message": "<사람이 읽을 수 있는 문장>", "detail": {} } }
```

---

## 0. 전역 — 422 를 계약 형태로 (DR-022·DR-030)

**현재 결함**: `RequestValidationError` 핸들러가 없어 FastAPI 기본 본문
`{"detail":[...]}` 이 그대로 나간다. 프런트엔드는 `body.error.message` 를 찾지 못해
`요청이 실패했습니다 (422).` 로 폴백한다 (research R3).

**변경**: `RequestValidationError` 핸들러를 등록한다.

| 항목 | 값 |
|---|---|
| HTTP 상태 | `422` (유지) |
| `error.code` | `DEFINITION_INVALID` — 기존 코드를 재사용한다 |
| `error.message` | 어느 필드가 왜 거절됐는지 한국어 한 문장 |
| `error.detail` | `{"fields": [{"loc": "passphrase", "reason": "..."}]}` |

**새 `ErrorCode` 를 만들지 않는 이유**: 의미가 이미 "요청이 규격에 맞지 않음"으로 같다.
새로 만들면 프런트엔드 `ErrorCode` 유니온(`frontend/src/api/client.ts:12-34`)과 계약
문서를 함께 늘려야 하는데 얻는 것이 없다.

**효과 범위**: 이 하나로 앱의 모든 엔드포인트에서 나는 검증 오류가 읽을 수 있게 된다.
키 쌍 화면만의 수정이 아니다.

---

## 1. 프로젝트 목록 — `GET /api/project/list` (신규, DR-002·DR-003·DR-004·DR-007)

첫 화면이 그릴 프로젝트 목록.

**응답 200**

```json
{
  "projects": [
    {
      "root": "/Users/me/.local/share/itb/projects/data-platform",
      "name": "데이터 플랫폼",
      "last_opened_at": "2026-09-04T02:11:00Z",
      "origin": "managed",
      "accessible": true,
      "unavailable_reason": null
    }
  ]
}
```

| 규칙 | 근거 |
|---|---|
| 관리 위치 스캔 ∪ 레지스트리, `root` 로 중복 제거 | DR-002 + DR-007 |
| `last_opened_at` 내림차순 | DR-004 |
| 프로젝트가 하나도 없으면 `{"projects": []}` 와 **200** | 빈 목록은 오류가 아니다 |
| `accessible` 은 조회 시점에 계산 | 파일 시스템은 도구 밖에서 바뀐다 |
| 레지스트리 파일이 깨졌으면 빈 목록 + 경고, 덮어쓰지 않음 | 사용자 기록을 조용히 잃지 않는다 |

---

## 2. 프로젝트 생성 — `POST /api/project/create` (변경, DR-001·DR-006)

**변경**: 요청에서 `path` 를 **제거한다.** 사용자가 위치를 지정하지 않는다.

**요청**

```json
{
  "name": "데이터 플랫폼",
  "default_start_url": "https://example.internal/login",
  "test_id_attribute": "data-testid"
}
```

| 필드 | 규칙 | 변화 |
|---|---|---|
| ~~`path`~~ | — | **제거** (DR-001) |
| `name` | 1–100자, 필수 | 유지 |
| `default_start_url` | `^https?://`, ≤2000자 | 유지 |
| `test_id_attribute` | 기본 `data-testid` | 유지 |

**응답 201** — 001 의 `ProjectView` 에 `root` 가 이미 있다. 만들어진 위치가 그대로
사용자에게 표시된다 (DR-006).

**서버 동작**

1. `name` 을 슬러그로 바꿔 `~/.local/share/itb/projects/<슬러그>/` 를 정한다.
2. 이미 있으면 `-2`, `-3` 을 붙여 충돌을 피한다. `PROJECT_ALREADY_EXISTS` 를 내지 않는다
   — 사용자가 위치를 모르는데 위치 충돌로 실패시킬 수 없다.
3. 생성 후 레지스트리에 `origin: "managed"` 로 등록한다.

**슬러그 규칙**: 경로 구분자·`..`·제어 문자를 제거하고 공백을 `-` 로 바꾼다. 결과가
비면 `project` 를 쓴다. 이름이 경로가 되는 지점이므로 경계 검증이 필요하다
(헌법 보안 요구).

---

## 3. 프로젝트 열기 — `POST /api/project/open` (변경, DR-005·DR-008)

**요청** (형태 유지)

```json
{ "path": "/Users/me/work/some-project" }
```

**변경**: `path` 에 경계 검증을 적용한다.

| 규칙 | 위반 시 |
|---|---|
| `resolve()` 후 사용자 홈 하위여야 한다 | `400 INVALID_PATH` |
| 유효한 프로젝트 구조여야 한다 | `404 PROJECT_NOT_FOUND` — **무엇이 없어서인지** 메시지에 적는다 (DR-008) |
| 읽기 권한이 있어야 한다 | `400 INVALID_PATH` — 권한 문제임을 밝힌다 |

**성공 시** 레지스트리에 `origin: "external"` 로 등록하고 `last_opened_at` 을 갱신한다
(DR-007).

---

## 4. 디렉터리 탐색 — `GET /api/fs/browse` (신규, DR-005)

브라우저가 절대 경로를 줄 수 없으므로 서버가 목록을 그린다 (research R4).

**요청**: `?path=<절대 경로>` — 생략하면 사용자 홈

**응답 200**

```json
{
  "path": "/Users/me/work",
  "parent": "/Users/me",
  "entries": [
    { "name": "some-project", "path": "/Users/me/work/some-project", "is_project": true }
  ]
}
```

| 규칙 | 막는 것 |
|---|---|
| `resolve()` 후 홈 하위가 아니면 `400 INVALID_PATH` | `..` 탈출 |
| 심볼릭 링크는 따라간 뒤 다시 검사 | 링크를 통한 이탈 |
| **디렉터리만 반환. 파일 이름도 주지 않는다** | 탐색기가 파일 유출 통로가 되는 것 |
| 숨김 디렉터리 제외 | `.ssh` 노출, 목록 소음 |
| 읽기 권한 없으면 `400 INVALID_PATH` + 사유 | 조용한 빈 목록 |
| 홈 최상위에서 `parent` 는 `null` | 경계 밖으로 올라가는 조작 |

`is_project` 는 사용자가 어디를 골라야 하는지 알려 주기 위한 것이다.

---

## 5. 프로젝트 목록에서 제거 — `DELETE /api/project/registry` (신규, DR-009)

**요청**: `{ "root": "<절대 경로>" }`

**응답 204**

**레지스트리 항목만 지운다. 디스크의 프로젝트는 지우지 않는다.** 목록 정리와 자산
삭제는 다른 조작이고, 되돌릴 수 없는 쪽을 조용히 하지 않는다.

관리 위치 스캔에 여전히 걸리는 프로젝트는 제거 후에도 목록에 남는다. 이는 정상이다 —
`GET /api/project/list` 가 스캔 ∪ 레지스트리이기 때문이다.

---

## 6. 세션 중지 — `POST /api/sessions/{id}/stop` (변경, DR-010·DR-013·DR-015)

**현재 결함**: `state.sessions.close()` + `_WORK.pop()` 으로 세션을 파괴해
이후 `save` 가 `SESSION_NOT_FOUND` 를 낸다 (research R1).

**변경**: 브라우저 자원만 해제하고 **`SessionWork` 는 남긴다.**

**응답 200** — `SessionView`, `state: "review"`

| 이 명령이 하는 것 | 이 명령이 더 이상 하지 않는 것 |
|---|---|
| 리코더·에이전트·미러·러너·인라인 정리 | ~~`state.sessions.close()`~~ |
| 브라우저 세션 종료 | ~~`_WORK.pop()`~~ |
| 상태를 `review` 로 | ~~`broker.drop()`~~ (이벤트 채널은 저장까지 열어 둔다) |

**`review` 상태에서 받는 명령**

| 명령 | 허용 | 근거 |
|---|---|---|
| `GET /api/sessions/{id}` | ✅ | DR-010 — Step 목록을 봐야 한다 |
| `PATCH`/`DELETE` 스텝, 순서 변경 | ✅ | DR-012 |
| `POST /api/sessions/{id}/save` | ✅ | DR-013 |
| `POST /api/sessions/{id}/discard` | ✅ | DR-014 (신규, 아래) |
| 실행·이어서·다시 집기·탭 전환 | ❌ `409 INVALID_TRANSITION` | 브라우저가 없다. 001 FR-043a |

**`review` 는 종료 상태가 아니다.** 001 의 `stopped` 와 다르다 — `stopped` 는 아무
명령도 받지 않는다.

---

## 7. 세션 버리기 — `POST /api/sessions/{id}/discard` (신규, DR-014)

`review` 상태의 초안을 저장하지 않고 버린다. 여기서 비로소 `SessionWork` 가 파괴된다.

**응답 204**

**확인 대화상자는 화면이 띄운다.** 서버는 이 명령을 받으면 곧바로 버린다 — 확인은
사용자 인터페이스의 책임이고, 서버가 두 번 묻는 구조를 만들면 어느 쪽이 진짜 확인인지
모호해진다. 화면은 기존 `has_unsaved_changes` 로 경고 여부를 판단한다.

---

## 8. 언어모델 사용 가능 여부 — `GET /api/ai/availability` (신규, DR-021)

AI 작성을 시작하기 **전에** 알려 주기 위한 읽기 전용 점검.

**응답 200**

```json
{ "available": false, "reason": "언어모델 자격 증명을 찾을 수 없습니다. `ANTHROPIC_API_KEY` 를 …" }
```

| 규칙 | 근거 |
|---|---|
| 자격 증명의 어떤 조각도 반환하지 않는다 | 헌법 보안 요구 |
| 언어모델을 **호출하지 않는다.** 해석 가능 여부만 본다 | 비용·지연 |
| 실패해도 200. `available: false` 로 답한다 | 점검 자체의 실패를 오류로 만들면 화면이 또 조용해진다 |

**원칙 II 확인**: 이 엔드포인트는 작성 경로 전용이다. 재실행 경로는 호출하지 않는다.
`itb.execution` 은 이 코드에 의존하지 않는다 (`.importlinter` 계약 유지).

---

## 9. 비밀 값 — 변경 없음 (DR-023~DR-027)

**새 엔드포인트를 만들지 않는다.** 인라인 입력은 기존 두 엔드포인트로 성립한다.

| 엔드포인트 | 역할 |
|---|---|
| `GET /api/secrets` | 변수 **이름과 존재 여부만**. 값은 어떤 경우에도 주지 않는다 |
| `PUT /api/secrets/{name}` | 공개키로 봉인. **비밀키가 필요 없다** — 인라인 입력이 가능한 이유 |

DR-025(공개키가 없을 때 그 자리에서 만들기)는 기존 `POST /api/keys/generate` 를 호출한다.
그래서 **DR-028 은 DR-025 의 선행 조건이다** — 키 생성이 고쳐지지 않으면 인라인 입력의
탈출구가 막힌다.

---

## 10. 키 쌍 생성 — `POST /api/keys/generate` (변경, DR-028~DR-031)

**요청 형태는 바뀌지 않는다.** `{ "passphrase": string | null }`

`passphrase` 제약은 `min_length=8, max_length=200` 그대로 둔다 — 8자 미만 암호구절을
받아들이는 것은 개선이 아니다. **바뀌는 것은 실패를 알리는 방식이다.**

| 상황 | 현재 | 변경 후 |
|---|---|---|
| 8자 미만 암호구절 | 422 + `요청이 실패했습니다 (422).` | 화면이 **제출 전에** 막고 제약을 안내 (DR-029). 그래도 도달하면 §0 핸들러가 읽을 수 있는 문장으로 (DR-030) |
| 이미 키가 있음 | `409 KEY_ALREADY_EXISTS` (이미 정상) | 유지 |
| 쓰기 권한 없음 | 500 | `400` + 권한 문제임을 밝히는 문장 (DR-030) |

**서버 계약이 거의 그대로인 것이 결론이다.** 이 결함은 대부분 §0(전역 422 핸들러)과
화면 쪽 안내로 해결된다.

---

## 변경 요약

| 엔드포인트 | 종류 | 요구사항 |
|---|---|---|
| (전역) `RequestValidationError` 핸들러 | 신규 | DR-022·DR-030 |
| `GET /api/project/list` | 신규 | DR-002·003·004·007 |
| `POST /api/project/create` | 변경 (`path` 제거) | DR-001·006 |
| `POST /api/project/open` | 변경 (경계 검증) | DR-005·008 |
| `GET /api/fs/browse` | 신규 | DR-005 |
| `DELETE /api/project/registry` | 신규 | DR-009 |
| `POST /api/sessions/{id}/stop` | 변경 (파괴하지 않음) | DR-010·013·015 |
| `POST /api/sessions/{id}/discard` | 신규 | DR-014 |
| `GET /api/ai/availability` | 신규 | DR-021 |
| `POST /api/keys/generate` | 변경 (오류 표현만) | DR-028~031 |
| `GET`/`PUT /api/secrets/*` | **변경 없음** | DR-023~027 |
