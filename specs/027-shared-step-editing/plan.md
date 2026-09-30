# Implementation Plan: Step 편집면과 조작 배선을 한 곳으로

**Branch**: `027-shared-step-editing` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/027-shared-step-editing/spec.md`

## Summary

007 이 화면의 **껍데기**를 통합하고 「소유와 표시를 나눈다」까지 했다. 그러나 **소유하는
쪽(어댑터 3개)을 합치지 않았고**, 그래서 같은 조작이 두 벌로 구현되고 Step 편집면이 두
벌이 됐다. 기능을 붙일 때마다 「어느 어댑터에?」를 고르게 되고, 한 곳만 고르면 아무도
모르게 비대칭이 된다 — 바로 앞 증분(026)이 그렇게 사고를 냈다.

이 증분은 **어댑터를 합치지 않되 「고를 필요가 없게」 만든다.**

1. **조작 배선** — 화면이 「내가 할 수 있는 일」의 묶음을 제공하고, 신설 모듈이 그것을 조작에 잇는다. 배선 모듈은 **국면을 모른다** — 조작표가 유일한 판정으로 남는다.
2. **Step 편집면** — 작고 이미 요구를 지키는 `StepEditFields` 를 정본으로 삼고, `StepDetail` 의 `ownFields` 갈래를 걷어낸다. `Workbench` 의 우회 props 둘이 없어진다.
3. **비대칭 검사** — 화면이 자기가 이어 둔 조작을 DOM 에 드러내고, 검사가 그것을 조작표와 대조한다. 목록을 손으로 적지 않는다.
4. **점진적 이행** — 13개 조작을 네 무리로 나눠 옮기고, 옮기지 않은 것은 기존 경로로 떨어진다.

## Technical Context

**Language/Version**: TypeScript 5 / React 19 (이 증분은 **거의 전부 프론트**다)

**Primary Dependencies**: Vite · Vitest · Testing Library. 새 의존성을 더하지 않는다.

**Storage**: 해당 없음 — 저장 형식도 서버 요청도 바뀌지 않는다.

**Testing**: `npx vitest run` · `npx tsc --noEmit`. 백엔드는 건드리지 않으므로 회귀 확인용으로만 돈다.

**Target Platform**: 로컬 실행 웹 앱

**Project Type**: Web application (이번 증분은 frontend 만)

**Performance Goals**: 없음. 렌더 경로에 층이 하나 늘지만 조작을 잇는 일은 클릭 시점에만 일어난다.

**Constraints**:
- 사용자가 보는 화면의 모습이 바뀌지 않아야 한다 (FR-021·SC-007)
- 조작표가 유일한 권한 판정으로 남아야 한다 (FR-006)
- 007 의 껍데기·3층 구조를 바꾸지 않는다 (FR-019)
- 추상이 늘기만 하면 실패다 (헌법 단순성 · research R7)

**Scale/Scope**: 프론트 신설 모듈 1 · 이전 대상 조작 13 · 통합 대상 편집면 2→1 · 제거되는 props 2 · 신설 검사 1

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 설계 후 재확인.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | 통과 | 이 증분은 **프론트 표시 계층만** 바꾼다. 편집이 지나는 서버 연산(`itb/execution/step_edits.py`)이 그대로이고, 사람·AI 가 같은 함수를 지나는 성질이 유지된다. 편집면이 하나가 되는 것은 오히려 「같은 편집이 같은 모양으로」를 **강화**한다. |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 통과 | 실행 경로를 건드리지 않는다. 언어모델 호출 경계와 무관하며, 백엔드 파일을 수정하지 않는다. |
| **III. Stateful Interactive Runner** | 통과 | 세션 수명·일시정지·인수를 건드리지 않는다. 조작이 무엇을 부르는지만 바뀌고, 무엇을 하는지는 그대로다. |
| **IV. Locator Resilience** | 통과 | 로케이터와 무관하다. |
| **V. Asset Portability** | 통과 | 저장 형식이 바뀌지 않으므로 Export 대응도 그대로다. |

**단순성 규칙** (Development Workflow & Quality Gates):

| | 는다 | 준다 |
|---|---|---|
| 모듈 | 1 (`lib/actionWiring.ts`) | — |
| 개념 | 1 (능력 묶음) | — |
| 중복 구현 | — | 조작 13개 × 2벌 |
| 편집면 | — | 2벌 → 1벌 |
| `Workbench` props | — | 2 (`stepDetailOwnFields`·`stepDetailExtra`) |

**정당화된다.** 다만 research R7 이 **실패의 정의**를 적어 두었다 — 배선 모듈이 국면을
알기 시작하거나 능력 묶음이 화면마다 다른 모양이 되면, 층만 하나 더한 것이므로 되돌린다.

**결론**: **위반 없음.** Complexity Tracking 은 비운다.

## Project Structure

### Documentation (this feature)

```text
specs/027-shared-step-editing/
├── plan.md              # 이 파일
├── spec.md              # 요구사항 25 · 성공 기준 9
├── research.md          # R1~R8 — 실제 코드에서 확인한 결정
├── data-model.md        # 능력 묶음 · 배선 표 · DOM 노출 · 편집면
├── quickstart.md        # **무엇이 깨졌는지 빨리 아는 법**에 무게
├── contracts/
│   └── wiring-contract.md   # 배선 모듈이 하지 않을 것 · 화면이 노출할 것
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks 산출물 (아직 없음)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── lib/
│   │   ├── actionWiring.ts      # [신설] 능력 묶음 · 배선 표 · makeRunAction
│   │   ├── actions.ts           # [건드리지 않음]
│   │   └── capabilities.ts      # [건드리지 않음] — 유일한 권한 판정으로 남는다
│   ├── components/
│   │   ├── StepEditFields.tsx   # [정본] 편집면. 거의 그대로 쓴다
│   │   └── workbench/
│   │       ├── StepDetail.tsx   # [수정] ownFields 갈래를 걷어내고 StepEditFields 를 쓴다
│   │       └── Workbench.tsx    # [수정] stepDetailOwnFields·stepDetailExtra 제거
│   └── pages/
│       ├── SessionScreen.tsx    # [수정] runAction switch → 능력 묶음
│       ├── EditView.tsx         # [수정] 〃
│       └── ResultView.tsx       # [수정] 〃
└── tests/
    ├── ActionWiring.test.tsx    # [신설] 표 ↔ 배선 대조 (이 증분의 안전장치)
    └── (기존 검사 다수)          # 회귀 확인 대상

