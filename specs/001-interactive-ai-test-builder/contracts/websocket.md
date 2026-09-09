# WebSocket Event Contract

**경로**: `/api/sessions/{session_id}/events`
**방향**: **서버 → 클라이언트 단방향.** 클라이언트는 명령을 보내지 않는다 (contracts/README.md 참조).
**형식**: 이벤트 하나 = JSON 객체 하나. 모든 이벤트에 `type` 과 `seq`(단조 증가 정수)가 있다.

> **010 이 이 계약을 개정하지 **않았다**는 기록** (2026-09-09).
>
> 010「대상 브라우저를 제품 화면 안에서 조작한다」는 미러에서 대상 브라우저를 조작하게
> 만든다. 그것이 이 소켓의 단방향 계약을 깨는 것처럼 보이지만 **깨지 않는다** — 조작은
> **새 소켓**(`/api/sessions/{session_id}/control`)으로 받는다.
>
> 나눈 이유는 둘이다 (010 research R4). ① 한 소켓이 프레임 밀기와 조작 받기를 같이 하면
> 조작 폭주가 프레임 전달을 막고 그 역도 성립한다. ② 조작 채널이 끊겨도 관찰은 그대로여야
> 하고, 그 역도 같다 (FR-047b 가 지키던 성질이다).
>
> 이 소켓에 010 이 더한 것은 **이벤트 셋뿐**이며 방향은 그대로다 —
> `browser_prompt`·`browser_prompt_resolved`·`control_surface`, 그리고 `mirror_frame` 의
> 필드 추가(`pageScale`·`offsetTop`·`frameSeq`). 계약은
> `specs/010-headless-mirror-control/contracts/mirror-control.md` §4 에 있다.

> **경로 결정 (T160, 2026-09-03)**: 초안은 `/ws/sessions/{sid}` 였다. 구현은 세션 리소스
> 아래(`/api/sessions/{sid}/events`)에 두었고 그 쪽을 계약으로 확정한다. 근거는 두 가지다 —
> ① 클라이언트→서버 표면이 `/api` 하나로 유지되어 개발 서버 프록시 규칙과 바인딩 정책
> (FR-088a)이 한 곳에서 끝난다. ② 이벤트는 세션의 하위 리소스이므로 경로가 소유 관계를
> 그대로 드러낸다. 별도 `/ws` 접두사는 전송 방식을 리소스 이름에 섞는 것이다.

```json
{ "type": "step_finished", "seq": 42, "...": "..." }
```

**재연결**: 연결이 끊기면 클라이언트는 `GET /api/sessions/{sid}` 로 전체 상태를 다시 받고 재연결한다.
서버는 이벤트를 버퍼링하거나 재전송하지 않는다 — 단독 로컬 도구이므로 전체 상태를 다시 받는 것이 싸고,
재전송 버퍼는 유실 시 조용히 어긋나는 상태를 만든다.

---

## 상태 이벤트

| `type` | 페이로드 | 화면 대응 | 요구사항 |
|--------|----------|-----------|----------|
| `state_changed` | `{ state, current_step_index, active_tab }` | 헤더 배지 (`RUNNING`/`PAUSED`/`AI 수행 중`/`사람이 녹화 중`) | FR-033, data-model §8 |
| `session_lost` | `{ reason }` | 세션 유실 안내. Step은 보존됨 | FR-041 |
| `edit_warning` | `{ messages: [...] }` | 편집이 화면에 적용되지 않았다는 경고 | FR-040b |

## Step 목록 이벤트

| `type` | 페이로드 | 요구사항 |
|--------|----------|----------|
| `step_added` | `{ step, at_index }` | FR-024, FR-036, FR-061, FR-079 |
| `step_updated` | `{ step }` | FR-035 |
| `step_removed` | `{ step_id }` | FR-035 |
| `steps_reordered` | `{ order: [step_id, ...] }` | FR-035 |

`step_added` 는 녹화 중 사용자 동작, AI 성공 동작, 자연어 Step 추가에서 **모두 같은 이벤트**로 나간다.
프론트에 작성 주체별 분기가 없어야 한다 — 원칙 I을 UI 계층까지 밀어 놓는 장치다.
Step 안의 `author` 필드는 배지 표시용이다 (FR-014, FR-075).

## 실행 이벤트

| `type` | 페이로드 | 화면 대응 | 요구사항 |
|--------|----------|-----------|----------|
| `step_started` | `{ step_id, index, tab }` | 현재 실행 중 표시 + 브라우저 오버레이 | FR-046, FR-047 |
| `step_finished` | `{ step_id, index, outcome, duration_ms, resolved_candidate }` | 체크·소요 시간 | FR-046, FR-051 |
| `step_failed` | `{ step_id, index, error_message, locator_attempts, tab_wait_ms }` | 실패 상세 | FR-021, FR-054 |
| `run_finished` | `{ outcome, total_ms, passed_count, total_count, failed_step_index }` | 결과 요약 | FR-048, FR-050 |

