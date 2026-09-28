# Implementation Plan: 022 — 예산 소진을 막힘과 갈라 말한다

**Branch**: `022-limit-continue-choice` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-limit-continue-choice/spec.md`

## Summary

막힘의 종류에 **세 번째 값**(예산 소진)을 더하고, 그 값이 세 곳의 행동을 가른다 —
이어갈 때 AI 에게 보내는 지시, 화면이 여는 칸, 화면이 보여 주는 문구. 여기에 판단
근거(누적 사용량·진전 여부)를 막힘 정보에 실어 화면까지 보낸다.

**새 경로·새 선택지·새 종료 방식을 만들지 않는다.** 조사에서 이어가기(`retry`)와
끝내기(`abort`)가 이미 있고 예산 리셋까지 하고 있음이 확인됐다 ([research.md](./research.md) R0).
남은 것은 그것들이 예산 소진 상황에서 **틀린 말과 틀린 지시**를 쓰고 있다는 것이다.

가장 무거운 것은 문구가 아니라 동작이다 — 예산 소진 뒤 이어가면 AI 가 「같은 동작을
다시 시도하라」는 지시를 받아 **이미 성공한 일을 반복한다** (FR-006 · SC-001).

## Technical Context

**Language/Version**: Python 3.13 (backend) · TypeScript/React (frontend)

**Primary Dependencies**: FastAPI, Playwright for Python · React, Tailwind, shadcn 기반 부품

**Storage**: 해당 없음 — 이 기능은 세션 메모리 안의 상태만 다룬다. Step DSL 을 건드리지 않는다.

**Testing**: pytest (`backend/scripts/test-backend.sh` — 병렬 계층 + 순차 계층) · vitest (frontend)

**Target Platform**: 로컬 실행 웹 앱

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 해당 없음 — 사용자 조작 한 번에 대한 반응이며 기존 막힘 경로와 같다.

**Constraints**:
- 헌법 원칙 II — 실행 경로에서 LLM 도달 불가. 이 기능은 **작성 경로만** 건드리므로
  `execution-no-llm` 계약과 무관하다.
- 020 이 만든 `BlockedKind` 의 축(「왜 막혔는가」)을 흐리지 않는다.
- 확정 디자인 밖의 요소를 새로 만들지 않는다 — 기존 `Button` 부품과 기존 막힘 패널 구조를 쓴다.

**Scale/Scope**: 백엔드 3 파일 · 프론트 2 파일 · 새 파일 0. 아래 구조 절 참조.

## Constitution Check

*GATE: Phase 0 이전 통과 · Phase 1 설계 후 재확인*

| 원칙 | 관련 | 판정 |
|---|---|---|
| I. Unified Step Model (NON-NEGOTIABLE) | Step 을 만들거나 바꾸지 않는다. 이 기능은 **몇 개 만들었는지 세기만** 한다 | **통과** |
| II. Deterministic Replay (NON-NEGOTIABLE) | 작성 경로 전용. 저장된 테스트의 실행 경로에 닿지 않는다. `.importlinter` 계약 변경 없음 | **통과** |
| III. Stateful Interactive Runner | 예산 소진에서도 **세션을 닫지 않는다** — 기존 막힘과 같다. 브라우저는 그대로 살아 있고 사용자가 이어받을 수 있다 | **통과 (강화)** |
| IV. Locator Resilience | 무관 — 요소 식별을 건드리지 않는다 | **해당 없음** |
| V. Asset Portability | Step DSL 을 건드리지 않으므로 내보내기 가능성에 영향 없다 | **해당 없음** |

**Technology & Security**: 새 의존성 없음. 비밀값 없음. 화면에 새로 싣는 값은 숫자 둘
(누적 동작 수·Step 수)뿐이며 민감정보가 아니다.

**Phase 1 재확인**: 설계 후에도 위 판정이 유지된다. 데이터 모델이 세션 메모리 안의 계수
두 개와 열거형 값 하나뿐이고, 저장·실행·내보내기 어디에도 닿지 않는다.

## Project Structure

### Documentation (this feature)

```text
specs/022-limit-continue-choice/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — 뒤집힌 전제와 다섯 쟁점의 결론
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── blocked-view.md  # Phase 1 — 막힘 정보의 계약 (뷰·이벤트)
├── checklists/
│   └── requirements.md  # specify 단계 산출물
└── tasks.md             # /speckit-tasks 산출물 (이 명령이 만들지 않는다)
```

### Source Code (repository root)

```text
backend/
├── src/itb/authoring/
│   ├── tools.py          # BlockedKind 에 세 번째 값 · AttemptLimits 에 누적 계수
│   ├── agent.py          # AgentOutcome 에 누적·진전 · 예산 소진 판정을 결말에 싣는다
│   └── blocked.py        # ai_blocked 이벤트에 누적·진전 싣기
├── src/itb/api/routes/
│   └── sessions.py       # 재개 지시 분기 · BlockedView 확장
└── tests/
    ├── unit/             # 계수·판정·지시 분기의 단위 검증
    └── integration/      # 상한 도달 → 이어가기 → 반복 없음의 경로 검증

