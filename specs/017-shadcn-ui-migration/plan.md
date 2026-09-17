# Implementation Plan: shadcn/ui 부품 체계 전환과 화면 깨짐 전수 수정

**Branch**: `feat/ui-component-style` | **Date**: 2026-09-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-shadcn-ui-migration/spec.md`

## Summary

프론트엔드의 부품 층(`frontend/src/ui/`)을 shadcn/ui 방식으로 다시 세우고, 실제 화면을 띄워 찾은 깨짐
11건(B-01~B-11)을 고친다. **모습은 008 정본 그대로, 동작은 표준으로** — 사용자 결정 1.

**이 작업의 성격**: 015 가 「값을 어디서 가져오는가」를 다시 세웠다면 017 은 **「부품이 어떻게 동작하는가」**
를 다시 세운다. 조사에서 드러난 사실이 방향을 정했다 — 대화상자 5개·행 메뉴·펼침 어느 것도 초점 이동·
가두기·Esc·되돌림을 갖지 않았다. 그리고 가장 급한 깨짐(B-01)은 **015 가 고친 줄 알았던 것이 화면에 닿지
않은** 경우였다. 수정이 정본의 클래스 규칙에만 들어갔는데 앱은 그 규칙을 싣지 않는다.

**핵심 설계 결정 다섯** ([research.md](research.md)):

1. **CLI 가 아니라 원본 이식** (R1). `shadcn init` 이 CSS 에 쓰는 것(tw-animate·oklch 변수·base 층)을 끌
   수 없다. 레지스트리 원본을 `src/ui/` 에 옮기며 클래스를 정본 이름으로 바꾼다.
2. **동작이 필요한 곳만 표준 부품** (R2). 대화상자·확인 대화상자·메뉴·탭·분절 선택·툴팁·알림.
   체크박스·라디오·선택칸·펼침은 **네이티브** — 정본 모습이 네이티브이고, 동작 이득이 없으며, 번들이
   8 kB 준다. **2026-09-16 개정**: 그 동작 층을 `radix-ui` 에서 **Base UI**(shadcn 의 기본 갈래)로
   바꾼다 — 사용자 결정 3·4 (spec 배경). 무엇을 표준 부품으로 둘지는 바뀌지 않는다.
3. **정본 밖 스케일을 구조로 막는다** (R4). 색에 더해 모서리·그림자·글자 크기·움직임 이름공간을 비운다.
   shadcn 원본의 `rounded-md`·`shadow-xs` 가 지금은 **생성되어 가드를 통과한다.**
4. **`cva` 는 쓰고 `tailwind-merge` 는 쓰지 않는다** (R5). 병합기는 이 테마를 모르고(실측), 이 저장소는
   호출자의 모양 덮어쓰기를 금지한다. 변종 표 안의 충돌은 넓힌 G-E 가 잡는다.
5. **알림 층의 자리는 문서의 띠가 정한다** (R6). 값 하나로는 풀리지 않는다 — 국면 띠가 있는 화면·없는
   화면·머리띠도 없는 화면이 섞여 있다.

## Technical Context

**Language/Version**: TypeScript 5.7, React 19

**Primary Dependencies**: **신규 2개** — `@base-ui/react` 1.8.x(Dialog·AlertDialog·Menu·Tabs·
ToggleGroup·Tooltip·**Toast**), `class-variance-authority` 0.7.x. shadcn CLI 는 의존성이 아니다 —
원본을 받아 오는 도구로만, **임시 폴더에서** 버전을 고정해 쓴다. 저장소에 `components.json` 을 두지
않는다 (R1).
*2026-09-16 개정: `radix-ui` 1.6.7 로 구현했다가 Base UI 로 바꾼다. 의존성 **수는 그대로**다. peer 는
React 17~19(우리는 19)이고 날짜 부품용 peer(`date-fns`·`@date-fns/tz`)는 선택 사항이라 설치하지 않는다.*
**들이지 않는 것**: `tailwind-merge`, npm `cn`, `lucide-react`, `tw-animate-css`, `sonner`, Geist 글꼴,
shadcn 의미 토큰, Base UI `Select`·`Checkbox`·`RadioGroup`·`Collapsible`(네이티브로 둔다).
기존: Tailwind CSS 4.3.3 · `@tailwindcss/vite`, Vite 6, Vitest 2, jsdom 25, `@testing-library/react` 16

**Storage**: N/A (프론트엔드 표현·상호작용 계층만)

**Testing**: Vitest 2 + jsdom + `@testing-library/react`. jsdom 환경 보완은 `tests/setup/dom.ts` 한 곳
(research R10). 시각 대조와 화면 순회는 backend 의 기존 Playwright(chromium) — L1 `scripts/design_render.py`,
L2 `scripts/design_compare_ba.py`, 신규 `scripts/screen_sweep.py`. 새 테스트 의존성 없음

**Target Platform**: 데스크톱 브라우저(chromium 계열), 뷰포트 1280~2560 × 800~1440

**Project Type**: Web application (frontend/ + backend/). **이번 작업은 `frontend/` 와 검증 스크립트
(`scripts/`)만 건드린다.** backend 무변경

**Performance Goals**: CSS gzip ≤ **6.78 kB**(+10%), JS gzip ≤ **181.3 kB**(+30% — research R12 에서 실측으로
고쳐 정함). `StepListPerformance`(50행 렌더) 계속 통과

**Constraints**:
- `frontend/src/theme/tokens.css` 정본 구획 무변경 (`extract_canon.py` 출력)
- Tailwind preflight 를 들이지 않는다. `--color-*: initial` 유지 (015 C-1·C-8)
- 기존 자동 테스트 1364건 전량 통과, 단언 2148 에서 줄지 않는다, 건너뜀 0 (헌법 Quality Gate 4)
- 008 시각 언어 유지 — 사용자 결정 1
- 백엔드·Step DSL·Runner·Generator 무변경

**Scale/Scope**: 부품 파일 8 → 약 20 · 원시 `<button>` 50 · `<input>` 50 · `<select>` 4 · `<textarea>` 5 ·
`<Button` 88 · `navLinkClasses` 26 · 수제 대화상자 5 · 수제 메뉴 1 · 알림 층 정의 3 · 테스트 110 파일
(판정 방법 변경 예상 약 20). 화면 깨짐 11건

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 후 재확인 — 아래 「Phase 1 재확인」.*

### 원칙 I~V

| 원칙 | 판정 | 근거 |
|---|---|---|
| I. Unified Step Model (NON-NEGOTIABLE) | **해당 없음** | Step DSL·Recorder·Generator·Step Editor 의 *모델*을 건드리지 않는다. 바뀌는 것은 Step 을 그리고 고르는 부품이다 |
| II. Deterministic Replay (NON-NEGOTIABLE) | **해당 없음 · 확인함** | 변경 파일은 `frontend/src/**`·`frontend/tests/**`·`scripts/**`·`specs/017-*/**`·`docs/PENDING-HUMAN-VERIFICATION.md` 뿐이다. 재생 경로(backend Runner)에 파일 변경 0건. 새 부품이 요청을 만들지 않는다 |
| III. Stateful Interactive Runner | **간접 영향 · 가드 있음** | 상태 기계는 무변경. 녹화·결과 국면의 조작(저장·중지·실패 Step 부터 실행)이 알림에 덮여 **누를 수 없던** 것(B-01)을 고친다 — 「멈추고 고치고 이어 가기」의 화면 쪽 전제다. 미러 입력이 대화상자·초점 관리에 빼앗기지 않는지는 FR-016·SC-013·quickstart H-2 가 본다 |
| IV. Locator Resilience | **해당 없음** | 해석 로직 무변경. `LocatorPriorityTable` 은 모습만 표 부품으로 |
| V. Asset Portability | **해당 없음** | Export·DSL 저장 형식 무변경 |

**원칙 II 에 대한 명시적 증거** (헌법 Quality Gate 1): `tasks.md` 의 어떤 작업도 `backend/` 를 대상으로 하지
않는다. 화면 순회 스크립트는 backend 를 **실행**할 뿐 고치지 않는다. quickstart §5 가 `git diff --stat
-- backend/` 0 을 확인한다.

### Technology & Security Constraints

**Stack 조항 — 정면 판단**

> **Stack** (fixed for this MVP; changing it requires an amendment): … **Frontend: React.** …

**판정: 개정 불필요.** 015 의 판정(Tailwind 도입)과 같은 논리이며, 이번에는 **실행 의존성**이 들어오므로
한 가지를 더 따진다.

1. **조항이 고정한 것은 열거된 항목이다.** 부품 동작 라이브러리는 React 를 대체하지 않는다. 화면은
   여전히 React 로 그려진다. *2026-09-16: 그 라이브러리를 다른 것(Base UI)으로 바꾸는 것도 같은
   판정에 든다 — 성격도 의존성 수도 그대로다.*
2. **조항의 목적** — MVP 중 기반 기술 교체로 인한 재작업 방지. 이 도입은 frontend 표현·상호작용 계층에만
   닿고 backend·Step DSL·교차 언어 스키마 의무와 무관하다.
3. **실행 의존성이라는 차이.** Tailwind 는 빌드 도구였고 동작 라이브러리는 번들에 실린다. 그 대가는 번들 예산
   (SC-011)과 공급망 점검(아래)으로 관리하며, 스택의 성격(React SPA)을 바꾸지 않는다.

⚠️ 015 와 같이 **이 판정은 뒤집힐 수 있다.** 유지보수자가 부품 라이브러리 도입을 스택 변경으로 읽으면 구현
전에 개정 절차가 선행되어야 한다.

**Security requirements**:

| 요구 | 이 기능에서 |
|---|---|
| No hardcoded secrets | 해당 없음. 순회 시드의 값은 가짜이며 격리 디렉터리(`.sweep/`, `.gitignore`)에만 산다 |
| 민감 입력 마스킹 | **확인 대상.** `Input` 부품이 `type="password"` 5곳과 `InlineSecret`·`SensitiveAcrossPhases` 가 지키는 마스킹을 깨지 않아야 한다 — 테스트 + quickstart H-6 |
| 외부 입력 검증 | 해당 없음 |
| 오류의 명시적 처리 | 해당 없음 |

**공급망**: npm 의존성 2개(`@base-ui/react`·`class-variance-authority`)가 늘어난다. 버전을 고정해
`package-lock.json` 에 남긴다. shadcn 원본은 저장소 안에서 고쳐지고 리뷰되며 출처가 파일 머리에 남는다 —
원격 코드가 런타임에 섞이지 않는다.

### Development Workflow & Quality Gates

| 게이트 | 이 기능에서 어떻게 만족하는가 |
|---|---|
| 1. 원칙 준수 | 위 표. 원칙 II 증거 명시 |
| 2. Round-trip integrity | **해당 없음** — Step DSL·Recorder·Generator 무변경 |
| 3. 테스트 동반 | 새 가드 2종(G-F 부품 모습 · G-G 원시 요소) · 넓힌 가드 2종(G-E `cva` · 헬퍼 판정 문자) · 순회 보고서 테스트 · 동작 테스트 4종(대화상자 초점·메뉴 키보드·모달 위 알림·대화상자와 미러 입력). [test-ledger.md](contracts/test-ledger.md) |
| 4. **No disabled tests** | 아래 별도 |
| 5. 성공 지표 인식 | PRD §18 의 재실행·인수 복구 흐름이 **B-01 로 직접 막혀 있었다** — 실패 Step 부터 재실행, 녹화 저장·중지가 알림 밑에 깔렸다. 이 기능은 그 조작 가능성을 되돌린다. 측정 지표 자체는 바꾸지 않는다 |

**게이트 4 — 가장 깨지기 쉬운 곳**

조사 결과 판정 방법을 바꿔야 하는 테스트가 **약 20개 파일**이다. 원인은 넷으로 모인다.

| 원인 | 파일 | 가장 쉬운 (그리고 금지된) 길 |
|---|---|---|
| 표준 메뉴가 `.click()` 으로 열리지 않는다 | `RowMenuVisible` · `TestListActions` · `EditEntryPoints` | 「메뉴가 열린다」 단언을 지운다 |
| **(09-16)** 상태 속성 이름이 갈래마다 다르다 (`data-state=active` → `data-active` · `aria-checked` → `aria-pressed`) | `InteractionStates` · `PacingControl` · `RunnerPacing` · 거르기·칩 계열 | 단언을 `toBeDefined()` 로 무르게 |
| **(09-16)** 알림이 부품으로 바뀐다 | `ToastPlacement` · `ToastDismiss` · `ToastOverModal` · `NoticesAreToasts` | 「자리」 단언을 지우고 「뜬다」만 남긴다 |
| 배타 선택이 `aria-pressed` 가 아니라 라디오로 알려진다 | `PacingControl` · `RunnerPacing` | `getAttribute` 단언을 `toBeDefined()` 로 |
| 모달이 뒤쪽에 `aria-hidden` 을 건다 | 확인 대화상자를 여는 화면 테스트 | 뒤쪽 확인을 뺀다 |
| 깨짐 수정이 배치 판단 자체를 바꾼다 | `VerticalSplit` · `TargetPane` · `ComposePhase` · `WorkbenchShell` · `NoticesAreToasts` | 기대값을 현재 값으로 맞추고 이유를 남기지 않는다 |

이 계획이 그 길을 막는 방법:

1. **판정 방법만 바꾸고 검증 대상은 바꾸지 않는다.** 줄마다 「무엇을 검증하던 테스트인가」를 먼저 적는다
   ([test-ledger.md](contracts/test-ledger.md) `verifies` 칸).
2. **넷째 원인은 판단이 바뀌는 것이다.** 기대값을 고치되 **그 판단이 옳다는 근거를 테스트 밖에서도 댄다** —
   화면 순회 보고서에서 그 깨짐이 사라졌다는 것 (data-model §9 「고쳤다」의 정의).
3. **단언 수를 센다.** 기준선 2148. 파일 단위 전·후를 기록에 적는다.
4. **가드는 넓히기만 한다** ([guards.md](contracts/guards.md) 「가드를 바꿀 때의 규칙」).

### Constitution Check 결과

**통과.** 위반 0건. Stack 조항 판정 1건은 근거를 남기고 진행하며 이의 제기 창구를 연다. 이전 기능의 결정을
뒤집는 것들은 Complexity Tracking 에 기록한다.

## Project Structure

### Documentation (this feature)

```text
specs/017-shadcn-ui-migration/
├── plan.md                  # 이 파일
├── spec.md                  # 사용자 스토리 4 · 요구사항 31 · 성공기준 13
├── baseline.md              # 전환 전 실측 — 테스트·소스·산출물·화면 깨짐 11건
├── baseline-shots/          # 전환 전 캡처 11장 (webp)
├── research.md              # Phase 0 — 결정 12 · 스파이크 5
├── data-model.md            # Phase 1 — 개념 12
├── quickstart.md            # Phase 1 — 기계 판정 §1~§5 · 사람 판정 H-1~H-8
├── contracts/
│   ├── ui-parts.md          # 부품 목록 · shadcn→정본 이식 대응표 · 흡수하는 특수 자리 · 동작 요구
│   ├── layout-contract-v3.md # 층위 · 알림 자리 · 화면 정책 · Step 패널 세로 배분
│   ├── guards.md            # G-A~G-G · 넓히는 헬퍼 · 새 가드 둘
│   ├── screen-sweep.md      # 화면 깨짐 순회 SW-1~SW-8
│   └── test-ledger.md       # 헌법 Gate 4 기록
├── checklists/
│   └── requirements.md
└── tasks.md                 # /speckit-tasks 산출 — 아직 없음
```

### Source Code (repository root)

```text
frontend/
├── package.json                  # @base-ui/react · class-variance-authority (09-16: radix-ui 제거)
├── vite.config.ts                # test.setupFiles 추가
├── src/
│   ├── theme/
│   │   ├── tokens.css            # 정본. **손대지 않는다**
│   │   ├── tokens.app.css        # 생성물. 손대지 않는다
│   │   ├── tailwind.css          # radius·shadow·text·animate 이름공간 비우기 (R4)
│   │   └── exceptions.ts         # raw-element 축 추가
│   ├── ui/                       # 부품 층 — 같은 자리에서 교체한다 (R1)
│   │   ├── cn.ts                 # 신규 · 로컬 잇기
│   │   ├── Button.tsx            # shadcn button 이식 · navLinkClasses 흡수
│   │   ├── Chip.tsx              # shadcn badge 이식
│   │   ├── Input.tsx · Textarea.tsx · NativeSelect.tsx · Checkbox.tsx · Radio.tsx · Label.tsx   # 신규
│   │   ├── Dialog.tsx · AlertDialog.tsx · OverlayPane.tsx · DropdownMenu.tsx                    # 신규 · Base UI
│   │   ├── Toast.tsx             # 신규 (09-16) · Base UI Toast — 손으로 만든 알림 층을 대신한다
│   │   ├── Tabs.tsx · ToggleGroup.tsx · Tooltip.tsx · Disclosure.tsx                            # 신규
│   │   ├── Field.tsx · Table.tsx · Notice.tsx · Surface.tsx · StepRow.tsx                       # 교체
│   │   └── useToastDismiss.ts    # 그대로
│   ├── lib/layout.ts             # Step 패널 바닥 상한 표 · 만들기 targetSlot (v3 L4·L5)
│   ├── components/
│   │   ├── design/Chrome.tsx     # Artboard policy · 머리띠를 스크롤 영역 밖으로 (v3 L3)
│   │   ├── Toast.tsx             # 알림 층 aria-live
│   │   └── workbench/*           # 알림 층 복사본 삭제 · StepDetail → DetailPanel · 원시 요소 → 부품
│   └── pages/*                   # 원시 요소 → 부품 · 수제 모달·메뉴 → 부품 · 화면 정책
└── tests/
    ├── setup/dom.ts              # 신규 · jsdom 보완 (R10)
    ├── helpers/tailwind.ts       # cva·cn 읽기 · 판정 문자 집합 (guards H-1·H-2)
    ├── UiSkin.test.ts · RawElements.test.ts · ScreenSweep.test.ts                                # 신규 가드
    ├── DialogFocus.test.tsx · MenuKeyboard.test.tsx · ToastOverModal.test.tsx · MirrorInputWithDialog.test.tsx
    └── sweep-report.json         # 신규 · 순회 보고서 (커밋)

scripts/                           # 저장소 루트 (Python)
├── screen_sweep.py               # 신규 · 화면 깨짐 순회 (screen-sweep.md)
├── design_compare_ba.py          # L2 · INTENDED 갱신
└── design_render.py              # L1 · 그대로

docs/PENDING-HUMAN-VERIFICATION.md # §17 추가 (quickstart H-1~H-8)
.gitignore                         # .sweep/ 추가
```

**Structure Decision**: 기존 `frontend/` + `backend/` 구조를 그대로 쓴다. 새 디렉터리는 `frontend/tests/setup/`
하나다. 부품은 shadcn 관례(`src/components/ui/`)가 아니라 **기존 `src/ui/`** 에 둔다 — 경로를 박은 테스트
5개와 015 의 `ui/`(도메인 모름) · `components/`(도메인 앎) 구분을 지킨다 (research R1).

## 전환 순서

**각 단계가 끝날 때 테스트 전량이 통과하고, 단계마다 커밋한다.** 한 화면·한 부품 = 한 커밋 (015 RK-5).

| 단계 | 내용 | 끝났다고 말할 수 있는 조건 |
|---|---|---|
| **0. 스파이크** | S1 이름공간 비우기 · S2 G-E `cva` · S3 jsdom + 표준 부품 · S4 개발 서버 순회 · S5 `:has()` 변종 | 다섯 다 되는 방법 확인. 실패하면 research 의 대안으로 |
| **1. 기반** | 의존성 · `cn` · `tests/setup/dom.ts` · 이름공간 비우기 · 가드 넓히기(H-1·H-2) · G-F · G-G(예산=기준값) · `screen_sweep.py` + 첫 보고서(깨짐을 **예산**으로 등록) | 화면 무변경 · 테스트 전량 통과 · 순회가 B-01~B-11 을 전환 전과 같이 잰다 |
| **2. US1 — 누를 수 있다** (MVP) | 알림 층 정의 하나 · 띠 조건 자리 · `aria-live` · 세션 토스트 삭제 | 순회에서 B-01·B-02 사라짐 · `ToastPlacement` 강화 |
| **3. US2 — 부품** | 부품 하나씩: `Button`·`Chip` → 폼 부품 → `Table` → `Dialog`·`AlertDialog`·`DetailPanel` → `Menu` → `Tabs`·`ToggleGroup` → `Tooltip`·`Disclosure`. 부품마다 그 부품의 원시 요소를 화면에서 옮긴다 | [ui-parts.md](contracts/ui-parts.md) §1 상태 전부 ✅ · G-G 예산 = 예외 수 · 옛 부품 참조 0 · 동작 테스트 4종 통과 |
| **4. US3 — 배치** | v3 L3(화면 정책·머리띠) · L4(Step 패널 바닥) · L5(만들기 자리) · L6(사유 문구) · B-07~B-09 는 3단계 부품이 대부분 끝낸다 — 남은 것 | 순회 허용되지 않은 검출 0 |
| **5. US4 — 판정** | 순회 보고서 확정 · L2 `INTENDED` · 가드 일부러 깨기(quickstart §1-2) · 번들 · test-ledger 마감 · 사람 판정 §17 등록 | quickstart §1~§5 전부 기대대로 |
| **6. 기반 교체와 알림** (2026-09-16 개정) | 6-0 스파이크 S6~S8 → 6-1 순회에 알림 화면 추가(**지금은 실패해야 한다**) → 6-2 알림을 Base UI Toast 로 · 자리 이동 · 되풀이 제거(N-02) → 6-3 부품 8개를 Base UI 로 · `radix-ui` 제거 → 6-4 대조·번들·기록 | `radix-ui` 참조 0 · 순회 검출 0(알림 화면 포함) · L2 등록되지 않은 차이 0 · 번들 ≤ 177.41 kB |

**2단계를 3단계 앞에 두는 이유**: B-01·B-02 는 사용자가 지금 겪는 작업 차단이고, 부품 전환 없이 고칠 수 있다.
3단계가 길어져도 가치가 먼저 나간다.

**3단계 안에서 대화상자·메뉴를 폼 부품 뒤에 두는 이유**: 대화상자가 `Button`·`Input` 을 쓴다. 그리고 모달이
테스트에 `aria-hidden` 영향을 주므로(test-ledger), 폼 부품의 테스트 변경과 섞이지 않게 커밋을 가른다.

## Complexity Tracking

> 헌법 위반은 없다. 아래는 **이전 결정을 뒤집거나 사용자 결정의 문구와 다르게 가는 것**의 기록이다.

| 뒤집는·달라지는 결정 | 왜 필요한가 | 무엇으로 대체하는가 |
|---|---|---|
| 015 FR-007 「컴포넌트 라이브러리를 도입하지 않는다」 | 사용자 요청 (017) | 부품 원본 이식 + 동작 층만 표준 부품 (research R1·R2) |
| **(09-16)** 017 자신의 R2 「동작 층은 `radix-ui`」 | shadcn 기본 갈래가 2026-07 부터 Base UI 다. 017 조사에 검토 자체가 없었다 | Base UI 로 교체 (research R2 개정) |
| **(09-16)** 017 N-02 판정 「의도된 예외 — 사용자 확인」 | 사용자가 자리를 옮기라고 결정했다. 브라우저 확인에서 알림 셋이 Step 01·02 행을 가리는 것을 봤다 | 알림 부품 교체 + 자리 이동 + 되풀이 제거 (research R6 개정 · layout-contract-v3 L2 개정) |
| **(09-16)** 017 ui-parts 「툴팁마다 공급자」 | 공식 부품이 뿌리에 하나를 둔다 | 뿌리 공급자 하나 |
| 015 T075 이후 정본 클래스 규칙이 앱에 실리지 않는데 09-11 수정이 그 규칙에만 들어갔다 | B-01 이 되살아났다 | 알림 자리를 부품 한 곳에서 띠 조건으로 (layout-contract-v3 L2). 정본의 `.toast-layer` 는 기록으로 남는다 |
| 2026-09-10 사용자 결정 「알림을 토스트 한 자리로」 중 **진행 중 세션 토스트** | 흐름 안 띠와 같은 사실을 되풀이하며 띠의 조작을 덮는다 (B-02). 반대로 토스트로 모으면 닫히지 않는 토스트가 목록 도구 줄을 덮는다 | 흐름 안 `ActiveSessionsBanner` 가 말한다 (research R6 ⑤). **사용자가 반대를 원하면 되돌린다** |
| 사용자 결정 1 문구 「shadcn 의미 토큰은 정본에 `var()` 별칭으로」 | 별칭을 테마에 등록하면 G-B 가 shadcn 원본 클래스를 못 잡는다 | 이식 대응표로만 둔다 (research R3 · ui-parts §2). **요지(모습은 정본)는 더 강하게 지켜진다.** 사용자가 문구대로 원하면 되돌리기 쉽다 |
| spec SC-011 JS 상한 +25% | 측정 전에 정한 값이었다. FR-011·FR-012 를 성립시키는 세 부품만으로 +23% | +30% (research R12). 요구사항이 필요로 하지 않는 17.6 kB 를 먼저 뺐다 |
| 007 DC-011 「좁은 창에서 스크롤한다」의 적용 범위 | 머리띠가 스크롤에 함께 밀려 나갔다 (B-11) | 스크롤은 **본문만** — 원칙은 유지, 머리띠를 밖으로 (v3 L3) |
| `StepList.tsx:470` `max-h-[52%]` (배치 표 밖 리터럴) | Step 목록을 6.6행으로 누른다 (B-03) · LC-1 위반 | 국면별 배치 표 (v3 L4) |

**되돌리는 비용**: 단계마다 커밋이므로 단계 단위로 되돌릴 수 있다. 2단계(알림)와 4단계(배치)는 3단계(부품)와
독립이다.

## 위험과 대응

| # | 위험 | 징후 | 대응 |
|---|---|---|---|
| RK-1 | 모달의 `aria-hidden`·`pointer-events` 가 테스트를 대량으로 깨뜨린다 | 3단계 대화상자 커밋에서 실패 폭증 | 대화상자 전환을 화면 하나씩. test-ledger 의 「순서만 바꾼다」 형태로 고친다 |
| RK-2 | 원본 이식 중 shadcn 모습이 섞인다 | L2 불일치 · 캡처에서 둥근 모서리 | 이름공간 비우기(R4)가 G-B 로 먼저 막고 G-F 가 정적 유틸리티를 막는다. 이식 대응표 밖의 클래스는 표에 줄을 더한 뒤 옮긴다 |
| RK-3 | 원시 요소 전환이 조용히 행동을 바꾼다 (Enter 제출·전파·자동 초점) | 화면 테스트 통과, 사람이 쓰면 다름 | 부품은 사건을 삼키지 않는다(ui-parts §3). 인라인 이름 고치기·IME·파일 입력은 자리별 테스트가 이미 있다 — 판정 방법을 바꾸지 않는다 |
| RK-4 | 동작 층이 미러 입력과 다툰다 | 한글 조합이 끊김 · 대화상자 중 대상 앱에 입력 | Step 상세는 비모달(R7) · `MirrorInputWithDialog` 테스트 · quickstart H-2 |
| RK-8 **(09-16)** | 알림 자리를 옮겼더니 다른 것을 덮는다 | 순회에 새 검출 | 후보 둘(오른쪽 아래 · 아래 가운데)을 스파이크에서 **미리 잰다**. 판정은 순회가 한다 |
| RK-9 **(09-16)** | 되풀이 알림을 지웠더니 「말하지 않는 화면」이 된다 | 국면이 바뀌었는데 아무 표시도 없다 | 지우기 전에 화면이 그 사실을 말하는지 확인한다(R6 개정 표) · 사람 판정 |
| RK-5 | 번들 상한 초과 | §4 에서 181.3 kB 초과 | 들이지 않기로 한 것이 들어왔는지 먼저 본다(`npm ls`). 그다음 Tooltip 을 부품 층에서 뺄지 사용자에게 묻는다 |
| RK-6 | 순회가 오탐으로 시끄러워 무시된다 | 허용 등록부가 사유 없이 늘어난다 | 등록은 사유 필수(SW-7). 전환 전 오탐에서 판정 규칙을 이미 고쳤다(SW-6) |
| RK-7 | `:has()` 가 jsdom 에서 계산되지 않아 알림 자리가 테스트로 증명되지 않는다 | jsdom 은 클래스만 본다 | 클래스 형태(서로 배제)는 테스트가, 실제 자리는 순회(chromium)가 본다 — 015 LC-4 의 겹 나누기와 같다 |

## Phase 1 재확인 — Constitution Check

설계 산출물(`data-model.md`·`contracts/`·`quickstart.md`)을 만든 뒤 다시 본다.

| 항목 | 재확인 결과 |
|---|---|
| 원칙 I~V | 변동 없음. 설계에서 backend·Step DSL·Runner·Generator 를 건드리는 것이 하나도 나오지 않았다 |
| 원칙 II 증거 | quickstart §5 가 backend 차이 0 을 절차로 확인한다 |
| 원칙 III | 설계로 강화됐다 — Step 상세를 비모달로 둔 결정(R7)과 `MirrorInputWithDialog` 테스트가 미러 입력 경로를 지킨다 |
| Stack 조항 | 판정 유지 (개정 불필요). 설계에서 React 를 대체하는 것이 나오지 않았다. 실행 의존성은 2개로 줄었다(`tailwind-merge` 제외) |
| 보안 — 민감값 마스킹 | quickstart H-6 · `InlineSecret`·`SensitiveAcrossPhases` 판정 방법 변경 없음 예상 |
| **게이트 4** | 설계로 강화됐다 — test-ledger 가 `verifies` 칸을 먼저 적게 하고, 「고쳤다」를 순회 보고서로 정의해 기대값 변경의 근거를 테스트 밖에 둔다 |
| 게이트 3 | 가드 넓히기 2 · 새 가드 2 · 순회 보고서 테스트 · 동작 테스트 4 — 각각을 **일부러 깨서 확인하는 절차**가 quickstart §1-2 에 있다 |

**설계에서 새로 드러난 것 1건**: 가드를 넓히면(guards H-2) **지금 검사를 벗어나 있던 클래스**가 드러난다
(`ui/Table.tsx:162` 등). 그 결과 1단계에서 기존 코드가 실패할 수 있다 — 그것은 가드를 좁혀 피하지 않고 고칠
대상이며, 1단계 작업에 포함한다.

**Phase 1 재확인 결과: 통과.** 위반 0건.
