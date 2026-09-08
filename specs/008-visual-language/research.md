# Research — 008 시각 언어 v2 적용

**날짜**: 2026-09-08 · **대상**: `specs/008-visual-language/spec.md`

이 문서의 모든 항목은 **실제로 실행해서 확인한 것**이다. 추측으로 적은 결정은 없다.
확인 명령은 각 항목에 그대로 적어 두었으므로 다시 돌려 볼 수 있다.

---

## R1 — 확정 디자인 18장의 스타일 시트는 서로 같은가

**결론: 18장이 **글자 하나까지 같은** 80줄 시트를 공유한다.** 정본을 뽑아낼 때 화면 사이
차이를 조정할 필요가 없다.

확인:

```bash
for f in docs/design/008-visual-language/*.dc.html; do
  python3 -c "
import re,hashlib,sys
m=re.search(r'<style>(.*?)</style>', open('$f').read(), re.S)
print(hashlib.md5(m.group(1).encode()).hexdigest()[:10])"
done | sort -u
# → f6420bb606  (한 줄만 나온다 = 18장 전부 동일)
```

**의미가 크다.** 계획을 세우기 전에는 "18장 사이 차이를 먼저 확인해야 한다"가 전제였다.
차이가 없으므로 **정본은 판단이 아니라 추출**이다 — 사람이 어느 값을 고를지 정하는 단계가
아예 없어진다. 그 시트가 선언하는 것은 다음 넷이다.

| 구획 | 내용 |
|---|---|
| `:root` 토큰 | 색 20 · 모서리 3 · 그림자 2 · 글꼴 2 = 27개 |
| 바탕 규칙 | `*` box-sizing · `body`(13px/1.5, tabular-nums) · `a` |
| 재사용 형태 | `.lbl` `.mono` `.pane` `.btn`(+`primary`/`danger`/`off`/`sm`) `.why` `.chip`(+`pass`/`fail`/`warn`/`run`/`ai`) |
| 껍데기·행 | `.hdr` `.phase` `.notice` `.body` `.left` `.steps` `.steps-hd` `.srow`(+`pass`/`fail`/`run`/`sel`) |

---

## R2 — 확정 디자인을 실제로 열어 볼 수 있는가 (FR-283)

**결론: 열린다. 고칠 것이 없다.** `support.js` 404 는 무해하다.

`*.dc.html` 은 `<script src="./support.js">` 를 참조하는데 저장소에 그 파일이 없다(19개 파일이
전부 참조). 명세는 이것을 "대조 절차가 성립하지 않을 수 있다"는 위험으로 적었다. 실제로
렌더해서 확인했다.

```bash
backend/.venv/bin/python <스크립트>   # playwright chromium, file:// 로 로드
```

| 측정 | TestList | Language | Main |
|---|---|---|---|
| 아트보드 실측 크기 | 1440×900 | 1440×1020 | 1440×900 |
| `body` 배경 | `rgb(242,244,247)` = `#F2F4F7` | 같음 | 같음 |
| `.btn` 계산 높이 / 모서리 | 32px / 3px | 32px / 3px | 32px / 3px |
| `.chip` 계산 높이 | 19px | 19px | 22px |
| `body` 글꼴 | `"IBM Plex Sans KR", system-ui, sans-serif` | 같음 | 같음 |
| 콘솔 오류 | `support.js` 404 **하나뿐** | 같음 | 같음 |

`<helmet>` 은 알 수 없는 요소라 `display:inline` 으로 떨어지지만, 그 안의 `<style>` 과
`<link>` 는 브라우저가 정상 적용한다. 스크린샷도 디자인 의도대로 나온다.

**따라서 R2 는 위험이 아니라 기회다.** 확정 디자인의 값을 **렌더해서 잴 수 있다**는 뜻이고,
이것이 R4 의 대조 축을 통째로 바꾼다.

> `support.js` 참조는 남겨 둔다. 확정 디자인 파일은 이 기능의 **입력**이며 코드가 고치지
> 않는다 (spec Assumptions). 404 가 렌더에 영향이 없다는 것을 여기 기록하는 것으로 족하다.

---

## R3 — 기존 657건 검사는 클래스 전환에 얼마나 깨지는가

**결론: 대부분 안전하다. 정확히 4건만 의도적으로 다뤄야 한다.**

질의 방식 분포 (`frontend/tests/`):

