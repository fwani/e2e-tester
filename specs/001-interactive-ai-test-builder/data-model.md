# Data Model: Interactive AI Test Builder

**Feature**: `001-interactive-ai-test-builder` | **Date**: 2026-09-03
**Authority**: 이 문서의 모든 구조는 `itb/domain/*.py` 의 Pydantic v2 모델이 권위 정의다 (research R6).
아래 표기는 그 모델의 설명이며, 불일치가 생기면 코드가 옳다.

---

## 1. 저장 레이아웃

단독 로컬 도구(FR-088)이므로 데이터베이스 서버가 없다. 프로젝트 하나 = 디렉터리 하나.

```text
<프로젝트 디렉터리>/
├── itb-project.yaml          # 프로젝트 메타 — 커밋 대상
├── tests/
│   ├── TC-001-project-create.yaml   # 테스트 정의 — 커밋 대상, 사람이 읽는 형식
│   └── TC-002-project-delete.yaml
├── secrets.local.yaml        # 민감 값 암호문 — .gitignore 대상
├── .runs/                    # 실행 산출물 — .gitignore 대상
│   └── TC-001/
│       ├── result.json
│       ├── failure.png
│       ├── console.log
│       └── network.jsonl
└── .gitignore                # 프로젝트 생성 시 자동 작성
```

키 쌍은 프로젝트 밖에 둔다: `~/.config/itb/keys/{private.key,public.key}` (FR-089a, FR-089e).

**설계 근거**: 테스트 정의만 커밋 대상이고 비밀값·실행 산출물은 제외된다. 이 분리가 FR-088b
(사용자가 그대로 버전 관리에 넣을 수 있음)와 FR-089c(암호문조차 정의 파일에 넣지 않음)를 동시에 만족한다.
실행 이력은 테스트별 최근 1건만 보관한다(spec Assumptions) — `.runs/<테스트ID>/` 를 덮어쓴다.

---

## 2. Project

| 필드 | 타입 | 규칙 |
|------|------|------|
| `name` | str | 필수. 1~100자 |
| `default_start_url` | str | 필수. `http`/`https` 스킴만 허용 (FR-085) |
| `browser` | enum | `chromium` 만 (MVP) |
| `test_id_attribute` | str | 기본 `data-testid`. 대상 앱이 쓰는 속성명 (research R4) |
| `next_test_number` | int | `TC-001` 자동 부여용 카운터 |

`itb-project.yaml` 예:

```yaml
name: 데이터 플랫폼
default_start_url: https://example.internal/login
browser: chromium
test_id_attribute: data-testid
next_test_number: 5
```

---

## 3. Test

테스트 하나 = `tests/` 아래 YAML 파일 하나. PRD §9의 형태를 따른다.

| 필드 | 타입 | 규칙 |
|------|------|------|
| `id` | str | 프로젝트 내 유일. `TC-\d{3}` 패턴. 자동 부여 |
| `name` | str | 필수. 1~200자 |
| `authoring_mode` | enum | `record` \| `ai` — 목록의 작성 방식 배지 (FR-002) |
| `start_url` | str | 필수. 스킴 검증 |
| `browser` | enum | `chromium` |
| `variables` | list[Variable] | 0개 이상 |
| `steps` | list[Step] | **1개 이상** (FR-029: Step 0개 저장 금지) |
| `ai_instruction` | str \| null | 자연어 지시문 원문. **실행 대상이 아니다** (FR-063) |
| `created_at` / `updated_at` | datetime | ISO 8601 |

`Test.last_run` 은 정의 파일에 넣지 않는다. `.runs/<id>/result.json` 에서 읽는다 — 정의 파일이 실행마다
바뀌면 git diff가 무의미해지기 때문이다.

---

## 4. Step (원칙 I — 단일 모델)

**사람이 만든 Step과 AI가 만든 Step은 같은 타입이다.** 작성 주체는 부가 정보이며 실행에 영향을 주지 않는다
(FR-014).

공통 필드:

