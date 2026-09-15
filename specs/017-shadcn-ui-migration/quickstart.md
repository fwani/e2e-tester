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

**기대**: CSS gzip ≤ **6.78 kB** · JS gzip ≤ **181.3 kB**. 넘으면 원인을 찾는다 — 들이지 않기로 한 의존성
(`tailwind-merge`·`lucide-react`·`tw-animate-css`·Radix `Select`·`Checkbox`)이 들어왔는지 먼저 본다.

```bash
npm ls tailwind-merge lucide-react tw-animate-css sonner 2>&1 | grep -v "empty" || true
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
