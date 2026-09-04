# Implementation Plan: 결함 수정과 확정 디자인 준수

**Branch**: `001-interactive-ai-test-builder` (기존 브랜치에서 이어짐) | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-defect-fix-design-conformance/spec.md`

## Summary

1차 구현(001)이 tasks 168건을 완료했지만 실사용에서 핵심 흐름이 동작하지 않고 화면이 확정
디자인과 다르다. 이 라운드는 새 기능을 만들지 않는다 — **001 이 이미 요구한 것을 실제로
성립시킨다.**

원인은 전부 코드에서 확인했다 (research.md). 네 가지가 드러났다.

1. **중지가 세션을 파괴한다.** `stop` 이 `_WORK.pop()` 하므로 이후 저장이 구조적으로
   불가능하다. 화면을 붙잡아 두는 것만으로는 안 고쳐진다.
2. **실패가 화면에 도달하는 경로가 없다.** AI 실패 사유는 상태에 담기지만, 그것을 그리는
   컴포넌트가 세션 상태 조건 뒤에 숨어 렌더되지 않는다.
3. **422 를 계약 형태로 바꾸는 핸들러가 없다.** 앱 전체의 모든 검증 오류가 원인을 알 수
   없는 한 문장이 된다. 키 쌍 화면만의 문제가 아니다.
4. **디자인은 팔레트만 옮겨졌고 기하는 지어냈다.** 확정 디자인에 `border-radius` 가 0회인데
   구현은 `--radius: 10px` 를 쓴다. 테두리 3px→1px, 하드 오프셋 그림자 26회→0회.

기술적 접근은 **기존 스택 유지 + 최소 계약 변경 + 디자인 전사**다. Step DSL 을 건드리지
않는다. 새 엔드포인트 5개, 변경 4개, 그리고 8화면 전사가 작업의 전부다.

## Technical Context

**Language/Version**: Python 3.13 (백엔드, `requires-python >=3.12`) / TypeScript 5.x (프런트엔드)

**Primary Dependencies**: FastAPI ≥0.115, Playwright ≥1.49, Pydantic ≥2.9, PyNaCl ≥1.5, anthropic ≥0.40 / React 18, Vite

**Storage**: 로컬 평문 파일. 테스트 정의 YAML, 비밀 파일(공개키 봉인), **신규**: 레지스트리 JSON (`~/.config/itb/registry.json`), 관리 프로젝트 (`~/.local/share/itb/projects/`)

**Testing**: pytest + pytest-asyncio (백엔드), vitest + jsdom (프런트엔드), import-linter (헌법 원칙 II 강제)

**Target Platform**: 사용자 1인의 로컬 장비. 단독 로컬 도구 (001 FR-088). 서버는 `127.0.0.1` 에만 바인드

**Project Type**: 웹 애플리케이션 (backend + frontend)

**Performance Goals**: 이 라운드에 새 성능 목표 없음. 001 의 것을 유지 (Step 200개 렌더 예산 — `StepListPerformance.test.tsx` 가 지킨다)

**Constraints**:
- 헌법 v1.1.0 이 스택을 고정한다. 교체하지 않는다
- 확정 디자인 8종은 해석 대상이 아니다 (DC-001)
- 기준선 아래로 내려갈 수 없다: 백엔드 726, 프런트엔드 62 (RG-001)
- 디렉터리 탐색 API 는 사용자 홈 하위로 한정 (헌법 보안 요구)

**Scale/Scope**:
- 확정 디자인 8화면 전면 재작성 — `<div>` 677개, 인라인 `<svg>` 98개
- 독립 화면으로 분리해야 하는 것 4종 (AiRecord·RunnerPaused·Takeover·StepInspector)
- REST: 신규 5, 변경 4, 무변경 2
- 요구사항 48건 (DR 31 + DC 12 + RG 5)

## Constitution Check

*GATE: Phase 0 연구 전 통과. Phase 1 설계 후 재확인.*

### 원칙 I — Unified Step Model (NON-NEGOTIABLE)

| 확인 | 결과 |
|---|---|
| Step DSL 을 바꾸는가 | **아니다.** data-model.md 의 엔티티 6개 중 Step 을 담거나 필드를 더하는 것이 없다 |
| 새 Step 표현을 만드는가 | 아니다. `RecordingDraft` 는 기존 `SessionWork` 의 수명을 늘릴 뿐이다 |
| 화면 분리가 저장 경로를 나누는가 | 아니다. D3·D5·D6·D8 이 독립 화면이 되어도 저장은 `POST /api/sessions/{id}/save` 하나다 |
| 사람 Step 과 AI Step 이 갈라지는가 | 아니다. `authoring_mode` 는 이미 있는 메타데이터이고 실행 방식을 바꾸지 않는다 |

**통과.** `.importlinter` 의 `domain-is-pure` 계약이 계속 강제한다.

### 원칙 II — Deterministic Replay (NON-NEGOTIABLE)

| 확인 | 결과 |
|---|---|
| 재실행 경로에 언어모델이 도달 가능해지는가 | 아니다 |
| 신규 `GET /api/ai/availability` 의 위치 | `itb.api` — `.importlinter` 의 `execution-no-llm` 계약에서 `source_modules` 에 없다. 허용된 계층이다 |
| 그 엔드포인트가 언어모델을 호출하는가 | **아니다.** 자격 증명 해석 가능 여부만 본다 |
| 재실행 경로가 그것을 읽는가 | 아니다. 작성 경로 전용이다 |

**통과.** 임포트 그래프가 바뀌므로 `lint-imports` 를 매 작업 후 돌린다 (RG-004).

### 원칙 III — Stateful Interactive Runner

| 확인 | 결과 |
|---|---|
| 일시정지 중 브라우저 세션이 유지되는가 | 유지된다. 이 라운드가 건드리지 않는다 |
| `review` 상태 도입이 이를 약화시키는가 | **아니다. 강화한다.** 지금은 중지가 Step 까지 함께 버린다 |
| `review` 에서 브라우저가 없는데 실행 명령을 받는가 | 거절한다 — `409 INVALID_TRANSITION` (001 FR-043a) |

**통과.**

### 원칙 IV — Locator Resilience

이 라운드는 locator 로직을 건드리지 않는다. `locator-strategy-is-pure` 계약 유지.
D8(StepInspector)을 독립 화면으로 분리하는 것은 표시의 변화이며 해석 규칙의 변화가 아니다.

**통과 (해당 없음).**

### 원칙 V — Asset Portability

| 확인 | 결과 |
|---|---|
| Export 를 이 라운드에서 구현하는가 | 아니다. 헌법 v1.1.0 의 release-gate 항목으로 **여전히 남아 있다** |
| DSL 이 export 를 가로막는 방향으로 바뀌는가 | 아니다. DSL 을 바꾸지 않는다 |
| 저장 위치 변경이 이식성을 해치는가 | 아니다. 평문 YAML 그대로다. `~/.local/share/itb/projects/` 를 고른 이유 중 하나가 사용자가 자기 자산으로 인식하고 버전 관리에 넣게 하는 것이다 |

**통과.** 001 의 기존 deferral 을 이어받는다. 새 deferral 을 만들지 않는다.

### 보안 요구 (조직 mandate, non-negotiable)

| 요구 | 이 라운드의 대응 |
|---|---|
| 하드코딩 비밀 금지 | 신규 코드에 없음. `LlmAvailability` 는 자격 증명 조각을 담지 않는다 |
| 민감 값 마스킹·변수 참조 | 인라인 입력이 기존 경로를 그대로 쓴다. 값 반환 엔드포인트는 여전히 0개 |
| 경계에서 입력 검증 | **이 라운드가 강화한다** — `GET /api/fs/browse` 홈 경계, `POST /api/project/open` 경계, 프로젝트 이름 → 슬러그 변환 |
| 임의 셸 실행 금지 | 새 실행 능력 없음. 탐색기는 디렉터리 이름만 읽는다 |
| 오류를 명시적으로 처리 | **이 라운드의 핵심.** 전역 422 핸들러 + 조용한 실패 제거 |

**통과.** 새 공격면은 `GET /api/fs/browse` 하나이고, 홈 하위 한정·디렉터리만 반환·심볼릭
링크 재검사·숨김 제외로 좁혔다.

### 품질 게이트

| 게이트 | 대응 |
|---|---|
| 1. 원칙 준수 | 위 표. 재실행 경로 변경 없음을 `lint-imports` 로 증명 |
| 2. 왕복 무결성 | DSL·Recorder·Generator 를 바꾸지 않으므로 해당 없음 |
| 3. 테스트 동반 | 신규 엔드포인트 5개에 contract 테스트, 결함 4건에 회귀 테스트 |
| 4. 테스트 비활성화 금지 | RG-002. 문구 변경으로 인한 기대값 수정만 허용하고 근거를 남긴다 |
| 5. 성공 지표 인식 | 001 SC-001·002·005 측정은 이 라운드가 성립시키는 흐름에 달려 있다. 이 라운드 전에는 측정 자체가 불가능했다 |

**결론: 위반 없음. Complexity Tracking 을 채우지 않는다.**

### Phase 1 설계 후 재확인

설계 산출물(data-model.md, contracts/)을 작성한 뒤 위 항목을 다시 확인했다.
**새로 생긴 위반 없음.** 특히:

- `review` 세션 상태는 Step 모델이 아니라 세션 수명 주기의 변화다 (원칙 I 유지).
- `GET /api/ai/availability` 는 `itb.api` 에 있고 언어모델을 호출하지 않는다 (원칙 II 유지).
- 새 `ErrorCode` 를 만들지 않고 `DEFINITION_INVALID` 를 재사용해 계약 표면을 늘리지 않았다.
- 비밀 값 인라인 입력은 **새 엔드포인트가 0개다** — 기존 공개키 전용 경로를 그대로 쓴다.

## Project Structure

### Documentation (this feature)

```text
specs/002-defect-fix-design-conformance/
├── plan.md                       # 이 파일
├── spec.md                       # 요구사항 (DR 31 · DC 12 · RG 5 · SC 12)
├── research.md                   # Phase 0 — 원인 규명과 결정
├── data-model.md                 # Phase 1 — 엔티티 6종
├── quickstart.md                 # Phase 1 — 검증 가이드
├── contracts/
│   ├── rest-api-delta.md         # 001 계약 대비 변경분만
│   └── design-conformance.md     # 확정 디자인 8종 전사 절차 (UI 계약)
├── checklists/
│   └── requirements.md           # 명세 품질 체크리스트 (16/16 통과)
├── design-conformance/           # 구현 중 생성 — DC-012·DC-009 기록
│   ├── <Screen>.md × 8
│   └── undefined-states.md
└── tasks.md                      # Phase 2 (/speckit-tasks 가 만든다)
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── api/
│   │   ├── app.py                # 변경 — RequestValidationError 핸들러 추가
│   │   ├── state.py              # 변경 — 레지스트리·관리 위치 경로
│   │   └── routes/
│   │       ├── project.py        # 변경 — list·create(path 제거)·open(경계)·registry 삭제
│   │       ├── sessions.py       # 변경 — stop 이 파괴하지 않음, discard 신규
│   │       ├── secrets_routes.py # 변경 없음 (오류 표현은 app.py 가 처리)
│   │       ├── fs.py             # 신규 — GET /api/fs/browse
│   │       └── ai.py             # 신규 — GET /api/ai/availability
│   ├── storage/
│   │   ├── repository.py         # 변경 — 관리 위치 기준 생성
│   │   ├── registry.py           # 신규 — ProjectRegistryEntry 읽기·쓰기
│   │   └── paths.py              # 신규 — XDG 경로 결정 (~/.config/itb, ~/.local/share/itb)
│   └── (domain·locator·execution·generator·recording·mirror·llm·authoring — 변경 없음)
└── tests/
    ├── contract/                 # 신규 엔드포인트 5개
    ├── integration/              # 결함 4건의 회귀 테스트
    └── unit/                     # registry·paths·슬러그·경계 검증

