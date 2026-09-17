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
| `PacingControl.test.tsx` | 고른 실행 속도가 남는다 | `aria-pressed` → `role="radio"` + `aria-checked` | `ToggleGroup type="single"` 은 배타 선택을 라디오로 알린다 (FR-013) | 4→4 | ✅ T060 — `aria-pressed` 4곳 → `aria-checked`. 누르기는 `fireEvent.click` 그대로 통과(토글 항목은 클릭으로 고른다) |
| `RunnerPacing.test.tsx` | 실행 중에 바꾼 속도가 남는다 | 같음 | 1→1 | ✅ T060 — `aria-pressed` 1곳 → `aria-checked` · 머리주석의 같은 문장 |
| `NoticesAreToasts.test.tsx` | 목록의 알림이 내용을 밀어내지 않고 한 층에 뜬다 | 진행 중 세션 경우 — 토스트가 아니라 **흐름 안 띠 하나**가 그 사실을 말함을 확인한다 | B-02 · FR-018b. 같은 사실을 두 자리가 말했다 | 2→5 (세션 경우) | ✅ T023 |
| `ListLiveState.test.tsx` · `RecheckPhase12.test.tsx` | 실행 중·끝난 세션이 있을 때 목록에서 **실행 화면으로 돌아갈 수단이 있다** (005 FR-168) | 복귀 조작을 토스트의 「실행 화면 보기」가 아니라 띠의 「이어서 보기」로 찾는다 | B-02 — 같은 `onResumeSession` 을 부르는 조작이 한 화면에 둘이었다. 008 이 적은 「복귀 조작은 화면에 하나뿐」(`TestList.tsx:1368`)을 되살린다. 문구는 바꾸지 않는다 (spec Assumptions) | 1→1 · 1→1 | ✅ T023 |
| `ToastPlacement.test.tsx` | 알림 층이 한 자리(오른쪽 위)에 뜬다 | **더한다**: 층 클래스가 띠 조건 셋을 서로 배제하는 형태로 갖는다 | B-01. `top` 을 고정하는 테스트가 없어 회귀가 들어왔다 | 5→16 | ✅ T019 |
| `WorkbenchShell.test.tsx` | 작업 화면 틀이 1440 을 최소로 창을 채운다 | 틀 구조 — 머리띠가 가로 스크롤 영역 밖, 본문이 `min-width 1440 · width 100%` | 같음 | 불필요 (T070) — 머리띠를 `Artboard` 의 `header` 인자로 옮겼지만 틀 검사가 역할·표식으로 찾아 그대로 통과 |
| `WorkbenchHeight.test.tsx` | 작업 화면이 창 높이에 맞고 Step 목록이 스크롤 영역이다 | 높이 인라인 읽기 자리 조정 (머리띠가 밖으로 나온 뒤의 요소) | 같음 | 불필요 (T070) — 창 높이에 묶는 선언(`height:100dvh`)이 세로 배치 상자에 그대로 남는다 |
| `VerticalSplit.test.ts` · `TargetPane.test.tsx` · `ComposePhase.test.tsx` | 국면별 대상 앱 자리의 배치 판단 | 만들기 국면의 `targetSlot` 기대값 `fixed(88)` → `content` | 2→2 | ✅ T073 — **바꾼 것은 `ComposePhase` 의 두 단언뿐**(`targetSlot.kind`·`data-slot-size` 를 `fixed` → `content`). `VerticalSplit`·`TargetPane` 은 표에서 기대값을 읽으므로 그대로 통과. 판단이 바뀐 근거: 순회 `test-create` 의 세로 넘침(B-04) — 88px 는 한 줄 안내를 위해 잰 값이었고 만들기 국면은 세 줄 안내를 그린다 |
| `StepRowLayout.test.tsx` · `SavePlacement.test.tsx` · `RerecordBandPlacement.test.tsx` | Step 패널 머리·바닥의 구성 | 바닥 상한을 배치 표에서 읽는 형태로 | 같음 | 불필요 (T072) — 바닥 상한을 `lib/layout.ts` 표에서 내려받게 바꿨지만 세 파일은 바닥의 **존재와 자리**를 보므로 그대로 통과 |
| `DetailPlacement.test.tsx` · `DetailBlocksMirrorInput.test.tsx` | Step 상세 판의 자리·미러 입력 차단 | 판이 `DetailPanel`(비모달 Dialog) 로 그려진 뒤 같은 속성을 읽는다 | 같음 | 불필요 (T052) — 판을 `data-workbench-step-detail` 로 찾으므로 `DetailPanel` 로 그린 뒤에도 그대로 통과 |
| `DesignTokens.test.tsx` · `InteractionStates.test.tsx` · `FocusRing.test.tsx` | 부품이 정본 치수·상태·초점을 지킨다 | 부품 파일이 `cva` 형태로 바뀐 뒤 찾는 문자열 갱신. 경로(`src/ui/*.tsx`)는 그대로 | FocusRing 4→6 · InteractionStates 1→4 · DesignTokens 같음 | ✅ — `FocusRing` 은 넓혔고(T013 · 넓힌 가드 표), `InteractionStates` 는 탭·분절 띠 검사가 `ui/Tabs`·`ui/ToggleGroup` 으로 옮겨졌다(T062). `DesignTokens` 는 판정을 바꾸지 않고 통과 — 부품이 `cva` 가 되어도 찾는 문자열(`overflow-x-auto` · 치수 토큰)이 그대로였다 |
| `ClassConflict.test.ts` | 나중에 적은 클래스가 진다 | 헬퍼가 `cva`·`cn` 을 읽는다 (guards H-1) | 그대로 | ✅ T012 (Foundational) |
| `ImplementationCount.test.ts` | 구현이 또 한 벌 생기지 않는다 | `RETIRED` 에 옛 모달·수제 메뉴·옛 겹침 판 추가 | 옛 구현 삭제를 센다 | +5 | ✅ T054·T056 — `RETIRED` 는 파일 존재를 보므로 **이름 단위 퇴역 목록**을 새로 뒀다 (넓힌 가드 표) |
| `ImportPreview.test.tsx` · `InlineSecret.test.tsx` · `TestGroups.test.tsx` | 선택칸으로 고른 값이 반영된다 | **변경 없음 예상** — `NativeSelect` 는 실제 `<select>` 다 | 같음 | 불필요 (T038·T045·T047) — 예상대로 그대로 통과 |
| `StepRowActions.test.tsx` · `RerecordStart.test.tsx` · `DeleteOutcome.test.tsx` | 체크박스로 고른 Step | **변경 없음 예상** — `Checkbox` 는 실제 `<input type=checkbox>` 다 | 같음 | 체크박스는 불필요(예상대로). **`DeleteOutcome` 은 행 메뉴 때문에 바뀌었다** (T056) — 메뉴를 `userEvent.click` 으로 열고, 메뉴의 「삭제」를 `menuitem` 으로 찾는다. 두 「삭제」(메뉴 항목 · 행 안 확인 단추)가 이제 역할로 갈린다 |
| 확인 대화상자를 여는 화면 테스트 (`SaveNamePrompt` · `RunTrigger` · `RunFinished` · `PauseTransition` 등) | 확인 후의 동작 | 대화상자가 열린 동안 뒤쪽 요소를 `getByRole` 로 찾던 순서를 **닫은 뒤**로 | 같음 | 불필요 (T050·T051) — 확인 창을 누르는 `SaveNamePrompt`·`TestDefinition` 이 `document.querySelector` 로 찾아 포털·`aria-hidden` 의 영향을 받지 않았다 |
| `BeforeAfterParity.test.ts` | 전환 전후 화면이 같다 | 보고서 갱신 · `INTENDED` 추가 | 그대로 | ✅ 매 단계 — 4-B 에서 의도된 차이 106건(버튼 `.btn` 배치 · B-08) 등록. L2 단계 누르기가 전환 뒤의 `radio` 도 누르도록 넓혔다 (T061) |
| `TestListFilters.test.tsx` | 결말 필터 넷이 있고 누르면 목록이 걸러지며 개수는 거르기 전 전체다 | 필터 항목을 역할 `button` → `radio` 로, 묶음을 `group` → `radiogroup` 으로 찾는다. 정렬 단추는 그대로 | 넷 중 하나를 고르는 묶음이라는 사실이 보조기술에 들린다 (FR-013) | 같음 | ✅ T061 |
| `TestGroups.test.tsx` | 그룹 칩으로 거르고 그룹 조작이 고른 상태에서만 나온다 | 칩 12곳을 역할 `radio` 로 찾는다. 「+ 그룹」·「이름 바꾸기」·「그룹 없애기」는 그대로 `button` | 같음 | 같음 | ✅ T061 |
| `TestListSelection.test.tsx` · `ListLiveState.test.tsx` | 걸러 보기와 선택 · 실행 중 행 | 필터 항목을 역할 `radio` 로 (2곳 · 1곳) | 같음 | 같음 | ✅ T061 |
| `AiRecord.test.tsx` | 만들기 국면에서 AI 로 만들기를 고르면 지시문 자리가 나온다 | 「AI로 만들기」 카드를 역할 `radio` 로 | 둘 중 하나를 고르는 카드 묶음 | 같음 | ✅ T061 |
| `InteractionStates.test.tsx` | 비활성 탭(S-11)이 활성과 구별된다 | 찾는 곳 `ui/Table`(`[&>button:disabled]`) → `ui/Tabs`(`disabled:border-solid`·`disabled:text-ink-3`). **더한다**: `ui/ToggleGroup` 분절 띠의 비활성 표시(S-12)와 「고른 색은 쓸 수 있을 때만」 | 탭·분절 띠가 부모 규칙에서 자기 부품으로 옮겨졌다 | 1→4 | ✅ T062 |

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
| `UiSkin.test.ts` (G-F) | 부품의 모습이 정본이다 | **파일이 없어도 요구한다** — `behavior = radix` 부품 여섯이 있고 `radix-ui` 를 가져오는지 · 조작 부품 넷이 있는지. 전환 중에는 「파일이 생긴 뒤부터」였다 | — (전환이 끝나 조건만 굳혔다) | 6→10 | ✅ T077 |
| `ScreenSweep.test.ts` | 순회 보고서가 낡지 않고 깨짐이 남지 않았다 | 「남은 알려진 깨짐이 전환 전 실측의 것뿐인가」(기록) → **알려진 깨짐 등록부와 남은 검출이 비어 있다**(단언) | — (B-01~B-11 을 전부 고쳐 등록부를 비웠다) | 1→2 | ✅ T078 |

