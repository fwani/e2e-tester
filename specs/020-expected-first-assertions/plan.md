# Implementation Plan: 기대 동작 기준 검증

**Branch**: `020-expected-first-assertions` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-expected-first-assertions/spec.md`

---

## Summary

저장된 테스트 정의를 **제품 동작의 사본**에서 **사용자의 요구서**로 바꾼다. 그러려면 세
가지가 함께 바뀌어야 한다.

| # | 바뀌는 것 | 어디 |
|---|---|---|
| 1 | 검증 Step 은 작성 시점에 통과하지 않아도 기록된다 | `authoring/tools.py` · `domain/step.py` |
| 2 | 검증 실패가 실행을 멈추지 않는다 | `execution/runner.py` |
| 3 | 실패한 검증이 알려진 결함 / 회귀로 갈린다 | `domain/run_result.py` · `ResultView.tsx` |

새 의존성이 없다. 새 화면이 없다. **새 엔티티는 셋**뿐이고 (`AuthoringMismatch` ·
`AssertionClass` · `BlockedKind`), 셋 다 기존 모델에 붙는 부가 정보다.

가장 큰 구조적 변화는 3번이 아니라 **2번**이다 — `Runner.run_step()` 의 중단 규칙은 001
이래 「실패하면 멈춘다」 하나였고, 그것을 Step 종류로 가른다.

---

## Technical Context

**Language/Version**: Python 3.12+ (백엔드) · TypeScript 5 / React 19 (프론트엔드)

**Primary Dependencies**: FastAPI · Playwright for Python · Pydantic v2 · Anthropic SDK
(작성 경로 전용) · Vite · Tailwind + shadcn 계열 UI. **새 의존성 없음.**

**Storage**: 파일. 테스트 정의(플레인 텍스트) · 실행 결과 `.runs/<테스트ID>/result.json`.
**마이그레이션 없음** — 새 필드의 기본값이 호환을 만든다.

**Testing**: pytest (`backend/scripts/test-backend.sh` — 병렬 계층 + `-m timing` 순차 계층) ·
vitest + `tsc --noEmit` (프론트엔드)

**Target Platform**: 로컬 데스크톱에서 도는 웹 애플리케이션 (백엔드 + 브라우저)

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 이 기능은 성능 목표를 새로 세우지 않는다. **단, 실행 시간이
길어진다** — 검증 실패 후 계속 진행하므로 전에는 돌지 않던 Step 이 돈다. 이것은 의도한
비용이며 Step 당 예산(`timeout_ms`)은 그대로다.

**Constraints**:
- 헌법 원칙 I — 새 필드가 실행 판정을 바꾸면 안 된다
- 헌법 원칙 II — 재실행 경로에 LLM 호출이 추가되면 안 된다
- 헌법 원칙 V — 내보낸 Playwright 테스트가 같은 검증을 해야 한다
- 도구 표면 계약 — `TOOL_NAMES` 16종 · `STEP_PRODUCING_TOOLS` 9종 ↔ Step 종류 1:1 유지
- 스키마 단일 출처 — 백엔드 Pydantic 이 권위, TypeScript 는 생성물

**Scale/Scope**: 백엔드 모듈 7개 · 프론트엔드 화면 3개(Step 목록 · Step 상세 · 결과) ·
생성 스키마 2개 · 문서 1개(`docs/prd.md`).

---

## Constitution Check

*GATE: Phase 0 전 통과 · Phase 1 후 재확인*

### 초기 평가 (Phase 0 전)

| 원칙 | 위험 | 판정 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | 새 필드가 실행 방식을 바꾸면 위반. 사람/AI 가 다른 모델을 쓰면 위반 | **통과** — `mismatch` 는 `AssertionStep` 의 부가 정보이고 작성 주체와 무관하다. 원칙이 허용하는 「MAY be recorded as metadata」에 해당 |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 알려진 결함/회귀 판정이 LLM 을 부르면 위반 | **통과** — 판정은 저장된 `mismatch` 와 `outcome` 의 결정적 조합. 순수 함수 |
| **III. Stateful Interactive Runner** | 어긋남 후 세션이 죽으면 위반 | **통과** — 어긋남은 상한에 중립이고(R5), 검증 실패는 실행을 멈추지도 않는다(R8). 원칙과 **같은 방향** |
| **IV. Locator Resilience** | — | **해당 없음** |
| **V. Asset Portability** | 내보낸 테스트가 검증을 빠뜨리면 위반 | **통과** — 생성기가 `mismatch` 를 읽지 않는다. 검사로 고정 (C-3) |

**보안 제약**: `mismatch.observed` 는 화면에서 읽은 텍스트다. **저장 시점에 `Scrubber` 를
거친다** — 헌법의 「Recorded input values … MUST be masked in UI, logs, screenshots
metadata, and exports」가 그대로 걸린다.

**품질 게이트**:
- 라운드트립 무결성 — Step DSL 을 바꾸므로 `record → store → replay → export → run` 전량 필요
- 비활성 테스트 금지 — FR-033 이 기존 실행 동작을 바꾸므로 **기존 검증이 깨질 수 있다.**
  깨진 검증은 지우지 않고 **새 기대로 고친다**
- 성공 지표 영향 — FR-030 이 PRD §18 문면을 고친다 (R11)

### 재평가 (Phase 1 설계 후)

| 원칙 | 설계가 만든 것 | 판정 |
|---|---|---|
| I | I-1·I-2 불변식과 그것을 고정하는 검사 C-2·C-3 | **통과 · 강화됨** — 원칙이 코드가 아니라 검사로 지켜진다 |
| II | `classify_assertion` 순수 함수. 기존 `test_replay_no_llm.py` 가 계속 돈다 | **통과** |
| III | `failed_index` 를 설정하지 않는 규칙 (R8) | **통과** |
| V | 생성기 무변경 + C-3 | **통과** |

**위반 없음.** Complexity Tracking 은 비워 둔다.

---

## Project Structure

### Documentation (this feature)

```text
specs/020-expected-first-assertions/
├── plan.md                    # 이 파일
├── spec.md
├── research.md                # R1~R12
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
├── contracts/
│   ├── tool-surface.md        # 도구 입출력 · 지침 · 이벤트
│   └── execution.md           # 중단 규칙 · 결말 · 분류 · 화면
└── tasks.md                   # /speckit-tasks 산출물
```

### Source Code (repository root)

```text
backend/src/itb/
├── domain/
│   ├── assertion.py           # + AuthoringMismatch
│   ├── step.py                # + AssertionStep.mismatch
│   └── run_result.py          # + AssertionClass, StepResult.assertion_class,
│                              #   classify_assertion(), counts_by_class()
├── authoring/
│   ├── agent.py               # SYSTEM_PROMPT 검증 절, AgentOutcome.blocked_kind
│   ├── blocked.py             # + BlockedKind
│   ├── tools.py               # _execute(keep_on_failure), assert_condition,
│   │                          #   AttemptLimits.record_mismatch, report_blocked(kind),
│   │                          #   TOOL_SCHEMAS 문구
│   └── nl_step.py             # NL_STEP_SYSTEM_HINT 검증 규칙
├── execution/
│   └── runner.py              # run_step 중단 규칙, assertion_class 채우기
├── api/
│   ├── routes/sessions.py     # ai_finished.mismatch_count
│   └── ws/session_events.py   # ai_blocked.kind
└── schema/export.py           # (변경 없음 — 새 필드가 자동으로 실린다)

