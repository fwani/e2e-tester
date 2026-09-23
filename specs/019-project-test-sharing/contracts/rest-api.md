# Phase 1 Contract: REST API — 공유용 내보내기·가져오기

**Feature**: `019-project-test-sharing` | **Date**: 2026-09-23

신규 라우터 `itb.api.routes.sharing`, 접두사 `/api/share`. 기존 오류 형식
(`ErrorResponse` / `ErrorBody`)을 그대로 쓴다.

**`/api/project` 아래에 두지 않는다.** 프로젝트 대조 가드(`app.py` 의 `_project_guard`)가
`/api/project` 로 시작하는 경로를 제외하므로, 그 아래에 두면 화면이 A 를 보는데 서버가 연 B 를
조용히 내보내게 된다 (014 가 같은 이유로 `/api/export` 를 쓴다). 새 프로젝트로 가져오는 경로는
열린 프로젝트가 없어도 동작해야 하며, 클라이언트가 헤더를 보내지 않으면 가드는 걸리지 않는다.

---

## 1. `GET /api/share/export/preview`

내보내면 **무엇이 나가는지** 보여 준다. 파일을 만들지 않고, 프로젝트도 바꾸지 않는다 (FR-006·FR-008).

**Query**

| 이름 | 형 | 기본 | 설명 |
|---|---|---|---|
| `test_ids` | str | 없음 | 쉼표로 구분한 식별자. 없으면 프로젝트 전체 (FR-001·FR-002). |

**200 응답**

```json
{
  "test_count": 3,
  "group_count": 1,
  "project_name": "dev-graphio",
  "start_urls": [
    { "scope": "project", "test_id": null, "url": "https://example.internal" },
    { "scope": "test", "test_id": "TC-002", "url": "https://example.internal/admin" }
  ],
  "plaintext_values": [
    { "test_id": "TC-001", "step_id": "step-01", "step_label": "아이디 입력",
      "field": "value", "value": "platform1", "truncated": false }
  ],
  "required_secrets": [
    { "name": "SECRET_INPUT_LOGIN_PW",
      "usages": [{ "test_id": "TC-001", "step_id": "step-02",
                   "step_label": "비밀번호 입력", "field": "value" }] }
  ],
  "unreadable": ["TC-004"]
}
```

- `plaintext_values` 는 **가리지 않는다.** 이 화면의 목적이 값을 보여 주는 것이다 (research R11).
  120자를 넘으면 자르고 `truncated: true`.
- `{{VAR}}` 참조는 값이 아니므로 `plaintext_values` 에 넣지 않는다.
- `unreadable` 은 정의를 읽을 수 없어 빠지는 테스트다. 내보내기를 막지 않는다.

**오류**: `PROJECT_NOT_OPEN`(404), `SHARE_EXPORT_EMPTY`(400 — 내보낼 것이 하나도 없을 때).

---

## 2. `POST /api/share/export`

묶음 파일을 만들어 내려보낸다 (FR-001·FR-002·FR-010).

**Request**

```json
{ "test_ids": ["TC-001", "TC-002"] }
```

`test_ids` 가 `null` 이거나 없으면 프로젝트 전체. 선택을 본문으로 받기 위해 `POST` 다 —
`GET` 이면 식별자가 URL 길이 상한에 걸린다.

**200 응답**: 본문이 YAML 바이트.

| 헤더 | 값 |
|---|---|
| `Content-Type` | `application/yaml; charset=utf-8` |
| `Content-Disposition` | `attachment; filename="<ascii>.itbshare.yaml"; filename*=UTF-8''<percent-encoded>` |
| `X-ITB-Share-Test-Count` | 담긴 테스트 수 |
| `X-ITB-Share-Unreadable` | 빠진 테스트 수 (0이면 보내지 않는다) |

파일명은 `<프로젝트 slug>-<YYYYMMDD-HHMMSS>.itbshare.yaml`. 한글 프로젝트 이름을 위해 ASCII
대체 이름과 RFC 5987 이름을 함께 싣는다 — 014 의 `_content_disposition` 과 같은 수법이며 그
함수를 공유 모듈로 옮겨 **한 곳에서** 만든다.

**보증**: 응답 본문에 민감 값의 평문도 암호문도 없다. 묶음은 메모리에서 완성된 뒤에야 응답
본문이 되므로, 실패는 언제나 "파일이 없다" 이지 "파일이 이상하다" 가 아니다 (FR-024 와 같은 성질).

**오류**: `PROJECT_NOT_OPEN`(404), `SHARE_EXPORT_EMPTY`(400).

---

## 3. `POST /api/share/import/plan`

묶음 파일을 올려 **계획**을 만든다. 디스크에 아무것도 쓰지 않는다 (FR-022·FR-023).

**Request**: `multipart/form-data`

