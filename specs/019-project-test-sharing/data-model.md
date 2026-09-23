# Phase 1 Data Model: 프로젝트·테스트 공유용 내보내기·가져오기

**Feature**: `019-project-test-sharing` | **Date**: 2026-09-23

정본은 `backend/schema/share-bundle.schema.json` 이다. 백엔드는 Pydantic 모델에서 그 스키마를
내보내고(`python -m itb.schema.export --check` 가 어긋남을 잡는다), 프론트엔드는 거기서 타입을
생성한다(`npm run gen:types`). **손으로 유지하는 두 번째 정의를 두지 않는다** (헌법 §교차 언어
스키마 의무).

---

## 1. 저장되는 것과 저장되지 않는 것

| 것 | 사는 곳 | 수명 |
|---|---|---|
| 공유 묶음 파일 | 사용자가 받아 간 곳 | 도구가 보관하지 않는다 |
| 가져오기 계획 | 서버 메모리 (`SharePlanStore`) | 30분 또는 서버 종료까지 |
| 가져온 테스트 | `<프로젝트>/tests/*.yaml` | 사용자 자산 |
| 가져오기 출처 표시 | 각 테스트 파일 안 (`imported_from`) | 테스트와 함께 |
| 채워 넣은 민감 값 | `<프로젝트>/secrets.local.yaml` (암호문) | 사용자 자산, 커밋 제외 |
| 채워 넣은 비민감 값 | 해당 `tests/*.yaml` 의 `variables[].value` | 사용자 자산, 커밋 대상 |

**묶음 파일을 도구가 보관하지 않는 것이 중요하다.** 보관하면 그 자체가 관리 대상이 되고,
"어느 묶음에서 왔는지" 를 파일 경로로 기억하게 되며, 사용자가 지운 파일을 도구가 붙잡고 있게
된다. 출처는 테스트 안의 **표시 이름**으로만 남는다.

---

## 2. 공유 묶음 (ShareBundle)

YAML 문서 하나. 최상위 키 순서는 사람이 읽기 좋게 고정한다 — 경고가 맨 위다.

```yaml
# 이 파일에는 비밀번호·API 키 등 민감 값이 들어 있지 않습니다.
# 가져온 뒤 필요한 값은 받는 분이 직접 입력합니다. (required_values 참고)
bundle_version: 1
generator: itb 0.19.0
created_at: 2026-09-23T04:12:00Z
project:
  name: dev-graphio
  default_start_url: https://example.internal
  browser: chromium
  test_id_attribute: data-testid
  max_tabs: 10
  groups:
    - prefix: USER
      name: 사용자관리
required_values:
  - name: SECRET_INPUT_LOGIN_PW
    sensitive: true
    declared: true
    usages:
      - test_id: TC-001
        step_id: step-02
        step_label: 비밀번호 입력
        field: value
  - name: LOGIN_ID
    sensitive: false
    declared: true
    usages:
      - test_id: TC-001
        step_id: step-01
        step_label: 아이디 입력
        field: value
tests:
  - dsl_version: 1
    id: TC-001
    name: 운영 관리 메뉴 진입
    # ... Test 모델 그대로
```

### 2.1 필드

| 필드 | 형 | 규칙 |
|---|---|---|
| `bundle_version` | int | `1` 만 읽는다. 크면 거부(FR-030), 작으면 이 도구에 그런 버전이 없으므로 거부. |
| `generator` | str | 만든 도구 이름·버전. 표시·진단용이며 판정에 쓰지 않는다. 최대 100자. |
| `created_at` | datetime (UTC) | 만든 시각. |
| `project` | BundleProject | 아래 2.2. |
| `required_values` | list[RequiredValue] | 아래 2.3. **참고용 요약이며 정본이 아니다** (R7). |
| `tests` | list[Test] | `itb.domain.test_case.Test` 그대로. 1개 이상, `MAX_BUNDLE_TESTS` 이하. |

### 2.2 BundleProject

`Project` 에서 **가져가는 쪽에 의미 없는 것을 뺀 것**이다.

| 포함 | 뺀 것과 이유 |
|---|---|
| `name`, `default_start_url`, `browser`, `test_id_attribute`, `max_tabs`, `groups` | `next_test_number` — 이미 쓰이지 않는 하위 호환 필드다(도메인 주석). 묶음에 실으면 새 형식이 옛 잔재를 물려받는다. |

