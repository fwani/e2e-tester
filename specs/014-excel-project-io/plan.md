# Implementation Plan: 엑셀로 프로젝트 내보내기·가져오기

**Branch**: `014-excel-project-io` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-excel-project-io/spec.md`

## Summary

프로젝트 ↔ 스프레드시트(`.xlsx`)의 두 방향 통로를 만든다.

**내보내기**는 열린 프로젝트를 워크북 하나로 만든다 — 그룹 하나가 시트 하나, 테스트 하나가 행 하나,
컬럼 7개 고정. 최근 실행 결과를 함께 싣고 민감 값은 싣지 않는다. 서버가 `openpyxl` 로 만들어
`Content-Disposition` 과 함께 내려보내고, 프론트는 blob 으로 받아 저장한다.

**가져오기**는 두 걸음이다. 미리보기가 파일을 해석해 **계획**을 메모리에 만들고 무엇이 생길지
보여 준다. 확정하면 그룹과 **초안**이 만들어진다. 초안은 테스트가 아니다 — 스텝이 없고 실행할 수
없으며 `drafts/` 에 따로 산다. 사용자가 초안을 골라 **기존 AI 작성 경로**로 녹화하고, 저장하는
순간 정식 테스트가 되고 초안은 사라진다.

핵심 설계 판단은 **"엑셀은 테스트의 두 번째 표현이 아니다"** 이다. 가져오기가 `Test` 를 직접
만들지 않는 것, 초안에 `steps` 필드가 아예 없는 것, `itb.portability` 가 `itb.authoring` 을
임포트하지 못하게 계약으로 막는 것 — 셋 다 같은 판단에서 나온다 (헌법 원칙 I).

## Technical Context

**Language/Version**: Python 3.12+ (백엔드), TypeScript 5.7 / React 19 (프론트엔드)

**Primary Dependencies**: FastAPI, Pydantic v2, PyYAML, Playwright — 기존 그대로.
**신규 1개**: `openpyxl` (읽기·쓰기 겸용, 순수 Python). 프론트엔드 신규 의존성 **없음**.

**Storage**: 파일시스템. `<프로젝트>/drafts/D-####-<slug>.yaml` 신규,
`itb-project.yaml`·`tests/*.yaml` 은 기존 형식 유지 (`Test` 에 선택 필드 2개 추가).
가져오기 계획은 서버 메모리에만 30분 존재하고 디스크에 쓰지 않는다.

**Testing**: pytest (`unit` / `contract` / `integration` / `e2e` / `abnormal`), vitest + Testing Library.
`lint-imports`(import-linter), `ruff`, `tsc --noEmit`, `python -m itb.schema.export --check`.

**Target Platform**: 로컬에서 도는 데스크톱 웹앱 (FastAPI + Vite dev server).

**Project Type**: 웹 애플리케이션 (backend + frontend 분리).

**Performance Goals**: 테스트 100건·그룹 10개 내보내기 10초 이내 (SC-002).
가져오기 5,000행 해석은 `read_only` 스트리밍으로 메모리 상수.

**Constraints**:
- 파일 100MB · 압축해제 500MB · 시트 200 · 전체 행 5,000 (이 기능 고유 상한)
- 프로젝트 테스트 999 (**기존 상한. 새로 만들지 않고 공유한다** — FR-036c)
- 재생 경로에서 LLM 도달 불가 (헌법 원칙 II, import-linter 가 강제)
- 프론트엔드 런타임 의존성은 React 둘로 유지

**Scale/Scope**: 백엔드 신규 패키지 1개(모듈 6개) + 신규 라우터 2개 + 기존 라우터 2곳 수정,
프론트엔드 신규 화면 2개 + 기존 화면 2곳 수정. 신규 엔드포인트 8개.

## Constitution Check

*GATE: Phase 0 이전에 통과해야 하고, Phase 1 설계 후 다시 본다.*

