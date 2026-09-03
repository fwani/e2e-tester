# Specification Quality Checklist: Interactive AI Test Builder (MVP — P0 + P1)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-03
**Feature**: [spec.md](../spec.md)
**Validation iterations run**: 2 (초기 작성 후 1회, `/speckit-clarify` 후 1회)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — 3건 모두 2026-09-03 clarify 세션에서 해소
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Coverage Traceability

명세가 근거 문서를 빠뜨리지 않았는지 확인한 결과.

| 근거 | 명세 반영 위치 |
|------|---------------|
| PRD §5 Flow A (Manual Record) | US1, FR-023~FR-030 |
| PRD §6 자연어 Record | US4, FR-059~FR-068 |
| PRD §7 Interactive Editing | US3, FR-031~FR-043 |
| PRD §7.2 AI Add | US6, FR-078~FR-081 |
| PRD §8 Human Takeover | US5, FR-069~FR-077 |
| PRD §9 Test Step Model | FR-010~FR-016, Key Entities |
| PRD §10 Locator 전략 | US7, FR-017~FR-022 |
| PRD §11 Test Execution | US2, FR-044~FR-058 |
| PRD §12 AI 사용 원칙 | FR-044, FR-063, SC-006 |
| PRD §14 P0 / P1 | Scope In Scope 2개 절 |
| PRD §15 제외 항목 | Scope Out of Scope |
| PRD §16 핵심 화면 | FR-002~FR-009, FR-026~FR-027, FR-046~FR-058 |
| PRD §18 성공 지표 5종 | SC-001~SC-005 |
| PRD §20 핵심 가설 | US5 (Why this priority) |
| 헌법 원칙 I Unified Step Model | FR-010, FR-014, FR-062, FR-075, FR-080 |
| 헌법 원칙 II Deterministic Replay | FR-044, FR-045, FR-063, FR-080, SC-006 |
| 헌법 원칙 III Stateful Runner | FR-031~FR-043, SC-007 |
| 헌법 원칙 IV Locator Resilience | FR-017~FR-022, SC-008 |
| 헌법 원칙 V Asset Portability | Assumptions (P2로 이연, Step 모델 설계 제약으로 유지) |
| 헌법 보안 요건 | FR-082~FR-087, SC-010 |
| `TestList.dc.html` | FR-002~FR-007 |
| `CreateTest.dc.html` | FR-008, FR-009, Assumptions(브라우저) |
| `AiRecord.dc.html` | FR-059~FR-064 |
| `Main.dc.html` | FR-026, FR-027, FR-046, FR-047 |
| `RunnerPaused.dc.html` | FR-031~FR-039, FR-078 |
| `Takeover.dc.html` | FR-069~FR-077 |
| `StepInspector.dc.html` | FR-019, FR-020, FR-016 |
| `RunResult.dc.html` | FR-050~FR-058 |

## Notes

### 재검증 결과 (2026-09-03, `/speckit-clarify` 이후)

**16/16 항목 통과** (이전 15/16). 상태가 바뀐 항목 1건:

- `No [NEEDS CLARIFICATION] markers remain` — 미통과 → **통과**. 마커 3건이 모두 결정으로 대체되었다.

회귀(통과 → 미통과)한 항목은 없다.

### clarify 세션에서 확정된 결정 5건

| # | 질문 | 결정 | 반영 위치 |
|---|------|------|-----------|
| 1 | 이미 실행된 Step 편집 시 Resume 보장 범위 | 편집은 정의에만 반영, 브라우저는 되돌리지 않음, 경고 후 현재 상태에서 이어서 실행 | FR-040a~d, US3 시나리오 8·9 |
| 2 | MVP 배포 형태 | 단독 로컬 도구. 계정·권한 없음. 로컬 파일 저장 | FR-088a~d, 새 제외 범위 절 |
| 3 | 브라우저 조작 지점 | 관찰 국면 = 제품 내 읽기 전용 미러, 조작 국면 = 실제 브라우저 창 | FR-023a~c, FR-047a~b |
| 4 | 민감 값 보관·공급 | 비대칭 키 쌍. 공개키 암호화 / 실행 시 비밀키 복호화. 환경 변수 우선 | FR-089a~g, SC-011, 엔티티 2종 추가 |
| 5 | 검증 조건 범위 | 4종 — 보임 / 안 보임·없음 / 텍스트 / URL | FR-013a~c, FR-037 |

### 규모

기능 요구사항 120개(하위 요구사항 포함), 성공 기준 12개, 사용자 스토리 7개, 명세 711줄.
요구사항 20개를 크게 넘으므로 `/speckit-checklist`로 별도 품질 점검을 수행할 가치가 있다.

### 사이클 중 범위 변경 1건 (2026-09-03, plan 단계 중)

사용자가 **멀티 탭 지원**을 명시적으로 요청했다. 기존 명세는 "단일 탭만 지원"이었으므로 정면 충돌이며,
plan을 계속하기 전에 spec → research → data-model 순으로 되돌아가 고쳤다.

| 문서 | 변경 |
|------|------|
| `spec.md` | FR-030 전면 개정 → FR-030a~g. FR-012에 탭 참조 추가. FR-013에 `close_tab` 추가. FR-023a·FR-047c 연계. US1 시나리오 2건·US2 시나리오 1건 추가. 엣지 케이스 5건 추가. 새 엔티티 `TabRef`. SC-012 추가 |
| `research.md` | R1에 탭 관리, R2에 멀티 탭 기록 절, R3에 탭별 미러 전환, R5에 `list_tabs`·`close_tab` 도구 추가 |
| `data-model.md` | `Step.tab` 필드, `close_tab` Step 종류, 탭 해석 규칙, `TabHandle` 엔티티와 번호 재사용 금지 불변식, `StepResult.tab`/`tab_wait_ms` |
| `contracts/` | REST 탭 엔드포인트 2개, WebSocket 탭 이벤트 3개, DSL 멀티 탭 전체 예 |

**설계상 다행인 점**: `add_init_script` 와 `expose_binding` 을 `Page` 가 아니라 `BrowserContext` 에
등록하는 결정(research R2)이 이미 내려져 있었기 때문에, 새 탭에 리코더가 자동 주입된다. 멀티 탭 지원의
추가 비용이 탭 참조 부여·해석과 미러 탭 전환으로 한정되었다.

**새로 생긴 취약점**: 탭 참조를 열린 순서로 부여하므로 대상 앱이 비결정적 순서로 탭을 열면 참조가 어긋난다.
감추지 않고 실패로 드러내며, SC-012(탭 참조 어긋남 실패율 10% 이하)를 그 실측 지표로 두었다.
URL 패턴 기반 탭 식별은 P2로 이연했다.

### 남은 주의 사항

- **성능 목표 미정** — Step 실행 지연, 미러 뷰 갱신 빈도 등 정량 목표가 없다. 영향이 낮고 기술 선택에
  종속되므로 `/speckit-plan`에서 정하는 것이 적절하다. (Deferred)
- **언어모델 제공자·모델 미정** — 작성 단계에만 영향을 주고 원칙 II가 실행 경로를 격리하므로 명세 수준의
  결정이 아니다. `/speckit-plan`의 research 단계 대상이다. (Deferred)
- **일시정지 세션 유휴 상한 미정** — 단독 로컬 도구로 확정되어 자원 격리 압력이 사라졌으므로 영향이 낮다.
  (Outstanding, 낮은 영향)
