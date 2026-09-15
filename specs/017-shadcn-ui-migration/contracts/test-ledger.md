# Contract: 테스트 변경 기록

**Feature**: 017 | **Status**: 살아 있는 문서 — 테스트를 고칠 때마다 줄을 채운다 |
**요구**: 헌법 Quality Gate 4 · FR-028 · SC-008

## 규칙

1. **무엇을 검증하던 테스트인가**(`verifies`)는 바뀌지 않는다. 바뀌는 것은 판정 방법뿐이다.
2. 삭제 · `skip` · `todo` · 무른 단언으로의 교체(`toBeDefined()`·`toBeTruthy()` 로 구체 값을 대신하기)를 하지 않는다.
3. 단언 수를 센다 — 기준선 **2148** (`node frontend/scripts/count-assertions.mjs`). 파일 단위로 전·후를 적고,
   줄면 그 자리와 사유를 적는다. 무른 단언 기준선 **639** 는 늘면 사유를 적는다.
4. 고친 테스트 파일 머리주석에도 무엇을 왜 바꿨는지 적는다 (저장소 관행).

## 예상되는 변경 — 계획 단계 조사로 알려진 것

**「예상」은 확정이 아니다.** 실제로 고치게 되면 `상태` 를 채우고, 고치지 않아도 통과하면 `불필요` 로 적는다.

