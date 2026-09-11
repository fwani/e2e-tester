# API Contract — 016 편집 중 AI 구간 재녹화

**Date**: 2026-09-11 | 기준 계약: `specs/001-interactive-ai-test-builder/contracts/rest-api.md` ·
`websocket.md`

**델타 문서다.** 여기 적힌 것만 새로 생기거나 바뀐다. 나머지는 기존 계약 그대로다.

---

## 1. 세션 생성 — 모드 하나 추가

`POST /api/sessions`

```
mode: "record" | "replay" | "ai" | "rerecord"
                                    ^^^^^^^^ 016
```

### `mode: "rerecord"` 의 요청

| 필드 | 형 | 필수 | 설명 |
|---|---|---|---|
| `test_id` | `str` | ✔ | 저장된 테스트. 초안·미저장 세션은 대상이 아니다 |
| `rerecord_step_ids` | `list[str]` | ✔ | 교체할 구간의 Step id, 목록 순서대로. 연속이어야 한다 |

`ai_instruction` 은 **받지 않는다.** 재녹화의 지시는 채팅으로 온다 — 시작 시점에 지시를
받으면 「지시 한 번」과 「대화」 두 입구가 생기고, 사용자는 어느 쪽에 써야 하는지 모른다.

### 서버가 하는 일 (순서가 계약이다)

```
1. 구간 검증        존재 · 연속 · 비어 있지 않음        위반 → 400 DEFINITION_INVALID
2. 점유 검증        다른 세션이 그 테스트를 잡았는가     위반 → 409 SESSION_BUSY
3. 세션 생성        authoring_mode = ai                  ← R5. 국면 판정이 여기 걸린다
4. BEGIN_REPLAY     엔진을 세우고 러너를 띄운다
5. 도착점까지 실행   pause_before_index = 구간 첫 Step 의 순번
   └─ 이 구간에 에이전트 태스크는 존재하지 않는다 (불변식 6, 원칙 II)
6. 러너 종료 확인    PAUSED 도달
7. 에이전트 준비     _build_agent — 아직 돌리지 않는다
8. 트랜잭션 생성     RerecordTransaction(range, arrival_index, created=[])
```

5번과 7번 **사이에 순서가 있다**는 것이 원칙 II 의 이 기능에서의 형태다.

### 저장하지 않은 편집 (FR-022)

**재녹화는 디스크의 저장된 정의로 시작한다.** 편집 화면에 저장하지 않은 편집이 남아
있으면 그것은 세션에 반영되지 않고, 세션이 정의를 잡는 동안 사용자는 그것을 저장할
수도 없다 — 말없이 시작하면 편집이 사라진 것처럼 보인다.

**서버는 거절하지 않는다. 화면이 먼저 확인을 받는다.** 서버는 미저장 편집의 존재를
알지 못하기 때문이다 — 그것은 화면이 들고 있는 것이고(`hasPendingEdits`, 권한표 조건
C9), 서버에 알리려면 편집을 보내야 하는데 그러면 그것은 이미 저장이다.

화면의 확인 문면과 선택지:

> 저장하지 않은 편집이 있습니다. 재녹화는 **저장된 정의**로 시작하므로 그 편집은
> 반영되지 않습니다.
>
> `[저장하고 시작]` `[저장하지 않고 시작]` `[취소]`

`저장하지 않고 시작` 을 고르면 편집은 화면에 남아 있고, 세션이 끝난 뒤 되돌아온다.
**버리지 않는다** — 사용자가 버리기를 선택하지 않았다.

### 응답

`SessionView` (아래 §3 델타 포함). 상태는 `paused`.

### 실패

| 상황 | 코드 | `category` | `next_action` |
|---|---|---|---|
| 구간이 연속이 아니다 | `400 DEFINITION_INVALID` | 제품이 막았다 | 이어진 Step 을 고르세요 |
| 구간 id 가 없다 | `400 DEFINITION_INVALID` | 제품이 막았다 | 화면을 새로 고치세요 |
| 다른 세션이 잡았다 | `409 SESSION_BUSY` | 제품이 막았다 | 그 세션을 닫으세요 |
| 도착점에 닿지 못했다 | `409` + 실패한 Step 정보 | 제품이 막았다 | 그 Step 을 먼저 고치세요 (FR-020) |

도착점 실패는 **세션을 남긴다** — 어디서 왜 실패했는지 보려면 세션이 필요하다. 상태는
`paused` 이고 트랜잭션은 만들어지지 않는다.

---

## 2. 새 엔드포인트 4개

### 2-1. `POST /api/sessions/{session_id}/chat` — AI 에게 말 걸기

FR-007·FR-009·FR-010·FR-011

**요청**

| 필드 | 형 | 설명 |
|---|---|---|
| `text` | `str` | 1자 이상 `MAX_INSTRUCTION_CHARS` 이하 |

**게이트**: 상태가 `paused` 여야 한다. (`ai_blocked` 에서 말을 거는 것은 기존
`AiChoice.ANSWER` 경로다 — 두 입구를 만들지 않는다.)

**하는 일**

```
1. 입력 검증                 위반 → 400 DEFINITION_INVALID
2. 정의 요약 생성             값을 읽지 않는다 (R8)
3. BEGIN_AI 적용             PAUSED → AI_RUNNING
4. 에이전트 태스크 시작        요청은 즉시 반환한다 (기존 _start_agent 와 같다)
5. 턴이 끝나면 PAUSE 적용      AI_RUNNING → PAUSED
   또는 막히면 AI_BLOCK        AI_RUNNING → AI_BLOCKED (기존 경로)
```

**응답**: `SessionView` (상태 `ai_running`). 진행과 결과는 WebSocket 이벤트로 온다.

