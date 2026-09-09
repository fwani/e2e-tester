# Implementation Plan: 대상 브라우저를 제품 화면 안에서 조작한다

**Branch**: `010-headless-mirror-control` | **Date**: 2026-09-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-headless-mirror-control/spec.md`

## Summary

조작 국면에서 사용자가 **제품 화면 안 미러 영역에서 직접 조작**하게 만든다. 대상 브라우저는
창 없이 띄우는 것이 기본이 되고, 실제 창은 사용자가 명시적으로 요청하는 폴백으로 남는다.

**접근**: 화면을 보내는 절반은 이미 있다 (`mirror/screencast.py`). 이 기능은 **반대 방향
하나를 새로 만들고, 기존 절반은 성질을 유지한 채 좌표 정보만 확장한다.**

- 조작은 `mirror/input.py` 가 담당한다. `screencast.py` 는 `Input` 을 여전히 모르는
  모듈로 남는다 (research R5).
- 조작 사건은 **새 WebSocket** 으로 받는다. 기존 관찰 소켓의 단방향 계약을 깨지 않는다
  (research R4).
- 좌표 역변환은 프레임에 `pageScale`·`offsetTop`·`seq` 를 더해 클라이언트가 한다
  (research R3).
- Step 은 **기존 리코더가 그대로 만든다.** 미러 조작 전용 수집 경로를 만들지 않는다
  (research R1 — 실측으로 확인).

**설계를 좌우한 두 실측** (research R1·R2):

| 확인한 것 | 결과 | 이것이 없으면 |
|---|---|---|
| 주입한 입력이 대상 페이지에서 신뢰된 이벤트가 되는가 | `isTrusted: true` — 클릭·호버·휠·문자 입력 전부 | FR-321~FR-324 불성립 → 범위 재검토 |
| 조합 중인 한글을 원격으로 전달할 수 있는가 | `Input.imeSetComposition` 이 중간 상태를 그대로 만든다. 8자 26.7ms | FR-327 불성립 → 확정만 전달로 후퇴 |

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript + React (frontend)

**Primary Dependencies**: FastAPI, Playwright for Python (CDP 직접 사용), React

**Storage**: 없음 — 이 기능은 저장 형식을 바꾸지 않는다 ([data-model.md](data-model.md)
「저장 형식 변경 요약」). 업로드된 파일만 세션 범위 임시 저장소에 두고 세션과 함께 지운다.

**Testing**: pytest (backend, 계층별 tier 분류 있음), vitest (frontend)

**Target Platform**: 로컬 실행. **이 기능 이후 화면 없는 기계에서도 전체 흐름이 동작한다**
(SC-518). 루프백 바인딩 전제는 유지한다 (FR-343).

**Project Type**: web application (backend + frontend)

**Performance Goals**: 조작 → 화면 반영이 사용자가 같은 곳을 다시 누르지 않을 만큼 짧을 것
(SC-514). 실측 기준선: 로컬 헤드리스에서 클릭 → 프레임 도착 **중앙값 약 25ms, 최대 43ms,
12/12 성공** (research R8). 조합 중 입력은 키당 3.3ms (research R2).

**Constraints**:
- 조작 채널과 프레임 통로가 서로를 막지 않아야 한다 (FR-336).
- 조작 채널 장애가 실행을 실패시켜서는 안 된다 (FR-348 · FR-047b 유지).
- 채널이 받을 수 있는 것은 정해진 사건 목록으로 한정되어야 한다 (FR-344).

**Scale/Scope**: 요구사항 49건(FR-314~FR-353 + 하위), 성공 기준 11건. 사용자 이야기 5개.
백엔드 신규 모듈 2~3개, 기존 모듈 수정 6~8개, 프론트 신규 1~2개, 기존 수정 4~6개,
개정되는 기존 검증 2건.

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 후 재확인.*

### I. Unified Step Model (NON-NEGOTIABLE) — 통과

미러 조작이 Step 모델에 **아무것도 더하지 않는다.**

- 근거 1 (구조): 조작 사건은 대상 브라우저의 입력으로 변환될 뿐이고, Step 은 **기존
  리코더가 대상 페이지에서 만든다.** 서버가 조작 사건을 Step 으로 변환하는 경로를 만들지
  않는다 ([contracts/mirror-control.md](contracts/mirror-control.md) §2 — 조작 채널은
  Step 을 만들지 않는다).
- 근거 2 (실측): 주입한 입력이 대상 페이지에서 `isTrusted: true` 이벤트가 되고, 리코더는
  `isTrusted` 를 검사하지 않는다 (research R1). 즉 미러 조작과 창 조작이 리코더에게
  **구분되지 않는다** — 두 경로가 다른 Step 을 낼 구조가 없다.
- 근거 3 (검증): FR-324 가 그 동등성을 자동 검증으로 고정하도록 요구한다. tasks 에서
  「같은 화면·같은 조작을 두 경로로 하면 같은 Step 이 나온다」는 검증이 작업이 된다.
- 근거 4 (저장): [data-model.md](data-model.md) 의 「저장 형식 변경 요약」이 전부 「없음」이다.

### II. Deterministic Replay (NON-NEGOTIABLE) — 통과 (해당 없음)

이 기능은 **재실행 경로를 건드리지 않는다.** 조작 채널은 조작 국면에서만 열리고
(FR-342), 저장된 테스트를 실행하는 경로에 언어모델 호출을 새로 만들지 않는다. 조작
채널이 받는 사건 목록에 모델 호출로 이어지는 것이 없다 (contracts §2).

### III. Stateful Interactive Runner — 통과 (강화)

- 일시정지·인수 국면에서 미러 조작이 가능해지므로(FR-314·US3), 사람이 세션을 이어받는
  경로가 **짧아진다.** 세션 상태 유지 요건은 그대로다.
- 실제 창으로 전환할 때도 세션 상태(인증·화면·입력값)와 녹화가 유지되어야 한다 (FR-349).
- 조작 채널의 어떤 상태 전이도 실행 상태 기계를 전이시키지 않는다 (contracts §5 불변식 4).

### IV. Locator Resilience — 통과

- 미러에서 만든 Step 의 요소 후보 집합과 검증 상태가 창 조작과 **같아야 한다** (FR-322).
  이는 후보 수집이 기존 경로 그대로이기 때문에 성립한다 — 후보는 살아 있는 페이지에서
  리코더가 수집한다.
- 좌표는 **입력을 어디로 보낼지**만 정하고, **요소를 무엇으로 식별할지**에는 관여하지
  않는다. 좌표가 Step 에 저장되지 않는다 (data-model §1 — 조작 사건은 저장되지 않는다).
  이 분리가 원칙 IV 를 지키는 자리다.

### V. Asset Portability — 통과 (영향 없음)

Step DSL 이 바뀌지 않으므로 내보내기 대응도 바뀌지 않는다. 이 기능은 **조작 수단**의
변경이며 자산 형식의 변경이 아니다.

### Technology & Security Constraints — 통과

| 요건 | 이 기능에서 |
|---|---|
| 비밀값 하드코딩 금지 | 해당 없음 — 새 비밀값을 도입하지 않는다 |
| 민감 입력의 변수 참조 저장·마스킹 | FR-329. 미러 경로도 **기존 치환 파이프라인을 지난다** — 리코더가 Step 을 만들기 때문에 치환 순서(수집 → 검증 → 치환 → Step → 이벤트)가 그대로 적용된다 |
| 모든 외부 입력의 경계 검증 | FR-341 (조작 사건), FR-337a·c (업로드 파일), contracts §4 (대화상자 문구는 대상 페이지에서 온 값 — 표시 시 이스케이프) |
| 브라우저를 넘는 권한 금지 | FR-344 · contracts §2 의 사건 목록이 상한이다. 임의 CDP 명령·페이지 스크립트 실행 경로가 없다 |
| 접근 범위 확대 금지 | FR-343. 루프백 바인딩 전제를 유지한다. 새 엔드포인트도 같은 서버·같은 바인딩이다 |
| 명시적 오류 처리 | FR-339·FR-345~FR-347 · SC-516 — 조작할 수 없는 모든 상황에서 사유가 화면에 있어야 한다. 조용한 실패가 0건이어야 한다 |

### Development Workflow & Quality Gates

| 게이트 | 계획 |
|---|---|
| 1. 원칙 준수 | 위 표. 재실행 경로 무영향 근거는 II 에 명시 |
| 2. 왕복 정합성 | Step DSL 이 안 바뀌므로 기존 왕복 검증이 그대로 유효하다. **추가로** FR-324 의 두 경로 동등성 검증을 넣는다 |
| 3. 테스트 | 조작 사건 검증(단위), 채널 상태 전이(단위), 좌표 역변환(단위), 두 경로 동등성(통합), 국면별 조작 가능성(프론트 단위), 조작 채널 장애 주입(통합, SC-519) |
| 4. 비활성 테스트 금지 | **개정되는 검증 2건은 삭제하지 않고 방향을 바꾼다** (research R10 · 아래 Complexity Tracking) |
| 5. 성공 지표 영향 | 테스트 작성 시간과 인수인계 복구 시간(PRD §18)에 직접 영향. SC-511·SC-514 가 그 대리 지표다 |

**게이트 통과.** 위반 없음. 아래 Complexity Tracking 은 위반이 아니라 **기존 결정을
뒤집는 변경의 근거**를 남기기 위한 것이다.

## Project Structure

### Documentation (this feature)

```text
specs/010-headless-mirror-control/
├── plan.md                      # 이 파일
├── spec.md                      # 요구사항 (FR-314~FR-353, SC-511~SC-519)
├── research.md                  # Phase 0 — 실측 R1~R10
├── data-model.md                # Phase 1 — 전송·표시 모델 (저장 변경 없음)
├── quickstart.md                # Phase 1 — 검증 절차
├── contracts/
│   └── mirror-control.md        # Phase 1 — 국면표·조작 채널·REST·관찰 WS 변경
├── checklists/
│   └── requirements.md          # 명세 품질 체크리스트
└── tasks.md                     # Phase 2 (/speckit-tasks 가 만든다)
```

### Source Code

```text
backend/src/itb/
├── mirror/
│   ├── screencast.py            # 수정 — 프레임 페이로드에 pageScale·offsetTop·seq 추가
│   │                            #        Input 을 모르는 모듈로 남는다 (목록 유지)
│   ├── tab_switch.py            # 수정 — 보고 있는 탭을 조작 대상으로 넘긴다 (FR-317)
│   ├── input.py                 # 신규 — CDP Input 전용. 자기 명령 목록을 가진다
│   └── prompts.py               # 신규 — 대화상자·파일 선택 가로채기와 응답
├── api/
│   ├── ws/
│   │   ├── session_events.py    # 수정 — browser_prompt·control_surface 이벤트 추가
│   │   │                        #        방향(서버→클라)은 그대로
│   │   └── control_channel.py   # 신규 — 조작 전용 WS. 국면에 따라 열리고 닫힌다
│   └── routes/
│       ├── sessions.py          # 수정 — 조작 채널 엔드포인트 등록, 국면 전이 시 채널 정리
│       ├── control.py           # 신규 — 조작 위치 전환·브라우저 요구 응답 (REST)
│       └── session_files.py     # 신규 — 파일 업로드 (상한·정리·검증)
├── execution/
│   ├── session.py               # 수정 — headless 기본값 전환 (FR-352)
│   └── state_machine.py         # 수정 — 조작 국면 판정을 채널 개폐에 노출
└── storage/
    └── paths.py                 # 수정 — 세션 범위 파일 저장 위치

