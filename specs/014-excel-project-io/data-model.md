# Phase 1 Data Model — 엑셀로 프로젝트 내보내기·가져오기

**Feature**: `014-excel-project-io` | **Date**: 2026-09-10

---

## 1. 무엇이 새로 생기고 무엇이 바뀌는가

| 대상 | 상태 | 저장 위치 |
|---|---|---|
| `Draft` | **신규** 도메인 모델 | `<프로젝트>/drafts/D-####-<slug>.yaml` |
| `Test.description`, `Test.actor` | **기존 모델에 필드 추가** | 기존 `tests/*.yaml` 그대로 |
| `MAX_TEST_NUMBER` | **기존 매직 넘버를 상수로** | `domain/test_case.py` |
| `ImportPlan` 계열 | **신규**, 디스크에 쓰지 않음 | 서버 메모리 (30분) |
| 워크북 행/시트 | **신규**, 파생 산출물 | 사용자가 받는 `.xlsx` |
| 새 오류 코드 7개 | **기존 열거형에 추가** | `domain/error.py` |

---

## 2. `Draft` — 아직 녹화되지 않은 테스트의 의도

`itb/domain/draft.py` (신규). `itb.domain` 은 순수해야 하므로 pydantic 외에는 아무것도 쓰지 않는다.

```python
DRAFT_ID_PATTERN = r"^D-\d{4}$"
MAX_DRAFT_NUMBER = 9999

class Draft(BaseModel):
    """스프레드시트 행 하나에서 온, 아직 스텝이 없는 테스트의 의도.

    **이것은 Test 가 아니다.** 실행할 수 없고, 내보내기에 실리지 않으며,
    녹화가 저장되는 순간 사라진다. 원칙 I 이 요구하는 "테스트의 표현은 하나"를
    지키기 위해, 초안은 테스트와 같은 모양을 갖지 않는다 — steps 필드가 아예 없다.
    """
    model_config = ConfigDict(extra="forbid",
                              json_schema_serialization_defaults_required=True)

    draft_id: str = Field(pattern=DRAFT_ID_PATTERN)
    name: str = Field(min_length=1, max_length=200)          # 대상기능(제목)
    description: str | None = Field(default=None, max_length=2000)   # 테스트항목
    actor: str | None = Field(default=None, max_length=100)          # 수행자
    procedure: str | None = Field(default=None, max_length=2000)     # 수행 절차
    expectation: str | None = Field(default=None, max_length=2000)   # 기대 결과

    desired_test_id: str | None = Field(default=None, pattern=TEST_ID_PATTERN)
    group_prefix: str = Field(default=RESERVED_PREFIX, pattern=GROUP_PREFIX_PATTERN)

    source: DraftSource
    created_at: datetime
```

```python
class DraftSource(BaseModel):
    """어느 파일의 어느 시트 몇 행에서 왔는가. 사용자가 원본을 되짚을 수 있어야 한다."""
    model_config = ConfigDict(extra="forbid")
    file_name: str = Field(min_length=1, max_length=200)
    sheet_name: str = Field(min_length=1, max_length=31)
    row: int = Field(ge=2)          # 1행은 머리글이므로 데이터는 2행부터
```

### 검증 규칙

| 규칙 | 근거 |
|---|---|
| `name` 은 비어 있을 수 없다 | FR-018 — 제목 없는 행은 애초에 초안이 되지 않는다 |
| `desired_test_id` 의 접두어는 `group_prefix` 와 같아야 한다 | 접두어가 곧 소속이라는 013 의 결정과 어긋나지 않게 |
| `group_prefix` 가 `TC` 면 그룹 없는 초안이다 | 기존 예약 접두어 규약 그대로 |
| 지시문 길이 검사 | `name`+`description`+`actor`+`procedure`+`expectation` 을 조립한 결과가 `MAX_INSTRUCTION_LENGTH`(8,000)를 넘으면 안 된다. 각 필드 상한의 합(200+2000+100+2000+2000 = 6,300)에 머리말을 더해도 8,000 안에 든다 — **구조로 보장된다** |