### 초기 평가 (Phase 0 이전)

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. 단일 스텝 모델** (NON-NEGOTIABLE) | ✅ 통과 | 가져오기가 `Test` 를 만들지 않는다. 실행 가능한 테스트는 오직 기존 녹화 경로에서만 생긴다. 스프레드시트는 **입력**이고 워크북은 **파생 산출물**이다 — 어느 쪽도 테스트의 저장 형태가 아니다 |
| **II. 결정적 재생** (NON-NEGOTIABLE) | ✅ 통과 | LLM 은 작성 국면에서만 쓰인다. 초안은 그 국면의 입력일 뿐이고, 저장된 테스트를 실행하는 경로에 초안·워크북·`itb.portability` 어느 것도 관여하지 않는다 |
| **III. 상태 유지 러너** | ✅ 해당 없음 | 세션 상태 기계를 바꾸지 않는다. `draft_id` 는 세션 생성 입력이며 새 상태나 전이를 만들지 않는다 |
| **IV. Locator 탄력성** | ✅ 해당 없음 | 초안은 `target` 을 만들지 않는다. 후보 묶음은 녹화가 실제 DOM 에서 수집한다 — 표의 글로 만들어낼 수 없고, 만들어내려 하지도 않는다 |
| **V. 자산 이식성** | ✅ 통과 (주의 1건) | `.xlsx` 는 저장 형식이 아니라 파생 산출물이다. 정본은 `tests/*.yaml` 그대로다. 초안도 사람이 읽는 YAML 로 저장하고 버전 관리 대상에 둔다. **주의**: 아래 참조 |

**원칙 V 에 관한 주의 — 이름이 같지만 다른 것이다.**

헌법 원칙 V 가 말하는 Export 는 **표준 Playwright 프로젝트로 내보내기**이고, 릴리스 게이트
RG-1 로 등록돼 있다. 이 기능의 「엑셀로 내보내기」는 그것이 **아니다**.

- 이 기능은 RG-1 을 해소하지 **않는다**. RG-1 은 그대로 미해결로 남는다.
- 이 기능은 RG-1 을 새로 미루지도 **않는다**. 이연을 더하지 않으므로 Incremental delivery 규칙의
  적용 대상이 아니다.
- 화면과 문서에서 두 기능의 이름이 섞이지 않도록 한다. 「엑셀로 내보내기」와
  「Playwright 로 내보내기」는 나란히 있게 되며, 후자는 지금처럼 비활성 상태로 남는다.

### 보안 요구사항

| 요구 | 대응 |
|---|---|
| 민감값 비노출 | 내보내기는 Step 의 `label` 과 변수 **참조**만 싣는다. `Variable.value` 를 읽지 않는다. `secrets/` 를 임포트하지 않는 것으로 구조적으로 보장하고, 민감 변수를 포함한 프로젝트로 검사 테스트를 둔다 (SC-008) |
| 경계 입력 검증 | 업로드 바이트 → 압축 해제 총량 → 구조 상한 3겹 (research R3). 셀 값은 전부 도메인 모델의 `max_length`·패턴을 통과해야 초안이 된다 (FR-037) |
| 수식 주입 | `= + - @` 로 시작하는 셀 값 앞에 `'` 를 붙여 텍스트로 고정 (research R13). 내보낸 파일은 남이 연다 |
| zip 폭탄 | `ZipFile.infolist()` 로 열기 전에 압축 해제 총량과 압축비를 검사 |
| 하드코딩 비밀 | 없음. 새 자격 증명·키를 도입하지 않는다 |
| 명시적 오류 처리 | 새 오류 코드 7개 전부 `CATEGORY`·`NEXT_ACTION` 표에 등록. `test_error_contract.py` 가 누락을 잡는다 |

### 품질 게이트

