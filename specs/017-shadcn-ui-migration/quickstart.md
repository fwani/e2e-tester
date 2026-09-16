# Quickstart: shadcn/ui 전환 검증

**Feature**: 017 | **Date**: 2026-09-15 | **Phase**: 1

전환이 끝났는지, 그리고 **끝났다는 말이 사실인지**를 확인하는 절차다. §1~§5 는 기계가 판정하고
§H 는 사람이 판정한다. 기준 수치는 [baseline.md](baseline.md) 에 있다.

---

## 0. 사전 준비

```bash
cd frontend && npm install
cd ../backend && uv sync && uv run playwright install chromium
```

화면 순회와 L2 는 backend 가상환경의 Playwright 를 쓴다. 새 테스트 의존성은 없다.

---

## 1. 기계 판정 — 테스트와 가드

### 1-1. 전량 통과와 단언 수 (SC-008 · 헌법 Gate 4)

```bash
cd frontend
npx tsc --noEmit
npx vitest run
node scripts/count-assertions.mjs
```

**기대**: 타입 검사 통과 · 전량 통과(기준 1364 이상) · 건너뜀 0 · 단언 **2148 이상** · 무른 단언이
639 보다 늘었다면 [test-ledger.md](contracts/test-ledger.md) 에 사유가 있다.

### 1-2. 가드가 실제로 잡는가 (SC-010)

한 번에 하나씩 넣고, 실패를 확인하고, **되돌린다.**

| 넣는 것 | 넣는 곳 | 실패해야 하는 가드 |
|---|---|---|
| `rounded-md` | `ui/Button.tsx` 변종 하나 | G-B `ClassExistence` |
| `shadow-xs` | 같음 | G-B |
| `disabled:opacity-50` | `ui/Input.tsx` | G-F `UiSkin` |
| `focus-visible:ring-[3px]` | `ui/Button.tsx` | G-F |
| `import { XIcon } from "lucide-react"` | `ui/Dialog.tsx` | G-F |
| 뒤에 적었는데 CSS 에서 지는 쌍 (`bg-ink` 뒤 `bg-panel` 이 아니라 반대 순서가 되도록) | `ui/Button.tsx` `cva` | G-E `ClassConflict` |
| `<button className="h-control">x</button>` | `pages/TestList.tsx` | G-G `RawElements` |
| `outline-hidden` | 아무 화면 | `FocusRing` |

```bash
npx vitest run tests/ClassExistence.test.ts tests/UiSkin.test.ts tests/ClassConflict.test.ts \
  tests/RawElements.test.ts tests/FocusRing.test.tsx
```

**실행 기록 (2026-09-15 · T079)** — 한 번에 하나씩 넣고 해당 가드 파일만 돌린 뒤 되돌렸다(파일 해시가 넣기 전과 같음을 확인).

| 넣은 것 | 넣은 곳 | 가드 | 결과 | 실패 메시지 첫 줄 |
|---|---|---|---|---|
| `rounded-md` | `src/ui/Button.tsx` | G-B ClassExistence | **실패 — 잡았다** | → 이 클래스는 아무 CSS 도 만들지 않는다. 화면은 스타일 없이 렌더된다. |
| `shadow-xs` | `src/ui/Button.tsx` | G-B ClassExistence | **실패 — 잡았다** | → 이 클래스는 아무 CSS 도 만들지 않는다. 화면은 스타일 없이 렌더된다. |
| `disabled:opacity-50` | `src/ui/Input.tsx` | G-F UiSkin | **실패 — 잡았다** | → shadcn 원본의 기본 모습이 부품에 남아 있다. 이 클래스들은 테마와 무관하게 생성되므로 G-B 를 |
| `focus-visible:ring-[3px]` | `src/ui/Button.tsx` | G-F UiSkin | **실패 — 잡았다** | → shadcn 원본의 기본 모습이 부품에 남아 있다. 이 클래스들은 테마와 무관하게 생성되므로 G-B 를 |
| `import { XIcon } from "lucide-react"` | `src/ui/Dialog.tsx` | G-F UiSkin | **실패 — 잡았다** | →   src/ui/Dialog.tsx — 아이콘 묶음을 들이지 않는다 — 글자 기호를 쓴다 (FR-010): expected [ Array(1) ] to deeply equal [] |
| `뒤에 적었는데 CSS 에서 지는 쌍 — bg-ink 뒤 bg-panel` | `src/ui/Button.tsx` | G-E ClassConflict | 통과 — 아래 설명 |  |
| `뒤에 적었는데 CSS 에서 지는 쌍 — bg-panel 뒤 bg-ink` | `src/ui/Button.tsx` | G-E ClassConflict | **실패 — 잡았다** | → 한 요소에 같은 속성을 선언하는 유틸리티가 둘 이상 붙어 있다. |
| `<button className="h-control">x</button>` | `src/pages/TestList.tsx` | G-G RawElements | **실패 — 잡았다** | → 원시 조작 요소가 예산보다 1개 많다 — 새로 들어온 자리를 부품으로 바꾼다. |
| `outline-hidden` | `src/pages/TestList.tsx` | FocusRing | **실패 — 잡았다** | → 초점 링을 지우고 있다. 마우스로 쓰면 아무 차이가 없고 스크린샷도 같지만, |

