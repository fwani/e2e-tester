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

**전환을 마치고 나서 `grep` 기준을 완료 판정에서 뺐다.** 그 명령은 주석 안의 색까지 세는데,
이 기능의 결과로 코드에는 「v1 은 `#C9A227` 을 직접 정했다」처럼 **제거한 값을 증거로
인용하는 주석**이 남았다. 그 문장은 화면에 나가지 않으므로 위반이 아니다. 세는 규칙은
`contracts/visual-language.md` §4 가 정하고 `count-violations.mjs` 가 구현하며, 가드가 같은
함수를 쓴다 — 판정과 강제가 한 규칙이다 (quickstart 「완료 판정」).

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
| US2 껍데기·Step 목록 | 116 | 350 | 9종 | 675 통과 |
| US2 Step 상세 | 78 | 262 | 8종 | 675 통과 |
| US2 국면 화면 | 25 | 172 | 5종 | 675 통과 |
| **US3 남은 6장** | **0** | **1** | **0종** | 675 통과 |
| **US4 가드 고정** | **0** | **0** | **0종** | **676 통과** (50파일 657 → 53파일 676) |

## 완료 판정 (2026-09-08)

| SC | 판정 | 근거 |
|---|---|---|
| SC-402 색 리터럴 0 | ✅ | `count-violations.mjs` 합계 0 |
| SC-403 팔레트 밖 0종 | ✅ | 같은 명령, 0종 |
| SC-404 값이 두 곳에 없다 | ✅ | G-2 인라인 시각 언어 선언 0 |
| SC-405 가드가 실제로 잡는다 | ✅ | 검사 안에서 인위적 원문으로 확인 + 실물 파일에 위반을 심어 검사가 실패하고 `파일:줄 — 값` 을 보고하는 것을 확인 (심은 것은 되돌렸다) |
| SC-407 검사 전부 통과 | ✅ | 53파일 676건. 삭제·비활성 0건 (`git diff --diff-filter=D` 로 확인) |
| SC-409 900px 에서 Step 13행 | ✅ | 실측 — 행 52px · Step 패널 760px · **완전히 보이는 행 14**. 알림 띠(32px)가 있는 국면에서 13행. v1 은 5행이었다 |
| SC-401 미판정·불일치 0 | ⏳ | L1·L2 는 18장 전부 `일치`. **L3 54항목은 사람 몫** (DC-C) |
| SC-406 정보가 줄지 않았다 | ⏳ | L3 판정에 포함 |
| SC-408 빠진 요소 0 | ⏳ | L3-1 판정에 포함. 구현자가 아는 차이 1건을 `undefined-states.md` §2 에 적었다 |
| SC-410 색 없이도 구분된다 | ⏳ | L3-3 판정에 포함 |

US1 이 0 으로 만든 파일: `pages/TestList.tsx`(90→0 · 141→0) · `components/design/Chrome.tsx`
(11→0 · 20→0) · `components/Badges.tsx`(0→0).

정본에서 `#A32C13`(`--fail-dark`)·`#5732B0`(`--ai-dark`)를 뺐으므로(확정 디자인에 없다)
그 둘이 팔레트 밖으로 새로 잡힌다. 대신 `#E4DFD1`·`#B8860B`·`#E5D3AC`·`#EFC7BC` 가
사라졌다 — 앞의 둘은 v1 잔재라 지웠고, 뒤의 둘은 진짜 v2 값이라 `--warn-line`·
`--fail-line` 으로 정본에 들어왔다.

---

## 이 기능이 만든 것 (T091)

`plan.md` 의 Structure Decision 은 「신규 파일은 셋뿐」이라 적었다. 실제로는 **여덟**이다.
다섯이 더 생겼고 전부 요구사항이 요구한 것이지만, 계획의 목록과 어긋나므로 무엇을 왜
더 만들었는지 남긴다. (`plan.md` 는 고치지 않는다 — converge 의 계약)

| 파일 | 계획에 | 왜 필요했나 |
|---|---|---|
| `frontend/src/theme/exceptions.ts` | ✅ | 예외 등록부. 검사가 읽어야 「등록되지 않은 예외는 존재할 수 없다」가 성립한다 (FR-267) |
| `frontend/tests/VisualLanguage.test.tsx` | ✅ | L2 가드. 축 G-1~G-6 |
| `scripts/design_render.py` | ✅ | L1 측정. chromium 으로 두 시트를 렌더해 계산값을 비교한다 |
| `scripts/extract_canon.py` | ➕ | **정본을 추출한다.** 계획은 「기계 추출」을 결정했지만 그 일을 할 파일을 세지 않았다. 이것이 없으면 추출은 사람이 손으로 하는 일이 되고, 그것이 007 의 「전사」다 |
| `frontend/scripts/count-violations.mjs` | ➕ | **세는 규칙의 정의처.** 가드와 완료 판정이 같은 함수를 써야 「판정과 강제가 한 규칙」이 된다. 규칙을 두 곳에 두면 그것 자체가 이 기능이 고치려는 결함이다 |
| `frontend/src/theme/tone.ts` | ➕ | 결말의 **뜻**(`outcomeTone`)과 정본의 **형태**(`.chip.pass`)를 잇는다. 잇는 자리가 없어서 두 어휘가 말없이 어긋나 있었고, 통과한 테스트의 표식이 아무 변형도 받지 못한 채 그려지고 있었다 — 008 이 찾아 고친 결함이다 |
| `frontend/tests/CanonMatchesDesign.test.ts` | ➕ | L1 을 **검사로** 만든다. `design_render.py` 는 재기만 하고, 낡은 보고서로 통과할 수 없게 하는 것은 이 파일이다 |
| `frontend/tests/TestListFilters.test.tsx` | ➕ | FR-272(필터·정렬)와 FR-273(격자 공유)의 회귀 가드. 새로 만든 조작은 새로 만든 검사가 받쳐야 한다 |

**고친 파일 중 계획이 세지 않은 것**: `scripts/design_baseline.py`(축 개편) ·
`docs/design/008-visual-language/replacement-map.md`(「전사」 방침 폐기) ·
`conformance/*.md` 18장(재생성) · `conformance/undefined-states.md`(실제 기록).
