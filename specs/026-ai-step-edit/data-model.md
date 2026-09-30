# Data Model — 026 고른 Step 을 AI 에게 고쳐 달라기

새 저장 형식은 없다. **디스크에 내려가는 것이 하나도 늘지 않는다** — 이 기능이 다루는
것은 전부 세션이 사는 동안의 상태다 (FR-024).

---

## 1. `StepEditTransaction` — 진행 중인 Step 수정 하나

**자리**: `backend/src/itb/authoring/step_edit.py` (신설). 순수 데이터 · 순수 함수이며
세션도 브라우저도 알지 못한다 — `rerecord.py` 와 같은 성질이다.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `target_id` | `str` | 사용자가 고른 Step 의 **식별자**. 순번이 아니다 — 수정 중 앞에 Step 이 끼워지면 순번은 밀린다 |
| `origin` | `Step` | 대상의 **시작 시점 사본**. 되돌리기의 근거 (FR-020) |
| `arrival_index` | `int` | 도착점. 대상의 시작 시점 순번 (0-based). 되맞춤과 되끼우기에 쓴다 |
| `baseline_ids` | `frozenset[str]` | 시작 시점에 목록에 있던 Step 의 id. 「이번에 만든 것」을 **도출**한다 |
| `settled` | `bool` | 확정·버리기로 끝났는가. 연타 방지 |

`origin` 이 016 에 없는 유일한 필드이고, 이 기능의 전부다.

### 연산

| 이름 | 하는 일 | 016 과 다른가 |
|---|---|---|
| `created(steps)` | `baseline_ids` 에 없는 id — 이번 세션이 만든 것 | 같다 |
| `owns(step_id, steps)` | **`target_id` 이거나** `created` 에 속하면 참 | **다르다** — 앞 절반이 새것 |
| `can_commit(steps)` | `not settled` — **만든 것이 없어도 참** | **다르다** (research R5) |
| `commit(steps, idx)` | 아무것도 지우지 않는다. 결과는 지금 목록 그대로 | **다르다** |
| `discard(steps, idx)` | `created` 를 지우고, 대상을 `origin` 으로 되돌린다 — **하나의 결과로** | **다르다** (research R7) |
| `close()` | `settled = True`. 호출자가 결과를 반영한 뒤 부른다 | 같다 |

### 불변식

- **불변식 A**: `owns()` 가 참인 id 는 `target_id` 이거나 `baseline_ids` 밖이다. 그 둘 말고는 어떤 경우에도 참이 아니다.
- **불변식 B**: 버리기 뒤 목록은 시작 시점과 **id 수열까지 동일**하다 — 대상의 식별자가 유지된다 (FR-029).
- **불변식 C**: `settled` 가 참인 트랜잭션은 `owns()` 판정에 쓰이지 않는다. 즉 끝난 뒤 AI 는 아무것도 고칠 수 없다.
- **불변식 D**: `origin` 은 만들어진 뒤 바뀌지 않는다. 대상이 여러 번 고쳐져도 되돌아가는 곳은 하나다.

---

## 2. `restore_step()` — 되돌리는 순수 함수

**자리**: `backend/src/itb/execution/step_edits.py` (기존 모듈에 추가). 사람의 편집과 AI 의
편집이 지나는 그 모듈이다 (원칙 I).

```
restore_step(steps, current_step_index, origin, at_index) -> EditResult
```

| 상황 | 하는 일 |
|---|---|
| `origin.id` 가 목록에 있다 | 그 자리를 `origin` 으로 **교체**한다 |
| `origin.id` 가 목록에 없다 | `at_index` 로 **클램프한 위치**에 되끼운다 |

둘째 경우가 이 함수의 존재 이유다 — AI 는 대상 Step 을 지울 수 있고, 지워진 것은 교체로
돌아오지 않는다 (research R3).

`at_index` 는 기존 `_clamp()` 를 지난다. 되끼울 때 그 사이 목록이 짧아졌을 수 있다.

---

## 3. 세션 상태의 추가

**자리**: `backend/src/itb/api/routes/sessions.py` 의 `SessionWork`.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `step_edit` | `StepEditTransaction \| None` | 진행 중인 Step 수정. 세션당 최대 하나 |

`rerecord` 와 **동시에 존재하지 않는다.** 세션 모드가 하나이므로 구조적으로 그렇다 —
`mode="rerecord"` 는 `rerecord` 를, `mode="step_edit"` 은 `step_edit` 을 만든다.

### 권한 판정의 새 모양

```
in_scope(step_id) ==
    (rerecord 가 살아 있고 그것이 owns) 또는 (step_edit 이 살아 있고 그것이 owns)
```

**둘째 항이 거짓이면 판정이 016 과 글자 그대로 같다** — 그것이 FR-014 이고 SC-006 이
검사한다.

---

## 4. 세션 시작 요청의 추가

**자리**: `SessionStartRequest`.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `mode` | `"record" \| "replay" \| "ai" \| "rerecord" \| "step_edit"` | `step_edit` 이 새것 |
| `step_edit_step_id` | `str \| None` | 고칠 Step 하나의 식별자. `step_edit` 모드에서만 쓴다 |

**여럿을 받지 않는다.** 목록이 아니라 값 하나인 것이 계약이고, 그래서 「둘 이상 고름」은
경계에서 표현조차 되지 않는다 (FR-003 은 화면이 먼저 막고, 이 타입이 마지막으로 막는다).

---

## 5. 화면에 내려가는 모양

| 이름 | 뜻 |
|---|---|
| `StepEditView` | 진행 중인 수정의 상태 — 대상 식별자·대상 순번·이번에 만든 Step 수·확정 가능 여부 |
| `step_edit_changed` (이벤트) | 수정 상태가 바뀌었다. `rerecord_changed` 와 같은 모양 |
| `step_edit_realign_failed` (이벤트) | 되맞춤 실패 — 정의는 되돌아갔고 화면은 어긋나 있다 (FR-028) |

**`rerecord_*` 이벤트를 재사용하지 않는다.** 화면이 둘을 구분해야 하기 때문이다(FR-033) —
같은 이벤트로 보내면 화면이 페이로드를 보고 어느 쪽인지 판정하게 되고, 그 판정이 곧
프론트에 생긴 두 번째 모드 구현이다.

### 무엇이 바뀌었는지 보이기 (FR-034)

`StepEditView` 는 **대상의 지금 모습**만 들고 화면이 그것을 목록의 그 자리에 그린다.
「시작 시점과의 차이」를 서버가 계산해 내려보내지 않는다 — 차이 계산은 표시 문제이고,
서버가 계산하면 어떤 필드가 「바뀐 것」인지의 정의가 서버에 생긴다. 화면은 `origin` 을
시작 시점에 받아 두고 비교한다.

---

## 6. 무엇이 바뀌지 않는가

- **`Step` 자체의 모양** — 새 필드가 없다. 원칙 I 이 요구하는 대로, AI 가 고친 Step 과 사람이 고친 Step 은 저장 형식에서 구별되지 않는다 (SC-004).
- **`RerecordTransaction`** — 016 은 그대로다 (FR-030).
- **`Test` 저장 형식** — 확정되지 않은 수정은 디스크에 닿지 않는다 (FR-024).
- **대화 이력** — 016 의 것을 그대로 쓴다. 정의에 저장되지 않는다.