| 질의 | 횟수 | 클래스 전환 영향 |
|---|---|---|
| `getByText`·`findByText`·`queryByText`·`getAllByText` | 312 | 없음 |
| `getByRole`·`findByRole`·`queryByRole`·`getAllByRole` | 77 | 없음 |
| `getByLabelText` 계열 | 73 | 없음 |
| `getByTestId` | 10 | 없음 |
| `getByAltText` 계열 | 3 | 없음 |

구조에 묶인 곳은 `querySelector` 인데, 확인해 보니 **선택자가 전부 `data-*` 속성**이다 —
`[data-step-row='st-1']` · `[data-cell='number']` · `[data-outcome='recorded']` ·
`[data-workbench-phase-bar]`. 클래스 이름이 바뀌어도 걸리지 않는다.

**깨지는 것은 인라인 `style` 을 직접 읽는 4건뿐이다** (`tests/WorkbenchShell.test.tsx`):

```js
expect(el("[data-workbench-phase-bar]").style.flex).toBe("0 0 48px");
expect(el("[data-workbench-step-panel]").style.flex).toBe("0 0 460px");
expect(frame.style.minWidth).toBe("1440px");
expect(left.style.flexGrow).toBe("1");
```

이것들은 **시각 언어가 아니라 배치 계약**이다 (007 `ui-contract.md` §1-2, `lib/layout.ts`).
48·460·1440 은 색이나 서체가 아니라 껍데기의 골격 수치이고, 007 이 표를 정본으로 세워
컴포넌트가 스스로 판단하지 못하게 막아 둔 값이다.

**결정: 배치 계약은 인라인 `style` 로 남긴다.** 값의 출처만 정본 토큰으로 바꾼다. 그러면
위 4건은 그대로 초록이고, 값은 여전히 한 곳에서 온다. 배치를 클래스로 옮기면 007 이 세운
`DETAIL_PLACEMENT`·`VERTICAL_SPLIT` 표의 강제력(컴파일 시점 `Record<Phase, …>`)을 잃는다 —
그 대가를 치를 이유가 없다.

---

## R4 — 시각 언어 정본을 어디에 어떻게 두는가

### 대안 비교

| 안 | 값이 한 곳인가 | 우회를 기계가 잡는가 | 33파일 전환 비용 | 657건 영향 | 판정 |
|---|---|---|---|---|---|
| **A. 전역 클래스 시트 승격** (`tokens.css` 에 80줄 정본을 그대로) | ✅ 시트가 유일한 정의처 | ✅ tsx 에서 색 리터럴을 세면 된다 | 중 — `style={{…}}` → `className` | 4건만 (R3) | **채택** |
| B. CSS Modules | ✅ | ✅ | 상 — 파일마다 `.module.css` 33개, 정본이 다시 쪼개진다 | 4건 | 기각 |
| C. CSS-in-JS 도입 | ✅ | △ 런타임 문자열이라 정적 검사가 약해진다 | 상 — 의존성 추가 | 미상 | 기각 |
| D. 인라인 + `var(--토큰)` 참조 | ❌ **형태가 여전히 33곳에 흩어진다** — `.btn` 의 높이·여백·굵기 조합이 파일마다 복제된다 | △ 색은 잡지만 형태 중복은 못 잡는다 | 하 | 0건 | 기각 |

**D 를 기각하는 이유가 이 기능의 핵심이다.** D 는 색만 토큰화하므로 SC-402(색 리터럴 0)는
만족시키지만 SC-404(값이 두 곳에 존재하지 않는다)는 만족시키지 못한다. `.btn` 하나가
`display·align·gap·height·padding·border·radius·background·color·font·shadow` 11개 선언인데,
이것을 33개 파일이 각자 복제하면 **지금과 똑같은 상태**다. 007→008 에서 "전사"가 결함이 된
것이 정확히 이 지점이다.

**C 를 기각하는 이유**: 헌법의 단순성 요구다. 프레임워크 없는 현 구성에서 의존성을 늘리는
비용이, 얻는 것보다 크다. 정본이 이미 순수 CSS 80줄로 존재한다 (R1).

### 채택안 — A

1. `docs/design/008-visual-language/*.dc.html` 의 `<style>` 80줄을 **기계적으로 추출**해
   `frontend/src/theme/tokens.css` 의 정본 구획으로 넣는다. R1 이 18장 동일을 보장하므로
   추출에 사람 판단이 없다.
2. dc.html 의 토큰 이름은 축약형(`--r`·`--sans`·`--e-1`)이고 현행 `tokens.css` 는 서술형
   (`--radius`·`--font-sans`·`--e-1`)이다. **현행 이름을 유지하고 값만 정본에서 받는다** —
   이름을 바꾸면 이미 쓰이는 46곳이 함께 깨지고, 이름은 대조 대상이 아니다(값이 대조 대상이다).
   추출 스크립트가 이름 대응표를 갖는다.
