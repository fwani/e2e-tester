# REST 계약 — 엑셀로 프로젝트 내보내기·가져오기

**Feature**: `014-excel-project-io` | **Date**: 2026-09-10

이 문서는 이 기능이 더하는 엔드포인트만 다룬다. 기존 규약은 그대로 적용된다.

**모든 요청에 `X-ITB-Project-Root` 헤더가 붙는다** (파일 업로드 포함). 서버의 열린 프로젝트와
다르면 미들웨어가 409 `PROJECT_MISMATCH` 로 거절한다. 새 프로젝트를 만드는 경로
(`POST /api/import/create-project`)만 예외이며, 이는 `/api/project` 계열과 같은 취급이다.

**오류 본문은 기존 형태 그대로다**:

```json
{ "error": { "code": "IMPORT_FILE_REJECTED", "category": "blocked",
             "message": "...", "next_action": "...", "detail": {} } }
```

---

## 1. 내보내기

### `GET /api/project/export`

열린 프로젝트 전체를 워크북 하나로 만들어 돌려준다. 프로젝트의 어떤 파일도 바꾸지 않는다(FR-012).

**요청**: 본문 없음.

**응답 200** — 바이너리

```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="itb-export-20260910-141530.xlsx";
                     filename*=UTF-8''%ED%86%B5%ED%95%A9-20260910-141530.xlsx
X-ITB-Export-Warnings: 2
```

`X-ITB-Export-Warnings` 는 변환·잘림이 일어난 건수다. 0이면 헤더를 붙이지 않는다.
자세한 내용은 파일 자체가 아니라 아래 미리보기 엔드포인트에서 얻는다.

**응답 404** `PROJECT_NOT_OPEN` — 열린 프로젝트가 없다.
**응답 500** `EXPORT_FAILED` — 워크북을 만들지 못했다. 반쯤 만들어진 파일을 주지 않는다(FR-013).

읽을 수 없는 테스트 정의가 있어도 내보내기는 성공한다. 그 테스트는 빠지고 경고에 잡힌다 —
`GET /api/tests` 가 `problems` 로 같은 일을 하는 것과 같은 태도다.

### `GET /api/project/export/warnings`

내보내기에서 무엇이 바뀌었는지 미리 본다. 파일을 만들지 않는다.

**응답 200**

```json
{
  "sheet_renames": [
    { "group_name": "사용자/권한 관리", "sheet_name": "사용자_권한 관리", "reason": "forbidden_char" }
  ],
  "truncations": [
    { "test_id": "TC-042", "column": "수행 절차", "kept_lines": 210, "dropped_lines": 14 }
  ],
  "unreadable": ["TC-077"],
  "test_count": 128,
  "sheet_count": 5
}
```

---

## 2. 가져오기 — 미리보기

### `POST /api/import/preview`

`multipart/form-data`, 필드 `file`. 파일을 해석해 **계획**을 만들고 메모리에 30분 보관한다.
프로젝트에는 아무것도 만들지 않는다(FR-016).

열린 프로젝트가 있으면 그 프로젝트에 비추어 계획을 세운다(기존 그룹·수용량). 없으면
`create-project` 용 계획이 된다.

**응답 200**

```json
{
  "plan_id": "pl_7f3a2b91",
  "file_name": "통합테스트설계서.xlsx",
  "expires_at": "2026-09-10T09:42:00Z",
  "draft_count": 23,
  "group_count": 3,
  "sheets": [
    {
      "sheet_name": "그룹 없음",
      "prefix": "TC",
      "prefix_source": "ungrouped",
      "needs_prefix": false,
      "group_name": null,
      "existing_group_name": null,
      "name_differs": false,
      "row_count": 5,
      "renumbered": []
    },
    {
      "sheet_name": "회원",
      "prefix": "USER",
      "prefix_source": "from_rows",
      "needs_prefix": false,
      "group_name": "회원",
      "existing_group_name": "사용자관리",
      "name_differs": true,
      "row_count": 12,
      "renumbered": [{ "row": 7, "from": "USER-003", "to": "USER-014" }]
    },
    {
      "sheet_name": "데이터관리",
      "prefix": null,
      "prefix_source": null,
      "needs_prefix": true,
      "group_name": "데이터관리",
      "existing_group_name": null,
      "name_differs": false,
      "row_count": 6,
      "renumbered": []
    }
  ],
  "skipped": [
    { "sheet_name": "회원", "row": 9, "reason": "no_title" },
    { "sheet_name": "메모", "row": 1, "reason": "no_columns" }
  ],
  "capacity": { "needed": 23, "available": 976, "ok": true },
  "warnings": []
}
```

