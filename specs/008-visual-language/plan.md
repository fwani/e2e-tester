# Implementation Plan: v1 잔재를 걷어내고 v2「계기판」을 코드에 세운다

**Branch**: `008-visual-language` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-visual-language/spec.md`

## Summary

확정 디자인 18장은 **글자 하나까지 같은 80줄 스타일 시트**를 공유한다 (research R1). 그 시트를
`frontend/src/theme/tokens.css` 의 **정본**으로 기계 추출하고, 33개 화면 파일이 인라인 값을
버리고 `className` 으로만 소비하게 한다. 값이 한 곳에만 존재하면 어긋남은 사건이 아니라 불가능이
된다.

같은 어긋남이 다시 생기지 않게 하는 것이 나머지 절반이다. `import.meta.glob` 로 화면 파일
**전체를 열거**하는 가드가 색 리터럴과 시각 언어 인라인 선언을 세고 `파일:줄` 로 보고한다.
대조 축은 텍스트 통계에서 **렌더 계산값**으로 바꾼다 — 확정 디자인이 chromium 에서 정상
렌더된다는 것을 확인했으므로(research R2) 디자인과 정본을 같은 방식으로 재서 비교할 수 있다.
그 결과 사람이 눈으로 판정할 항목이 **화면당 3개, 총 54개**로 줄어든다. 지금은 509칸이며
전부 미판정이다.

## Technical Context

**Language/Version**: TypeScript 5 / React 19 · Python 3.11+ (대조 도구)

**Primary Dependencies**: Vite · vitest · @testing-library/react · playwright (backend venv, 대조 도구 전용). **새 런타임 의존성 없음**

**Storage**: N/A — 이 기능은 저장 형식을 건드리지 않는다

**Testing**: vitest + @testing-library/react. 기준선 **50파일 · 657건 전부 통과** (커밋 `b033ee0`)

**Target Platform**: 데스크톱 브라우저, 최소 기준 폭 1440px

**Project Type**: Web application (backend + frontend). **이 기능은 frontend 와 대조 도구에만 닿는다**

**Performance Goals**: Step 목록 200개 렌더 예산 유지 (`tests/StepListPerformance.test.tsx`). 900px 높이에서 Step 13행 (SC-409)

**Constraints**: 새 의존성 금지 · 검사 삭제/약화 금지 · 백엔드 무변경 · 확정 디자인 무변경

**Scale/Scope**: 화면 18종 · 전환 대상 tsx 33개 (11,234줄) · 정본 시트 80줄 · 잔존색 17종 · 색 리터럴 327곳

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 설계 후 재점검.*

| 원칙 | 이 기능과의 관계 | 판정 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | Step DSL·스키마·저장 형식을 **건드리지 않는다.** 변경 대상은 `frontend/src/theme/` · 화면 컴포넌트의 표시 속성 · `frontend/tests/` · `scripts/design_baseline.py` 뿐이다. `src/types/generated/` 는 읽기만 한다 | ✅ 해당 없음 (무관함을 명시) |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 재생 경로에 닿지 않는다. LLM 호출을 새로 만들지 않으며, 백엔드 `api/routes/` 를 수정하지 않는다 (research R7 이 필터를 클라이언트로 결정한 이유 중 하나) | ✅ 해당 없음 (무관함을 명시) |
| **III. Stateful Interactive Runner** | 화면 전환·세션 유지 동작을 바꾸지 않는다. FR-274 가 정보·조작·문구 보존을 요구하므로 국면 전환 완주 검증을 US2 수용 시나리오 5에 둔다 | ✅ 보존 요구로 반영 |
| **IV. Locator Resilience** | 무관. `LocatorPriorityTable` 은 **표시만** 바뀌고 우선순위 로직은 건드리지 않는다 | ✅ 해당 없음 |
| **V. Asset Portability** | 무관. 내보내기 경로에 닿지 않는다 | ✅ 해당 없음 |

**품질 게이트**

| 게이트 | 계획이 어떻게 만족시키나 |
|---|---|
| 1. 원칙 준수 | 위 표. 재생 경로 무변경을 파일 범위로 증명한다 |
| 2. 왕복 무결성 | Step DSL·Recorder·Generator 무변경이므로 해당 없음 |
| 3. 테스트 동반 | 정본 추출·가드·대조 도구 각각에 검사를 붙인다. 화면 전환마다 657건을 돌린다 |
| 4. **검사 무력화 금지** | 인라인 `style` 을 읽는 4건(`WorkbenchShell.test.tsx`)이 유일한 충돌 후보다. **삭제·약화하지 않고 그대로 초록으로 유지한다** — research R3 의 결정에 따라 배치 계약을 인라인으로 남기기 때문이다. 다른 검사가 깨지면 왜 깨졌는지 먼저 판정하고, 그 판정을 커밋 본문에 적는다 |
| 5. 성공 지표 인식 | PRD §18 의 네 흐름(작성·변환·재생·복구)에 기능 변경이 없다. 다만 밀도 개선(5행→13행)이 작성·복구의 조작 수를 줄이는 방향임을 SC-409 로 센다 |

**보안 제약**

- 비밀 값 가림은 `InlineSecretInput` · `SecretValues` · `KeyManagement` 의 **표시 로직**에 있다.
  이 기능은 그 로직을 건드리지 않고 껍데기만 바꾼다. `tests/InlineSecret.test.tsx` ·
  `tests/SensitiveAcrossPhases.test.tsx` · `tests/KeyManagement.test.tsx` 가 회귀를 막는다 (FR-277)
- 새 외부 입력 경로가 없다. 가드가 읽는 것은 저장소 안의 소스 원문뿐이다
- 하드코딩 비밀값 없음 — 이 기능이 다루는 리터럴은 색상 값이다

**단순성**

새 의존성 0. 새 빌드 단계 0. 정본은 이미 존재하는 순수 CSS 80줄이고, 가드는 이미 도는 vitest
옆에 붙는다. CSS Modules·CSS-in-JS 를 기각한 근거는 research R4 에 있다 — 007→008 에서 "전사"
방침이 결함이 된 전례가 있으므로, **정본을 다시 쪼개는 안은 모두 기각했다.**

**위반 없음. Complexity Tracking 불필요.**

## 일곱 가지 결정

계획이 반드시 정해야 했던 것과 그 답이다. 근거는 전부 [research.md](./research.md) 에 있다.

| # | 결정 | 근거 |
|---|---|---|
| 1 | **전역 클래스 시트 승격.** dc.html 의 80줄을 `tokens.css` 정본으로 기계 추출. 토큰 **이름은 현행 유지**, 값만 정본에서 받는다 | R1(18장 동일) · R4(대안 4개 비교). 인라인+`var()` 안은 색만 고치고 형태 중복을 남겨 SC-404 를 못 만족시킨다 |
| 2 | **vitest 가드 1개.** `import.meta.glob` 로 화면 파일 전체 열거. 색 리터럴·시각 언어 인라인 선언·미등록 클래스·정본 이탈을 세고 `파일:줄` 로 보고 | R5. 손으로 import 하는 현행 방식이 V-09 의 원인이다 |
| 3 | **예외 등록부 = `frontend/src/theme/exceptions.ts`.** 가드가 그 파일을 읽는다. 항목마다 사유 문자열 필수 | R5 (FR-267 은 검사가 등록부를 읽어야 성립한다) |
| 4 | **대조 축 3층 (L1 값 / L2 소비 / L3 구조).** L1·L2 는 기계, L3 만 사람. `design_baseline.py` 는 고쳐 쓴다 | R6. 509칸 → 54칸. 001·002 가 남긴 미완 기록이 근거다 |
| 5 | **확정 디자인은 그대로 둔다.** `support.js` 404 는 렌더에 영향이 없음을 실측 확인 | R2 |
| 6 | **전환 순서 = 정본/가드(경고) → US1 → US2 → US3 → US4(가드 조이기).** 검증 단위는 파일이 아니라 **화면** | R8 |
| 7 | **목록 필터·정렬은 클라이언트.** 백엔드 `list_tests` 는 `q` 만 받고, 응답이 이미 `outcome`·`last_run_at` 을 담는다 | R7. 백엔드 무변경은 Out of Scope 와도 일치 |

### 이 계획이 성립하는 논증

```
L1: 정본 시트 == 확정 디자인 시트   (렌더 계산값 비교 — 기계)
L2: 화면 코드 == 정본만 소비        (가드 — 기계)
─────────────────────────────────────────────────────
∴  화면의 색·기하·타이포 == 확정 디자인   (구성상)

