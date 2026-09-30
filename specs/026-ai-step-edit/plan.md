# Implementation Plan: 고른 Step 을 AI 에게 고쳐 달라기

**Branch**: `026-ai-step-edit` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/026-ai-step-edit/spec.md`

## Summary

저장된 테스트의 편집 화면에서 **Step 하나**를 골라 AI 에게 자연어로 고쳐 달라고 한다.
제품이 브라우저를 열어 그 Step 직전까지 실행하고, AI 가 지금 화면을 보며 그 Step 을
**보존한 채** 고친다.

기술적으로 이 기능은 **016 의 형제**다. 도구도, 대화 통로도, 도착점 실행도, 되맞춤도
이미 있다. 새로 만드는 것은 016 이 **의도적으로 만들지 않은 하나**다 — 대상 Step 의
**원본 보관**. 016 은 「AI 가 기존 Step 을 건드리지 않는다」는 전제 위에서 스냅샷 없이
되돌렸고(research R7), 이 기능이 그 전제를 깨기 때문이다.

접근:

1. **권한**은 `sessions.py` 의 `in_scope` 람다 한 자리에 항을 더해 넓힌다. 고른 Step 이 없는 세션에서는 판정이 글자 그대로 016 과 같다.
2. **트랜잭션**은 `authoring/step_edit.py` 를 형제로 새로 둔다. `rerecord.py` 는 건드리지 않는다.
3. **되돌리기**는 `step_edits.restore_step()` 신설로 성립시킨다 — 고쳐진 Step 은 교체하고, 지워진 Step 은 되끼운다.
4. **모델의 말**은 `TOOL_SCHEMAS`·docstring·`SYSTEM_PROMPT` 세 자리를 함께 고친다. 하나라도 빠지면 코드가 넓어져도 모델이 시도하지 않는다.
5. **화면**은 조작 셋을 새로 등록하고, 두 AI 입구를 「고른 Step 이 남는가」로 가른다.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5 / React 19 (frontend)

**Primary Dependencies**: FastAPI · Playwright for Python · `claude_agent_sdk`(선택 의존성) · Vite · Vitest

**Storage**: 파일 기반 테스트 정의 (JSON). **이 기능은 저장 형식을 바꾸지 않는다.**

**Testing**: `bash scripts/test-backend.sh` (backend) · `npx vitest run` (frontend). `uv run pytest`·`npm test` 는 쓰지 않는다 — 앞은 저장소 설정을 지나지 않고 뒤는 감시 모드다.

**Target Platform**: 로컬 실행 웹 앱 (제품 서버 + 브라우저)

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 없음. 이 기능의 비용은 **도착점 재실행 시간**이며 016 이 이미 치르는 것과 같다.

**Constraints**:
- 재실행 경로에서 언어모델 호출 불가 (원칙 II) — 도착점 실행·되맞춤 실행 포함
- 도구 표면 16종 고정 — 늘리지 않는다
- 저장 형식에서 AI 편집과 사람 편집이 구별되지 않아야 함 (원칙 I)

**Scale/Scope**: 백엔드 신설 모듈 1 · 순수 함수 1 · 세션 모드 1 · API 2 · 이벤트 2 · 프론트 조작 3

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 설계 후 재확인.*

| 원칙 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | 통과 | AI 의 편집은 `itb/execution/step_edits.py` 를 지난다. 되돌리기용 `restore_step()` 도 **같은 모듈**에 둔다 — 라우터에 두면 그것이 두 번째 구현이다 (research R3). Step 에 새 필드가 없고 작성 주체를 저장 형식에 남기지 않는다. |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 통과 | 도착점 실행과 되맞춤 실행은 **러너만** 돈다. 016 이 세운 순서(러너 → 멈춤 → 그제서야 에이전트)를 그대로 받는다. `tests/test_principle_ii_timeline.py` 가 두 태스크의 생존 구간이 겹치지 않음을 본다. 저장되는 것은 컴파일된 Step 뿐이고 지시문은 실행되지 않는다. |
| **III. Stateful Interactive Runner** | 통과 | 버리기가 세션을 끝내지 않는다 (FR-026). AI 가 막혀도 브라우저를 닫지 않는다 (FR-036). 되맞춤은 쿠키·저장소를 지우지 않는다 — 016 `_return_to_start()` 의 판단 그대로. |
| **IV. Locator Resilience** | 통과 | 대상 재지정은 기존 `repick_target` 이고, 후보 묶음은 살아 있는 페이지에서 수집된다. 모델이 셀렉터를 지어 넣을 수 없다. 이 기능은 그 규칙을 건드리지 않는다. |
| **V. Asset Portability** | 통과 | 저장 형식이 바뀌지 않으므로 Export 대응도 바뀌지 않는다. DSL 변경 없음. |

**보안 제약**:
- 민감 값은 대화 이력·에이전트 컨텍스트에 나타나지 않는다 (FR-041). 016 의 `Scrubber`·`scrubber_source` 통로를 그대로 쓴다.
- 경계 검증: `step_edit_step_id` 는 **값 하나**이며 존재 검증은 기존 `find_index` 에 맡긴다. 새 검증 구현을 만들지 않는다.
- 실패는 명시적으로 알린다 — 되맞춤 실패는 두 사실을 함께 말한다 (FR-028).

**결론**: **위반 없음.** Complexity Tracking 은 비운다.

## Project Structure

### Documentation (this feature)

```text
specs/026-ai-step-edit/
├── plan.md              # 이 파일
├── spec.md              # 요구사항 42 · 성공 기준 10
├── research.md          # R1~R10 — 실제 코드에서 확인한 결정
├── data-model.md        # StepEditTransaction · restore_step · 세션 상태
├── quickstart.md        # 사람이 손으로 확인하는 법 + 전량 검증 명령
├── contracts/
│   ├── api-contract.md  # 세션 시작 · 확정 · 버리기 · 이벤트
│   ├── agent-tools.md   # 권한 범위 · 설명문 세 자리 · 거절문
│   └── ui-contract.md   # 조작 셋 · 두 입구의 구분 · 배선 네 단계
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks 산출물 (아직 없음)
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── authoring/
│   │   ├── step_edit.py        # [신설] StepEditTransaction — rerecord.py 의 형제
│   │   ├── rerecord.py         # [건드리지 않음] 016 그대로 (FR-030)
│   │   ├── tools.py            # [수정] TOOL_SCHEMAS · 편집 도구 docstring · 거절문
│   │   └── agent.py            # [수정] SYSTEM_PROMPT 의 편집 권한 지침
│   ├── execution/
│   │   └── step_edits.py       # [수정] restore_step() 추가
│   └── api/routes/
│       └── sessions.py         # [수정] mode="step_edit" · in_scope 확장 · commit/discard
└── tests/                      # 신설 검사 + 016 회귀 검사