## 단언 수 기록

| 시점 | 테스트 파일 | 단언 | 무른 단언 | 건너뜀 | 증감 사유 |
|---|---|---|---|---|---|
| 전환 전 (baseline) | 110 | 2148 | 639 | 0 | — |
| Foundational 끝 (2026-09-15) | 113 | **2184** (+36) | **640** (+1) | 0 | 새 가드 `UiSkin`·`RawElements`·`ScreenSweep` 과 넓힌 `FocusRing`. 무른 단언 +1 은 `ScreenSweep` 의 「보고서가 있다」(`not.toBeNull()`) — 파일이 없을 때 뒤따르는 단언들이 `undefined` 를 상대로 헷갈리는 메시지를 내지 않게 먼저 묻는 자리이며, 구체 값은 바로 다음 단언(digest 일치)이 본다 |

| US1 끝 (2026-09-15) | 113 | **2197** (+13) | 640 (±0) | 0 | `ToastPlacement` 에 알림 층 높이·배제 조건·복사본 없음·띠 표식·`aria-live` 단언 · `NoticesAreToasts` 세션 경우를 「한 자리가 말한다 · 복귀 조작 하나」로 |
| US2 4-A·4-B 끝 (2026-09-15) | 113 | **2203** (+6) | 640 (±0) | 0 | G-B 가 조립 조합의 한 낱말짜리 값을 읽는지 자체 점검(+1 · T029) · 템플릿 구멍 판정 자체 점검 4 + 전수 1(+5 · N-04). 화면 전환(원시 요소 77 → 부품)에서 **바꾼 단언은 없다** — 테스트가 역할·이름·`data-*` 로 찾으므로 부품이 감싸도 그대로 통과했다 |
| US2 4-C 끝 (2026-09-15) | 116 | **2236** (+33) | 640 (±0) | 0 | 새 동작 테스트 `DialogFocus`(7 검사) · `ToastOverModal`(4) · `MirrorInputWithDialog`(2) · `ImplementationCount` 이름 단위 퇴역(+5). 새 파일의 첫 판에 무른 단언 7개(`toBeDefined` · `not.toBeNull`)가 있었다 — `data-state`·`aria-live`·`role` 의 **구체 값**으로 바꿔 무른 단언을 늘리지 않았다. 대화상자 전환에서 **바꾼 기존 단언은 없다** — 확인 창을 누르는 두 파일(`SaveNamePrompt`·`TestDefinition`)이 `document.querySelector` 로 찾아 포털과 `aria-hidden` 의 영향을 받지 않았다 |
| US2 4-D 끝 (2026-09-15) | 117 | **2252** (+16) | **639** (−1) | 0 | 새 동작 테스트 `MenuKeyboard`(7 검사 — Enter·Space·↓ 로 열기 · 화살표 · Esc 복귀 · 항목 선택 · 실제 행 단추의 `aria-haspopup`·`aria-expanded`). 무른 단언 −1 은 `RowMenuVisible` 의 「메뉴가 열렸다」를 `not.toBeNull()` 에서 `data-state` 값으로 바꾼 것 |
| US2 4-E 끝 (2026-09-15) | 117 | **2255** (+3) | 639 (±0) | 0 | `InteractionStates` 의 탭 비활성 검사가 `ui/Tabs` 로 옮겨지며 분절 띠(S-12) 검사를 더했다(1→4). 고르기 단추의 역할이 `radio` 가 되며 **판정 방법만** 바뀐 파일 8개(PacingControl·RunnerPacing·TestListFilters·TestGroups·TestListSelection·ListLiveState·AiRecord·ComposePhase 는 그대로 통과)는 단언 수가 같다 |
| US2 4-F·4-G 끝 (2026-09-15) | 118 | **2270** (+15) | 639 (±0) | 0 | 새 `TooltipDisclosure`(6 검사 · 14 단언) · `ImplementationCount` 이름 단위 퇴역에 수제 펼침 토글(+1). 툴팁·펼침 전환과 클래스 잇기(`cn`) 전환에서 **바꾼 기존 단언은 없다** — 알림 `×` 는 글자 `×` 와 이름 「알림 닫기」를 그대로 지켰다 (`ToastDismiss`) |
| US3·US4 끝 (2026-09-15) | 118 | **2274** (+4) | 639 (±0) | 0 | `UiSkin` 파일 존재 요구(+3) · `ScreenSweep` 등록부가 비었다는 단언(+1). 배치 수정에서 **판정 방법이 바뀐 것**은 `ComposePhase` 의 단언 둘뿐(`fixed` → `content` · B-04). 최종: 기준선 2148 대비 +126, 무른 단언은 기준선 639 와 같다 |
| 브라우저 확인 끝 (2026-09-15) | 118 | **2275** (+1) | 639 (±0) | 0 | `TestListActions` 「「이름」을 고르면 이름 칸이 초점을 받는다」(+1 · N-08). 실제 브라우저에서 찾은 017 회귀를 붙잡는다 — 고침을 빼고 돌려 **실패함을 확인**했다. 기존 단언은 바꾸지 않았다 |

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
| `TooltipDisclosure.test.tsx` | 툴팁이 키보드 초점·포인터에 뜨고 Esc 로 닫힌다 · 잘린 글자만 초점을 받고 전체 문구를 보인다 · 네이티브 요약 줄이 펼침을 바꾸고 표식 글자는 낭독에서 빠진다 | FR-019 · ui-parts §4 (T063·T065 · 계획에 없던 파일 — 부품 테스트) |

