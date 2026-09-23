# Implementation Plan: 프로젝트·테스트 공유용 내보내기·가져오기

**Branch**: `019-project-test-sharing` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-project-test-sharing/spec.md`

## Summary

프로젝트 또는 고른 테스트를 **평문 YAML 묶음 파일 하나**로 내보내고, 그 파일을 받아 **실행 가능한
상태까지** 복원한다.

**내보내기**는 `Test` 모델을 그대로 직렬화한다. 요약을 담은 매니페스트 아래에 테스트 정의가
있는 그대로 들어간다 — 스텝, 로케이터 후보 전부, 검증 스텝, 변수 선언. 민감 값은 들어가지
않는데, 그것이 선택의 결과가 아니라 **구조의 결과**다: `Variable` 모델이 `sensitive=True` 인
변수에 값을 허용하지 않고(`_no_plaintext_secret`), 묶음을 만드는 `itb.sharing` 은 import-linter
계약으로 `itb.secrets` 를 임포트하지 못한다. 담고 싶어도 담을 경로가 없다.

**가져오기**는 두 걸음이다 — 014 엑셀 통로가 쓰는 계획·확정 구조를 그대로 따른다. 파일을 올리면
서버가 해석해 **계획**을 메모리에 만들고 무엇이 생길지 보여 준다. 확정하면 새 프로젝트를 만들거나
열린 프로젝트에 테스트를 더한다. 확정 전에는 디스크에 아무것도 쓰지 않는다.

**값 인계**는 값을 옮기지 않고 **요구를 옮긴다.** 묶음에는 채워야 할 변수의 이름·민감 여부와
쓰이는 자리만 있다. 가져오기 결과가 그 목록을 「어느 테스트의 어느 스텝에서 쓰인다」와 함께
보여 주고, 받은 사람이 그 자리에서 값을 채운다 — 민감한 것은 **자기 키로** 봉인되고(기존
`PUT /api/secrets/{name}` 이 하던 일 그대로), 비민감한 것은 테스트 정의에 기록된다. 민감 값이
비면 세션 생성 시점에 막히고, 비민감 빈 값은 경고에 그친다.

선언이 없는 `{{변수}}` 참조는 **거부하지 않고 보충한다** — `Test._check_refs` 보다 먼저 도는
단계가 빈 자리를 드러내 사용자가 채울 수 있게 한다 (FR-047).

핵심 설계 판단은 **"묶음은 테스트의 두 번째 표현이 아니라 같은 표현을 담는 봉투다"** 이다.
묶음 안의 테스트를 별도 모델로 다시 정의하지 않고 `Test` 를 그대로 싣는 것, 가져오기가 `Test`
검증을 통과한 것만 저장하는 것, `itb.sharing` 이 `itb.authoring`·`itb.llm`·`itb.secrets` 를
임포트하지 못하게 막는 것 — 셋 다 같은 판단에서 나온다 (헌법 원칙 I·II, 보안 요건).

## Technical Context

**Language/Version**: Python 3.12+ (백엔드), TypeScript 5.7 / React 19 (프론트엔드)

**Primary Dependencies**: FastAPI, Pydantic v2, PyYAML — 기존 그대로. **신규 의존성 없음.**
묶음이 YAML 이므로 014 가 들여온 `openpyxl` 도 쓰지 않는다.

**Storage**: 파일시스템. 기존 구조를 그대로 쓴다 — `itb-project.yaml`, `tests/*.yaml`,
`secrets.local.yaml`. 묶음 파일은 사용자가 받아 가는 산출물이며 도구가 보관하지 않는다.
가져오기 계획은 서버 메모리에만 30분 존재하고 디스크에 쓰지 않는다.

**Testing**: pytest (`unit` / `contract` / `integration` / `e2e` / `abnormal`), vitest + Testing Library.
`lint-imports`(import-linter), `ruff`, `tsc --noEmit`, `python -m itb.schema.export --check`.

**Target Platform**: 로컬에서 도는 데스크톱 웹앱 (FastAPI + Vite dev server).

**Project Type**: 웹 애플리케이션 (backend + frontend 분리).

**Performance Goals**: 테스트 50건 내보내기·가져오기 각각 10초 이내, 화면 정지 구간 없음 (SC-008).
묶음 해석은 상한이 있는 단일 문서 파싱이므로 메모리 유계.

**Constraints**:

- 묶음 파일 20MB · 테스트 2,000건 · YAML 별칭(anchor/alias) 금지 (이 기능 고유 상한)
- 그룹당 테스트 번호 999 (**기존 상한. 새로 만들지 않고 참조한다** — `MAX_TEST_NUMBER`)
- 민감 값은 묶음에 어떤 형태로도 들어갈 수 없다 (import-linter 계약으로 강제)
- 재생 경로에서 LLM 도달 불가 (헌법 원칙 II, import-linter 가 강제)
- 가져오기는 전부 아니면 전무 (`itb.storage.test_moves.run_all` 재사용)
- 프론트엔드 신규 런타임 의존성 없음

**Scale/Scope**: 백엔드 신규 패키지 1개(모듈 7개) + 신규 라우터 1개(엔드포인트 6개) +
기존 모듈 5곳 수정. 프론트엔드 신규 화면 2개 + 신규 라우트 2개 + 기존 진입점 2곳 수정.
신규 JSON 스키마 1개.

## Constitution Check

*GATE: Phase 0 이전에 통과해야 하고, Phase 1 설계 후 다시 본다.*

### 초기 평가 (Phase 0 이전)

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | 통과 | 묶음은 `Test` 를 **그대로** 직렬화한다. 스텝의 두 번째 표현을 만들지 않는다. 가져온 테스트는 `Test` 검증을 통과한 것만 저장된다. 출처 표시(FR-028)는 원칙이 명시적으로 허용하는 **메타데이터**이며 스텝 실행에 관여하지 않는다. |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 통과 | `itb.sharing` 은 언어모델 경계에 닿지 않는다. `.importlinter` 의 `execution-no-llm` 계약 `source_modules` 에 `itb.sharing` 을 추가해 구조로 막는다. |
| **III. Stateful Interactive Runner** | 해당 없음 | 러너 상태 기계를 건드리지 않는다. 세션 생성 **직전**에 민감 값 유무를 검사할 뿐이며, 이미 살아 있는 세션의 수명에 관여하지 않는다. |
| **IV. Locator Resilience** | 통과 | 묶음은 로케이터 후보를 **전부** 옮긴다. 축약·선별하지 않는다. 축약하면 받은 쪽의 복원력이 보낸 쪽보다 낮아진다. |
| **V. Asset Portability** | 통과 (영향 없음) | 묶음은 문서화된 평문 YAML 이다. DSL 을 바꾸지 않으므로 Playwright Export 가능성을 좁히지 않는다. **이 기능은 원칙 V 의 Export 가 아니다** — 릴리스 게이트에 등록된 그 항목은 그대로 미해결로 남는다 (아래 참조). |

### 보안 요건 대조 (헌법 §Technology & Security Constraints)

| 요건 | 이 기능에서의 이행 |
|---|---|
| 하드코딩 비밀 금지 | 묶음 형식에 값 자리가 없다. 테스트 픽스처도 이름만 쓴다. |
| 민감 값은 변수 참조로만, 어디서든 마스킹 | `Variable._no_plaintext_secret` 이 스키마 수준에서 막는다. 더해 `itb.sharing` → `itb.secrets` 임포트를 계약으로 금지해 **암호문조차 들어올 경로를 없앤다**. |
| 모든 외부 입력은 경계에서 검증 | 묶음 파일은 ① 바이트 상한 ② YAML 별칭 금지 로더 ③ Pydantic 모델 ④ 선언 보충 ⑤ `Test` 도메인 검증 의 다섯 겹을 통과해야 한다. 보충(④)은 검증을 무르게 하지 않는다 — 빈 자리를 드러낼 뿐이고, 민감 값이 비면 실행이 막힌다. |
| 생성 코드는 데이터로 취급 | 해당 없음 (코드를 생성하지 않는다). |
| 오류는 명시적으로, 조용한 통과 금지 | 읽을 수 없는 정의·모르는 스텝 종류·상한 초과는 전부 사유와 함께 보고된다. 부분 복원을 하지 않는다. |
| 임의 셸 실행 금지 | 해당 없음. |

### 품질 게이트 대조 (헌법 §Development Workflow & Quality Gates)

- **게이트 2 (왕복 무결성)**: 이 기능이 새로운 왕복을 만든다 — `record → store → export bundle →
  import → replay`. SC-003 이 그 게이트다. `tests/e2e` 에 이 왕복 시나리오를 둔다.
- **게이트 3 (테스트 동반)**: 묶음 생성·해석·계획·확정 각각 단위 테스트, 사용자 흐름마다
  통합·e2e 시나리오. 기존 `tests/abnormal` 관례를 따라 손상 파일·상한 초과·권한 실패를 둔다.
- **게이트 4 (테스트 비활성화 금지)**: 해당 사항 없음.

### 성공 지표 영향 (헌법 §Quality Gates 5)

이 기능은 **재생 경로 앞에 선행 차단을 넣는다** (`POST /api/sessions`, `mode` 가 `replay`·
`rerecord` 일 때 민감 값이 비면 409). PRD §18 의 Replay Success Rate 에 대한 영향은 다음과 같다.

- 차단은 **실행 실패가 아니라 실행 시도의 거절**이므로 성공률의 **분모에 들어가지 않는다.**
  값이 없어 로그인에서 깨지던 실행이 통계에서 빠지므로 측정값은 **올라가는 방향**이다.
- 지표를 집계할 때 409 거절을 실패로 세면 반대 방향으로 왜곡된다. 집계 기준에 "세션이 만들어진
  실행만 센다" 를 명시해야 한다.
- 인수인계 복구(Takeover Recovery) 지표에는 영향이 없다 — 세션이 만들어지기 전에 걸린다.

### 이연 상태 확인 (헌법 §Governance — Incremental delivery)

기존에 등록된 이연 항목은 **원칙 V 의 Playwright Export** 하나이며, 이 기능은 그것을 회수하지
**않는다.** 이름이 비슷해 혼동되기 쉬우므로 명시한다 — 공유 묶음은 제품으로 돌아오기 위한
산출물이고, 원칙 V 의 Export 는 제품 없이 실행하기 위한 산출물이다. 릴리스 게이트 항목은 그대로
남는다. **이 기능은 새 이연을 만들지 않는다.**

### 재평가 (Phase 1 설계 후)

Phase 1 산출물([data-model.md](data-model.md), [contracts/rest-api.md](contracts/rest-api.md),
[quickstart.md](quickstart.md))을 놓고 다시 본 결과 **판정 변화 없음**. 설계가 원칙을 더
강하게 만든 지점이 두 곳이다.

1. `itb.sharing` 이 `itb.secrets` 를 임포트하지 못하게 한 계약 — 「담지 않는다」는 약속을
   코드 구조가 지킨다. 리뷰어의 주의력에 의존하지 않는다.
2. 묶음 안 테스트를 `Test` 로 다시 검증하는 것 — 받은 쪽에 원칙 I 을 위반하는 모양이
   들어올 수 없다. 검증을 통과하지 못하면 가져오기 전체가 서지 않는다.

**분석(analyze) 후 반영된 변경 1건**: 선언 없는 `{{변수}}` 참조를 거부하지 않고 보충하기로
했다 (FR-047). 스펙 Edge Case 와 data-model 의 검증 순서가 서로 다른 답을 주던 지점이었다.
보충은 원칙 I 을 무르게 하지 않는다 — 보충된 뒤에도 `Test` 검증을 그대로 통과해야 하고,
민감 변수라면 값이 채워지기 전까지 실행이 막힌다. 같은 판단에서 **비민감 변수의 빈 값도**
가져오는 사람이 채울 목록에 함께 올린다 (FR-040·FR-048).

## Project Structure

### Documentation (this feature)

```text
specs/019-project-test-sharing/
├── plan.md              # 이 파일
├── research.md          # Phase 0 산출물
├── data-model.md        # Phase 1 산출물
├── quickstart.md        # Phase 1 산출물
├── contracts/
│   └── rest-api.md      # Phase 1 산출물
├── checklists/
│   └── requirements.md  # specify 산출물
└── tasks.md             # Phase 2 산출물 (/speckit-tasks 가 만든다)
```

### Source Code (repository root)

```text
backend/
├── schema/
│   └── share-bundle.schema.json          # 신규 — 묶음의 정본 스키마 (교차 언어 의무)
├── src/itb/
│   ├── sharing/                          # 신규 패키지
│   │   ├── __init__.py
│   │   ├── bundle.py                     # 묶음 모델 (ShareBundle, BundleProject, RequiredValue)
│   │   ├── builder.py                    # 프로젝트·테스트 → 묶음 + 내보내기 검토 요약
│   │   ├── reader.py                     # 바이트 → 묶음 (상한·별칭 금지·검증)
│   │   ├── planner.py                    # 묶음 + 대상 프로젝트 → 가져오기 계획
│   │   ├── applier.py                    # 계획 확정 → 결과 (원자적)
│   │   ├── limits.py                     # 이 기능 고유 상한
│   │   └── plan_store.py                 # 메모리 계획 보관소 (TTL 30분)
│   ├── api/routes/
│   │   └── sharing.py                    # 신규 라우터 — /api/share/*
│   ├── domain/test_case.py               # 수정 — Test.imported_from (선택 필드)
│   ├── api/routes/sessions.py            # 수정 — 세션 생성 전 민감 값 유무 검사
│   └── api/routes/tests.py               # 수정 — 테스트별 준비 상태 조회
└── tests/
    ├── unit/test_sharing_*.py
    ├── contract/test_sharing_api.py
    ├── integration/test_sharing_roundtrip.py
    ├── abnormal/test_sharing_bad_bundle.py
    └── e2e/test_share_roundtrip.py

frontend/src/
├── pages/
│   ├── ShareExport.tsx                   # 신규 — 내보내기 확인 (US1·US4)
│   └── ShareImport.tsx                   # 신규 — 가져오기 계획·결과·민감 값 (US2·US3·US5)
├── app/routes/
│   ├── ShareExportRoute.tsx              # 신규
│   └── ShareImportRoute.tsx              # 신규
├── pages/TestList.tsx                    # 수정 — 「공유용 내보내기」 진입점
├── app/routes/ProjectsRoute.tsx          # 수정 — 「공유 파일에서 가져오기」 진입점
└── types/generated/share-bundle.d.ts     # 생성물 (gen:types)

backend/.importlinter                     # 수정 — 계약 2건 추가
```

**Structure Decision**: 기존 웹 애플리케이션 구조(backend + frontend)를 그대로 따른다.
새 패키지를 `itb.portability`(엑셀) 옆에 `itb.sharing` 으로 따로 두는 이유는
[research.md](research.md) R8 에 있다 — 둘은 다루는 것이 다르고(설계서 vs 실행 가능한 정의),
같은 패키지에 두면 엑셀 경로가 스텝을 다루게 되는 길이 열린다.

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 정당화할 항목이 없다.

기록해 둘 판단이 하나 있다. 계획 보관소(`plan_store.py`)가 `itb.portability` 에 이미 있는 것과
모양이 같다. 제네릭으로 합치는 대신 **따로 둔다** — 담는 것이 다르고(`ParsedWorkbook` vs
`ShareBundle`), 합치려면 기존 엑셀 경로를 건드려야 하며, 얻는 것은 40줄 남짓이다. 상한값은
각자의 `limits.py` 에 두되 의미가 같은 값(TTL 30분, 동시 계획 8개)은 같은 근거를 주석으로
적어 둔다. 이것은 원칙 위반이 아니라 중복 허용의 기록이다.
