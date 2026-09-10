# 개발 안내

`quickstart.md` §0 의 설치·실행 절차를 개발자 관점으로 정리한 문서다 (T153).
제품을 **검증**하는 절차는 `specs/001-interactive-ai-test-builder/quickstart.md` 가 갖고,
이 문서는 **개발할 때 반복하는 것들**을 갖는다.

> **사람이 걸어야 남는 검증**은 [PENDING-HUMAN-VERIFICATION.md](PENDING-HUMAN-VERIFICATION.md)
> 가 한 곳에 모아 둔다 — 절차·기록 시트·규모가 항목별로 있고 판정 칸만 비어 있다.
> 자동 테스트가 왜 그것을 대체하지 못하는지도 그 문서가 실측 사례로 적었다.

## 확인된 환경

Python 3.13.0 (pyenv) · Node 23.7.0 / npm 10.9.2 · uv 0.9.7 · macOS 26.2 arm64

Playwright 1.62.0 이 Python 3.13 에서 정상 동작함을 실측했다 (research R1 검증 항목).
3.13 에서 설치가 깨지면 3.12 로 내리고 research.md R1 의 검증 항목을 갱신한다.

## 설치

```bash
cd backend && uv sync && uv run playwright install chromium
cd ../frontend && npm install
```

스키마 생성물은 **커밋 대상**이다 (헌법 Cross-language schema duty). 도메인 모델을 고쳤으면
다시 생성해서 함께 커밋한다.

```bash
cd backend && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
```

생성물을 갱신하지 않으면 `tests/contract/test_schema_drift.py` 가 실패한다. 그 테스트는
"손으로 타입을 만들기 시작하는 것" 을 막는 장치다.

## 실행

```bash
# 1) 검증용 대상 앱 (표준 라이브러리만 쓴다)
python fixtures/sample-app/serve.py --port 4300

# 2) 백엔드 — 로컬 인터페이스에만 바인딩한다 (FR-088a)
cd backend && uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320

# 3) 프론트엔드
cd frontend && npm run dev            # http://127.0.0.1:4310
```

브라우저는 **창 없이 뜬다** (010 FR-352). 조작은 제품 화면 안 미러 영역에서 한다 —
클릭·스크롤·마우스 올리기·끌어놓기·한글 입력이 전부 거기서 성립한다. 창을 띄우려면
`ITB_HEADLESS=0` 을 명시한다.

010 이전에는 반대였다. 조작 국면(녹화·사람 인수)이 실제 창을 요구했고 창이 기본이었다
(001 clarify 결정 3). 뒤집은 이유는 둘이다 — 조작 국면마다 발생하던 화면·창 왕복을 없애고
(SC-511), **화면 없는 기계에서도 전체 흐름이 동작하게** 한다 (SC-518). 창이 기본이면
CI 러너·원격 서버에서 제품이 아예 뜨지 못한다.

### 조작 위치 — 미러가 기본, 창은 폴백 (010)

「지금 조작이 어디서 이루어지는가」를 **조작 위치**(control surface)라 부른다. 값은 둘이다.

| 값 | 언제 | 무엇이 조작을 받는가 |
|---|---|---|
| `mirror` (기본) | 항상 | 제품 화면 안 미러 영역 |
| `window` | 사용자가 명시적으로 전환했을 때 | 실제 브라우저 창 (미러는 관찰용) |

**전환은 사용자 요청으로만 일어난다** (FR-353). 제품이 상황을 판단해 창을 열지 않는다 —
요청하지 않은 창은 그 자체로 조작 위치를 잃게 만들고, 화면 없는 기계에서는 그 시도가
실패한다. 대신 막힌 상황(1 FPS 강등·제품이 대신 받을 수 없는 브라우저 요구)에서 **전환
수단이 그 자리에 보인다** (FR-353a).

전환은 `POST /api/sessions/{id}/control-surface` 로 요청하고, 창을 띄울 수 없는 환경이면
**사유와 함께 거절된다** (FR-351). 조용히 실패하지 않는다.

**조작은 별개의 소켓을 탄다** — `WS /api/sessions/{id}/control`. 관찰 소켓
(`/events`)의 서버 → 클라이언트 단방향 계약은 그대로다. 한 소켓이 프레임 밀기와 조작
받기를 같이 하면 조작 폭주가 프레임 전달을 막고 그 역도 성립한다 (research R4).
계약은 `specs/010-headless-mirror-control/contracts/mirror-control.md` 에 있다.

### 미리보기(미러)가 정적 화면에서도 나온다 (005)

CDP `Page.startScreencast` 는 **화면이 변할 때만** 프레임을 만든다. 그래서 미러에는 두 가지
장치가 있다 — 마지막 프레임 캐시(구독이 뒤늦게 붙어도 현재 화면을 준다)와 무프레임 감시
(마지막 프레임 후 2초 조용하면 스크린샷 한 장). **감시가 도는 것은 정상 동작이며 강등이
아니다** — `mirror_degraded` 를 발행하지 않는다.

이 장치가 없던 동안 정적 화면에서는 프레임이 한 장도 도달하지 않았다(실측 0건).

### 실행 결말은 네 값이다 (005)

`Outcome` 은 `pass · fail · stopped · partial_pass` 다.

