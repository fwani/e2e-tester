# Specification Quality Checklist: Tailwind CSS 전환

**Purpose**: 계획 단계로 넘어가기 전에 명세의 완결성과 품질을 검증한다
**Created**: 2026-09-10
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
      — **조건부 통과.** 아래 Notes 1번 참조. 이 기능은 대상 자체가 기술 스택이라
      기술 이름을 지울 수 없다. 대신 *어떻게* 매핑할지(설정 파일 형태·플러그인 선택·
      클래스 명명)는 명세에서 빼고 plan 으로 넘겼다.
- [x] Focused on user value and business needs
      — 유지보수자 가치(고칠 곳이 한 군데)와 제품 사용자 가치(아무것도 안 바뀜)를 구분해 기술
- [x] Written for non-technical stakeholders
      — **조건부 통과.** Notes 1번 참조
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
      — 해소됨. FR-006 은 2026-09-10 사용자 결정(**전면 해체**)으로 확정
- [x] Requirements are testable and unambiguous
      — FR 20개 모두 검색·테스트 실행·대조로 판정 가능
- [x] Success criteria are measurable
      — SC-002 는 "0건"이 아니라 "문서화된 예외 건수"로 잡았다. 런타임 계산값을 인라인으로
      남기는 것은 정당하므로, 0 을 목표로 두면 편법을 유도한다
- [x] Success criteria are technology-agnostic (no implementation details)
      — SC 8개 모두 결과로 서술. Tailwind 라는 단어가 SC 에 없다
- [x] All acceptance scenarios are defined — US1~US3 각 3개
- [x] Edge cases are identified — 6건. 특히 jsdom 테스트 붕괴와 정본 재추출 충돌
- [x] Scope is clearly bounded — Assumptions 의 "범위 밖" 6항목
- [x] Dependencies and assumptions identified — Dependencies 절 + Assumptions 7항목

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows — 매핑 → 전환 → 회귀 방지의 3단
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification — Notes 1번 참조

## Notes

**1. "구현 세부 배제" 항목의 조건부 통과에 대해**

이 명세는 파일 경로(`theme/tokens.css`·`extract_canon.py`)와 도구 이름(Tailwind)을 담고 있다.
일반적으로는 감점 사유다. 여기서는 그렇게 판단하지 않았다 — 이 기능의 *대상*이 기술 구조
자체이기 때문이다. 기술 이름을 지운 명세는 "스타일을 잘 정리한다" 이상을 말하지 못하고,
그런 명세로는 다음 단계에서 무엇을 지켜야 하는지 알 수 없다.

대신 실제로 지켜야 할 경계는 지켰다: **무엇을 지킬 것인가**(정본 단일성·시각 동일성·테스트 보존)는
명세에 있고, **어떻게 매핑할 것인가**(Tailwind 설정 형태, v3/v4 선택, 플러그인, 클래스 명명 규칙,
전환 순서)는 전부 plan 으로 넘겼다.

**2. FR-006 — 해소됨, 그러나 위험을 안고 간다**

기존 의미 클래스 109개의 처리는 작업량이 몇 배로 갈리는 결정이라 사용자에게 질의했고,
2026-09-10 **전면 해체**로 확정됐다. 세 선택지 중 작업량과 시각 회귀 위험이 가장 큰 쪽이며,
`VisualLanguage.test.tsx` 처럼 클래스 이름을 전제로 하던 회귀 가드의 재설계를 강제한다.

명세는 그 대가를 숨기지 않고 적었다 — Edge Cases 2건, FR-006a/006b, SC-009/010,
Assumptions 2항목이 이 결정 때문에 추가됐다. 위험을 실제로 줄이는 것은 plan 의 몫이다:
전환 순서(한 부품씩 vs 한 화면씩)와 각 단계의 검증 방법이 이 결정의 성패를 가른다.

**3. 검증되지 않은 전제 1건**

Assumptions 의 헌법 Stack 조항 해석(Tailwind 는 스택 교체가 아니다)은 명세 작성자의 판단이다.
`plan.md` 의 Constitution Check 에서 정면으로 다뤄야 하며, 판단이 뒤집히면 헌법 개정이 선행된다.
