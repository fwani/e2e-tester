---

description: "Task list for 010-headless-mirror-control"
---

# Tasks: 대상 브라우저를 제품 화면 안에서 조작한다

**Input**: Design documents from `/specs/010-headless-mirror-control/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/mirror-control.md](contracts/mirror-control.md)

**Tests**: 포함한다. 헌법 품질 게이트 3이 자동화 테스트를 요구하고, FR-324·FR-332 가
동등성·좌표 정확성을 **자동 검증으로 고정하라고 명시**한다. 테스트는 선택이 아니다.

**Organization**: 사용자 이야기별로 묶는다. 다만 이 기능은 **US1 이전에 조작 경로 자체를
세워야** 하므로 Foundational 이 두껍다 — 그것이 US1~US5 가 공유하는 통로다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 이야기에 속하는가 (US1~US5)

## Path Conventions

`backend/src/itb/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup — 헤드리스 기본값 전환

**Purpose**: 대상 브라우저를 창 없이 띄우는 것을 기본으로 만든다. 이후 모든 작업이 이
전제 위에서 돈다.

**⚠️ 개정 작업이 포함된다.** 기존 검증을 **삭제하지 않고 방향을 바꾼다** (헌법 품질
게이트 4 · plan.md Complexity Tracking).

- [X] T001 `headless_default()` 기본값을 `True` 로 뒤집고 알 수 없는 값·오타를 헤드리스
      유지로 읽게 바꾼다 in `backend/src/itb/execution/session.py` (FR-352)
- [X] T002 헤드리스 기본값 검증 2건을 개정한다 — `test_headless_is_off_by_default_in_the_product`
      와 `test_unknown_headless_value_keeps_the_window` 를 **반대 방향**(기본이 창 없음,
      오타는 기본값으로 붙음)으로 바꾸고, 무엇이 왜 뒤집혔는지를 독스트링에 남긴다
      in `backend/tests/unit/test_test_tiers.py` (research R10)
- [X] T003 [P] `_headless_browsers` 픽스처의 의미를 재정리한다 — 제품 기본값과 같아졌으므로
      그 픽스처가 지금 무엇을 위해 있는지를 주석으로 명시하고, 창을 띄우는 검증이 있으면
      그것만 명시적으로 반대로 둔다 in `backend/tests/conftest.py`
- [X] T004 [P] 창 존재를 전제한 안내 문구를 조사해 목록으로 남긴다 — 이후 US5 에서
      `window` 상태의 문구로 옮길 대상이다 in `frontend/src/lib/wording.ts` (M-05)

**Checkpoint**: `uv run pytest -m "not browser and not timing" -q` 가 통과한다. 대상
브라우저가 창 없이 뜬다.

---

## Phase 2: Foundational — 조작 통로

**Purpose**: 조작 사건이 흐르는 통로와 좌표 변환의 근거를 만든다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 사용자 이야기도 시작할 수 없다. US1~US5 가
전부 이 통로를 쓴다.

### 프레임 좌표계 확장 (좌표 변환의 근거)

- [X] T005 프레임 페이로드에 `pageScale`·`offsetTop`·`seq` 를 추가한다 — `_forward` 가
      metadata 에서 `pageScaleFactor`·`offsetTop` 을 읽어 넣고, 프레임마다 증가하는
      `seq` 를 발급한다. `width`·`height` 의 의미는 바꾸지 않는다
      in `backend/src/itb/mirror/screencast.py` (FR-331 · data-model §2)
- [X] T006 강등 경로(1 FPS 스크린샷)와 무프레임 보충 경로도 같은 필드를 채우게 한다 —
      `_send_frame` 을 지나는 세 경로가 모두 같은 모양이어야 한다
      in `backend/src/itb/mirror/screencast.py`
- [X] T007 [P] 새 프레임 필드를 수신하고 타입에 반영한다 in `frontend/src/api/ws.ts`
- [X] T008 [P] 프레임 필드 확장 검증 — 세 경로(스크린캐스트·강등·무프레임 보충)가 모두
      새 필드를 채우는지 in `backend/tests/unit/test_mirror_frame_delivery.py`

### 조작 모듈 (CDP Input)