frontend/
├── src/
│   ├── App.tsx                   # 변경 — 화면 상태를 8+4 로 (DC-008)
│   ├── theme/tokens.css          # 변경 — --radius 제거, 3px 테두리, 하드 그림자, 배경 #EFEBE0
│   ├── api/client.ts             # 변경 — 신규 엔드포인트 5개
│   ├── pages/                    # 전사 대상
│   │   ├── TestList.tsx          # D1
│   │   ├── CreateTest.tsx        # D2
│   │   ├── AiRecord.tsx          # D3 — 패널 → 독립 화면
│   │   ├── Runner.tsx            # D4
│   │   ├── RunnerPaused.tsx      # D5 — 패널 → 독립 화면
│   │   ├── Takeover.tsx          # D6 — 패널 → 독립 화면
│   │   ├── RunResult.tsx         # D7
│   │   ├── StepInspector.tsx     # D8 — components/ 에서 pages/ 로
│   │   ├── ProjectSetup.tsx      # 재작성 (DC-010 — 대응 디자인 없음)
│   │   ├── KeyManagement.tsx     # 시각 언어 정렬 + 제약 안내 (DR-029)
│   │   ├── SecretValues.tsx      # 시각 언어 정렬 (유지, DR-027)
│   │   └── TestDefinition.tsx    # 시각 언어 정렬
│   └── components/               # 전사 결과에 맞춰 정리
└── tests/                        # 문구 변경분만 기대값 수정 (근거 기록)

