# Implementation Plan: 사람이 말한 것을 AI 가 같은 화면에서 본다

**Branch**: `025-ai-instruction-context` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/025-ai-instruction-context/spec.md`

---

## Summary

AI 작성이 대화를 이어갈수록 어긋나는 원인을 **세 층에서** 고친다.

1. **턴 사이** — 한 턴이 끝나면 그 턴의 관찰·동작·막힘·응답이 전부 버려진다 (research R1
   실측). 턴이 끝날 때 **수행 기록**을 어시스턴트 차례로 이력에 남긴다.
2. **사람의 말과 화면 사이** — 관찰이 수집하는 것은 태그·속성으로 판정한 요소뿐이라,
   React 앱에서 클릭되는 `<div>` 가 목록에 없다. **커서 표시**를 신호로 범위를 넓히고,
   사람이 쓰는 낱말로 찾는 도구를 준다.
3. **요구받은 것** — 매 턴 다시 주어지는 것이 「내가 만든 Step」 하나뿐이다. 거친 지시문을
   한 번 정제한 **작업 계획**(제약 + 항목 + 진척)을 정본으로 삼아 함께 주입한다.

더해서, 한 턴 안에 쌓이는 낡은 화면 관찰을 접어 위의 것들이 실릴 자리를 만든다.

**설계의 중심 판단**: 016 이 정한 것을 뒤집지 않는다. 계획 주입은 정의 요약과 **같은 자리**에서
같은 예산·축약·민감값 규칙을 쓰고, 소유권은 `SessionWork` 에 두고 함수로 주입한다.

---

## Technical Context

**Language/Version**: Python 3.13 (backend) · TypeScript 5 / React 19 (frontend)

**Primary Dependencies**: FastAPI · Playwright for Python · `anthropic` SDK 1.3.0
(`beta.messages.tool_runner`) · Vite · Vitest

**Storage**: 계획·수행 기록은 세션 메모리. 정제 기록만 테스트 자산에 의도 기록으로 저장

**Testing**: `bash scripts/test-backend.sh` (백엔드 — `uv run pytest` 는 `timing` 계층을
병렬에 섞어 틀린 결과를 준다) · `npx vitest run` (프론트) · `uv run lint-imports` (헌법
원칙 II 계약)

**Target Platform**: 로컬 데스크톱에서 도는 웹 앱 (백엔드 + 브라우저)

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 관찰 한 번의 지연이 지금보다 눈에 띄게 늘지 않을 것. 정제는 세션
시작 전 1회

**Constraints**: 매 턴 앞머리 주입 총량 16KB 유지 (016 이 정한 값) · 수행 기록 32KB ·
관찰 목록 200개 상한 유지

**Scale/Scope**: 계획 항목 최대 200 · 한 지시의 도구 호출 상한 40 · 관찰 요소 상한 200

---

## Constitution Check

*GATE: Phase 0 전에 통과해야 하고, Phase 1 뒤 다시 본다.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. 단일 Step 모델** (NON-NEGOTIABLE) | 통과 | 계획·수행 기록·조작 가능 근거 중 어느 것도 Step 을 만들거나 바꾸지 않는다. `cursor` 로 발견된 요소도 같은 로케이터 후보 수집을 지나 같은 Step 이 된다 — 발견 경로가 Step 의 모양을 바꾸지 않는다 (FR-037·contracts/observation.md §7) |
| **II. 결정적 재생** (NON-NEGOTIABLE) | 통과 | 정제는 작성 시점의 1회다. 계획·수행 기록은 세션에 살고 실행 경로에서 읽히지 않는다. 새 코드는 `itb.authoring` 에 두므로 `.importlinter` 의 `execution-no-llm` 계약이 **구조로** 막는다 (FR-035·FR-036) |
| **III. 상태 있는 대화형 러너** | 통과 · **강화** | 이 기능의 핵심이 인수·재개를 실제로 동작하게 만드는 것이다. 남은 항목이 재개 지시에 실린다 (FR-026) |
| **IV. 로케이터 복원력** | 통과 | 후보 수집과 우선순위를 건드리지 않는다. 경로가 하나로 좁혀지지 않는 요소는 지금과 같이 거절된다 (FR-046). 수행 기록에 요소 참조를 남기지 않는 것도 같은 방향이다 |
| **V. 자산 이식성** | 통과 | 계획은 테스트 자산이 아니다. 정제 기록을 의도 기록으로 보관하는 것은 원칙 II 가 명시적으로 허용한 범위다 |

**품질 게이트**

| 게이트 | 계획 |
|---|---|
| 1. 원칙 준수 | `lint-imports` 가 원칙 II 를 기계로 확인한다. 작업 목록에 넣는다 |
| 2. 왕복 무결성 | Step DSL·녹화·생성기를 바꾸지 않는다. 관찰 범위 확대가 녹화를 건드리지 않음을 회귀로 확인한다 (FR-045) |
| 3. 테스트 | **research R1 이 드러낸 빈칸을 메운다** — 지금 검증은 가짜 드라이버가 SDK 의 messages 처리를 대체해 이력 유실을 잡지 못했다. 실제 tool runner 의 계약을 직접 확인하는 검증을 넣는다 |
| 4. 비활성 테스트 금지 | 없음 |
| 5. 성공 지표 | PRD §18 의 자연어 변환 성공률·인수 복구에 직접 영향. 각 US 의 Independent Test 가 그 측정이다 |

**위반 없음. Complexity Tracking 에 적을 이연 항목이 없다.**

---

## Project Structure

### Documentation (this feature)

```text
specs/025-ai-instruction-context/
├── plan.md                    # 이 파일
├── spec.md
├── research.md                # R1~R13
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api-contract.md        # 정제 엔드포인트 · 계획 조회/수정 · 이벤트
│   ├── agent-context.md       # 모델에게 가는 것 — 주입·수행 기록·접기·mark_item
│   └── observation.md         # 관찰 범위 · actionability · find_by_text
├── checklists/
│   └── requirements.md
└── tasks.md                   # /speckit-tasks 가 만든다
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── authoring/
│   │   ├── plan.py            # 신규 — WorkPlan·PlanItem·Constraint, 상태 전이
│   │   ├── refine.py          # 신규 — 지시문 정제 (LLM 1회, 도구 호출로 구조 강제)
│   │   ├── journal.py         # 신규 — 턴 저널 → 수행 기록 문자열
│   │   ├── fold.py            # 신규 — 턴 내부 낡은 관찰 접기
│   │   ├── summary.py         # 수정 — 계획 주입 문자열을 여기서 함께 만든다
│   │   ├── agent.py           # 수정 — 턴 끝에 어시스턴트 차례 추가, plan_source 주입
│   │   ├── tools.py           # 수정 — mark_item·find_by_text, actionability, 저널 수집
│   │   └── claude_code_driver.py  # 수정 — 접기 비적용 사유 주석
│   ├── recording/injected/
│   │   └── recorder.js        # 수정 — __itbObserve 2단계 후보 수집 (INTERACTIVE 는 유지)
│   └── api/routes/
│       ├── instruction.py     # 신규 — POST /api/instruction/refine
│       └── sessions.py        # 수정 — work_plan 수용, 계획 조회/수정, plan_progress
└── tests/
    ├── unit/
    │   ├── test_work_plan.py          # 상태 전이·순번·거절
    │   ├── test_turn_journal.py       # 무엇을 남기고 무엇을 남기지 않는가
    │   ├── test_plan_injection.py     # 주입 문자열·예산·축약·민감값
    │   └── test_observation_fold.py   # 접기 규칙
    ├── contract/
    │   ├── test_instruction_refine.py # 정제 엔드포인트 (성공·실패 둘 다 200)
    │   ├── test_plan_api.py           # 조회·수정·이벤트
    │   └── test_tool_runner_history.py  # **R1 의 빈칸** — SDK 계약 직접 확인
    ├── integration/
    │   ├── test_resume_continuity.py  # US1 — 재개가 이어지는가
    │   └── test_plan_progress.py      # US5 — 진척과 남은 항목
    └── e2e/
        └── test_actionable_elements.py  # US3 — 클릭되는 div 를 찾는가