## 예상되는 변경 — 2026-09-16 갈래 교체 (Radix → Base UI)

**「예상」은 확정이 아니다.** 실제로 고치게 되면 `상태` 를 채우고, 고치지 않아도 통과하면 `불필요` 로 적는다.
**단언 수 기준선은 2275**(무른 단언 639 · 건너뜀 0 · 118 파일 · 1418 건)였다.

**2026-09-16 현재 2274 · 1417 건이다 (−1).** 줄어든 자리는 하나이고 아래 `ToastDismiss` 절에 적혀 있다 —
손으로 만든 밀어내기의 중간 상태(`FLY_MS` 180ms)를 재던 단언이라 부품에는 그 상태가 없다. **그 밖의
이유로는 줄지 않는다**(헌법 Gate 4 · 기준선 2148 은 그대로 넘는다). 무른 단언은 639 에서 늘지 않는다 —
T104 에서 새 검사에 `not.toBeNull()` 을 썼다가 계수기가 640 으로 잡아, 사유를 등록하는 대신 **굳은
단언으로 바꿨다**(「`bottom-[N px]` 클래스가 하나인가」).

| 파일 | verifies (바뀌면 안 되는 것) | change (판정 방법) | why | 상태 |
|---|---|---|---|---|
| `InteractionStates.test.tsx` | 탭·분절 띠의 상태별 모습이 정본을 따른다 | 찾는 문자 `data-[state=active]:` → `data-[active]:` · `data-[state=on]:` → `data-[pressed]:` | 갈래가 쓰는 상태 속성 이름이 다르다 (research R2 개정 · ui-parts §2) | ✅ T106 — **예상이 정확했다.** 실제로 고친 단언은 분절 띠 쪽 하나(`enabled:data-[state=on]:bg-sunken` → `enabled:data-[pressed]:bg-sunken`)뿐이다 — 탭 쪽은 이 검사가 **부품 소스를 읽는** 방식이라 `ui/Tabs` 의 문자열이 바뀌며 저절로 맞았다 |
| `PacingControl` · `RunnerPacing` | 고른 실행 속도가 남고 보조기술에 알려진다 | `role=radio` + `aria-checked` → 단추 + `aria-pressed` | 새 갈래의 고르기 묶음은 **눌림** 의미다. 대안(라디오 유지)은 research R2 개정에 적었다 | ✅ T106 — **판정 방법이 아니라 계약이 바뀐 자리다.** 「무엇을 골랐는지 남는가」는 그대로지만 「셋 중 하나」라는 뜻을 잃는다(017 T060 이 `aria-pressed`→라디오로 **올렸던** 것을 되돌린다). 사용자 결정(2026-09-16 「Base UI 기준에 맞춘다」) · 두 파일의 **주석도 함께 고쳤다** — 안 고치면 검사가 제 의도를 거꾸로 설명하게 된다. 손실은 ui-parts §4 와 H-10 에 있다 |
| `TestListFilters` · `TestGroups` · `TestListSelection` · `StepInsert` · `ListLiveState` · `AiRecord` | 거르기·그룹 칩·Step 넣기 종류·만드는 방법 카드가 동작하고 고른 것이 알려진다 | 같음 (`radio`/`radiogroup` → 단추/`group`) | 같음 | ✅ T106 — **30곳**(`TestListFilters` 12 · `TestGroups` 12 · `TestListSelection` 2 · `StepInsert` 2 · `ListLiveState` 1 · `AiRecord` 1). 묶음은 부품이 `role:'group'` 을 단다(실측). **`ComposePhase` 는 손대지 않았다** — 예상 목록에 있었으나 역할로 찾는 자리가 없어 그대로 통과했다. 이름으로 찾아 누르는 판정은 전부 그대로다 |
| `MenuKeyboard` · `RowMenuVisible` · `TestListActions` · `EditEntryPoints` · `DeleteOutcome` | 메뉴가 키보드로 열리고 항목이 골라진다 · 「이름」 뒤 초점이 칸에 간다(N-08) | ① 자리 감싸개 선택자(`data-radix-popper-content-wrapper`) → **우리 표식**(`data-slot=menu-positioner`)과 포털(`[data-base-ui-portal]`) ② 열림 표식 `data-state="open"` → **`data-open`** ③ **누른 뒤 메뉴를 기다린다**(5파일) | ①은 남의 내부 이름 대신 우리 표식으로 묻는다 — 실측 사슬 `BODY > [data-base-ui-portal] > [menu-positioner]{position:fixed} > [role=menu]`. ③은 새 갈래가 `mousedown` 에서 열되 **rAF 한 프레임 뒤**에 열기 때문이다(`useClick` 의 「Wait until focus is set on the element」). `userEvent` 는 마이크로태스크까지만 기다린다 — **키보드 길은 rAF 를 안 거쳐** 그쪽 6건이 계속 통과한 것이 단서였다. 역할(`menuitem`)로 찾는 판정과 초점 단언은 **그대로** | ✅ T105 — `EditEntryPoints` 의 「정의 보기가 없다」는 기다림이 생기며 **뜻이 살아났다**(전에는 아직 안 열려서 통과했다) |
| `DialogFocus` | 대화상자 초점 이동·가두기·Esc·되돌림 | ① 열림 표식 `data-state="open"` → **`data-open`**(값 없는 속성) ② Tab 가두기 판정을 「팝업 안에 있는가」 → **「살아 있는 뒤쪽 조작에 앉지 않는가」** | ① 갈래가 쓰는 상태 표식이 다르다 ② 실제 브라우저는 `inert` 로 바깥을 **Tab 순서에서 뺀다**. jsdom 은 `inert` 를 구현하지 않아 그 조작이 순서에 남는다 — 실측(T104): Tab 3회 울타리 `span`(포털 안) · 4회 `body` · 5회 연 단추 → **한 틱 뒤 팝업 안으로 되돌아왔다.** 가려짐 자체는 바로 옆 검사(「뒤쪽 조작은 보조기술에서 가려진다」)가 따로 못 박는다 | ✅ T104 — `data-slot=alert-dialog-overlay` 는 **그대로 뒀다**(Backdrop 이 물려받는다) |
| `ToastOverModal` | 모달이 열린 동안 알림이 낭독되고 눌린다 (R6 ③④) | 열림 표식 `data-state="open"` → **`data-open`** 2곳 | 같음. 그리고 **R6 ④ 의 보호 코드가 없어졌다** — 모달은 **자기 포털 안**에서 시작한 누름만 `outside-press` 로 받고, 알림 층은 body 직계라 열린 동안 `data-base-ui-inert` 를 받는다(T104 실측). `inNoticeLayer` 는 죽은 코드가 되어 지웠다 | ✅ T104 — 검사 문장은 그대로 |
| `MirrorInputWithDialog` | 열린 동안 입력이 미러로 새지 않고, 닫으면 입력 경로가 되살아난다 | `body.style.pointerEvents === "none"` → **바깥이 `aria-hidden`+`data-base-ui-inert` 인가** | Radix 는 body 에 포인터 잠금을 걸었다. Base UI 는 그러지 않고 **스크롤 잠금 + body 직계 자식 inert** 로 막는다(T104 실측). 묻는 것은 그대로 — 열린 동안 바깥이 조작 대상이 아닌가 | ✅ T104 |
| `UiSkin` (G-F) | 동작 층 부품이 **동작을 손으로 다시 짜지 않는다** | 갈래 목록 하나(`RADIX_ALLOWED`) → **파일마다 자기 갈래**(`BASE_PARTS` / `RADIX_PARTS`) | 갈래를 **한 파일씩** 옮기는 동안에도 질문이 살아 있어야 한다. 하나로 뭉뚱그리면 옮긴 파일에서 「radix 를 가져오는가」가 거짓이 되어 **검사를 끄는 쪽으로 몰린다.** 파일마다 자기 갈래를 요구하면 옮기는 중에도 엄격하다 — T107 이 `RADIX_PARTS` 를 비운다 | ✅ T104 |
| `TooltipDisclosure` | 툴팁이 뜨고 Esc 로 닫힌다 | ~~렌더 껍데기에 공급자 하나를 두른다~~ → **팝업을 `role="tooltip"` 대신 우리 표식(`data-slot=tooltip-content`)으로 집는다** (3곳) | **예상이 틀렸다 (2026-09-16).** ① 공급자를 뿌리로 옮길 이유가 없었다 — Base UI 가 없는 부품을 알리는 오류는 `Root`·`Portal`·`Positioner` 셋뿐이라 **공급자는 필수가 아니다**. T063 의 「툴팁마다 공급자」 결정을 그대로 뒀고 껍데기도 건드리지 않았다. ② 대신 예상에 없던 것이 걸렸다: 새 갈래의 팝업에는 **`role="tooltip"` 이 없다**(실측 — 트리거 `aria-describedby=null`, 팝업 `id=null`). **뜨는 것 자체는 그대로**라 판정 방법만 옮겼다 | ✅ T106 — 잃은 연결은 ui-parts §4 에 적었다 |
| `ToastPlacement` · `ToastDismiss` · `ToastOverModal` · `NoticesAreToasts` | 알림이 한 층에 뜨고 · 흐름을 밀지 않고 · 대화상자 위에서 눌리고 · 퇴장 셋을 갖는다 | 층 클래스(`TOAST_LAYER_CLASSES`) 읽기 → 부품의 층 표식(`[data-toast-layer]`)과 관리자 통로. **자리의 실제 판정은 순회가 한다** | 알림이 부품으로 바뀐다 (research R6 개정). 요구는 그대로 | 🔶 `ToastPlacement` 옮김 (T102) — 아래 별도 줄 |

