# Implementation Plan: Interactive AI Test Builder (MVP — P0 + P1)

**Branch**: `001-interactive-ai-test-builder` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-interactive-ai-test-builder/spec.md`

**Constitution**: v1.0.0 — 원칙 I·II는 NON-NEGOTIABLE

**Phase 0/1 산출물**: [research.md](./research.md) · [data-model.md](./data-model.md) ·
[contracts/](./contracts/) · [quickstart.md](./quickstart.md)

---

## Summary

코드를 쓰지 않고 실제 브라우저로 신뢰할 수 있는 E2E 테스트를 만드는 **단독 로컬 도구**를 구현한다.
사람이 직접 녹화하거나 자연어로 AI에게 지시해 테스트를 만들고, 실행 중 언제든 멈춰 고친 뒤 브라우저 상태를
유지한 채 이어서 완성한다. 저장된 테스트는 언어모델 없이 결정적으로 반복 실행된다.

**기술적 접근의 핵심 세 가지**:

1. **일시정지는 브라우저 조작이 아니다.** 장수명 `BrowserContext` 를 유지한 채 러너 태스크가
   `asyncio.Event` 를 await 하는 것으로 Pause를 구현한다. 상태 저장·복원 로직이 없다. (research R1)
2. **제품을 입력 경로에서 빼낸다.** 사용자는 실제 브라우저 창을 조작하고 제품은 입력을 전달하지 않는다.
   전달하지 않으므로 한글 IME·hover·드래그·파일 대화상자에서 깨질 것이 없다. 관찰은 읽기 전용
   스크린캐스트 미러가 담당한다. (clarify 결정 3, research R2·R3)
3. **원칙 II를 임포트 경계로 강제한다.** 런타임 플래그가 아니라 `import-linter` 계약으로
   `itb.execution` 에서 `itb.llm` 도달을 차단하고 CI에서 빌드를 실패시킨다. (research R5)

부수 결정 두 가지가 요구사항을 공짜로 해결한다. 입력을 `change`/`blur` 로 잡으면 한글 IME 조합 문제와
FR-025(연속 입력 병합)가 동시에 사라진다. `add_init_script` 와 `expose_binding` 을 `Page` 가 아니라
`BrowserContext` 에 등록하면 멀티 탭(FR-030)이 별도 코드 없이 따라온다.

---

## Technical Context

**Language/Version**: Python 3.13.0 (백엔드) · TypeScript / React (프론트엔드)
> Playwright for Python이 3.13을 지원하지 않으면 3.12로 내린다 — 설치 첫 작업에서 확인한다 (research R1).

**Primary Dependencies**:

| 영역 | 선택 | 근거 |
|------|------|------|
| 웹 프레임워크 | FastAPI + uvicorn | 헌법 고정 |
| 브라우저 자동화 | Playwright for Python, **`async_api`** | sync API는 asyncio 루프에서 오류 (R1) |
| 도메인 모델 / 검증 | Pydantic v2 | DSL 권위 정의 + 경계 검증 (R6) |
| 언어모델 | `anthropic` SDK, `AsyncAnthropic`, 모델 `claude-opus-5` | R5 |
| 민감 값 암호화 | PyNaCl `SealedBox` (X25519) | 공개키 봉인 / 비밀키 개봉이 요구 형태와 정확히 일치 (R7) |
| 직렬화 | PyYAML 안전 로더 | 사람이 읽는 평문 저장 (R6) |
| 아키텍처 경계 강제 | **import-linter** | 원칙 II를 CI에서 강제 (R5) |
| 프론트엔드 | React + Vite | 디자인이 순수 HTML/CSS라 이식 용이 |
| 타입 생성 | `json-schema-to-typescript` | Pydantic → JSON Schema → TS (R6) |
| 테스트 | pytest / pytest-asyncio (백엔드), Vitest (프론트) | |
| 패키지 관리 | uv (Python) / npm (Node) | 환경에 이미 설치됨 |

**Storage**: 로컬 파일 시스템만. 프로젝트 = 디렉터리 1개. 테스트 정의는 커밋 대상 YAML,
비밀 값 암호문과 실행 산출물은 `.gitignore` 대상. 데이터베이스 서버 없음. (FR-088b, data-model §1)

**Testing**: pytest — `unit` / `contract` / `integration` / `e2e` 4계층 + Vitest.
헌법 품질 게이트 3이 Recorder·Runner 상태 기계·Generator 각각의 단위 테스트와 사용자 향 흐름당
최소 1개의 종단 테스트를 요구한다.

**Target Platform**: 개발 확인 환경은 macOS 26.2 arm64. 로컬 인터페이스에만 바인딩하는 데스크톱형
로컬 웹 앱. 브라우저는 Chromium만 (MVP).

**Project Type**: 단독 로컬 도구 (backend + frontend 2-프로젝트 구조). 서버 배포·계정·권한 없음 (FR-088).

**Performance Goals** (research R8): Step 실행 제품 오버헤드 p95 < 50 ms · 녹화 이벤트 → Step 반영
p95 < 200 ms · 미러 5~10 fps, 프레임 지연 p95 < 300 ms · 세션 시작 준비 < 2 s ·
Step 대기 시간 기본 5000 ms.

**Constraints**:
- 저장된 테스트 실행 경로에서 언어모델 호출 **0건** (SC-006, 코드 구조로 강제)
- 미러가 끊겨도 실행 영향 **0** (FR-047b)
- 민감 값 평문 노출 **0건** (SC-010)
- Playwright 객체는 FastAPI 메인 이벤트 루프에서만 호출 (`run_in_threadpool` 금지, R1)
- 동시 실행 테스트당 1건 (FR-043), 동시 탭 상한 10 (FR-030g)

**Scale/Scope**: 사용자 1명 · 프로젝트 1개 열림 · 테스트 수십~수백 개 · 테스트당 Step 200개까지 ·
화면 8종 (디자인 확정) · 기능 요구사항 120개 · 사용자 스토리 7개

---

## Constitution Check

*GATE: Phase 0 research 전에 통과해야 하고, Phase 1 design 후 재확인한다.*

### Phase 0 이전 (초기 평가)

| 게이트 | 판정 | 근거 |
|--------|------|------|
| I. Unified Step Model | PASS | spec FR-010·FR-014·FR-062·FR-075·FR-080이 단일 모델을 명시. 컴포넌트별 표현 없음 |
| II. Deterministic Replay | PASS | FR-044·FR-045·FR-063. LLM Step 타입 미도입 |
| III. Stateful Interactive Runner | PASS | FR-031~FR-043 |
| IV. Locator Resilience | PASS | FR-017~FR-022 |
| V. Asset Portability | **CONDITIONAL** | DSL은 평문·문서화·버전관리 가능. **그러나 Playwright Export는 P2로 이연** → Complexity Tracking에 기록 |
| 기술 스택 고정 | PASS | Python/FastAPI/Playwright + React |
| Cross-language schema duty | 미결 → R6에서 해소 | 권위 정의 지점 결정 필요 |
| 비밀값 하드코딩 금지 | PASS | FR-084 |
| 민감 값 마스킹 | PASS | FR-082·FR-083 |
| 경계 입력 검증 | PASS | FR-085 |
| 생성 코드 이스케이프 | PASS | 계약에 명시 |
| 임의 셸 실행 금지 | PASS | FR-086 |
| 명시적 오류 처리 | PASS | FR-087 |
| 품질 게이트 1~5 | 미결 → Phase 1에서 설계 | 강제 수단 필요 |

### Phase 1 이후 (재평가)

| 게이트 | 판정 | 설계상 강제 수단 |
|--------|------|-----------------|
| **I. Unified Step Model** | PASS | 판별 유니온 `Step` 하나. `author` 는 부가 정보로 실행에 미영향(data-model §4). WebSocket `step_added` 이벤트가 사람·AI·자연어 경로에서 **동일**하므로 UI 계층에도 분기가 없다(contracts/websocket.md). 에이전트 도구 표면이 Step 종류와 1:1이라 컴파일 실패 경우가 원리적으로 없다(R5) |
| **II. Deterministic Replay** | PASS | `import-linter` `forbidden` 계약으로 `itb.execution`→`itb.llm`/`anthropic` 차단, CI 빌드 실패. 동적 검증으로 재실행 중 클라이언트 생성 스파이 0건 확인. `itb.execution` 은 `ai_instruction` 을 읽지 않는다 |
| **III. Stateful Interactive Runner** | PASS | 장수명 `BrowserContext` + `asyncio.Event`. 상태 기계 불변식 1(PAUSED·AI_BLOCKED에서 세션 종료 금지)·2(편집은 PAUSED에서만)·3(편집은 정의만 변경)을 data-model §8에 명문화하고 단위 테스트 대상으로 지정 |
| **IV. Locator Resilience** | PASS | 순수 함수 `choose_strategy` 를 Runner·Generator가 공유(R4). 기록 시점 후보 검증으로 `Candidate.status` 가 실제 데이터가 되고 SC-008을 기록 시점에 측정 가능 |
| **V. Asset Portability** | **CONDITIONAL** | DSL 요건 충족(평문 YAML·문서화·버전관리·검증 규칙 공개). Export 미구현은 아래 기록. 완화: `contracts/step-dsl.md` 에 DSL→Playwright 대응표를 명시하고 후보 선택을 `choose_strategy` 한 곳에 모아 두어 Export 추가 시 우선순위 로직을 다시 짜지 않게 했다 |
| **Cross-language schema duty** | PASS | Pydantic v2 권위 정의 → JSON Schema → TS 생성. **CI 드리프트 테스트**가 커밋된 생성물과 새 생성물을 비교(R6) |
| **보안 요건 전체** | PASS | PyNaCl SealedBox + 별도 비밀 파일 + 로그 스크러버(R7). 어떤 API 응답·WebSocket 이벤트도 복호화 값을 담지 않음(계약에 명문화). 민감 변수의 `value` 가 null이어야 한다는 **스키마 불변식**으로 정의 파일 유입을 차단 |
| **품질 게이트 1 (원칙 준수 증거)** | PASS | `lint-imports` + `test_replay_no_llm` 이 원칙 II 증거를 자동으로 생산 |
| **품질 게이트 2 (라운드트립 정합성)** | PASS | `tests/integration/test_roundtrip.py` 를 필수 작업으로 편성 |
| **품질 게이트 3 (테스트)** | PASS | 4계층 테스트 구조. Recorder·Runner 상태 기계·Generator 단위 테스트 필수. 사용자 향 흐름 7개당 종단 테스트 1개 이상 |
| **품질 게이트 4 (테스트 비활성화 금지)** | PASS | quickstart 완료 체크리스트 항목으로 포함 |
| **품질 게이트 5 (성공 지표 인식)** | PASS | R8이 목표를 정량화. SC-001·002·004·005는 자동화 불가로 별도 수동 측정 세션에 편성 |

**미해결 위반 없음.** 조건부 1건은 아래에 근거와 함께 기록한다.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-interactive-ai-test-builder/
├── plan.md                    # 이 파일
├── spec.md                    # 요구사항 (FR 120, SC 12)
├── research.md                # Phase 0 — 결정 R1~R8
├── data-model.md              # Phase 1 — 엔티티, 상태 기계, 불변식
├── quickstart.md              # Phase 1 — 검증 절차
├── contracts/
│   ├── README.md              # 경계 설계 원칙
│   ├── rest-api.md            # 명령
│   ├── websocket.md           # 관찰 (서버 → 클라이언트 단방향)
│   └── step-dsl.md            # 사용자 자산 형식 — 가장 중요한 계약
├── checklists/
│   └── requirements.md        # 명세 품질 체크리스트 (16/16)
└── tasks.md                   # Phase 2 (/speckit-tasks 산출물 — 이 명령이 만들지 않음)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── .importlinter                    # 원칙 II 강제 계약
└── src/itb/
    ├── domain/                      # 순수 — 아무것도 임포트하지 않는다
    │   ├── step.py                  # Step 판별 유니온 (원칙 I의 단일 모델)
    │   ├── locator.py               # TargetLocator, Candidate
    │   ├── assertion.py             # 4종 검증 조건
    │   ├── test_case.py             # Test, Project, Variable
    │   └── run_result.py            # RunResult, StepResult, LocatorAttempt
    ├── locator/                     # domain 만 임포트
    │   ├── strategy.py              # choose_strategy — Runner·Generator 공유 (원칙 IV)
    │   └── collector.py             # 후보 수집 + 기록 시점 검증 규칙
    ├── recording/
    │   ├── recorder.py              # 컨텍스트 바인딩 수신 → Step
    │   ├── tabs.py                  # tab_index 부여·해석 (FR-030)
    │   └── injected/recorder.js     # add_init_script 로 주입
    ├── execution/                   # ★ itb.llm 임포트 금지 (CI 강제)
    │   ├── session.py               # SessionManager, 장수명 BrowserContext
    │   ├── state_machine.py         # RunSession 상태 기계 (단위 테스트 필수)
    │   ├── runner.py                # 러너 태스크, Pause = asyncio.Event
    │   ├── step_executor.py         # Step 종류별 실행 + 탭 해석
    │   └── artifacts.py             # 스크린샷·콘솔·네트워크 수집
    ├── mirror/
    │   └── screencast.py            # CDP Page.startScreencast — Input 도메인 미사용
    ├── secrets/
    │   ├── keys.py                  # 키 쌍 생성·적재, 권한·암호구
    │   ├── store.py                 # SealedBox 봉인·개봉, 지문 검사
    │   └── scrubber.py              # 산출물 기록 직전 마스킹 (FR-089d)
    ├── storage/
    │   ├── repository.py            # 프로젝트·테스트·결과 파일 입출력
    │   └── yaml_io.py               # 안전 로더 + 검증 오류 위치 보고
    ├── generator/                   # execution 쪽 — llm 임포트 금지
    │   └── playwright_gen.py        # Step → Playwright 코드 (P2 Export 대비)
    ├── authoring/                   # llm 임포트 허용
    │   ├── agent.py                 # tool_runner 루프, 시도 상한
    │   ├── tools.py                 # Step과 1:1 도구 표면
    │   └── nl_step.py               # 자연어 Step 추가 (FR-078~081)
    ├── llm/
    │   └── client.py                # AsyncAnthropic 경계 — 유일한 SDK 접점
    ├── schema/
    │   └── export.py                # Pydantic → JSON Schema 내보내기
    └── api/
        ├── app.py                   # FastAPI lifespan (Playwright start/stop)
        ├── routes/                  # project, tests, sessions, steps, secrets, tabs
        └── ws/session_events.py     # 단방향 이벤트 송신

backend/tests/
├── unit/            # domain, locator, state_machine, recorder, generator, secrets
├── contract/        # REST·WebSocket·DSL 계약, 스키마 드리프트
├── integration/     # 픽스처 앱 대상: roundtrip, replay_no_llm, locator_coverage,
│                    #                secret_leakage, multitab, performance
└── e2e/             # 사용자 스토리 7개 각각 최소 1개

frontend/
├── package.json
└── src/
    ├── pages/       # TestList, CreateTest, Runner, RunResult  (디자인 8화면 대응)
    ├── components/  # StepList, StepInspector, MirrorView, TabStrip,
    │                # PauseActions, AiBlockedCard, LocatorPriorityTable
    ├── api/         # REST 클라이언트 + WebSocket 구독
    └── types/generated/step-dsl.d.ts   # 생성물 — 손으로 고치지 않는다

fixtures/sample-app/     # 검증용 대상 앱 (로그인·프로젝트·새 창 약관 화면)
```

