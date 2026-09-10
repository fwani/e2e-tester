# Phase 0 — 조사: 작성 화면의 저장·선택·삭제·기록

**대상**: [spec.md](spec.md) · FR-360~FR-398 (50건) · SC-600~SC-613 (17건)

이 문서가 답하는 것은 하나다 — **7건의 보고를 고칠 때, 이미 있는 구조 중 무엇을 쓰고 무엇을
새로 만드는가.** 이 저장소는 007·008·009·010 을 거치며 자리 문법과 조작 표를 정본으로 모아
왔다. 그 정본을 우회해 고치면 다음 화면에서 같은 문제가 다시 생긴다.

각 항목은 **코드에서 확인한 사실**로 시작한다. 사실 없이 결정을 적지 않는다.

---

## R1. 저장·이름을 어디로 옮기는가

**확인한 사실**

| 무엇 | 어디 | 지금 상태 |
|---|---|---|
| 저장 버튼·이름 칸 | `components/workbench/ActionPalette.tsx` | Step 패널(우측 460px) 바닥. 이름 → 시작 주소 → AI 지시문 → 저장 순 |
| 국면 띠 | `components/workbench/PhaseBar.tsx` | 48px. 국면 알약 → 테스트 이름 → 진행 → 결말 요약 → **주요 조작** |
| 조작의 집 표 | `specs/007-unify-test-screens/contracts/ui-contract.md` §4-1 | 「국면 띠 = `run.*`」, 「팔레트 = 나머지 전부 (…저장)」 |
| 자리 검사 | `frontend/tests/CapabilityUI.test.tsx` | `data-action` 을 세어 "감춰진 조작 0건" 과 "한 조작에 한 자리" 를 확인 |

국면 띠는 **이미 테스트 이름을 그린다** (`PhaseBar.tsx` 의 `.phase-name`, `maxWidth: 300`).
즉 이름이 화면에 두 번 있다 — 국면 띠의 표시와 팔레트의 입력칸.

**결정**

- `save`·`edits.revert`·`test.rename` 의 집을 **국면 띠**로 옮긴다. 조작의 집 표를 고친다.
- `test.rename` 은 국면 띠의 **기존 이름 표시를 그 자리에서 고치는 형태**로 만든다. 새 입력칸을
  더하는 것이 아니라 표시와 입력을 하나로 합치는 것이다 — 이름이 화면에 두 번 있던 것이 그대로
  해소된다.
- `test.setStartUrl` 과 `ai.compose` 는 **팔레트에 남긴다.** 국면 띠에 표시되지 않는 값이므로
  "보이는 곳에서 고친다" 논리가 성립하지 않고, 국면 띠는 48px 한 줄이라 긴 URL 을 담을 수 없다.

**대안과 기각 사유**

| 대안 | 기각 사유 |
|---|---|
| 헤더(60px)에 저장 | 헤더의 집은 이동(`nav.*`·`session.open`·`result.show`)이다. 저장을 이동 옆에 두면 「나가기」와 「저장」이 같은 묶음이 되어 잘못 누른다 |
| 이름 변경을 대화상자로 | 이름을 고치려면 항상 한 번 더 눌러야 한다. 지금 문제가 「저장할 때 이름을 묻는다」인데 대화상자는 그것을 조작으로 고정한다 |
| 팔레트에 그대로 두고 스크롤만 개선 | 보고 1번은 "스크롤이 길다" 가 아니라 "자리가 불편하다" 다. 자리를 안 옮기면 안 고친 것이다 |

**따라오는 일**: `PhaseBarWidth.test.tsx` 가 국면 띠의 폭 회귀를 잡고 있다. 조작이 늘면 그 검사가
먼저 깨지므로, 조작 묶음의 `flex: 0 1 auto` 축소 규칙(이미 있다)을 이름 입력칸에도 적용해야 한다.

---

## R2. 이름을 다시 묻는 곳은 정확히 어디인가

**확인한 사실** — 세 곳이다.