- [X] T009 `mirror/input.py` 를 만든다 — 전용 CDP 세션, **자기 명령 목록**
      (`Input.dispatchMouseEvent`·`Input.dispatchKeyEvent`·`Input.insertText`·
      `Input.imeSetComposition`·`DOM.setFileInputFiles`), 목록 밖 전송 거부.
      `screencast.py` 를 임포트하지 않는다 in `backend/src/itb/mirror/input.py`
      (research R5 · FR-344)
- [X] T010 조작 사건 → CDP 명령 변환을 구현한다 — contracts §2 의 표 그대로. 좌표는
      이미 대상 화면 좌표계로 도착한다고 가정한다 in `backend/src/itb/mirror/input.py`
- [X] T011 미해제 포인터 추적을 넣는다 — `pointer.down` 후 `pointer.up` 이 없는 상태를
      기억하고, 채널이 닫히거나 정지할 때 `pointer.up` 을 보낸다
      in `backend/src/itb/mirror/input.py` (FR-318 · contracts §2)
- [X] T012 보고 있는 탭을 조작 대상으로 넘긴다 — 활성 탭이 아니라 표시 중인 탭이다
      in `backend/src/itb/mirror/tab_switch.py` (FR-317)
- [X] T013 [P] `screencast.py` 가 여전히 `Input` 명령을 보내지 않는지 고정하는 검증
      in `backend/tests/unit/test_mirror_input.py` (research R5)
- [X] T014 [P] 명령 목록 한정 검증 — 목록 밖 명령 전송이 거부되는지
      in `backend/tests/unit/test_mirror_input.py` (FR-344)
- [X] T015 [P] 미해제 포인터 해제 검증 — 누른 상태에서 채널을 닫으면 `pointer.up` 이
      가는지 in `backend/tests/unit/test_mirror_input.py` (FR-318)

### 조작 채널 (새 WebSocket)

- [X] T016 조작 사건 모델과 경계 검증을 만든다 — `kind` 목록 한정, 좌표 범위, `text`
      길이 상한, `modifiers` 비트, `tab` 실재 여부. 어기면 **버리고 사유를 돌려준다**
      in `backend/src/itb/api/ws/control_channel.py` (FR-341 · data-model §1)
- [X] T017 `WS /api/sessions/{id}/control` 을 만든다 — 조작 국면에서만 수립되고, 세션당
      하나, 관찰 국면 전이·세션 유실 시 서버가 **사유와 함께** 닫는다
      in `backend/src/itb/api/ws/control_channel.py` (FR-342 · FR-347 · contracts §2)
- [X] T018 채널 상태 전이를 구현한다 — `closed`/`open`/`suspended`. 프레임 끊김에
      `suspended`, 회복에 `open` in `backend/src/itb/api/ws/control_channel.py`
      (FR-346 · data-model §3)
- [X] T019 조작 국면 판정을 채널 개폐에 노출한다 — 채널이 상태 기계를 **전이시키지
      않는다**는 것이 불변식이다 in `backend/src/itb/execution/state_machine.py`
      (contracts §5 불변식 4)
- [X] T020 채널을 세션 라우터에 등록하고, 국면 전이 시 채널을 정리한다
      in `backend/src/itb/api/routes/sessions.py`
- [X] T021 [P] 채널 상태 전이 검증 — 국면별 개폐, 관찰 국면에서 `open` 이 존재할 수
      없음 in `backend/tests/unit/test_control_channel.py` (FR-315 · FR-342)
- [X] T022 [P] 경계 검증 — 범위를 벗어난 좌표·키·값이 거절되고 잘려서 전달되지 않는지
      in `backend/tests/unit/test_control_channel.py` (FR-341)
- [X] T023 [P] 채널 장애 주입 검증 — 채널을 끊거나 폭주시켜도 진행 중인 실행이 완주하는지
      (10회) in `backend/tests/integration/test_control_channel_failure.py`
      (FR-348 · SC-519)

### 국면 × 조작 권한표