### `ToastPlacement` — **판정 방법이 아니라 판단이 바뀐 자리** (2026-09-16)

017 은 층을 오른쪽 **위**에 두고, 머리띠·국면 띠를 덮지 않도록 문서에 있는 띠를 읽어 `top` 을 세 값으로
갈랐다(B-01). 이 파일의 「띠 조건 셋이 각자의 자리를 갖는다」·「조건이 서로 배제된다」 두 검사가 그
규칙을 붙잡고 있었다.

자리를 **아래**로 내리면서 그 규칙 자체가 없어졌다 — 아래에서는 띠와 겹치지 않는다. 그래서 두 검사를
지우고 **「층이 아래에 있다」**(`bottom-s4` 가 있고 `top-*`·`data-shell` 조건이 없다)로 바꿨다.

| 무엇 | 전 | 후 |
|---|---|---|
| 층을 찾는 법 | `[data-workbench-notice-layer]` (작업대가 그리던 층) | `[data-toast-layer]` (앱 뿌리의 층 하나) |
| 「복사본이 없다」 | 작업대 층의 클래스 문자열이 `TOAST_LAYER_CLASSES` 와 같은가 | **작업대가 층을 아예 그리지 않는다**(0개) · 층은 하나다 |
| 띠 조건 셋 · 서로 배제 | 있음 | **지움** — 자리가 아래로 내려가 띠를 읽을 이유가 없다 |
| 읽는 동안 멈춤 | 층(`[data-workbench-notices]`)에 포인터 | **알림 자체**(`[data-slot=toast]`)에 포인터 — 부품이 그 규칙을 갖는다 |