| 파일 | verifies (바뀌면 안 되는 것) | change (판정 방법) | why | 전→후 단언 | 상태 |
|---|---|---|---|---|---|
| `RowMenuVisible.test.tsx` | 행 메뉴가 표에 잘리지 않고 보이며, 다시 누르면 닫힌다 | `.click()` → `userEvent.click()` 으로 연다. 위치 인라인 스타일 읽기 → 메뉴 내용이 문서에 있고 표 컨테이너 밖(포털)에 있음을 확인 | 같음 (4 검사 · 판정 대상만 옮김) | ✅ T056 — **실제 변경**: 포인터 누름(`userEvent.click`)으로 연다. 「문서 바닥에 붙는다」·「창 기준 고정 배치」를 메뉴 자신이 아니라 Radix 가 자리 잡는 감싸개(`data-radix-popper-content-wrapper`)에서 본다. 「닫으면 사라진다」는 다시 누르기 대신 **Esc** 로 닫는다 — 모달 메뉴가 열린 동안 뒤쪽(여는 단추 포함)은 포인터를 받지 않아 jsdom 에서 다시 누를 수 없다. 실제 브라우저에서 다시 누르면 바깥 누름으로 닫힌다. 여는 법의 키보드 경로는 `MenuKeyboard` 가 본다 |
| `TestListActions.test.tsx` | 행 메뉴에서 편집·이름 바꾸기·삭제에 닿는다 | 메뉴 열기를 `userEvent` 로 | 같음 | ✅ T056 — 열기를 `userEvent.click` 으로. 「이름」 항목을 역할 `button` 이 아니라 `menuitem` 으로 찾는다 — 보조기술이 듣는 역할이 실제로 바뀌었다 |
| `EditEntryPoints.test.tsx` | 행 메뉴의 「편집」이 편집 국면으로 간다 | 같음 | 같음 | ✅ T056 — 열기 2곳을 `userEvent.click` 으로 |
| `PacingControl.test.tsx` | 고른 실행 속도가 남는다 | `aria-pressed` → `role="radio"` + `aria-checked` | `ToggleGroup type="single"` 은 배타 선택을 라디오로 알린다 (FR-013) | 4→4 | ⬜ |
| `RunnerPacing.test.tsx` | 실행 중에 바꾼 속도가 남는다 | 같음 | 같음 | | ⬜ |
| `NoticesAreToasts.test.tsx` | 목록의 알림이 내용을 밀어내지 않고 한 층에 뜬다 | 진행 중 세션 경우 — 토스트가 아니라 **흐름 안 띠 하나**가 그 사실을 말함을 확인한다 | B-02 · FR-018b. 같은 사실을 두 자리가 말했다 | 2→5 (세션 경우) | ✅ T023 |
| `ListLiveState.test.tsx` · `RecheckPhase12.test.tsx` | 실행 중·끝난 세션이 있을 때 목록에서 **실행 화면으로 돌아갈 수단이 있다** (005 FR-168) | 복귀 조작을 토스트의 「실행 화면 보기」가 아니라 띠의 「이어서 보기」로 찾는다 | B-02 — 같은 `onResumeSession` 을 부르는 조작이 한 화면에 둘이었다. 008 이 적은 「복귀 조작은 화면에 하나뿐」(`TestList.tsx:1368`)을 되살린다. 문구는 바꾸지 않는다 (spec Assumptions) | 1→1 · 1→1 | ✅ T023 |
| `ToastPlacement.test.tsx` | 알림 층이 한 자리(오른쪽 위)에 뜬다 | **더한다**: 층 클래스가 띠 조건 셋을 서로 배제하는 형태로 갖는다 | B-01. `top` 을 고정하는 테스트가 없어 회귀가 들어왔다 | 5→16 | ✅ T019 |
| `WorkbenchShell.test.tsx` | 작업 화면 틀이 1440 을 최소로 창을 채운다 | 틀 구조 — 머리띠가 가로 스크롤 영역 밖, 본문이 `min-width 1440 · width 100%` | B-11 · layout-contract-v3 L3 | | ⬜ |
| `WorkbenchHeight.test.tsx` | 작업 화면이 창 높이에 맞고 Step 목록이 스크롤 영역이다 | 높이 인라인 읽기 자리 조정 (머리띠가 밖으로 나온 뒤의 요소) | 같음 | | ⬜ |
| `VerticalSplit.test.ts` · `TargetPane.test.tsx` · `ComposePhase.test.tsx` | 국면별 대상 앱 자리의 배치 판단 | 만들기 국면의 `targetSlot` 기대값 `fixed(88)` → `content` | B-04 · v3 L5 — 판단 자체가 바뀐다. **테스트가 지키던 성질(표가 결정하고 부모가 내려준다)은 같다** | | ⬜ |
| `StepRowLayout.test.tsx` · `SavePlacement.test.tsx` · `RerecordBandPlacement.test.tsx` | Step 패널 머리·바닥의 구성 | 바닥 상한을 배치 표에서 읽는 형태로 | B-03 · v3 L4 | | ⬜ |
| `DetailPlacement.test.tsx` · `DetailBlocksMirrorInput.test.tsx` | Step 상세 판의 자리·미러 입력 차단 | 판이 `DetailPanel`(비모달 Dialog) 로 그려진 뒤 같은 속성을 읽는다 | 같음 | 불필요 (T052) — 판을 `data-workbench-step-detail` 로 찾으므로 `DetailPanel` 로 그린 뒤에도 그대로 통과 |
| `DesignTokens.test.tsx` · `InteractionStates.test.tsx` · `FocusRing.test.tsx` | 부품이 정본 치수·상태·초점을 지킨다 | 부품 파일이 `cva` 형태로 바뀐 뒤 찾는 문자열 갱신. 경로(`src/ui/*.tsx`)는 그대로 | research R1 · R5 | | ⬜ |
| `ClassConflict.test.ts` | 나중에 적은 클래스가 진다 | 헬퍼가 `cva`·`cn` 을 읽는다 (guards H-1) | 그대로 | ✅ T012 (Foundational) |
| `ImplementationCount.test.ts` | 구현이 또 한 벌 생기지 않는다 | `RETIRED` 에 옛 모달·수제 메뉴·옛 겹침 판 추가 | 옛 구현 삭제를 센다 | +5 | ✅ T054·T056 — `RETIRED` 는 파일 존재를 보므로 **이름 단위 퇴역 목록**을 새로 뒀다 (넓힌 가드 표) |
| `ImportPreview.test.tsx` · `InlineSecret.test.tsx` · `TestGroups.test.tsx` | 선택칸으로 고른 값이 반영된다 | **변경 없음 예상** — `NativeSelect` 는 실제 `<select>` 다 | 같음 | 불필요 (T038·T045·T047) — 예상대로 그대로 통과 |
| `StepRowActions.test.tsx` · `RerecordStart.test.tsx` · `DeleteOutcome.test.tsx` | 체크박스로 고른 Step | **변경 없음 예상** — `Checkbox` 는 실제 `<input type=checkbox>` 다 | 같음 | 체크박스는 불필요(예상대로). **`DeleteOutcome` 은 행 메뉴 때문에 바뀌었다** (T056) — 메뉴를 `userEvent.click` 으로 열고, 메뉴의 「삭제」를 `menuitem` 으로 찾는다. 두 「삭제」(메뉴 항목 · 행 안 확인 단추)가 이제 역할로 갈린다 |
| 확인 대화상자를 여는 화면 테스트 (`SaveNamePrompt` · `RunTrigger` · `RunFinished` · `PauseTransition` 등) | 확인 후의 동작 | 대화상자가 열린 동안 뒤쪽 요소를 `getByRole` 로 찾던 순서를 **닫은 뒤**로 | 같음 | 불필요 (T050·T051) — 확인 창을 누르는 `SaveNamePrompt`·`TestDefinition` 이 `document.querySelector` 로 찾아 포털·`aria-hidden` 의 영향을 받지 않았다 |
| `BeforeAfterParity.test.ts` | 전환 전후 화면이 같다 | 보고서 갱신 · `INTENDED` 추가 | 매 단계 | | ⬜ |