충돌 쌍은 **두 순서를 다 넣었다.** G-E 가 묻는 것은 「나중에 적은 클래스가 산출 CSS 에서 **지는가**」다. `bg-ink bg-panel` 은 나중에 적은 `bg-panel` 이 CSS 에서도 이겨 적은 대로 그려지므로 통과하고, 반대 순서 `bg-panel bg-ink` 는 나중에 적은 `bg-ink` 가 져서 실패한다 — 015 의 흰 버튼(적은 것과 그려진 것이 다름)이 이 가드가 막는 형태다. 한 요소에 같은 속성이 둘 붙는 것 자체는 부품 표의 설계(바탕·변종이 같은 속성을 갖지 않는다 — `ui/Button` 머리주석)가 막는다.

### 1-3. 옛 부품이 남지 않았다 (SC-006)

```bash
npx vitest run tests/ImplementationCount.test.ts tests/RawElements.test.ts
grep -rn "ui/Modal\|OverlayPane\b\|navLinkClasses\|filter(Boolean).join" src || echo "없음"
```

**기대**: `RETIRED` 전부 참조 0 · 원시 요소 예산 = 등록된 예외 수 · grep 결과 없음.

### 1-4. 정본 무변경 (SC-012)

```bash
git diff 75520ee -- src/theme/tokens.css | head
backend/.venv/bin/python ../scripts/design_render.py --compare
```

**기대**: `tokens.css` 차이 없음 · L1 불일치 0.

---

## 2. 화면 깨짐 순회 (SC-001~SC-004 · FR-025)

```bash
# 저장소 루트에서
backend/.venv/bin/python scripts/screen_sweep.py
cd frontend && npx vitest run tests/ScreenSweep.test.ts
```

[screen-sweep.md](contracts/screen-sweep.md) 가 절차다. 격리 인스턴스를 띄우고, 실제 재실행으로 결과를
만들고, 개발 서버로 화면 × 폭 4종을 연다.

**기대**:

| 확인 | 기준 |
|---|---|
| 종료 코드 | 0 |
| 허용되지 않은 검출 | 0 |
| 순회한 화면 × 폭 | SW-5 × SW-4 전부 |
| `runner-record` | **실시간 연결됨** 상태로 잰 것 |
| B-01~B-11 | 전부 사라졌거나 허용 등록부에 사유와 함께 |

**B-01~B-11 각각을 다시 본다** — 순회 보고서의 검출 목록에서 baseline.md 표의 요소가 사라졌는지.

| # | 보고서에서 사라져야 하는 것 |
|---|---|
| B-01 | `result-fail` 의 `처음부터 실행`·`Step 05부터 실행` 덮임 · `runner-disconnected` 의 `빠름`…`저장` 덮임 |
| B-02 | `test-list-session` 의 세션 띠 조작 덮임 |
| B-03 | (캡처) `edit@1440` Step 목록 8행 이상 — 보고서의 `stepRowsVisible` |
| B-04 | `test-create` 빈 미러 자리의 넘침 |
| B-05 · B-06 | `test-create` Step 패널 머리 줄바꿈 · 자연어 입력칸 폭 ≥ 240 |
| B-07 · B-08 | `test-list-selected` 줄바꿈 · 선택칸 폭 · 체크박스 크기 일치 |
| B-09 | (캡처) 초안 표 머리·본문 열 정렬 |
| B-10 | `@1920`·`@2560` 에서 `data` 화면이 창 폭을 채운다 — 보고서의 `contentWidth` |
| B-11 | `test-list-bulk-confirm@1280` 창 밖 0 |