### 상태 전이

```
(스프레드시트 행)
      │ 가져오기 확정
      ▼
   Draft ──── 사용자가 삭제 ────▶ (없음)
      │
      │ POST /api/sessions {mode:"ai", draft_id}
      ▼
  AI 작성 세션 ── 버림 ──▶ Draft 그대로 남음
      │
      │ 저장
      ▼
    Test        + Draft 파일 삭제
```

초안은 **번호를 예약하지 않는다.** `desired_test_id` 는 희망일 뿐이고, 실제 부여는 저장 시점에
`allocate_test_id` 가 한다(FR-032). 예약하지 않기로 한 덕분에 「번호 정리」·새 테스트 만들기와
아무 상호작용이 없다.

### 파일 형식

`<프로젝트>/drafts/D-0001-로그인.yaml`:

```yaml
draft_id: D-0001
name: 로그인
description: 올바른 자격 증명으로 로그인되는지 확인한다
actor: 관리자
procedure: |-
  1. 로그인 화면을 연다
  2. 아이디와 비밀번호를 입력한다
  3. 로그인 버튼을 누른다
expectation: |-
  1. 대시보드로 이동한다
  2. 우측 상단에 사용자 이름이 보인다
desired_test_id: USER-003
group_prefix: USER
source:
  file_name: 통합테스트설계서.xlsx
  sheet_name: 사용자관리
  row: 4
created_at: 2026-09-10T09:12:00Z
```

기존 `storage/yaml_io.py` 를 그대로 쓴다 — `safe_load`, 4MB 상한, 원자적 쓰기, `sort_keys=False`.

---

## 3. `Test` 확장

`itb/domain/test_case.py` 의 `Test` 에 두 필드를 더한다. **`dsl_version` 은 1 그대로다** (research R11).

```python
    description: str | None = Field(default=None, max_length=2000)
    """테스트항목. 무엇을 확인하는 테스트인지 사람이 읽는 설명."""

    actor: str | None = Field(default=None, max_length=100)
    """수행자 역할. 자유 텍스트이며 자격 증명이 아니다 (FR-026a·FR-026b).

    이 값으로 로그인을 시도하지 않는다. 계정은 지금처럼 민감 변수가 맡는다.
    """
```

기본값이 `None` 이므로 이미 저장된 테스트 파일이 그대로 읽힌다. 필드 순서는 `name` 뒤에 놓아
YAML 에서 사람이 읽기 좋은 자리에 오게 한다 (`sort_keys=False` 라 선언 순서가 파일 순서다).

**재생성 의무**: `backend/schema/step-dsl.schema.json` 과
`frontend/src/types/generated/step-dsl.d.ts` 를 다시 만들어 커밋해야 한다. CI 의 `schema-drift`
잡이 이것을 강제한다.

---

## 4. `MAX_TEST_NUMBER` — 흩어진 999 를 모은다

`domain/test_case.py`:

```python
MAX_TEST_NUMBER = 999
"""프로젝트 하나가 담을 수 있는 테스트 수의 상한.

식별자의 번호가 세 자리이므로 이것이 곧 프로젝트의 수용량이다. 번호는 접두어를 넘어
프로젝트 전체에서 고유하다 (013 research R3).
"""
```

바꿔야 할 곳:

| 위치 | 지금 | 바꾼 뒤 |
|---|---|---|
| `storage/repository.py:323` | `if number > 999:` | `if number > MAX_TEST_NUMBER:` |
| `api/routes/tests.py:482` | `if len(ordered) > 999:` | `if len(ordered) > MAX_TEST_NUMBER:` |
| `domain/test_case.py:259` | `le=999` | `le=MAX_TEST_NUMBER` |
| (신규) 가져오기 수용량 검사 | — | 같은 상수 참조 |

이것이 FR-036c 를 만족시키는 방법이다 — 값을 맞추는 게 아니라 출처를 하나로 만든다.

---

## 5. 가져오기 계획 — 디스크에 쓰지 않는 것들