`groups` 에는 **묶음 안 테스트가 실제로 쓰는 접두어의 그룹만** 담는다. 빈 그룹을 옮기면 받는
쪽에 테스트 없는 그룹이 생긴다 — 전체 프로젝트를 내보낼 때는 빈 그룹도 프로젝트 구성이므로
담고, 고른 테스트만 내보낼 때는 담지 않는다.

### 2.3 RequiredValue

받는 사람이 **채워야 실행되는 것**의 목록이다. 민감한 것과 그렇지 않은 것을 한 목록에 둔다 —
받는 사람에게는 둘 다 "비어 있어서 채워야 하는 것" 이고, 다른 것은 저장 위치뿐이다 (FR-040).

| 필드 | 형 | 설명 |
|---|---|---|
| `name` | str (`VARIABLE_NAME_PATTERN`) | 변수 이름. |
| `sensitive` | bool | 참이면 봉인 대상, 거짓이면 테스트 정의에 기록된다 (FR-048). |
| `declared` | bool | 묶음에 변수 선언이 있었는가. 거짓이면 참조만 있어 **보충한 것**이다 (FR-047). |
| `usages` | list[ValueUsage] | 1개 이상. 비면 그 변수를 담지 않는다. |

**담는 기준**: 민감 변수는 **전부** 담는다(정의에 값을 가질 수 없으므로 언제나 비어 있다).
비민감 변수는 **값이 비어 있는 것만** 담는다 — 값이 있으면 채울 것이 없다.

**ValueUsage**: `test_id`, `step_id`, `step_label`(없으면 `null`), `field` ∈
{`value`, `assertion.value`, `url`}.

`field` 의 목록은 `itb.domain.test_case.VARIABLE_VALUE_FIELDS` 하나에서 온다 — 참조를 찾는
`referenced_variable_names` 와 자리를 세는 이 기능이 같은 것을 봐야 한다 (R7).

### 2.4 묶음에 실을 때 비우는 것

| 필드 | 처리 | 이유 |
|---|---|---|
| `Test.imported_from` | `None` 으로 만든다 | 전달이 이어질 때 앞 사람의 가져오기 기록과 파일 이름이 따라간다 (R9). |
| `Test.created_at` / `updated_at` | 그대로 둔다 | 언제 만들어진 테스트인지는 받는 쪽에도 의미가 있다. 개인 식별 정보가 아니다. |

---

## 3. 가져오기 계획 (SharePlan)

메모리에만 있다. 확정 전에는 디스크에 아무것도 쓰지 않는다.

| 필드 | 형 | 설명 |
|---|---|---|
| `plan_id` | str | 계획과 확정을 묶는 키. |
| `created_at` / `expires_at` | datetime | TTL 30분. |
| `file_name` | str | 올린 파일의 표시 이름. **정규화된 값이다** (`sanitize_display_name`). |
| `bundle` | ShareBundle | 해석된 묶음 전체. 확정 때 다시 올리게 하지 않는다. |
| `target` | `"new"` \| `"current"` | 어디로 들어가는가. |
| `target_project_name` | str \| None | `new` 일 때 만들어질 이름 (충돌 회피 후). |
| `groups` | list[GroupPlan] | 아래 3.1. |
| `tests` | list[TestPlan] | 아래 3.2. |
| `required_values` | list[PlannedValue] | 아래 3.3. |
| `capacity` | list[GroupCapacity] | 그룹별 여유 (`prefix`, `needed`, `available`, `ok`). |
| `notices` | list[Notice] | 확인이 필요한 것 — 시작 URL, 이름 변경, 빠진 테스트, 재가져오기 등. |
| `blocking` | list[str] | 비어 있어야 확정할 수 있다. 용량 부족·접두어 확보 실패 등. |

**계획은 확정의 입력이 아니라 예고다.** 확정은 `plan_id` 와 사용자의 선택만 받고, 서버가 보관한
`bundle` 로 계획을 **다시 세운다** — 그 사이 대상 프로젝트가 바뀌었을 수 있기 때문이다. 다시
세운 결과가 예고와 다르면(새 충돌 발생 등) 확정을 멈추고 새 계획을 돌려준다.

### 3.1 GroupPlan

| 필드 | 설명 |
|---|---|
| `source_prefix` / `source_name` | 묶음 안의 값. |
| `target_prefix` / `target_name` | 대상에서 쓸 값. |
| `action` | `reuse`(이름이 같은 그룹에 들어감) \| `create` \| `create_renamed_prefix` \| `skip` |
| `reason` | `skip`·`create_renamed_prefix` 일 때 사유. |