**Structure Decision**: 백엔드/프론트엔드 2-프로젝트 구조를 택한다. 언어가 다르고 배포 단위가 다르므로
단일 프로젝트로 묶을 이유가 없다.

백엔드 내부 패키지 경계가 이 계획의 핵심 설계다. `domain` → `locator` → `execution` 방향으로만
의존하고, `authoring` 과 `llm` 은 그 바깥에 둔다. **`execution` 이 `llm` 을 임포트할 수 없다는 사실이
파일 배치와 `.importlinter` 계약으로 표현되며, CI가 이를 검사한다.** 원칙 II를 사람의 주의력에
의존시키지 않는 유일한 방법이다.

`generator/` 를 원칙 II 금지 구역(`execution` 쪽)에 두는 이유는, Export가 P2여도 그 코드가 언어모델에
의존하게 되면 내보낸 테스트가 결정적이지 않게 되기 때문이다. 지금 경계를 그어 둔다.

`fixtures/sample-app` 을 저장소에 포함한다. 사내 앱에 의존하면 종단 테스트가 환경에 묶여 CI에서 돌지
않는다. 픽스처 앱은 `data-testid` 가 있는 요소와 없는 요소를 섞어 두어 후보 수집률(SC-008)을 실제로
측정할 수 있게 만든다.