| 게이트 | 계획 |
|---|---|
| 1. 원칙 준수 | 재생 경로 무관함을 `lint-imports` 로 증명한다 — `itb.portability` 를 `execution-no-llm` 계약의 `source_modules` 에 **추가**한다 |
| 2. 왕복 무결성 | Step DSL·Recorder·Generator 를 바꾸지 않으므로 기존 왕복은 영향받지 않는다. `Test` 필드 2개 추가는 스키마 재생성 + 기존 왕복 테스트로 확인한다. **엑셀 왕복은 무손실이 아니며**, spec 이 이를 명시적으로 범위 밖에 둔다 |
| 3. 테스트 동반 | 단위(시트 이름 변환·컬럼 대조·수식 이스케이프·번호 재부여), 계약(엔드포인트 8개), 통합(전부-아니면-전무 되돌림·수용량 거절·민감값 누출), e2e(사용자 이야기 3개), 프론트(화면 2개 + 기존 2곳) |
| 4. 비활성 테스트 금지 | 없음 |
| 5. 성공지표 인지 | 테스트 작성 흐름(PRD §18)에 새 진입점이 생긴다. 초안 경로의 저장 성공률을 기존 AI 작성과 같은 방식으로 볼 수 있어야 한다 |

### 재평가 (Phase 1 설계 후)

설계를 마친 뒤 다시 확인했다. **판정 변화 없음.**

설계에서 원칙을 지키려고 실제로 내린 결정 셋:

1. `Draft` 에 `steps` 필드를 **두지 않았다.** 두면 "스텝 0개짜리 테스트"가 되고, 그 순간
   `Test` 의 `min_length=1` 을 우회하는 두 번째 테스트 표현이 생긴다 (원칙 I).
2. `itb.portability` 를 `execution-no-llm` 계약에 **추가했다.** 가져오면서 바로 AI 를 돌리는
   지름길이 나중에 생기지 않도록, 주석이 아니라 빌드가 막는다 (원칙 I·II).
3. 초안 세션에 새 모드를 만들지 않고 `POST /api/sessions` 에 `draft_id` 만 더했다.
   상태 기계에 갈래를 늘리지 않는다 (원칙 III).

## Project Structure

### Documentation (this feature)