- [X] T024 조작 항목 두 개를 권한표에 추가한다 — 「미러에서 조작하기」·「실제 창으로
      전환하기」. 조작 국면에서 켜고 관찰 국면에서 끄며, 끈 사유를 기존 잠금 사유 체계로
      표현한다 in `frontend/src/lib/capabilities.ts` (FR-316 · research R9)
- [X] T025 런타임 덮어쓰기를 추가한다 — 프레임 없음·끊김·강등·채널 미접속. 국면 열에
      적지 않는다 in `frontend/src/lib/capabilities.ts` (FR-333 · FR-345~FR-347)
- [X] T026 [P] 국면별 조작 가능성 검증 — 8국면 전부와 런타임 덮어쓰기 4건
      in `frontend/tests/Capabilities.test.ts`

### 미러의 조작 수용

- [X] T027 `MirrorView` 가 「조작을 받는가」를 props 로 받게 바꾼다 — `pointerEvents`
      를 그 값으로 결정하고, **스스로 국면을 보지 않는다.** 파일 머리말의 「입력을 전달하는
      코드가 없다」 선언을 「국면이 정한다」로 개정한다
      in `frontend/src/components/MirrorView.tsx` (FR-316 · FR-319)
- [X] T028 좌표 변환과 사건 전송을 만든다 — 표시 좌표 → 대상 화면 좌표. **상수
      1280·800 을 쓰지 않고** 이미지의 자연 크기·표시 크기·`width`/`height`·`pageScale`·
      `offsetTop` 으로 계산한다 in `frontend/src/components/mirror/useMirrorInput.ts`
      (FR-330 · FR-331 · research R3)
- [X] T029 조작 채널 클라이언트를 만든다 — 접속·재접속·사유 표시. 조작 성공 응답을
      기다리지 않는다 in `frontend/src/api/control.ts` (contracts §2)
- [X] T030 **`MirrorView.test.tsx` 를 개정한다** — 「입력을 전달하지 않는다」를
      「**관찰 국면에서** 전달하지 않는다」로 바꾼다. 삭제하지 않는다
      in `frontend/tests/MirrorView.test.tsx` (헌법 품질 게이트 4)
- [X] T031 [P] 좌표 변환 검증 — 축소 프레임(1600×1200 → 1067×800, 배율 비정수)에서
      왕복 변환이 의도한 좌표를 내는지. **12px 밀집 요소 3개**를 포함한다
      in `frontend/tests/MirrorInput.test.ts` (FR-332 · SC-512 · research R3)
- [X] T032 [P] 프레임 없음·끊김 상태에서 사건을 보내지 않는지 검증
      in `frontend/tests/MirrorInput.test.ts` (FR-333 · FR-346)

**Checkpoint**: 조작 통로가 서고, 국면표가 조작 가능성을 정하고, 좌표 변환이 검증된다.
아직 사용자 이야기는 하나도 완성되지 않았다.

---

## Phase 3: User Story 1 — 제품 화면을 벗어나지 않고 녹화한다 (Priority: P1) 🎯 MVP

**Goal**: 미러에서 클릭·스크롤·마우스 올리기를 하고, 그 조작이 Step 으로 쌓이는 것을 같은
화면에서 본다.

**Independent Test**: 대상 앱을 열고 미러에서 버튼 셋을 순서대로 클릭한다. 클릭 Step 이
셋 쌓이고, 각 Step 의 요소 후보가 창에서 직접 클릭했을 때와 같다.

### 원칙 I 증거 — 두 경로 동등성 (가장 중요)

> 이 검증이 깨지면 미러 조작을 켜 둘 수 없다. 기능이 아니라 결함이다.

- [X] T033 [US1] 두 경로 동등성 검증을 만든다 — 같은 화면·같은 조작을 미러 경로와 창
      경로로 하고, 만들어진 Step 의 **종류·값·요소 후보 집합·검증 상태 전부**를 비교한다
      in `backend/tests/integration/test_mirror_recording_parity.py`
      (FR-322~FR-324 · SC-513 · 헌법 원칙 I·IV)

### 구현

- [X] T034 [US1] 포인터 사건(누름·놓음·이동)과 휠을 대상에 전달하고 리코더가 잡는 것을
      확인한다 — 전용 수집 경로를 만들지 않는다 in `backend/src/itb/mirror/input.py`
      (FR-314 · FR-321 · research R1)