## 미러 이벤트

| `type` | 페이로드 | 요구사항 |
|--------|----------|----------|
| `mirror_frame` | `{ tab, data: "<base64 jpeg>", width, height }` | FR-047 |
| `mirror_tab_changed` | `{ tab }` | FR-030f, FR-047c |
| `mirror_degraded` | `{ mode: "screenshot", reason }` | research R3 폴백 |
| `mirror_stopped` | `{ reason }` | FR-047b |

**`mirror_frame` 은 유실 가능한 이벤트로 취급한다.** 프론트는 마지막 프레임만 그리면 되고,
서버는 프레임 전송 실패를 실행에 반영하지 않는다 (FR-047b). `mirror_*` 이벤트가 끊겨도
`step_*` 이벤트는 계속 흐른다 — 두 스트림이 같은 연결을 쓰더라도 논리적으로 독립이다.

## 탭 이벤트

| `type` | 페이로드 | 요구사항 |
|--------|----------|----------|
| `tab_opened` | `{ tab, url, title }` | FR-030a |
| `tab_closed` | `{ tab }` | FR-030c |
| `tab_limit_reached` | `{ limit, message }` | FR-030g |

`tab_opened` 의 `title` 은 **막 열린 탭에서 빈 문자열일 수 있다.** 문서가 아직 로드되지
않았기 때문이다. 클라이언트는 `GET /api/sessions/{sid}/tabs` 로 최신 제목을 받는다.

**탭 닫힘은 `tab_closed` 이벤트를 항상 만들고, `close_tab` Step 은 조건부로 만든다.**
이벤트는 지금 열린 탭 목록을 갱신하는 신호이고, Step 은 재실행 때 같은 닫기를 재현하는
정의다 (FR-030c). Step 이 만들어지지 않는 두 경우:

- **녹화 중이 아닐 때.** 재실행 중 `close_tab` Step 이 탭을 닫는 것이 다시 Step 을 만들면
  실행이 정의를 늘린다.
- **그 탭의 클릭이 닫음을 유발했을 때.** 페이지 안의 "닫기" 버튼을 누른 것은 이미 클릭
  Step 으로 남아 있고 재실행 때 그 클릭이 같은 닫힘을 만든다. 두 Step 을 모두 남기면 한
  사건이 두 번 표현된다 — 클릭이 유발한 화면 이동을 억제하는 것(FR-030b)과 같은 판정이다.

실행 시 `close_tab` 은 **목표 상태 기준으로 판정한다.** 대상 탭이 이미 닫혀 있거나 열리지
않았으면 통과다 — 이 Step 의 목표는 "그 탭이 열려 있지 않음" 이고 그 상태는 이미 충족돼
있다. `hidden` 검증이 처음부터 없던 요소도 통과시키는 것과 같은 규칙이다.

## AI 이벤트

| `type` | 페이로드 | 화면 대응 | 요구사항 |
|--------|----------|-----------|----------|
| `ai_progress` | `{ message }` | AI가 무엇을 하는 중인지 | FR-060 |
| `ai_blocked` | `{ attempted, reason, choices: ["takeover","retry","skip","abort"] }` | 실패 카드 + 4선택지 | FR-069, FR-070 |
| `ai_finished` | `{ step_count }` | "테스트로 저장" 활성화 | FR-063 |
| `ai_error` | `{ reason }` | 언어모델 호출 실패. Step은 보존됨 | FR-067 |

## 진단 이벤트

| `type` | 페이로드 | 화면 대응 | 요구사항 |
|--------|----------|-----------|----------|
| `run_error` | `{ reason }` | 실행이 예상 못한 오류로 끝났거나 **결과를 기록하지 못했다** | FR-087 |
| `artifact_note` | `{ message }` | 산출물을 남기지 못한 사유 (스크린샷 촬영 실패 등) | FR-052, FR-053 |

두 이벤트는 **조용한 실패를 막기 위해 존재한다.** 결과 파일을 쓰지 못했거나 스크린샷을
남기지 못한 것은 실행 자체를 멈출 이유는 아니지만, 사용자가 모르면 "산출물이 원래 없는
것"으로 오인한다 (헌법 §보안 — 오류는 명시적으로 처리한다).

**`ai_*` 이벤트는 작성 세션에서만 나간다.** `replay` 모드 세션에서 `ai_*` 이벤트가 관측되면
원칙 II 위반이다. 이를 테스트로 검증한다 (SC-006).

---

## 민감 값 취급

**어떤 이벤트도 복호화된 민감 값을 담지 않는다** (FR-089d). `step_added` 의 `fill` Step은 민감 변수를
`{{LOGIN_PASSWORD}}` 참조로만 담는다. `step_failed` 의 `error_message` 는 디스크에 쓰기 전과 동일한
로그 스크러버를 통과한 뒤 전송된다 (research R7).