frontend/
├── src/
│   ├── pages/ComposeView.tsx          # 수정 — 정제 결과 확인·수정
│   ├── components/workbench/
│   │   ├── PlanPanel.tsx              # 신규 — 진척 목록
│   │   └── AiAuthoringPanel.tsx       # 수정 — 남은 항목 표시
│   ├── api/client.ts                  # 수정 — refine·plan 호출
│   └── api/ws.ts                      # 수정 — plan_progress 이벤트
└── tests/
    ├── PlanPanel.test.tsx
    ├── ComposeRefine.test.tsx
    └── PlanProgress.test.ts
```

**Structure Decision**: 기존 웹 앱 구조를 그대로 쓴다. 새 모듈은 전부 `itb.authoring` 아래
둔다 — 그 자리가 `.importlinter` 로 실행 계층과 끊겨 있어 헌법 원칙 II 가 구조로 보장되는
유일한 곳이다. 관찰 스크립트만 `itb.recording.injected` 에 있는데, 그것은 브라우저에 주입되는
JS 이고 언어모델과 무관하다.

---

## 구현 순서와 그 이유

US 우선순위와 **의존 관계**가 다른 자리가 있다. 순서는 이렇게 간다.

| 단계 | 내용 | 왜 이 순서인가 |
|---|---|---|
| 1 | **R1 의 빈칸을 메우는 검증** | 고치기 전에 「지금 유실된다」를 실패하는 테스트로 고정한다. 그러지 않으면 고친 뒤에도 무엇이 달라졌는지 말할 수 없다 |
| 2 | **US1 — 턴 사이 이력 보존** | 다른 모든 것의 토대다. 이력이 이어지지 않으면 계획을 주입해도 재개가 성립하지 않는다 |
| 3 | **US3 — 관찰 범위** | 이것이 막히면 나머지가 값을 내지 못한다. US1 과 독립이므로 병행 가능 |
| 4 | **US2 — 계획 주입** | 계획이 없어도 동작하는 경로를 먼저 확인한 뒤, 계획이 있을 때 붙는다 |
| 5 | **US4 — 정제** | US2 가 붙이는 것의 질을 결정한다. 정제 없이도 US2 가 성립하므로 뒤 |
| 6 | **US5 — 진척** | US4 의 항목 위에서 성립 |
| 7 | **US6 — 턴 내부 접기** | P3. research R4 의 「확인 필요」가 부정이면 **이 단계만 빼고 끝낸다** |

**7단계가 실패해도 1~6 이 온전하다.** 접기는 다른 것들이 매여 있지 않은 유일한 조각이며,
그것이 이 순서를 고른 이유다.

---

## 위험과 대응

| 위험 | 징후 | 대응 |
|---|---|---|
| `set_messages_params` 로 접은 것을 runner 가 되돌린다 | 접기가 적용되지 않거나 메시지가 중복된다 | research R4 의 「확인 필요」. 구현 시 실측하고, 어긋나면 US6 를 이번 증분에서 뺀다 |
| 커서 판정으로 목록이 부푼다 | 관찰 결과가 상한에 상시로 걸린다 | 조상 중복 제거가 1차 방어. 실측으로 후보 좁히기 조건을 조정한다. `find_by_text` 가 잘린 경우의 보완책이다 |
| 관찰이 느려진다 | 「화면을 살펴보는 중」이 길어진다 | 2단계 후보를 먼저 좁힌 뒤에만 `getComputedStyle` 을 돈다 (research R13). 실측값을 작업에 남긴다 |
| 정제가 사용자 뜻을 바꾼다 | 구체값이 합쳐지거나 사라진다 | 사용자 확인 단계가 1차 방어 (FR-018). 구체값 보존을 검증으로 고정한다 (FR-015) |
| 예산 배분이 어긋나 축약이 상시로 일어난다 | 계획이 늘 부분만 보인다 | 016 이 8KB → 16KB 로 고친 전례. **실측 작업을 목록에 넣는다** (research R6) |
| 자격 증명이 매 턴 실린다 | 평문 비밀번호가 반복 노출 | 정제 단계에서 변수 참조로 치환 (FR-010·research R10). 못 잡은 것이 지금 수준으로 남는 것이 하한 |

---

## 무엇을 하지 않는가

- **대화 이력을 모델로 요약해 접지 않는다.** 수행 기록은 제품이 아는 사실로 만든다.
- **`INTERACTIVE` 상수와 녹화 경로를 건드리지 않는다.** 관찰 전용 후보 수집을 따로 둔다.
- **`response_format` 을 쓰지 않는다.** 이 모델에서의 동작을 이 저장소가 실측한 적이 없다.
  정제는 도구 호출로 구조를 강제한다.
- **기존 세션 생성 경로를 바꾸지 않는다.** `work_plan` 은 선택 항목이고, 없으면 지금과 같이
  동작한다.
- **프롬프트 캐싱을 도입하지 않는다.** 지금 쓰고 있지 않고(research R11), 이 기능이 그것을
  막지 않게만 둔다.
