# Implementation Plan: 부정 검증과 상태 검증

**Branch**: `021-negative-state-assertions` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-negative-state-assertions/spec.md`

---

## Summary

검증의 어휘를 두 칸 늘린다. **새 개념을 만들지 않고 기존 두 축에 값을 더한다.**

| 축 | 지금 | 더하는 값 |
|---|---|---|
| 무엇을 보는가 (`kind`) | `visible` · `hidden` · `text` · `url` | `enabled` · `disabled` |
| 어떻게 비교하는가 (`match`) | `equals` · `contains` | `not_equals` · `not_contains` |

새 엔티티가 없다. 새 화면이 없다. 새 의존성이 없다. 저장 형식의 버전도 올리지 않는다.

**가장 큰 변화는 어휘가 아니라 대기 규칙이다.** 지금 텍스트 검증은 화면을 한 번 읽고
판정한다. 그 위에 부정형을 얹으면 조용히 통과하는 검증을 대량으로 만들게 되므로
([research.md R3](./research.md)), 값 비교 검증의 대기를 공통 도우미 하나로 합친다. 이것이
이 기능에서 기존 동작을 바꾸는 유일한 지점이고, 회귀 위험도 여기에 모여 있다.

조사 중 두 가지가 드러나 범위가 늘었다 ([R5](./research.md) · [R6](./research.md)):
**Playwright 생성기가 이미 구현되어 있어** 새 종류를 반드시 반영해야 하고, **Step 목록이
비교 방식을 표시하지 않아** 부정형 도입 전에 먼저 고쳐야 한다.

---

## Technical Context

**Language/Version**: Python 3.12+ (백엔드) · TypeScript 5 / React 19 (프론트엔드)

**Primary Dependencies**: FastAPI · Playwright for Python · Pydantic v2 · Anthropic SDK
(작성 경로 전용) · Vite · Tailwind + shadcn 계열 UI. **새 의존성 없음.**

**Storage**: 파일. 테스트 정의(플레인 텍스트) · 실행 결과. **마이그레이션 없음** —
열거형에 값을 더할 뿐이므로 기존 파일에는 새 값이 등장하지 않는다.

**Testing**: pytest (`backend/scripts/test-backend.sh` — 병렬 계층 + `-m timing` 순차 계층) ·
vitest + `tsc --noEmit` (프론트엔드)

**Target Platform**: 로컬 데스크톱에서 도는 웹 애플리케이션 (백엔드 + 브라우저)

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 새 목표를 세우지 않는다. **단, 실패하는 텍스트 검증의 소요 시간이
늘어난다** — 즉시 실패에서 제한 시간(기본 10초) 소진으로 바뀐다. 의도한 비용이며 Step 당
예산은 그대로다. 통과하는 검증은 지금과 같거나 빠르다(조건이 참이면 즉시 통과).

**Constraints**:
- 헌법 원칙 I — 검증 조건의 정의는 한 곳(백엔드 도메인)에서만 규정한다
- 헌법 원칙 II — 재실행 경로에 LLM 호출이 추가되면 안 된다. 상태 판정은 결정적이어야 한다
- 헌법 원칙 IV — 검증 대상도 후보 묶음으로 식별한다. CSS 단독 후보를 만들지 않는다
- 헌법 원칙 V — 내보낸 Playwright 테스트가 같은 검증을 해야 한다 (R5 로 필수 확정)
- 도구 표면 계약 — `TOOL_NAMES` 16종 · `STEP_PRODUCING_TOOLS` 9종 유지. **도구를 늘리지
  않는다.** 새 검증은 기존 `assert_condition` 의 인자 값으로 들어간다
- 스키마 단일 출처 — 백엔드 Pydantic 이 권위, TypeScript 는 생성물

**Scale/Scope**: 백엔드 모듈 6개 · 프론트엔드 4개 지점 · 생성 스키마 2개 · 계약 문서 1개.

---

## Constitution Check

*GATE: Phase 0 전 통과 · Phase 1 후 재확인*

### 초기 평가 (Phase 0 전)

| 원칙 | 위험 | 판정 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | 새 종류가 작성 경로마다 다른 형태로 만들어지면 위반 | **통과** — 조건 형태는 도메인 한 곳이 규정하고 세 경로가 같은 생성 함수를 쓴다. 새 Step 종류를 만들지 않고 기존 `AssertionStep` 의 조건 값만 늘린다 |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 상태 판정이 추론에 기대면 위반 | **통과** — 조작 가능 여부는 브라우저가 주는 사실이다. 비폼 요소 경고는 **작성 시점**에만 나가고 실행 판정을 바꾸지 않는다 ([R2](./research.md)) |
| **III. Stateful Interactive Runner** | 해당 없음 | **통과** — 세션 수명·일시정지 규칙을 건드리지 않는다 |
| **IV. Locator Resilience** | 상태 검증 대상을 CSS 단독으로 저장하면 위반 | **통과** — 기존 검증과 같은 수집 경로를 쓴다. 오히려 **이 기능이 원칙 IV 를 지킨다** — 표현 수단이 없어 사용자가 셀렉터 트릭을 쓰던 것을 없앤다 |
| **V. Asset Portability** | 생성기에 새 종류를 넣지 않으면 내보내기가 깨진다 | **조건부 통과** — R5 로 생성기 반영을 범위에 넣었다. 넣지 않으면 위반이므로 **릴리스 게이트가 아니라 이번 구현의 필수 항목**이다 |

**보안 제약**: 비교 값에 민감 값이 들어갈 수 있다. 기존 규칙(변수 참조로만 저장, 화면·로그
마스킹)이 그대로 적용된다. 부정 비교라고 해서 다르게 다루지 않는다.

### Phase 1 후 재평가

| 원칙 | 설계 후 판정 |
|---|---|
| I | **통과** — [data-model.md](./data-model.md) 의 형태 규칙 표가 유일한 출처이고, API·작성 도구·화면이 모두 그것을 따른다 |
| II | **통과** — 공통 대기 도우미는 시각과 브라우저 상태만 읽는다. LLM 경로 없음 |
| III | **통과** — 변경 없음 |
| IV | **통과** — 새 종류도 후보 묶음 수집 경로를 거친다 |
| V | **통과** — [contracts/export-mapping.md](./contracts/export-mapping.md) 에 6개 대응을 못 박았고, 생성기 작업이 tasks 에 들어간다 |

**미해결 위반 없음.** Complexity Tracking 에 기록할 예외 없음.

---

## Project Structure

### Documentation (this feature)

```
specs/021-negative-state-assertions/
├── spec.md                      # 명세 (완료)
├── plan.md                      # 이 문서
├── research.md                  # 설계 결정 6건 (완료)
├── data-model.md                # 조건 형태 규칙과 판정표
├── contracts/
│   ├── assertion-surface.md     # 도메인·API·도구 표면 계약
│   └── export-mapping.md        # DSL ↔ 표준 Playwright 대응 (원칙 V)
├── quickstart.md                # 사람이 손으로 확인하는 절차
├── checklists/
│   └── requirements.md          # 명세 품질 (완료)
└── tasks.md                     # 다음 단계에서 생성
```

### Source Code (repository root)

변경이 닿는 지점을 전수로 적는다. **빠진 곳이 있으면 어휘가 절반만 동작한다.**

```
backend/src/itb/
├── domain/
│   ├── assertion.py          ★ AssertionKind +2, MatchMode +2, 형태 규칙 확장
│   └── manual_step.py        ★ 수동 삽입 서술에 부정 비교 허용 (FR-022)
├── execution/
│   ├── step_executor.py      ★ 공통 대기 도우미 + 상태 검증 분기 + 텍스트 폴링
│   └── assertion_builder.py  ★ 새 종류의 대상 필수 규칙 · 표시 이름 · 비폼 경고
├── authoring/
│   ├── tools.py              ★ 도구 스키마 enum · 오류 문구 · 종류 설명
│   └── agent.py              ★ 작성 지침 — 부정 검증을 뒤집지 말 것
├── generator/
│   └── playwright_gen.py     ★ R5 — 새 종류·비교 방식의 내보내기 대응
├── api/routes/
│   └── steps.py              ☆ 요청 모델이 도메인 열거형을 그대로 쓰므로 자동 확장
└── sharing/reader.py         ☆ dsl_version 유지로 변경 없음 (확인만)

