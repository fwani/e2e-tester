# Implementation Plan: Step 을 원하는 자리에 넣고, 행에서 옮기고 지운다

**Branch**: `009-step-editing-flow` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-step-editing-flow/spec.md`

---

## Summary

Step 을 추가하는 길이 셋뿐이고 셋 다 「살아 있는 브라우저 + 일시정지」를 요구한다. 그런데
그 요구의 근거는 하나뿐이다 — **요소 후보는 살아 있는 화면에서만 수집·검증된다**(헌법 원칙
IV). 요소를 지목하지 않는 Step 종류 넷(주소 이동 · 탭 닫기 · 주소 검증 · 화면 텍스트
검증)까지 같은 잠금에 걸려 있다.

이 계획은 그 잠금을 **표 위에서 갈라 놓는다.**

1. **`InsertableKind` 를 domain 에 세운다** — 손으로 만들 수 있는 종류의 유일한 정본.
   생성 타입으로 프론트에 내려가므로 목록이 두 벌이 되지 않는다.
2. **삽입 연산을 세션 없는 편집에 더한다** — 기존 편집 묶음·기존 `insert_step` 연산·기존
   `revision` 충돌 흐름을 그대로 쓴다.
3. **이미 있는데 쓰이지 않던 셋을 잇는다** — 위치 지정 삽입(호출처 0), 목표 앞에서 멈추는
   재생(도달 5걸음), 행 조작 자리(전달 화면 0). **배관이 아니라 입구를 만든다.**
4. **조작 34 → 36.** 표를 먼저 고치고 화면에 붙인다 (UC-000).

새 Step 종류·새 실행 방식·새 저장 흐름을 만들지 않는다.

---

## Technical Context

**Language/Version**: Python 3.12 (백엔드) · TypeScript 5 / React 19 (프론트엔드)

**Primary Dependencies**: FastAPI · Playwright for Python · pydantic v2 · Vite · vitest ·
@testing-library/react

**Storage**: 프로젝트 디렉터리의 평문 Step DSL 파일 (`itb.storage`). 스키마 변경 없음

**Testing**: pytest (마커 `browser` · `timing` 으로 나눠 돈다) · vitest · import-linter ·
ruff · `scripts/extract_canon.py --check` · `frontend/scripts/count-violations.mjs`

**Target Platform**: 로컬 데스크톱 (백엔드 프로세스 + 브라우저 UI)

**Project Type**: web application — `backend/` + `frontend/`

**Performance Goals**: 사람의 조작 횟수가 목표다 — SC-501~SC-504. 서버 처리량 목표 없음

**Constraints**:

- 조작 표(`capabilities.ts`)가 정본이다. 조작을 더하면 8국면 셀을 전부 채워야 컴파일된다
- 시각 언어 정본은 `dc.html 의 <style>` → `extract_canon.py` → `tokens.css` 한 방향이다
- Step DSL 스키마는 `itb.domain` 이 정본이고 프론트는 생성물을 받는다
- `.importlinter` — domain 은 다른 계층을 임포트하지 못하고, execution 은 authoring·llm 을
  임포트하지 못한다

**Scale/Scope**: 실무 테스트 20~50 Step. 화면 8국면 · 조작 36 · 표 288칸

---

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 설계 후 재확인한다.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | **통과** | 새 Step 종류를 만들지 않는다. `ManualStepSpec` 은 **입력 서술**이고 만들어지는 것은 기존 `NavigateStep`·`CloseTabStep`·`AssertionStep` 이다. `author` 는 `human` 이며 실행 방식을 바꾸지 않는다. 삽입은 세 입구가 `step_edits.insert_step` 한 곳으로 모인다 |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | **통과** | 재생 경로를 건드리지 않는다. 기존 `pause_before_index` 를 쓸 뿐이다. `itb.domain.manual_step` 은 domain 이므로 `.importlinter` 의 `execution-no-llm` 이 authoring·llm 도달을 구조로 막는다. **LLM 호출을 새로 만드는 코드가 없다** |
| **III. Stateful Interactive Runner** | **강화된다** | 원칙 III 은 이미 "편집이 처음부터의 실행을 강요해서는 안 된다"와 "일시정지 중 추가된 Step 은 일시정지 위치에 삽입된다"를 요구한다. FR-291 이 그 요구를 조작 하나로 만든다. 삽입은 브라우저에 명령을 보내지 않으므로 세션 상태가 보존된다 |
| **IV. Locator Resilience** | **통과 · 강화** | 손으로 넣는 경로에서 `TargetLocator` 를 **받지 않는다** — 요청 모델에 그 종류가 없다. 지금은 런타임 문구로만 막던 것을 타입으로 막는다 |
| **V. Asset Portability** | **통과** | 새 Step 종류가 없으므로 생성기가 이미 셋을 다룬다 (`playwright_gen._assertion_lines` 가 `url`·대상 없는 `text` 를 처리한다). DSL 은 평문 그대로다 |
| **보안 요구** | **통과** | `ManualStepSpec` 에 평문 민감 값을 받는 필드가 없다. 검증 실패 시 `_missing_fields` 로 **위치만** 싣는다 (003 EC-005). 새 권한·새 실행 능력을 만들지 않는다 |
| **품질 게이트 2 (왕복 무결성)** | **계획됨** | SC-510 통합 테스트 — 넣고 저장하고 다시 읽고 실행한다 (research R9) |
| **품질 게이트 3 (테스트 동반)** | **계획됨** | 백엔드 단위·계약·통합, 프론트 표 커버리지·화면 테스트 |
| **품질 게이트 5 (성공 지표 인식)** | **해당** | PRD §18 의 「테스트 생성 시간」에 직접 영향을 준다. 조작 횟수로 측정한다 (SC-501~504) |

**위반 없음.** Complexity Tracking 절을 쓰지 않는다. 이연(deferral)도 없다.

한 가지를 명시한다 — **원칙 IV 의 제약을 완화하지 않는다.** 이 기능은 「요소를 손으로 넣을
수 있게」 하지 않는다. 요소를 요구하지 않는 Step 을 요소 잠금에서 빼는 것뿐이다.

---

## Project Structure

### Documentation (this feature)

```text
specs/009-step-editing-flow/
├── plan.md                      # 이 파일
├── spec.md                      # 명세 (FR-285~313 · SC-501~510)
├── research.md                  # Phase 0 — 결정 R1~R9
├── data-model.md                # Phase 1 — 모델·연산·표
├── quickstart.md                # Phase 1 — 검증 절차
├── contracts/
│   └── step-editing.md          # Phase 1 — 007 ui-contract §2·§3 개정판 + API
├── checklists/
│   └── requirements.md          # 명세 품질 체크리스트
└── tasks.md                     # Phase 2 (/speckit-tasks 가 만든다)
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── domain/
│   │   └── manual_step.py          # 신규 — InsertableKind · ManualStepSpec · build_step
│   ├── schema/
│   │   └── export.py               # MODELS 에 "manual-step" 추가
│   ├── execution/
│   │   ├── step_edits.py           # 변경 없음 — insert_step 을 그대로 쓴다
│   │   └── runner.py               # pause_before_index 읽기 전용 노출
│   └── api/routes/
│       ├── tests.py                # InsertStepOp · _apply_edits 분기 · 삽입 경고
│       ├── steps.py                # POST /{id}/steps:manual 신규
│       └── sessions.py             # SessionView.pause_before_index
├── schema/
│   └── manual-step.schema.json     # 생성물
└── tests/
    ├── unit/                       # manual_step 조립·라벨·거절
    ├── contract/                   # 두 입구의 요청·응답·거절 규칙
    └── integration/                # 왕복 무결성 · 목표 앞 정지 흐름

