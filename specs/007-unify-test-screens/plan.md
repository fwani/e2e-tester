# Implementation Plan: 네 화면을 하나로 — 통합 작업 화면과 국면별 조작 권한

**Branch**: `007-unify-test-screens` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-unify-test-screens/spec.md`

## Summary

사용자는 "측정 · 결과보기 · 실행 · 편집 페이지가 다 달라서 사용성이 떨어진다" 고 말했다.
코드에서 확인한 것은 Step 목록을 그리는 구현이 **4벌**, Step 상세가 **2벌**이며, 편집
국면만 화면 껍데기 자체가 다르고, 결말 표식의 자리가 국면에 따라 **좌우로 반대**라는 것이다.

**기술적 접근**: 표시와 소유를 분리한다. 하나의 표시 컴포넌트(`Workbench`)가 3층 구조 ·
단일 Step 목록 · 단일 Step 상세를 그리고, 국면별 데이터 소유는 세 어댑터
(`SessionScreen` · `ResultView` · `EditView`)에 남긴다. 국면 × 조작 권한은 **데이터 표**로
한 곳에 두고 화면은 그것만 읽는다.

**핵심 발견**: 3층 구조(60px 헤더 + 74px 국면 띠 + 본문)는 새 발명이 아니라 **확정 디자인
6종의 공통분모**다. 우측 Step 패널 460px 도 3종이 공유한다. 통합은 확정 디자인을 벗어나는
일이 아니라, 확정 디자인이 이미 공유하던 문법으로 나머지를 모으는 일이다.

**이행**: 국면 단위 **제자리 교체**. 한 국면을 옮기는 커밋에 그 국면의 옛 구현 삭제를 포함해
공존을 금지한다 — 통합 화면이 하나 더 늘어나면 4벌이 5벌이 된다.

## Technical Context

**Language/Version**: TypeScript 5.7 (frontend) · Python 3.11+ (backend — 이 라운드 변경 없음)

**Primary Dependencies**: React 19 · Vite 6 · (backend) FastAPI · Playwright for Python

**Storage**: 정의 파일 · 결과 파일 (평문 구조 형식). **이 기능은 저장 형식을 변경하지 않는다**

**Testing**: vitest 2 + @testing-library/react + jsdom (frontend) · pytest (backend)

**Target Platform**: 로컬 단독 도구. 브라우저에서 여는 단일 사용자 웹 UI

**Project Type**: web application (frontend + backend). 이번 변경은 **frontend 전용**

**Performance Goals**: Step 200개 목록에서 국면 전환이 지각되는 지연 없이 완료.
기존 `StepListPerformance.test.tsx` 의 기준을 낮추지 않는다

**Constraints**:
- 최소 기준 폭 1440px. 그보다 좁으면 재배치하지 않고 스크롤 (DC-011)
- 백엔드 변경 없음 (research R6). 필요해지면 설계가 틀렸다는 신호로 보고 멈춘다
- `noUncheckedIndexedAccess` 아래에서 타입 검사 통과
- 실행 진입은 `App.tsx` 의 단일 경로만 사용 (FR-248)

**Scale/Scope**: 7국면 · 33개 조작 · 삭제 대상 4개 페이지 파일 + 3개 페이지의 껍데기 ·
현재 관련 코드 약 5,000줄

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 후 재확인.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | **통과 · 강화** | Step DSL 을 변경하지 않는다 (FR-250). 이 기능은 오히려 원칙 I 을 **표시 층으로 확장**한다 — "사람 Step 과 AI Step 은 같은 모델" 이라는 원칙이 지금 화면에서는 4벌의 서로 다른 행으로 나타난다. 단일 Step 행 구현이 그것을 바로잡는다. 작성 주체는 배지로만 드러나고 행 구조를 바꾸지 않는다 (FR-228) |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | **통과** | 재생 경로에 언어모델 호출을 도입하지 않는다 (FR-251). 국면 판정과 조작 권한 판정은 규칙(정적 표 + 런타임 덮어쓰기)으로만 이루어진다. AI 지시문은 계속 기록일 뿐 실행 대상이 아니다 |
| **III. Stateful Interactive Runner** | **통과** | 세션 소유 구조(`SessionScreen`)를 유지한다 (research R2). Pause → Edit → Resume 경로가 그대로이며, 007 은 그 경로에 **더 많은 국면에서 도달**하게 만든다. 세션을 끊는 변경이 없다 |
| **IV. Locator Resilience** | **통과** | 후보 해석 순서는 제품 전역 고정 규칙이며 007 이 건드리지 않는다 (FR-232). Step 상세가 하나로 합쳐지면서 후보 표시가 **한 구현**이 되므로 순서가 두 곳에서 해석될 여지가 줄어든다 |
| **V. Asset Portability** | **통과 · 영향 없음** | DSL 을 변경하지 않으므로 Export 가능성에 영향이 없다. Export 자체는 이 라운드 범위 밖이며 기존 릴리스 게이트 항목으로 남는다 |

### 기술·보안 제약

| 제약 | 판정 |
|---|---|
| 비밀값 하드코딩 금지 | 해당 없음 — 007 은 값을 다루지 않는다 |
| 민감 값 마스킹 | **적용** — 어떤 국면에서도 참조 형태(`{{NAME}}`)로만 보인다 (FR-252). 단일 Step 행·단일 상세이므로 마스킹 규칙도 한 곳이다 |
| 경계 입력 검증 | 편집 요청의 검증은 서버(`step_edits`)가 유일한 구현으로 이미 있다. 007 이 두 번째 구현을 만들지 않는다 |
| 오류 명시 처리 | **적용** — `Notice` 가 `nextAction` 을 별도 칸으로 갖는다 (003 EC-004) |
| 교차 언어 스키마 단일 정의 | **적용** — 생성 타입(`types/generated/*`)을 소비만 한다. `WorkbenchModel` 은 표시 모델이며 저장 스키마가 아니다 |

### 품질 게이트

| 게이트 | 계획 |
|---|---|
| 1. 원칙 준수 | 재생 경로 변경 없음. 위 표가 증거 |
| 2. 왕복 무결성 | DSL·Recorder·Generator 변경이 없어 해당 없음. 단 정의 조회 → 화면 → 편집 연산 → 저장의 왕복은 기존 006 테스트가 지킨다 |
| 3. 테스트 동반 | 자동 검사 4종(구현 개수 · 행 자리 · 껍데기 · 권한 커버리지) + 기존 테스트 갱신. `quickstart.md` §1 |
| 4. 테스트 비활성화 금지 | **가장 큰 위험이다.** 007 은 선택자와 구조를 바꾸므로 기존 테스트가 대량으로 깨진다. **고쳐서 통과시킨다.** 검증하는 행동이 바뀌면 그것은 회귀다 |
| 5. 성공 지표 인식 | 이 기능은 PRD §18 의 "테스트 수정 후 재실행" 흐름에 직접 작용한다. SC-005·SC-009 가 그 측정이다 |

**결론: 통과.** 위반 없음. `Complexity Tracking` 에 기록한 것은 위반이 아니라 **추적이
필요한 위험**이다.

### Phase 1 설계 후 재확인

설계 산출물(`data-model.md` · `contracts/*`)을 만든 뒤 다시 대조했다. 판정은 바뀌지 않았고,
설계가 원칙을 **더 강하게** 만든 지점 셋을 기록한다.

| 원칙 | 설계가 더한 것 |
|---|---|
| I | `WorkbenchStep` 이 작성 주체를 배지로만 갖고 행 구조에 반영하지 않는다. 지금은 AI 작성 국면의 행이 보라 배경 + 보라 체크로 **구조적으로** 다르다 — 설계가 그것을 없앤다 |
| II | 국면 판정(`lib/phase.ts`)과 권한 판정(`lib/capabilities.ts`)이 정적 표 + 규칙 함수다. 언어모델이 닿는 자리가 구조적으로 없다 |
| IV | Step 상세가 하나가 되면서 후보 해석 순서를 표시하는 구현이 2벌에서 1벌이 된다. 순서를 두 곳에서 해석할 여지가 사라진다 |

설계가 새로 만든 위반은 없다. 새로 드러난 위험 하나(`StepResult` 에 Step DSL 이 없다)는
`Complexity Tracking` 넷째 항목에 기록했다.

## Project Structure

### Documentation (this feature)

```text
specs/007-unify-test-screens/
├── plan.md                    # 이 파일
├── spec.md                    # 요구사항 49건 (FR-217~FR-255)
├── research.md                # Phase 0 — R1~R8
├── data-model.md              # Phase 1 — 표시 모델
├── quickstart.md              # Phase 1 — 검증 절차
├── contracts/
│   ├── ui-contract.md         # 화면 문법 + 33개 조작 + 7×33 권한표
│   └── design-conformance-007.md   # 새 artboard 절차 · 대체 관계 · 승인
├── design-conformance/        # 구현 중 채운다
│   ├── replacement-map.md     # 기존 6종 → 새 artboard 대체 관계 (FR-254b)
│   ├── Workbench.md           # 대조 기록 (사람이 판정)
│   └── undefined-states.md    # 007 이 정한 미정의 상태 (DC-009)
├── checklists/
│   └── requirements.md        # 명세 품질 체크리스트
└── tasks.md                   # Phase 2 — /speckit-tasks 가 만든다
```

### Source Code (repository root)

**변경 대상은 `frontend/src` 뿐이다.** `backend/` 는 이 라운드에서 변경하지 않는다.

```text
docs/design/
└── Workbench.dc.html          # 신규 — 통합 화면 artboard 초안 (1440×900)
    canvas.json                # 항목 추가

frontend/src/
├── App.tsx                    # 화면 상태를 국면으로 재정리. startRun·openBrowserAt·
│                              #   openSession·pendingRun 은 그대로 (FR-248·FR-249)
├── hooks/useScreenUrl.ts      # WorkbenchLocation(국면·testId·stepId) 반영
├── lib/
│   ├── capabilities.ts        # 신규 — 국면 × 조작 권한표 + 런타임 덮어쓰기 (FR-233)
│   ├── phase.ts               # 신규 — 국면 판정 한 곳 (data-model §1)
│   ├── wording.ts             # 확장 — 이유·해소 방법 문구 단일 출처
│   └── sessionState.ts        # 유지
├── components/workbench/      # 신규 — 통합 화면의 표시 층
│   ├── Workbench.tsx          #   3층 껍데기. 데이터를 읽지 않는다
│   ├── PhaseBar.tsx           #   층② 74px 국면 띠
│   ├── TargetPane.tsx         #   층③ 좌 — 미러 / 산출물 / 브라우저 열기 / 빈 이유
│   ├── PhaseAside.tsx         #   층③ 좌 아래 — 국면 보조 영역
│   ├── StepList.tsx           #   층③ 우 460px — **단일 Step 목록**
│   ├── StepDetail.tsx         #   겹침 640px — **단일 Step 상세**
│   ├── NoticeStack.tsx        #   알림
│   └── ActionButton.tsx       #   CapabilityState 를 받아 그린다. disabled 이유 부착
├── components/design/
│   ├── Chrome.tsx             # 유지 (헤더 조각)
│   ├── DesignStepList.tsx     # StepOutcome 에 `recorded` 추가 → StepList 로 흡수
│   └── BrowserFrame.tsx       # 유지 (TargetPane 이 쓴다)
└── pages/
    ├── SessionScreen.tsx      # 세션 5국면 어댑터. 소유 구조 유지 (research R2)
    ├── ResultView.tsx         # 신규 — 결과 국면 어댑터 (RunResult.tsx 를 대체)
    ├── EditView.tsx           # 신규 — 편집 국면 어댑터 (TestDefinition.tsx 를 대체)
    ├── Runner.tsx             # ← 삭제 (이행 1)
    ├── RunnerPaused.tsx       # ← 삭제 (이행 2)
    ├── Takeover.tsx           # ← 삭제 (이행 3)
    ├── AiRecord.tsx           # ← 삭제 (이행 4)
    ├── RunResult.tsx          # ← 삭제 (이행 5, ResultView 로)
    ├── StepInspector.tsx      # ← 삭제 (이행 6, StepDetail 로)
    ├── TestDefinition.tsx     # ← 삭제 (이행 6, EditView 로)
    ├── TestList.tsx           # 유지 — 통합 대상 아님 (FR-217a)
    ├── CreateTest.tsx         # 유지
    ├── AiCompose.tsx          # 유지 — 지시문 작성은 테스트 만들기 흐름이다
    ├── ProjectSetup.tsx       # 유지
    ├── KeyManagement.tsx      # 유지
    └── SecretValues.tsx       # 유지

frontend/tests/
├── ImplementationCount.test.tsx   # 신규 — SC-001
├── StepRowLayout.test.tsx         # 신규 — SC-002 (7국면 × 칸 자리)
├── WorkbenchShell.test.tsx        # 신규 — SC-003
├── CapabilityCoverage.test.ts     # 신규 — SC-007 · FR-247
├── PhaseContext.test.tsx          # 신규 — SC-005 (지목 Step 왕복)
└── (기존 30여 개)                  # 선택자·구조 기대 갱신. 행동은 유지
```

**Structure Decision**: 기존 `frontend/src/{components,pages,lib,hooks}` 구조를 그대로
쓰고 `components/workbench/` 하나를 더한다. 새 최상위 디렉터리를 만들지 않는다 —
표시 층의 재배치이며 새 계층이 아니다.

`components/design/` 을 남기는 이유: 확정 디자인에서 **바이트 단위로 같은 조각**만 모은
곳이라는 성격이 007 에서도 유효하다. `Chrome.tsx` 의 헤더 조각은 8종 전부에서 동일하다.

## Phase 2 — 이행 순서

`research.md` R7 의 결정. **각 순서 항목은 옛 구현 삭제를 포함한 하나의 작업 단위다.**

| # | 단위 | 완료 판정 |
|---|---|---|
| 0 | 공통 계약 — `phase.ts` · `capabilities.ts` · `WorkbenchModel` 타입 · `StepOutcome` 에 `recorded` 추가 · `Workbench` 껍데기 · `ActionButton` | `CapabilityCoverage` 통과. 아직 어느 국면도 옮기지 않았으므로 화면 동작 변화 없음 |
| 0b | artboard 초안 + 대체 관계 + 승인 등록 | `docs/design/Workbench.dc.html` 존재 · `replacement-map.md` 가 6종의 모든 영역을 다룸 · `PENDING-HUMAN-VERIFICATION.md` 항목 등록 |
| 1 | 실행 중 국면 | `pages/Runner.tsx` 없음 · 참조 0건 · 기존 Runner 관련 테스트 갱신 통과 |
| 2 | 일시정지 / 검토 국면 | `pages/RunnerPaused.tsx` 없음 · 권한표 PAU 열을 현재 동작과 대조한 기록 |
| 3 | 사람이 직접 조작 국면 | `pages/Takeover.tsx` 없음 · 런타임 조건 C4 확정 |
| 4 | AI 작성 국면 | `pages/AiRecord.tsx` 없음 · `PhaseAside` 가 실제로 쓰임 · W-6(AI 실패 상시 표시) 통과 |
| 5 | 결과보기 국면 | `pages/RunResult.tsx` 없음 · 결과 ↔ 정의 `step_id` 매칭 동작 · 「이 결과 이후 정의가 바뀌었습니다」 알림 동작 |
| 6 | 편집 국면 + Step 상세 | `pages/TestDefinition.tsx` · `pages/StepInspector.tsx` 없음 · `ImplementationCount` 통과 (구현 1개 / 1개) |
| 7 | 맥락 유지 마무리 | `PhaseContext` 통과 — 세션 → 결과 구간이 이어진다 (S-10) |
| 8 | 대조 기록 · 미정의 상태 기록 | `Workbench.md` 기준값 채움 · `undefined-states.md` 작성 · **사람 판정은 대기 항목** |

**순서를 바꾸지 않는다.** 1~3 이 껍데기를 굳히고, 4 가 국면 보조 영역을 검증하고, 5 가 좌측
영역 전환을 검증한 뒤에야 6(가장 먼 껍데기)이 온다.

## Complexity Tracking

> Constitution Check 에 위반은 없다. 아래는 **추적이 필요한 위험**이며, 헌법
> "Incremental delivery" 규칙의 형식을 빌려 기록한다.

| 항목 | 왜 지금 완결되지 않는가 | 지금의 완화 | 회복 경로 |
|---|---|---|---|
| **새 artboard 의 사람 승인** | 확정 디자인 승인은 사람의 결정이며 구현이 대신할 수 없다 (002 §4 · DC-001) | 초안의 값을 기존 6종에서 **기계적으로 추출한 것만** 쓴다. 새로 정하는 값은 A1~A5 다섯 개로 한정하고 목록으로 제시한다. 승인 전 상태를 대조 기록 첫 줄에 명시한다 | `docs/PENDING-HUMAN-VERIFICATION.md` 에 릴리스 게이트 항목으로 등록. 승인 후 A1~A5 가 바뀌면 그 범위만 고친다 |
| **대조 기록의 사람 판정** | 구현자가 자기 구현을 판정하면 대조가 아니다 (002 §4). 001 T156 이 같은 이유로 미완이었다 | 기준값 칸은 스크립트가 채워 판정에 필요한 정보를 미리 갖춘다. 판정 대상 항목 수를 문서에 명시한다 | 같은 파일에 등록. `불일치`·`미판정` 0건이 완료 판정 |
| **기존 테스트 대량 갱신** | 화면 구조가 바뀌면 선택자·구조 기대가 깨진다. 30여 개 파일이 대상 | 이행을 국면 단위로 쪼개 한 번에 깨지는 범위를 줄인다. 각 단위 커밋에서 그 국면의 테스트를 갱신한다 | 게이트 4 — **삭제·건너뛰기 금지.** 갱신으로만 통과시킨다. 검증 행동이 바뀌면 회귀로 판정 |
| **결과 국면의 구조 정보가 현재 정의에서 온다** | `StepResult` 에 Step DSL 이 없다 (research R3). 결과 이후 정의가 바뀌면 "그때의 대상" 을 복원할 수 없다 | `step_id` 매칭 실패를 감지해 「이 결과 이후 정의가 바뀌었습니다」를 알린다 — 지금은 알 방법조차 없다 | 결과 스키마에 Step DSL 스냅샷을 담는 것은 저장 형식 변경이므로 별도 결정으로 남긴다. 필요해지면 그때 판단 |

## 결정하지 않은 것

- **결과 스키마에 Step DSL 스냅샷 추가** — research R3 의 셋째 대안. 저장 형식 변경이며
  이 기능의 범위 밖이다 (FR-250)
- **테스트 목록·테스트 만들기·키 관리·비밀 값 화면의 껍데기 통일** — FR-217a 로 범위에서
  제외했다. 진입점만 유지한다
- **런타임 조건 C4** (사람이 직접 조작 중 속도 설정 적용 여부) — 현재 동작을 확인해야 한다.
  이행 순서 3에서 확정한다 (UC-401)