| 필드 | 타입 | 규칙 |
|------|------|------|
| `id` | str | 테스트 내 유일. `step-\d{2,}` |
| `type` | enum | `click` \| `fill` \| `select` \| `navigate` \| `assertion` \| `close_tab` (FR-013) |
| `label` | str | 사람이 읽는 표시 이름. 목록·결과 화면에 나온다 |
| `author` | enum | `human` \| `ai` (FR-014, FR-075) |
| `tab` | int | **탭 참조.** 열린 순서. 최초 탭 = 0 (FR-030a) |
| `timeout_ms` | int | 기본 5000 (research R8). 1~60000 |
| `frame_url` | str \| null | 하위 프레임에서 기록된 경우. MVP 실행은 main frame만 (research R2) |

종류별 추가 필드:

| type | 추가 필드 |
|------|-----------|
| `click` | `target: TargetLocator` |
| `fill` | `target: TargetLocator`, `value: str` (변수 참조 가능) |
| `select` | `target: TargetLocator`, `value: str` |
| `navigate` | `url: str` |
| `assertion` | `assertion: Assertion` |
| `close_tab` | 없음 — `tab` 필드가 대상을 가리킨다 (FR-030c) |

### 탭 해석 규칙 (FR-030a~e)

- `tab` 은 **열린 순서**다. 최초 탭이 0, 그다음 열린 탭이 1이다. 새 탭 열림은 Step이 아니다 (FR-030b) —
  새 탭을 열게 한 클릭이 이미 Step이기 때문이다.
- 실행 시 `tab` 에 해당하는 탭이 없으면 `timeout_ms` 까지 열리기를 기다린다. 상한 초과 시 "탭 N이
  열리지 않았다"로 실패한다 (FR-030d).
- 조작 국면에서는 대상 탭을 앞으로 가져온다 (FR-030e).
- 동시 탭 상한 10 (FR-030g). 초과 시 기록 중단.

**알려진 취약점**: 대상 앱이 탭을 비결정적 순서로 열면 참조가 어긋나 해당 Step이 실패한다. 이를 감추지 않고
실패 메시지에 순서 불일치 가능성을 포함한다. SC-012가 이 취약점의 실측 지표다.

Pydantic에서는 `type` 을 판별자로 하는 판별 유니온으로 정의한다. 이 구조가 그대로 JSON Schema →
TypeScript 판별 유니온으로 내려간다 (research R6).

---

## 5. Assertion (FR-013a — 4종)

| 필드 | 타입 | 규칙 |
|------|------|------|
| `kind` | enum | `visible` \| `hidden` \| `text` \| `url` |
| `target` | TargetLocator \| null | `visible`·`hidden`·요소 대상 `text` 에서 필수. `url` 에서는 null |
| `match` | enum | `equals` \| `contains` — `text`·`url` 에서만 사용 |
| `value` | str \| null | 비교 값. `{{변수명}}` 참조 가능 (FR-013b) |

| kind | 의미 | 통과 조건 |
|------|------|-----------|
| `visible` | 요소가 보인다 | 대기 시간 안에 요소가 나타나고 보이면 통과 |
| `hidden` | 요소가 없거나 보이지 않는다 | 처음부터 없었던 경우와 사라진 경우 **모두 통과** (spec 엣지 케이스) |
| `text` | 텍스트 일치/포함 | `target` 이 있으면 그 요소, 없으면 화면 전체 |
| `url` | 현재 주소 일치/포함 | 요소 탐색 없음 |

요소 갯수·입력값 검증은 범위 외 (FR-013c).

---

## 6. TargetLocator (원칙 IV)

**단일 셀렉터가 아니라 후보 묶음이다** (FR-017).

| 필드 | 타입 | 비고 |
|------|------|------|
| `tag` | str \| null | 진단용 |
| `test_id` | Candidate \| null | 우선순위 1 |
| `role` | str \| null | 우선순위 2 (accessible_name과 짝) |
| `accessible_name` | str \| null | |
| `label` | Candidate \| null | 우선순위 3 |
| `text` | Candidate \| null | 우선순위 4 |
| `stable_attr` | Candidate \| null | 우선순위 5. `{name, value}` |
| `css` | Candidate \| null | 우선순위 6 — 최후 |

`Candidate`:

| 필드 | 타입 | 값 |
|------|------|-----|
| `value` | str | 수집된 값 |
| `status` | enum | `verified` \| `unverified` \| `not_collected` |

