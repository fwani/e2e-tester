# Specification Quality Checklist: 저장된 테스트를 고치는 길

**Purpose**: 계획(plan) 단계로 넘어가기 전에 명세의 완결성과 품질을 검증한다
**Created**: 2026-09-07
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

검증 1회차에 전 항목 통과. 다만 두 항목은 판단 근거를 남긴다.

1. **"No implementation details"** — 「문제의 실제 모습」 표에 소스 파일 경로와 엔드포인트
   경로가 나온다. 이것은 **요구사항이 아니라 관찰 증거**이며, 005 명세가 UX 리포트를 출처로
   삼아 코드 위치를 함께 적은 것과 같은 형태다. 요구사항(FR) 본문에는 언어·프레임워크·구현
   방식이 없다. 편집 화면을 새로 만들지 기존 화면을 편집 가능하게 할지는 명세가 정하지 않고
   설계로 넘겼다 (FR-179 · Assumptions).

2. **Step 종류 이름(`fill`·`select`·`navigate`)** — 이 제품의 Step DSL 은 헌법 Principle I
   이 정한 제품의 단일 진실이므로 도메인 어휘로 본다. 기술 스택 노출이 아니다.

3. **[NEEDS CLARIFICATION] 0건** — 범위를 가르는 단 하나의 질문(브라우저 없는 편집을
   포함하는가)은 명세 작성 중 사용자에게 확인했고 Assumptions 첫 항목에 결정으로 기록했다.
   남은 미확정 1건("편집 가능 여부의 기준으로 나뉘지 않는 항목")은 설계 단계에서 판정할
   사항이므로 Assumptions 에 「확인 필요」로 남겼다 — 명세를 막지 않는다.

---

## 구현 후 최종 확인 (T086 · 2026-09-07)

명세는 구현을 거치며 두 곳이 바뀌었다. 둘 다 조용히 넘기지 않고 근거를 남겼다.

1. **FR-187 범위 제외** — 헌법 원칙 IV 가 MUST 로 고정한 해석 순서와 충돌하고, 브라우저
   없이 검증할 수 없는 후보는 거짓 `verified` 이거나 조용한 무효 편집이 된다 (설계 조사 R6).
   테스트로 고정했다: 편집 요청 모델에 locator 필드를 넣으면 422 다
   (`test_definition_edit_api.py::test_locator_fields_are_not_accepted`).

2. **FR-177 재작성** — 원문은 "정의 보기 화면이 편집으로 넘어가는 수단을 제공" 이었는데,
   설계가 목록의 「정의 보기」를 「편집」으로 대체하면서(R1) 그 표면이 사라졌다. 적용 대상을
   「읽기 전용으로 그려지는 경우」로 좁혔다 (analyze F1).

체크리스트 16항목은 그대로 통과 상태다 — 두 변경 모두 요구사항을 **명확하게** 만들었고,
모호하게 만들지 않았다.

**남은 미완 1건**: T092 (quickstart S1~S8 을 사람이 직접 걷는 확인). 자동 검증으로 덮이지
않는 시각·조작 항목이며, 005 의 T110 과 같은 성질이다.