---

## 3. 전환 전후 대조 — L2 (SC-007 · FR-027)

```bash
backend/.venv/bin/python scripts/design_compare_ba.py --compare
cd frontend && npx vitest run tests/BeforeAfterParity.test.ts
```

**기대**: 등록되지 않은 불일치 0. `INTENDED` 의 항목마다 사유가 있고, 사유가 가리키는 깨짐 수정(B-xx)이나
구조 변경이 [data-model.md](data-model.md) §11 의 종류에 든다.

**순회와 L2 는 함께 본다.** 순회는 「깨지지 않았다」, L2 는 「그 밖은 같다」다. 한쪽만 초록이면 끝이 아니다.

---

## 4. 번들 (SC-011)

```bash
cd frontend && npx vite build 2>&1 | grep -E "index-.*\.(css|js)"
```

**기대**: CSS gzip ≤ **6.78 kB** · JS gzip ≤ **181.3 kB**.
*2026-09-16 개정 — 갈래 교체 뒤에는 **JS gzip ≤ 177.41 kB**(Radix 로 구현한 실측)를 함께 본다. 기반
교체는 추가가 아니므로 늘지 않아야 한다 (research R12 개정).*
넘으면 원인을 찾는다 — 들이지 않기로 한 의존성(`tailwind-merge`·`lucide-react`·`tw-animate-css`·
`sonner`·Geist 글꼴)이 들어왔는지, 옛 갈래(`radix-ui`)가 남았는지 먼저 본다.

```bash
npm ls tailwind-merge lucide-react tw-animate-css sonner radix-ui 2>&1 | grep -v "empty" || true
npm ls @base-ui/react                      # 09-16 — 이것만 있어야 한다
grep -rn "radix" src tests | grep -vi "개정\|이력\|09-16" | head   # 0 이어야 한다
```

---

## 5. 원칙 II 증거 (헌법 Gate 1)

```bash
git diff --stat 75520ee -- backend/ | tail -1
```

**기대**: backend 변경 0.

---

## H. 사람 판정

기계가 보지 못하는 것이다. `docs/PENDING-HUMAN-VERIFICATION.md` §17 에 등록하고 판정 칸을 채운다.

| # | 무엇을 | 어떻게 | 기준 |
|---|---|---|---|
| H-1 | **키보드만으로 전체 순회** | 목록 → 행 메뉴 → 편집 → Step 상세 → 저장 확인 → 결과 → 다시 실행 확인. 마우스를 쓰지 않는다 | 초점이 보이지 않는 순간 0 · 대화상자에서 초점이 밖으로 새지 않는다 · 닫으면 연 자리로 돌아온다 (SC-009) |
| H-2 | **한글 입력과 대화상자** | 녹화 중 미러에 한글을 조합 입력 → 저장 확인 대화상자를 열고 닫기 → 다시 조합 입력 | 대화상자가 열린 동안 대상 앱에 입력 0 · 닫은 뒤 조합이 끊기지 않는다 (SC-013) |
| H-3 | **hover · 비활성** | 버튼 변종 전부, 메뉴 항목, 탭, 분절 선택에 마우스를 올린다. 비활성 조작에 올려 사유 `title` 을 본다 | 정본 hover 바탕 · 비활성은 점선이며 사유가 뜬다 |
| H-4 | **정본 모습** | 전환 전 캡처(`baseline-shots/`)와 같은 화면을 나란히 본다 | 모서리·색·그림자·글꼴에서 shadcn 기본 모습의 흔적 없음 |
| H-5 | **넓은 창** | 1920·2560 에서 목록·가져오기·작업 화면·프로젝트·비밀 값을 오간다 | 데이터 화면은 채우고 폼 화면은 가운데 — 오른쪽이 비는 화면 0 |
| H-6 | **민감값 마스킹** | 비밀 값·키 관리·민감 입력 칸 | 전환 전과 같이 가려진다 (헌법 보안 요건) |
| H-7 | **순회가 닿지 못한 화면** | 가져오기 미리보기(엑셀 파일) · 일시정지 · AI 작성 · 사람 인수 | 1280·1440 에서 덮임·넘침·줄바꿈을 눈으로 본다 |
| H-8 | **모달이 열린 동안의 알림** | 녹화 중 저장 확인을 연 채 연결을 끊는다 | 알림이 보이고 「닫기」를 누르면 대화상자가 닫히지 않는다 |
| H-9 **(09-16)** | **알림이 가리지 않는다** | 녹화 → 조작 몇 개 → 「중지」. 검토 국면에서 알림이 떠 있는 동안 Step 목록의 행과 패널 바닥 조작을 눌러 본다 | 가려서 못 누르는 조작 0 · 알림은 5초 뒤 사라지고 포인터를 올리면 멈춘다 (N-02 닫힘) |
| H-10 **(09-16)** | **되풀이가 사라졌다 · 고르기 낭독** | 같은 절차에서 뜨는 알림을 센다. 실행 속도·거르기를 화면 낭독기로 듣는다 | 국면 전환·세션 종료 알림이 뜨지 않는다(저장 안 됨만) · 고른 항목이 무엇인지 들린다 (라디오 → 눌림으로 바뀐 것을 확인) |