---

## Complexity Tracking

> Constitution Check의 조건부 판정 1건.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **원칙 V — Playwright Export 미구현** (MVP는 DSL 평문 저장까지만 충족) | Export는 PRD §14에서 P2로 분류되었고 사용자가 이번 사이클 범위를 P0+P1로 확정했다. PRD §20이 지정한 MVP 기술 검증 대상은 Recorder·Stateful Runner·Deterministic Compiler 셋이며, Export는 그중 어느 것도 검증하지 않는다. 검증되지 않은 Step 모델 위에 Export를 먼저 짜면 모델이 바뀔 때마다 다시 짜야 한다 | **지금 Export를 구현하는 대안**: 헌법 원칙 V를 완전히 충족하지만 범위 결정과 충돌하고, Step 모델이 아직 실사용으로 검증되지 않은 상태에서 생성기를 고정하게 된다. **완화 조치를 대신 취했다** — ① DSL을 평문·문서화·버전관리 가능한 형태로 저장해 원칙 V의 자산 이식성 요건 중 잠금 방지 부분은 지금 충족한다 ② `contracts/step-dsl.md` 에 DSL→Playwright 대응표를 확정해 둔다 ③ 후보 선택을 `choose_strategy` 순수 함수 한 곳에 모아 Runner와 Generator가 공유하게 하고, `generator/playwright_gen.py` 를 지금 자리 잡아 둔다. Export를 붙일 때 우선순위 로직을 다시 짜는 일이 없도록 하는 것이 이 완화의 목적이다 |

