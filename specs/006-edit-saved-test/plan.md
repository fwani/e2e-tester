# Implementation Plan: 저장된 테스트를 고치는 길 — 편집 진입점과 브라우저 없는 편집

**Branch**: `006-edit-saved-test` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-edit-saved-test/spec.md`

## Summary

사용자 보고 한 문장("생성된 테스트 케이스에서 수정하는 방법이 명확하지 않다")을 출처로,
제품에서 확인한 9건(E-01~E-09)을 고친다. 요구사항 FR-175~FR-216(42건, 그중 FR-187 은 범위
제외), 성공 기준 SC-301~SC-309.

**핵심 판단**: 조사 결과 **편집 능력은 이미 다 만들어져 있고, 심지어 브라우저를 모르는 순수
모듈로 분리되어 있다** (`itb.execution.step_edits`). 없는 것은 두 가지다.

1. **그리로 가는 길** — 목록에 편집 진입점이 없고, 「고치기」 버튼은 읽기 전용 화면으로 가고,
   실제 편집 팔레트는 달리는 실행을 「일시정지」로 잡아야 도달한다.
2. **세션을 요구하지 않는 저장 경로** — Step 을 바꾸는 API 가 전부 세션에 매여 있어서, 오탈자
   하나를 고치려고 브라우저를 띄우고 대상 앱에 접속해야 한다.

그래서 이 기능은 편집 기능을 새로 만드는 작업이 **아니다**. 이미 있는 순수 편집 연산에
**두 번째 호출자**(정의 파일 저장)를 붙이고, 화면 셋에 진입점을 놓고, 정의 보기 화면을 편집
가능하게 만드는 작업이다.

붙일 네 곳:

1. **정의 편집 계약** — `GET/PUT /api/tests/{id}/definition`. 초안은 화면이 **편집 연산
   목록**으로 들고, 저장은 한 번의 PUT 이다. 서버가 저장된 정의를 읽어 그 연산을
   `step_edits` 로 적용하므로 편집 규칙의 구현이 프론트로 새지 않는다.
   `revision`(파일 내용 해시)으로 외부 변경을 감지한다 (research R3·R4)
2. **변수 파생 로직 추출** — `sessions.py` 의 `_variables_for()` 를 도메인 계층 순수 함수로
   옮겨 세션 저장과 정의 저장이 같은 것을 쓴다. 두 벌이면 민감 표시가 한쪽에서 강등된다 (R5)
3. **`pause_before_index`** — 세션 생성에 멈춤 지점을 더한다. `RunEngine._pace()` 의 기존
   Step 경계에 목표 인덱스 비교를 두므로 새 상태·새 모드가 없다 (R7)
4. **정의 보기 화면이 편집 가능해진다** — 새 화면을 만들지 않는다. 진입점 3개(목록 행 메뉴,
   결과 화면 「Step nn 고치기」, 정의 보기)가 모두 이 한 화면으로 온다 (R1)

**설계 조사가 명세를 하나 되돌렸다**: FR-187(Step 마다 locator 후보 우선순위 선택)은 헌법
원칙 IV 의 MUST(고정된 해석 순서)와 충돌하고, 브라우저 없이 검증할 수 없는 후보는 거짓
`verified` 를 적거나 조용히 무효가 된다. **범위에서 제외**하고 그 필요는 US3 의 「다시 집기」로
보냈다 (R6). 명세에 이유와 대체 경로를 적었다.

## Technical Context

**Language/Version**: Python 3.13 (backend) · TypeScript 5.7 / React 19 (frontend)

**Primary Dependencies**: FastAPI · Playwright for Python · React 19. **의존성 추가 없음** —
편집 연산·저장·해시 모두 표준 라이브러리와 기존 모듈로 된다

**Storage**: 파일. 테스트 정의는 프로젝트의 `tests/*.yaml`. 원자적 쓰기는 기존
`itb.storage.atomic` 을 쓴다. 새 저장소·새 파일 종류 없음

**Testing**: pytest (backend: unit·contract·integration·abnormal) · Vitest + Testing Library
(frontend). 정의 편집은 **브라우저 없이 검증 가능**하므로 대부분 단위·계약 테스트로 덮인다

**Target Platform**: 로컬 단독 도구. 백엔드 `127.0.0.1` 바인딩. 브라우저는 headed 단일 모드

**Project Type**: 웹 애플리케이션 (backend + frontend 분리)

**Performance Goals**: 편집 화면 열림 — 브라우저 기동 없이 파일 읽기 1회. 편집 조작의 화면
반응은 서버 왕복 없음(초안이 화면에 있다). 저장은 파일 쓰기 1회

**Constraints**:
- Step DSL 을 **바꾸지 않는다** (원칙 I). 스키마 변경이 필요한 요구는 범위에서 뺐다
  (FR-187 · "비활성 Step" 개념)
- 편집·저장 경로에 언어모델 호출을 만들지 않는다 (원칙 II, FR-210)
- locator 해석 순서와 후보 검증 상태를 건드리지 않는다 (원칙 IV, R6)
- 민감 값은 참조만 다룬다. 평문이 편집 화면·요청·로그에 나타나는 경로를 만들지 않는다
  (FR-212·FR-215, R10)
- 스키마는 백엔드가 권위이고 프론트 타입은 생성물 (헌법 Cross-language schema duty)

**Scale/Scope**: 신규 화면 0개(기존 화면 1개가 모드를 얻는다) · 신규 엔드포인트 2개 ·
백엔드 변경 파일 약 6개 · 프론트 변경 파일 약 5개 · 요구사항 41건(제외 1건 별도)

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 설계 후 재확인.*

| 원칙 | 이 기능과의 관계 | 판정 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | **Step DSL 을 바꾸지 않는다.** 정의 편집은 기존 `Step`·`Test` 모델을 읽고 쓴다. 편집 연산도 세션 편집과 **같은 모듈**(`step_edits`)을 쓰므로 편집 경로가 두 번째 표현을 만들지 않는다 (R2). 화면도 하나다 — 「보기」와 「편집」이 같은 화면의 두 모드다 (R1) | ✅ 통과 (이 원칙의 방향과 같다) |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 정의 편집·검증·저장·충돌 감지·경고 문구 생성은 **전부 규칙 기반**이다. 새 코드 경로에서 언어모델을 부르지 않는다. 자연어 Step 추가는 지금처럼 **세션 작성 경로**에만 남고 정의 편집 경로로 옮기지 않는다 | ✅ 통과 |
| **III. Stateful Interactive Runner** | 상태 기계에 새 상태를 넣지 않는다. `pause_before_index` 는 기존 Step 경계에서 기존 `PAUSED` 로 들어간다 (R7). 브라우저 없이 편집한 뒤 저장하고 세션을 여는 순서(FR-203)는 "편집이 처음부터 실행을 강요하지 않는다" 는 이 원칙의 취지를 강화한다 | ✅ 통과 |
| **IV. Locator Resilience** | **해석 순서와 후보 검증 상태를 건드리지 않는다.** 그것을 건드리려던 FR-187 을 범위에서 뺐다 (R6). 편집 화면에서 locator 후보는 읽기 전용이며, 후보를 다시 만드는 것은 실제 요소에서 수집·검증하는 「다시 집기」뿐이다 | ✅ 통과 (제외 결정으로 보호) |
| **V. Asset Portability** | Step DSL 과 저장 형식이 그대로이므로 내보내기 대응이 바뀌지 않는다. 오히려 이 기능은 원칙 V 를 강화한다 — 사용자가 편집기로 YAML 을 직접 고치는 것을 정상 사용으로 인정하고 충돌을 감지한다 (FR-209, R4) | ✅ 통과 |

**Cross-language schema duty**: 신규 요청·응답 모델(`DefinitionView`·`SaveDefinitionRequest`)은
백엔드 Pydantic 모델이 권위이고, 프론트는 `frontend/src/types/generated/` 로 생성한 타입을
쓴다. `Test`·`Step` 자체는 바뀌지 않으므로 기존 생성 타입이 그대로 쓰인다.

**Security requirements**:
- 요청은 경계에서 검증한다 (FR-211). `extra="forbid"`, Step 목록은 기존 `Step` 어댑터로
  파싱, 순서·인덱스 범위 검사, 알 수 없는 Step id 거절
- 민감 값 평문을 받는 필드를 만들지 않는다 (R10). 정의 편집 요청에는 참조 문자열만 들어온다
- 원자적 쓰기로 부분 저장된 정의 파일을 만들지 않는다 (기존 `atomic.write_text`)
- 오류는 명시적으로 다룬다 — 스키마 위반·충돌·실행 중은 각각 다른 코드와 다음 행동을 준다

**Quality gates**:
1. 원칙 준수 — 재생 경로에 언어모델이 닿지 않음을 이 기능이 새로 만드는 경로에서 확인한다
2. 왕복 정합성 — 편집 → 저장 → 재실행, 그리고 편집 → 저장 → 내보내기 대응(정의 형식 불변)
3. 테스트 — 정의 편집은 브라우저 없이 검증되므로 단위·계약 테스트 비중이 높다. 화면은 Vitest
4. 비활성 테스트 없음
5. 성공 지표 — 이 기능은 PRD §18 의 "테스트 생성" 이 아니라 **수정 왕복**에 영향을 준다.
   SC-303(왕복 끊김 0건)·SC-305(실행 잡기 0건)가 그 측정이다

**위반 없음** → Complexity Tracking 은 비어 있다.

### Phase 1 설계 후 재확인

| 원칙 | 재확인 결과 |
|---|---|
| I | `data-model.md` 의 편집 가능 표를 전수 작성한 결과 **새 필드가 하나도 필요하지 않았다.** 편집 대상은 모두 기존 필드다 |
| II | 신규 엔드포인트 2개 어디에도 작성(authoring) 계층 호출이 없다. `contracts/rest-api.md` 에 그 사실을 계약으로 적었다 |
| III | `pause_before_index` 는 `SessionState` 에 값 하나를 더할 뿐 상태 집합을 바꾸지 않는다 |
| IV | 편집 요청 모델에 locator 관련 필드가 **없다.** 구조적으로 후보를 손댈 수 없다 |
| V | 저장 경로가 `repo.write_test()` 하나로 수렴한다 — 세션 저장과 정의 저장이 같은 함수를 쓴다 |

## Project Structure

### Documentation (this feature)

```text
specs/006-edit-saved-test/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — 결정 10건 (R1~R10)
├── data-model.md        # Phase 1 — 편집 가능 표, 초안 상태, 검증 규칙
├── quickstart.md        # Phase 1 — 사람이 직접 걷는 검증 절차
├── contracts/
│   ├── rest-api.md      # 신규 엔드포인트 2개 + 세션 생성 필드 1개
│   └── ui-contract.md   # 진입점 3개, 편집 화면의 두 모드, 문구 규칙
├── checklists/
│   └── requirements.md  # specify 단계 품질 체크리스트
└── tasks.md             # /speckit-tasks 산출물 (이 명령이 만들지 않는다)
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── api/routes/
│   │   ├── tests.py            # ← 변경: GET/PUT /{id}/definition 추가
│   │   └── sessions.py         # ← 변경: pause_before_index, _variables_for 추출
│   ├── domain/
│   │   └── test_case.py        # ← 변경: derive_variables() 순수 함수 이식
│   ├── execution/
│   │   ├── step_edits.py       # 변경 없음 — 그대로 재사용한다 (R2)
│   │   └── runner.py           # ← 변경: _pace() 에 멈춤 지점 비교
│   └── storage/
│       └── repository.py       # ← 변경: definition_revision(test_id) 추가
└── tests/
    ├── contract/               # ← 신규: 정의 편집 계약
    ├── unit/                   # ← 신규: 변수 파생, revision, 검증 규칙
    └── integration/            # ← 신규: 편집→저장→재실행, pause_before_index

frontend/
├── src/
│   ├── api/client.ts           # ← 변경: definition 조회·저장 클라이언트
│   ├── App.tsx                 # ← 변경: 편집 진입점 배선, 이탈 확인
│   ├── pages/
│   │   ├── TestDefinition.tsx  # ← 변경: 편집 모드 (핵심)
│   │   ├── TestList.tsx        # ← 변경: 행 메뉴에 「편집」
│   │   └── RunResult.tsx       # ← 변경: 「Step nn 고치기」가 편집으로
│   ├── components/
│   │   └── StepEditFields.tsx  # ← 신규(작을 것): 값·라벨·대기시간 입력
│   └── lib/wording.ts          # ← 변경: 편집 관련 어휘 한 곳에
└── tests/                      # ← 신규: 편집 화면 · 진입점 · 이탈 확인
```

**Structure Decision**: 기존 웹 애플리케이션 구조를 그대로 쓴다. **신규 화면 0개** — 편집은
기존 `TestDefinition` 화면의 모드다 (R1). 신규 백엔드 모듈 0개 — 편집 연산은
`itb.execution.step_edits` 를 재사용하고(R2), 변수 파생은 `sessions.py` 에 있던 것을 도메인
계층으로 **옮긴다**(복사하지 않는다, R5).

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 비어 있다.

기록해 둘 것 하나: **원칙 V 의 Export 는 이 기능에서도 아직 구현되지 않는다.** 그것은
001 plan 이 등록한 기존 릴리스 게이트 항목이며 이 기능이 새로 만든 이연이 아니다. 이 기능은
그 게이트에 대해 두 가지 의무만 진다 — DSL 을 바꾸지 않는 것(지킨다: 위 표 I), 저장 형식을
평문으로 유지하는 것(지킨다: 위 표 V). 새 이연을 등록하지 않는다.
