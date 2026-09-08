# 기준선 — 008 시각 언어 전환

**측정**: `node frontend/scripts/count-violations.mjs` (T001)

**시점**: 2026-09-08 · 커밋 `b01daf0` 시점의 작업 트리


> **이 표가 진행의 유일한 판정 기준이다.** 단계마다 다시 재서 열을 추가한다.
> 수치가 늘어나면 멈추고 보고한다.

## 세는 규칙

| 축 | 세는 것 | 근거 |
|---|---|---|
| 색 | `#rgb`~`#rrggbbaa` · `rgb(` · `rgba(` · `hsl(` · `hsla(` — 표기를 바꿔 빠져나갈 수 없다 | G-1 · FR-265 |
| 인라인 | 시각 언어 속성 25종의 인라인 선언 (`background`·`border*`·`boxShadow`·`color`·`font*`·`letterSpacing`·`lineHeight`·`opacity`·`outline`·`textDecoration`·`textTransform`) | G-2 · FR-263 |
| 팔레트 밖 | 정본 `tokens.css` 가 선언하지 않는 색 | SC-403 |

**주석은 세지 않는다.** 주석 안의 색은 근거를 적은 것이지 화면에 나가는 값이 아니다.

## 명세 수치와의 차이 — 정정 2건

spec.md 는 `grep` 으로 잰 값을 적었고 그것은 주석을 포함한다. T001 은 주석을 걷어내고
표기 변형까지 잡으므로 값이 다르다. **정확한 쪽은 T001 이다.**

| | spec.md | T001 | 왜 다른가 |
|---|---|---|---|
| 색 | 327 | **338** | `grep` 은 `#rrggbb` 만 봤다. T001 은 `rgba(`·3자리 hex 도 센다 |
| 인라인 | 437 (`style={{` **블록** 수) | **730** (속성 수) | 블록 하나가 여러 속성을 갖는다. 고칠 대상은 속성이다 |
| 팔레트 밖 | 17종 | **16종** | `#F5D000` 은 `ActionButton.tsx:39` **주석 안**에만 있다 — v1 노란 배경을 설명하는 문장이며 화면에 나가지 않는다. 전환 때 그 주석도 함께 고친다 (T029) |

`grep` 기준 값(327·437·17)도 계속 유효하다 — quickstart 「완료 판정」이 그 명령을 쓴다.
**둘 다 0 이 되어야 한다.**

## 기준선

| 파일 | 색 | 인라인 | 팔레트 밖 |
|---|---|---|---|
| `pages/TestList.tsx` | 90 | 141 | #E4DFD1 #B8860B |
| `components/workbench/StepList.tsx` | 37 | 49 | — |
| `pages/SessionScreen.tsx` | 30 | 39 | #F0F7F2 |
| `components/workbench/WorkArea.tsx` | 29 | 64 | #EFC7BC #E5D3AC #FFF6D9 #1F7A3D #8A6A16 #FFF6D8 |
| `components/workbench/StepDetail.tsx` | 20 | 51 | — |
| `pages/ProjectSetup.tsx` | 13 | 70 | — |
| `components/workbench/ActionPalette.tsx` | 13 | 25 | — |
| `components/workbench/TargetPane.tsx` | 12 | 28 | — |
| `components/workbench/ActionButton.tsx` | 11 | 23 | — |
| `components/design/Chrome.tsx` | 11 | 20 | — |
| `components/InlineSecretInput.tsx` | 9 | 17 | — |
| `components/LocatorPriorityTable.tsx` | 9 | 15 | #EAF5EE |
| `components/workbench/PhaseBar.tsx` | 9 | 15 | #B8860B |
| `components/PacingControl.tsx` | 9 | 13 | #8A5A00 |
| `components/design/BrowserFrame.tsx` | 8 | 16 | #2A303A |
| `pages/EditView.tsx` | 6 | 17 | — |
| `components/workbench/NoticeStack.tsx` | 6 | 11 | #8A6A16 |
| `components/ErrorNotice.tsx` | 5 | 12 | #C9A227 #FDF8E7 #B4453C #FBEDEB |
| `pages/KeyManagement.tsx` | 4 | 36 | — |
| `components/workbench/Workbench.tsx` | 4 | 5 | — |
| `pages/ResultView.tsx` | 3 | 5 | — |
| `pages/SecretValues.tsx` | 0 | 23 | — |
| `components/AssertionForm.tsx` | 0 | 8 | — |
| `components/SessionLostBanner.tsx` | 0 | 8 | — |
| `components/StepEditFields.tsx` | 0 | 8 | — |
| `components/LiveConnectionBanner.tsx` | 0 | 3 | — |
| `components/MirrorView.tsx` | 0 | 3 | — |
| `components/StartingIndicator.tsx` | 0 | 3 | — |
| `components/TabStrip.tsx` | 0 | 2 | — |
| **합계 (29파일)** | **338** | **730** | **16종** |

**팔레트 밖 16종**: `#1F7A3D` · `#2A303A` · `#8A5A00` · `#8A6A16` · `#B4453C` · `#B8860B` · `#C9A227` · `#E4DFD1` · `#E5D3AC` · `#EAF5EE` · `#EFC7BC` · `#F0F7F2` · `#FBEDEB` · `#FDF8E7` · `#FFF6D8` · `#FFF6D9`

## 검사 기준선

```
Test Files  50 passed (50)
     Tests  657 passed (657)
```

## 진행 기록

| 단계 | 색 | 인라인 | 팔레트 밖 | 검사 |
|---|---|---|---|---|
| 기준선 | 338 | 730 | 16종 | 657 통과 |
| Phase 2 정본 | 338 | 730 | 16종 | 668 통과 (신규 11) |
| US1 목록 | **237** | **569** | 15종 | 675 통과 (신규 7) |

US1 이 0 으로 만든 파일: `pages/TestList.tsx`(90→0 · 141→0) · `components/design/Chrome.tsx`
(11→0 · 20→0) · `components/Badges.tsx`(0→0).

정본에서 `#A32C13`(`--fail-dark`)·`#5732B0`(`--ai-dark`)를 뺐으므로(확정 디자인에 없다)
그 둘이 팔레트 밖으로 새로 잡힌다. 대신 `#E4DFD1`·`#B8860B`·`#E5D3AC`·`#EFC7BC` 가
사라졌다 — 앞의 둘은 v1 잔재라 지웠고, 뒤의 둘은 진짜 v2 값이라 `--warn-line`·
`--fail-line` 으로 정본에 들어왔다.

