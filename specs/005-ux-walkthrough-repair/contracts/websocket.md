# Contract: WebSocket 이벤트 (005 라운드 변경분)

**Feature**: `specs/005-ux-walkthrough-repair` | **Date**: 2026-09-07

001 의 [`contracts/websocket.md`](../../001-interactive-ai-test-builder/contracts/websocket.md)
를 **확장한다.** 새 이벤트 타입은 없다. `mirror_frame` 의 전송 시점이 늘고,
`run_finished` 의 `outcome` 값이 늘어난다.

**단방향(서버 → 클라이언트) 원칙은 유지된다.** 클라이언트가 명령을 보내는 경로를 만들지
않는다.

---

## 1. `mirror_frame` — 구독 직후 한 장을 보낸다

### 변경 전

CDP 스크린캐스트가 만든 프레임을 그때그때 발행했다. 구독자가 없으면 버렸다.
스크린캐스트는 **화면이 변할 때만** 프레임을 만들므로, 유일한 초기 프레임이 구독 전에
버려지면 정적 화면에서는 한 장도 도달하지 않았다 (U-24, 실측 0건).

### 변경 후 — 두 가지가 추가된다

**(a) 구독 시 마지막 프레임 1장**

새 구독자가 붙으면 그 세션의 **마지막 프레임 한 장**을 즉시 보낸다. 형태는 기존
`mirror_frame` 과 동일하다.

```json
{ "type": "mirror_frame", "seq": 1, "tab": 0, "data": "<base64 jpeg>", "width": 1280, "height": 800 }
```

이것은 **재전송이 아니라 현재 상태 전달**이다. `mirror_frame` 은 이 계약에서 이미
"유실 가능 · 프론트는 마지막 프레임만 그리면 된다"로 정의돼 있으므로(001 websocket.md
§미러), 한 장 전달은 "재전송하지 않는다" 원칙과 충돌하지 않는다. 그 원칙은 **순서 있는
상태 이벤트**를 두고 한 말이다.

보낼 프레임이 없으면(아직 한 장도 못 만들었다) 아무것도 보내지 않는다.

**(b) 무프레임 감시**

마지막 프레임 후 `MIRROR_IDLE_S`(2초) 넘게 새 프레임이 없으면 스크린샷 한 장을 같은
이벤트로 보낸다. 화면이 계속 조용하면 2초 주기로 계속 보낸다.

기존 강등 경로(스크린캐스트 시작 실패 시 1 fps 스크린샷 루프)와 **같은 코드**를 쓴다.
주기만 다르다.

`mirror_degraded` 는 **발행하지 않는다** — 강등이 아니라 정상 동작의 보완이다. 강등
배너를 띄우면 사용자는 문제가 있다고 읽는다.

### 유지되는 성질

| 성질 | 근거 | 이 변경이 지키는 방법 |
|---|---|---|
| 미러는 입력을 대상 브라우저로 전달하지 않는다 (FR-047a) | 허용 CDP 명령 화이트리스트 3개, `Input` 도메인 미임포트 | **송신 쪽만 만진다.** 화이트리스트에 명령을 추가하지 않는다. 스크린샷은 CDP 가 아니라 Playwright API 를 쓴다 |
| 미러가 끊겨도 실행에 영향이 없다 (FR-047b) | 러너가 미러를 알지 못한다 | 캐시와 감시 태스크를 미러 모듈 안에 둔다. 감시 태스크의 예외는 삼킨다 |
| 프레임은 유실 가능하다 | 001 계약 | 그대로. 마지막 프레임만 그리면 된다 |

---

## 2. `run_finished` — `outcome` 값이 늘어난다

```json
{
  "type": "run_finished",
  "outcome": "pass | fail | stopped | partial_pass",
  "total_ms": 3210,
  "passed_count": 5,
  "total_count": 7,
  "attempted_count": 7,
  "failed_step_index": 5,
  "scope": "full | partial",
  "start_index": 0
}
```

| 필드 | 상태 |
|---|---|
| `outcome` | **값 2개 추가** — `stopped`, `partial_pass` |
| `attempted_count` | **신규** — 실행 대상 Step 수 (전체 − 건너뜀) |
| `scope`·`start_index` | **신규** — 부분 실행 여부와 시작 지점 |

`passed_count / total_count` 는 뜻이 바뀌지 않는다. **요약 문장은 `attempted_count` 로
만든다** — 지금은 `total_count` 로 만들어 부분 실행이 `0 / 7` 로 보인다 (U-02).

알 수 없는 `outcome` 을 만난 클라이언트는 `fail` 로 취급한다 (보수적 기본값).

---

## 3. `session_lost` — 의도적 중지에서는 발행하지 않는다

형태는 그대로다. 바뀌는 것은 **발행 조건**이다.

사용자가 요청한 중지(`STOP → REVIEW`)는 유실이 아니다. 지금은 유실 감지기의
"정상 종료면 유실이 아니다" 가드에 `REVIEW` 가 빠져 있어 의도적 중지가 매번 이 이벤트를
발행하고, 후처리가 결과를 `fail` 로 확정한다 (U-03).

**진짜 유실**(사용자가 브라우저 창을 손으로 닫음, 탭이 모두 닫힘)에서는 그대로 발행한다.
두 경우의 사유 문구를 같게 쓰지 않는다.

사용자에게 보이는 `reason` 에 세션 식별자를 넣지 않는다 (FR-135).

---

## 4. `state_changed` — 전이 중임을 화면이 알 수 있어야 한다

형태는 그대로다. `pause_settled` 는 **이벤트에 싣지 않는다** — 세션 뷰 필드다
(contracts/rest-api.md §3).

이유: `state_changed` 는 상태 기계의 전이만 말한다. "요청은 갔고 아직 경계에 닿지 않았다"
는 상태가 아니라 러너의 사실이다. 이벤트에 실으면 상태와 사실이 한 봉투에 섞인다.

화면은 일시정지 요청을 보낸 직후 **스스로** 전이 표시를 켜고(낙관적 표시),
`POST /pause` 응답의 `pause_settled` 로 확정한다.

---

## 5. 이벤트 목록 요약

| 이벤트 | 005 에서 |
|---|---|
| `mirror_frame` | 구독 직후 1장 + 무프레임 감시 추가 |
| `run_finished` | `outcome` 값 2개, 필드 3개 추가 |
| `session_lost` | 발행 조건 축소 (의도적 중지 제외) |
| `mirror_degraded` | 변경 없음. 무프레임 감시는 강등이 아니다 |
| `state_changed`·`step_started`·`step_finished`·`step_failed`·`run_error`·`edit_warning`·`tab_*`·`artifact_note` | 변경 없음 |

새 이벤트 타입은 **없다.**