| 값 | 언제 | 실패 집계 |
|---|---|---|
| `pass` | 실행 대상 Step 전부 통과 | 아니오 |
| `fail` | 실패 Step 이 있다 · 세션 유실 | 예 |
| `stopped` | 사용자가 중지를 요청했다 | **아니오** |
| `partial_pass` | 실패 Step 을 건너뛰고 나머지를 마쳤다 | 아니오 |

판정은 `itb.domain.run_result.decide_outcome()` **한 곳**이 한다. 화면·목록이 각자
`outcome == "fail"` 로 갈리면 결말이 늘 때 한 곳이 빠뜨린다.

`partial_pass` 라는 이름은 `RunScope.PARTIAL`(부분 실행 = 실행 **범위**)과 구별하기
위한 것이다. 결말과 범위는 다른 축이다 — Step 06~07 만 돌아 전부 통과하면 결말은 `pass`
이고 범위가 `partial` 이다.

**결말 값을 추가하면 스키마를 다시 생성해야 한다.** 순서는 아래를 지킨다.

```bash
cd backend && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
```

어기면 `tests/contract/test_schema_drift.py` 가 실패한다. 드리프트 검사는 **권위 정의에서
스키마 파일까지**만 본다 — 프론트 타입 생성물이 낡았는지는
`tests/contract/test_run_outcome_contract.py` 가 본다. 둘 다 있어야 양쪽 끝이 맞는다.

화면 쪽 어휘는 `frontend/src/lib/wording.ts` 한 곳에서 나온다. 결말 문장·칩·색 역할·
Step 번호 변환이 전부 여기 있고, **알 수 없는 값은 실패로 취급한다**(보수적 기본값) —
통과로 보이면 사용자가 확인하지 않고 넘어가기 때문이다. 사전 밖에서 어휘를 만들지
않는지는 `frontend/tests/OutcomeVocabulary.test.tsx` 와
`frontend/tests/StepNumberConsistency.test.tsx` 가 원문을 훑어 확인한다.

### 세션 상태를 화면이 읽는 법 (005 Phase 12)

**"세션이 있는가" 와 "지금 돌고 있는가" 는 다른 질문이다.** 실행이 끝나도 세션은
`failed`·`review` 로 등록에 남는다 — 기록·저장·결과 경로가 거기 있기 때문이다. 그래서
세션의 **존재**로 "실행 중" 을 판정하면 행이 영원히 `RUNNING` 에 고착된다.

이 착오는 두 번 났다. 백엔드에서는 `active_session_for_test` 가 등록 여부를 보고 재실행을
항상 거절했고(005 FR-124 가 그것을 생존 판정으로 고쳤다), 화면에서는 목록 행이 같은 착오로
결말을 감췄다(재점검 N-02).

판정은 `frontend/src/lib/sessionState.ts` 한 곳에서 나온다.

| 질문 | 함수 | 쓰는 곳 |
|---|---|---|
| 지금 Step 이 돌고 있는가 | `isRunning(state)` | 목록 행의 칩·「실행 중」·결과 버튼 노출 |
| 돌아갈 화면이 남았는가 | `isResumable(state)` | 복귀 수단(「실행 화면 보기」) |

`paused`·`ai_blocked` 는 **실행 중이 아니다** — 세션은 열려 있지만 사용자의 다음 조작을
기다린다. 그것을 「실행 중」이라고 부르면 사용자는 기다리면 끝난다고 읽는다.

`SessionScreen.tsx` 는 미러 국면 판정을 위해 더 세분된 집합(조작·관찰·종료·탭 없음)을
따로 갖는다. 여러 화면이 함께 묻는 질문만 위 모듈에 둔다.

### 화면은 하나이고 국면이 일곱이다 (007)

007 이전에는 한 테스트를 놓고 화면이 여섯이었다 — 실행 중·일시정지·사람이 직접 조작·
AI 작성·결과·편집. 여섯은 Step 목록을 **각자** 그렸고(4벌), Step 상세를 각자 열었고(2벌),
같은 정보를 다른 자리에 뒀다. 사용자가 말한 "다 따로 만드니까 사용성이 떨어진다" 의
코드 상 형태가 그것이다.

지금은 화면이 하나다. **국면**이 여덟이고, 국면은 `frontend/src/lib/phase.ts` 가 판정한다.

