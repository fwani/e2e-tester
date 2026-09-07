# Implementation Plan: 실행 속도 조절과 로딩 대기

**Branch**: `004-run-pacing-readiness` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-run-pacing-readiness/spec.md`

## Summary

두 결함을 한 기능으로 고친다.

1. **실행이 쉬지 않고 진행돼 사람이 못 따라간다.** 러너 루프에 Step 간 간격을 넣고, 속도를
   네 단계(`빠름`·`보통`·`느림`·`한 스텝씩`)로 고르게 한다. `한 스텝씩` 은 새 상태를 만들지
   않고 기존 `PAUSED` 를 매 경계에서 자동으로 적용한다.

2. **로딩 중인 요소를 "없음" 으로 판정한다.** 원인은 예산 부족이 아니라 예산을 쓰는
   방식이다 — 현재 `resolve()` 는 최상위 후보 하나에만 남은 예산 전체를 건다. 실측으로
   재현했다(research R1: 5004ms 실패 → 폴링 시 2089ms 통과). **모든 후보를 100ms 주기로
   다시 확인**하도록 바꾸고, 잘못된 요소를 조용히 채택하던 `.first` 폴백을 제거한다
   (research R2).

두 변경 모두 Step 모델도, 우선순위 규칙도 건드리지 않는다. 바뀌는 것은 **언제 다시
확인하는가**와 **Step 사이에 얼마나 쉬는가** 둘뿐이다.

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript / React 18 (frontend)

**Primary Dependencies**: FastAPI, Playwright for Python, Pydantic v2 — **추가 없음**

**Storage**: 기존 파일 기반. 속도 설정만 `~/.config/itb/preferences.json` 신규
(research R8). 테스트 자산(`tests/*.yaml`)과 `itb-project.yaml` 은 건드리지 않는다.

**Testing**: pytest (unit / contract / integration / e2e / abnormal), 기존 921건 유지

**Target Platform**: 로컬 데스크톱 (macOS·Linux), Chromium headed 기본

**Project Type**: Web application (backend + frontend), 기존 구조 유지

**Performance Goals**:
- 요소가 즉시 존재하는 Step 의 추가 비용 **100ms 미만** (SC-003, 실측 근거 research R4·R7)
- 요소 등장 후 다음 동작까지 오버슈트 **100ms 이하** (FR-116)
- 일시정지·중지 반영 **1초 이내** (SC-007, 실측 설계 research R6 로 지연 0)

**Constraints**:
- 한 Step 의 총 소요는 그 Step 의 대기 예산을 넘지 않는다 (FR-117, 기존 규칙 유지)
- Step 간 간격은 예산 밖 (FR-105)
- 속도는 판정을 바꾸지 않는다 (FR-104)

**Scale/Scope**: 백엔드 6개 모듈 수정 + 1개 신규, 프론트엔드 3개 화면 수정 + 1개 컴포넌트
신규. 신규 오류 코드 2종.

## Constitution Check

*GATE: Phase 0 이전 통과 필요. Phase 1 이후 재확인.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | ✅ 통과 | Step 종류를 늘리지 않는다. 속도는 세션의 실행 옵션이고 대기는 실행 정책이다. 어느 쪽도 Step DSL 에 필드를 더하지 않는다. `timeout_ms` 는 기존 필드이며 기본값만 바뀐다. |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | ✅ 통과·강화 | 변경 범위(`runner`·`step_executor`·`locator_runtime`·`session`)에 언어모델 호출이 없다. `.importlinter` 의 `execution-no-llm` 계약이 그대로 유효하며, 이번 변경은 그 계약을 지나는 모듈 안에서만 일어난다. FR-104(속도가 판정을 바꾸지 않음)와 FR-118(내보낸 테스트 동일 판정)은 결정성을 **더 강하게** 요구한다. |
| **III. Stateful Interactive Runner** | ✅ 통과·강화 | `한 스텝씩` 은 기존 `PAUSED` 를 재사용한다(research R7). 새 상태도, 새 전이 규칙도 없다. Step 경계에서만 멈추는 기존 불변식을 그대로 따르고, 간격 자체가 Step 경계이므로 편집 안전 지점이 오히려 늘어난다. |
| **IV. Locator Resilience** | ✅ 통과·강화 | 우선순위(`itb.locator.strategy`)를 **바꾸지 않는다.** 폴링은 매 라운드에서 `ordered_strategies()` 순서를 그대로 따른다. `.first` 폴백 제거는 "CSS 가 유일 후보가 되면 안 된다" 와 같은 계열의 강화다 — 모호한 매칭을 조용히 통과시키던 경로가 사라진다. |
| **V. Asset Portability** | ⚠️ 조건부 통과 | FR-110 으로 속도를 테스트 자산에서 구조적으로 배제한다(저장 위치가 다름). 예산 기본값 상향은 생성기가 `step.timeout_ms` 를 그대로 읽으므로 내보낸 코드에 자동 반영된다. **다후보 폴링은 내보낸 테스트에 반영되지 않는다** — 아래 Complexity Tracking 에 기록한다. |

**보안 요건 (조직 mandate)**:
- 비밀값을 새로 다루지 않는다. 대기·간격 로직은 값을 보지 않는다.
- `preferences.json` 은 취향만 담는다. 자격 증명·경로·식별자를 넣지 않는다.
- 읽기 실패를 조용히 넘기지 않는다 — 기본값으로 진행하되 사유를 경고로 알린다 (research R8).
- 폴링 루프의 예외를 삼키지 않는다. 잘못된 셀렉터로 인한 `count()` 실패는 현재처럼
  `count=0` 으로 기록하되, **시도 내역에 남긴다.**

**Phase 1 이후 재확인** (설계 산출물을 만든 뒤):

| 확인 | 결과 |
|---|---|
| 설계가 Step DSL 에 필드를 더했는가 | 아니오 — data-model 요약표가 "Step DSL 바뀌지 않는다" 로 닫혀 있다 |
| 설계가 새 상태·전이를 만들었는가 | 아니오 — data-model §7 이 `state_machine.py` 무수정을 명시 |
| 설계가 우선순위 규칙을 바꿨는가 | 아니오 — 폴링이 매 라운드 `ordered_strategies()` 순서를 따른다 |
| 새 임포트 방향이 계약을 깨는가 | 아니오 — `domain-is-pure` 때문에 `DEFAULT_TIMEOUT_MS` 를 옮기지 않기로 확정(data-model §8). `run_pacing.py` 는 아무것도 임포트하지 않는다 |
| 새 저장 파일이 테스트 자산을 오염시키는가 | 아니오 — `~/.config/itb/preferences.json`, 프로젝트 트리 밖 |
| 원칙 V 이연이 넓어졌는가 | 아니오 — 아래 Complexity Tracking 이 기존 이연의 경계 안임을 기록 |

**품질 게이트**:
1. 원칙 대조 — 위 표. 재실행 경로 변경에 대해 LLM 도달 불가 증거는 `.importlinter` 계약.
2. 왕복 무결성 — 예산 기본값 변경이 생성 코드에 반영되므로 `test_roundtrip.py` 가 검증한다.
3. 테스트 — 대기 알고리즘·간격·설정 저장 각각 단위 테스트, 지연 로딩 픽스처로 통합 테스트,
   속도 4단계 e2e 1건.
4. 비활성 테스트 없음 — 기존 921건을 줄이지 않는다.
5. 성공지표 — 재실행 성공률(PRD §18)에 직접 기여. SC-001·SC-002 가 그 측정이다.

## Project Structure

### Documentation (this feature)

```text
specs/004-run-pacing-readiness/
├── plan.md              # 이 파일
├── spec.md
├── research.md          # Phase 0 — R1~R10, 실측 포함
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── rest-api.md      # 세션 속도 변경 · 설정 조회/저장
│   ├── websocket.md     # pacing_changed 이벤트
│   └── error-contract.md # 신규 오류 코드 2종
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks 산출물)
```

### Source Code (repository root)

```text
backend/src/itb/
├── domain/
│   ├── step.py                    # 수정: DEFAULT_TIMEOUT_MS 5000 → 10000
│   ├── error.py                   # 수정: ELEMENT_NOT_READY · ELEMENT_AMBIGUOUS 추가
│   └── run_pacing.py              # 신규: RunPacing 열거형 + 간격 대응표 (순수)
├── locator/
│   └── strategy.py                # 수정: 대기 상수·정책 문서 (Runner·Generator 공유 지점)
├── execution/
│   ├── locator_runtime.py         # 수정: 다후보 폴링, .first 폴백 제거, 보임 선호
│   ├── step_executor.py           # 수정: 신규 오류 코드 매핑, 대기 시간 기록
│   ├── runner.py                  # 수정: Step 간 간격, 한 스텝씩 자동 일시정지
│   └── session.py                 # 수정: pacing 보유, _pause_requested 이벤트
├── domain/run_result.py           # 수정: StepResult 에 element_wait_ms 추가
├── storage/
│   └── preferences.py             # 신규: ~/.config/itb/preferences.json 읽기·쓰기
├── api/routes/
│   ├── sessions.py                # 수정: 생성 시 pacing, POST /{id}/pacing
│   └── preferences_routes.py      # 신규: GET·PUT /api/preferences
└── schema/export.py               # 수정: 신규 스키마 내보내기

frontend/src/
├── components/
│   └── PacingControl.tsx          # 신규: 속도 선택 (실행 중 변경 가능)
├── pages/
│   ├── Runner.tsx                 # 수정: 속도 컨트롤, 현재 Step 강조
│   ├── RunnerPaused.tsx           # 수정: 한 스텝씩 문구 구별
│   └── RunResult.tsx              # 수정: 대기 시간·신규 오류 코드 표시
└── api/client.ts                  # 수정: 신규 엔드포인트

backend/tests/
├── unit/test_run_pacing.py        # 신규: 간격 대응표, 마지막 Step 예외
├── unit/test_preferences.py       # 신규: 읽기 실패 시 기본값
├── unit/test_error_handling.py    # 수정: 신규 코드 분류
├── integration/test_lazy_loading.py    # 신규: 지연 로딩 픽스처 (SC-001·SC-002)
├── integration/test_pacing_interrupt.py # 신규: 간격 중 일시정지·중지 (SC-007)
├── integration/test_performance.py     # 수정: SC-003 정상 경로 비용
└── e2e/test_us2_replay_and_diagnose.py # 수정: 속도 4단계 판정 동일 (SC-005)

fixtures/sample-app/                # 수정: 지연 로딩 화면 추가
```

**Structure Decision**: 기존 `backend/` + `frontend/` 2계층 구조를 그대로 쓴다. 새 계층을
만들지 않으며, 신규 파일은 4개(`run_pacing.py`, `preferences.py`, `preferences_routes.py`,
`PacingControl.tsx`)뿐이다. 나머지는 기존 모듈 수정이다 — 실행 로직이 이미 한곳에 모여
있어 새 위치가 필요하지 않다.

`run_pacing.py` 를 `domain/` 에 두는 이유: 간격 대응표는 순수 데이터이며 Playwright 도
FastAPI 도 필요 없다. `execution/` 에 두면 화면 계약(스키마 내보내기)이 실행 계층을
임포트하게 된다.

## Phase 요약

| Phase | 산출물 | 상태 |
|---|---|---|
| 0 — Research | [research.md](./research.md) — R1~R10, 결함 실측 재현 포함 | 완료 |
| 1 — Design | [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md) | 완료 |
| 2 — Tasks | tasks.md | `/speckit-tasks` |

## 구현 순서 (Phase 2 입력)

의존 관계상 아래 순서를 지켜야 한다. 같은 묶음 안은 병렬 가능하다.

1. **기반 (병렬)** — `domain/run_pacing.py`, `domain/error.py` 코드 2종,
   `domain/step.py` 기본값, `storage/preferences.py`
2. **대기 알고리즘** — `locator/strategy.py` 상수 → `execution/locator_runtime.py` 폴링
   → `execution/step_executor.py` 오류 매핑 → `domain/run_result.py` 기록 필드
3. **속도** — `execution/session.py` (`_pause_requested`, pacing 보유) →
   `execution/runner.py` (간격, 자동 일시정지)
4. **API** — `api/routes/preferences_routes.py`, `api/routes/sessions.py`,
   `schema/export.py`
5. **화면** — `PacingControl.tsx` → `Runner.tsx` · `RunnerPaused.tsx` · `RunResult.tsx`
6. **픽스처·검증** — 지연 로딩 화면 → 통합·e2e 테스트

**2번을 3번보다 먼저** 하는 이유: 속도 조절이 있으면 대기 결함이 "느려서 그런 것" 으로
보여 검증이 흐려진다. 대기를 먼저 고쳐 SC-001·SC-002 를 독립적으로 확인한다.

## 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| `.first` 폴백 제거로 기존에 통과하던 테스트가 실패한다 | 회귀로 보이지만 실제로는 **잘못된 통과가 드러나는 것**(research R2) | 실패하는 테스트를 되돌리지 않는다. 어느 요소를 잡고 있었는지 확인하고 대상 정의를 고친다. 헌법 품질 게이트 4(테스트를 약화시키지 않는다)를 따른다 |
| 예산 기본값 상향으로 실패 확인이 2배 느려진다 | 디버깅 체감 저하 | 신규 코드 `ELEMENT_NOT_READY` 가 "기다렸으나 안 나타남" 을 즉시 알려 원인 추정 시간을 줄인다. Step 별 조정이 이미 가능하다 |
| 폴링이 대상 앱에 부하를 준다 | 느린 앱에서 더 느려짐 | `count()` 는 CDP 질의이며 네트워크 요청을 만들지 않는다. 라운드당 15ms 실측(R1). 대기 중에만 발생 |
| 속도 설정이 CI·자동 실행을 느리게 한다 | 무인 실행 시간 증가 | 세션 생성 시 명시한 값이 설정 파일보다 우선한다. 무인 경로는 `빠름` 을 명시한다 |
| 자동 일시정지가 AI 세션과 충돌한다 | AI 판단 중 멈춤 | 간격·자동 일시정지는 **저장된 Step 을 실행하는 구간**에만 적용한다. AI 가 다음 동작을 정하는 시간에는 적용하지 않는다 (spec 엣지 케이스) |

## Complexity Tracking

> 헌법 Check 에서 조건부 통과한 항목의 기록. 헌법 Governance "Incremental delivery" 규칙을
> 따른다.

| 위반 | 왜 필요한가 | 기각한 더 단순한 대안 |
|---|---|---|
| **원칙 V — 내보낸 테스트는 다후보 폴링을 하지 않는다.** 제품 안에서 하위 후보로 통과한 Step 이 내보낸 코드에서는 최상위 후보로만 시도된다. | 생성기는 `ordered_strategies()[0]` 하나로 코드를 만든다. 다후보 대기를 표준 Playwright 코드로 내려면 후보별 폴백 헬퍼를 생성 코드에 심어야 하는데, 그것은 "제품 런타임 shim 없이 동작한다" 는 원칙 V 요구와 정면으로 부딪친다. 내보내기 자체가 아직 릴리스 게이트 항목(001 plan)이므로, 지금 생성기를 고치면 Step 모델이 다시 바뀔 때 재작성된다. | *생성 코드에 폴백 루프를 심는다* — 내보낸 프로젝트가 제품 고유 헬퍼에 의존하게 되어 원칙 V 를 더 크게 위반한다. *폴링을 포기한다* — 사용자가 보고한 결함을 고치지 않는 것이다. |

**이번 증분에서 지키는 최소 의무** (헌법 Governance 3항):

- 대기 예산 기본값을 생성 코드에 반영한다. 생성기가 `step.timeout_ms` 를 이미 읽으므로
  코드 변경 없이 자동 반영되며, `test_roundtrip.py` 가 이를 검증한다.
- 폴링 주기·보임 선호 규칙을 `itb.locator.strategy` (Runner·Generator 공유 지점)에 상수와
  문서로 둔다. 생성기가 나중에 다후보 코드를 낼 때 참조점이 하나로 남는다.
- Step DSL 에 필드를 더하지 않는다 — 내보내기를 더 어렵게 만드는 변경이 없다.

**복구 경로**: 내보내기 구현 시 "다후보 대기를 표준 Playwright 로 표현" 을 함께 설계한다.
릴리스 게이트 항목으로 등록한다.

**주의**: 원칙 V 의 이 항목은 001 에서 이미 한 번 기록된 계열이다. 헌법은 "같은 항목이 두
증분에 걸쳐 이연되면 개정 제안이나 범위 결정의 근거" 라고 정한다. 004 는 이연을 **새로
만들지 않고** 기존 이연의 경계 안에 머무른다 — 내보내기가 아직 구현되지 않았다는 사실이
바뀌지 않았기 때문이다. 다음 증분에서 내보내기를 다룰 때 이 항목을 함께 닫아야 한다.