- [X] T035 [US1] 미러 영역의 포인터 사건을 채널로 흘린다 — 누름·놓음·이동·휠. 이동은
      전송량을 억제한다(throttle) in `frontend/src/components/mirror/useMirrorInput.ts`
      (FR-314 · FR-336)
- [X] T036 [US1] 조작을 받는 상태·받지 않는 상태를 화면에 구분해 그린다 — 클릭해 보고
      나서 알게 되어서는 안 된다 in `frontend/src/components/MirrorView.tsx` (FR-319)
- [X] T037 [US1] 조작 국면의 미러 문구를 바꾼다 — 「실제 브라우저 창에서 조작 중」은
      `window` 상태의 문구로 옮기고, `mirror` 상태의 문구를 새로 둔다
      in `frontend/src/lib/wording.ts` (FR-350 · T004 의 목록)
- [X] T038 [US1] 조작 후 짧은 시간 안에 프레임이 오지 않으면 한 장을 찍어 보낸다 —
      기존 2초 무프레임 감시를 **조작 국면에서만** 줄인다
      in `backend/src/itb/mirror/screencast.py` (FR-335 · research R8)
- [X] T039 [US1] 조작 국면에서 프레임 ack 가 반드시 흐르게 한다 — ack 가 멈추면 3프레임
      뒤 프레임 밀기가 정지하고, 그것은 사용자에게 「조작해도 화면이 안 바뀐다」로 보인다
      in `backend/src/itb/mirror/screencast.py` (research R8)
- [X] T040 [P] [US1] 관찰 국면에서 조작이 전달되지 않고 사유가 보이는지 검증
      in `frontend/tests/MirrorInput.test.ts` (FR-315 · SC-516)
- [X] T041 [P] [US1] 조작 후 프레임 보충 검증 — 화면이 변하지 않는 조작에서도 현재
      화면이 확인되는지 in `backend/tests/unit/test_mirror_frame_delivery.py` (FR-335)

**Checkpoint**: 창 전환 0회로 클릭·스크롤·호버 녹화가 완결된다 (SC-511). US2 없이도
가치가 있다 — 텍스트 입력만 창에서 하면 된다.

---

## Phase 4: User Story 2 — 미러에서 한글을 입력한다 (Priority: P1)

**Goal**: 미러에 초점이 있을 때 평소처럼 타이핑하고, **조합 중 중간 상태가 대상 입력
요소에 실시간으로 반영**되며, 입력 Step 이 기존과 같은 형태로 쌓인다.

**Independent Test**: 미러에서 검색창을 클릭하고 「주문 내역」을 입력한 뒤 다른 곳을
클릭한다. 대상 검색창에 그 값이 들어가고 입력 Step 하나가 그 값으로 쌓인다.

### 구현

- [X] T042 [US2] 키 사건과 문자 입력을 전달한다 — `key.down`/`key.up`/`text.insert`
      in `backend/src/itb/mirror/input.py` (FR-325)
- [X] T043 [US2] 조합 사건을 전달한다 — `ime.compose` → `Input.imeSetComposition`,
      `ime.commit` → `Input.insertText`. 조합 중 값이 입력 요소에 실시간으로 들어가야
      한다 in `backend/src/itb/mirror/input.py` (FR-327 · research R2)
- [X] T044 [US2] 조합을 조작 채널로 흘리는 프론트 브리지를 만든다 — 로컬 IME 의
      `compositionstart`/`update`/`end` 를 채널 사건으로 옮기고, **다음 키가 앞 키의
      전달 완료를 기다리지 않게** 한다
      in `frontend/src/components/mirror/ImeBridge.tsx` (FR-327a)
- [X] T045 [US2] 미러 영역의 초점 소유를 정한다 — 초점이 있으면 키가 대상으로 가고
      없으면 제품 화면이 받는다. 어느 쪽이 받는 상태인지 화면에서 구분되어야 한다
      in `frontend/src/components/MirrorView.tsx` (FR-320)