```
lib/phase.ts          국면 판정의 유일한 지점 (AI 세션은 `authoring_mode` 로 — `state` 가 아니다)
lib/actions.ts        조작 식별자 34개
lib/capabilities.ts   국면 × 조작 권한표 + 런타임 조건 + 전 국면 덮어쓰기
lib/wording.ts        화면 어휘 — 국면 이름·조작 라벨·비활성 이유
lib/layout.ts         ③ 좌측 두 자리의 세로 배분 — 국면이 정하고 표가 소유한다

components/workbench/ 표시 층. **데이터를 읽지 않고 명령을 만들지 않는다**
  Workbench.tsx       3층 껍데기 (헤더 60px · 국면 띠 48px · 본문)
  PhaseBar.tsx        ② 국면 띠 — 실행 조작 + **저장·되돌리기·이름** (011)
  StepList.tsx        **단일** Step 목록 (우 460px) — 칸 0 은 삭제 대상 체크 (011)
  StepDetail.tsx      **단일** Step 상세 (**목록 왼쪽** 겹침 640px · 011)
  ActionPalette.tsx   조작의 집 — 순서와 구성을 여기가 갖는다
  BulkDeleteConfirm.tsx  복수 삭제 확인 — 세션·편집이 같은 구현을 쓴다 (011)
  TargetPane.tsx      ③-a 대상 앱 슬롯 — 미러 / 산출물 / 브라우저 열기 / 빈 상태
  WorkArea.tsx        ③-b 국면 작업 영역 — 그 국면에서 실제로 하는 일의 유일한 자리

pages/ComposeView.tsx    만들기 국면의 어댑터 (세션도 저장된 테스트도 Step 도 없다)
pages/SessionScreen.tsx  세션 다섯 국면의 어댑터 (구독·상태·명령을 소유한다)
pages/ResultView.tsx     결과 국면의 어댑터
pages/EditView.tsx       편집 국면의 어댑터
```

**두 표시 컴포넌트는 자기 크기를 모른다.** `TargetPane`·`WorkArea` 는 높이를 인자로만
받고, `Workbench` 가 `lib/layout.ts` 의 배분표를 국면으로 한 번 조회해 내려 준다. 1회차에는
둘이 각자 하드코딩했고 — `flex: "1"` 과 `flex: 0 0 auto` — 합쳐 보면 **편집 국면에서 채울
것이 없는 자리가 700px 를 가져갔다** (2회차 S-12). 판단이 두 파일에 흩어져 있으면 어느 한
쪽만 보고는 그 결함을 볼 수 없다.

한 국면에서 두 자리가 동시에 「남는 높이 전부」일 수 없다 (UC-100). `tests/VerticalSplit.test.ts`
가 그것과 「선언한 주 자리가 실제로 더 큰 배분을 갖는가」를 센다.

어댑터는 국면을 `WorkbenchModel` 로 바꾸는 일만 한다. 그리는 것은 `Workbench` 하나다.

**조작 가능 여부를 화면이 스스로 판단하지 않는다.** `capabilities.ts` 의 표가 정본이고,
표와 코드가 다르면 코드를 고친다. 단 **현재 쓸 수 있는 조작이 표에서 「해당 없음」이면
그것은 표의 오류**이며 표를 고친다 (UC-401).

**조작마다 자리가 하나다.** 자리를 국면마다 조립하면 한 국면이 하나를 빠뜨리고, 빠진 것이
감춰진 조작이 된다. `tests/CapabilityUI.test.tsx` 가 그것을 센다 — 표가 `–` 로 두지 않은
조작이 여덟 국면 전부의 화면에 있고, 비활성인 것은 모두 이유를 갖는지.

| 조작 묶음 | 자리 |
|---|---|
| `run.*` (실행·일시정지·계속·중지·속도) | 국면 띠 |
| `session.open`·`result.show`·`nav.editStep`·`nav.back` | 헤더 |
| `browser.openAt`·`artifact.select`·`tab.select` | 대상 앱 영역 |
| `step.select` | Step 패널 |
| `step.update`·`step.markSensitive`·`step.repick` | Step 상세 |
| 나머지 (Step 작성·순서·삭제, 테스트 속성, 저장) | 조작 팔레트 |

### 조작의 집이 바뀐 곳 (011)

「같은 조작은 어느 국면에서나 같은 자리에」가 FR-235 이고, 그 **자리**를 정하는 표는
`specs/007-unify-test-screens/contracts/ui-contract.md` §2-7 이 갖는다. 011 이 그 표를
계약으로 올렸다 — 그 전까지 규칙은 `ActionPalette.tsx` 머리말 주석에만 있었고, 주석은
자기 근거로 계약에 없는 절을 가리키고 있었다.

011 이 옮긴 것:

| 조작 | 이전 | 이후 | 왜 |
|---|---|---|---|
| `save` · `edits.revert` | 조작 팔레트 (Step 패널 바닥) | **국면 띠** | 저장은 작성 흐름의 종착점인데 그 자리가 Step 목록을 다 지난 곳이었다. 못 찾고 나가면 기록이 사라진다 |
| `test.rename` | 팔레트 입력칸 | **국면 띠의 이름 표시 그 자리** | 이름이 화면에 두 번 있었다 (띠의 표시 + 팔레트의 칸). 보이는 곳에서 고치면 하나가 된다 |
| Step 상세 | 우측 겹침 (목록을 덮었다) | **목록 왼쪽** 겹침 | 상세와 목록이 둘 다 오른쪽이라 방금 고른 행을 보면서 상세를 읽을 수 없었다 |

`test.setStartUrl`·`ai.compose` 는 팔레트에 **남았다.** 국면 띠에 표시되지 않는 값이라
「보이는 곳에서 고친다」 논리가 성립하지 않고, 48px 한 줄은 긴 URL 도 여러 줄 지시문도
담을 수 없다.

### Step 행의 네 상태는 채널이 다르다 (011)

한 행이 동시에 넷을 가질 수 있고, **표시 자리가 서로 달라야 한다.**