| # | 위치 | 조건 | 지금 동작 |
|---|---|---|---|
| 1 | `SessionScreen.tsx` → `sessionSaveLabel(view.saved_at != null)` | `saved_at` 은 **이 세션에서 저장한 시각**이다 | 저장된 테스트에서 시작한 세션도 첫 저장 전에는 `null` → 라벨이 「저장」이고 이름 칸을 채워야 활성 |
| 2 | `SessionScreen.tsx` `RerunConfirm` (`rerun-save-name`) | 저장하지 않고 다시 실행 | 이름 입력칸을 **무조건** 그린다 |
| 3 | `SessionScreen.tsx` `LeaveConfirm` (`leave-save-name`) | 저장하지 않고 나가기 | 이름 입력칸을 **무조건** 그린다 |

**핵심**: 판정에 쓰이는 값이 틀렸다. `saved_at` 은 "이 세션이 저장을 했는가" 이고, 물어야 할 것은
"이 테스트에 **이름이 이미 있는가**" 다. 후자는 세션 응답에 이미 있다 —
`sessions.py:594` 가 `test_id=w.saved_test_id or w.session.test_id` 로 내려보낸다.

**결정**

- 판정식을 `saved_at != null` → **`test_id != null`** 로 바꾼다. `test_id` 가 있으면 이름이 정해진
  테스트이고, 저장은 「변경 저장」이며 이름을 묻지 않는다.
- `RerunConfirm`·`LeaveConfirm` 은 `test_id === null` 일 때만 이름 입력칸을 그린다.
- 편집 국면(`EditView`)은 원래 이름을 묻지 않는다 (`saveEditsLabel(pending, saving)`).
  **고칠 것이 없다** — 사용자 보고 2번이 실제로 가리킨 것은 편집에서 브라우저를 열어 세션으로
  넘어간 뒤의 경로이며, 그것이 위 세 곳이다.

**대안과 기각 사유**: `saved_at` 을 세션 생성 시점에 채우는 것 — 그러면 "이 세션에서 저장했다"
라는 뜻이 사라진다. 그 값은 저장 확인줄과 「초안」 표시가 쓰고 있어(`wording.ts:366` 주석) 다른
표시가 함께 틀어진다.

---

## R3. Step 상세를 왼쪽으로 옮기면 무엇이 가려지는가

**확인한 사실**

- 자리는 하나다. `lib/layout.ts` 는 `DETAIL_PLACEMENT` 표를 **의도적으로 없앴고**(2026-09-09),
  그 주석이 이유를 적어 두었다 — 같은 것을 보는 자리가 두 곳이면 사용자가 매번 어디를 볼지
  판단해야 한다. 011 은 그 판단을 되돌리지 않는다.
- 폭: 기준 1440px = 대상 앱(남는 폭) + Step 패널 460px. 상세는 640px 겹침.
- 왼쪽으로 옮기면 상세는 `1440 − 460 − 640 = 340px` 지점부터 그려진다. 대상 앱 영역의 **왼쪽
  340px 는 그대로 보인다.**

**결정** (clarify 결정 1)

- 겹침을 유지하고 자리만 오른쪽 → 왼쪽. 상세의 오른쪽 가장자리가 Step 패널의 왼쪽 가장자리에
  붙는다.
- 대상 앱 영역의 **폭을 바꾸지 않는다** (FR-373). 겹침이므로 닫으면 원래대로 드러난다.
- 010 이 미러 조작을 만들었으므로 새 위험이 하나 생긴다 — 상세가 미러 위를 덮고 있는데 그
  아래로 포인터·키 입력이 새면 사용자가 보이지 않는 곳을 조작하게 된다. FR-373b 가 그것을 막는다.

**대안과 기각 사유**: 대상 앱을 밀어 나란히 놓기 — 상세가 닫혀 있는 시간이 열려 있는 시간보다
길다. 상시 340px 를 잃는 대신 볼 때만 가리는 쪽이 총비용이 작다. 사용자도 이 쪽을 택했다.

---

## R4. 한 행에 표시해야 하는 상태가 넷이 됐다