**중지**: 기존 `POST /{id}/pause` 가 그대로 동작한다 (`AI_RUNNING` 은 `PAUSABLE_STATES`).

### 2-2. `POST /api/sessions/{session_id}/rerecord/commit` — 확정

FR-025·FR-026·FR-028·FR-030

**게이트**: 상태 `paused` · 트랜잭션이 있고 `settled` 가 아님 · `created_step_ids` 가
비어 있지 않음(불변식 10).

**하는 일**: `delete_steps(steps, range.step_ids)` 한 번. 전부-또는-전무.
트랜잭션을 `settled` 로 닫는다.

**응답**: `SessionView`. `rerecord` 필드가 `null` 이 된다.

**실패**

| 상황 | 코드 | `next_action` |
|---|---|---|
| 만든 Step 이 없다 | `409` | 지시를 보내 Step 을 먼저 만드세요 |
| 트랜잭션이 없다 | `409` | — |

### 2-3. `POST /api/sessions/{session_id}/rerecord/discard` — 버리기

FR-027·FR-031·FR-031a·FR-031b·FR-031c

**게이트**: 확정과 같다. 단 `created_step_ids` 가 비어 있어도 **허용**한다 — 아무것도
만들지 않은 채 그만두는 것은 정상이다.

**하는 일**

```
1. delete_steps(steps, created_step_ids)   전부-또는-전무. 목록이 시작 전과 같아진다
2. 트랜잭션을 settled 로 닫는다
3. 도착점까지 다시 실행한다                  ← FR-031. 세션은 살아 있다 (FR-031a)
   └─ 이 구간에도 에이전트 태스크는 없다 (FR-031b · 불변식 6)
4. 실패하면 두 사실을 함께 알린다            ← FR-031c
```

**응답**: `SessionView`. 되맞춤 실행 중이므로 상태는 `replaying` 이고, 도달하면 `paused`.

**되맞춤 실패**: `rerecord_realign_failed` 이벤트(§4-3)를 내보내고 상태는 `paused` 로
둔다. 정의는 **이미 되돌아가 있다** — 그 사실을 응답과 이벤트가 모두 말한다.

**연타 방지**: 트랜잭션이 `settled` 인 동안 두 번째 호출은 `409`. 되맞춤이 도는 중에도
같다.

### 2-4. `GET /api/sessions/{session_id}/chat` — 대화 이력 조회

FR-009. 화면 새로 고침·재접속 후 이력을 되찾기 위한 것이다.

**응답**

```
{ "turns": [ { "role": "user" | "assistant", "text": str, "at": iso8601 } ] }
```

**민감값**: 이력에는 사용자가 친 문장이 그대로 들어간다. 서버는 그것을 **디스크에 쓰지
않으므로** 세션이 끝나면 사라진다 (FR-014 · R8).

---

## 3. `SessionView` 델타

| 필드 | 형 | 설명 |
|---|---|---|
| `rerecord` | `RerecordView \| null` | 진행 중인 교체. 없으면 `null` |

`RerecordView`:

| 필드 | 형 | 설명 |
|---|---|---|
| `range_step_ids` | `list[str]` | 교체 대상 (옛 Step). **화면이 이것으로 「교체 대상」을 계산한다** (불변식 7) |
| `created_step_ids` | `list[str]` | 이번에 만든 Step |
| `can_commit` | `bool` | 확정 가능 여부. 서버가 판정한다 — 화면이 조건을 복제하면 서버와 갈린다 |

`mode` 필드는 늘리지 않는다. 화면은 `authoring_mode === "ai"` 와 `rerecord !== null` 로
재녹화 세션을 안다.

---

## 4. 새 이벤트 3개

기존 이벤트(`step_added`·`ai_progress`·`ai_blocked`·`ai_error`·`ai_finished`)는 **그대로
쓴다.** 재녹화가 만든 Step 도 `step_added` 로 나간다 — 작성 주체별 이벤트를 만들지 않는
것이 원칙 I 이다.

### 4-1. `chat_turn`

사용자의 말 또는 AI 의 답이 이력에 붙었다.

```
{ "role": "user" | "assistant", "text": str, "at": iso8601 }
```

### 4-2. `rerecord_changed`

트랜잭션 상태가 바뀌었다 (시작·Step 추가·확정·버리기).

```
{ "rerecord": RerecordView | null }
```

### 4-3. `rerecord_realign_failed`

버리기의 되맞춤 실행이 실패했다 (FR-031c).

```
{
  "failed_step_id": str | null,
  "reason": str,
  "definition_reverted": true   ← 정의는 이미 되돌아갔다. 이 사실을 함께 말한다
}
```

`definition_reverted` 를 상수 `true` 로 싣는 이유는 화면이 **두 사실을 한 자리에서**
말하게 하기 위해서다. 사유만 보내면 화면은 「되돌아갔는가」를 다른 이벤트에서 추론해야
하고, 추론이 틀리면 사용자에게 거짓을 말한다.

---

## 5. 스키마 드리프트

헌법 Cross-language schema duty.

| 새 모델 | 스키마 내보내기 필요? |
|---|---|
| `RerecordView` | **아니오** — `SessionView` 는 지금도 `MODELS` 에 없다. 프론트가 `client.ts` 에 손으로 든다 |
| `ChatTurn` | 같음 |

`MODELS` 에 있는 것은 `step-dsl`·`step`·`project`·`run-result`·`error-response`·
`manual-step`·`draft` 일곱이며, **전부 디스크에 쓰이거나 DSL 의 일부다.** 세션 뷰는
둘 다 아니다. 이 기능은 그 일곱을 하나도 바꾸지 않으므로
`uv run python -m itb.schema.export --check` 는 변경 없이 통과해야 한다 — **통과하지
않으면 저장 형식을 건드린 것이고, 그것은 이 계획의 위반이다.**