`itb/portability/importer.py`. 확정 전에는 아무것도 만들지 않으므로(FR-016) 전부 메모리에만 있다.

```python
@dataclass(frozen=True, slots=True)
class SheetPlan:
    sheet_name: str
    prefix: str | None          # None = 읽어내지 못했다. 사용자가 채워야 한다 (FR-022a)
    prefix_source: PrefixSource # from_rows | user_supplied | ungrouped
    group_name: str             # 시트 이름에서 온 이름 (기존 그룹이 있으면 쓰이지 않는다)
    existing_group_name: str | None  # 이미 있는 그룹의 이름. 다르면 알린다 (FR-024a)
    rows: list[RowPlan]

@dataclass(frozen=True, slots=True)
class RowPlan:
    row: int
    name: str
    description: str | None
    actor: str | None
    procedure: str | None
    expectation: str | None
    desired_test_id: str | None
    renumbered_from: str | None   # 파일 안 중복이라 번호가 바뀐 경우 원래 값 (FR-023b)

@dataclass(frozen=True, slots=True)
class SkippedRow:
    sheet_name: str
    row: int
    reason: SkipReason            # no_title | no_columns | empty

@dataclass(frozen=True, slots=True)
class ImportPlan:
    plan_id: str
    file_name: str
    created_at: datetime
    sheets: list[SheetPlan]
    skipped: list[SkippedRow]
    warnings: list[str]

    @property
    def draft_count(self) -> int: ...
    @property
    def needs_prefix(self) -> list[str]:
        """접두어를 사용자에게 물어야 하는 시트 이름들."""
```

### 계획 보관소

`api/state.py` 에 얹는다.

| 항목 | 값 | 근거 |
|---|---|---|
| 수명 | 30분 | 사용자가 미리보기를 보고 결정하기에 넉넉하고, 메모리에 오래 남지 않는다 |
| 최대 개수 | 8 | 넘으면 오래된 것부터 버린다 |
| 만료 후 확정 | `IMPORT_PLAN_NOT_FOUND` | 파일을 다시 고르게 한다 |

---

## 6. 워크북 — 파생 산출물의 모양

### 컬럼 (단일 출처: `portability/columns.py`)

내보내기와 가져오기가 **같은 정의**를 쓴다. 두 벌로 두면 언젠가 어긋난다.

| # | 머리글 | 내보내기 원천 | 가져오기 대상 |
|---|---|---|---|
| 1 | `TC ID` | `Test.id` | `Draft.desired_test_id` |
| 2 | `대상기능` | `Test.name` | `Draft.name` (**필수**) |
| 3 | `테스트항목` | `Test.description` | `Draft.description` |
| 4 | `수행자` | `Test.actor` | `Draft.actor` |
| 5 | `수행 절차` | 검증이 아닌 Step 들의 `label` | `Draft.procedure` |
| 6 | `기대 결과` | `type=="assertion"` 인 Step 들의 `label` | `Draft.expectation` |
| 7 | `결과` | 최근 실행 결과 (R5 표) | **무시한다** (FR-020) |

머리글 대조는 앞뒤 공백을 떼고 대소문자를 무시한다(FR-017). 필수 컬럼은 `TC ID` 와 `대상기능`.

### 절차·기대 결과 셀의 모양

```
1. 로그인 화면을 연다
2. 아이디를 입력한다
3. 로그인 버튼을 누른다
```

- 스텝 실행 순서대로 번호를 매긴 여러 줄 (FR-005)
- 셀 한도(32,767자)를 넘으면 자르고 마지막 줄에 `… (이하 N줄 생략)` 을 남긴다 (FR-010)
- 각 줄 앞에 수식 주입 방어를 적용한다 (research R13)

### 시트

- 순서: `그룹 없음` → `Project.groups` 의 저장 순서 (research R6)
- 1행은 머리글, 고정(freeze panes)한다 (US4)
- 데이터는 시트 안에서 TC ID 순 정렬 (FR-004)
- 테스트가 없는 그룹도 머리글만 있는 시트를 갖는다 (FR-002)
- 초안은 실리지 않는다 (FR-027)