| 필드 | 형 | 설명 |
|---|---|---|
| `file` | file | 묶음 파일. `MAX_BUNDLE_BYTES` 초과면 읽지 않고 거부. |
| `target` | str | `new` \| `current`. 기본 `new`. |

**201 응답**

```json
{
  "plan_id": "a1b2c3...",
  "file_name": "dev-graphio-20260923-041200.itbshare.yaml",
  "expires_at": "2026-09-23T04:42:00Z",
  "target": "new",
  "target_project_name": "dev-graphio (2)",
  "project_renamed_from": "dev-graphio",
  "generator": "itb 0.19.0",
  "created_at": "2026-09-23T04:12:00Z",
  "groups": [
    { "source_prefix": "USER", "source_name": "사용자관리",
      "target_prefix": "USER", "target_name": "사용자관리",
      "action": "create", "reason": null }
  ],
  "tests": [
    { "source_id": "TC-001", "target_id": "TC-001", "name": "운영 관리 메뉴 진입",
      "renumbered": false, "group_prefix": "TC", "status": "create", "reason": null }
  ],
  "capacity": [{ "prefix": "TC", "needed": 3, "available": 996, "ok": true }],
  "required_secrets": [
    { "name": "SECRET_INPUT_LOGIN_PW",
      "usages": [{ "test_id": "TC-001", "step_id": "step-02",
                   "step_label": "비밀번호 입력", "field": "value" }],
      "already_stored": false,
      "env_provided": false }
  ],
  "notices": [
    { "code": "START_URL_CHECK", "message": "시작 URL 이 https://example.internal 입니다. 이 환경에 접근할 수 있는지 확인하세요.", "detail": null },
    { "code": "REIMPORT", "message": "같은 묶음을 이미 가져온 적이 있습니다.", "detail": {"matched_tests": 3} }
  ],
  "blocking": []
}
```

- `required_secrets[].usages[].test_id` 는 **`target_id` 기준**이다. 재부여된 번호로 보여 줘야
  사용자가 찾을 수 있다.
- `blocking` 이 비어 있지 않으면 확정할 수 없다. 화면은 확정 버튼을 잠근다.
- `REIMPORT` 판정은 대상 프로젝트에 `imported_from.source_file` 이 같은 테스트가 있는지로 본다.

**오류**: `SHARE_BUNDLE_TOO_LARGE`(413), `SHARE_BUNDLE_MALFORMED`(400),
`SHARE_BUNDLE_UNSUPPORTED_VERSION`(400), `SHARE_BUNDLE_INVALID_TEST`(400 — 어느 테스트의
무엇이 문제인지 `detail` 에 전부), `PROJECT_NOT_OPEN`(404, `target=current` 일 때만).

---

## 4. `GET /api/share/import/plan/{plan_id}`

만료 전 계획을 다시 본다. 화면 새로 고침에 쓴다.

**200**: 3번과 같은 본문. **404**: `SHARE_PLAN_NOT_FOUND`.

---

## 5. `POST /api/share/import/commit`

계획을 확정한다. **전부 성공하거나 아무것도 만들지 않는다** (FR-024).

**Request**