`status` 는 **기록 시점 검증 결과**다 (research R4). `verified` 는 녹화 직후 그 후보로 찾은 요소가 실제
클릭한 요소와 동일함을 확인했다는 뜻이다. `StepInspector` 화면의 `사용 중` / `대체 N` / `최후` /
`수집되지 않음` 표시는 이 값과 우선순위 순서에서 파생된다 (FR-019).

**불변식**: 후보가 하나도 없는 `TargetLocator` 는 유효하지 않다. 최소한 `css` 는 항상 수집된다.
SC-008(후보 2개 이상 확보 90%)은 `verified` 후보 수를 세어 측정한다.

---

## 7. Variable / SecretStore / KeyPair

### Variable (테스트 정의 안)

| 필드 | 타입 | 규칙 |
|------|------|------|
| `name` | str | `[A-Z][A-Z0-9_]*`. 테스트 내 유일 |
| `value` | str \| null | **`sensitive=true` 이면 반드시 null** (FR-082) |
| `sensitive` | bool | 기본 false |

**불변식**: `sensitive and value is not None` → 검증 실패. 이것이 민감 값이 정의 파일에 들어가는 것을
스키마 수준에서 막는다.

### SecretStore (`secrets.local.yaml`)

```yaml
public_key_fingerprint: "SHA256:a1b2c3..."   # 키 교체 감지 (spec 엣지 케이스)
values:
  LOGIN_PASSWORD: "c2VhbGVkYm94Y2lwaGVydGV4dA=="   # SealedBox 암호문, base64
```

### 값 해석 순서 (실행 시, FR-089g)

```
1. 동일 이름 환경 변수가 있으면 → 그 값
2. secrets.local.yaml 에 암호문이 있으면 → 비밀키로 복호화
3. Variable.value 가 있으면 → 그 값 (민감하지 않은 변수)
4. 없으면 → 해당 Step 실패, 사유 명시 (FR-089f)
```

### KeyPair

| 필드 | 위치 | 권한 |
|------|------|------|
| 비밀키 | `~/.config/itb/keys/private.key` | `0600`. 선택적 암호구 보호 (FR-089e) |
| 공개키 | `~/.config/itb/keys/public.key` | `0644` |

---

## 8. RunSession — 상태 기계

**이 상태 기계가 원칙 III의 구현체다.** 헌법 품질 게이트가 이것의 단위 테스트를 요구한다.

```text
                    ┌──────────┐
                    │ STARTING │  브라우저 실행 중
                    └────┬─────┘
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌───────────┐   ┌───────────┐   ┌────────────┐
   │ RECORDING │   │ REPLAYING │   │ AI_RUNNING │
   │ 사람 녹화  │   │ 결정적 실행│   │  AI 수행   │
   └─────┬─────┘   └─────┬─────┘   └──┬──────┬──┘
         │               │            │      │ 도구 실패
         │  일시정지      │  일시정지   │ 일시 │
         └───────┬───────┴────────────┘ 정지 ▼
                 ▼                     │ ┌────────────┐
           ┌──────────┐◀───────────────┘ │ AI_BLOCKED │
           │  PAUSED  │                  │ 선택 대기   │
           │ 편집 가능 │                  └──┬───┬───┬─┘
           └────┬─────┘         직접 수행 ────┘   │   └──── 종료
                │                  │         AI에게 다시
   계속하기 /   │                  ▼             │
   이 Step부터  │        ┌────────────────────┐  │
                │        │ TAKEOVER_RECORDING │──┘
                │        │  사람이 이어받음     │  계속하기
                │        └──────────┬─────────┘
                ▼                   ▼
           ┌─────────────────────────────┐
           │ COMPLETED / FAILED / STOPPED │
           └─────────────────────────────┘

           ┌──────┐  브라우저 창이 외부에서 닫힘 (어느 상태에서든)
           │ LOST │  → Step 보존, 이어서 실행 불가 (FR-041)
           └──────┘
```