필드 뜻:

| 필드 | 뜻 |
|---|---|
| `needs_prefix` | `true` 면 확정 요청에서 이 시트의 접두어를 채워야 한다 (FR-022a) |
| `existing_group_name` · `name_differs` | 접두어가 같은 기존 그룹이 있고 이름이 다르다. **기존 이름을 유지한다** (FR-024a) |
| `renumbered` | 파일 안 TC ID 중복으로 번호가 바뀐 행 (FR-023a·b) |
| `skipped[].reason` | `no_title`(대상기능 빈 칸) · `no_columns`(필수 컬럼 없음) · `empty`(빈 행) |
| `capacity` | 만들 수 있는가. `ok:false` 여도 미리보기는 200 이다 — 확정에서 막는다 |

**응답 400** `IMPORT_FILE_REJECTED`

```json
{ "error": { "code": "IMPORT_FILE_REJECTED", "category": "blocked",
  "message": "시트가 상한(200개)을 넘습니다. 이 파일은 300개입니다.",
  "next_action": "더 작은 파일을 고르거나, 스프레드시트 형식(.xlsx)인지 확인한 뒤 다시 시도하세요.",
  "detail": { "limit": 200, "actual": 300, "kind": "sheet_count" } } }
```

`detail.kind` 는 `file_bytes` · `uncompressed_bytes` · `sheet_count` · `row_count` ·
`not_xlsx` · `corrupt` 중 하나다.

---

## 3. 가져오기 — 확정

### `POST /api/import/commit`

열려 있는 프로젝트로 가져온다. 전부 아니면 전무다(FR-025).

**요청**

```json
{
  "plan_id": "pl_7f3a2b91",
  "prefixes": { "데이터관리": "DATA" }
}
```

`prefixes` 는 `needs_prefix: true` 인 시트에 대한 답이다. 시트를 빼거나 빈 문자열을 주면
**그 시트를 건너뛴다** (FR-022b).

**응답 201**

```json
{
  "created_groups": [{ "prefix": "DATA", "name": "데이터관리" }],
  "reused_groups": [{ "prefix": "USER", "name": "사용자관리" }],
  "drafts": [
    { "draft_id": "D-0001", "name": "로그인", "group_prefix": "USER",
      "desired_test_id": "USER-003" }
  ],
  "skipped": [{ "sheet_name": "회원", "row": 9, "reason": "no_title" }],
  "skipped_sheets": [{ "sheet_name": "메모", "reason": "no_prefix" }],
  "renumbered": [{ "row": 7, "from": "USER-003", "to": "USER-014" }]
}
```

**응답 400**

| 코드 | 언제 |
|---|---|
| `IMPORT_PLAN_NOT_FOUND` | 계획이 만료됐거나 없다 |
| `IMPORT_CAPACITY_EXCEEDED` | `detail: {needed, available}` (FR-036b) |
| `DEFINITION_INVALID` | 사용자가 준 접두어가 형식에 안 맞거나 `TC` 예약어다 |
| `GROUP_PREFIX_RESERVED` | 접두어로 `TC` 를 줬다 |

**응답 500**

| 코드 | 뜻 |
|---|---|
| `IMPORT_FAILED` | 도중 실패했고 **전부 되돌렸다**. 프로젝트는 이전과 같다 |
| `IMPORT_PARTIAL` | 되돌리지 못했다. `detail.stranded: [{target, where}]` |

### `POST /api/import/create-project`

파일에서 **새 프로젝트를 만들며** 가져온다 (FR-014a·b·c).

**요청**

```json
{
  "plan_id": "pl_7f3a2b91",
  "name": "통합테스트",
  "default_start_url": "https://example.internal",
  "test_id_attribute": "data-testid",
  "prefixes": { "데이터관리": "DATA" }
}
```

`name` 의 기본값은 파일 이름에서 확장자를 뗀 것이며, 프론트가 미리 채워 보여 준다(FR-014b).

**응답 201**: `POST /api/import/commit` 의 응답에 `project` (`ProjectView`) 를 더한 것.
성공하면 그 프로젝트가 열린 상태가 된다 — `POST /api/project/create` 와 같은 부수 효과다.

**응답 400/409**: `PROJECT_ALREADY_EXISTS`, `INVALID_PATH` 등 기존 프로젝트 만들기 오류가 그대로 온다.

**실패 시**: 만들다 만 프로젝트를 남기지 않는다. 프로젝트 디렉터리를 휴지통으로 옮기고
레지스트리에서 지운다.

---

## 4. 초안

### `GET /api/drafts`

**응답 200**

