# Specification Quality Checklist: 네 화면을 하나로 — 통합 작업 화면과 국면별 조작 권한

**Purpose**: 계획 단계로 넘어가기 전에 명세의 완결성과 품질을 검증한다
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
- [ ] Success criteria are technology-agnostic (no implementation details)
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

### clarify 세션 2026-09-08 — 미해결 3건 전부 해소

| 위치 | 확정 내용 |
|---|---|
| FR-217 · FR-217a | 통합 대상은 한 테스트의 **일곱 국면**. 목록 · 테스트 만들기 · 키 관리 · 비밀 값은 제외 |
| FR-218 ~ FR-218f | 껍데기는 고정, 내부 배분만 유연. **3층 구조**(헤더 / 전폭 국면 띠 / 좌: 대상 앱 + 국면 보조 · 우: Step 목록 + 상세)로 확정 |
| FR-254 ~ FR-254c | 통합 화면 **artboard 를 새로 만들어** 확정 디자인을 갱신하고 그것을 대조 기준으로 삼는다. 대체 관계를 기록하고, 승인 전 초안은 기준이 아니다 |

추가로 확정한 것 — 국면 고유 내용(AI 지시문 · 진행 로그 · 차단 선택지 · 검증 추가 폼)의 자리는
좌측 대상 앱 영역 아래의 국면 보조 영역이며, AI 실패 · 차단 사유는 그 자리에 상시 보인다
(FR-218e · FR-218f). 001 research R2 의 "실패가 조건 뒤에 숨는" 결함을 구조로 막는다.

### 여전히 미충족 (1건, 근거 있음)

`Success criteria are technology-agnostic` — SC-001(`Step 목록을 그리는 구현이 1개, Step
상세가 1개`)은 구현 구조를 직접 센다. 사용자가 제기한 문제 자체가 "다 따로 만드니까" 이므로
중복 구현 개수가 이 기능의 성과를 재는 가장 직접적인 지표다. 사용자 체감 쪽 지표는
SC-002 · SC-003 · SC-005 · SC-008 이 별도로 담당한다. 의도적으로 남긴다.

### 관찰 근거 표의 파일 경로 인용

`문제의 실제 모습` 표는 파일 경로와 줄 번호를 인용한다. 005 · 006 명세가 확립한 관행이며
"추측이 아니라 확인된 사실" 임을 밝히는 근거 표시다. 요구사항 본문은 어떤 구조로 만들지를
지정하지 않는다.

### 다음 단계

`/speckit-plan` — 확정된 3층 구조와 새 artboard 방침을 설계로 옮긴다.