| 상태 | 채널 |
|---|---|
| 결말 | 행 왼쪽 3px 테두리 + 오른쪽 결말 칸의 형태 아이콘 |
| 일시정지 | 바탕 (`--warn-t`) |
| 지목 | 안쪽 링 (`box-shadow: inset`) + `aria-current="true"` |
| 삭제 대상 | 칸 0 의 체크 칸 |

011 이전에는 앞의 셋이 `border-left-color`·`background` 두 채널을 다퉜고, `StepRow` 의
배타 삼항이 셋을 줄 세워 **언제나 하나만 남았다** — 통과한 Step 을 고르면 결말이 사라지고,
일시정지 행은 골라도 선택이 보이지 않았다.

**체크 칸은 결말 아이콘과 형태가 갈린다.** 결말의 통과는 이미 체크(✓)이고, 008 에 「빈
사각형이 체크박스로 읽혔다」는 기록이 있다 — 진짜 체크 칸이 생겼으므로 반대 방향의 혼동을
막아야 한다.

### 지목과 삭제 대상은 다른 축이다 (011)

행 본문을 누르는 것은 **지목**(상세 열기)이고, 칸 0 의 체크는 **삭제 대상**이다. 같은
누름에 두 뜻을 주면 사용자는 상세를 보려다 삭제 대상을 만든다.

삭제 대상 선택은 **인덱스가 아니라 Step id 로** 갖는다. 인덱스로 가지면 순서 변경 뒤 다른
Step 이 지워진다 — 고른 것은 「세 번째 행」이 아니라 「그 Step」이다.

복수 삭제는 **원자적이다.** 세션은 `POST /api/sessions/{id}/steps:delete` 가, 편집은 저장
요청의 `edits` 에 `delete` 를 여러 개 싣는 것이 그 일을 한다 (편집은 라우트를 더하지
않았다 — 이미 편집 연산 목록을 받는다). 하나라도 못 찾으면 아무것도 지워지지 않는다.

### 전이 안내는 걷어야 한다 (005 FR-146)

일시정지가 10초 안에 성립하지 않으면 서버가 "아직 실행 중입니다" 안내를 붙인다. 그 문장은
**그 순간에만** 참이므로 실행이 끝나면 걷어야 한다 — 그러지 않으면 같은 화면의 배지가
「실행 종료」라고 말하는 옆에서 「아직 실행 중」이라고 말한다.

`add_edit_warning(..., transient=True)` 로 표시하고 `clear_transient_edit_warnings()` 로
걷는다. 계약(문자열 목록)은 바뀌지 않는다. 걷은 뒤에는 `publish_edit_warnings_now()` 로
**빈 목록이라도** 내보내야 한다 — 보통의 `publish_edit_warnings()` 는 비어 있으면 보내지
않으므로, 걷었다는 사실이 화면에 닿지 않는다.

걷는 자리는 둘이다. 정상 종료는 러너(`RunnerTask._loop`), 중지는 stop 라우트. **러너의
`finally` 에 두지 않는다** — 그 블록은 완료 신호만 올려야 한다. 여기서 세션 메서드를
부르면 그것이 실패하는 순간 `_finished`·`_boundary` 가 올라가지 않고, 실행 완료를 기다리는
모든 것이 영구히 멈춘다. 실제로 그렇게 났다.

### 사용자에게 보이는 문구에 세션 식별자를 넣지 않는다 (005 FR-135)

`SessionError` 의 문장에는 진단을 위해 세션 UUID 가 들어 있다. **그것을 `detail` 로 그대로
올리지 않는다** — 화면이 배너로 띄우면 사용자가 할 수 있는 일과 무관한 잡음이자 불안
신호가 된다. 식별자는 `detail.session_id` 로만 싣는다.

같은 사실은 엔드포인트마다 **같은 문장**을 쓴다. `tabs.py` 가 `sessions.py` 와 다른 문장을
쓰던 것이 재점검 U-03-b 의 절반이었다. `tests/contract/test_no_session_id_in_messages.py`
가 세션 경로 전부를 훑어 확인한다.

종료된 세션에 대한 **탭 조회는 하지 않는다.** 탭은 살아 있는 브라우저의 속성이므로 404 가
정상이고, 그것을 오류로 띄우면 사용자가 한 일(중지)의 정상적인 결과를 오류로 말하게 된다.
`SessionScreen.tsx` 의 `TABLESS_STATES` 가 그 경계다.

### 암호구로 잠근 비밀키

키 관리 화면에서 암호구를 걸어 키를 만들었으면, **백엔드를 다시 띄운 뒤에는 그 화면에서 잠금을
해제한다.** 암호구는 백엔드 프로세스 메모리에만 남으므로 재기동하면 다시 잠긴다. 잠긴 채로
실행하면 민감 변수를 쓰는 Step 이 "잠겨 있다" 는 사유와 함께 실패한다 (FR-089f).

사람이 없는 실행(CI·헤드리스)에서는 환경 변수로 공급한다. 셸 히스토리에 남지 않게 `read -rs` 로
받는다 — 값을 명령줄에 직접 적으면 히스토리와 프로세스 목록에 남는다.

```bash
cd backend
read -rs ITB_KEY_PASSPHRASE && export ITB_KEY_PASSPHRASE   # 입력 후 Enter (화면에 안 보임)
uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320
```

