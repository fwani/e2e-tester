# WebSocket Event Contract

**경로**: `/ws/sessions/{session_id}`
**방향**: **서버 → 클라이언트 단방향.** 클라이언트는 명령을 보내지 않는다 (contracts/README.md 참조).
**형식**: 이벤트 하나 = JSON 객체 하나. 모든 이벤트에 `type` 과 `seq`(단조 증가 정수)가 있다.

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
| `state_changed` | `{ state, current_step_index }` | 헤더 배지 (`RUNNING`/`PAUSED`/`AI 수행 중`/`사람이 녹화 중`) | FR-033, data-model §8 |
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
| `tab_limit_reached` | `{ limit }` | FR-030g |

## AI 이벤트

| `type` | 페이로드 | 화면 대응 | 요구사항 |
|--------|----------|-----------|----------|
| `ai_progress` | `{ message }` | AI가 무엇을 하는 중인지 | FR-060 |
| `ai_blocked` | `{ attempted, reason, choices: ["takeover","retry","skip","abort"] }` | 실패 카드 + 4선택지 | FR-069, FR-070 |
| `ai_finished` | `{ step_count }` | "테스트로 저장" 활성화 | FR-063 |
| `ai_error` | `{ reason }` | 언어모델 호출 실패. Step은 보존됨 | FR-067 |

**`ai_*` 이벤트는 작성 세션에서만 나간다.** `replay` 모드 세션에서 `ai_*` 이벤트가 관측되면
원칙 II 위반이다. 이를 테스트로 검증한다 (SC-006).

---

## 민감 값 취급

**어떤 이벤트도 복호화된 민감 값을 담지 않는다** (FR-089d). `step_added` 의 `fill` Step은 민감 변수를
`{{LOGIN_PASSWORD}}` 참조로만 담는다. `step_failed` 의 `error_message` 는 디스크에 쓰기 전과 동일한
로그 스크러버를 통과한 뒤 전송된다 (research R7).