---

## 실행 기록

### 2026-09-15 · 017 마감 (T085)

| § | 확인 | 결과 |
|---|---|---|
| 1-1 | 타입 검사 · 테스트 · 단언 수 | `tsc` 통과 · **1417 / 1417 통과** (파일 118) · 단언 **2274** (기준선 2148 · +126) · 무른 단언 **639** (기준선과 같다) · 건너뜀 0 |
| 1-2 | 가드가 실제로 잡는가 | 8가지 전부 해당 가드가 실패 (위 §1-2 실행 기록 · T079) |
| 1-3 | 옛 부품이 남지 않았다 | `ImplementationCount`·`RawElements` 통과 · 원시 조작 요소 예산 0 (등록된 예외는 미러 한글 조합 칸 1) · grep 은 주석 속 이력과 계약이 정한 파일 이름 `ui/OverlayPane` 뿐 |
| 1-4 | 정본 무변경 | `git diff 75520ee -- src/theme/tokens.css` 0줄 · L1 대조 725칸 불일치 0 |
| 2 | 화면 깨짐 순회 | 18화면 × 4폭 = 72회 · **알려진 깨짐 0 · 등록되지 않은 검출 0** · 닿지 못함 0 · 허용 28(사유 있음) · `edit@1440` Step 목록 8행 |
| 3 | L2 대조 | 8화면 × 56속성 · **등록되지 않은 차이 0** · 의도된 차이 182건 전부 사유 있음 (정본 기준 폭 1440 에서 잰다) |
| 4 | 번들 | CSS gzip **6.69 kB** (≤ 6.78) · JS gzip **177.41 kB** (≤ 181.3) · `tailwind-merge`·`lucide-react`·`tw-animate-css`·`sonner` 없음 |
| 5 | 원칙 II | `git diff 75520ee -- backend/` **0줄** |
| H | 사람 판정 | 미실행 — `docs/PENDING-HUMAN-VERIFICATION.md` §17 에 기록 칸과 사용자 확인이 필요한 판단 여섯을 두었다 |

순회 도중 한 번 **메모리 부족으로 작업이 멈췄다** (다른 프로그램이 함께 떠 있던 기계). 멈춘 회차는 버리고 순회를 단독으로 다시
돌렸다 — 위 수치는 그 회차의 것이다.

### 2026-09-15 · converge 뒤 (T087~T089)

| § | 확인 | 결과 |
|---|---|---|
| 1-1 | 타입 검사 · 테스트 · 단언 수 | `tsc` 통과 · **1417 / 1417 통과** (파일 118) · 단언 **2274** · 무른 단언 **639** · 건너뜀 0 — T085 와 같다 |
| 2 | 화면 깨짐 순회 | 72회 · **알려진 깨짐 0 · 등록되지 않은 검출 0** · 닿지 못함 0 · 허용 28(사유 있음) |
| 3 | L2 대조 | **등록되지 않은 차이 0** · 의도된 차이 182건 — T085 와 같다 |

T088 의 `data-slot` 은 모양을 바꾸지 않는다 — 그 값을 고르는 CSS·클래스·스크립트가 없다(grep 0). 그래도 두 보고서는
소스 요약값으로 낡음을 판정하므로(`보고서가 낡지 않았다` 두 건이 실패했다) 다시 쟀다. 이번에도 L2 뒤 순회 도중 메모리
부족으로 멈춰, L2 결과(그 회차에서 끝났다)는 쓰고 순회만 단독으로 다시 돌렸다.