**확인한 사실** — `StepList.tsx` 의 `StepRow` 는 세 상태를 **한 클래스 자리**에 배타적으로 넣는다.

```
className={`srow ${step.isPausedHere ? "paused" : selected ? "sel" : OUTCOME_MARK[step.outcome]}`}
```

결과: 통과한 Step 을 고르면 `sel` 이 `pass` 를 밀어내 **결말이 사라지고**, 일시정지 행은
골라도 `paused` 가 이겨 **선택이 보이지 않는다.** 이것이 보고 7번의 실체다.

칸 구성은 `[번호 26][이름 1fr][시간 58][결말 20][조작]` 이고, 정본 격자(`.srow`)가 갖는다.
`StepRowLayout.test.tsx` 가 칸을 센다.

**결정** — 네 상태에 **각각 다른 자리**를 준다 (FR-371).

| 상태 | 자리 | 근거 |
|---|---|---|
| 결말 | 행 왼쪽 3px 표식 + 오른쪽 칸의 형태 아이콘 | 008 이 정한 짝. 바꾸지 않는다 |
| 일시정지 | `data-paused-here` 속성 + 전용 표식 | 이미 속성으로 말하고 있다 |
| 지목(상세 열림) | **새 축** — 행 배경 + `aria-current` | 왼쪽 3px 를 다투지 않는다 |
| 삭제 대상 | **새 칸 0** — 체크 칸 | clarify 결정 2 |

즉 칸 구성이 `[체크 22][번호 26][이름 1fr][시간 58][결말 20][조작]` 이 된다.

**주의 — 008 이 이미 겪은 함정**: `OutcomeMark` 의 `pending` 이 빈 사각형이던 시절 "체크박스로
읽혔다" 는 기록이 `StepList.tsx` 주석에 있다. 이제 **진짜 체크 칸이 생기므로** 결말 아이콘과
체크 칸이 서로 다른 형태·다른 칸에 있어야 한다. 결말 아이콘은 이미 체크(✓)를 쓰고 있어, 체크
칸은 사각형 계열로 가야 한다.

---

## R5. 복수 삭제 — 절반은 이미 있다

**확인한 사실**

| 경로 | API | 원자성 |
|---|---|---|
| 저장된 테스트 편집 | `PUT /api/tests/{id}/definition` — 본문이 **편집 연산 목록**(`edits: [...]`) | 목록 전체가 한 번에 적용된다. `delete` 연산을 여러 개 넣으면 **이미 원자적 복수 삭제다** |
| 세션(일시정지·검토) | `DELETE /api/sessions/{id}/steps/{step_id}` — 하나씩 | 없다. N번 호출해야 하고 중간에 끊기면 부분 적용 |

즉 **백엔드에 새로 만들 것은 세션 경로 하나뿐이다.**

**결정**

- 세션에 배치 삭제를 더한다: `POST /api/sessions/{id}/steps:delete`, 본문 `{ step_ids: [...] }`.
  메모리 상 Step 목록을 **한 번에** 교체해 부분 적용을 만들지 않는다 (FR-388).
- 편집 경로는 라우트를 더하지 않는다. 화면이 `edits` 에 `delete` 를 여러 개 실어 보낸다.
- 「이 뒤 전부」는 **서버 개념이 아니다.** 화면이 지목 이후의 Step id 를 모아 위 두 경로에
  그대로 싣는다. 서버에 범위 개념을 넣으면 "그 사이 목록이 바뀌면 무엇을 지우는가" 가 서버와
  화면 양쪽에 생긴다.

**대안과 기각 사유**: `DELETE` 에 `step_ids` 를 쿼리로 싣기 — 목록이 길면 URL 길이 제한에 걸리고,
삭제 대상을 URL 에 남기는 것은 로그에 그대로 남는다. `POST …:delete` 는 이 저장소가 이미 쓰는
형태다 (`steps:manual`, `steps:reorder`).

---

## R6. Step 별 스크린샷 — 보관 정책이 저장소 구조와 이미 맞는다

**확인한 사실**

