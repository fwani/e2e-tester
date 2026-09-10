# Implementation Plan: Tailwind CSS 전환

**Branch**: `015-tailwind-css-migration` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-tailwind-css-migration/spec.md`

## Summary

프론트엔드 스타일링을 Tailwind CSS v4 로 옮긴다. 값의 정본(`theme/tokens.css`)은 손대지
않고 **이름만 다시 붙여** Tailwind 테마로 잇는다. 그 위에서 두 가지를 해체한다 —
의미 클래스 139개는 React 부품 컴포넌트로, 배치 인라인 455곳은 유틸리티 클래스로.

**이 작업의 성격**: 새 기능이 아니라 **두 개의 굳은 계약을 다시 세우는 일**이다.
008 시각 언어 계약과 007 배치 계약이 각각 실제 결함(값 리터럴 338개 / S-12 배치 뒤바뀜)을
겪고 세워졌다. 계약을 개정하되 **그 계약이 막던 결함은 다시 허용하지 않는다** — 이것이
FR-020 이고, 계획의 절반이 여기 쓰인다.

**핵심 설계 결정 셋**:

1. 정본을 참조만 한다 (`@theme inline`). 값이 없으므로 어긋날 수 없다 — 규칙이 아니라 구조로
   FR-001 을 만족시킨다.
2. `Record<Phase, …>` 배치 표를 **그대로 둔다.** 표의 출력만 스타일 객체에서 클래스 문자열로
   바꾼다. 컴파일 시점 강제(FR-020a)와 단일 소재지(FR-020b)를 잃지 않는다.
3. 없어지는 `.style.` 단언 45개+ 를 **3겹**(판단·도달·실재)으로 나눈다. 합치면 이전보다
   촘촘하다 — 특히 "클래스 이름이 실제로 CSS 를 만드는가"는 지금 아무도 확인하지 않는다.

## Technical Context

**Language/Version**: TypeScript 5.7, React 19

**Primary Dependencies**: Tailwind CSS v4 (4.3.3) · `@tailwindcss/vite` — **신규 2개**.
기존: Vite 6, React 19, Vitest 2, jsdom 25

**Storage**: N/A (프론트엔드 표현 계층만)

**Testing**: Vitest 2 + jsdom + `@testing-library/react`.
시각 대조는 backend 의 기존 Playwright(chromium)를 재사용 — 새 의존성 없음

**Target Platform**: 데스크톱 브라우저 (최소 폭 1440px — `WorkbenchShell.test.tsx`)

**Project Type**: Web application (frontend/ + backend/). **이번 작업은 frontend/ 만 건드린다.**

**Performance Goals**: 배포 산출 CSS 가 전환 전보다 커지지 않는다 (SC-007).
개발 빌드 시간이 체감 수준으로 나빠지지 않는다

**Constraints**:
- `frontend/src/theme/tokens.css` 1~203줄은 `scripts/extract_canon.py` 의 출력. **손대지 않는다**
- 기존 자동 테스트 86개 파일 전량 통과. 삭제·건너뛰기 0건 (헌법 Quality Gate 4)
- 백엔드·Step DSL·Runner·Generator 무변경

**Scale/Scope**: `.tsx` 43개 · 의미 클래스 139개 · 배치 인라인 455곳 ·
영향받는 테스트 13개 파일 45+ 단언

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 후 재확인.*

### 원칙 I~V

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. Unified Step Model (NON-NEGOTIABLE) | **해당 없음** | Step DSL·Recorder·Generator·Step Editor 의 *모델*을 건드리지 않는다. 바뀌는 것은 Step 을 그리는 CSS 뿐 |
| II. Deterministic Replay (NON-NEGOTIABLE) | **해당 없음 · 확인함** | 이 작업이 만드는 코드 경로에 LLM 요청이 없다. 프론트엔드 표현 계층만 바뀌며 재생 경로(backend Runner)에 파일 변경이 0건 |
| III. Stateful Interactive Runner | **해당 없음** | Pause→Edit→Resume 의 상태 기계에 손대지 않는다. 다만 그 국면을 *그리는* 배치가 바뀌므로, 국면별 화면이 회귀하지 않는지는 FR-008·SC-001 이 본다 |
| IV. Locator Resilience | **해당 없음** | Locator 해석 로직 무변경 |
| V. Asset Portability | **해당 없음** | Export·DSL 저장 형식 무변경 |

**원칙 II 에 대한 명시적 증거** (헌법 Quality Gate 1 이 요구): 이 기능의 변경 파일은 전부
`frontend/src/**` 의 표현 계층과 `frontend/tests/**` 다. 재생 경로는 backend 에 있고
변경 목록에 backend 파일이 없다. `tasks.md` 의 어떤 작업도 backend 를 대상으로 하지 않는다.

### Technology & Security Constraints

**Stack 조항 — 정면 판단** (사용자가 명시적으로 요구한 항목):

> **Stack** (fixed for this MVP; changing it requires an amendment):
> Backend: Python/FastAPI … **Frontend: React.** … Test Step DSL: plain-text …

**판정: 개정 불필요.** Tailwind 도입은 이 조항이 말하는 스택 변경이 아니다.

근거 셋:

1. **조항이 고정한 것은 열거된 세 항목이다.** Tailwind 는 React 를 대체하지 않는다.
   React 는 그대로 남고, Tailwind 는 그 위에서 CSS 를 만든다. 열거 항목 중 어느 것도
   교체되지 않는다.
2. **조항의 목적에 비추어도 그렇다.** 스택을 고정한 이유는 MVP 중 기반 기술 교체로 인한
   재작업을 막는 것이다. Tailwind 는 backend·Step DSL·Runner·Generator 어디에도 닿지 않고,
   교차 언어 스키마 의무(같은 절의 다음 문단)와도 무관하다. 이 도입이 만드는 재작업은
   프론트엔드 표현 계층에 한정되며, 그 재작업 자체가 이 기능의 내용이다.
3. **선례.** 008 은 `scripts/extract_canon.py`(Python)와 `count-violations.mjs`(Node)를
   새로 들이면서 개정 절차를 밟지 않았다. 도구 추가는 스택 변경으로 취급되지 않아 왔다.

⚠️ **이 판정은 뒤집힐 수 있다.** 유지보수자가 "프론트엔드 스타일링 방식도 스택"이라고 읽으면
헌법 개정이 선행되어야 한다. 판단 근거를 남기는 것이 이 절의 목적이며, 이의가 있으면
구현 시작 전에 제기되어야 한다.

**Security requirements**:

| 요구 | 이 기능에서 |
|---|---|
| No hardcoded secrets | 해당 없음 — 스타일에 비밀값이 없다 |
| 민감 입력 마스킹 | **확인 대상.** `InlineSecret`·`SensitiveAcrossPhases` 테스트가 있는 화면의 마스킹 표현이 전환으로 깨지지 않아야 한다. FR-008 에 포함 |
| 외부 입력 검증 | 해당 없음 |
| 생성 코드를 데이터로 취급 | 해당 없음 |
| 오류의 명시적 처리 | 해당 없음 |

**공급망 관점**: npm 의존성 2개(`tailwindcss`·`@tailwindcss/vite`)가 늘어난다. 둘 다 같은
제공자의 공식 패키지이며 버전을 고정해 `package-lock.json` 에 남긴다.

### Development Workflow & Quality Gates

| 게이트 | 이 기능에서 어떻게 만족하는가 |
|---|---|
| 1. 원칙 준수 | 위 표. 원칙 II 증거 명시 |
| 2. Round-trip integrity | **해당 없음** — Step DSL·Recorder·Generator 무변경 |
| 3. 테스트 동반 | 새 가드 4종(클래스 실재·충돌 금지·행선지 대응·L2 대조). 기존 86개 파일 유지 |
| 4. **No disabled tests** | **이 기능 최대의 위험.** 아래 별도 |
| 5. 성공 지표 인식 | PRD §18 지표(테스트 생성·NL 변환·재생·인계 복구)는 기능 동작 지표이며 이 작업이 직접 바꾸지 않는다. **다만 시각 회귀는 「테스트 생성 시간」에 간접 영향**을 준다 — 조작이 안 보이거나 초점이 사라지면 느려진다. SC-001·SC-008 이 그것을 막는다 |

**게이트 4 — 가장 깨지기 쉬운 곳**

13개 파일 45+ 단언이 `element.style.X` 를 읽는다. 인라인을 제거하면 이 값들은 전부 `""` 가
되어 **한꺼번에 실패한다.** 이때 가장 쉬운 길은 단언을 지우거나 `toBeDefined()` 로 무르게
바꾸는 것이고, 그것이 헌법 게이트 4 위반이다.

이 계획이 그 길을 막는 방법:

1. **판정 방법만 바꾸고 검증 대상은 바꾸지 않는다** (research R4 의 3겹).
   각 테스트가 무엇을 보던 것인지 파일 머리주석에 이미 적혀 있다 — 그것을 다시 읽고
   같은 것을 새 방법으로 본다.
2. **바꾼 테스트마다 무엇을 왜 바꿨는지 적는다** (FR-014). 이 저장소의 기존 관행이다.
3. **단언 수를 센다.** 전환 전후의 단언 총수를 비교해 줄어들면 그 자리를 지목한다.
   "지우지 않았다"를 말이 아니라 수치로 확인한다.

### Constitution Check 결과

**통과.** 위반 0건. Stack 조항 판정 1건은 근거를 남기고 진행하며, 이의 제기 창구를 열어 둔다.

## Project Structure

### Documentation (this feature)

```text
specs/015-tailwind-css-migration/
├── plan.md                      # 이 파일
├── spec.md                      # 요구사항 22 · 성공기준 13
├── research.md                  # Phase 0 — 결정 8건 + 미해결 스파이크 3건
├── data-model.md                # Phase 1 — 이 기능이 다루는 개념과 그 관계
├── quickstart.md                # Phase 1 — 검증 절차
├── contracts/
│   ├── tailwind-theme.md        # 정본 토큰 ↔ Tailwind 이름 대응 규칙
│   ├── layout-contract-v2.md    # 007/008 배치 계약의 개정판
│   └── class-migration.md       # 의미 클래스 139개 행선지 대응표 (SC-009)
├── checklists/
│   └── requirements.md
└── tasks.md                     # /speckit-tasks 산출 — 아직 없음
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── theme/
│   │   ├── tokens.css           # 정본. **손대지 않는다** (extract_canon.py 출력)
│   │   ├── tailwind.css         # 신규 — @import + @theme inline 대응만. 값 없음
│   │   ├── exceptions.ts        # 기존 예외 등록부. 새 체계에 맞게 갱신
│   │   └── tone.ts
│   ├── lib/
│   │   ├── layout.ts            # 배치 표. Record<Phase,…> **유지**, 출력만 클래스로
│   │   └── capabilities.ts      # PHASE_TABLE — 같은 규율. 참고만
│   ├── ui/                      # 신규 — 의미 클래스 139개가 해체되어 오는 곳
│   │   └── (Button, Chip, Notice, Modal, Field, … 부품 컴포넌트)
│   ├── components/              # 기존 43개 .tsx 중 부품 아닌 것
│   └── pages/
├── tests/                       # 86개 파일. 13개가 판정 방법 변경 대상
├── scripts/
│   └── count-violations.mjs     # 위반 계수기. 새 축(충돌·행선지)을 더한다
└── vite.config.ts               # @tailwindcss/vite 추가

scripts/                          # 저장소 루트 (Python)
├── extract_canon.py             # 정본 추출. **손대지 않는다**
├── design_render.py             # L1 대조. 방법론을 L2 가 재사용
└── design_compare_ba.py         # 신규 — L2 대조 (전환 전 ↔ 후)

docs/
└── PENDING-HUMAN-VERIFICATION.md # 사람 판정 항목 등록 (기존 관행)
```

**Structure Decision**: 기존 `frontend/` + `backend/` 웹 애플리케이션 구조를 그대로 쓴다.
새로 만드는 디렉터리는 `frontend/src/ui/` 하나뿐이며, 이것이 해체된 의미 클래스 139개의
행선지다. `components/` 와 나누는 기준은 **재사용 가능한 부품인가**다 —
`ui/` 는 도메인을 모르고, `components/` 는 안다.

## 전환 순서

research R6 의 결정을 작업 순서로 편다. **각 단계가 끝날 때 테스트 전량이 통과해야 한다.**

| 단계 | 내용 | 끝났다고 말할 수 있는 조건 |
|---|---|---|
| **0. 스파이크** | S1(`@theme inline` + `var()`) · S2(클래스 실재 가드) · S3(L2 대조) | 셋 다 되는 방법이 확인됨. **S1 실패 시 R2 재설계** |
| **1. 기반** | Tailwind 설치 · `tailwind.css` · 토큰 이름 대응 · L2 기준선 뜨기 | 유틸리티가 정본 색을 그린다. 기존 화면 무변경·테스트 전량 통과 |
| **2. 부품** | 의미 클래스 139개 → `ui/` 컴포넌트. 한 부품씩 | 대응표 「미완료」 0건. `tokens.css` 에 부품 클래스 0개 |
| **3. 배치** | 인라인 455곳 → 유틸리티. 한 화면씩 | 인라인 잔량 = 문서화된 예외뿐 |
| **4. 계약·가드** | 계약 문서 개정 · 가드 4종 완성 · 테스트 13개 판정 방법 전환 | 단언 수 감소 0. 새 가드가 실제로 실패를 잡는다 |
| **5. 판정** | L2 대조 · 사람 대조 등록 | 불일치 0건 또는 설명된 차이만 |

**2단계와 3단계 사이에 화면이 깨지지 않는 이유**: Tailwind 유틸리티와 남은 의미 클래스는
공존한다. 단 **한 요소는 한 체계만** 쓴다 (research R7) — 이 규칙을 가드가 센다.

## Complexity Tracking

> 헌법 위반은 없다. 아래는 **이전 기능의 결정을 뒤집는 것**에 대한 기록이며,
> 헌법 Governance 의 "Deviations discovered after merge are recorded" 정신을 따른다.

| 뒤집는 결정 | 왜 필요한가 | 무엇으로 대체하는가 |
|---|---|---|
| 008 `visual-language.md` §2 「허용되는 인라인 `style`」 | 사용자가 배치까지 전면 전환을 선택했다 (2026-09-10). 이 목록이 남아 있으면 전환 대상의 정의가 모순된다 | `contracts/layout-contract-v2.md` 가 대체한다. 허용 목록이 사라지고 **인라인은 런타임 계산값만** 남는다 |
| 007 배치 계약 — 배치를 인라인 `style` 로 표현 | 위와 같음 | **표현만** 클래스로 바뀐다. `Record<Phase,…>` 표와 「부모가 내려준다」 구조는 **유지**된다 (research R3). 구조가 남으므로 S-12 는 다시 허용되지 않는다 |
| `element.style.X` 기반 레이아웃 단언 45개+ | 인라인이 사라지면 읽을 것이 없다 | 3겹(판단·도달·실재)으로 분해 (research R4). 단언 수는 줄지 않고 늘어난다 |

**되돌리는 비용**: 각 단계가 별도 커밋이므로 단계 단위로 되돌릴 수 있다.
2단계(부품)와 3단계(배치)는 서로 독립이므로 한쪽만 되돌리는 것도 가능하다.

## 위험과 대응

| # | 위험 | 징후 | 대응 |
|---|---|---|---|
| RK-1 | S1 실패 — `@theme inline` 이 정본 참조로 동작하지 않음 | 스파이크에서 불투명도 수식이 깨짐 | R2 를 다시 정한다. 차선책은 `extract_canon.py` 에 Tailwind 블록 생성을 더하는 것(정본 파이프라인 확장) — 값은 여전히 한 곳에서 온다 |
| RK-2 | 테스트 13개가 무르게 바뀜 | 단언 수 감소, `toBeDefined()` 증가 | 단언 수를 세는 것을 게이트로 (게이트 4 대응 3) |
| RK-3 | 부품 일관성 상실 — 같은 버튼이 화면마다 다름 | `ui/` 밖에서 버튼 모양을 조립 | 부품 먼저 전환(R6) + 대응표(R8) |
| RK-4 | Tailwind 가 클래스를 못 찾아 조용히 무스타일 | 화면이 벌거벗음. 테스트는 통과 | 클래스 실재 가드(R4 ③). **이 위험이 R4 ③ 의 존재 이유다** |
| RK-5 | 커밋이 거대해져 회귀 추적 불가 | TestList(55곳)·ProjectSetup(55곳)을 한 커밋에 | 화면 하나 = 커밋 하나. 큰 화면은 더 쪼갠다 |
| RK-6 | 정본이 두 곳이 됨 | `tailwind.css` 에 값이 적힘 | 값 없는 대응만 허용. 가드가 센다 (FR-016) |

## Constitution Check — Phase 1 재확인

설계 산출물(`data-model.md`·`contracts/`·`quickstart.md`)을 만든 뒤 다시 본다.

| 항목 | 재확인 결과 |
|---|---|
| 원칙 I~V | 변동 없음. 설계에서 backend·Step DSL·Runner·Generator 를 건드리는 것이 하나도 나오지 않았다 |
| 원칙 II 증거 | `quickstart.md` 의 검증 절차 전부가 frontend 와 대조 스크립트에 한정된다. 재생 경로에 닿는 절차가 없다 |
| Stack 조항 | 판정 유지 (개정 불필요). 설계에서 React 를 대체하는 것이 나오지 않았다 |
| 보안 — 민감값 마스킹 | `quickstart.md` H-6 으로 판정 항목화했다 |
| **게이트 4 (No disabled tests)** | 설계로 강화됐다. `quickstart.md` §1-1 이 **단언 총수 비교**를 절차에 넣었고, `layout-contract-v2.md` LC-6 이 계약으로 못 박았다. 말이 아니라 수치로 확인된다 |
| 게이트 3 (테스트 동반) | 가드 4종(G-A~G-D)이 `data-model.md` §7 에 정의됐고, 각각 **실제로 실패를 잡는지 확인하는 절차**가 `quickstart.md` 에 있다 (§1-3·§1-4) |

**설계에서 새로 드러난 것 1건**: `quickstart.md` §1-7 (국면을 임시 추가해 컴파일 실패를
확인) 은 FR-020a 가 살아 있음을 **실증하는** 절차다. 계획 단계에서는 "표를 유지하므로
강제가 남는다"는 논증이었는데, 논증만으로는 나중에 누군가 표를 우회해도 알 수 없다.
절차로 만들어 두면 확인할 수 있다.

**Phase 1 재확인 결과: 통과.** 위반 0건.