backend/schema/*.schema.json  ☆ 재생성 산출물

frontend/src/
├── types/generated/*.d.ts    ☆ 재생성 산출물
├── components/
│   └── AssertionForm.tsx     ★ 종류 6개 · 비교 방식 4개 · 한계 안내 (FR-026)
├── components/workbench/
│   └── StepList.tsx          ★ R6 — 요약 문구에 비교 방식과 한국어 종류
└── lib/wording.ts            ★ 종류·비교 방식의 한국어 문구를 한곳에
```

★ = 손으로 고침 · ☆ = 생성물이거나 확인만

---

## 구현 순서 — 왜 이 순서인가

1. **도메인 먼저** (`assertion.py`). 헌법이 요구하는 순서다 — 스키마가 먼저 바뀌고 소비자가
   따라온다. 여기서 형태 규칙이 확정되지 않으면 나머지가 각자 규칙을 만든다.
2. **대기 도우미와 실행** (`step_executor.py`). 어휘보다 먼저 고쳐야 한다. 대기가 없는
   상태에서 부정형을 붙이면 **거짓 통과가 기본값인 기능**이 잠깐이라도 존재하게 된다.
3. **생성기** (`playwright_gen.py`). 실행과 짝이다. 둘이 갈리면 원칙 V 가 깨지고, 갈린
   것을 나중에 발견하면 어느 쪽이 맞는지 판단해야 한다.
4. **작성 경로 셋** (도구 · 수동 삽입 · API). 어휘가 실제로 쓰이기 시작하는 지점.
5. **표시** (R6 먼저, 그다음 폼). 목록 요약을 고치지 않은 채 부정형을 노출하면 정반대
   뜻의 Step 두 개가 목록에서 구별되지 않는다.

---

## 회귀 위험과 확인 방법

| # | 위험 | 확인 |
|---|---|---|
| 1 | 텍스트 검증 실패가 제한 시간을 꽉 채워 기존 테스트가 느려지거나 타임아웃 | 전량 실행 전후의 소요 시간 비교. 느려진 테스트는 `timeout_ms` 를 짧게 준다 — **제품 동작을 되돌리지 않는다** |
| 2 | 텍스트 검증에 폴링이 생겨 전에 실패하던 것이 통과로 바뀜 | 방향이 개선이므로 허용. 단 **어느 테스트가 바뀌었는지 명시**한다. 조용히 초록으로 바뀌면 안 된다 |
| 3 | 열거형 확장이 생성 스키마 드리프트 검사를 깨뜨림 | `schema.export --check` 와 타입 재생성을 같은 작업에서 함께 돌린다 |
| 4 | 새 종류가 생성기 분기에 없어 내보내기가 예외 | `test_export_keeps_assertion.py` 에 6개 조합을 추가한다 |
| 5 | 020 의 어긋남 기록·분류가 새 종류에서 동작하지 않음 | 분류 함수는 `kind` 를 보지 않으므로 구조상 동작한다. **테스트로 못 박는다** |
| 6 | 공유 묶음 읽기가 새 값을 거부 | `dsl_version` 을 올리지 않으므로 영향 없음. 왕복 테스트로 확인 |

---

## Complexity Tracking

**기록할 예외 없음.** 헌법 원칙 위반도, 정당화가 필요한 복잡도도 없다.

새 개념을 만들지 않고 기존 두 축에 값을 더하는 설계라, 이 기능이 더하는 구조적 복잡도는
열거형 값 4개와 대기 도우미 함수 하나다. 오히려 **줄어드는 것이 있다** — 값 비교 검증의
대기 규칙이 두 갈래(폴링/즉시)에서 하나로 합쳐진다.