남는 것: L3 구조·가감·상태 표현      (사람, 화면당 3항목)
```

L1 과 L2 중 하나라도 없으면 이 논증이 무너지고, 다시 사람이 509칸을 채우는 일로 돌아간다.
**그래서 US4 는 선택 사항이 아니다.**

## Project Structure

### Documentation (this feature)

```text
specs/008-visual-language/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — R1~R8, 전부 실측
├── data-model.md        # Phase 1 — 정본·등록부·대조표의 구조
├── quickstart.md        # Phase 1 — 화면 하나를 옮기는 표준 절차
├── contracts/
│   ├── visual-language.md      # 정본의 계약 — 무엇이 정본이고 무엇이 소비인가
│   └── design-conformance.md   # 대조 3층의 정의와 완료 판정
├── checklists/requirements.md
├── spec.md
└── tasks.md             # /speckit-tasks 산출 (이 명령이 만들지 않는다)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── theme/
│   │   ├── tokens.css          # ★ 정본 — dc.html 80줄에서 기계 추출
│   │   └── exceptions.ts       # ★ 신규 — 예외 등록부 (가드가 읽는다)
│   ├── pages/                  # 8개 — 전환 대상
│   ├── components/             # 13개 — 전환 대상
│   │   ├── workbench/          # 8개 — 잔재 최다
│   │   └── design/             # 2개 — 껍데기
│   ├── lib/layout.ts           # 배치 계약 — 유지, 값 출처만 정본으로
│   └── App.tsx · main.tsx
└── tests/
    ├── DesignTokens.test.tsx   # 뒤집는다 — 파일 전체 열거 + 4개 축
    ├── VisualLanguage.test.tsx # ★ 신규 — L2 소비 가드
    ├── WorkbenchShell.test.tsx # 그대로 초록 유지 (배치 계약)
    └── … 47개                  # 전부 초록 유지