backend/schema/                # 재생성: step.schema.json, run-result.schema.json

frontend/src/
├── types/generated/           # 재생성: step.d.ts, run-result.d.ts
├── components/
│   ├── Badges.tsx             # 결함 후보 칩
│   └── workbench/
│       ├── StepList.tsx       # 행 표시
│       └── StepDetail.tsx     # 기대/관찰, 표시 걷어내기
├── pages/ResultView.tsx       # 회귀 / 알려진 결함 / 해소됨
├── lib/wording.ts             # 분류 라벨 — 화면이 문구를 직접 만들지 않는다
└── theme/tone.ts              # 칩 색 역할

fixtures/sample-app/           # + 결함이 있는 화면 (기대와 다른 값을 내놓는 폼)

docs/prd.md                    # §18 Replay Success Rate 판정 단위 문장 (R11)
```

**Structure Decision**: 기존 백엔드/프론트엔드 2계층 구조를 그대로 쓴다. 새 디렉터리를
만들지 않는다 — 이 기능은 새 능력이 아니라 **기존 경로 다섯 곳의 판단을 고치는 것**이다.

---

## 구현 순서의 제약

의존 관계가 순서를 정한다. `/speckit-tasks` 가 이것을 작업으로 편다.

```
① 도메인 (AuthoringMismatch · mismatch · AssertionClass · BlockedKind)
   │   여기가 먼저여야 나머지가 참조할 타입이 생긴다
   ├──② 작성 경로 (tools · agent · nl_step)         → US1 · US2 · US4
   ├──③ 실행 경로 (runner · classify)               → US3 · US6
   └──④ 스키마 재생성 → ⑤ 프론트엔드                → US2 · US3 · US5
                                                      (③ 없이 ⑤의 결과 화면은 검증 불가)