frontend/
├── src/components/workbench/
│   └── WorkArea.tsx      # 예산 소진 분기 — 제목·칸·선택지·누적 표시
├── src/pages/
│   └── SessionScreen.tsx # BlockedView 의 새 필드를 화면 모델로 옮긴다
└── tests/                # 예산 소진 화면과 기존 막힘 화면이 갈리는지
```

**Structure Decision**: 기존 구조를 그대로 쓴다. **새 모듈을 만들지 않는다** — 이 기능이
더하는 것은 이미 있는 자리의 값 하나(열거형)와 계수 둘이며, 새 파일을 만들면 「막힘」에
대한 지식이 두 곳으로 갈린다.

## 설계 결정

근거는 [research.md](./research.md) 에 있고 여기서는 결론과 그 결론이 코드에서 무엇이 되는지만 적는다.

### D1. `BlockedKind` 에 세 번째 값을 더한다 (R1)

```
BlockedKind = needs_input | product_mismatch | budget_exhausted   ← 더함
```

`product_mismatch` 와 묶지 않는 이유는 **이어가기의 의미가 정반대**이기 때문이다 —
제품 불일치는 이어가도 같은 결과이고, 예산 소진은 이어가면 진행된다.

기존 소비자는 깨지지 않는다. 프론트가 `?? "needs_input"` 로 읽고 `product_mismatch` 만
분기하므로, 새 값은 `else` 로 떨어져 **지금과 같은 화면**이 된다 (R1 말미).

### D2. 누적은 `AttemptLimits` 가 함께 센다 (R2)

```
AttemptLimits
  calls        — 이번 시도의 호출 수. 예산을 새로 줄 때 0 으로
  total_calls  — 이 지시에 쓴 누적 호출 수. 예산을 새로 줘도 남는다   ← 더함
```

`record_call()` 이 유일한 통과 지점이므로 두 계수를 같은 자리에 두면 어긋날 수 없다.

**`reset()` 을 `reset_attempt()` 로 바꾼다.** 하는 일이 「전부 되돌린다」에서 「이번 시도의
예산만 되돌린다」로 좁아졌고, 이름이 그 사실을 말해야 한다. 호출부는 네 곳
(`agent.chat`·`resume_with_answer`·`resume_after_takeover`·`sessions._start_agent_note`)이며
전부 같은 뜻으로 부르고 있으므로 기계적 치환이다.

### D3. 「진전」은 Step 수 증가로 정의한다 (R3)

```
AttemptLimits
  steps_at_attempt_start  — 이번 시도를 시작할 때의 Step 수           ← 더함
