# Quickstart — 화면 하나를 v2 로 옮기는 표준 절차

33개 파일에 **같은 절차를 반복 적용**한다. 화면마다 방식을 새로 정하면 그것이 다시 전사가 된다.

**검증 단위는 파일이 아니라 화면이다.** 한 화면에 딸린 파일을 다 옮긴 뒤 검사를 돌린다.

---

## 사전 확인 (한 번만)

```bash
cd /Users/fwani/Documents/develop/e2e-tester

# 기준선 — 초록이어야 시작할 수 있다
cd frontend && npx vitest run --reporter=basic 2>&1 | tail -3
#  Test Files  50 passed (50)
#       Tests  657 passed (657)

# 현재 위반 수 — 단계마다 내려가는지 볼 기준
cd .. && grep -roE '#[0-9A-Fa-f]{6}' --include='*.tsx' frontend/src | wc -l   # 327
```

확정 디자인은 브라우저에서 그대로 열린다 (`support.js` 404 는 무해 — research R2).

```bash
open docs/design/008-visual-language/TestList.dc.html
```

---

## 화면 하나를 옮기는 6단계

### 1. 기준을 연다

```bash
open docs/design/008-visual-language/<Screen>.dc.html
```

디자인이 그 화면에서 **무엇을 쓰는지** 먼저 읽는다. 값을 읽는 게 아니라 **형태**를 읽는다.

```bash
# 이 화면이 쓰는 형태 목록
grep -oE 'class="[^"]+"' docs/design/008-visual-language/<Screen>.dc.html | sort | uniq -c | sort -rn
```

### 2. 대응 파일을 연다

`scripts/design_baseline.py` 의 `SCREENS` 표가 화면 → 파일 대응을 갖는다.

### 3. 인라인을 형태로 바꾼다

**규칙 하나**: 인라인 선언 뭉치가 디자인의 어떤 형태와 같은 일을 하면, 그 형태의 클래스로 바꾼다.

```tsx
// 전 — 값이 여기에 있다
<button style={{
  display: "inline-flex", alignItems: "center", gap: "7px",
  height: "32px", padding: "0 12px",
  border: "1px solid #14171C", borderRadius: "3px",
  background: "#14171C", color: "#FFFFFF",
  boxShadow: "0 1px 2px rgba(20, 23, 28, 0.07)",
  font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
}}>결과 보기</button>

// 후 — 값은 정본에 있다
<button className="btn">결과 보기</button>
```

**남겨도 되는 인라인**: 배치뿐이다 (`display`·`flex`·`gap`·`width`·`padding`·`position` 등).
`contracts/visual-language.md` §2 의 허용 목록을 따른다. 치수 값은 정본 토큰이나
`lib/layout.ts` 에서 와야 하며 지어낼 수 없다.

**형태가 없으면**: 정본을 늘리지 **않는다.** 확정 디자인에 그 형태가 없다는 뜻이므로
`undefined-states.md` 에 기록하고 기존 형태의 조합으로 그린다 (FR-266·DC-009).

### 4. 잔재 색을 판정한다

이 화면에 v2 팔레트 밖 색이 있으면 **하나씩 판정한다.** 일괄 치환하지 않는다.

```bash
grep -nE '#(E4DFD1|F5D000|C9A227|E5D3AC|FFF6D9|FFF6D8|FDF8E7|EAF5EE|F0F7F2|FBEDEB|EFC7BC|B8860B|8A6A16|8A5A00|B4453C|2A303A|1F7A3D)' \
  frontend/src/<파일>
```

| 판정 | 처리 |
|---|---|
| v1 잔재 | 디자인이 같은 자리에 쓰는 v2 토큰으로 바꾼다 |
| 디자인에 대응이 있다 | 그 토큰을 쓴다 |
| 대응이 없다 | `theme/exceptions.ts` 에 **사유와 함께** 등록한다. 사유가 없으면 등록이 아니다 |

### 5. 검사를 돌린다

```bash
cd frontend && npx vitest run --reporter=basic 2>&1 | tail -5
```

