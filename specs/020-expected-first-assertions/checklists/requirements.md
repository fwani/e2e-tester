# Specification Quality Checklist: 기대 동작 기준 검증

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
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

## Notes

**배경 절의 코드 경로 언급에 대해** — `tools.py`·`agent.py` 등 파일 이름이 배경 표에 나온다.
이것은 구현 지시가 아니라 **현재 동작의 근거**다. 「지금 이렇게 동작한다」는 주장은 검증
가능해야 하고, 근거 없이 적으면 이해관계자가 확인할 방법이 없다. 요구사항(FR)·성공
기준(SC) 절에는 구현 세부가 없다.

**해소된 clarification 2건** (2026-09-28, 사용자 결정):

| 항목 | 질문 | 결정 |
|---|---|---|
| FR-021 | 알려진 결함만 실패한 실행의 결말 판정 | (A) 현행대로 FAIL — 결함이 있으면 테스트는 실패한 것이 맞고, 구분은 화면에서 한다 |
| FR-029 | 어긋남 표시 해제의 되돌리기 | (A) 일반 Step 편집과 동일 — 표시와 기록을 함께 제거하고 별도 되돌리기를 두지 않는다 |

**남은 위험** — FR-030(지표 재정의)은 `docs/prd.md` §18 의 수정을 수반한다. PRD 는 이
명세의 상위 문서이므로 plan 단계에서 수정 범위를 명시해야 한다.

**2026-09-28 사용자 추가 전제** — 「성공 케이스를 담아 테스트를 성공시키는 것이 목적이
아니라, 사용자가 원하는 스텝이 도는지·검증되는지 확인하고, 저장된 스텝을 자동으로 돌려
끝까지 패스하는지 확인하는 것이 목적」. 이 문장이 명세 맨 앞 절로 들어갔고 두 갈래를
더했다.

| 갈래 | 더해진 것 |
|---|---|
| 정의는 제품 동작의 사본이 아니라 사용자의 요구서다 | US1 AS-6, FR-031·FR-032, SC-010 |
| 실행은 끝까지 가야 한다 | US6(P1), FR-033~FR-036, SC-008·SC-009 |

FR-033 은 **기존 실행 동작의 변경**이다 — 지금까지 검증 실패는 실행을 중단시켰다
(`itb/execution/runner.py` `run_step()` 이 `StepFailure` 에 `False` 를 돌려준다).
Assumptions 절에 의도된 변경임을 적었고, 설정으로 끄지 않기로 했다.

---

## 구현 중 드러난 것 (2026-09-28)

| # | 무엇 | 반영 |
|---|---|---|
| 1 | **F1 은 결말을 덮는 게 아니라 증거를 지운다.** `clear_failed_steps` 가 모든 `FAIL` 을 `SKIPPED` 로 바꾼다 | 고칠 곳이 1 → 3 (baseline.md) |
| 2 | **`BlockedKind` 는 `blocked.py` 에 둘 수 없다.** 임포트가 순환한다 | `tools.py` 로 (data-model §4) |
| 3 | **막힘 종류는 세션 뷰에도 필요하다.** 이벤트에만 두면 새로고침 뒤 답 칸이 다시 열린다 | `BlockedView.kind` 추가 |
| 4 | **`null` 과 `undefined` 를 같게 다뤄야 한다.** 생성 타입은 필수라고 말하는데 옛 데이터에는 칸이 없다 | `?? null` · 회귀 검증 (data-model §7) |
| 5 | **T024(기존 검증 고치기)의 범위가 비어 있었다.** 검증 실패 중단을 전제한 검증이 0건 | baseline.md T002 |

**FR-031(우회 금지)은 검증할 수 없다 — 이것이 남은 위험이다.**

정합성 점검 F2 는 「지침 외의 방어가 없으므로 검증이 유일한 그물」로 적었는데, 구현해
보니 그 그물도 칠 수 없다. 검증은 드라이버를 대본으로 갈아 끼우고, 갈아 끼우는 것이
바로 「우회할지 말지」의 판단이다.

제품이 할 수 있는 것은 셋뿐이고 전부 검증된다 (`test_no_alternate_route.py`):
지침에 규칙이 들어 있는가, 우회하지 않기로 한 모델에게 막다른 길을 주지 않는가,
그 보고에 질문이 붙지 않는가. **모델이 실제로 지키는지는 실사용에서 관찰해야 한다.**