```

진전 여부 = (지금 Step 수 > 시도 시작 시 Step 수). 시작 값이 없는 첫 시도에서는 진전
없음을 **판정하지 않는다** — 비교할 직전 값이 없다 (spec Edge Cases).

도구 호출 성공을 포함하지 않는 이유는 그것이 거의 항상 참이어서 **울리지 않는 경고**가
되기 때문이다 (R3).

### D4. 「여기까지」는 기존 끝내기를 쓴다 (R4)

새 종료 방식을 만들지 않는다. `abort` 가 하는 일(상태 전이 후 저장 여부 확인)이 그대로
맞다. 문구만 그 상황의 말로 바꾼다.

### D5. 이어가기는 기존 `retry` 를 쓰되 지시를 가른다 (R5)

```python
# sessions.py ai_choice — 지금
note = "같은 동작을 지금 화면 상태에서 다시 시도하세요." if RETRY else "그 동작은 건너뜁니다. …"

# 바뀐 뒤 — 막힘의 종류가 지시를 고른다
RETRY + budget_exhausted → "남은 지시를 이어서 수행하세요. 이미 끝낸 동작은 다시 하지 마세요."
RETRY + 그 밖           → 지금 그대로
```

막힘 종류는 `w.last_blocked` 에서 읽는다 — `_blocked_view` 가 이미 같은 자리를 같은
방식으로 읽고 있다. **새 저장소가 필요 없다.**

### D6. 누적·진전은 `AgentOutcome` 에 실어 뷰와 이벤트 둘 다 얻는다

`AgentOutcome.tool_calls` 는 이미 있으나 **아무도 읽지 않는다.** 이것을 살리고 옆에
누적과 진전을 더한다. `_blocked_view` 가 `last_blocked` 에서 읽으므로 **화면을 새로
고쳐도 남는다** (FR-022) — `BlockedView` 가 정확히 그 목적으로 존재한다.

`AgentOutcome` 은 상태를 소유하지 않고 **판정 시점의 값을 싣는다.** `step_count`·
`tool_calls` 가 이미 그렇게 실려 있으므로 일관된다.

## 구현 순서 (US 단위)

각 단계가 독립적으로 검증 가능하다.

| 단계 | 내용 | 검증 |
|---|---|---|
| 기반 | `BlockedKind.BUDGET_EXHAUSTED` · `AttemptLimits` 계수 둘 · `reset_attempt()` 개명 | 단위 — 계수가 리셋을 건너 남는가 |
| US1 (P1) | 상한 도달이 새 종류로 판정되고, 이어가기 지시가 갈린다 | 통합 — 상한 도달 후 이어가기가 「이어서」 지시를 받는가 |
| US2 (P2) | 화면이 예산 소진을 갈라 그린다 — 제목·칸·선택지 | 프론트 — 예산 소진과 기존 막힘이 다르게, 기존 막힘은 지금과 같게 |
| US3 (P3) | 누적·진전을 결말에 싣고 화면에 표시 | 통합 + 프론트 — 두 번 이어간 뒤 누적이 합쳐지는가 |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| `reset()` 개명이 호출부를 놓친다 | 개명이므로 놓치면 **즉시 터진다**(`AttributeError`). 조용히 틀리지 않는다 |
| 프론트가 새 `kind` 를 모른 채 배포된다 | `?? "needs_input"` 와 `else` 분기로 **지금 화면**이 된다. 기능이 안 보일 뿐 깨지지 않는다 |
| 진전 없음이 정당한 탐색에 뜬다 | 안내는 이어가기를 막지 않는다 (FR-021). 반대 방향 오작동이 더 해롭다 (R3) |
| 기존 막힘 화면이 바뀐다 | SC-005 가 이것을 직접 검증한다. `kind` 분기 밖을 건드리지 않는다 |
| 이어가기 지시 변경이 다른 막힘에 샌다 | FR-007 · US1 시나리오 3 이 「예산 소진이 아니면 지금 그대로」를 고정한다 |

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 비운다.

위반 없음. 새 프로젝트·새 계층·새 추상을 만들지 않으며, 더하는 것은 기존 열거형의 값
하나와 기존 자료구조의 계수 둘이다.