```text
specs/014-excel-project-io/
├── plan.md              # 이 파일
├── spec.md
├── research.md          # Phase 0 — 결정 14건
├── data-model.md        # Phase 1 — Draft·Test 확장·계획·워크북·오류코드·원자성
├── quickstart.md        # Phase 1 — 손으로 확인하는 방법
├── contracts/
│   └── rest-api.md      # Phase 1 — 신규 8개 + 기존 3곳 변경
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks 산출물 (아직 없음)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                      # [수정] openpyxl 추가
├── schema/
│   ├── step-dsl.schema.json            # [재생성] Test.description·actor
│   ├── draft.schema.json               # [신규]
│   └── error-response.schema.json      # [재생성] 오류 코드 7개
├── src/itb/
│   ├── domain/
│   │   ├── draft.py                    # [신규] Draft, DraftSource, 지시문 조립
│   │   ├── test_case.py                # [수정] Test.description·actor, MAX_TEST_NUMBER
│   │   └── error.py                    # [수정] 오류 코드 7개 + 두 표
│   ├── portability/                    # [신규 패키지]
│   │   ├── limits.py                   #   이 기능 고유 상한
│   │   ├── columns.py                  #   7개 컬럼 단일 출처
│   │   ├── sheet_name.py               #   그룹 이름 ↔ 시트 이름 (순수)
│   │   ├── workbook.py                 #   openpyxl 과 닿는 유일한 지점
│   │   ├── exporter.py                 #   Project + Test[] + 결과 → 행
│   │   └── importer.py                 #   워크북 → ImportPlan
│   ├── storage/
│   │   ├── drafts.py                   # [신규] 초안 읽기·쓰기·목록·삭제
│   │   ├── repository.py               # [수정] drafts 경로, MAX_TEST_NUMBER 참조
│   │   └── test_moves.py               #   (변경 없음 — run_all 을 그대로 쓴다)
│   └── api/
│       ├── app.py                      # [수정] 라우터 2개 등록
│       ├── state.py                    # [수정] 가져오기 계획 보관소
│       └── routes/
│           ├── excel.py                # [신규] export / import preview·commit·create-project
│           ├── drafts.py               # [신규] 초안 목록·조회·삭제
│           ├── sessions.py             # [수정] draft_id, 저장 시 번호 부여·초안 삭제
│           ├── tests.py                # [수정] draft_count, MAX_TEST_NUMBER 참조
│           └── project.py              # [수정] export 엔드포인트
└── tests/
    ├── unit/          test_sheet_name.py · test_excel_columns.py · test_formula_escape.py
    ├── contract/      test_excel_export_api.py · test_excel_import_api.py · test_drafts_api.py
    ├── integration/   test_import_atomicity.py · test_import_capacity.py
    │                  test_export_no_secrets.py · test_draft_to_test.py
    ├── e2e/           test_us7_excel_export.py · test_us8_excel_import.py
    │                  test_us9_draft_recording.py
    └── abnormal/      (기존 test_error_contract.py 가 새 코드를 자동으로 검사)

frontend/
├── src/
│   ├── types/generated/                # [재생성] step-dsl.d.ts, error-response.d.ts, draft.d.ts
│   ├── api/client.ts                   # [수정] excel·drafts 네임스페이스, blob 내려받기
│   ├── pages/
│   │   ├── ImportPreview.tsx           # [신규] 미리보기 + 시트별 접두어 입력
│   │   ├── DraftList.tsx               # [신규] 초안 목록 + 녹화 시작
│   │   ├── ProjectSetup.tsx            # [수정] 「엑셀에서 새 프로젝트」 진입점
│   │   ├── TestList.tsx                # [수정] 내보내기·가져오기 진입점, 초안 영역
│   │   └── ComposeView.tsx             # [수정] 초안에서 온 지시문 미리 채우기
│   └── App.tsx                         # [수정] 화면 전환 2개
└── tests/
    ├── ExcelExport.test.tsx · ImportPreview.test.tsx
    ├── DraftList.test.tsx · DraftToRecording.test.tsx
    └── abnormal/excel-blockers.test.tsx

backend/.importlinter                    # [수정] execution-no-llm 에 itb.portability 추가
```

**Structure Decision**: 기존 backend/frontend 2분할을 그대로 따른다. 새 최상위 패키지
`itb.portability` 를 만드는 이유는 research R2 에 있다 — 남의 파일 형식을 다루는 코드를
우리 자산 형식을 다루는 `itb.storage` 와 섞으면 "정본이 무엇인가"가 코드 배치에서 흐려지고,
그것은 원칙 V 가 걸린 지점이다. 초안 **저장**은 우리 형식이므로 `itb.storage.drafts` 에 둔다.

## 구현 순서

사용자 이야기 우선순위를 따르되, 공유 기반을 먼저 둔다. 각 묶음은 독립적으로 검증 가능하다.

| 단계 | 내용 | 검증 |
|---|---|---|
| **0. 기반** | `MAX_TEST_NUMBER` 정리, `Test` 필드 2개, 오류 코드 7개, 스키마·타입 재생성, `.importlinter` 수정, `openpyxl` 추가 | 기존 테스트 전부 통과 + `lint-imports` + `schema.export --check` |
| **1. 내보내기** (US1) | `columns`·`sheet_name`·`workbook`·`exporter`, `GET /api/project/export`, 프론트 blob 내려받기 | US1 시나리오 6개 |
| **2. 가져오기 해석** (US2 전반) | `importer`, 3겹 방어, 계획 보관소, `POST /api/import/preview` | 미리보기 계약 + 거절 경로 |
| **3. 가져오기 확정** (US2 후반) | `Draft` 모델, `storage/drafts`, `run_all` 원자성, commit·create-project, 미리보기 화면 | US2 시나리오 14개, 되돌림 통합 테스트 |
| **4. 초안 녹화** (US3) | `draft_id` 세션, 지시문 조립, 저장 시 번호 부여·초안 삭제, 초안 목록 화면 | US3 시나리오 6개 |
| **5. 마감** (US4) | 머리글 고정·열 너비·결과 칸 서식 | US4 시나리오 2개 |