값 끝에 개행이 섞이면 열리지 않는다. `export ITB_KEY_PASSPHRASE="$(echo …)"` 같은 방식을 쓰지 않는
이유다. 암호구가 틀리면 기동은 되고 경고가 로그에 남는다 — 민감 변수를 쓰지 않는 테스트가 이것
때문에 막히면 안 되기 때문이다.

### 언어모델 자격 증명 (US4~US6 을 손으로 써 볼 때만)

```bash
ant auth status        # 활성 프로필이 있으면 그대로 쓴다
ant auth login         # 또는 export ANTHROPIC_API_KEY=...
```

**키를 코드·설정 파일에 넣지 않는다** (FR-084). SDK 가 환경 변수 → 프로필 순으로 해석한다.

자동 테스트는 자격 증명을 쓰지 않는다 — `AuthoringAgent` 의 `driver` 자리에 대본대로 도구를
부르는 가짜 모델을 끼운다 (`backend/tests/us4_support.py`).

### 키 없이 AI 경로를 눈으로 보기 (개발용, 선택)

API 키가 없어도 **이미 로그인된 Claude Code** 로 AI 작성 경로를 끝까지 돌려 볼 수 있다.
UX 워크스루에서 S6·S7 이 자격 증명 때문에 미검증으로 남는 것이 이 스위치가 있는 이유다.

```bash
uv sync --extra claude-code    # 선택 의존성. 한 번만
claude                          # 로그인돼 있는지 확인

cd backend
ITB_AI_DRIVER=claude-code uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320
```

| | 기본 (미설정) | `ITB_AI_DRIVER=claude-code` |
|---|---|---|
| 경로 | Messages API (`anthropic`) | 로그인된 Claude Code (`claude-agent-sdk`) |
| 자격 증명 | API 키 / `ant` 프로필 | `claude` 로그인 |
| 도구 | `build_tools` (`@beta_async_tool`) | `build_mcp_tools` (in-process MCP) |
| 모델·effort | `LlmConfig` 대로 | **Claude Code 기본값** (`config` 무시) |

**결과를 품질 근거로 쓰지 않는다.** `output_config.effort`·`betas`/`fallbacks`·
`stop_reason: "refusal"` 은 Messages API 전용이라 이 경로에서 전달되지 않고 모델도 다르다.
SC-002 같은 성공 기준 측정은 **기본 드라이버로만** 한다.

이 경로에서도 에이전트는 브라우저 도구 11종만 쓴다 — Claude Code 가 기본으로 주는
`Read`·`Write`·`Bash` 등은 권한 콜백이 거부한다 (FR-086,
`backend/src/itb/authoring/claude_code_driver.py`). `setting_sources=[]` 로 개발자의
`settings`·`CLAUDE.md`·훅도 읽지 않는다.

정확히 `claude-code` 한 값만 스위치를 켠다. 오타·대문자는 기본으로 떨어지며, 그것을
`backend/tests/unit/test_driver_selection.py` 가 고정한다. 테스트는 이 환경 변수를 항상
지우고 돌린다 (`backend/tests/conftest.py`).

## 저장된 테스트 편집 (006)

**편집 규칙의 구현은 한 곳이다** — `backend/src/itb/execution/step_edits.py`. 그 모듈은
Playwright 도 FastAPI 도 임포트하지 않는 순수 모듈이고, **호출자가 둘**이다.

| 경로 | 호출자 | 실행 위치 |
|---|---|---|
| 일시정지 세션 편집 | `api/routes/steps.py` (`/api/sessions/{id}/steps*`) | 세션의 현재 위치 |
| 저장된 정의 편집 | `api/routes/tests.py` (`PUT /api/tests/{id}/definition`) | 없음 → `0` 을 넘긴다 |

`current_step_index=0` 으로 부르면 "이미 실행된 구간을 고쳤다" 경고가 하나도 생기지 않는다.
그래서 정의 편집이 그 모듈을 **고치지 않고** 쓸 수 있다.

**세 번째 구현을 만들지 말 것.** 편집 조작이 필요하면 `step_edits` 에 인자를 더한다.
`backend/tests/unit/test_definition_edit_core.py` 가 그 구조를 테스트로 고정한다 —
두 번째 구현이 생기면 그 파일이 깨진다.

같은 이유로 변수 파생은 `domain/test_case.py` 의 `derive_variables()` 한 곳이다. 두 벌이면
한쪽에서 민감 표시가 비민감으로 강등되고, 재실행이 빈 값을 채운다 (조용한 실패다).

### 저장 요청은 편집 결과가 아니라 편집 연산 목록이다

```
PUT /api/tests/TC-001/definition
{ "revision": "<GET 이 준 지문>", "edits": [{"op": "update", "step_id": "step-02", "value": "operator"}] }
```

결과 전체를 받으면 "어느 Step 종류가 값을 갖는가" 같은 판정이 프론트로 넘어가고, 그것이
규칙의 두 번째 구현이 된다. 연산을 받으면 서버가 규칙의 주인으로 남는다.

`revision` 은 정의 파일 내용의 SHA-256 앞 16자다. 불일치면 `409 DEFINITION_STALE` 이고
응답에 현재 정의가 실린다 — 사용자가 편집기로 YAML 을 직접 고치는 것은 정상 사용이므로
(헌법 원칙 V) 실제로 일어난다. **강제 플래그는 없다**: 덮어쓰기는 응답이 준 새 `revision` 을
실어 다시 보내는 것이다. 플래그는 습관이 되고, 습관이 되면 감지가 무의미해진다.