scripts/
└── design_baseline.py            # 신규 — dc.html 에서 기준값 추출, 대조표 골격 생성
```

**Structure Decision**: 001 이 정한 backend/frontend 2 프로젝트 구조를 그대로 쓴다.
신규 파일은 5개(`registry.py`, `paths.py`, `fs.py`, `ai.py`, `design_baseline.py`)뿐이고
나머지는 기존 파일의 변경이다. 결함 수정 라운드이므로 구조를 바꿀 이유가 없다.

`StepInspector.tsx` 만 `components/` → `pages/` 로 옮긴다. `canvas.json` 이 독립 artboard
로 정의했고 DC-008 이 독립 화면을 요구하기 때문이다.

## 구현 순서와 의존 관계

작업 순서에 하나의 강제 관계가 있다.

```
전역 422 핸들러 (DR-022·DR-030)
        │
        ├──▶ 키 쌍 생성 (DR-028~031)
        │            │
        │            └──▶ 비밀 값 인라인 입력의 탈출구 (DR-025)
        │
        └──▶ 그 밖의 모든 검증 오류 표시
```

**DR-028 은 DR-025 의 선행 조건이다.** 키 생성이 고쳐지지 않으면 "공개키가 없을 때 그
자리에서 만들기"가 막힌다 (contracts/rest-api-delta.md §9).

그 외에는 독립적이다. 디자인 전사(DC)는 결함 수정(DR)과 병렬로 진행할 수 있으나,
**같은 파일을 건드리는 경우 전사를 먼저 한다** — 전사는 파일을 통째로 다시 쓰므로
나중에 하면 앞선 수정을 덮는다. 특히:

| 파일 | 전사(DC) | 결함 수정(DR) | 순서 |
|---|---|---|---|
| `pages/Runner.tsx` | D4 | DR-010 (중지) | 전사 → 수정 |
| `pages/AiRecord.tsx` | D3 | DR-016~020 | 전사 → 수정 |
| `pages/CreateTest.tsx` | D2 | DR-021 | 전사 → 수정 |
| `pages/ProjectSetup.tsx` | DC-010 재작성 | DR-001~009 | 함께 |
| `pages/KeyManagement.tsx` | DC-010 정렬 | DR-029 | 함께 |

백엔드 작업(레지스트리·탐색기·세션 수명·422 핸들러)은 프런트엔드와 독립이므로 병렬
가능하다.

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 채우지 않는다.

001 의 Export deferral 은 이 라운드가 이어받으며, 헌법 v1.1.0 의 release-gate 항목으로
여전히 등록되어 있다. **새 deferral 을 추가하지 않는다.**