- [X] T046 [US2] 조합 중 미러 밖을 클릭했을 때의 처리를 정한다 — 확정할지 버릴지를
      한 곳에서 결정하고 그 결정을 주석으로 남긴다
      in `frontend/src/components/mirror/ImeBridge.tsx` (명세 Edge Cases)
- [X] T047 [US2] 민감 입력이 미러 경로에서도 변수 참조로 저장되는지 확인한다 — 리코더가
      Step 을 만들기 때문에 기존 치환 파이프라인(수집 → 검증 → 치환 → Step → 이벤트)이
      그대로 적용되어야 한다 in `backend/src/itb/mirror/input.py` (FR-329)
- [X] T048 [US2] **FR-328 확인 작업** — 입력만 하고 확정 계기가 없는 상태에서 녹화를
      멈출 때 Step 이 남는지 코드로 확인한다. 리코더의 `change`/`blur` 확정과 150ms
      디바운스 경로 중 무엇이 Step 을 만드는지 밝히고, 남지 않으면 그 자리를 고친다
      in `backend/src/itb/recording/recorder.py` (research 미해결 항목)
- [X] T049 [P] [US2] 조합 중 값이 Step 으로 새지 않는지 검증 — 리코더의 `composing`
      플래그가 조합 중 `input` 을 무시하는 것을 미러 경로에서도 확인한다
      in `backend/tests/integration/test_mirror_recording_parity.py` (FR-326 · FR-327c)
- [X] T050 [P] [US2] 연속 타이핑 유실·순서 검증 — 8자 이상을 연속 입력해 최종 값이
      정확한지 in `backend/tests/integration/test_mirror_recording_parity.py`
      (SC-515b · FR-327b)
- [X] T051 [P] [US2] 민감 값이 화면·이벤트·로그에 평문으로 나타나지 않는지 검증
      in `backend/tests/unit/test_mirror_input.py` (FR-329)

**Checkpoint**: 녹화가 미러 안에서 완결된다 — SC-511 이 온전히 성립한다.

---

## Phase 5: User Story 3 — 실패한 실행을 화면 안에서 이어받는다 (Priority: P2)

**Goal**: 일시정지·인수 국면에서 미러가 곧바로 조작 가능해지고, 같은 화면에서 막힌 곳을
손으로 지나 실행을 이어간다.

**Independent Test**: 일시정지 후 미러에서 요소를 클릭해 화면을 넘기고 재개한다. 재개
이후 Step 이 그 화면을 전제로 정상 진행된다.

### 구현

- [X] T052 [US3] 일시정지·인수 국면에서 채널이 열리게 한다 — 세션 상태(인증·화면·
      입력값)가 유지되어야 한다 in `backend/src/itb/api/ws/control_channel.py`
      (FR-314 · 헌법 원칙 III)
- [X] T053 [US3] 인수 흐름에서 창을 전제한 부분을 미러 조작으로 바꾼다
      in `backend/src/itb/recording/takeover.py` (FR-314)
- [X] T054 [US3] 일시정지 화면에서 미러 조작 수단을 그린다
      in `frontend/src/pages/SessionScreen.tsx` (FR-319)
- [X] T055 [P] [US3] 일시정지 중 미러 조작 후 재개가 정상 진행되는지 검증
      in `backend/tests/integration/test_mirror_takeover.py` (헌법 원칙 III)
- [X] T056 [P] [US3] 실행 중·AI 수행 중 조작이 전달되지 않고 사유가 보이는지 검증
      in `frontend/tests/MirrorInput.test.ts` (FR-315)

**Checkpoint**: 인수인계가 한 화면에서 끝난다.

---

## Phase 6: User Story 4 — 화면에 나타나지 않는 것을 처리한다 (Priority: P2)

**Goal**: 파일 선택과 브라우저 대화상자를 제품 화면이 대신 받아 처리하고, 처리할 수 없는
것은 **조용히 실패하지 않고** 무엇이 막혔는지 말한다.

**Independent Test**: 파일 첨부 요소를 미러에서 클릭하고 제품 화면이 띄운 수단으로 파일을
지정한다. 대상 페이지가 그 파일을 받고 Step 이 쌓인다.

### 브라우저 요구 가로채기

