# 대체 관계 — 폐기된 19장 → 008 의 18장

**날짜**: 2026-09-08
**폐기 대상**: `docs/design/_retired/` (v1 확정 8종 + 007 초안 12장)
**새 기준**: `docs/design/008-visual-language/` 18장

이 문서는 **무엇이 어디로 갔는지**를 판정 넷으로 적는다.

| 판정 | 뜻 |
|---|---|
| `그대로` | 같은 화면이 같은 목적으로 이어진다 |
| `이동` | 다른 화면·다른 자리로 옮겨졌다 |
| `분리` | 한 장이 둘 이상으로 갈라졌다 |
| `옮기지 않음` | 새 기준에 없다 — **이유가 필수다** |

---

## 1. v1 확정 디자인 8종

| 폐기된 것 | 판정 | 어디로 | 비고 |
|---|---|---|---|
| `TestList.dc.html` | `분리` | `TestList.dc.html` + `EmptyList.dc.html` | 테스트 0개 상태가 v1 에 없었다. 첫 사용자가 보는 화면이 정의되지 않은 채였다 |
| `CreateTest.dc.html` | `이동` | `Create.dc.html` | 1000px 다이얼로그 → 여덟째 국면. 007 FR-217b 가 정한 것을 그대로 따른다 |
| `AiRecord.dc.html` | `분리` | `AiWriting.dc.html` + `AiBlocked.dc.html` | v1 은 진행 중과 막힘을 한 장에 그려서 막힘 상태의 선택지 3개가 정의되지 않았다 |
| `Main.dc.html` (실행 중) | `이동` | `Run.dc.html` | 이름이 국면을 말하도록 바꿨다. `Main` 이라는 이름은 이제 편집 국면이 갖는다 (캔버스 진입 아트보드) |
| `RunnerPaused.dc.html` | `그대로` | `Paused.dc.html` | 검증 추가 폼이 42px 띠에서 나와 제 높이를 갖는다 |
| `Takeover.dc.html` | `그대로` | `Takeover.dc.html` | AI 실패 사유가 이어받는 동안 계속 보이는 것(001 R2)을 유지 |
| `RunResult.dc.html` | `그대로` | `Result.dc.html` | 산출물이 별도 640 열이 아니라 대상 앱 슬롯 자리에 온다 (007 S-11 해소를 이어받음) |
| `StepInspector.dc.html` | `그대로` | `StepDetail.dc.html` | 640px 겹침 패널. LOCATOR 우선순위 표가 핵심이고 그대로다 |

## 2. 007 통합 화면 초안

| 폐기된 것 | 판정 | 어디로 | 비고 |
|---|---|---|---|
| `Workbench.dc.html` (1회차 · 1520×8400) | `이동` | 008 의 국면 10장 전체 | 일곱 국면을 한 장에 세로로 쌓은 초안이었다. 국면마다 아트보드를 나눠 대조가 화면 단위로 성립하게 했다 |
| `007-rework/Create.dc.html` | `그대로` | `Create.dc.html` | |
| `007-rework/Record.dc.html` | `그대로` | `Record.dc.html` | |
| `007-rework/AiBlocked.dc.html` | `그대로` | `AiBlocked.dc.html` | |
| `007-rework/Takeover.dc.html` | `그대로` | `Takeover.dc.html` | |
| `007-rework/Run.dc.html` | `그대로` | `Run.dc.html` | |
| `007-rework/Paused.dc.html` | `그대로` | `Paused.dc.html` | |
| `007-rework/Result.dc.html` | `그대로` | `Result.dc.html` | |
| `007-rework/Main.dc.html` (편집) | `그대로` | `Main.dc.html` | ③-a 를 118 → 88 로 줄였다. 조작 높이가 46 → 32 로 내려간 만큼이다 |
| `007-rework/DirectionA.dc.html` | `옮기지 않음` | — | **이유**: 채택된 안의 규칙 시트였다. 그 규칙은 `Language.dc.html` 이 대체하며, v2 는 규칙 자체가 달라 옮길 내용이 없다 |
| `007-rework/DirectionB.dc.html` | `옮기지 않음` | — | **이유**: 채택하지 않은 대안(Step 상세를 가운데 붙박이 열로 · 기준 폭 1720 필요)의 기록이다. 그 판단의 근거는 `specs/007-unify-test-screens/spec.md` 와 `research.md` 에 글로 남아 있고, 008 은 같은 결론(겹침 640)을 유지하므로 재검토 대상이 아니다 |
| `007-rework/DirectionC.dc.html` | `옮기지 않음` | — | **이유**: 위와 같다 — 국면을 탭으로 두는 안이며, 미러를 보면서 고치는 동시성을 잃는다는 이유로 기각됐다. 008 도 같은 이유로 채택하지 않는다 |