**이 이연은 다음 사이클에서 반드시 회수해야 한다.** 회수하지 않은 상태로 제품을 사용자에게 내보내면
원칙 V의 사용자 약속("제품을 쓰지 않더라도 자산을 계속 사용할 수 있다")이 지켜지지 않는다.
헌법 개정으로 원칙을 낮추는 것이 아니라, P2에서 구현해 원칙을 충족시키는 것이 이 항목의 해소 경로다.

---

## 다음 단계

`/speckit-tasks` 로 작업을 분해한다. 편성 시 다음을 반영할 것:

1. **research의 "검증 필요 사항" 8건을 첫 작업으로 편성한다.** Playwright 3.13 지원, headed 모드
   스크린캐스트 동작, `get_by_role` 이름 매칭, PyNaCl 설치, `context.on("page")` 커버리지 등은 가정이며
   틀리면 설계가 바뀐다. 코드를 쌓기 전에 확인한다.
2. `.importlinter` 계약과 `lint-imports` CI 연결을 **초기 작업**에 둔다. 나중에 붙이면 이미 경계를
   넘은 코드를 되돌려야 한다.
3. 스키마 생성 파이프라인(R6)을 도메인 모델 직후에 둔다. 프론트가 손으로 타입을 만들기 시작하면 안 된다.
4. 사용자 스토리 우선순위(P1~P7)를 작업 순서의 기준으로 삼되, `domain` → `locator` → `execution` 의
   기술 의존을 앞세운다.
