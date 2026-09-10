# Specification Quality Checklist: 엑셀로 프로젝트 내보내기·가져오기

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-10
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

## 검증 이력

### specify 1회차 — 초안 검증 (2026-09-10)

발견한 문제 3건, 모두 조치했다.

| # | 항목 | 문제 | 조치 |
|---|---|---|---|
| 1 | 구현 세부 누출 | 서버/프론트 역할 분담이 요구사항 쪽에 있었다 | 요구사항에서 빼고 Assumptions 에 근거와 함께 남겼다. 파일 확장자(`.xlsx`)는 사용자가 교환하는 **형식 규약**이라 요구사항에 필요하다고 판단해 유지 |
| 2 | 측정 불가 | SC-003 이 "잘 읽힌다"였다 | 도구 3종(엑셀·구글 시트·LibreOffice)을 명시하고 "별도 변환 없이 표로 읽힌다"로 바꿨다 |
| 3 | 미해결 표시 누락 | 범위를 크게 가르는 결정 2건이 조용한 가정으로 묻혀 있었다 | [NEEDS CLARIFICATION] 2건으로 올려 사용자에게 물었고, 답을 받아 FR-014a~c · FR-026a~b 로 확정했다 |

### clarify — 모호성 스캔 (2026-09-10)

질문 4건을 물어 모두 답을 받았다. 반영 위치는 아래와 같다.

| 질문 | 확정 | 반영 |
|---|---|---|
| 가져오기 파일 상한 | 100MB / 시트 200 / 총 5,000행. 단 제품의 기존 상한과 맞물려야 한다 | FR-036, FR-036a~c · SC-010 · 시나리오 13·14 |
| 접두어를 정할 수 없는 시트 | 미리보기에서 사용자가 입력. 비우면 건너뛴다. 시스템이 만들어내지 않는다 | FR-022a~c · 시나리오 10 |
| 파일 안 TC ID 중복 | 뒤엣것에 비어 있는 새 번호. 행을 잃지 않는다 | FR-023a~b · 시나리오 11 |
| 기존 그룹과 접두어 같고 이름 다름 | 기존 이름 유지 + 알림. 가져오기가 기존 자산을 고치지 않는다 | FR-024a · SC-011 · 시나리오 12 |

**「기존 상한과 맞물려야 한다」가 이번 clarify 의 가장 중요한 소득이다.** 파일을 *읽는* 상한과
프로젝트가 *수용할 수 있는* 양은 다른 것이고, 후자를 확인하지 않으면 초안을 만들다가 번호가
바닥나 반쯤 만들어진 상태로 끝난다. FR-036a·FR-036b 가 그것을 막는다.

### 체크리스트 상태

specify 종료 시점 16/16 → clarify 종료 시점 16/16. 상태가 바뀐 항목 없음.
clarify 는 통과 여부를 바꾼 것이 아니라, "testable and unambiguous" 를 만족하던 항목들의
**해상도**를 올렸다 (FR-022 의 "~하거나 ~하거나" 두 갈래를 하나로 확정한 것이 대표적이다).

## Notes

- 미해결 항목 0건. `/speckit-plan` 으로 진행 가능하다.
- plan 단계에서 정할 사안으로 미룬 것: 초안의 디스크 배치, 시트 이름 변환 규칙의 구체적 알고리즘,
  스프레드시트 라이브러리 선택과 계층 배치(import-linter 계약), 오류 코드 이름.