## 3. 008 이 새로 정의한 것

**v1 에 대응 화면이 아예 없던 것들이다.** `specs/001-.../spec.md` 는 이 공백을 이미
기록해 두었다 — "docs/design 8화면에 대응 화면이 없다. 구현 시 새로 설계해야 한다."
그 결과 이 화면들은 디자인 없이 구현됐고, 지금까지 대조 대상이 아니었다.

| 새로 정의한 것 | 대상 | 왜 필요했나 |
|---|---|---|
| `ProjectSetup.dc.html` | `pages/ProjectSetup.tsx` | 제품의 **첫 화면**인데 디자인이 없었다 |
| `EmptyList.dc.html` | `pages/TestList.tsx` (0개) | 첫 사용자가 실제로 보는 상태 |
| `Keys.dc.html` | `pages/KeyManagement.tsx` | 디자인 없이 구현됐다 |
| `Secrets.dc.html` | `pages/SecretValues.tsx` | 디자인 없이 구현됐다 |
| `Finished.dc.html` | `SessionScreen` (실행 종료) | 007 걷기가 결함 2건을 찾은 상태다 — 국면 표시와 결말 요약이 어긋났고, 돌아온 화면이 결말을 말하지 못했다. 정의된 화면이 없어서 생긴 공백이다 |
| `AiWriting.dc.html` | `SessionScreen` (AI 진행) | `AiRecord` 에서 분리 (§1) |
| `Language.dc.html` | `theme/tokens.css` | 시각 언어 자체의 정의. v1 에는 이 문서가 없어 토큰이 "지어낸 값"을 담을 수 있었다 (002 가 고친 결함) |
| `States.dc.html` | `ErrorNotice` · `SessionLostBanner` · `LiveConnectionBanner` · `StartingIndicator` | 알림·오류·확인의 문구와 형태 규칙. 003 이 글로 정한 것을 화면으로 옮겼다 |

---

## 4. 코드 전환 — 7건 중 6건 완료

순서가 중요했다 — 1번을 건너뛰면 2번이 즉시 실패한다 (가드가 v1 을 하드 단언하고 있었다).

| # | 대상 | 할 일 | 상태 |
|---|---|---|---|
| 1 | `frontend/tests/DesignTokens.test.tsx` | **v1 을 하드 단언한다** — `border-radius` 없음 · `--radius` 없음 · 1px 테두리 금지 · 하드 그림자 필수 · 배경 `#EFEBE0`. 전부 v2 와 정반대다. v2 를 단언하도록 뒤집는다 | 완료 |
| 2 | `frontend/src/theme/tokens.css` | v2 토큰으로 교체. `Language.dc.html` 이 기준이다 | 완료 |
| 3 | `frontend/src/lib/layout.ts` | ③-a 고정 높이 118 → 88 | 완료 |
| 4 | `specs/007-unify-test-screens/contracts/ui-contract.md` §1-2 | 헤더 60→56 · 국면 띠 74→48 · 조작 44→32 · Step 행 → 52. Step 패널 460 과 기준 폭 1440 은 그대로 | 완료 |
| 5 | `components/workbench/{StepList,PhaseBar,ActionButton,TargetPane,StepDetail}.tsx` · `pages/TestList.tsx` | 이 파일들은 v1 dc.html 의 인라인 값을 **전사**했다. 주석이 가리키는 경로가 지금 `_retired/` 다. 값과 주석을 함께 옮긴다 | 완료 |
| 6 | `frontend/tests/{StepRowLayout,WorkbenchShell}.test.tsx` | 치수를 단언한다. 4번을 따라 갱신 | 완료 |
| 7 | `docs/design/008-visual-language/conformance/*.md` | 리뷰어가 `관측값`·`판정` 을 채운다. 완료 조건은 `불일치`·`미판정` 0건 | **남음** — 리뷰어 몫 |