| 상태 | 디자인 배지 | 브라우저 세션 | 편집 가능 |
|------|-------------|---------------|-----------|
| `STARTING` | — | 실행 중 | 아니오 |
| `RECORDING` | `작성 RECORD` | 유지, 실제 창 전면 (FR-023a) | 아니오 |
| `REPLAYING` | `RUNNING` | 유지, 읽기 전용 미러 | 아니오 |
| `AI_RUNNING` | `AI 수행 중` | 유지, 읽기 전용 미러 | 아니오 |
| `PAUSED` | `PAUSED` | **유지** (FR-032) | **예** (FR-035) |
| `AI_BLOCKED` | 실패 카드 + 4선택지 | **유지** (FR-069) | 아니오 |
| `TAKEOVER_RECORDING` | `사람이 녹화 중` + `세션 유지` | 유지, 실제 창 전면 | 아니오 |
| `COMPLETED`/`FAILED`/`STOPPED` | 결과 화면 | 종료 | — |
| `LOST` | 세션 유실 안내 | 없음 | 아니오 |

### 불변식

1. **`PAUSED`·`AI_BLOCKED` 에서 브라우저 세션은 절대 종료되지 않는다.** (FR-032, FR-069)
2. 편집 명령은 `PAUSED` 에서만 받는다. 다른 상태에서 오면 거절한다.
3. `PAUSED` 에서 이미 실행된 Step을 편집하면 **테스트 정의만 변경**하고 브라우저에 아무 명령도 보내지
   않는다. 편집 지점이 `current_step_index` 이전이면 경고 플래그를 세운다. (FR-040a~c)
4. `REPLAYING` 상태의 코드 경로는 `itb.llm` 을 임포트할 수 없다 — `import-linter` 강제 (FR-044).
5. 테스트당 활성 세션은 1개 (FR-043).

| 필드 | 타입 | 비고 |
|------|------|------|
| `session_id` | str | UUID |
| `test_id` | str \| null | 저장 전 초안이면 null |
| `state` | enum | 위 상태 |
| `current_step_index` | int | 0-기반. 다음에 실행할 Step |
| `tabs` | list[TabHandle] | 열린 순서. `tab_index` → 실제 Page 매핑 |
| `active_tab_index` | int | 조작 전면 배치·미러 대상 탭 |
| `mirrored_tab_index` | int | 미러가 표시 중인 탭. 한 번에 하나 (research R3) |
| `steps` | list[Step] | 작업 중 사본. 저장 시 Test로 커밋 |
| `edit_warnings` | list[str] | 불변식 3의 경고 (FR-040b) |
| `pause_event` | asyncio.Event | 메모리 전용. 직렬화하지 않는다 |

---

### TabHandle (메모리 전용, 직렬화하지 않음)

| 필드 | 타입 | 비고 |
|------|------|------|
| `tab_index` | int | 열린 순서. 부여 후 불변 |
| `page` | Playwright Page | |
| `opened_at` | datetime | |
| `closed` | bool | 닫힌 탭도 목록에서 제거하지 않는다 — 이후 Step의 `tab` 값이 밀리면 안 되기 때문 |

**불변식**: `tab_index` 는 재사용하지 않는다. 탭 0을 닫고 새 탭을 열면 그 탭은 0이 아니라 다음 번호를 받는다.
번호를 재사용하면 저장된 Step의 `tab` 참조가 다른 탭을 가리키게 된다.

---

## 9. RunResult

`.runs/<테스트ID>/result.json` 에 저장. 테스트당 최근 1건.

| 필드 | 타입 | 화면 대응 |
|------|------|-----------|
| `test_id` | str | |
| `outcome` | enum | `pass` \| `fail` — `TestList` 상태 배지 (FR-048) |
| `started_at` / `finished_at` | datetime | |
| `total_ms` | int | `RunResult` 의 "총 시간" (FR-050) |
| `passed_count` / `total_count` | int | "통과 / 전체" |
| `failed_step_index` | int \| null | "멈춘 STEP" |
| `browser` | str | "Playwright · Chromium" 표기 (FR-058) |
| `steps` | list[StepResult] | Step별 결과 (FR-051) |
| `artifacts` | Artifacts | 아래 |

### StepResult

