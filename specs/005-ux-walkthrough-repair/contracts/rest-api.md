# Contract: REST API (005 라운드 변경분)

**Feature**: `specs/005-ux-walkthrough-repair` | **Date**: 2026-09-07

001 의 [`contracts/rest-api.md`](../../001-interactive-ai-test-builder/contracts/rest-api.md)
와 004 의 변경분을 **확장한다.** 새 엔드포인트는 없다. 응답에 필드가 늘고, 한 엔드포인트의
거절 조건이 좁아진다. 기존 클라이언트는 새 필드를 무시하면 그대로 동작한다.

---

## 1. `POST /api/sessions` — 거절 조건이 좁아진다

### 변경 전

같은 `test_id` 로 세션이 **등록되어 있으면** 거절했다. 종료된 세션도 등록에 남으므로,
방금 끝난 실행 뒤의 재실행이 항상 거절됐다 (U-01).

### 변경 후

**살아 있는 세션이 있을 때만** 거절한다. 종료 상태(`completed·failed·stopped·review·lost`)
의 세션은 다음 실행을 막지 않는다.

거절 응답의 본문이 바뀐다 — 어디로 가야 하는지를 함께 준다 (FR-126).

```json
{
  "code": "SESSION_ALREADY_ACTIVE",
  "message": "TC-002 가 지금 실행 중입니다.",
  "category": "blocked",
  "next_action": "실행 중인 세션으로 이동한 뒤 중지하세요.",
  "detail": { "test_id": "TC-002", "session_id": "<활성 세션 ID>" }
}
```

`detail.session_id` 는 **화면이 그 세션으로 이동하는 버튼을 만들기 위한 것**이다.
사용자에게 보이는 `message`·`next_action` 에는 세션 식별자를 넣지 않는다 (FR-135).

### 동시 요청

같은 `test_id` 로 동시에 도착한 생성 요청 중 **정확히 1건만 201** 이고 나머지는 위 409 다
(FR-128). 확인과 예약이 테스트별 락 안에서 함께 이루어진다.

---

## 2. `GET /api/sessions/{session_id}` · 세션을 돌려주는 모든 응답 — 필드 추가

`SessionView` 에 다음이 추가된다. 세션 뷰를 돌려주는 모든 엔드포인트에 동일하게 적용된다
(`POST /api/sessions`, `GET /api/sessions`, pause·resume·run-from·stop 등).

| 필드 | 형 | 뜻 |
|---|---|---|
| `step_results` | `StepProgress[]` | 이 세션에서 지금까지 확정된 Step 결과 |
| `pause_settled` | `bool` | 일시정지가 실제로 걸렸는가. `false` = 전이 중 |
| `run_scope` | `"full" \| "partial"` | 현재 실행의 범위 |
| `run_start_index` | `int` | 현재 실행이 시작한 Step (0-기반) |
| `saved_at` | `datetime \| null` | 마지막 저장 시각. `null` = 미저장 |

`StepProgress`:

```json
{ "step_id": "s3", "outcome": "pass", "duration_ms": 92 }
```

`outcome` 은 `pass · fail · skipped · not_run` 중 하나다 (기존 `StepOutcome`).

**왜 뷰에 싣는가**: WebSocket 계약은 "재전송하지 않는다 · 끊기면 세션 조회로 전체 상태를
다시 받는다"다. 그 전체 상태에 Step 결과가 없어서, 화면을 다시 그리면 그때까지의 결과가
사라졌다 (U-18·U-05). 이벤트 재전송 버퍼를 만드는 대신 스냅샷을 채운다.

---

## 3. `POST /api/sessions/{id}/pause` — 응답의 뜻이 명확해진다

형태는 그대로 세션 뷰다. **`pause_settled` 로 결과를 읽는다.**

| 응답 | 뜻 | 화면 |
|---|---|---|
| `state=paused`, `pause_settled=true` | 실제로 멈췄다 | 정지. 편집 가능 |
| `state=paused`, `pause_settled=false` | 요청은 갔고 아직 Step 경계에 닿지 않았다 | **전이 중**. 편집 불가, 중지 가능 |

이 엔드포인트는 Step 경계를 최대 `PAUSE_SETTLE_TIMEOUT_S`(10초) 기다린 뒤 응답한다
(기존 동작). **화면은 응답을 기다리지 않고 요청 직후 전이 상태를 표시하고**, 응답으로
확정한다 (FR-142).

기존의 `edit_warnings` 경고("Step 하나가 10초 안에 끝나지 않아…")는 유지된다. 다만 화면은
그 경고를 **기다리지 않고** 처음부터 대기 사실을 말한다.

### 전이 중 실행이 끝난 경우

일시정지가 성립하기 전에 러너가 종료하면 **결말이 일시정지를 이긴다** — 응답의 `state` 는
`paused` 가 아니라 종료 상태(`completed`·`failed`)다 (FR-146).

---

## 3-b. `POST /api/sessions/{id}/resume` — 요청 본문이 생긴다

지금은 본문이 없다. **선택 필드 하나가 생긴다.**

```json
{ "skip_failed": false }
```