**환경 보완 (T056)** — `tests/setup/dom.ts` 가 jsdom 의 `el.matches(':popover-open')`·`el.matches(':modal')` 에 바로 거짓을 돌려준다. jsdom 이 이 둘에 한 번 약 150ms 를 써 Radix 메뉴·툴팁을 여는 검사가 2~10초씩 걸리고 5초 제한을 넘었다(floating-ui 가 조상마다 묻는다). jsdom 에는 최상위 층이 없어 **같은 답을 빨리 낸다** — 판정을 바꾸거나 제한을 늘리지 않았다 (research S3 원인 판명).

## 넓힌 가드 — 판정 대상이 늘어난 것

가드를 **좁히지 않고 넓히기만** 한다 ([guards.md](guards.md) 「가드를 바꿀 때의 규칙」). 넓혀서 새로 드러난
위반은 가드가 아니라 코드를 고쳤다.

| 파일 | verifies | 넓힌 것 | 새로 드러난 것 | 전→후 단언 | 상태 |
|---|---|---|---|---|---|
| `helpers/tailwind.ts` (G-B·G-C·G-E·G-F·`FocusRing` 공용) | 화면 코드의 클래스를 빠짐없이 읽는다 | 대괄호 **안에서만** `= & > ( ) , + * ~ " '` 허용 · `[` 로 시작하는 토큰 허용 (H-2). `cva(…)`·`cn(…)` 조합 읽기 (H-1). `이름({ … })` 호출의 객체 인자를 클래스로 읽지 않기. **산출 CSS 에서 이름을 뽑을 때 뒤에 속성 선택자 `[` 가 붙는 형태**(`.aria-\[invalid\=true\]\:border-fail[aria-invalid="true"]`)도 인정 — 전에는 `aria-[…]:`·`data-[…]:` 변종 클래스를 전부 「생성되지 않음」으로 봤다 (T029) | `ui/Field` 의 `[&_input]:outline-none` (N-01) · `ui/StepRow` 의 `[&_input:disabled]:opacity-40`(정본 S-13 — 예외 등록) | 헬퍼 (단언 없음) | ✅ T011·T012 |
| `FocusRing.test.tsx` | 초점 링을 지우지 않는다 | `outline-hidden` 추가 · 변형 접두와 무관하게 유틸리티 본체를 본다 | N-01 | 4→6 | ✅ T013 |
| `VisualLanguage.test.tsx` G-6 | 죽은 예외가 없다 | `raw-element` 축을 태그 이름 단위로 판정 | — | 그대로 | ✅ T015 |
| `ClassExistence.test.ts` (G-B) | 코드가 쓰는 클래스가 실제로 CSS 를 만든다 | 리터럴에 더해 **조립 조합**(`cva`·`cn`·`[…].join`)의 클래스도 실재를 확인 · 한 낱말짜리 변종 값을 읽는지 자체 점검 | `aria-invalid:border-fail` — Tailwind v4 에 없는 변종. 세 부품(`Input`·`Textarea`·`NativeSelect`)에 들어갔는데 넓히기 전에는 토큰이 여럿인 한 곳에서만 잡혔다. `aria-[invalid=true]:` 로 고치고 대응표를 바로잡았다 | 3→4 | ✅ T029 |
| `ClassExistence.test.ts` (G-B) | 코드가 쓰는 클래스가 실제로 CSS 를 만든다 | **템플릿 구멍이 `undefined`·`null`·`false` 를 글자로 내놓지 않는다** — 조립 검사는 구멍 앞에 클래스 글자가 붙은 형태만 봤다. 판정 함수를 위반 두 형태·정상 두 형태로 먼저 자체 점검 | N-04 — 가져오기 미리보기 시트 행(015 치환 569e51e)과 **미러 조작 면**에 `undefined` 클래스. 둘 다 코드를 고쳤다 | 4→9 | ✅ T045 |
| `ImplementationCount.test.ts` | 구현이 또 한 벌 생기지 않는다 | 파일 목록(`RETIRED`)에 더해 **다른 파일 안의 조각**을 이름·정의 형태로 센다 — `SessionScreen` 지역 `Modal` · `ui/Surface` `Modal`·`OverlayPane` · `EditView` 역할 alertdialog 판 · `StepDetail` 역할 dialog 판 | 대화상자 구현이 부품 밖에 네 벌 있었다 — 전부 `ui/Dialog`·`ui/AlertDialog`·`ui/OverlayPane` 으로 옮기고 지웠다. 계획은 `RETIRED` 에 올리는 것이었으나 그 목록은 **파일이 없음**을 보므로 파일 안의 함수를 셀 수 없었다 | +5 | ✅ T054 |