scripts/
├── design_baseline.py          # 고쳐 쓴다 — 텍스트 통계 → L1 렌더 계산값 + L3 항목
└── design_render.py            # ★ 신규 — chromium 으로 dc.html·정본을 렌더해 계산값 추출

docs/design/008-visual-language/
├── *.dc.html                   # 입력. 고치지 않는다
└── conformance/*.md            # 재생성 — 축이 바뀐다
```

**Structure Decision**: 기존 web application 구조를 그대로 쓴다. 새 디렉터리는 없고, 신규 파일은
셋뿐이다 — `theme/exceptions.ts`(등록부) · `tests/VisualLanguage.test.tsx`(L2 가드) ·
`scripts/design_render.py`(L1 측정). 백엔드는 건드리지 않는다.

## 전환 순서 (검증 단위 = 화면)

각 단계 끝에서 `npm test`(657건)가 초록이어야 다음으로 간다.

| 단계 | 대상 | 끝났을 때 |
|---|---|---|
| **0. 정본** | `tokens.css` 추출 · `exceptions.ts` · `design_render.py` · 가드(경고 모드) | 정본이 서고, 위반 327건이 수치로 보인다 |
| **1. US1** | `TestList.tsx` · `design/Chrome.tsx` · `Badges.tsx` + 필터/정렬 신설 | 목록 2상태가 디자인과 같고 그 파일의 색 리터럴 0 |
| **2. US2** | `workbench/*` 8 · `SessionScreen` · `EditView` · `ComposeView` · `MirrorView` · `TabStrip` · `PacingControl` · `LocatorPriorityTable` · `AssertionForm` · `StepEditFields` · `InlineSecretInput` | 9국면 + Step 상세가 디자인과 같다 |
| **3. US3** | `ProjectSetup` · `KeyManagement` · `SecretValues` · `ResultView` · `ErrorNotice` · `SessionLostBanner` · `LiveConnectionBanner` · `StartingIndicator` · `NoticeStack` · `design/BrowserFrame` | 나머지 6장 |
| **4. US4** | 가드를 **실패 모드**로 전환 · `design_baseline.py` 개편 · 대조표 18장 재생성 · L3 판정 | 미판정 0 · 불일치 0 |

**0단계에서 가드를 경고 모드로 두는 이유**: 33파일이 전부 위반 상태이므로 처음부터 실패시키면
1단계 첫 커밋조차 못 만든다. 위반 수를 **상한선**으로 잡고 단계마다 내려서, 4단계에서 0으로
고정한다. 상한선은 올릴 수 없다 — 올리려면 커밋 본문에 이유를 적어야 한다.

## 위험과 대응

| 위험 | 조짐 | 대응 |
|---|---|---|
| 정본 클래스가 실제 화면을 감당하지 못한다 | US1 에서 `.btn`·`.chip` 으로 표현 안 되는 조작이 나온다 | **확정 디자인에 없는 형태**라는 뜻이다. 정본을 임의로 늘리지 않고 `undefined-states.md` 에 기록한다 (FR-266·DC-009). US1 에서 드러나므로 33파일 뒤가 아니라 첫 화면에서 값을 치른다 (R8) |
| 클래스 전환으로 검사가 깨진다 | 657건 중 일부 빨강 | R3 이 4건으로 좁혔다. 그 외가 깨지면 **왜 깨졌는지 판정**하고 커밋 본문에 적는다. 검사를 고쳐 통과시키지 않는다 (게이트 4) |
| 필터·정렬 신설이 기능 추가로 번진다 | 정렬 기준이 디자인에 없는 것까지 늘어난다 | 디자인이 정의한 것만 만든다 — 필터 4종, 정렬 「최근 실행 순」. 그 이상은 Out of Scope |
| L3 판정이 또 미완으로 남는다 | 54항목이 채워지지 않는다 | 항목 수를 화면당 3개로 묶은 것이 1차 대응이다. 그래도 남으면 **그 사실을 완료 보고에 명시**한다 — 조용히 넘어가는 것이 001·002 를 반복하게 만든 방식이다 |
| 밀도 개선이 접근성을 해친다 | 글자가 11px 로 내려가 읽기 어려워진다 | 확정 디자인의 대비비는 문서화돼 있다(`--ink-3` 4.6:1). 11px 는 라벨·보조 정보에만 쓰이고 본문은 13px 다. 값을 임의로 바꾸지 않고, 문제가 있으면 불일치로 기록해 디자인 개정으로 넘긴다 |

## Complexity Tracking

헌법 위반 없음. 이 표는 비운다.

## 다음 단계

`/speckit-tasks` — 위 5단계를 작업 단위로 자른다. 검증 단위가 화면이므로 작업도 화면 단위로
묶고, 같은 화면 안의 파일들은 `[P]` 로 병렬 가능 표시를 붙인다.

## Constitution Check — Phase 1 설계 후 재점검

설계가 끝난 뒤 다시 봤다. **새 위반 없음.**

| 확인 | 결과 |
|---|---|
| 새 런타임 의존성 | 0. playwright 는 backend venv 에 이미 있고 **대조 도구 전용**이라 제품에 실리지 않는다 |
| 새 파일 | 3개 — `theme/exceptions.ts` · `tests/VisualLanguage.test.tsx` · `scripts/design_render.py`. 전부 검사·도구이며 제품 코드가 아니다 |
| 백엔드 변경 | 0 (research R7 이 필터를 클라이언트로 결정) |
| 검사 삭제·약화 | 0. 인라인 `style` 을 읽는 4건은 **배치 계약으로 유지**하므로 초록 그대로다 (R3) |
| 원칙 I·II | 설계 어디에도 Step DSL·재생 경로가 없다. `contracts/` 두 문서 모두 표시 층만 다룬다 |
| 보안 | 가림 로직 무변경. 가드가 읽는 것은 저장소 안의 소스 원문뿐이며 새 입력 경로가 없다 |
| 단순성 | 정본은 이미 존재하는 순수 CSS 80줄이고, 가드는 도는 검사 옆에 붙는다. 정본을 다시 쪼개는 안(CSS Modules·CSS-in-JS)은 R4 에서 기각 |

**Complexity Tracking: 비어 있음** — 정당화가 필요한 위반이 없다.