3. 컴포넌트는 `className` 으로만 소비한다. 시각 언어 값을 인라인으로 적지 않는다.
4. 예외는 배치 계약뿐이다 (R3).

---

## R5 — 정본 우회를 기계가 잡는 방법 (FR-278·FR-279)

**결론: vitest 검사 한 개가 화면 파일 전체를 열거해 센다.** 표본이 아니다.

현행 `DesignTokens.test.tsx` 는 `import tokens from "../src/theme/tokens.css?raw"` 처럼
**파일 5개를 손으로 import** 한다. 화면 파일이 늘면 검사 대상에서 빠진다 — V-09 가 이것이다.

Vite 는 `import.meta.glob("../src/**/*.tsx", { query: "?raw", eager: true })` 로 디렉터리
전체를 열거할 수 있다. 이렇게 하면 **새 파일이 자동으로 검사 대상이 된다.** 빠뜨릴 수 없다.

검사 항목(정적, 원문 대상):

| # | 세는 것 | 근거 |
|---|---|---|
| G-1 | 색 리터럴 (`#rgb`/`#rrggbb`/`rgb(`/`rgba(`/`hsl(`) | FR-265 · SC-402 |
| G-2 | 시각 언어 속성의 인라인 선언 (`background`·`border`·`borderRadius`·`boxShadow`·`font*`·`color`·`letterSpacing`) | FR-263 · SC-404 |
| G-3 | 정본에 없는 클래스 이름 사용 | FR-264 |
| G-4 | 정본 시트에 dc.html 에 없는 값이 추가됐는가 | FR-266 (`design_baseline.py` 와 양쪽에서 조인다) |

**실패 메시지는 `파일:줄 — 발견한 값` 형식**이다 (FR-279). 수치만 보고하면 고칠 곳을 모른다.
원문을 줄 단위로 훑으므로 줄 번호가 자연히 나온다.

**예외 등록부** (FR-267): `frontend/src/theme/exceptions.ts` 에 `파일 → 사유 → 허용 패턴`
으로 두고 **검사가 그 파일을 읽는다.** 등록부에 없는 예외는 검사가 잡는다. 등록부 자체가
코드이므로 리뷰에 걸리고, 항목마다 사유 문자열이 필수다.

> 왜 `.eslintrc` 가 아니라 vitest 인가 — 저장소에 eslint 구성이 없다. 검사를 하나 더 도입하는
> 것보다 이미 도는 657건 옆에 붙이는 편이 단순하다(헌법 단순성). `npm test` 하나로 전부 돈다.

---

## R6 — 대조 축의 재설계 (FR-281·FR-282)

**결론: 세 층으로 나눈다. 사람이 보는 항목이 화면당 3개로 줄어든다.**

현행 축이 못 잡는 것은 명세 V-10 에 있다 — `div 141개` 는 마커가 빠져도, 필터가 없어도,
격자가 달라도 그대로다. R2 가 **디자인을 렌더해서 잴 수 있다**는 것을 확인했으므로 축을
바꿀 수 있다.

| 층 | 무엇을 대조하나 | 누가 | 어떻게 |
|---|---|---|---|
| **L1 값** | 정본 시트 ↔ 확정 디자인 시트 | 기계 | 양쪽을 chromium 으로 렌더해 계산값(`getComputedStyle`)을 비교한다. `.btn` 높이 32px, `.chip` 모서리 2px 처럼 **브라우저가 계산한 값**을 잰다 |
| **L2 소비** | 화면 코드 ↔ 정본 | 기계 | R5 의 G-1~G-4 |
| **L3 구조·가감** | 화면 ↔ 확정 디자인 | 사람 | 디자인에 있는 요소가 화면에 있는가 / 없는 것을 더하지 않았는가 / 상태 표현이 형태를 함께 쓰는가 |

**이 셋이 합쳐지면 논증이 성립한다.** L1 이 정본=디자인을 보이고, L2 가 화면=정본을 보이면,
색·기하·타이포는 **구성상** 화면=디자인이다. 사람이 볼 것은 L3 만 남는다 — 화면당 3항목,
18장이면 54항목이다. 509칸이 54칸이 된다.

**이것이 SC-401(미판정 0건)을 실제로 도달 가능하게 만드는 유일한 경로다.** 001 T156 ·
002 T099 가 남긴 기록은 "사람이 500칸을 채우는 절차는 완료되지 않는다"는 증거다 (V-11).