### locator 후보는 편집할 수 없다

편집 요청 모델에 `target`·`css`·`test_id` 류 필드가 **아예 없다.** 후보는 살아 있는
페이지에서만 수집·검증되므로(원칙 IV), 손으로 넣은 값은 `verified` 를 얻을 수 없다.
`verified` 로 적으면 거짓말이고, 아니면 실행에 쓰이지 않는 조용한 무효 편집이다.

요소를 다시 집어야 하면 편집 국면의 「브라우저 열어 Step nn 에서 멈추기」를 쓴다 —
`POST /api/sessions` 에 `pause_before_index` 를 실으면 러너가 그 Step **직전**에서 기존
`PAUSED` 로 들어간다. 사용자가 달리는 실행을 「일시정지」로 잡을 필요가 없다.

## 검증

```bash
# ★ 헌법 원칙 II (NON-NEGOTIABLE). 이것이 실패하면 다른 검사는 의미가 없다
cd backend && uv run lint-imports

cd backend && uv run ruff check src/ tests/
cd backend && uv run pytest
cd backend && uv run python -m itb.schema.export --check
cd frontend && npx tsc --noEmit && npx vitest run
```

CI(`.github/workflows/ci.yml`)는 경계 검사 잡을 최우선으로 실행하고 실패하면 후속 잡을
돌리지 않는다.

### 테스트 계층

| 경로 | 무엇을 보는가 | 실제 스택 |
|------|---------------|-----------|
| `tests/unit/` | 순수 로직 — 도메인 불변식, 상태 기계, 후보 우선순위, 생성기, 시도 상한 | 없음 |
| `tests/contract/` | REST·WebSocket·DSL 계약, 스키마 드리프트 | 일부 |
| `tests/abnormal/` | 이상 조작 목록(고장 4종 × 조작 면 3종) 판정 | 대부분 |
| `tests/integration/` | 픽스처 앱 대상 실제 동작 — 녹화·재실행·일시정지·AI·비밀값 | 있음 |
| `tests/e2e/` | 사용자 스토리별 quickstart 절차 | 있음 |

### 개발 루프에서는 브라우저 계층을 뺀다

디렉터리로 나누지 않는다 — `tests/contract/` 에도 실브라우저 검증이 섞여 있어서
경로만으로는 선이 맞지 않는다. 선은 **`browser` 마커**다. 그 마커는
`tests/conftest.py` 의 `pytest_collection_modifyitems` 가 **자동으로** 붙인다:
무거운 픽스처(`tests/tiers.py` 의 `HEAVY_FIXTURES`)를 요구하는 검증이 그 계층이다.
손으로 달지 않으므로 새 파일에서 잊을 일이 없고, 목록이 낡으면
`tests/unit/test_test_tiers.py` 가 실패한다.

```bash
# 개발 루프 — 브라우저·npm·픽스처 앱 없이 돈다
cd backend && uv run pytest -m "not browser" -q

# 커밋 전 — 전량
cd backend && uv run pytest -q

# 실브라우저 계층만
cd backend && uv run pytest -m browser -q
```

**빠진 것을 통과로 읽지 않는다.** `-m "not browser"` 는 개발 중 되돌림을 빠르게 보기
위한 것이고, 커밋·CI 는 전량을 돈다. CI 는 두 계층을 **별도 잡으로 동시에** 돌린다
(`.github/workflows/ci.yml` 의 `backend-fast`·`backend-browser`).

### 병렬 실행

`pytest-xdist` 가 기본으로 켜져 있다 (`pyproject.toml` 의
`addopts = "-n auto --dist loadfile"`). `--dist loadfile` 은 필수다 —
`tests/abnormal/test_ui_surface.py` 는 시나리오를 목록 순서대로 돌아야 하고 세션 범위
`product_ui` 를 18건이 나눠 쓴다. 검증을 프로세스에 흩으면 그 순서가 깨진다.

실패 하나를 따라갈 때는 순차로 돌리는 편이 낫다 — 분배된 출력은 어느 프로세스의
것인지 읽기 어렵다.

```bash
cd backend && uv run pytest -n 0 -x tests/unit/test_secrets.py
```

### 창을 띄우려면 명시해야 한다 (010 이 뒤집었다)

제품 기본값은 **창 없이 띄우는 것**이다 (FR-352). 창을 띄우려면 `ITB_HEADLESS=0` 을
명시한다.

```bash
# 실제 창을 띄우고 싶을 때만
ITB_HEADLESS=0 uv run itb
```

**알 수 없는 값·오타는 기본값(창 없음)으로 붙는다.** 010 이전에는 반대 방향의 규칙이
있었다 — 오타가 창을 없애지 않게 하는 것이 목적이었고, 그때는 창이 사람의 유일한 조작
수단이었으므로 옳았다. 조작 수단이 미러로 옮겨간 지금 오타가 창을 **열어** 버리면 화면
없는 기계에서 브라우저 실행 자체가 실패한다 — 그 실패야말로 원인을 드러내지 않는다.