backend/tests/
├── unit/
│   ├── test_test_tiers.py       # **개정** — headless 기본값 검증 2건의 방향 전환
│   ├── test_mirror_input.py     # 신규 — 사건 목록 한정·경계 검증·좌표 변환
│   └── test_control_channel.py  # 신규 — 상태 전이·국면별 개폐
├── integration/
│   ├── test_mirror_recording_parity.py  # 신규 — 두 경로 동등성 (FR-324, 원칙 I 증거)
│   └── test_control_channel_failure.py  # 신규 — 채널 장애 주입 (SC-519)
└── conftest.py                  # 수정 — _headless_browsers 픽스처의 의미 재정리

frontend/src/
├── components/
│   ├── MirrorView.tsx           # 수정 — 조작을 받는 상태를 props 로 받는다.
│   │                            #        스스로 국면을 보지 않는다 (FR-316)
│   └── mirror/
│       ├── useMirrorInput.ts    # 신규 — 표시 좌표 → 대상 좌표 변환, 사건 전송
│       └── ImeBridge.tsx        # 신규 — 조합 중 상태를 조작 채널로 흘린다
├── lib/
│   ├── capabilities.ts          # 수정 — 미러 조작·창 전환을 조작 항목으로 추가
│   └── wording.ts               # 수정 — 「실제 창에서 조작 중」을 window 상태의 문구로
├── api/
│   ├── ws.ts                    # 수정 — 새 프레임 필드, browser_prompt 수신
│   ├── control.ts               # 신규 — 조작 채널 클라이언트
│   └── client.ts                # 수정 — 파일 업로드·요구 응답·조작 위치 전환
└── pages/
    └── SessionScreen.tsx        # 수정 — 브라우저 요구 표시, 조작 위치 전환 수단

