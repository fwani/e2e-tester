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
| FR-217 · FR-217a | 통합 대상은 한 테스트의 **일곱 국면**. 목록 · 테스트 만들기 · 키 관리 · 비밀 값은 제외 — *2회차에 만들기가 통합 대상이 되어 여덟 국면 (FR-217b)* |
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

---

## 2회차 검증 (2026-09-08 · 재설계)

**개정 범위**: 관찰 S-12~S-15 · 요구사항 FR-217b · FR-218e-1 · FR-254d · FR-256~262 신설 ·
User Story 5·6 신설 · SC-010~012 신설. FR 49 → 59, SC 9 → 12, User Story 4 → 6.

재검증 결과 — 아래 두 항목이 **처음에 미충족이었고 이 회차에서 고쳤다.**

| 항목 | 처음 상태 | 고친 내용 |
|---|---|---|
| `All acceptance scenarios are defined` | **미충족** — FR-256~262(세로 배분)와 FR-258~260(만들기 국면)에 대응하는 수용 시나리오가 없었다. 요구사항만 있고 "무엇을 보면 됐다고 하는가" 가 없으면 검증할 수 없다 | User Story 5(지금 하는 일이 큰 자리를 갖는다 · 시나리오 5개) · User Story 6(만들기부터 같은 화면이다 · 시나리오 5개) 신설 |
| `No implementation details` | **미충족** — Key Entities 의 「세로 배분」이 `fill` / `content` / `px` 를 값으로 적었다. CSS 어휘이며 명세가 정할 것이 아니다 | 「남는 높이 전부」 / 「내용에 맞는 높이」 / 「정해진 높이」로 바꾸고, 구체적 표현은 UI 계약 소관임을 명시 |

나머지 항목은 재검증에서 충족을 유지한다. 특히:

- `Requirements are testable` — FR-257(주 작업이 ③-a 보다 작은 자리에 놓이지 않는다)은 두
  자리의 높이를 재어 판정할 수 있다. SC-010 이 그 판정을 국면 수로 센다
- `Scope is clearly bounded` — 「이 기능이 하지 않는 것」에 2회차 항목 셋을 추가했다 (최소
  기준 폭을 바꾸지 않는다 · 좌측의 자리를 없애지 않는다 · 만들기만 흡수하고 목록은 아니다)
- `Dependencies and assumptions identified` — 「자리의 고정과 크기의 고정은 다르다」를
  Assumptions 에 명시했다. 1회차가 둘을 함께 고정한 것이 S-12 의 원인이라는 판단이 근거다

### 여전히 미충족 (1건, 1회차와 같은 근거)

`Success criteria are technology-agnostic` — SC-001 이 구현 개수를 직접 센다. 2회차도 같은
이유로 남긴다. 신설한 SC-010~012 는 사용자 체감 쪽이다 — 자리의 크기(SC-010) · 껍데기가
바뀌는 횟수(SC-011) · 답에 도달하는 조작 수(SC-012).

### 1회차 확정 사항 중 2회차가 뒤집은 것

| 1회차 | 2회차 | 뒤집은 근거 |
|---|---|---|
| FR-217a — 「테스트 만들기」는 통합 대상이 아니다 | FR-217b — 통합 대상이다 | 만들기는 여러 테스트를 다루는 화면이 아니라 **한 테스트를 다루는 첫 국면**이다. 목록·키 관리와 같은 부류로 분류한 것이 S-14(껍데기 3벌)의 원인 |
| 「국면 보조 영역」 | 「국면 작업 영역」 (FR-218e-1) | 이름이 그 자리를 보조로 규정했고, 그 규정이 편집 폼 전체를 42px 띠에 넣는 판단으로 이어졌다 (S-12) |
| FR-218a — 좌측 대상 앱 영역이 남는 자리를 차지한다 | FR-218a(폭만) + FR-256(세로는 국면이 정한다) | 폭 규칙을 높이에도 적용한 것이 「채울 것이 없는 자리가 주 자리를 차지하는」 형태로 나타났다 (S-12·S-13) |

**뒤집은 것을 지우지 않고 기록한다.** 1회차의 판단과 그것이 무엇을 낳았는지가 함께 남아야
같은 분류를 다시 하지 않는다.

### 다음 단계

`/speckit-plan` — 세로 배분 규칙과 만들기 국면을 설계로 옮긴다. 1회차 plan 의 3층 구조는
유지되고, ③ 좌측의 높이 모델과 `PhaseAside` → 작업 영역 개명이 추가된다.