### 2026-09-15 · 브라우저 확인 뒤 (T090~T093)

| § | 확인 | 결과 |
|---|---|---|
| 1-1 | 타입 검사 · 테스트 · 단언 수 | `tsc` 통과 · **1418 / 1418 통과** (파일 118) · 단언 **2275** (+1 · N-08) · 무른 단언 **639** · 건너뜀 0 |
| 2 | 화면 깨짐 순회 | 72회 · **알려진 깨짐 0 · 등록되지 않은 검출 0** · 닿지 못함 0 · 허용 28(사유 있음) |
| 3 | L2 대조 | **등록되지 않은 차이 0** · 의도된 차이 182건 — 앞 회차와 같다 |
| H | 사람 판정 | H-1·H-3·H-5·H-7 통과 · H-4·H-6 부분 · H-2(실제 한글 입력기) · H-8(연결 끊기) 은 사람이 남는다 — `docs/PENDING-HUMAN-VERIFICATION.md` §17 |

브라우저 확인은 순회와 같은 시드로 격리 인스턴스를 띄워 했다(`.sweep/data` · 사용자 프로젝트를 읽지도 쓰지도 않음). 거기서 찾은
N-08(017 회귀)·N-09(전환 전부터)를 고쳤다. 두 수정 모두 순회·L2 가 재는 화면 밖이라 두 보고서의 수치는 바뀌지 않았다.

### 2026-09-16 · 알림을 Base UI Toast 로 · 자리를 재서 정했다 (T094~T103)

| § | 확인 | 결과 |
|---|---|---|
| 1-1 | 타입 검사 · 테스트 · 단언 수 | `tsc` 통과 · **1417 / 1417 통과** (파일 118) · 단언 **2274** (앞 회차 2275 · −1) · 무른 단언 **639**(기준선과 같다) · 건너뜀 0 |
| 2 | 화면 깨짐 순회 | **19화면 × 4폭 = 76회** · **등록되지 않은 검출 0** · 닿지 못함 0 · 허용 28(사유 있음) · **`edit-notice` 네 폭 모두 검출 0 — N-02 가 닫혔다** |
| 3 | L2 대조 | 8화면 × 56속성 · **대조 34272칸** · 등록되지 않은 차이 0 · 의도된 차이 **188** |
| 1-4 | 정본 무변경 | `git diff 75520ee -- src/theme/tokens.css` **0줄** |
| 4 | 번들 | **이 회차에서는 판정하지 않는다** — `radix-ui` 와 `@base-ui/react` 가 아직 함께 들어 있어(T107 이 지운다) JS gzip 이 **189.40 kB** 다. 예산(≤ 177.41 kB)은 갈래 교체가 끝난 **T108** 에서 잰다 |
| 5 | 원칙 II | `git diff 75520ee -- backend/` **0줄** |
| H | 사람 판정 | H-9·H-10 미실행 — 알림 쌓임과 되풀이는 사람이 본다 |

**단언이 하나 준 자리**: `ToastDismiss` 의 「날아가는 동안은 아직 살아 있다」. 손으로 만든 180ms(`FLY_MS`)를
재던 단언이라 부품에는 그 상태가 없다 (test-ledger 09-16 · 기준 2148 은 그대로 넘는다).

**무른 단언이 한 번 640 이 됐다가 639 로 돌아왔다.** 새 자리 검사에 `not.toBeNull()` 을 썼는데 계수기가
잡았다 — 「`bottom-[N px]` 클래스가 **하나**인가」를 못 박는 굳은 단언으로 바꿨다. 사유를 등록하는 대신
검사를 세게 했다.

**L2 는 의도된 차이가 307 → 188 로 줄었는데 대조는 29288 → 34272 로 늘었다.** `BeforeAfterParity` 의
「대조한 칸이 줄었다」가 내 과한 등록을 잡았기 때문이다 — 층을 지우며 밀린 자리 번호 때문에 짝을 잃은
90 칸을 「의도된 차이」로 등록했었다. 등록을 지우고 짝을 되살렸다 (test-ledger 「가드가 잡은 것」 셋째 줄).