frontend/
├── src/
│   ├── lib/
│   │   ├── actions.ts              # 34 → 36 · step.reorder → step.moveUp
│   │   ├── capabilities.ts         # PHASE_TABLE 8국면 셀 · 덮어쓰기 목록
│   │   └── wording.ts              # 라벨·이유 문구
│   ├── api/client.ts               # insertStepManual · definition insert 연산
│   ├── components/workbench/
│   │   ├── StepList.tsx            # 칸 5 · rowActions 소비
│   │   ├── ActionPalette.tsx       # 이동·삭제 자리를 행에 양도 (hidden)
│   │   └── model.ts                # 행 조작 모델
│   ├── pages/
│   │   ├── EditView.tsx            # 삽입 연산 · 행 조작 · 「이 앞에 추가」
│   │   └── SessionScreen.tsx       # ReorderPanel 제거 · 행 조작 · 진행 표시
│   ├── theme/tokens.css            # extract_canon.py 재생성 결과
│   └── types/generated/
│       └── manual-step.d.ts        # 생성물
└── tests/                          # 표 커버리지 · 행 조작 · 흐름

docs/design/008-visual-language/
├── *.dc.html                       # 18장 시트에 .srow 다섯째 칸 · 행 마크업 8장
├── conformance/*.md                # 대조표에 칸 5 추가
└── replacement-map.md              # 정본 클래스에 .srow-ops 추가

.github/workflows/ci.yml            # 스키마 드리프트 비교 경로에 manual-step 추가
```

**Structure Decision**: 기존 `backend/` + `frontend/` 2계층을 그대로 쓴다. 새 패키지·새
계층을 만들지 않는다. 유일한 신규 모듈은 `itb/domain/manual_step.py` 이며, 그 자리를 고른
근거는 [research.md](./research.md) R1 이다.

---

## 구현 순서 — 독립 인수 가능한 세 단위

**순서가 의존성이다.** US1 이 삽입 연산과 조작 id 를 세우고, US2 는 그 삽입 지점에서
브라우저 경로를 잇고, US3 은 그 둘을 행으로 내린다.

### 0단계 — 표와 정본을 먼저 고친다 (US1~US3 공통 전제)

UC-000 이 요구하는 순서다. 화면을 먼저 고치면 표와 코드가 갈리고, 갈린 표는 「눌러도 아무
일이 없는 칸」을 만든다.

1. `actions.ts` — `step.insertManual` · `step.moveDown` 추가, `step.reorder` →
   `step.moveUp` 개칭. 컴파일러가 21곳을 전수로 요구한다
2. `capabilities.ts` — `PHASE_TABLE` 8국면 × 3조작 셀, 덮어쓰기 목록
   ([contracts/step-editing.md](./contracts/step-editing.md) §2)
3. `wording.ts` — 라벨과 이유 문구. **새 `DISABLED_REASON` 키를 만들지 않는다** (기존
   `NOT_STARTED_YET`·`NEEDS_PAUSE`·`RUNNING_NO_EDIT`·`RESULT_NO_EDIT`·`C7` 로 충분하다)
4. `dc.html` 18장 시트 → `extract_canon.py` → `tokens.css` (§6 의 순서)

**인수**: `CapabilityCoverage.test.ts` 가 36 × 8 = 288칸을 통과한다.
`extract_canon.py --check` 가 통과한다.

### 1단계 — US1: 브라우저 없이 삽입 (P1)

**백엔드**

1. `itb/domain/manual_step.py` — `InsertableKind` · `ManualStepSpec` 판별 유니온 ·
   `build_step`
2. `itb/schema/export.py` — `MODELS["manual-step"]`, 스키마·타입 재생성, CI 경로 추가
3. `tests.py` — `InsertStepOp`, `_apply_edits` 분기, 삽입 경고 (data-model §3)
4. `steps.py` — `POST /{id}/steps:manual` (data-model §4)

**프론트엔드**

5. `client.ts` — 두 입구의 래퍼
6. `EditView.tsx` — 「이 앞에 추가」 자리와 종류별 입력, 미저장 삽입 관리 (research R7)
7. `SessionScreen.tsx` — 일시정지 중 직접 입력 삽입

**인수**: quickstart US1 절 전체. 통합 테스트로 왕복 무결성(SC-510).

### 2단계 — US2: 「이 자리에 추가」 (P2)

1. `runner.py` — `pause_before_index` 읽기 전용 접근자
2. `sessions.py` — `SessionView.pause_before_index`
3. `SessionScreen.tsx` — 진행 표시(FR-293)와 도달 전 실패 문구(FR-294)
4. `App.tsx` · `EditView.tsx` — 저장 → 세션 생성 → 도착 후 녹화 시작을 하나로 (§5 의 5단계)
5. `ResultView.tsx` — 「고치기」가 그 Step 을 고른 상태로 넘긴다 (FR-297)

**인수**: quickstart US2 절 전체. 재연결 후에도 목표가 남는지(2-1)와 도달 전 실패(2-2)를
포함한다.

### 3단계 — US3: 행 조작 (P3)

1. `StepList.tsx` — 칸 5, `rowActions` 소비, 끝단 좁히기(FR-300)
2. `SessionScreen.tsx` — `ReorderPanel` **제거**, 행 조작 연결
3. `EditView.tsx` — 팔레트의 「위로 옮기기」 단독 버튼 제거, 행 조작 연결
4. `ActionPalette.tsx` — 이동·삭제 자리를 행에 양도(`hidden`)
5. 확정 디자인 마크업 8장 · 대조표 · `replacement-map.md`

**인수**: quickstart US3 절 전체. 조작 횟수(SC-503·SC-504)와 목록 중복 없음(SC-505),
키보드 경로(SC-507).

---

## 위험과 대응

| 위험 | 왜 위험한가 | 대응 |
|---|---|---|
| 조작 개칭이 넓게 번진다 (21곳) | 남는 참조가 있으면 화면이 조용히 조작을 잃는다 | 타입 개칭이므로 **컴파일러가 전수로 요구한다.** 런타임에 남을 수 없다 |
| `.srow` 격자 변경이 18장 시트에 걸린다 | 일부만 고치면 정본이 갈린다 | `extract_canon.py --check` 가 18장 동일성을 단언한다. 0단계에서 먼저 통과시킨다 |
| 460px 패널에서 이름 칸이 좁아진다 (약 227px) | 긴 Step 이름이 잘린다 | 이미 `text-overflow: ellipsis` 다. 전체 이름은 Step 상세가 갖는다. L3 대조에서 사람이 확인한다 |
| 도착 시 녹화 자동 시작이 놀라움을 준다 | 의도하지 않은 조작이 기록된다 | 도착 알림이 「지금부터 기록됩니다」를 말하고, 「기록 멈추기」가 그 국면의 정본 조작으로 이미 있다 (research R5) |
| 미저장 삽입과 순서 변경이 섞인다 | 정수 위치가 앞선 연산에 따라 가리키는 곳이 바뀐다 | 화면은 미리보기 목록 기준으로 저장 시점에 위치를 확정한다 (research R7) |
| 삽입 입구가 셋이 된다 | 규칙이 갈릴 수 있다 | 셋 다 `step_edits.insert_step` 한 연산으로 모인다. 계약 테스트가 세 입구의 결과가 같은지 본다 |

---

## 범위 밖 (명세 Assumptions 와 같다)

- 끌어놓기(drag&drop) 순서 변경 — 행의 위로·아래로로 조작 횟수 문제가 해소된다
- 「자리만 잡아 두는 미완성 Step」 — 원칙 IV 와 006 FR-187 제외 결정을 유지한다
- 테스트 목록 화면의 삽입 입구 — 그 화면에는 Step 이 보이지 않는다
- Playwright 내보내기 변경 — 새 Step 종류가 없으므로 생성기를 고칠 것이 없다

---

## Phase 1 후 헌법 재확인

설계 산출물(`data-model.md` · `contracts/step-editing.md` · `quickstart.md`)을 놓고 다시
본다.

| 원칙 | 재확인 결과 |
|---|---|
| I | `ManualStepSpec` 은 기존 세 Step 을 만들 뿐이며 저장 형태가 하나다. 삽입 입구 셋이 한 연산으로 모인다 — **통과** |
| II | 재생 경로에 추가된 것은 `pause_before_index` 를 **읽는** 접근자 하나다. 새 분기·새 호출이 없다 — **통과** |
| III | 삽입이 브라우저에 명령을 보내지 않는다는 것이 계약에 명시됐다 (data-model §4) — **통과** |
| IV | 요청 모델에 `target` 필드가 없다. 판별 유니온이 `click` 을 성립시키지 않는다 — **통과** |
| V | 생성기 변경 0건. DSL 은 평문 그대로 — **통과** |
| 보안 | 오류에 값이 실리지 않는 규칙을 계약에 적었고 quickstart 1-3 이 그것을 실측한다 — **통과** |

**설계 후에도 위반 없음.** Complexity Tracking 은 비운다.