| 무엇 | 어디 | 지금 |
|---|---|---|
| 촬영 | `execution/artifacts.py` `_write_screenshot` | **실행당 1장**. 실패 시점 페이지에서만 |
| 저장 위치 | `.runs/<테스트ID>/failure.png` | `repository.py:9` 주석: 「.gitignore 대상, **최근 1건만**」 |
| 결과 모델 | `domain/run_result.py` `Artifacts.failure_screenshot` | 실행 전체에 하나 |
| 서빙 | `GET /api/tests/{id}/result/artifacts/{kind}` | `kind ∈ {screenshot, console, network, trace}` |
| 민감 값 | `_contains_secret` | PNG 는 치환 불가 → **들어 있으면 쓰지 않고 사유만 남긴다** |
| 초안 세션 | `paths.draft_run_dir` = `.runs/_draft` | 테스트 ID 가 없는 세션용 |

**핵심 발견**: clarify 결정 3(「테스트당 최근 실행 1회분만」)이 **이미 저장소가 하고 있는 일**이다.
`run_dir` 은 테스트당 하나이고 결과를 덮어쓴다. 새 정책을 만드는 것이 아니라, Step 별 파일에도
같은 규율을 적용하면 된다.

**결정**

- 촬영 지점: `execution/step_executor.py` — Step 이 끝나고 **`duration_ms` 를 확정한 뒤**에 찍는다.
  촬영 시간이 시간 초과 판정에 들어가지 않는다 (FR-395).
- 저장 위치: `.runs/<테스트ID>/steps/<0기반 index>.png`. 초안은 `.runs/_draft/steps/`.
- 보관: 실행 **시작 시** `steps/` 디렉터리를 비운다. 실행마다 Step 개수·인덱스가 달라지므로
  덮어쓰기만으로는 이전 실행의 남은 파일이 섞인다 (FR-396a).
- 결과 모델: `StepResult` 에 `screenshot: str | None = None` 과 `screenshot_note: str | None = None`
  을 더한다. 둘 다 기본값이 있으므로 **기존 결과 파일이 그대로 읽힌다** (SC-613).
- 실패 Step: 기존 `failure.png` 와 같은 화면이므로 **파일을 두 벌 만들지 않는다.** 실패 Step 의
  `screenshot` 은 `failure.png` 의 상대 경로를 가리킨다 (FR-394).
- 서빙: `kind` 를 늘리지 않고 새 경로를 판다 —
  `GET /api/tests/{id}/result/steps/{index}/screenshot`. `kind` 표는 "실행 전체의 산출물" 이고
  Step 별은 인덱스를 갖는 다른 성질이다. 경로 검증(프로젝트 루트 밖 거절)은 기존 함수를 쓴다.
- 민감 값: `_contains_secret` 규칙을 그대로 승계한다. 들어 있으면 쓰지 않고 `screenshot_note` 에
  사유를 남긴다 (FR-392).

**대안과 기각 사유**

| 대안 | 기각 사유 |
|---|---|
| Step 시작 시점에도 찍기 | 앞 Step 의 끝 화면과 같다. 장수만 두 배 |
| `kind` Literal 에 `step_screenshot` 추가 | 인덱스를 어디에 실을지가 없다. 쿼리로 실으면 `kind` 마다 다른 매개변수를 갖게 된다 |
| 한 장으로 이어 붙인 시트 | 부분 실패·건너뜀에서 어느 칸이 어느 Step 인지 대응이 깨진다 |
| 실행당 장수 상한 | 사용자가 상한을 두지 않기로 정했다 (clarify 결정 3). 누적은 「최근 1회분」이 막는다 |

---

## R7. 지시문으로 Step 더하기 — 막는 것은 권한표 한 줄이다

**확인한 사실**

- `lib/capabilities.ts` 의 `editing` 행:
  `"step.recordStart": off("NEEDS_BROWSER", "browser.openAt")`,
  `"step.addNaturalLanguage": off("NEEDS_BROWSER", "browser.openAt")`.
  둘 다 같은 이유로 잠겨 있고 해소 방법도 같다.
