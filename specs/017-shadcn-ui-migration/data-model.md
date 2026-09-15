# Data Model: shadcn/ui 부품 체계 전환

**Feature**: 017 | **Date**: 2026-09-15 | **Phase**: 1

이 기능은 사용자 데이터를 다루지 않는다. 저장소·스키마·마이그레이션이 없다. 여기서 「모델」은
**전환을 성립시키는 개념과 그 사이의 규칙**이다 (015 data-model 과 같은 성격).

---

## 개념 지도

```
확정 디자인 (docs/design/008-visual-language/*.dc.html)
        │ extract_canon.py · 손대지 않는다
        ▼
   정본 토큰 ─────────────────────────────┐  값은 여기에만
   theme/tokens.css → tokens.app.css       │
        │ @theme inline (참조만)             │
        ▼                                  │
   테마 이름공간  ◄── 비운 것: color · radius · shadow · text · animate (R4)
   theme/tailwind.css                      │
        │                                  │
        │         shadcn 원본 (레지스트리)    │
        │               │ 이식 대응표 (ui-parts §2)
        ▼               ▼                  │
   부품 (src/ui/*) ── 동작 층: Radix | 네이티브 | 원시
        │  변종 표 (cva)  ◄── G-E · G-F      │
        │                                  │
        ▼                                  │
   화면 (src/pages · src/components)  ◄── G-G 원시 요소 예산
        ▲                  │
        │ 배치를 내려받는다   │ 층위 (layout-contract-v3 §L)
   배치 표 (lib/layout.ts)  │
   화면 정책 (Artboard)     ▼
                     실제 화면 ──► 화면 순회 ──► 깨짐 기록 · 순회 보고서
                           └────► L2 대조 ──► 의도된 차이
```

---

## 1. 정본 토큰 (Canon Token)

015 와 같다. `theme/tokens.css` 의 `:root` 가 유일한 값의 출처이며 이 기능은 **값을 하나도 바꾸지
않는다** (FR-009). 앱이 싣는 것은 `split-canon.mjs` 가 뽑은 `tokens.app.css`(변수와 요소 규칙)다.

**규칙**: 정본 파일의 정본 구획 변경 0줄 (SC-012). 정본의 **클래스 규칙**(`.toast-layer` 등)은 앱에
실리지 않는다 — 그 규칙만 고치면 화면에 닿지 않는다 (B-01 의 원인, research R6).

## 2. 테마 이름공간 (Theme Namespace)

`theme/tailwind.css` 의 `@theme inline` 이 여는 이름.

| 이름공간 | 상태 | 남는 이름 |
|---|---|---|
| `--color-*` | 비움 (015) | 정본 색 + `transparent`·`current`·`inherit` |
| `--radius-*` | **비움 (017)** | `base`·`chip`·`lg` |
| `--shadow-*` · `--inset-shadow-*` · `--drop-shadow-*` | **비움 (017)** | `e1`·`e2` |
| `--text-*` | **비움 (017)** | 없음 — 글자 크기는 임의값 |
| `--animate-*` | **비움 (017)** | 없음 |
| `--spacing-*` | 유지 (015 판단) | 기본 배수 + 정본 치수(`control`·`step`·`steps`…) |
| `--font-weight-*` | 유지 | 정본과 같은 값 |

**규칙**: 오른쪽 값은 전부 `var(정본)` 또는 키워드 (`TailwindThemeLiteral`). shadcn 의미 토큰
(`--primary` 등)을 등록하지 않는다 (research R3).

## 3. 부품 (UI Part)

`src/ui/*.tsx`. 도메인을 모른다.

| 속성 | 뜻 |
|---|---|
| `kind` | 버튼 · 칩 · 입력 · 선택 · 체크박스 · 라디오 · 라벨 · 대화상자 · 메뉴 · 탭 · 분절 선택 · 툴팁 · 펼침 · 표 · 알림 · 면 |
| `behavior` | `radix` (구조·동작을 `radix-ui` 에서) · `native` (네이티브 요소의 동작) · `raw` (동작 없음) |
| `source` | shadcn 레지스트리 항목과 버전 (`new-york-v4/button @ shadcn 4.21.0`) 또는 `015` (기존 부품 계승) |
| `variants` | 변종 표 — §4 |
| `slots` | `data-slot` 이름 (shadcn 관례). 순회·테스트가 부품을 집는 통로 |
| `hooks` | 부품이 내보내는 `data-*` 의도 속성 (`data-variant`·`data-tone`·`data-size`…) — 테스트가 붙잡는다 (FR-005) |

**규칙**:

- 종류마다 부품 정의는 **하나** (FR-003 · SC-006). 옛 부품을 남긴 채 새 부품을 두지 않는다.
- 부품은 `className` 을 받지 않는다. **`layout` 은 배치만** (015 규율 · research R5).
- `behavior` 가 `radix` 인 부품만 포털·초점 관리를 갖는다. 목록은 [ui-parts.md](contracts/ui-parts.md) §1.

## 4. 변종 표 (Variant Table)

부품 파일 안의 `cva(base, { variants, compoundVariants, defaultVariants })`.

**규칙**:

- 변종이 건드리는 속성은 `base` 가 갖지 않는다 (015 `ui/Button` 머리주석의 규율).
- 한 조합 안에 같은 속성이 둘이면 **나중에 적은 쪽이 산출 CSS 에서도 이긴다** — 아니면 G-E 실패.
- 변종 표는 부품 `.tsx` 안에 있다. `.ts` 에만 있는 클래스는 G-B 조회가 못 보므로 실패한다.
- 값 이름은 정본 유틸리티뿐 — 이식 대응표(§5)를 거친다.

## 5. 이식 대응 (Skin Map Entry)