frontend/
├── src/
│   ├── lib/
│   │   ├── actions.ts          # [수정] ai.stepEdit · ai.stepEditCommit · ai.stepEditDiscard
│   │   └── capabilities.ts     # [수정] 모든 국면에 셀 추가
│   ├── pages/
│   │   ├── EditView.tsx        # [수정] 두 입구 · 시작 조건 검증
│   │   └── SessionScreen.tsx   # [수정] 수정 상태 소유 · 이벤트 소비
│   ├── components/workbench/
│   │   ├── Workbench.tsx       # [수정] props 통과 — 빠뜨려도 타입 검사가 통과한다
│   │   └── (수정 표시 컴포넌트) # [신설 가능] 대상 표시 · 확정/버리기
│   ├── api/
│   │   ├── client.ts           # [수정] step-edit 엔드포인트
│   │   └── ws.ts               # [수정] step_edit_changed · step_edit_realign_failed
│   └── theme/workspace.css     # [수정] 새 클래스는 이 정본에 선언한다
└── tests/
```

**Structure Decision**: 기존 web application 구조를 그대로 쓴다. 새 최상위 디렉터리를
만들지 않는다. 백엔드에서 **신설되는 파일은 `authoring/step_edit.py` 하나**이며, 그것이
형제 모듈인 이유는 research R2 에 있다.

## Phase 0 — Research

완료. [research.md](./research.md) 에 R1~R10.

가장 중요한 셋:

- **R2** — 트랜잭션을 016 에 합치지 않는다. 합치면 016 불변식 9 의 증명이 조건부가 된다.
- **R3** — `restore_step()` 이 필요한 진짜 이유는 AI 가 대상 Step 을 **지울 수 있기** 때문이다. 지워진 것은 교체로 돌아오지 않는다.
- **R8** — 설명문 세 자리를 함께 고쳐야 한다. `TOOL_SCHEMAS` 를 빠뜨리면 코드가 넓어져도 모델이 시도하지 않는다.

## Phase 1 — Design & Contracts

완료.

- [data-model.md](./data-model.md) — `StepEditTransaction`(불변식 A~D) · `restore_step()` · 세션 상태 · 화면에 내려가는 모양
- [contracts/api-contract.md](./contracts/api-contract.md) — 세션 시작 순서가 계약이다 (원칙 II)
- [contracts/agent-tools.md](./contracts/agent-tools.md) — 도구가 하나도 늘지 않는다. 바뀌는 것은 설명문이다
- [contracts/ui-contract.md](./contracts/ui-contract.md) — 두 입구를 「고른 Step 이 남는가」로 가른다
- [quickstart.md](./quickstart.md) — 손으로 확인하는 법 + 전량 검증 명령

### Constitution Check (설계 후 재확인)

설계가 원칙을 더 건드리는 자리는 없다. 오히려 둘이 **강화**된다.

- **원칙 I** — `restore_step()` 을 `step_edits` 에 둠으로써 되돌리기까지 사람·AI 공통 함수가 된다. 지금은 사람의 되돌리기가 연산 목록 방식이지만, Step 단위 되돌리기가 필요해질 때 쓸 자리가 생긴다.
- **원칙 II** — 026 이 도착점 실행과 되맞춤 실행을 **새로 만들지 않고** 016 의 것을 그대로 쓰므로, 경계 검사가 덮는 면적이 늘지 않는다.

**남은 위험은 기술이 아니라 화면이다.** 두 AI 입구가 닮아 보이면 이 기능은 동작해도
쓰이지 않는다. SC-010(처음 보는 사용자 5명 중 4명이 「고른 Step 이 남는가」를 맞힌다)이
그것을 재는 유일한 기준이고, 자동 검사로는 덮이지 않는다.

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 비운다.

해당 없음.