- `EditView.tsx` 에 `openBrowser()` 가 이미 있고(457~480행), 저장하지 않은 변경이 있으면
  「저장하고 열기」를 먼저 확인한다 (FR-203, `save-before-browser` 알림).
- 즉 **필요한 부품이 전부 있다.** 사용자가 두 단계로 나눠 하고 있을 뿐이다.

**결정** (clarify 결정 4)

- `editing` 행의 두 조작을 `ON` 으로 바꾸고, 실행 시 `openBrowser()` 를 앞에 붙인다.
- 저장하지 않은 변경이 있으면 기존 「저장하고 열기」 확인이 그대로 걸린다 (FR-374b) — 새 확인을
  만들지 않는다.
- 브라우저 열기가 실패하면 지시문 수행을 시작하지 않고 사유를 알린다 (FR-374c).
- `step.recordStart` 도 같은 규칙으로 맞춘다. 둘 중 하나만 자동으로 열면 대등성이 다시 깨진다.

**주의**: `capabilities.ts` 의 `off("NEEDS_BROWSER", …)` 를 지우면 `CapabilityCoverage.test.ts` 가
그 사유 문자열의 쓰임을 세고 있을 수 있다. 다른 국면에서 쓰이지 않게 되면 문구를 정리해야 한다
(010 T092 와 같은 성격의 일이다).

---

## R8. 이 기능이 고쳐야 하는 기존 검증

자리와 표를 바꾸므로 **정본을 세는 검사가 먼저 깨진다.** 그것이 정상이고, 함께 고치는 것이 작업의
일부다. 조용히 지우면 안 된다 (헌법 §품질 게이트 4).

| 검사 | 왜 깨지는가 |
|---|---|
| `frontend/tests/CapabilityUI.test.tsx` | 저장·이름의 자리가 팔레트 → 국면 띠 |
| `frontend/tests/CapabilityCoverage.test.ts` | `editing` 행의 두 조작이 `off` → `ON` |
| `frontend/tests/StepRowLayout.test.tsx` | 칸이 넷 → 다섯 (체크 칸 신설) |
| `frontend/tests/StepRowActions.test.tsx` | 행 조작 옆에 체크 칸이 생긴다 |
| `frontend/tests/PhaseBarWidth.test.tsx` | 국면 띠에 조작·입력칸이 는다 |
| `frontend/tests/SaveFeedback.test.tsx` | 저장 라벨 판정식이 `saved_at` → `test_id` |
| `frontend/tests/RunResult.test.tsx` | 결과 화면에 Step 별 스크린샷 자리가 는다 |
| `frontend/tests/VisualLanguage.test.tsx` · `CanonMatchesDesign.test.ts` | 새 표시(지목·체크)가 정본 토큰을 써야 한다 |
| `backend/tests/contract/test_schema_drift.py` | `StepResult` 에 필드 둘이 는다 |
| `specs/007-unify-test-screens/contracts/ui-contract.md` §4-1 | 조작의 집 표에서 저장·이름이 옮겨간다 |

---

## R9. 무엇을 하지 않는가

- **국면을 더하거나 없애지 않는다.** `lib/phase.ts` 의 열 국면은 그대로다.
- **`DETAIL_PLACEMENT` 표를 되살리지 않는다.** 상세 자리는 국면과 무관하게 하나다.
- **Step DSL 을 바꾸지 않는다.** 스크린샷은 실행 **결과**에 붙는 것이지 정의에 붙지 않는다.
  원칙 I·V 에 영향이 없다.
- **재생 경로에 LLM 을 들이지 않는다.** 지시문으로 더한 Step 은 작성 시점에 결정적 Step 으로
  컴파일된다 — 기존 규칙 그대로다 (원칙 II).
- **행 조작(`↑ ↓ + ×`)을 없애지 않는다.** 복수 삭제는 그것을 **더하는** 것이지 대체가 아니다.
  한 개를 지우는 데 체크하고 버튼을 찾는 것은 지금보다 나쁘다.
