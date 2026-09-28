# Specification Quality Checklist: AI 의 손이 어디에 있는지 보인다

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

**검증 1회차에서 고친 것**

- 배경 절에 코드 심볼(`duplicate_with`·`unique`·`_act_on_element`)이 들어가 있었다.
  같은 사실을 제품 언어로 바꿔 적었다 — 「이름만으로 구별되지 않는 요소가 여럿」,
  「가리키는 자리가 하나로 좁혀지지 않으면」.

**[NEEDS CLARIFICATION] 를 두지 않은 이유**

요구를 받을 때 사용자가 「명세에서 정해야 할 것」으로 여섯 가지를 열거했다. 여섯 모두
합리적 기본값이 있어 Assumptions 에 결정과 근거를 적었다. 되물어야 진행할 수 있는 항목은
없다.

| 정해야 했던 것 | 정한 값 | 근거를 적은 곳 |
|---|---|---|
| 표시의 수명 | 시간으로 끊는다 (프레임 번호로 맞추지 않는다) | Assumptions 1·2 |
| 미러 프레임이 없을 때 | 그리지 않는다 | FR-016 |
| 초당 1장 강등 상태 | 표시한다 | Assumptions 3 |
| 성공·실패 구분 | 구분한다 | FR-013 · US2 |
| 화면 살펴보는 중 | 그리지 않는다 | FR-011 · Assumptions 4 |
| 재생 실행 중 | 표시하지 않는다 | FR-007 · SC-006 · Assumptions 5 |

**설계 단계로 넘긴 것**

- 수명의 구체적 길이 (Assumptions 2). 값 하나이고, 명세가 정할 성질이 아니다.