검증은 `tests/conftest.py` 의 `_headless_browsers` 가 값을 명시적으로 세운다. 제품
기본값과 같아졌지만 지우지 않은 이유는 그 픽스처의 독스트링에 있다 — 개발자의 셸 환경을
덮고, 검증의 전제를 제품 기본값의 변화로부터 떼어 놓는다. 별도 프로세스로 뜨는 제품
서버에는 `tests/abnormal/product_ui.py` 가 환경 변수로 넘긴다 (monkeypatch 가 프로세스
경계를 넘지 못한다).

`tests/unit/test_test_tiers.py` 가 기본값과 오타 처리 두 성질을 못 박는다. 010 이 그
검증의 **방향을 바꿨고 삭제하지 않았다** — 무엇이 왜 뒤집혔는지가 각 독스트링에 있다.

### 느린 것은 지우지 않고 비용을 내린다

두 곳이 그 예다. **검증하는 성질은 그대로 두고 비용만 내렸고**, 제품 기본값이 새지
않도록 각각 잠금 검증을 뒀다.

| 무엇 | 제품 값 | 테스트 값 | 잠금 |
|------|---------|-----------|------|
| 암호구 파생 (argon2id) | MODERATE (회당 ~2.7초) | INTERACTIVE | `test_secrets.py::test_product_derivation_cost_is_moderate` |
| 미러 무프레임 감시 주기 | 2.0초 / 강등 1.0초 / **조작 국면 0.25초** | 0.10초 / 0.05초 / 0.05초 | `test_mirror_frame_delivery.py::test_product_intervals_are_the_measured_ones` |
| 브라우저 창 | **띄우지 않는다** (010) | 띄우지 않는다 | `test_test_tiers.py::test_headless_is_on_by_default_in_the_product` |

조작 국면의 감시 주기가 짧은 이유는 **조작 피드백**이다 (010 FR-335). 조작이 화면을 바꾸면
프레임이 곧 오지만(실측 중앙값 약 17~25ms), 화면을 바꾸지 않는 조작은 프레임을 만들지
않는다. 그때 2초를 기다리면 사용자는 그것을 「내 클릭이 안 먹었다」로 읽고 같은 곳을 다시
누른다. 관찰 국면에서는 줄이지 않는다 — 사람이 조작하고 있지 않으므로 기다리게 만들
피드백도 없고, 초당 네 장은 실행 중인 브라우저를 갉아먹는다.

### 고정 시간 대기를 쓰지 않는다

녹화 검증은 오랫동안 "동작한 뒤 0.4~0.8초 자고 나서 읽는다" 였다. 그 대기는 두 가지를
동시에 틀리게 한다 — 부하가 있으면 짧고(8분할에서 `steps` 가 빈 배열로 읽혔다),
평상시에는 길다(대개 100ms 안에 도달하는데 나머지를 그냥 기다린다).

`tests/step_wait.py` 의 `wait_for_steps` 는 시간을 재지 않고 **조건을 본다.** 조건이
서면 즉시 돌아오고, 서지 않으면 마감까지 기다린 뒤 마지막으로 읽은 것을 돌려준다 —
판정은 호출한 검증이 자기 단언으로 한다. 새 녹화 검증도 이것을 쓴다.

파생을 **건너뛰지 않는다** — INTERACTIVE 도 진짜 argon2id 파생이다. 제품 비용 그대로
봉인·개봉이 맞물리는지는 `@pytest.mark.production_kdf` 를 붙인 검증 하나가 확인한다.

### 테스트를 지우거나 건너뛰지 않는다

헌법 품질 게이트 4다. 깨진 테스트는 고치거나, 정말 낡았다면 **이유를 기록하고** 지운다.
`skip` 으로 덮으면 검증하지 않은 것이 통과로 보인다.

**느리다는 것은 낡았다는 뜻이 아니다.** 수행 시간을 줄이려고 검증을 지우는 것은 이
게이트가 금지하는 것과 같다 — 확인하지 않은 것이 통과로 보인다. 줄일 곳은 검증의
개수가 아니라 검증 하나의 비용과 분배다 (위 두 절).

## 자주 겪는 문제

**녹화한 Step 의 후보가 전부 `not_collected` 로 나온다**
클릭이 화면 이동을 유발하면 후보 검증이 그 이동과 경쟁한다. CSS·testId 는 동작 시점에
페이지 안에서 검증하므로 영향을 받지 않지만(`recorder.js` 의 `statusOf`), `role`·`label`·
`text` 는 Playwright 로 검증하므로 놓칠 수 있다. 테스트에서는 사람처럼 조작한다 —
`us2_support.click_like_a_person` 이 마우스를 올려 두고 잠깐 기다린 뒤 누른다.

**통합 테스트가 "픽스처 앱이 뜨지 않았다" 로 실패한다**
`fixtures/sample-app/serve.py` 가 쓰는 포트가 막혔거나 파이썬 실행 파일이 다르다.
`conftest.py` 는 실패를 **건너뛰지 않고 명확한 사유로 실패시킨다** — 조용히 건너뛰면
검증하지 않은 것을 통과로 오인하기 때문이다.