## Complexity Tracking

> 헌법 위반은 없다. 아래는 **단순함(Simplicity) 기준으로 정당화가 필요한 추가**다.

| 추가한 것 | 왜 필요한가 | 기각한 더 단순한 대안 |
|---|---|---|
| 런타임 의존성 `openpyxl` | `.xlsx` 는 zip + XML 이다. 손으로 쓰고 읽는 것은 이 기능 자체보다 큰 일이 된다 | CSV 로 대체 — 시트=그룹이라는 이 기능의 뼈대가 CSV 에 없다. 프론트에서 SheetJS — 프론트 의존성 방침과 어긋나고 민감값 판단을 브라우저로 옮기게 된다 |
| 최상위 패키지 `itb.portability` | 남의 형식을 다루는 코드가 `itb.storage` 에 섞이면 정본이 무엇인지 코드 배치에서 흐려진다 (원칙 V) | `itb.storage.excel` 로 두기 — 위 이유로 기각 |
| 새 도메인 개념 `Draft` | 표의 글로는 실행 가능한 테스트를 만들 수 없다. `Test` 로 저장하려면 `steps` 의 `min_length=1` 과 `target` 후보 묶음을 가짜로 채워야 하고, 그것은 원칙 I·IV 를 동시에 깬다 | 스텝 하나짜리 껍데기 `Test` 만들기 — 실행하면 의미 없이 실패하는 테스트가 목록에 쌓인다. 가져오기를 미리보기까지만 하고 사람이 손으로 만들기 — 그러면 이 기능의 가치 대부분이 사라진다 |
| 계획 보관소 (메모리 30분) | 확정 전에 아무것도 만들지 않아야 하는데(FR-016), 확정 때 파일을 다시 올리게 하면 미리보기에서 본 것과 같은 파일이라는 보장이 없다 | 확정 시 파일 재업로드 — 위 이유. 임시 파일로 디스크 보관 — 정리 책임이 생기고 두 번째 임시 저장 개념이 된다 |
| 프론트 신규 화면 2개 | 미리보기는 시트별 결정을 받아야 하고, 초안 목록은 "다음에 무엇을 녹화할지"를 보여야 한다(FR-035) | 모달로 처리 — 시트가 200개까지 올 수 있어 모달에 담기지 않는다 |

**이연(deferral) 없음.** 헌법 Incremental delivery 규칙의 적용 대상이 아니다.
기존 릴리스 게이트 RG-1(Playwright Export)은 이 기능과 무관하게 그대로 남는다.

## 계획 중 발견한 명세의 빈틈

구현이 임의로 정하지 않도록 여기에 적어 두고, `spec.md` 에도 반영했다.

| 발견 | 내용 | 조치 |
|---|---|---|
| FR-006 이 실행 결과를 세 가지로만 다룬다 | 제품의 `Outcome` 은 `pass`·`fail`·`stopped`·`partial_pass` 네 값이다. 뒤 둘을 `P`/`F` 로 접으면 보고서에 거짓이 실린다 | research R5 에서 다섯 표기로 정하고 FR-006 을 보완했다 |
| 999 가 매직 넘버로 두 곳에 박혀 있다 | FR-036c 는 "값이 같다"가 아니라 "출처가 하나다"를 요구한다 | `MAX_TEST_NUMBER` 로 끌어올리고 기존 두 곳을 고친다 (data-model §4) |
