# Specification Quality Checklist: 입력값 검증 — 칸에 무엇이 들어 있는지 묻는다

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

### 검증 과정에서 고친 것

- **Input 줄에서 구현 세부가 새어 있었다.** 최초 작성본은 사용자 원문을 그대로 실으면서
  관찰 함수 이름과 소스 경로를 담았다. 명세는 비개발자도 읽어야 하므로 같은 사실을
  현상 수준(「입력값은 화면에 보이지만 텍스트로 관찰되지 않는다」)으로 다시 썼다.

### 「표준 Playwright」 언급에 대하여

FR-020~FR-022 와 US2 가 표준 Playwright 를 명시한다. 이것은 구현 선택이 아니라
**헌법 원칙 V 가 정한 제품 약속**이다 — 「사용자는 제품을 사용하지 않더라도 생성한 테스트
자산을 계속 사용할 수 있다」. 021 명세도 같은 이유로 같은 표현을 쓴다. 기술 누수가 아니라
요구사항의 일부로 판단해 유지했다.

### 명세 단계에서 확정한 열린 질문

기능 설명이 열어 둔 네 질문은 모두 이 명세에서 답했다. 근거는 Assumptions 에 있다.

| 질문 | 답 |
|---|---|
| 여러 줄 입력 칸·선택 목록도 같은 종류로 덮는가 | 덮는다. 같은 질문이므로 종류를 나누지 않는다 |
| 값이 없는 대상에 걸면 | 작성 시점 거절 (FR-031) |
| 입력 칸에 텍스트 검증을 막을 것인가 | 막지 않고 경고한다 (FR-030) |
| 작성 시점 어긋남 기록이 적용되는가 | 같게 적용된다 (FR-009) |

### 명세 단계에서 새로 드러난 것

- **비밀번호 값의 평문 유출 경로** (FR-015~FR-017). 기능 설명에 없던 위험이다. 입력 Step
  에는 민감값 방어선이 있지만 검증 Step 의 비교 값에는 없어서, 이 종류가 그대로 우회로가
  된다. 헌법의 보안 제약은 비협상이므로 범위에 포함했다.
- **체크박스·라디오를 거절해야 하는 이유** (FR-032). 값을 갖긴 하지만 그 값이 체크 여부와
  무관하다.
- **손으로 Step 을 넣는 경로는 구조적으로 지원 불가.** 그 경로가 대상 요소를 받지 않기
  때문이며, 범위 외 표에 이유와 함께 명시했다.