- [X] T057 [US4] `mirror/prompts.py` 를 만든다 — 대화상자를 가로채 관찰 WS 로 알리고
      응답을 대상에 전달한다. **가로채지 않으면 대상 페이지가 멈춘다**는 것이 이 모듈이
      조작 국면에서 항상 켜져 있어야 하는 이유다
      in `backend/src/itb/mirror/prompts.py` (FR-338 · research R7)
- [X] T058 [US4] 파일 선택 요구를 가로채 알린다 — 운영체제 창은 뜨지 않는다
      in `backend/src/itb/mirror/prompts.py` (FR-337 · research R6)
- [X] T059 [US4] 처리 수단이 없는 요구를 `unsupported` 로 알린다 — 인증 요구 팝업 등.
      무엇이 막혔고 어떤 수단이 남아 있는지를 담는다
      in `backend/src/itb/mirror/prompts.py` (FR-339)
- [X] T060 [US4] `browser_prompt`·`browser_prompt_resolved` 이벤트를 관찰 WS 에
      추가한다 — 방향(서버→클라)은 그대로다
      in `backend/src/itb/api/ws/session_events.py` (contracts §4)
- [X] T061 [US4] 요구 응답 엔드포인트를 만든다 — 이미 해소된 요구, 다른 세션의
      `prompt_id` 는 거절한다 in `backend/src/itb/api/routes/control.py`
      (FR-340 · contracts §3)

### 파일 수신

- [X] T062 [US4] 파일 업로드 엔드포인트를 만든다 — 파일당 크기 상한·세션당 개수 상한,
      초과는 **사유와 함께 거절** in `backend/src/itb/api/routes/session_files.py`
      (FR-337a)
- [X] T063 [US4] 저장 경로를 서버 발급 `fileId` 로 만든다 — 사용자가 보낸 이름을 경로에
      쓰지 않는다. 표시 이름은 정리해 따로 둔다
      in `backend/src/itb/storage/paths.py` (FR-337c)
- [X] T064 [US4] 세션 종료·유실 시 업로드 파일을 지운다. 비정상 종료로 남은 것을 정리하는
      경로도 둔다 in `backend/src/itb/api/routes/sessions.py` (FR-337b)
- [X] T065 [US4] `file.attach` 사건으로 파일을 대상에 지정한다 —
      `DOM.setFileInputFiles`. 파일 지정과 그 다음 조작의 순서를 보장하는 방식을 정하고
      주석으로 남긴다 in `backend/src/itb/mirror/input.py`
      (FR-337 · research 미해결 항목)

### 화면

- [X] T066 [US4] 브라우저 요구를 화면에 그린다 — 대화상자 문구는 **대상 페이지에서 온
      값이므로 이스케이프한다.** 파일 고르기 수단을 제시한다
      in `frontend/src/pages/SessionScreen.tsx` (FR-338 · 헌법 보안 요건)
- [X] T067 [US4] 파일 업로드·요구 응답 클라이언트를 추가한다
      in `frontend/src/api/client.ts`
- [X] T068 [P] [US4] 대화상자 가로채기·응답 검증 (헤드리스)
      in `backend/tests/integration/test_browser_prompts.py` (FR-338)
- [X] T069 [P] [US4] 업로드 상한 초과 거절과 세션 종료 후 정리 검증
      in `backend/tests/unit/test_session_files.py` (FR-337a · FR-337b)
- [X] T070 [P] [US4] 파일 이름에 경로 구분자·상위 참조가 들어와도 무해한지 검증
      in `backend/tests/unit/test_session_files.py` (FR-337c)
- [X] T071 [P] [US4] 요구 표시와 응답의 화면 동작 검증
      in `frontend/tests/BrowserPrompt.test.tsx` (FR-338 · FR-339)

**Checkpoint**: 파일 첨부와 대화상자를 포함한 화면의 녹화가 미러 안에서 완결된다 (SC-517).

---

## Phase 7: User Story 5 — 막히면 실제 창으로 내려간다 (Priority: P3)

**Goal**: 실제 창 조작이 폴백으로 남고, **사용자가 누를 때만** 전환된다.

**Independent Test**: 미러가 강등된 상태를 만들고 화면 안내대로 실제 창으로 전환해 조작을
마친다.