```json
{
  "drafts": [
    {
      "draft_id": "D-0001",
      "name": "로그인",
      "description": "올바른 자격 증명으로 로그인되는지 확인한다",
      "actor": "관리자",
      "group_prefix": "USER",
      "desired_test_id": "USER-003",
      "desired_id_available": true,
      "source": { "file_name": "통합테스트설계서.xlsx", "sheet_name": "회원", "row": 4 },
      "created_at": "2026-09-10T09:12:00Z"
    }
  ],
  "count": 23
}
```

`desired_id_available` 은 지금 그 번호가 비어 있는지다. `false` 여도 막지 않는다 —
저장할 때 다른 번호를 받는다는 예고일 뿐이다(FR-032).

### `GET /api/drafts/{draft_id}`

**응답 200**: 위 항목에 `procedure`, `expectation`, `suggested_instruction` 을 더한 것.

`suggested_instruction` 은 서버가 초안에서 지은 AI 지시문이다. 프론트는 이것을 지시문 칸에
채워 보여 주고, 사용자가 고칠 수 있다(FR-031).

**응답 404** `DRAFT_NOT_FOUND`

### `DELETE /api/drafts/{draft_id}`

**응답 204**. 그 초안만 사라진다(FR-029).
**응답 404** `DRAFT_NOT_FOUND`

---

## 5. 기존 엔드포인트의 변경

### `POST /api/sessions` — `draft_id` 추가

```python
class CreateSessionRequest(BaseModel):
    mode: Literal["record", "replay", "ai"]
    ...
    draft_id: str | None = Field(default=None, pattern=DRAFT_ID_PATTERN)   # 신규
```

- `mode == "ai"` 일 때만 허용한다. 다른 모드와 함께 오면 400 `DEFINITION_INVALID`.
- `ai_instruction` 을 함께 주면 **그것이 쓰인다** (사용자가 고친 것). 없으면 서버가
  초안에서 짓는다.
- 없는 초안이면 404 `DRAFT_NOT_FOUND`.
- 세션은 `draft_id` 를 저장까지 들고 간다.

**새 상태나 새 전이를 만들지 않는다.** 기존 AI 작성 경로 그대로다 (원칙 I·III).

### `POST /api/sessions/{id}/save` — 초안에서 온 세션의 저장

요청 형태는 그대로다. 동작만 달라진다.

1. 세션에 `draft_id` 가 있고 그 초안의 `desired_test_id` 가 비어 있으면 **그 번호를 부여한다**
2. 이미 쓰이고 있으면 `allocate_test_id` 로 빈 번호를 받는다
3. 저장이 성공하면 초안 파일을 지운다(FR-033)

**응답 200** — 기존 `Test` 에 필드 두 개를 더한다:

```json
{ "...": "기존 Test 필드",
  "from_draft": "D-0001",
  "desired_id_taken": { "wanted": "USER-003", "assigned": "USER-014" } }
```

`desired_id_taken` 은 희망 번호를 주지 못했을 때만 실린다 — 그때 사용자에게 알려야 한다(FR-032).

### `GET /api/tests` — 초안 수를 함께 알린다

`TestListResponse` 에 한 필드를 더한다.

```python
    draft_count: int = 0
    """녹화되지 않은 초안 수. 목록 화면이 "N건 남음" 을 보이는 데 쓴다 (FR-035)."""
```

초안 자체는 `tests` 에 섞지 않는다(FR-027). 목록 화면이 별도 영역에 보인다.

---

## 6. 상한 요약

| 대상 | 값 | 출처 |
|---|---|---|
| 업로드 파일 크기 | 100MB | `portability/limits.py` (이 기능 고유) |
| 압축 해제 총량 | 500MB · 압축비 100:1 | `portability/limits.py` |
| 시트 수 | 200 | `portability/limits.py` |
| 전체 데이터 행 | 5,000 | `portability/limits.py` |
| 프로젝트 테스트 수 | 999 | `domain/test_case.MAX_TEST_NUMBER` (**공유**) |
| 초안 수 | 9,999 | `domain/draft.MAX_DRAFT_NUMBER` |
| 그룹 접두어 | `^[A-Z][A-Z0-9]{0,7}$`, `TC` 예약 | `domain/test_case` (**공유**) |
| 셀 한 칸 | 32,767자 | 엑셀 형식 자체의 상한 |

행 5,000 과 테스트 999 가 어긋나 보이는 것은 의도적이다 — 파일을 **읽는** 상한과 프로젝트가
**수용하는** 양은 다른 것이고, 후자는 확정 직전에 따로 검사한다(FR-036a·b).