| 필드 | 형 | 기본값 | 뜻 |
|---|---|---|---|
| `skip_failed` | `bool` | `false` | 실패한 Step 을 건너뛰고 다음 Step 부터 이어간다 |

본문을 보내지 않으면 `{"skip_failed": false}` 와 같다 — 기존 클라이언트가 그대로 동작한다.

### 거절 조건

| 상황 | 응답 |
|---|---|
| 실패 Step 이 있고 `skip_failed=false` | **409** `CANNOT_RESUME_PAST_FAILURE`. `detail.failed_step_index` 를 싣는다. 화면은 그 자리에 이유와 대안(그 Step 고치기 / 그 Step 부터 실행)을 보여준다 (FR-136) |
| 실패 Step 이 있고 `skip_failed=true` | 200. 다음 Step 부터 이어가고 **결말은 `partial_pass`** 다 (FR-137) |
| 실패 Step 이 없고 `skip_failed=true` | 200. 건너뛸 것이 없으므로 무해하게 무시한다. 결말은 평소와 같다 |

**두 경로를 한 필드로 가르는 이유**: 사용자가 누르는 버튼이 둘이고(「계속하기」·「실패한
Step 건너뛰고 계속」) 그 둘은 같은 재개다. 엔드포인트를 둘로 나누면 재개 규칙(편집된 목록을
대상으로 삼는 것, 러너를 새로 띄우지 않는 것)이 두 벌이 된다.

---

## 4. `POST /api/sessions/{id}/stop` — 결말이 `stopped` 로 기록된다

형태는 그대로다. 바뀌는 것은 **저장되는 결과**다.

- 저장된 `RunResult.outcome` 이 `stopped` 다 (기존: `fail`)
- `stopped_step_index` 에 중지 시점 Step 이 기록된다
- 세션 유실 이벤트(`session_lost`)를 **발행하지 않는다** (U-03)

이미 종료된 세션에 중지가 다시 도착하면 **무해하게 처리한다** — 오류가 아니라 현재 뷰를
돌려준다. 화면은 이미 끝났다는 사실을 표시한다.

`STOP → REVIEW` 로 세션이 남는 것(DR-010, 중지는 화면을 떠나지 않는다)은 유지된다.

---

## 5. `POST /api/sessions/{id}/run-from` — 범위가 결과에 남는다

형태는 그대로다. 저장되는 결과에 `start_index` 와 `scope="partial"` 이 남는다.

`start_index == 0` 이면 `scope="full"` 이다.

---

## 6. `GET /api/tests` — 행 요약에 결말 4값이 실린다

행 요약(`last_run` 계열)의 결말은 `pass · fail · stopped · partial_pass` 중 하나다.
클라이언트가 알 수 없는 값을 만나면 `fail` 로 취급한다 (보수적 기본값).

`failure_summary.step_index` 는 **0-기반 그대로 유지한다.** 표시 변환은 클라이언트 책임이며
한 곳에서만 이루어진다 (FR-138). 지금 목록만 변환을 빠뜨려 1 작게 보인다 (U-07) — 계약이
아니라 클라이언트의 결함이다.

---

## 7. `GET /api/tests/{test_id}/result` — 최근 전체 실행을 함께 준다

응답에 보조 필드가 추가된다.

| 필드 | 형 | 뜻 |
|---|---|---|
| `last_full_run` | `RunResult \| null` | 최근 **전체** 실행. 이번 실행이 전체면 `null` |

부분 실행 결과 화면이 "최근 전체 실행: 5 / 7 통과"를 함께 보여주기 위한 것이다 (FR-152).
`result-full.json` 이 없는 기존 프로젝트에서는 `null` 이다.

---

## 8. 오류 코드

| 코드 | `category` | 언제 | `next_action` |
|---|---|---|---|
| `CANNOT_RESUME_PAST_FAILURE` | `blocked` | 실패 Step 이 있는데 `skip_failed` 없이 재개를 요청했다 | 그 Step 을 고친 뒤 이어가거나, 그 Step 부터 다시 실행하세요. |

`SESSION_ALREADY_ACTIVE` 는 코드가 그대로이고 `message`·`next_action`·`detail` 만 바뀐다 (§1).

`blocked` 인 것은 의도적이다 — **사용자가 할 일이 있다.**

---

## 9. 호환성 정리

| 변경 | 기존 클라이언트 영향 |
|---|---|
| 세션 뷰 필드 5개 추가 | 없음 (무시하면 동작) |
| 결과 응답 `last_full_run` 추가 | 없음 |
| `Outcome` 값 2개 추가 | **있음** — `fail` 로 취급하는 기본값이 필요하다 |
| `POST /sessions` 거절 조건 축소 | 없음 (거절이 줄어드는 방향) |
| `POST /resume` 선택 필드 추가 | 없음 (미전송 = `false`) |
| `POST /resume` 가 실패 Step 앞에서 409 | **있음** — 지금은 조용히 건너뛰어 200 이었다. 그 조용한 건너뜀이 U-05 의 결함이므로 의도된 변경이다 |
| 중지 결말이 `stopped` | **있음** — `fail` 로만 분기하던 화면은 중지를 통과로 오인할 수 있다. 이 라운드에서 화면을 함께 고친다 |