대응 규칙은 [research.md](research.md) R6 의 표가 정본이다.

### 3.2 TestPlan

| 필드 | 설명 |
|---|---|
| `source_id` | 묶음 안의 식별자. |
| `target_id` | 대상에서 받을 식별자. 같으면 재부여 없음. |
| `name` | 테스트 이름. |
| `renumbered` | `source_id != target_id` |
| `group_prefix` | 들어갈 그룹의 대상 접두어. |
| `status` | `create` \| `skip` |
| `reason` | `skip` 사유 (그룹 건너뜀, 용량 부족, 정의 검증 실패). |

### 3.3 PlannedValue

`RequiredValue` + 대상 쪽 사정.

| 필드 | 설명 |
|---|---|
| `name` / `sensitive` / `declared` | `RequiredValue` 와 같다. |
| `usages` | 자리 목록. **`target_id` 기준으로 고쳐 쓴다** — 재부여된 식별자를 보여 줘야 사용자가 찾을 수 있다. |
| `already_stored` | 민감 변수일 때, 대상 프로젝트의 `secrets.local.yaml` 에 같은 이름의 암호문이 있는가 (FR-046). 비민감이면 `null`. |
| `env_provided` | 같은 이름의 환경 변수가 있는가. 있으면 값을 채우지 않아도 실행된다 (R10). |
| `blocks_run` | 값이 없을 때 실행이 막히는가. **민감 변수만 참이다** (FR-044). |

**`already_stored` 와 `env_provided` 만 `itb.secrets`·환경을 필요로 한다.**
`itb.sharing.planner` 는 그 둘을 `None` 으로 두고 만들고, 라우터가 `SecretStore.has(name)` 와
`os.environ` 으로 채운다 (R3).

---

## 4. 가져오기 결과 (ShareReport)

확정 뒤 한 번 만들어져 응답으로만 나간다. 저장하지 않는다.

| 필드 | 설명 |
|---|---|
| `project_root` | 만들어졌거나 들어간 프로젝트 경로. |
| `project_name` | 최종 이름 (충돌로 바뀌었으면 바뀐 이름). |
| `project_renamed_from` | 바뀌었을 때 원래 이름. |
| `created_tests` | `[{target_id, source_id, name, group_prefix}]` |
| `renumbered` | `[{from, to}]` — `created_tests` 의 부분집합을 따로 뽑은 것. 화면이 이것만 강조한다. |
| `created_groups` | `[{prefix, name}]` |
| `skipped` | `[{source_id, reason}]` |
| `repaired_variables` | `[{test_id, name, sensitive}]` — 선언이 없어 보충한 변수 (FR-047). |
| `required_values` | `PlannedValue` 목록 — 이제 **해야 할 일**이다. |
| `notices` | 시작 URL 확인 등. |

---

## 5. `Test` 모델 변경 (기존 파일 수정)

```python
class ImportProvenance(BaseModel):
    """이 테스트가 공유 묶음에서 왔다는 표시 (019 FR-028).

    **실행에 관여하지 않는다** — 헌법 원칙 I 이 허용하는 메타데이터다.
    """
    model_config = ConfigDict(extra="forbid", ...)

    source_file: str = Field(max_length=200)   # 올린 파일의 표시 이름
    imported_at: datetime
    original_id: str = Field(pattern=TEST_ID_PATTERN)


class Test(BaseModel):
    ...
    imported_from: ImportProvenance | None = None
    """기본값 None. **`dsl_version` 을 올리지 않는다** — 올리면 기존 파일이 전부 거절된다."""
```

**하위 호환 확인 항목** (기존 자산이 그대로 읽혀야 한다):

- 019 이전에 저장된 `tests/*.yaml` 에는 이 키가 없다 → 기본값 `None` 으로 읽힌다.
- `extra="forbid"` 이므로 019 로 저장한 파일을 019 이전 도구가 읽으면 거절된다. 이것은
  의도한 방향이다 — 아래로는 호환하지 않는다 (US2 AS5 와 같은 판단).

### 5.1 새 상수

```python
VARIABLE_VALUE_FIELDS = ("value", "assertion.value", "url")
"""변수 참조가 나타날 수 있는 자리 (019 R7).

`referenced_variable_names` 와 공유 묶음의 자리 계산이 **같은 것을 봐야 한다.**
네 번째 자리가 생기는 날 한 곳만 바뀌면, 참조는 찾는데 자리는 못 찾는 상태가 된다.
"""
```