**`lint-imports` 가 깨졌다**
`itb.execution`(또는 `storage`·`generator`·`locator`·`domain`·`mirror`·`recording`)에서
`itb.llm`·`itb.authoring`·`anthropic`·`claude_agent_sdk` 에 닿는 임포트가 생겼다는 뜻이다.
원칙 II 위반이므로 런타임 가드가 아니라 **임포트를 없애서** 고친다.

**AI 경로가 상한에 걸려 멈춘다**
도구 호출 40회, 동일 요소 연속 실패 3회가 상한이다 (FR-066). 상한 도달은 예외가 아니라
상태로 남고, 에이전트 루프가 매 턴 그 상태를 보고 끊는다 — SDK 가 도구 예외를 잡아 모델에게
돌려주므로 예외로는 루프를 끊을 수 없기 때문이다.

## 저장 레이아웃

```text
<프로젝트 디렉터리>/
├── itb-project.yaml      # 커밋 대상
├── tests/TC-001-*.yaml   # 커밋 대상 — 사용자 자산
├── secrets.local.yaml    # .gitignore 대상 (암호문)
└── .runs/                # .gitignore 대상 (실행 산출물)
    └── TC-001/
        ├── result.json       # 최근 실행 결과
        ├── result-full.json  # 최근 **전체** 실행 (부분 실행이 덮지 않는다 · 005 FR-152)
        ├── failure.png       # 실패 시점 화면
        ├── console.log
        ├── network.log
        └── steps/            # 011 — Step 별 화면
            ├── 0.png
            └── 2.png         # 1 은 민감 값이 있어 남기지 않았다 (구멍이 정상이다)
```

**Step 별 화면의 보관은 「테스트당 최근 실행 1회분」이다** (011 clarify 결정 3). 장수 상한도
보관 기간 장치도 없다 — `.runs/<테스트ID>/` 가 이미 테스트당 하나이므로, 실행 **시작 시**
`steps/` 를 비우는 것으로 끝난다 (`execution/artifacts.clear_step_screenshots`).

덮어쓰기만으로는 부족하다: Step 을 줄여 다시 돌리면 이전 실행의 높은 인덱스 파일이 남고,
사용자는 지금 실행에 없는 화면을 보게 된다.

민감 값이 담긴 화면은 **쓰지 않는다.** PNG 를 치환하면 파일이 깨지므로, 기록 직전에 검사해
들어 있으면 남기지 않고 사유만 `StepResult.screenshot_note` 에 적는다 (헌법 §보안).

키 쌍은 프로젝트 밖에 있다: `~/.config/itb/keys/`.

**실행 속도도 프로젝트 밖에 있다**: `~/.config/itb/preferences.json`. 속도는 보는 사람의
취향이지 프로젝트의 속성이 아니므로, 프로젝트 파일에 넣으면 개인 취향이 팀 저장소에
커밋된다. 파일이 없거나 깨져도 실행은 막히지 않는다 — 기본값(`보통`)으로 진행하고 사유를
경고로 알린다.

## 실행 속도 (004)

Step 사이에 사람이 따라올 시간을 준다. 네 단계이며 실행 중에도 바꿀 수 있다.

| 값 | 간격 | 쓰는 자리 |
|---|---|---|
| `fast` | 없음 | **무인 실행·CI.** 004 이전 동작이다 |
| `normal` | 500ms | 기본값 |
| `slow` | 1500ms | 화면 변화를 눈으로 확인할 때 |
| `step` | 자동 일시정지 | 한 Step 씩 확인하며 편집할 때 |

**무인 실행은 `fast` 를 명시해야 한다.** 저장된 취향이 CI 를 느리게 만들지 않는 유일한
방법이다.

```bash
curl -X POST http://127.0.0.1:4320/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"mode":"replay","test_id":"TC-001","pacing":"fast"}'
```

시간을 재는 테스트도 마찬가지다 — `tests/integration/test_performance.py` 의 오버헤드
측정이 `fast` 를 고정하는 이유가 그것이다. 간격은 일부러 준 시간이지 제품이 낭비한
시간이 아니다.

**속도는 저장된 테스트를 실행할 때만 걸린다.** AI 로 만드는 **중**에는 적용되지 않는다 —
작성 루프가 러너 태스크를 쓰지 않기 때문이다. AI 가 만든 테스트를 저장한 뒤 재실행하면
사람이 만든 테스트와 똑같이 적용된다.

## 지연 로딩 픽스처 (004)

로딩 중인 요소를 "없음" 으로 판정하던 결함(004 US2)을 재현하는 화면이다.

| 경로 | 지연 | 무엇을 재는가 |
|---|---|---|
| `/lazy.html?ms=2000` | 2000ms (기본) | 하위 후보로만 늦게 나타나는 요소를 기다리는가 |
| `/lazy.html` 로딩 중 | — | 같은 텍스트 스켈레톤 2개. 잘못된 요소를 잡지 않는가 |
| `/late-visible.html?ms=1000` | 1000ms | DOM 에 붙었지만 안 보이는 요소를 기다리는가 |

**`lazy.html` 의 2000ms 를 함부로 줄이지 말 것.** 옛 대기 예산(5000ms)보다도 작은데 004
이전 코드는 실패한다 — 결함이 예산 부족이 아니라 알고리즘 때문임을 이 값이 증명한다.