`scripts/design_baseline.py` 는 008 을 읽도록 옮겼고 `assert_baseline` 의 단언도 뒤집었다
(v1 의 하드 오프셋 그림자가 섞여 들어오면 멈춘다).

전환 뒤 격리 환경(포트 4510·4520 · 격리 XDG)에서 제품을 띄워 목록 · 편집 · Step 상세 ·
키 관리 · 비밀 값을 눈으로 확인했고, 자동 검사가 초록인 상태에서 결함 4건을 더 찾아
고쳤다 (③-a 넘침 · 비활성 사유가 층을 덮음 · `pending` 이 체크박스로 읽힘 · 정규식을
빠져나간 하드 그림자 1건).

---

## 5. 명세 개정이 필요한 것 — FR-230

**상태**: 코드·계약·검사는 이미 새 규칙을 따른다. `specs/007-.../spec.md` 의 FR-230
문장만 아직 옛 규칙이다.

| | |
|---|---|
| 현행 FR-230 | Step 상세는 **같은 자리에** 같은 구성으로 열려야 하며, 국면에 따라 열리는 자리가 달라지지 않는다 |
| 개정안 | Step 상세를 **거는 자리는 국면이 정하되 표가 정본이다** (`lib/layout.ts` 의 `DETAIL_PLACEMENT`). 구현은 한 벌이고(FR-229) 항목과 순서는 같다(FR-231) |

**왜.** 007 은 S-05(같은 Step 이 국면에 따라 다른 자리에서 열림)를 자리 고정으로 막았다.
그러나 S-05 의 실제 원인은 **구현이 두 벌이라 갈라진 것**이었다 — 자리가 둘이라는 사실
자체가 아니다.

그리고 같은 라운드가 모순을 하나 남겼다. ③-b 를 「그 국면의 주 작업 자리」로 정하고 편집
국면에 `fill` 을 줬는데(FR-257), 그 항목의 근거 주석은 **「하는 일은 Step 편집이다」**
였다. 정작 Step 편집 폼은 겹침에 있었고, ③-b 에 담기로 했던 테스트 이름·시작 주소·지시문은
FR-235 로 조작 팔레트에 갔다. 남은 것은 **비어 있는 것이 정상인 자리에 남는 높이를 전부
주는 배분**이었고, 편집 화면에 들어오면 절반이 아무 말도 하지 않았다.

**무엇으로 S-05 를 막는가.** 자리 고정 대신 셋을 검사가 센다
(`frontend/tests/WorkbenchShell.test.tsx`).

1. 모든 국면에서 상세가 **정확히 한 벌**만 그려진다 (SC-001)
2. 거는 자리가 `DETAIL_PLACEMENT` 와 **한 글자도 다르지 않다** — 컴포넌트가 스스로
   판단하지 않는다 (UC-101)
3. `placement` 만 바꿔 그렸을 때 **담는 것이 같다** — 배치는 껍데기만 바꾼다 (FR-231)

계약 문서는 이미 갱신했다: `specs/007-unify-test-screens/contracts/ui-contract.md` §1-2-1.
UC-102(한 값에 입력칸이 둘일 수 없다)도 그 절에 함께 있다.
