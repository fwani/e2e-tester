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

---

## 2차 검증 — 키 입력으로 범위를 넓힌 뒤 (2026-09-28)

사용자가 둘째 요구(「텍스트 입력 후 엔터·스페이스를 인식하지 못해 스텝 생성이 실패한다」)를
주었고, 023 에 합치기로 결정해 명세를 다시 썼다.

### Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

### Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

### 규모

| | 1차 | 2차 |
|---|---|---|
| User Story | 3 | **4** |
| 기능 요구 (FR) | 26 | **38** |
| 성공 기준 (SC) | 8 | **12** |
| 작업 | 50 | **73** |
| 계약 문서 | 2 | **3** |

### 범위를 넓히며 판단한 것

- **디렉터리 이름을 바꾸지 않았다.** `023-input-value-assertion` 은 첫 요구만 담고 있어
  이제 절반만 맞는 이름이다. 그러나 경로는 이미 커밋 4건에 걸쳐 있고 브랜치 이름이기도
  하다. **문서 제목을 범위의 권위로 삼고** 그 사실을 spec 머리말에 적었다.
- **User Story 를 앞에 끼워 넣어 번호가 밀렸다.** 키 입력이 P1 이 되면서 기존 US1~US3 이
  US2~US4 가 됐다. 뒤에 붙이면 「나중 것이 덜 중요하다」로 읽히는데, 키 입력은 **작성이
  중단되는** 고장이라 그렇지 않다.
- **P1 이 둘이다.** 억지로 순위를 매기지 않았다. 둘은 서로 의존하지 않고 각각 지금 깨져
  있는 시나리오를 하나씩 고친다. 그 이유를 spec 의 User Scenarios 머리에 적었다.
- **FR 번호를 재사용하지 않았다.** 키 입력은 FR-050~060 의 새 블록을 쓴다. 기존 번호가
  tasks·contracts 에서 참조되고 있어 밀면 전부 어긋난다.

### 2차에서 새로 드러난 것

- **녹화가 값을 잃는다** — AI 만의 문제가 아니었다. 태그 칸을 사람이 녹화하면 Enter 뒤의
  빈 값 확정 이벤트가 앞선 입력 Step 을 덮어써서, 최종 정의는 「빈 문자열을 넣는다」 하나가
  된다. 사용자가 보고한 것보다 넓은 결함이며 [research R11](../research.md) 에 경로를
  적었다.
- **한글 IME 의 Enter 가 두 번 눌린다** — 조합 확정과 제출. 가르지 못하면 이 기능은
  한국어 사용자에게 쓸모없고, **영문 검증으로는 절대 드러나지 않는다.** 이것을 spec 의
  「어려운 질문」과 quickstart §10-3 양쪽에 두었다.
- **키 입력은 새 유출 경로가 아니다** — 값을 담지 않는다. 입력값 검증과 보안 성질이 다르다는
  것을 [research R13](../research.md) 에 적어, 같은 방어층을 두 번 쌓지 않도록 했다.

### 확인 필요로 남긴 것

| 항목 | 어디서 해소하나 |
|---|---|
| 한글 IME 에서 **Space** 가 Enter 와 같게 동작하는가 | T003 계열 실측 · quickstart §10-4 |
| `<select>` 값이 정말 내부 식별자로 관찰되는가 | T003 |
| 숨겨진 요소의 값이 읽히는가 | T004 |

셋 다 **문구나 명세 문장이 그 결과에 걸려 있어** 구현 전에 확인해야 한다.