## 단언 수 기록

| 시점 | 테스트 파일 | 단언 | 무른 단언 | 건너뜀 | 증감 사유 |
|---|---|---|---|---|---|
| 전환 전 (baseline) | 110 | 2148 | 639 | 0 | — |
| Foundational 끝 (2026-09-15) | 113 | **2184** (+36) | **640** (+1) | 0 | 새 가드 `UiSkin`·`RawElements`·`ScreenSweep` 과 넓힌 `FocusRing`. 무른 단언 +1 은 `ScreenSweep` 의 「보고서가 있다」(`not.toBeNull()`) — 파일이 없을 때 뒤따르는 단언들이 `undefined` 를 상대로 헷갈리는 메시지를 내지 않게 먼저 묻는 자리이며, 구체 값은 바로 다음 단언(digest 일치)이 본다 |

| US1 끝 (2026-09-15) | 113 | **2197** (+13) | 640 (±0) | 0 | `ToastPlacement` 에 알림 층 높이·배제 조건·복사본 없음·띠 표식·`aria-live` 단언 · `NoticesAreToasts` 세션 경우를 「한 자리가 말한다 · 복귀 조작 하나」로 |
| US2 4-A·4-B 끝 (2026-09-15) | 113 | **2203** (+6) | 640 (±0) | 0 | G-B 가 조립 조합의 한 낱말짜리 값을 읽는지 자체 점검(+1 · T029) · 템플릿 구멍 판정 자체 점검 4 + 전수 1(+5 · N-04). 화면 전환(원시 요소 77 → 부품)에서 **바꾼 단언은 없다** — 테스트가 역할·이름·`data-*` 로 찾으므로 부품이 감싸도 그대로 통과했다 |
| US2 4-C 끝 (2026-09-15) | 116 | **2236** (+33) | 640 (±0) | 0 | 새 동작 테스트 `DialogFocus`(7 검사) · `ToastOverModal`(4) · `MirrorInputWithDialog`(2) · `ImplementationCount` 이름 단위 퇴역(+5). 새 파일의 첫 판에 무른 단언 7개(`toBeDefined` · `not.toBeNull`)가 있었다 — `data-state`·`aria-live`·`role` 의 **구체 값**으로 바꿔 무른 단언을 늘리지 않았다. 대화상자 전환에서 **바꾼 기존 단언은 없다** — 확인 창을 누르는 두 파일(`SaveNamePrompt`·`TestDefinition`)이 `document.querySelector` 로 찾아 포털과 `aria-hidden` 의 영향을 받지 않았다 |
| US2 4-D 끝 (2026-09-15) | 117 | **2252** (+16) | **639** (−1) | 0 | 새 동작 테스트 `MenuKeyboard`(7 검사 — Enter·Space·↓ 로 열기 · 화살표 · Esc 복귀 · 항목 선택 · 실제 행 단추의 `aria-haspopup`·`aria-expanded`). 무른 단언 −1 은 `RowMenuVisible` 의 「메뉴가 열렸다」를 `not.toBeNull()` 에서 `data-state` 값으로 바꾼 것 |

## 새로 더하는 테스트

| 파일 | 무엇을 보는가 | 요구 |
|---|---|---|
| `UiSkin.test.ts` | 부품의 모습 가드 (G-F) | FR-029 · SC-010 |
| `RawElements.test.ts` | 원시 요소 예산 (G-G) | FR-030 · SC-005 |
| `ScreenSweep.test.ts` | 순회 보고서의 낡음·0건·범위 | FR-025 · SC-001~SC-003 |
| `DialogFocus.test.tsx` | 대화상자·확인 대화상자의 초점 이동·가두기·Esc·되돌림, 알림 층 클릭이 닫힘이 아님 | FR-011 · SC-009 |
| `MenuKeyboard.test.tsx` | 행 메뉴 키보드 열기·화살표·Esc | FR-012 |
| `ToastOverModal.test.tsx` | 모달이 열린 동안 알림 층이 `aria-hidden` 이 아니고 눌린다 | research R6 ③④ |
| `MirrorInputWithDialog.test.tsx` | 대화상자가 열린 동안 미러로 가는 입력 0, 닫힌 뒤 한글 조합 입력 경로 유지 | FR-016 · SC-013 |