**판단이 바뀌었으므로 근거를 테스트 밖에도 둔다** (헌법 Gate 4 · plan 「게이트 4」의 넷째 원인):
layout-contract-v3 L2(개정) · research R6(개정) · 순회 `edit-notice` 화면이 옛 자리에서 실제로
덮임을 검출했다는 기록(T097).

### `ToastDismiss` — 퇴장 셋은 그대로, **중간 상태 하나를 뺀다** (2026-09-16)

| 검사 | verifies (그대로) | 무엇을 바꿨나 |
|---|---|---|
| 5초 · 오류도 예외 아님 · 읽는 동안 멈춤 · `×` | 퇴장 셋과 멈춤 | 가져오는 곳만 `ui/Toast` 로 (`TOAST_LINGER_MS` 포함) |
| 밀어내기 손짓 만들기 | — | 움직임을 **두 번** 보낸다. 부품이 첫 움직임에서 출발점을 현재 자리로 다시 잡으므로(iOS 지연 흡수) 한 번만 보내면 이동 거리가 0 이 된다. 실제 손짓은 여러 번 온다 |
| 「충분히 밀면 사라진다」의 **중간 상태** | 충분히 밀면 없어진다 | 「날아가는 동안은 아직 살아 있다」 단언을 **뺀다** — 그 180ms 는 손으로 만든 밀어내기(`useToastDismiss` 의 `FLY_MS`)의 값이었고, 나가는 처리는 이제 부품의 것이다. 요구(2026-09-11 사용자 결정 「밀어서 없앨 수 있다」)는 그대로 |