### 구현

- [X] T072 [US5] 조작 위치 전환 엔드포인트를 만든다 — `mirror` ↔ `window`. 세션 상태와
      녹화를 유지한다. **서버가 스스로 전환하지 않는다**
      in `backend/src/itb/api/routes/control.py` (FR-349 · FR-353)
- [X] T073 [US5] 창을 띄울 수 없는 환경에서 전환 요청을 **사유와 함께 거절한다**
      in `backend/src/itb/api/routes/control.py` (FR-351)
- [X] T074 [US5] `control_surface` 이벤트를 관찰 WS 에 추가한다
      in `backend/src/itb/api/ws/session_events.py` (contracts §4)
- [ ] T075 [US5] 강등(1 FPS) 상태에서 조작 가능하되 **정확하지 않을 수 있다는 사실과
      전환 수단을 같은 자리에** 둔다 in `frontend/src/components/MirrorView.tsx`
      (FR-345 · FR-353a)
- [ ] T076 [US5] 막힌 상황(`unsupported` 요구·끊김)에서 전환 수단을 그 자리에 그린다
      in `frontend/src/pages/SessionScreen.tsx` (FR-339 · FR-353a)
- [ ] T077 [US5] `window` 상태의 미러 문구를 확정한다 — 「실제 브라우저 창에서 조작 중 ·
      이 영역은 관찰용입니다」가 이 상태의 문구다
      in `frontend/src/lib/wording.ts` (FR-350 · M-05)
- [ ] T078 [P] [US5] 전환 후 세션 상태·녹화 유지 검증
      in `backend/tests/integration/test_control_surface.py` (FR-349)
- [ ] T079 [P] [US5] 창을 띄울 수 없는 환경에서 거절 사유가 오는지 검증
      in `backend/tests/integration/test_control_surface.py` (FR-351)
- [ ] T080 [P] [US5] 제품이 스스로 창을 열지 않는지 검증 — 강등·`unsupported` 발생만으로
      전환이 일어나지 않아야 한다 in `backend/tests/integration/test_control_surface.py`
      (FR-353)

**Checkpoint**: 막힌 사용자에게 남는 수단이 있다. 다섯 이야기 전부 성립한다.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T081 조작할 수 없는 **모든** 상황에서 사유가 화면에 있는지 전수 확인하는 검증을
      만든다 — 관찰 국면·프레임 없음·끊김·강등·채널 미접속·세션 종료·`unsupported`.
      조용한 실패 0건 in `frontend/tests/abnormal/mirror-control-blockers.test.tsx`
      (SC-516)
- [ ] T082 [P] 001 의 계약 문서에 개정 표시를 남긴다 — `contracts/websocket.md` 와
      `spec.md` 의 FR-047a·clarify 결정 3 자리에 010 이 개정했다는 것과 그 위치
      in `specs/001-interactive-ai-test-builder/`
- [ ] T083 [P] 시각 언어 정본과의 정합성을 확인한다 — 미러의 새 상태 표시가 정본을
      벗어나지 않는지 (`python3 scripts/extract_canon.py --check`)
- [ ] T084 [P] `docs/` 에 조작 위치 개념을 반영한다 — 창이 기본이 아니게 되었다는 것과
      전환 방법
- [ ] T085 임포트 경계를 확인한다 (`uv run lint-imports`) — `mirror/input.py` 가
      `screencast.py` 를 임포트하지 않고, 그 역도 아닌지 (research R5)
- [ ] T086 지연을 실측해 기준선과 비교하는 검증을 둔다 — 클릭 → 프레임 중앙값 25ms·
      최대 43ms 에서 멀어졌으면 ack 흐름을 먼저 의심한다.
      `timing` 마커를 붙인다 in `backend/tests/integration/test_mirror_input_latency.py`
      (SC-514 · research R8)