| 필드 | 타입 | 비고 |
|------|------|------|
| `step_id` / `index` / `label` | | |
| `outcome` | enum | `pass` \| `fail` \| `skipped` \| `not_run` |
| `duration_ms` | int | 디자인의 `421 ms` 표기 |
| `resolved_candidate` | str \| null | 어느 후보로 찾았는지 (`test_id`, `role` …) |
| `locator_attempts` | list[LocatorAttempt] | 실패 시 시도 내역 (FR-021) |
| `error_message` | str \| null | 사람이 읽는 실패 이유 (FR-054) |
| `tab` | int | 어느 탭에서 실행했는지 |
| `tab_wait_ms` | int | 탭이 열리기를 기다린 시간 (FR-030d) |
| `candidate_disagreement` | list[str] | 후보 간 불일치 기록 (spec 엣지 케이스) |

### LocatorAttempt

`RunResult.dc.html` 의 "시도한 LOCATOR (우선순위 순)" 표시에 1:1 대응한다.

| 필드 | 타입 | 예 |
|------|------|-----|
| `candidate` | str | `test_id` |
| `expression` | str | `testId=save-dataset` |
| `matched` | bool | `false` |
| `waited_ms` | int | `5000` |

### Artifacts

| 필드 | 타입 | 비고 |
|------|------|------|
| `failure_screenshot` | path \| null | FR-052 |
| `console_log` | path \| null | FR-053 |
| `network_log` | path \| null | FR-053 |
| `trace` | null | **MVP 미지원** — `TRACE` 탭 비활성 (spec 디자인 차이 1) |

**모든 산출물은 디스크에 쓰기 직전 로그 스크러버를 통과한다** (FR-089d, research R7).

---

## 10. AiInstruction

| 필드 | 타입 | 비고 |
|------|------|------|
| `text` | str | 자연어 지시문 원문 |
| `produced_step_ids` | list[str] | 이 지시문에서 나온 Step |

`Test.ai_instruction` 에 원문만 보관한다. **실행 대상이 아니다** (FR-063). `AiRecord.dc.html` 의
"지시문은 테스트로 저장되지 않습니다" 문구가 이 결정의 사용자 향 표현이다.

`itb.execution` 은 이 필드를 읽지 않는다 — 읽을 이유가 없고, 읽는 코드가 생기면 원칙 II 경계가 흐려진다.

---

## 11. 엔티티 관계

```text
Project 1 ──* Test 1 ──* Step
                 │         └──1 TargetLocator ──* Candidate
                 │         └──1 Assertion (type=assertion)
                 ├──* Variable ─────┐
                 ├──0..1 AiInstruction
                 └──0..1 RunResult ──* StepResult ──* LocatorAttempt
                                    └──1 Artifacts
                                   ┌──┘
SecretStore *──── (Variable.name 로 참조, sensitive=true 인 것만)
     │
     └── 복호화 ── KeyPair (비밀키, 실행 시점에만)

RunSession ──1 (작업 중) Step 목록 ──▶ 저장 시 Test.steps 로 커밋
     └──* TabHandle  (tab_index → Page, 메모리 전용)
                ▲
          Step.tab 이 참조
```

## 12. 검증 규칙 요약 (FR-085 경계 검증)

| 대상 | 규칙 |
|------|------|
| 사용자 입력 URL | `http`/`https` 스킴만. 길이 상한 |
| 테스트 이름 | 1~200자. 경로 구분자·제어 문자 금지 (파일명으로 쓰이므로) |
| 테스트 ID | `TC-\d{3}` 패턴 강제 |
| 디스크의 테스트 정의 | Pydantic 검증 통과 필수. 실패 시 파일을 고칠 수 있게 오류 위치를 알린다 |
| 변수 이름 | `[A-Z][A-Z0-9_]*` |
| 민감 변수 | `value` 가 반드시 null (불변식) |
| Step 목록 | 1개 이상 (FR-029) |
| `timeout_ms` | 1~60000 |
| `Step.tab` | 0 이상의 정수. 상한 없음(열린 순서이므로) |
| 자연어 지시문 | 길이 상한. 언어모델로 보내기 전 검증 |
| 대상 화면에서 읽어온 내용 | 길이 절단 + 코드 생성 시 이스케이프 (헌법 보안 요건) |
| YAML 로드 | 안전 로더만. 임의 객체 역직렬화 금지 |