### 가드가 잡은 것 — **검사를 고치지 않고 코드를 고친 자리 다섯** (2026-09-16)

가드를 넓혀 통과시키지 않았다. 다섯 다 **검사가 옳았다** — 둘은 부품이, 하나는 **내가 쓴 등록부**가,
둘은 **내가 이식한 부품**이 틀렸다.

| 검사 | 무엇을 잡았나 | 어떻게 고쳤나 |
|---|---|---|
| `TestDefinition` 「읽기 전용 알림에 사유가 붙는다」 | 알림은 떴는데 `[data-notice='not-editable']` 로 집히지 않았다 — 새 부품이 표식을 **속성 이름**(`data-notice-not-editable`)으로 바꿔 내보냈다 | 값 있는 표식을 그대로 흘려보내는 통로(`attrs`)를 부품에 되살렸다. 검사는 한 줄도 고치지 않았다 (FR-005 의 통로) |
| `NoticesAreToasts` 「층은 하나다」 · `ToastDismiss` 「닫을 길이 없으면 밀리지도 않는다」 | 알림마다 층이 생겨 둘이 됐고, 닫을 길 없는 알림이 밀려 사라졌다 | 공급자가 없을 때 쓰는 **층 하나**를 모듈이 만들고, 밀어내기는 빈 배열로 껐다. 두 검사 다 원래 문장 그대로 통과 |
| `BeforeAfterParity` 「대조한 칸이 줄었다」 (**등록부를 잡았다**) | 작업대의 알림 층을 지우자 뒤 형제의 자리 번호가 밀려 `test-create` 의 **90 칸이 짝을 잃었고**, 나는 그것을 「의도된 차이」로 등록해 L2 를 통과시켰다. 가드가 대조 칸이 34328→29288 로 줄어든 것을 잡았다 — **「불일치 0」이 대조를 잃어서 쉬워진 것**이었다 | 등록을 지우고 **짝을 되살렸다**(`COLLECT_JS` 의 `DROP` — 없어진 층을 전환 전 나무에서도 빼 번호를 맞춘다). 대조 **34272칸**으로 돌아왔고, 되살린 90 칸에서 드러난 46 건은 전부 US3 줄들이 이미 설명하던 차이라 **자리 번호만 다시 매겼다**. 의도된 차이 307→**188** — 등록부가 줄고 대조가 늘었다 |
| `AuthoringParity` 「지시문이 실려 나간다」 (**내 이식이 만든 회귀를 잡았다**) | 상세 판을 Base UI 로 옮기자 **옆 칸에 치던 글자를 판이 가로챘다** — 「자연어로 Step 추가」에 「장바구니에 담아」를 쳤는데 `'장'` 만 남았다. 부품의 `initialFocus` 가 팝업 참조를 **이르게** 읽어 아무 데도 두지 않다가, 렌더가 더 도는 화면(EditView)에서 **뒤늦게** 초점을 옮긴 탓이다. HEAD 에서 14/14 통과함을 스택으로 확인해 **내가 깨뜨린 것**임을 먼저 못 박았다 | 초점을 **판이 DOM 에 붙는 순간 한 번만** 주는 콜백 참조로 바꿨다(`initialFocus={false}`). 중간에 시도한 마운트 효과는 **이르러서** `panel.current` 가 `null` 이었고 `?.` 때문에 **조용히 아무 일도 하지 않았다** — 계약이 깨진 채 통과할 뻔했다. 이때 「열리면 초점이 판 자체로 간다」를 붙잡는 검사가 **하나도 없다는 것**도 드러나, `DialogFocus` 에 두 검사(판이 초점을 가져온다 · 남의 입력을 먹지 않는다)를 새로 넣었다 (단언 +2 → 2276) |
| `TestListActions` 「「이름」을 고르면 이름 칸이 초점을 받는다」 (**내 고침을 두 번 되돌려 세웠다**) | 행 메뉴를 Base UI 로 옮기자 「이름」 뒤 초점이 칸이 아니라 `body` 에 떨어졌다 — **N-08 회귀**. 이 검사는 2026-09-15 브라우저 확인에서 생긴 회귀 감시였고, 이번에 제 몫을 했다 | 고침 **둘이 먼저 틀렸다**: ① `finalFocus` 로 칸을 가리키기 — 칸은 「이름」을 고른 **결과로** 열리므로 그 시점에 없다(`null`) ② `finalFocus:false` 로 두고 칸의 `autoFocus` 에 맡기기 — 항목을 고르는 방식에 따라 칸이 붙은 **뒤** 메뉴가 풀리며 초점이 문서로 떨어진다. 셋째로 **순서에 기대지 않는 고침**을 했다: `renaming` 이 열리는 그 렌더에서 **우리가** 칸으로 옮기고, `finalFocus` 는 「여는 단추로 되돌리지 마라」만 맡는다 |
| `ImplementationCount` | 구현이 또 한 벌 생기지 않는다 | 이름 단위 퇴역에 `radix-ui`·`asChild`·`useToastDismiss`·`TOAST_LAYER_CLASSES` 추가 | 옛 구현이 되살아나지 않게 | ⬜ |
| `UiSkin` (G-F) | 부품의 모습이 정본이다 | `behavior = base` 인 파일이 `@base-ui/react` 를 가져오는지 · 출처 줄에 **갈래**가 있는지 | guards 개정 | ✅ T099 — 출처 규칙을 **넓혔다**(`shadcn base/<항목>` 추가 · 옛 `new-york-v4` 형식은 그대로 받는다). 좁히지 않았다. **가드가 실제로 잡았다**: 새 알림 부품이 원본의 `outline-none` 을 들고 들어온 것을 「윤곽선 지우기」로 막았다 — 지우고 사유를 주석에 남겼다 |
| `ScreenSweep` | 순회 보고서가 낡지 않고 검출이 0 이다 | 화면 수 기대값 +2 (알림 화면) | screen-sweep SW-5 개정 | ⬜ |