⑥ 문서 (docs/prd.md §18)
```

**②와 ③은 서로 독립이다.** 병렬로 진행할 수 있고, 각각 단독으로 검증된다 — ②는 AI 작성
경로만, ③은 손으로 만든 `mismatch` 를 넣은 정의만 있으면 된다 (헌법 원칙 I 덕분이다).

---

## 위험과 대응

| 위험 | 크기 | 대응 |
|---|---|---|
| **FR-033 이 기존 검증을 깬다** — 검증 실패 후 멈춤을 전제한 통합 테스트가 있다 | 높음 | 깨진 검증을 지우지 않는다(품질 게이트 4). 새 기대로 고치고, 고친 이유를 검증에 적는다. `tests/us5_support.py` 가 「중간 Step 에서 반드시 실패하는 테스트」를 쓰고 있어 직접 영향권이다 |
| **모델이 지침을 어기고 기대값을 바꾼다** | 중간 | 지침만으로는 못 막는다. 도구 반환값(`assertion_failed` + `note`)과 상한 중립(R5)이 구조적 방어다. 「값을 바꾸지 마라」는 셋째 겹 |
| **결과 화면이 실패로 가득 찬다** | 중간 | 사실이므로 줄이지 않는다. 분류가 읽을 순서를 준다 (FR-020). 0건 분류는 싣지 않는다 |
| **`mismatch` 가 실행·생성 경로로 샌다** | 낮지만 치명적 | 검사 C-2·C-3 로 고정. 원칙 I·V 위반이 조용히 들어오는 유일한 경로다 |
| **민감값이 `observed` 로 샌다** | 낮지만 치명적 | 저장 시점 `Scrubber` 1회. 화면에서 다시 거르지 않는다 — 거르는 곳이 둘이면 기준이 사라진다 |
| 고정 대상 추가가 기존 검증에 영향 | 낮음 | 새 파일만 더한다. 기존 고정 대상을 고치지 않는다 |

---

## 범위 밖 (명시)

- **엑셀 입출력**(014) — Step DSL 왕복이 아니라 계획 수준의 표다. `mismatch` 를 나르지
  않는다 (R9). 이것이 결함이라면 별도 기능이다.
- **검증 종류 확장** — `visible`·`hidden`·`text`·`url` 4종 그대로.
- **결함 추적 시스템 연동 · 버그 리포트 자동 생성.**
- **AI 가 결함 여부를 판정하는 것** — 제품은 「기대와 달랐다」는 사실만 기록한다.
- **계속 진행을 끄는 설정** — 두지 않는다. 끌 수 있으면 결과를 읽는 사람이 실행 설정을
  먼저 확인해야 한다 (spec Assumptions).

---

## Complexity Tracking

> Constitution Check 에 위반이 없다. 이 표는 비어 있다.

정당화할 위반 없음.
