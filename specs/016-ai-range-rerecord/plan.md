# Implementation Plan: 편집 중 AI 구간 재녹화

**Branch**: `016-ai-range-rerecord` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-ai-range-rerecord/spec.md`

## Summary

편집 화면에서 Step n~m 을 골라 「AI 로 다시 만들기」를 누르면, 제품이 구간 직전까지
실행해 도착점을 만들고, 사용자가 채팅으로 지시하며 그 구간을 새 Step 으로 교체한다.

**만드는 것은 능력이 아니라 배선이다.** 필요한 부품은 이미 다 있다 — 도착점 만들기
(`pause_before_index`), 지정 위치 삽입(`StepCompiler.insert_at`), 전부-또는-전무 삭제
(`delete_steps`), 순수 편집 함수(`step_edits`), 대화 이어쓰기(`AuthoringAgent.messages`),
막힘 5선택지(`blocked.py`). 이 기능은 그것들을 하나의 조작으로 묶고, 세 가지를 새로 만든다:

1. **정의 요약을 에이전트 컨텍스트에 싣는다** — 값은 읽지 않는다 (R8)
2. **편집 도구 4종을 도구 표면에 노출한다** — 사람 편집과 같은 순수 함수를 지난다 (R2·R3)
3. **교체 트랜잭션** — 스냅샷 없이 id 목록 둘로 표현한다 (R7)

상태 기계는 전이 하나(`PAUSED + BEGIN_AI → AI_RUNNING`)만 늘고, 국면은 늘지 않는다 (R4).
조작은 42 → 46 이 된다.

## Technical Context

**Language/Version**: Python 3.13.0 (backend) · TypeScript 5 / Node 23.7.0 (frontend)

**Primary Dependencies**: FastAPI · Playwright 1.62.0 · Anthropic SDK (`tool_runner`) ·
React 19 · Tailwind CSS · Vitest · pytest · import-linter

**Storage**: 테스트 정의는 `~/.local/share/itb/projects/<프로젝트>/tests/*.yaml` 평문 YAML.
**이 기능은 저장 형식을 바꾸지 않는다** — 대화 이력도 트랜잭션 상태도 디스크에 쓰지 않는다.

**Testing**: `uv run lint-imports` (최우선) · `uv run ruff check` · `uv run pytest` ·
`uv run python -m itb.schema.export --check` · `npx tsc --noEmit` · `npm test -- --run`

**Target Platform**: 단독 로컬 도구. 127.0.0.1 바인딩. macOS 26.2 arm64 확인.

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 도착점 만들기는 앞 구간 Step 수에 비례한다 — 새 지연을 만들지
않는다. 정의 요약 생성은 Step 수에 선형이고 요청당 1회다.

**Constraints**:
- 도구 호출 상한은 구간 크기와 무관 (FR-042) — 기존 `MAX_TOOL_CALLS = 40` 유지
- 정의 요약이 지시문 상한(`MAX_INSTRUCTION_CHARS`)과 별개 예산을 갖는다 (FR-006)
- 확정되지 않은 교체는 디스크에 닿지 않는다 (FR-029)

**Scale/Scope**: Step 100개 규모 테스트까지. 백엔드 파일 약 8개 수정 + 2개 신규,
프론트 파일 약 7개 수정 + 2개 신규.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | **통과** | AI 편집 도구가 사람 편집과 **같은 순수 함수**(`step_edits`)를 지난다 (R2). Step 모델에 필드를 더하지 않는다 — 「교체 대상」은 세션이 들고 화면이 계산한다 (R7). `STEP_PRODUCING_TOOLS` ↔ Step 종류 1:1 검사는 그대로다 (R3) |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | **통과** | `execution-no-llm` 계약은 단방향 금지이고 `authoring → execution` 은 이미 허용·사용 중이다. 배선은 `itb.api` 에 둔다 (R1). 시간 축 검사 2개를 새로 세운다 — 러너·에이전트 태스크 비동시성, 도착점 구간 드라이버 호출 0회 (R9) |
| **III. Stateful Interactive Runner** | **통과** | 막히면 세션 유지(FR-041, 기존 `AI_BLOCKED` 경로 재사용). 버리기가 세션을 끝내지 않고 도착점으로 되맞춘다 (FR-031·FR-031a) — 불변식 3(편집은 화면에 반영된다)을 정면으로 다룬다 |
| **IV. Locator Resilience** | **통과** | AI 의 대상 재지정도 후보 묶음을 **살아 있는 페이지에서** 새로 수집한다. `element_ref` 만 받고 셀렉터를 받지 않는다 (FR-035·R2) |
| **V. Asset Portability** | **통과 (영향 없음)** | DSL 을 바꾸지 않는다. 저장 형식·Generator·Export 경로를 건드리지 않는다 |

**보안 요구**:
- 비밀값 하드코딩 없음 — 새 자격 증명 경로를 만들지 않는다
- 민감값: 정의 요약이 `value` 를 **읽지 않는다** (R8). 대화 이력은 디스크에 쓰지 않는다
- 경계 검증: 채팅 입력에 기존 지시문과 같은 상한·검증 적용 (FR-010). 구간 지정은 Step id
  존재·연속성·다른 세션 점유를 경계에서 검증
- 오류 명시 처리: 새 오류는 003 의 `category`·`next_action` 계약을 따른다

**품질 게이트**:
- Round-trip integrity: Step DSL 을 바꾸지 않으므로 record→store→replay 왕복이 그대로다.
  다만 재녹화로 만든 Step 이 이어 붙은 정의의 전체 실행을 검증한다 (SC-005)
- 테스트: 단위(요약·트랜잭션·도구 분류·상태 전이) + 통합(US1·US2·US3 각 1개 이상)
- 성공지표: SC-001·SC-002(조작 횟수)는 PRD §18 「테스트 생성 시간」에 직접 걸린다

**Complexity Tracking**: 위반 없음. 이연 항목 없음. (기존 릴리스 게이트 RG-1
Playwright Export 는 이 기능과 무관하며 새로 미루지도 않는다.)

---

## 명세 조정 (계획 단계의 발견)

R6 이 명세의 가정 하나를 무효로 만들었다. spec.md 를 함께 고친다.

| 항목 | 초안 | 조정 | 근거 |
|---|---|---|---|
| US1 Independent Test | "브라우저를 열지 않고 편집 화면에서 채팅 칸에" | "재녹화 세션 안에서, Step 을 만들지 않는 질문으로" | R6 — 채팅은 세션 안에서만 산다 |
| US1 Acceptance 1 | 편집 화면에서 바로 질문 | 세션이 열린 뒤 질문 | 같음 |
| US1 Acceptance 3·4 | 편집 화면의 채팅 자리 잠김 | 「AI 로 다시 만들기」 조작의 잠김 | 채팅 조작이 편집 국면에 없다 |
| Assumptions | "브라우저 없이 대화만 하는 경우가 있을 수 있으므로 계획 단계에서 판정한다" | 판정 완료 — 없다 | R6 |

명세의 FR 은 바뀌지 않는다. FR-007(평시에 먼저 말을 건다)은 **세션 안에서** 성립한다.

---

## Project Structure

### Documentation (this feature)

```text
specs/016-ai-range-rerecord/
├── plan.md              # 이 파일
├── research.md          # R1~R9 결정
├── data-model.md        # 엔티티·상태 전이·불변식
├── quickstart.md        # 검증 절차
├── contracts/
│   ├── api-contract.md      # REST 델타 · SessionView 델타 · 이벤트
│   ├── ui-contract.md       # 조작 4개 추가 · 개칭 2개 · 국면표 델타
│   └── agent-tools.md       # 도구 표면 델타 (편집 도구 4종)
├── checklists/
│   └── requirements.md  # specify 단계 산출
└── tasks.md             # tasks 단계 산출
```

### Source Code

```text
backend/src/itb/
├── authoring/
│   ├── summary.py          ★신규 — 정의 요약 (값을 읽지 않는다, R8)
│   ├── rerecord.py         ★신규 — 교체 트랜잭션 (R7)
│   ├── tools.py            수정 — 편집 도구 4종 · 분류 튜플 4개 (R3)
│   ├── agent.py            수정 — 컨텍스트 주입 · 턴 종료 처리 분기 (R4)
│   └── claude_code_driver.py  수정 — 새 도구가 MCP 표면에 따라 들어온다
├── execution/
│   ├── state_machine.py    수정 — PAUSED + BEGIN_AI → AI_RUNNING (R4, 한 줄)
│   └── step_edits.py       무변경 ← AI 가 그대로 쓴다 (R2)
├── api/routes/
│   └── sessions.py         수정 — mode=rerecord · 채팅 · 확정 · 버리기 (R5)
└── schema/export.py        수정 여부는 새 모델이 생길 때만 (헌법 Cross-language duty)

backend/tests/
├── unit/
│   ├── test_definition_summary.py   ★신규 — 값 비유출 property (SC-008)
│   ├── test_rerecord_transaction.py ★신규 — 확정·버리기 (SC-004)
│   ├── test_agent_edit_tools.py     ★신규 — 사람 편집과 같은 함수 (SC-006)
│   └── test_tool_surface.py         수정 — 네 분류 합집합 검사 (R3)
├── test_principle_ii_timeline.py    ★신규 — 태스크 비동시성·드라이버 0회 (R9)
└── us_rerecord/                     ★신규 — US1·US2·US3 통합

frontend/src/
├── lib/
│   ├── actions.ts          수정 — 조작 4개 추가 · 2개 개칭 (42 → 46)
│   └── capabilities.ts     수정 — 4개 조작 × 10 국면 행 채우기
├── components/workbench/
│   ├── ChatPanel.tsx       ★신규 — 대화 자리
│   ├── RerecordBar.tsx     ★신규 — 구간 표시 · 확정 · 버리기
│   ├── StepList.tsx        수정 — 「교체 대상」 표시 (세션이 준 id 로 계산)
│   └── model.ts            수정 — 재녹화 상태를 모델에 싣는다
└── api/client.ts           수정 — 새 엔드포인트 · SessionView 델타

frontend/tests/
├── ChatPanel.test.tsx           ★신규
├── RerecordTransaction.test.tsx ★신규
├── CapabilityCoverage.test.ts   수정 — 46개 조작
└── CapabilityUI.test.tsx        수정 — 새 조작의 자리
```

**Structure Decision**: 기존 backend/frontend 2원 구조를 그대로 쓴다. 새 최상위 디렉터리를
만들지 않는다. 신규 백엔드 모듈 2개는 **`itb.authoring` 안**에 둔다 — 둘 다 언어모델
경계 안쪽의 관심사이고, `itb.execution` 에 두면 `execution-no-llm` 계약에 걸린다.

---

## Phase 0: Outline & Research

**완료.** [research.md](./research.md) — R1~R9. NEEDS CLARIFICATION 잔여 0건.

핵심 결정 요약:

| # | 질문 | 결정 |
|---|---|---|
| R1 | AI 세션이 실행을 불러도 되는가 | 된다. 계약은 단방향 금지이고 배선은 `itb.api` 에 둔다 |
| R2 | 편집 도구가 쓸 함수 | `step_edits` 를 그대로. 옮기지 않는다 |
| R3 | 도구 표면 계약 | 12 → 16. 네 분류 튜플의 합집합을 검사한다 |
| R4 | 상태 기계 | 전이 하나만 추가 (`PAUSED + BEGIN_AI`) |
| R5 | 세션 생성 | 새 모드 `rerecord` (authoring_mode=ai + 러너) |
| R6 | 브라우저 없는 채팅 | **성립하지 않는다.** 채팅은 세션 안에서만 |
| R7 | 되돌리기 | 스냅샷 불필요. id 목록 둘로 충분 |
| R8 | 민감값 | 요약이 `value` 를 읽지 않는다 |
| R9 | 원칙 II 증명 | 린터 + 시간 축 검사 2개 |

---

## Phase 1: Design & Contracts

**완료.** 산출물 넷:

- [data-model.md](./data-model.md) — 엔티티 4개, 상태 전이 델타, 불변식 6개
- [contracts/api-contract.md](./contracts/api-contract.md) — REST 4개, `SessionView` 델타, 이벤트 3개
- [contracts/ui-contract.md](./contracts/ui-contract.md) — 조작 46개, 국면표 델타 4행 × 10열
- [contracts/agent-tools.md](./contracts/agent-tools.md) — 도구 16종, 편집 도구 4종 상세
- [quickstart.md](./quickstart.md) — 검증 절차 (US1·US2·US3 + 원칙 II + 민감값)

### Post-Design Constitution Re-check

설계 후 다시 본다. **새 위반 없음.**

- 원칙 I — 설계가 Step 모델을 건드리지 않음을 data-model 이 확인한다. 「교체 대상」이
  `SessionView` 에만 있고 `Step` 에 없다
- 원칙 II — contracts/api-contract 의 `mode=rerecord` 흐름도가 러너 종료와 에이전트 시작
  사이에 순서를 명시한다. 검사 2개가 tasks 에 박힌다
- 원칙 III — 버리기의 되맞춤 실행 실패(FR-031c)가 data-model 의 불변식으로 들어갔다
- 원칙 IV — agent-tools 의 `repick_target` 이 `element_ref` 만 받는 것이 계약에 적혔다
- 원칙 V — 영향 없음

### 검증 순서 (기존 그대로)

```bash
cd backend && uv run lint-imports          # ★ 원칙 II — 이것이 실패하면 나머지는 무의미
cd backend && uv run ruff check src/ tests/
cd backend && uv run pytest
cd backend && uv run python -m itb.schema.export --check
cd frontend && npx tsc --noEmit && npm test -- --run
```

---

## 알려진 위험

| 위험 | 완화 |
|---|---|
| **도착점 만들기가 느리다** — 앞 구간이 20 Step 이면 재녹화 시작이 그만큼 걸린다 | 실행 속도(`run.pacing`)가 이미 있다. 버리기 되맞춤도 같은 비용을 치르므로 SC-002(조작 횟수) 측정에서 시간도 함께 기록한다 |
| **컨텍스트가 커져 비용이 는다** | FR-006 이 요약 축약과 생략 표시를 요구한다. Step 100개 기준 예산을 tasks 에서 실측해 정한다 |
| **AI 가 편집 도구를 남용한다** — 만들고 고치기를 반복하며 예산을 태운다 | 도구 호출 상한이 편집 도구에도 적용된다 (FR-042). 시스템 프롬프트가 「고치기는 방금 만든 것을 다듬을 때만」을 말한다 |
| **`step.toggleDeleteTarget` 개칭이 011 의 계약을 건드린다** | 009 가 `step.reorder → step.moveUp` 으로 한 전례가 있다. 조작 수는 늘지 않고 검사(`CapabilityCoverage`)가 개칭을 강제로 따라오게 한다 |
| **`AI_RUNNING` 국면에서 편집이 잠긴 것을 사용자가 고장으로 읽는다** | 기존 권한표가 이미 `remedy` 를 준다. 채팅 턴이 끝나면 자동으로 `PAUSED` 로 돌아오므로 잠김이 짧다 |