**깨지면 고쳐서 통과시키지 않는다.** 먼저 판정한다.

| 왜 깨졌나 | 처리 |
|---|---|
| 검사가 인라인 `style` 을 읽는다 | 배치 계약이면 인라인을 유지한다 (research R3). 시각 언어면 검사를 v2 기준으로 **뒤집는다** — 약화가 아니라 기준 갱신이므로 커밋 본문에 적는다 |
| 검사가 문구·역할·라벨을 찾는다 | **정보를 잃은 것이다.** FR-274 위반이므로 화면을 고친다 |
| 검사가 `data-*` 를 찾는다 | 속성을 지웠다. 되돌린다 |

### 6. 대조표를 채운다

```bash
python3 scripts/design_baseline.py --write        # L1·L2 는 기계가 채운다
```

L3 3항목(가감·구조·상태)만 사람이 본다. **구현자가 자기 구현을 판정하지 않는다.**

---

## 화면 → 파일 대응

| 화면 | 파일 | 단계 |
|---|---|---|
| TestList · EmptyList | `pages/TestList.tsx` · `components/design/Chrome.tsx` · `components/Badges.tsx` | 1 (US1) |
| Create | `pages/ComposeView.tsx` | 2 (US2) |
| Record · AiWriting · AiBlocked · Takeover · Run · Paused · Finished | `pages/SessionScreen.tsx` · `components/workbench/*` 8 · `components/MirrorView.tsx` · `TabStrip` · `PacingControl` | 2 |
| Main (편집) | `pages/EditView.tsx` · `components/StepEditFields.tsx` · `AssertionForm.tsx` · `InlineSecretInput.tsx` | 2 |
| StepDetail | `components/workbench/StepDetail.tsx` · `components/LocatorPriorityTable.tsx` | 2 |
| ProjectSetup | `pages/ProjectSetup.tsx` | 3 (US3) |
| Keys · Secrets | `pages/KeyManagement.tsx` · `pages/SecretValues.tsx` | 3 |
| Result | `pages/ResultView.tsx` | 3 |
| States | `components/ErrorNotice.tsx` · `SessionLostBanner` · `LiveConnectionBanner` · `StartingIndicator` · `workbench/NoticeStack.tsx` | 3 |
| Language | `theme/tokens.css` | 0 (정본) |

---

## 완료 판정 (전체)

```bash
# SC-402 색 리터럴 0 · SC-403 팔레트 밖 0종 · SC-404 값이 두 곳에 없다
node frontend/scripts/count-violations.mjs
#   합계   0   0   0종

# 어디가 걸렸는지
node frontend/scripts/count-violations.mjs --lines

# SC-405 — 가드가 실제로 잡는지: 위반을 심어 검사가 실패하는지 본다
# SC-407 — 657건 이상 전부 통과
cd frontend && npx vitest run --reporter=basic 2>&1 | tail -3

# SC-401 — 미판정 0 · 불일치 0
grep -c '미판정\|불일치' docs/design/008-visual-language/conformance/*.md
```

> **`grep -roE '#[0-9A-Fa-f]{6}'` 를 완료 판정에 쓰지 않는다.** 그것은 **주석 안의 색까지**
> 센다. 이 기능의 결과로 코드에는 「v1 은 `#C9A227` 을 직접 정했다」처럼 **제거한 값을
> 증거로 인용하는 주석**이 남았고, 그 문장들은 화면에 나가지 않는다. 세는 규칙은
> `contracts/visual-language.md` §4 가 정하고 `count-violations.mjs` 가 그것을 구현하며,
> 가드(`tests/VisualLanguage.test.tsx`)가 같은 함수를 쓴다 — 판정과 강제가 한 규칙이다.

**SC-409(900px 에서 Step 13행)** 는 렌더로 확인한다 — `.srow` 52px × 13 = 676px 가 Step 패널
가용 높이에 들어가는지 본다.

**SC-406·SC-410** 은 L3 판정에 포함된다.