`scripts/design_baseline.py` 는 **고쳐 쓴다, 대체하지 않는다.** 지금 하는 일(dc.html 에서
기계적으로 뽑기)은 그대로 필요하고, 뽑는 대상만 텍스트 카운트에서 렌더 계산값 + L3 항목으로
바꾼다. `--write` 가 대조표를 생성하는 구조도 그대로다.

---

## R7 — 목록 필터·정렬을 어디서 계산하는가 (FR-272)

**결론: 화면 안에서 계산한다 (클라이언트).**

백엔드 목록 API 를 확인했다 (`backend/src/itb/api/routes/tests.py:93`):

```python
async def list_tests(state: State, q: Annotated[str | None, Query(max_length=200)] = None)
```

**질의 인자가 `q` 하나다.** 결말 필터도 정렬도 서버가 받지 않는다. 그런데 응답 행
(`TestListRow`)은 `outcome` 과 `last_run_at` 을 이미 담고 있고, 집계(`passed`·`failed`)도 함께
온다. 필터·정렬에 필요한 값이 전부 화면에 있다.

**따라서 백엔드를 건드리지 않는다.** 이것은 이 기능의 범위(spec Out of Scope: 백엔드·API 변경
없음)와도 맞고, 로컬 도구라 목록 규모가 작아 성능 문제도 없다 (`TestList.tsx` 의 기존 주석이
"로컬 도구이므로 디바운스 없이도 충분하다"고 같은 판단을 이미 적어 두었다).

검색(`q`)만 지금처럼 서버를 다시 부른다. **검색과 필터가 다른 층에서 작동한다는 사실은 화면
동작에 드러나지 않는다** — 사용자는 둘 다 즉시 반영되는 것으로 본다.

---

## R8 — 33개 파일의 전환 순서

**결론: 사용자 이야기 순서를 그대로 쓰되, 정본과 가드를 US1 안에서 먼저 세운다.**

| 단계 | 대상 | 왜 이 순서인가 |
|---|---|---|
| 0 | `theme/tokens.css` 정본 · 추출 스크립트 · 가드(경고만) | 정본 없이 화면을 옮기면 다시 전사가 된다. 가드는 이 시점엔 **세기만** 하고 실패시키지 않는다 — 33파일이 전부 위반 상태이므로 |
| 1 (US1) | `pages/TestList.tsx` · `components/design/Chrome.tsx` · `components/Badges.tsx` | 첫 화면. 정본이 실제 화면 하나를 감당하는지 여기서 판명된다. 감당 못 하면 여기서 정본을 고치는 것이 33파일 뒤에 고치는 것보다 싸다 |
| 2 (US2) | `components/workbench/*` 8 · `pages/SessionScreen.tsx` · `EditView.tsx` · `ComposeView.tsx` · `MirrorView` · `TabStrip` · `PacingControl` · `LocatorPriorityTable` · `AssertionForm` · `StepEditFields` · `InlineSecretInput` | 잔재가 가장 많고 표면이 가장 크다 |
| 3 (US3) | `pages/ProjectSetup.tsx` · `KeyManagement.tsx` · `SecretValues.tsx` · `ResultView.tsx` · `components/ErrorNotice.tsx` · `SessionLostBanner` · `LiveConnectionBanner` · `StartingIndicator` · `NoticeStack` · `design/BrowserFrame.tsx` | 정본을 소비하기만 한다 |
| 4 (US4) | 가드를 실패로 전환 · 대조표 재생성 · L3 판정 | 대상이 전부 옮겨진 뒤에야 가드를 조일 수 있다 |

**검증 단위는 파일이 아니라 화면이다.** 화면 하나를 옮길 때마다 657건을 돌린다. 파일 단위로
자르면 한 화면이 반쯤 옮겨진 상태가 생기고, 그 상태의 검사 실패는 진단이 어렵다.

---

## 미해결로 남긴 것

없다. 계획이 결정해야 할 7건이 전부 확인된 사실 위에서 결정됐다.

한 가지만 **구현 중 판명된다**: R4 채택안이 `.btn`·`.chip` 같은 형태로 33개 파일의 모든
조작을 감당하는지는 US1 에서 실제로 옮겨 봐야 안다. 감당 못 하는 형태가 나오면 그것은
**확정 디자인에 없는 형태**이므로 `undefined-states.md` 기록 대상이다 (DC-009) — 정본을
임의로 늘리지 않는다 (FR-266).