- [ ] T087 검증 절차 전체를 실행해 통과 조건을 확인한다 in
      `specs/010-headless-mirror-control/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존 없음. 즉시 시작
- **Foundational (Phase 2)**: Setup 완료 후. **모든 사용자 이야기를 막는다**
- **US1 (Phase 3)**: Foundational 완료 후
- **US2 (Phase 4)**: Foundational 완료 후. US1 과 독립적으로 진행 가능하나, 두 경로 동등성
  검증(T033)을 US1 이 세우므로 **T033 이후가 유리하다**
- **US3 (Phase 5)**: Foundational 완료 후. 조작 전달 자체는 US1 의 T034~T035 에 의존
- **US4 (Phase 6)**: Foundational 완료 후. US1~US3 과 독립
- **US5 (Phase 7)**: Foundational 완료 후. US4 의 `unsupported`(T059)와 함께 쓰면 가치가
  커지지만 독립적으로 완성 가능
- **Polish (Phase 8)**: 원하는 이야기가 모두 끝난 후

### 이 기능의 특이점 — Foundational 이 두꺼운 이유

조작 경로 자체가 없기 때문이다. 통로(T016~T023)·좌표 변환(T028·T031)·국면표(T024~T026)는
US1~US5 가 전부 공유하며, 이 중 하나라도 빠지면 어떤 이야기도 완성되지 않는다. 통로를
이야기별로 쪼개면 같은 통로를 다섯 번 만들게 된다.

### Within Each User Story

- 검증을 먼저 쓰고 실패를 확인한 뒤 구현한다
- 백엔드 전달 → 프론트 전송 → 화면 표시 순
- **T033(두 경로 동등성)은 US1 의 첫 작업이다** — 원칙 I 증거이므로 나중으로 밀지 않는다

### Parallel Opportunities

- Phase 1: T003·T004 병렬
- Phase 2: T007·T008 / T013·T014·T015 / T021·T022·T023 / T026 / T031·T032 각 묶음 병렬
- Phase 3: T040·T041 병렬
- Phase 4: T049·T050·T051 병렬
- Phase 5: T055·T056 병렬
- Phase 6: T068·T069·T070·T071 병렬
- Phase 7: T078·T079·T080 병렬
- Phase 8: T082·T083·T084 병렬

---

## Parallel Example: Phase 2 조작 모듈 검증

```bash
Task: "screencast.py 가 Input 명령을 보내지 않는지 (T013)"
Task: "명령 목록 한정 검증 (T014)"
Task: "미해제 포인터 해제 검증 (T015)"
```

---

## Implementation Strategy

### MVP (US1 까지)

1. Phase 1 Setup — 헤드리스 기본값 전환
2. Phase 2 Foundational — **조작 통로** (이 기능의 실질적 무게중심)
3. Phase 3 US1 — 클릭·스크롤·호버 녹화
4. **정지하고 검증**: T033 이 통과하는가? 통과하지 않으면 **여기서 멈춘다** — 원칙 I
   위반이므로 앞으로 나가면 안 된다
5. 텍스트 입력만 실제 창에서 하는 상태로도 쓸 수 있다

### Incremental Delivery

1. Setup + Foundational → 통로 준비
2. US1 → 녹화의 대부분이 미러 안에서 (MVP)
3. US2 → 녹화가 미러 안에서 완결 (SC-511 온전히 성립)
4. US3 → 인수인계도 한 화면에서
5. US4 → 파일·대화상자 화면까지 완결 (SC-517)
6. US5 → 막힌 사용자에게 수단이 남는다

### 멈춰야 하는 조건

- **T033(두 경로 동등성)이 통과하지 않으면 US2 로 가지 않는다.** 원칙 I 은 이 기능의
  전제이며 나중에 고칠 수 있는 항목이 아니다.
- **T002·T030 개정에서 기존 검증을 삭제하고 싶어지면 멈춘다.** 방향을 바꾸는 것과
  지우는 것은 다르다 (헌법 품질 게이트 4).

---

## Notes

- `[P]` = 다른 파일, 미완료 작업에 의존하지 않음
- **개정 작업 3건**(T002·T003·T030)은 삭제가 아니라 방향 전환이다. 무엇이 왜 뒤집혔는지를
  코드에 남긴다
- 각 작업 또는 논리적 묶음 후 커밋한다
- Step DSL 을 바꾸는 작업은 이 목록에 **하나도 없다.** 생기면 원칙 I 위반을 의심한다