frontend/tests/
├── MirrorView.test.tsx          # **개정** — 「입력을 전달하지 않는다」 검증의 방향 전환
├── MirrorInput.test.ts          # 신규 — 좌표 변환·국면별 전달 여부
└── BrowserPrompt.test.tsx       # 신규 — 대화상자·파일 선택 표시
```

**Structure Decision**: 기존 web application 구조(`backend/` + `frontend/`)를 그대로 쓴다.
새 디렉터리는 만들지 않는다 — `mirror/` 와 `api/ws/` 에 모듈을 더한다.

**모듈을 나눈 기준은 「무엇을 모르는가」다.** `screencast.py` 는 `Input` 을 모르고,
`input.py` 는 프레임을 모른다. 이 분리가 FR-336(서로 막지 않음)과 research R5(읽기 전용
미러 모듈의 성질 보존)를 파일 경계로 만든다.

## Complexity Tracking

이 기능은 헌법 원칙을 위반하지 않는다. 아래는 **기존 결정을 뒤집는 변경**과 **개정되는
검증**의 근거다 — 헌법 「Governance → Compliance review」가 요구하는 기록이다.

| 뒤집는 것 | 왜 필요한가 | 유지되는 것 · 대신 두는 장치 |
|---|---|---|
| **FR-047a** — 미러는 입력을 전달하지 않는다 | 조작 국면마다 제품 화면과 브라우저 창을 오가는 왕복이 발생하고, 창 전제가 화면 없는 기계에서의 사용을 막는다 (SC-511·SC-518) | 관찰 국면에서는 종전대로 전달하지 않는다. 전달 가능 여부를 화면이 아니라 **채널이** 강제한다 (FR-342). 채널이 받는 사건은 목록으로 한정된다 (FR-344) |
| **clarify 결정 3** — 조작은 실제 창에서 | 같은 이유 | 실제 창 조작이 **폴백으로 남는다** (FR-349~FR-353). 사용자가 누를 때만 전환한다 |
| **`headless_default()` 기본값** (`False` → `True`) | 미러가 조작 수단이 되면 창은 기본으로 필요하지 않다. 창이 기본이면 화면 없는 기계에서 제품이 뜨지 않는다 | 창을 띄우는 것은 환경 변수로 명시했을 때만. **알 수 없는 값·오타는 기본값(헤드리스)으로 붙는다** — 기존 검증이 지키던 「조용히 사라지지 않는다」의 대상이 창에서 **미러의 조작 가능성**으로 옮겨간다 |
| **기존 검증 2건 개정** (`test_test_tiers.py`) | 위 기본값 전환이 그 검증을 필연적으로 깨뜨린다 | **삭제하지 않는다** (헌법 품질 게이트 4). 같은 파일에서 **반대 방향을 검증**하도록 바꾼다. 개정 커밋에 「무엇이 왜 뒤집혔는지」를 남긴다 |
| **`MirrorView.test.tsx` 개정** | 「입력을 전달하는 코드가 없다」를 검증하던 항목이 이 기능의 요구와 정면으로 충돌한다 | 삭제하지 않는다. **관찰 국면에서 전달하지 않는다**를 검증하도록 바꾼다 — 지키려던 성질은 국면 조건과 함께 남는다 |

**개정이 관행이 되지 않게 하는 조건** (헌법 Governance): 이 기능은 001 의 결정을 뒤집는
것이고, 뒤집는 근거를 spec.md 「이 기능이 뒤집는 것」에 출처와 함께 남겼다. FR-047b~e 는
개정하지 않는다 — 뒤집는 범위를 명시적으로 좁혔다는 것이 기록이다.

## Phase 1 후 Constitution 재확인

Phase 1 산출물([data-model.md](data-model.md), [contracts/mirror-control.md](contracts/mirror-control.md))
작성 후 재평가했다.

| 원칙 | 재확인 결과 | 설계상의 증거 |
|---|---|---|
| I | 통과 | data-model 「저장 형식 변경 요약」이 전부 「없음」. contracts §2 에 Step 생성 경로가 없다 |
| II | 통과 | 조작 채널 사건 목록에 모델 호출로 이어지는 것이 없다 |
| III | 통과 | contracts §5 불변식 4 — 채널 상태가 실행 상태 기계를 전이시키지 않는다 |
| IV | 통과 | 좌표는 저장되지 않고 요소 식별에 관여하지 않는다 (data-model §1) |
| V | 통과 | Step DSL 무변경 → 내보내기 무영향 |
| 보안 | 통과 | contracts §2 의 사건 목록이 상한. §3 의 업로드 상한·경로 발급. §4 의 대상 페이지 문구 이스케이프. §5 불변식 6 — 접근 범위 불변 |

**설계 후 새로 드러난 것 하나**: 끌어놓기 중 채널이 끊기면 대상 페이지가 누른 상태로
남는다. 클라이언트의 성실함에 맡기면 안 되므로 **서버가 채널을 닫을 때 미해제 포인터에
`pointer.up` 을 보낸다** (contracts §2). FR-318 을 서버 쪽 불변식으로 옮긴 것이다.