shadcn 원본의 클래스 하나가 정본에서 무엇이 되는가. [ui-parts.md](contracts/ui-parts.md) §2 가 표다.

| 필드 | 예 |
|---|---|
| `shadcn` | `bg-primary text-primary-foreground` |
| `canon` | `bg-ink text-panel` |
| `rule` | 교체 · 삭제(전역 규칙에 맡김) · 형태 교체(흐림 → 점선) |

**규칙**: 대응이 「삭제」인 항목은 **무엇이 대신하는지**를 적는다 (예: 초점 링 → 전역 `:focus-visible`).

## 6. 원시 요소 예외 (Raw Element Exception)

`src/ui/` 밖에서 부품이 아닌 `<button|input|select|textarea>` 를 쓰는 자리.

| 필드 | 뜻 |
|---|---|
| `file` · `pattern` | 자리 |
| `axis` | `raw-element` (`theme/exceptions.ts` 의 새 축) |
| `reason` | **왜 부품이 될 수 없는가.** 빈 문자열은 등록이 아니다 |

**알려진 후보**: 미러의 IME 조합 칸(`MirrorView.tsx:406` — 보이지 않고 포인터를 받지 않으며 조합만
받는다. 이미 `class-name` 축에 등록됨). 그 밖의 후보(국면 이름 입력·파일 입력·전파를 멈추는 체크박스)는
부품의 변종으로 흡수한다 — [ui-parts.md](contracts/ui-parts.md) §3.

**수명**: 전환 중에는 G-G 가 **줄어드는 예산**을 센다. 완료 조건은 예산 = 등록된 예외 수.

```
원시 요소 N개 ──(화면 하나 전환)──► 예산 N−k ──► … ──► 예산 = 예외 수
                                 ▲
                   예산이 늘면 즉시 실패 (새 원시 요소가 들어왔다)
```

## 7. 층 (Layer)

화면에 겹쳐 뜨는 것의 z 순서. [layout-contract-v3.md](contracts/layout-contract-v3.md) §L1.

| z | 층 | 자리 |
|---|---|---|
| 10 | 따라오는 확정 띠 | 흐름 안 `sticky` |
| 20 | Step 상세 가림막 · 판 | `Workbench` 안 |
| 30 | 대화상자 가림막 · 내용 | 포털 (`body`) |
| 40 | 메뉴 내용 | 포털 |
| 50 | 툴팁 | 포털 |
| 60 | 알림 층 | 포털 (`body`) |

**규칙**: z 값은 이 표에서만 온다. 알림 층은 모달이 열려도 읽히고 눌린다 (research R6 ③④).

## 8. 화면 정책 (Page Policy)

| 필드 | 값 |
|---|---|
| `policy` | `data` (창 폭을 채운다) · `form` (읽기 폭으로 가운데) |
| `baseWidth` | `data` 1440 · `form` 960 또는 720 |
| `header` | 가로 스크롤 영역 **밖** |

화면별 배정은 [layout-contract-v3.md](contracts/layout-contract-v3.md) §L3.

## 9. 깨짐 기록 (Breakage Record)

| 필드 | 뜻 |
|---|---|
| `id` | `B-01`… (전환 전 실측) · `N-01`… (전환 중 발견) |
| `screen` · `viewport` | 순회 화면 이름 · 뷰포트 |
| `kind` | 덮임 · 넘침 · 잘림 · 줄바꿈 · 창 밖 · 콘솔 · 정책 |
| `element` | 요소 설명 (`button[data-variant]{Step 05부터 실행}`) |
| `cause` | 원인 자리 (`파일:줄`) |
| `verdict` | `fixed` · `allowed` |
| `reason` | `allowed` 면 필수 |

**상태 전이**:

```
검출 ──► 원인 확인 ──► fixed   (다음 순회에서 사라짐을 확인해야 fixed 다)
                 └──► allowed (순회 허용 등록부에 사유와 함께)
```

「고쳤다」는 **다음 순회 보고서에서 그 검출이 사라진 것**이다. 코드를 고친 커밋만으로는 `fixed` 가 아니다.

## 10. 순회 시나리오와 보고서 (Sweep Scenario · Sweep Report)

[screen-sweep.md](contracts/screen-sweep.md) 가 계약이다. 보고서(`frontend/tests/sweep-report.json`)는
`digest`·`screens × viewports`·`allowed[]`·`findings[]` 를 담고, 테스트가 낡음과 0건을 판정한다.

## 11. 의도된 차이 (Intended Difference)

L2 대조의 `INTENDED` 항목 (015 계승). 017 에서 생기는 종류:

| 종류 | 예 |
|---|---|
| 깨짐 수정 | 알림 층 `top` · Step 패널 바닥 상한 · 만들기 미러 자리 높이 |
| 구조 변경 | `NativeSelect` 감싸개 `div` · 머리띠가 스크롤 영역 밖으로 · 원시 `<table>` → 표 부품 |
| 넓은 창 정책 | 목록·가져오기가 창 폭을 채운다 |

**규칙**: `reason` 필수. 순회가 「깨짐 없음」을, L2 가 「그 밖은 같음」을 함께 증명한다.

## 12. 테스트 변경 기록 (Test Ledger Entry)

헌법 Quality Gate 4 의 기록. [test-ledger.md](contracts/test-ledger.md).

| 필드 | 뜻 |
|---|---|
| `file` | 테스트 파일 |
| `verifies` | **무엇을 검증하던 테스트인가** — 바뀌면 안 되는 것 |
| `change` | 판정 방법의 변경 |
| `why` | 부품 층의 어떤 사실이 변경을 강제하는가 |
| `assertions` | 전·후 단언 수 — 줄면 사유 |