```json
{
  "plan_id": "a1b2c3...",
  "project_name": "dev-graphio (2)",
  "default_start_url": "https://staging.example.internal"
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `plan_id` | ✓ | |
| `project_name` | `target=new` 일 때만 | 비면 계획의 `target_project_name`. 다시 충돌하면 서버가 또 비껴 만들고 결과에 알린다. |
| `default_start_url` | 선택 | 받는 쪽 환경이 다를 때 여기서 바꾼다 (Edge Case). 없으면 묶음의 값. |

**확정은 계획을 다시 세운다.** 서버가 들고 있는 묶음으로 현재 대상 프로젝트를 다시 보고,
결과가 예고와 달라졌으면 `SHARE_PLAN_STALE`(409) 과 함께 **새 계획**을 돌려준다. 사용자가
미리보기를 본 뒤 다른 창에서 테스트를 만들었을 수 있다.

**201 응답**

```json
{
  "project_root": "/Users/x/.local/share/itb/projects/dev-graphio-2",
  "project_name": "dev-graphio (2)",
  "project_renamed_from": "dev-graphio",
  "created_tests": [
    { "target_id": "TC-007", "source_id": "TC-001", "name": "운영 관리 메뉴 진입", "group_prefix": "TC" }
  ],
  "renumbered": [{ "from": "TC-001", "to": "TC-007" }],
  "created_groups": [{ "prefix": "USER", "name": "사용자관리" }],
  "skipped": [{ "source_id": "TC-004", "reason": "그룹 USER 의 번호가 모두 찼습니다." }],
  "required_secrets": [ /* 3번과 같은 모양, already_stored 갱신됨 */ ],
  "notices": [ /* 3번과 같은 모양 */ ]
}
```

**오류**: `SHARE_PLAN_NOT_FOUND`(404), `SHARE_PLAN_STALE`(409, 본문에 새 계획),
`SHARE_IMPORT_BLOCKED`(409), `SHARE_IMPORT_FAILED`(500), `SHARE_IMPORT_PARTIAL`(500).

**`target=new` 일 때 부수 효과**: 새 프로젝트가 만들어지고 레지스트리에 등록되며, 서버가 그
프로젝트를 연다 — `POST /api/project/create` 와 같은 동작이다. 화면은 응답의 `project_root` 로
자기 상태를 맞춘다.

---

## 6. `GET /api/tests/{test_id}/readiness`

실행할 수 있는 상태인가 (FR-044). 기존 `tests` 라우터에 더한다.

**200 응답**

```json
{
  "runnable": false,
  "missing_secrets": ["SECRET_INPUT_LOGIN_PW"],
  "undefined_variables": [],
  "key_available": true
}
```

- `missing_secrets` — 민감 변수인데 `secrets.local.yaml` 에 암호문이 없고 동일 이름 환경
  변수도 없는 것. **복호화하지 않고 존재만 본다** (research R10).
- `undefined_variables` — 기존 `undefined_variable_references` 의 결과 (비민감·빈 값).
  실행을 막지는 않는다.
- `key_available` — 이 설치에 키가 있는가 (FR-045).
- `runnable` 은 `missing_secrets` 가 비었는지로 정한다.

---

## 7. `POST /api/sessions` 변경 — 실행 전 차단

기존 엔드포인트에 **선행 검사**를 더한다. 저장된 테스트를 재생하려는 요청에서
`missing_secrets` 가 비어 있지 않으면 세션을 만들지 않고 거절한다.

**409 응답**

```json
{
  "error": {
    "code": "SECRET_VALUE_MISSING",
    "message": "값이 필요한 민감 변수가 있습니다. 값을 채운 뒤 실행하세요.",
    "detail": { "missing": ["SECRET_INPUT_LOGIN_PW"], "test_id": "TC-007" }
  }
}
```

**브라우저를 띄우기 전에 막는다.** 지금은 그 스텝에 도달해서야 실패하므로 받은 사람이 자기
환경 문제인지 테스트 문제인지 구분할 수 없다.

**AI 작성·녹화 세션에는 걸지 않는다.** 그 경로는 값을 **만드는** 중이므로 없는 것이 정상이다.

---

## 8. 민감 값 입력 — 기존 엔드포인트를 쓴다

새로 만들지 않는다.

| 하는 일 | 엔드포인트 |
|---|---|
| 이 프로젝트에 값이 있는 이름 목록 | `GET /api/secrets` |
| 값 채우기 (봉인) | `PUT /api/secrets/{name}` |
| 값 지우기 | `DELETE /api/secrets/{name}` |
| 키 상태·생성·잠금 해제 | `GET /api/keys/status`, `POST /api/keys/generate`, `POST /api/keys/unlock` |

**봉인 경로가 하나여야 한다.** 두 벌이 되면 마스킹·오류 처리가 갈리고, 한쪽에서 평문이 샌다
(research R13).

---

## 9. 계약 테스트에서 확인할 것

| # | 확인 |
|---|---|
| C1 | `POST /api/share/export` 응답 바이트에 `secrets.local.yaml` 의 어떤 암호문도, 알려진 평문 비밀값도 나타나지 않는다 (SC-004). |
| C2 | 내보낸 묶음을 그대로 `import/plan` 에 넣으면 계획이 서고, 확정하면 테스트 수가 같다 (SC-003 왕복). |
| C3 | 1바이트 손상시킨 묶음은 `SHARE_BUNDLE_MALFORMED` 로 거부되고, 그 뒤 대상 프로젝트의 파일 수가 그대로다. |
| C4 | `bundle_version: 99` 는 `SHARE_BUNDLE_UNSUPPORTED_VERSION` 으로 거부되고 부분 복원을 시도하지 않는다. |
| C5 | YAML 별칭이 든 묶음은 `SHARE_BUNDLE_MALFORMED` 로 거부된다 (파싱 전개 없이). |
| C6 | `TC-001` 이 있는 프로젝트에 `TC-001` 을 가져오면 둘 다 남고 `renumbered` 에 보고된다. |
| C7 | 확정 중 쓰기가 실패하면 만들어진 파일이 하나도 남지 않는다. |
| C8 | 민감 값이 빈 테스트로 `POST /api/sessions` 를 하면 409 `SECRET_VALUE_MISSING` 이고 세션이 만들어지지 않는다. |
| C9 | 같은 이름 환경 변수가 있으면 `missing_secrets` 에 들어가지 않는다. |
| C10 | `/api/share/*` 가 `X-ITB-Project-Root` 가 어긋난 요청에서 `PROJECT_MISMATCH` 로 거절된다. |
