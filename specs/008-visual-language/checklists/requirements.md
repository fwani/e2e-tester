# Specification Quality Checklist: v1 잔재를 걷어내고 v2「계기판」을 코드에 세운다

**Purpose**: 계획 단계로 넘어가기 전 명세의 완결성과 품질을 검증한다
**Created**: 2026-09-08
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

## 검증 기록

**2026-09-08 · 1회차 — 전 항목 통과.** 아래 셋은 초안을 쓰는 동안 의식적으로 피한 함정이며,
검증에서 다시 확인했다.

| 항목 | 함정 | 명세가 택한 형태 |
|---|---|---|
| No implementation details | "`tokens.css` 로 승격한다", "CSS 클래스로 소비한다" 처럼 파일명·기술을 지목하기 | "시각 언어의 값은 **한 곳에만** 존재한다"(FR-263), "이름으로 참조한다"(FR-265). 어떤 파일·어떤 방식인지는 계획 단계 소관 |
| Success criteria technology-agnostic | "`var(--)` 참조율 100%" 처럼 참조 문법에 묶기 | "색상 값을 직접 적은 곳이 0개"(SC-402), "값이 두 곳에 존재하지 않는다"(SC-404). 참조 방식과 무관하게 셀 수 있다 |
| Requirements testable | "일관성 있게 보인다" 같은 판정 불가 문장 | 전부 셀 수 있는 형태 — 색 0종(FR-268), 잉크 채움 화면당 1개(FR-269), 필터 4종 존재(FR-272), 미판정 0건(FR-284) |

**확정 디자인의 어휘는 구현 세부가 아니다.** FR-264 가 `.btn`·`.chip`·`.srow` 같은 이름을,
FR-269 가 `--hair`·`#14171C` 를 지목하는 것은 기술 선택이 아니라 **확정 디자인이 이미 정의한
대상을 가리키는 고유명**이다. 이름을 흐리면 무엇을 옮겨야 하는지가 사라진다.

## 남은 판단 (계획 단계에서 정한다 — 명세 결함 아님)

명세는 **무엇을**까지만 정했다. 아래는 `plan` 이 정할 **어떻게**다.

- 시각 언어 정본을 두는 방식 (전역 스타일 시트 / 모듈 스코프 / 다른 방식)
- 정본 우회를 잡는 검사의 구현 방식과, 예외 등록부를 두는 자리
- 대조 축 중 기계가 세는 것과 사람이 보는 것의 경계선
- 확정 디자인 화면을 실제로 열어 보는 경로 확보 방법 (FR-283)
- 33개 화면 파일의 전환 순서와 회귀 검증 단위

## Notes

- `[NEEDS CLARIFICATION]` 마커는 0건이다. 판정 주체(FR-284 의 완료 조건을 누가 채우는가)는
  이번 기능의 성패를 가르는 지점이지만, 001·002 가 같은 자리에서 미완으로 남은 기록이 있어
  **기계 판정을 최대화한다**는 전제로 확정했다. 근거는 spec.md 의 Assumptions 첫 항목에 있다.
  이 전제를 바꾸려면 FR-282·FR-284 와 SC-401 을 함께 고쳐야 한다.