### SC-016 — **초록이 「잡을 수 있어서」인지 확인했다** (2026-09-16 · T108)

검출 0 은 두 가지 중 하나다: 깨진 데가 없거나, **재는 눈이 멀었거나.** 둘을 가르는 길은 하나뿐이다 —
**깨뜨려 보고 잡히는지 본다.**

알림 자리를 017 의 옛 자리(오른쪽 위)로 되돌리고 순회를 돌렸다:

| | 결과 |
|---|---|
| 옛 자리로 되돌림 | `sweep exit 1` · **등록되지 않은 검출 4** — `covered button{전부 고르기} by div{먼저 저장해야 합니다…}` 가 **네 폭 모두**에서 |
| 자리를 되돌리기 취소 | `sweep exit 0` · 검출 0 · `git diff` 비어 있음(파일 원래대로) |

**되살아난 것이 정확히 N-02 다** — T097 이 처음 잡았던 그 검출이 같은 문구로 다시 나왔다. 즉 이 순회는
알림 자리가 조작을 덮는 순간을 **실제로** 잡으며, 지금의 초록은 자리가 옳아서 나온 초록이다.

이것이 「고쳤다 = 검출이 사라진 것」(T097)의 반대 방향 증명이고, 둘을 다 해야 **사라진 것이 고쳐서인지
못 보게 돼서인지** 갈린다. 같은 실수를 이번 Phase 에서 이미 한 번 했다 — L2 의 90 칸을 「의도된 차이」로
등록해 「불일치 0」을 **대조를 잃어서** 얻을 뻔했고, `BeforeAfterParity` 가 잡았다(위 셋째 줄).