---

## 6. 검증 순서 (묶음 → 저장)

네 겹이며, **앞의 겹을 통과하지 못하면 뒤를 시도하지 않는다.**

1. **바이트** — `MAX_BUNDLE_BYTES` 초과면 읽지 않는다. 상한 + 1 바이트만 읽어 판정한다.
2. **YAML** — 별칭 금지 로더로 파싱. 최상위가 매핑이 아니면 거부.
3. **묶음 모델** — `ShareBundle` Pydantic 검증. `bundle_version`, 건수·그룹 수 상한.
4. **선언 보충** — 참조는 있는데 선언이 없는 변수를 채워 넣는다 (FR-047). 이름이
   `SENSITIVE_VARIABLE_PREFIX`(`SECRET_`)로 시작하면 `sensitive=True, value=None`,
   아니면 `sensitive=False, value=""`. 보충한 것은 `repaired_variables` 에 기록한다.
5. **도메인** — 각 `Test` 를 `Test` 모델로 검증. 스텝 id 중복, 변수 선언·참조 일치,
   `dsl_version`, 로케이터 구조까지 기존 검증이 전부 돈다.

**4번이 5번 앞에 있는 이유**: `Test._check_refs` 는 선언 없는 참조를 거부한다. 보충하지 않고
검증에 넘기면 손으로 편집된 묶음이 통째로 거부되고, 사용자는 "무엇을 고쳐야 하는지" 대신
"읽을 수 없다" 만 받는다. 보충은 **없는 값을 지어내는 것이 아니라 빈 자리를 드러내는 것**이다 —
채우는 것은 사용자이며, 민감 변수라면 채우기 전까지 실행이 막힌다 (FR-044).

5번에서 한 건이라도 실패하면 **가져오기 전체를 거부한다** (FR-023·FR-024). 일부만 살려
들이면 "가져왔는데 왜 3개뿐이지" 를 사용자가 추적할 수 없다. 어느 테스트의 무엇이 문제인지
전부 모아 한 번에 보고한다.

**내보내기 쪽은 다르다.** 읽을 수 없는 테스트가 있으면 그것만 빠지고 나머지는 나간다 (R11) —
자기 프로젝트를 고칠 수 있는 사람은 내보내는 쪽이고, 막으면 갇힌다.

---

## 7. 오류 코드

`itb.api.errors.ErrorCode` 에 추가한다. 기존 관례대로 사유가 사용자에게 그대로 보인다.

| 코드 | 상황 | HTTP |
|---|---|---|
| `SHARE_EXPORT_EMPTY` | 내보낼 테스트가 없다 (FR-009) | 400 |
| `SHARE_BUNDLE_TOO_LARGE` | 바이트·건수·그룹 수 상한 초과 | 413 / 400 |
| `SHARE_BUNDLE_MALFORMED` | YAML 파싱 실패, 별칭 사용, 최상위 형식 오류 | 400 |
| `SHARE_BUNDLE_UNSUPPORTED_VERSION` | `bundle_version` 이 읽을 수 없는 값 | 400 |
| `SHARE_BUNDLE_INVALID_TEST` | 테스트 정의가 도메인 검증에 실패 | 400 |
| `SHARE_PLAN_NOT_FOUND` | `plan_id` 가 없거나 만료됨 | 404 |
| `SHARE_PLAN_STALE` | 다시 세운 계획이 예고와 달라졌다 | 409 |
| `SHARE_IMPORT_BLOCKED` | `blocking` 이 비어 있지 않은데 확정을 시도 | 409 |
| `SHARE_IMPORT_FAILED` | 쓰기 실패. 되돌렸다 | 500 |
| `SHARE_IMPORT_PARTIAL` | 쓰기 실패 후 **되돌리지 못했다**. 남은 것을 실어 보낸다 | 500 |
| `SECRET_VALUE_MISSING` | 실행 전 차단 (FR-044). 빠진 이름 목록을 실어 보낸다 | 409 |

`SHARE_IMPORT_PARTIAL` 을 `SHARE_IMPORT_FAILED` 와 나누는 이유는 사용자가 해야 할 일이 다르기
때문이다 — 전자는 남은 것을 손으로 지워야 하고, 후자는 다시 시도하면 된다.
`test_moves` 의 `AllOrNothingError` / `PartialFailureError` 구분을 그대로 따른다.