backend/                          # **건드리지 않는다**
```

**Structure Decision**: 기존 구조를 그대로 쓴다. **신설 파일은 `lib/actionWiring.ts` 와
그 검사 하나뿐**이다. 나머지는 기존 파일에서 로직이 옮겨 나가는 변경이다.

## Phase 0 — Research

완료. [research.md](./research.md) 에 R1~R8.

가장 중요한 넷:

- **R1** — 화면이 능력을 제공하고 배선이 잇는다. FR-003·FR-004·FR-005 를 동시에 만족시키는 모양이며, 배선이 국면을 받지 않으므로 FR-006 이 저절로 지켜진다.
- **R2** — 검사가 목록을 들지 않는다. 화면이 `data-wired-actions` 로 드러내고 검사가 조작표와 대조한다. 기존 `CapabilityUI` 는 「있는가」를 보고 이것은 「이어졌는가」를 본다.
- **R3** — 편집면 정본은 `StepEditFields`. **작고 이미 FR-010·FR-011 을 지킨다.** 큰 쪽으로 합치면 그 둘을 새로 만들어야 한다.
- **R7** — 늘어나는 것(모듈 1·개념 1)보다 줄어드는 것(중복 13쌍·편집면 1벌·props 2)이 많다. **실패의 정의**도 함께 적었다.

## Phase 1 — Design & Contracts

완료.

- [data-model.md](./data-model.md) — `ScreenCapabilities` · `ACTION_WIRING` · `runAction` · `data-wired-actions` · 편집면
- [contracts/wiring-contract.md](./contracts/wiring-contract.md) — **배선 모듈이 하지 않을 것**의 목록이 핵심이다
- [quickstart.md](./quickstart.md) — 「무엇이 깨졌는지 빨리 아는 법」 + 검사가 실제로 잡는지 시험하는 법

### Constitution Check (설계 후 재확인)

설계가 원칙을 더 건드리는 자리는 없다. 오히려 **원칙 I 이 강화된다** — 편집면이 하나가
되면 「사람이 어느 화면에서 고치든 같은 모양」이 코드의 성질이 된다.

**남은 위험은 기술이 아니라 범위다.** 이행 중에 「이왕 만지는 김에」가 들어오면 SC-007
(사용자가 보는 모습이 달라지지 않는다)을 잴 수 없게 된다. R5 가 조작을 네 무리로 나눈
것은 각 무리마다 그 기준을 확인하기 위해서다.

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 비운다.

해당 없음.