### 파일 이름

`{프로젝트이름 slug}-{YYYYMMDD-HHMMSS}.xlsx`. `storage/paths.py:139` 의 `slugify` 를 재사용한다 —
한글을 살리고 경로 구분자와 제어문자를 떨어낸다. HTTP 헤더에는 ASCII 대체 이름과 RFC 5987 이름을
함께 싣는다 (research R9).

---

## 7. 새 오류 코드

`domain/error.py` 의 `ErrorCode` 에 7개를 더하고, `CATEGORY` 와 `NEXT_ACTION` 두 표를 함께 채운다.
빠지면 `tests/abnormal/test_error_contract.py` 가 실패한다.

| 코드 | Category | next_action |
|---|---|---|
| `IMPORT_FILE_REJECTED` | blocked | 더 작은 파일을 고르거나, 스프레드시트 형식(.xlsx)인지 확인한 뒤 다시 시도하세요. |
| `IMPORT_PLAN_NOT_FOUND` | blocked | 미리보기가 만료됐습니다. 파일을 다시 고르세요. |
| `IMPORT_CAPACITY_EXCEEDED` | blocked | 프로젝트를 나누거나, 가져올 행을 줄인 뒤 다시 시도하세요. |
| `IMPORT_FAILED` | blocked | 아무것도 만들어지지 않았습니다. 원인을 고친 뒤 다시 시도하세요. |
| `IMPORT_PARTIAL` | blocked | 표시된 항목이 어디 있는지 확인한 뒤 손으로 정리하세요. |
| `DRAFT_NOT_FOUND` | blocked | 목록을 새로 고친 뒤 다시 시도하세요. |
| `EXPORT_FAILED` | blocked | 잠시 뒤 다시 시도하세요. 계속 실패하면 읽을 수 없는 테스트 정의가 있는지 확인하세요. |

`IMPORT_PARTIAL` 은 `detail.stranded` 에 `[{target, where}]` 를 싣는다 —
기존 `TEST_MOVE_PARTIAL` 과 같은 모양이다.

---

## 8. 원자성 — 무엇을 어떤 순서로 쓰는가

가져오기 확정은 두 종류의 쓰기를 한다. 순서와 되돌림이 계약이다.

```
1. 수용량 검사 (아무것도 안 건드림)
   ├ 만들 초안 수 + 기존 테스트 수 > MAX_TEST_NUMBER  →  IMPORT_CAPACITY_EXCEEDED
   └ 접두어 형식·예약어 검사                          →  DEFINITION_INVALID

2. itb-project.yaml 에 새 그룹 추가 (1회 원자적 쓰기)
   └ 실패 → 아무것도 안 만들어짐. IMPORT_FAILED

3. 초안 파일들을 run_all 로 만든다
   ├ validate: 이미 있는 draft_id 인가
   ├ do:       drafts/<id>-<slug>.yaml 쓰기
   ├ undo:     그 파일 삭제
   ├ AllOrNothingError  → 2번을 되돌리고 IMPORT_FAILED
   └ PartialFailureError → 2번을 되돌리고 IMPORT_PARTIAL (stranded 동반)
```

**그룹을 먼저 쓰는 이유**: 초안이 가리키는 접두어의 그룹이 아직 없으면 목록 화면이 그 초안을
어디에도 놓지 못한다. 반대 순서에서 실패하면 "그룹 없는 초안"이 남는다 —
`test_moves.rename_test_id` 가 산출물을 먼저 옮기는 것과 같은 판단이다:
**눈에 보이지 않는 흔적이 눈에 보이는 손실보다 낫다.**

「엑셀에서 새 프로젝트」 경로는 위 앞에 0번이 붙는다 — 프로젝트를 만들고, 1~3 중 어디서든
실패하면 만든 프로젝트 디렉터리를 휴지통으로 옮긴다(FR-014c). 지우지 않고 휴지통으로 보내는 것은
013 이 삭제를 휴지통 이동으로 정한 결정을 그대로 쓰는 것이다.
