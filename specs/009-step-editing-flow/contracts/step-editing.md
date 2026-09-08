# 계약 — Step 삽입과 행 조작

**기능**: `009-step-editing-flow` | **작성**: 2026-09-08

이 문서는 **007 `contracts/ui-contract.md` 의 개정판**이다. §2(조작 목록)와 §3(권한표)에
더해지는 것과 바뀌는 것만 적는다. 여기 적히지 않은 칸은 007·008 의 값이 그대로 유효하다.

> **UC-000 은 그대로다 — 표가 정본이다.** 조작이 어느 국면에서 어떤 상태인지는
> `frontend/src/lib/capabilities.ts` 가 정하고, 이 문서가 그 코드의 근거다. 둘이 다르면
> 코드를 고친다. 단 **현재 쓸 수 있는 조작이 표에서 「해당 없음」이면 표의 오류**다.

---

## 1. 조작 목록 — 34 → 36 (ui-contract §2 개정)

### 1-1. 추가 (2)

| id | 라벨 | 자리 | 근거 |
|---|---|---|---|
| `step.insertManual` | 직접 입력으로 Step 추가 | Step 행의 조작 칸 · 패널 바닥 | FR-285. 브라우저 없이 만들 수 있는 종류를 넣는다 |
| `step.moveDown` | 아래로 옮기기 | Step 행의 조작 칸 | FR-299. 지금 없는 방향 |

### 1-2. 개칭 (1)

| 이전 id | 새 id | 라벨 변화 | 근거 |
|---|---|---|---|
| `step.reorder` | `step.moveUp` | 순서 변경 → **위로 옮기기** | 별도 패널이 사라진다(FR-301). 「순서 변경」이 가리키던 그 패널이 없어지므로 이름이 실제 동작(한 칸 위로)과 같아야 한다 |

개칭은 21곳(8개 파일)에 걸친다. 컴파일러가 전수로 잡는다 — 남는 참조가 있으면 빌드가
실패한다.

### 1-3. 뜻이 넓어지는 것 (1) — **새 id 를 만들지 않는다**

| id | 라벨 | 이전 동작 | 새 동작 |
|---|---|---|---|
| `browser.openAt` | 브라우저 열어 이 Step **앞에서** 멈추기 | 저장 → 세션 생성(`pause_before_index`) → 그 자리에서 멈춘다 | 같은 배관 + **도착하면 직접 조작 녹화가 켜진다** (FR-291·FR-295) |

「브라우저에서 지목해 추가」를 별도 조작으로 두지 않는다. 도착지가 같은 두 버튼을 나란히
두면 사용자는 차이를 확인하느라 멈춘다 — 006 E-03 이 같은 형태였다 (research R3).

### 1-4. 없애는 것 (0)

기존 추가 경로 셋(`step.recordStart`·`step.addNaturalLanguage`·`step.addAssertion`)은
**그대로 있다** (FR-309). 자리도 문구도 바뀌지 않는다.

---

## 2. 권한표 — 신규 2개 16칸 + 개칭 1개 8칸 이관 (ui-contract §3 개정)

기호는 007 과 같다. ● 가능 · ○ 비활성(이유·해소 방법) · ◐ 런타임 조건 · – 해당 없음.

| 조작 | CRE 만들기 | REC 녹화 | AI 작성 | TKO 사람조작 | RUN 실행 중 | PAU 일시정지 | RES 결과 | EDT 편집 |
|---|---|---|---|---|---|---|---|---|
| `step.insertManual` | ○ `NOT_STARTED_YET` → `record.start` | ○ `NEEDS_PAUSE` → `run.pause` | ○ `NEEDS_PAUSE` → `run.pause` | ○ `NEEDS_PAUSE` → `run.resume` | ○ `RUNNING_NO_EDIT` → `run.pause` | ● | ○ `RESULT_NO_EDIT` → `nav.editStep` | ◐ `C7` |
| `step.moveUp` | ○ `NOT_STARTED_YET` → `record.start` | ○ `NEEDS_PAUSE` → `run.pause` | ○ `NEEDS_PAUSE` → `run.pause` | ○ `NEEDS_PAUSE` → `run.resume` | ○ `RUNNING_NO_EDIT` → `run.pause` | ● | ○ `RESULT_NO_EDIT` → `nav.editStep` | ◐ `C7` |
| `step.moveDown` | ○ `NOT_STARTED_YET` → `record.start` | ○ `NEEDS_PAUSE` → `run.pause` | ○ `NEEDS_PAUSE` → `run.pause` | ○ `NEEDS_PAUSE` → `run.resume` | ○ `RUNNING_NO_EDIT` → `run.pause` | ● | ○ `RESULT_NO_EDIT` → `nav.editStep` | ◐ `C7` |

### 2-1. 셀을 이렇게 정한 이유

- **`step.moveUp`·`step.moveDown` 은 개칭 전 `step.reorder` 의 열을 그대로 물려받는다.**
  같은 대상·같은 전제이며, 방향만 다르다. 열을 새로 판단하면 옮기는 두 방향이 국면에 따라
  다르게 잠기는 상태가 생긴다.
- **`step.insertManual` 의 EDT 열이 `◐ C7` 인 것이 이 기능의 핵심이다.** 지금 그 자리의
  추가 조작 셋은 전부 `○ NEEDS_BROWSER` 다. 요소 지목을 요구하지 않는 삽입에는 브라우저가
  필요 없으므로 **브라우저 없음으로 잠그지 않는다** (FR-307). 잠금의 근거는 「정의를 고칠
  수 있는가」(C7) 하나다.
- **PAU 열이 `●` 이고 `C2`(브라우저가 살아 있다)를 요구하지 않는다.** 이 조작은 정의
  목록을 고치는 것이고 브라우저에 아무 명령도 보내지 않는다 — `step.delete` 가 같은 이유로
  이미 `●` 다.
- **CRE 열에 자리를 남긴다** (`○`, 감추지 않는다). Step 이 0개일 때 「조작이 어디에
  쌓이는지」를 보여 주지 않으면 008 FR-260 이 고친 결함이 되돌아온다.
- **RES 열은 `○` 이고 해소 방법이 `nav.editStep` 이다.** 결과 화면은 읽기 전용이며, 그
  해소 방법이 **그 자리를 고른 상태로** 편집 화면을 연다 (FR-297) — 셀은 바뀌지 않고
  해소 방법의 **동작**이 정확해진다.

### 2-2. 런타임 덮어쓰기 (ui-contract §3-6 개정)

새 덮어쓰기 키를 만들지 않는다. 기존 목록에 조작 id 만 더한다.

| 키 | 사실 | 더하는 조작 |
|---|---|---|
| `O2` | `busy` | `step.insertManual` |
| `O3` | `sessionLost` | `step.insertManual` |
| `O4` | `hasSteps` 거짓 | `step.moveUp` · `step.moveDown` |
| `O6` | `pausing` | `step.insertManual` · `step.moveUp` · `step.moveDown` |

**`step.insertManual` 은 `O4` 에 넣지 않는다.** Step 이 0개일 때야말로 넣을 수 있어야
한다. `O4` 는 「대상이 없으면 뜻이 없는 조작」을 위한 것이고 삽입은 그 반대다.

`step.moveUp`·`step.moveDown` 은 개칭 전 `step.reorder` 가 있던 `O4`·`O6` 자리를
그대로 받는다. `O3`(세션 유실)에 순서 변경이 없던 것도 그대로다 — 정의 목록 편집은
브라우저를 요구하지 않는다.

### 2-3. 화면이 좁히는 것 (표가 아니라 사실)

표는 국면을 보고, 아래는 **화면이 아는 사실**을 본다. 007 `EditView.narrowByPick` 과 같은
형태이며 표를 대신하지 않는다.

| 사실 | 좁혀지는 조작 | 이유 문구 | 근거 |
|---|---|---|---|
| 첫 행이다 | `step.moveUp` | 「맨 위입니다」 | FR-300 |
| 마지막 행이다 | `step.moveDown` | 「맨 아래입니다」 | FR-300 |

좁혀진 조작은 **자리를 남기고 비활성**이다. 해소 방법을 달지 않는다 — 해소할 방법이 없는
사실이며, 없는 방법을 가리키면 006 E-03 이 된다.

---

## 3. 행 조작의 자리 (ui-contract §1-2 개정 · FR-298·FR-304)

### 3-1. 격자

```
이전  .srow { grid-template-columns: 26px 1fr 58px 20px; }
이후  .srow { grid-template-columns: 26px 1fr 58px 20px auto; }
```

| 칸 | 내용 | 폭 |
|---|---|---|
| 1 | 번호 | 26px |
| 2 | 이름 · 동작 칩 · 탭 배지 · 대상 요약 · 값 | `1fr` (460px 패널에서 약 227px) |
| 3 | 소요 시간 | 58px |
| 4 | 결말 표식 | 20px |
| **5** | **행 조작 4개** | **auto (약 92px)** |

**행 높이 52px 는 바뀌지 않는다.** 조작은 새 칸이며 기존 칸을 밀어내지 않는다.

### 3-2. 칸 5 의 조작 — 순서 고정

```
[위로 ↑] [아래로 ↓] [이 앞에 추가 +] [지우기 ×]
```

- 각 20px · 간격 4px. 정본의 「작은 자리 26px」 조작 높이 안에 든다.
- **hover 로 드러내지 않는다. 항상 보인다.** 보이지 않는 조작은 없는 조작이다 (FR-234).
  지금 `rowActions` 자리가 열려 있는데도 쓰이지 않는 것(M-08)이 그 증거다.
- 「이 앞에 추가」는 그 자리에서 **작은 선택 자리**를 연다. 그 안에 두 조작이 각자의 국면
  상태로 들어간다 — `step.insertManual`(종류 넷 중 고르고 값을 입력) ·
  `browser.openAt`(요소를 지목해야 하는 종류). 비활성이면 이유와 해소 방법이 그 자리에
  보인다.
- 「맨 뒤에 추가」는 행이 아니라 **패널 바닥**(`.steps-ft`)이 갖는다 — 007 FR-235 가 정한
  「그 국면의 Step 조작이 모이는 유일한 자리」다.

### 3-3. 없어지는 것

| 없어지는 것 | 대체 | 근거 |
|---|---|---|
| `SessionScreen` 의 `ReorderPanel` (별도 순서 변경 패널) | 행의 위로·아래로 | FR-301 · SC-505 |
| `EditView` 팔레트의 「위로 옮기기」 단독 버튼 | 행의 위로·아래로 | FR-299 |
| "먼저 Step 을 고르세요" 왕복 (이동·삭제) | 행 조작 | FR-298 · SC-504 |

팔레트에서 이동·삭제 자리를 **완전히 빼지는 않는다.** 표가 그 조작을 그 국면에 두라고
하면 자리는 있어야 한다 — 행에 있는 것이 그 자리다. `ActionPalette` 의 `hidden` 목록이
「이 국면에서 이 조작은 다른 자리가 갖는다」를 표현하는 기존 방법이며, 그것을 쓴다.

### 3-3-1. 읽기 전용 국면에서는 팔레트가 칸 5 를 갖는다

**결과 국면(RES)에서는 행에 칸 5 를 그리지 않는다.** 조작은 팔레트에 비활성으로 남는다.

**근거.** 표는 결과 국면의 이동·삭제·추가를 `○ RESULT_NO_EDIT → nav.editStep` 으로 둔다 —
자리는 있어야 한다. 그 자리를 행이 가지면 **행마다 같은 이유의 비활성 조작 4개**가 생기고,
20~50 Step 목록에서 최대 200개가 된다. 결말을 읽는 화면이 쓸 수 없는 조작으로 덮인다.

이것은 **감추는 것이 아니라 자리를 옮기는 것**이다 (FR-234 를 어기지 않는다). 007 FR-235 가
팔레트를 「그 국면의 Step 조작이 모이는 유일한 자리」로 정한 것이 이 경우를 위한 것이다.

규칙을 한 줄로: **고칠 수 있는 국면에서는 행이 갖고, 읽기 전용 국면에서는 팔레트가 갖는다.**
같은 조작이 두 자리에 동시에 보이는 국면은 없다 (006 E-03 의 형태를 만들지 않는다).

| 국면 | 칸 5 | 팔레트 |
|---|---|---|
| CRE · REC · AI · TKO · RUN · PAU · EDT | **행이 갖는다** | 양도(`hidden`) |
| RES 결과 | 그리지 않는다 | **팔레트가 갖는다** (비활성 + `nav.editStep`) |

### 3-4. 저장 전 삽입 Step 의 표시 (FR-310)

세션 없는 편집에서 아직 저장하지 않은 삽입 Step 은 행에 **「미저장」 칩**을 갖는다.
정본의 `.chip` 을 쓰고 새 색을 만들지 않는다.

일시정지 세션에서는 별도 표시가 필요 없다 — 이미 실행된 Step 은 결말 표식을 갖고 방금
넣은 Step 은 갖지 않으므로 구분된다. **통과한 것처럼 보이는 경로가 없다.**

---

## 4. API 계약

### 4-1. `PUT /api/tests/{test_id}/definition` — `insert` 연산 추가

요청 `edits[]` 에 새 연산이 들어간다.

```json
{
  "op": "insert",
  "at": 3,
  "spec": { "kind": "navigate", "url": "https://example.test/orders", "tab": 0 }
}
```

| 항목 | 규칙 |
|---|---|
| `at` | `0 ≤ at ≤ 현재 Step 수`. 그 위치 **앞**에 들어간다 |
| `spec` | `ManualStepSpec` — [data-model.md](../data-model.md) §2 |
| 다른 연산과의 관계 | 같은 묶음에 섞일 수 있고 **순서대로** 적용된다. 전부 또는 전무 |
| `revision` | 지금과 같다. 되돌려 보내지 않으면 저장할 수 없다 (006 FR-209) |

**응답**: 지금과 같은 `DefinitionView`. 경고는 `warnings` 에 실린다 (FR-312).

**거절**

| 상황 | 코드 | 문구 |
|---|---|---|
| `at` 이 범위를 벗어남 | `DEFINITION_INVALID` | 「넣을 위치가 범위를 벗어났습니다」 |
| `kind` 가 목록에 없음 | `DEFINITION_INVALID` | 요청 모델이 거절한다. **필드 이름만** 싣는다 |
| 필수 필드 누락 | `DEFINITION_INVALID` | 같음 — `_missing_fields` 규칙 |

**넘어온 값을 오류에 싣지 않는다** (003 EC-005). 이 라우트의 판별 유니온 거절은 전역
`RequestValidationError` 핸들러를 타고, `itb/api/errors.py` 의 `_reason` 이 **닫힌 문구
집합**만 쓰므로 값이 실리지 않는다. 세션 라우트(§4-2)는 기존 `_missing_fields` 규칙을
그대로 쓴다. **두 경로 모두 검사로 확인한다** — 규칙이 있다는 것과 그 경로를 탄다는 것은
다른 사실이다.

### 4-2. `POST /api/sessions/{session_id}/steps:manual` — 신규

```json
{ "at": 7, "spec": { "kind": "assert_url", "url": "/done", "match": "contains" } }
```

| 항목 | 규칙 |
|---|---|
| 전제 | `require_paused`. 실행 중이면 거절한다 (FR-306) |
| `at` | 생략하면 **일시정지 위치**. 범위를 벗어나면 클램프한다 (기존 `_clamp`) |
| 응답 | 기존 `StepsResponse` (`steps` · `edit_warnings` · `current_step_index`) |
| 이벤트 | 기존 `step_added` 를 그대로 발행한다 — 새 이벤트를 만들지 않는다 |
| 브라우저 | **아무 명령도 보내지 않는다** |

기존 `POST /api/sessions/{id}/steps`(완성된 Step 통째)는 **그대로 남는다**. 받는 것이
다르고 거절 규칙이 이미 계약 테스트로 고정돼 있다 (research R2).

### 4-3. `GET /api/sessions/{session_id}` — `pause_before_index` 추가

`SessionView` 에 필드 하나가 늘어난다.

```
pause_before_index: int | null   // 아직 도달하지 않은 목표 지점. 도달하면 null
```

WebSocket 재연결 시 전체 상태 동기화가 이 값을 실어 오므로 화면을 다시 그려도 「어디서
멈출 예정인지」가 사라지지 않는다 (005 U-18 과 같은 근거).

**기존 이벤트는 바뀌지 않는다.** 진행은 이미 Step 이벤트로 흐르고, 목표 지점만 스냅샷에
없었다.

---

## 5. 「이 앞에 추가」 흐름 (FR-291~FR-296)

`browser.openAt` 을 누른 뒤 일어나는 일. **새 실행 방식을 만들지 않는다** — 기존
`pause_before_index` 재생을 쓴다.

| # | 하는 일 | 누가 | 실패하면 |
|---|---|---|---|
| 1 | 미저장 변경 저장 | 화면 → `PUT /definition` | 충돌 흐름(006)을 탄다. 브라우저를 열지 않는다 |
| 2 | 세션 생성 (`mode=replay`, `pause_before_index=목표`) | 화면 → `POST /sessions` | 다른 세션이 잡고 있으면 그 세션으로 가는 방법을 보인다 |
| 3 | 목표 앞까지 재생 | 서버 러너 | 실패한 자리에서 멈춘다. **도달했다고 말하지 않는다** (FR-294) |
| 4 | 도착 · 일시정지 | 서버 | — |
| 5 | 직접 조작 녹화 시작 | 화면 → 기존 `record:start` | 켜지지 않으면 이유를 보이고 팔레트의 같은 조작을 가리킨다 |

**진행 표시** (FR-293): 2~4 동안 화면은 `pause_before_index` 와 현재 위치로 「Step nn
앞에서 멈춥니다 — 지금 Step mm」을 말한다. 그만두는 길은 그 국면의 `run.stop` 이다.

**목표가 맨 앞일 때** (FR-296): 재생할 Step 이 없다. 시작 주소를 열고 첫 Step 앞에서
멈춘다 — `pause_before_index=0` 이 이미 그 동작이다.

**도구 의도는 화면이 기억한다.** 서버 상태에 UI 의도를 저장하지 않는다. 새로 고치면
녹화는 켜지지 않은 채로 오고, 그때 팔레트의 같은 조작을 그대로 쓸 수 있다 (research R5).

---

## 6. 대조 대상 (FR-313)

`.srow` 격자가 바뀌므로 확정 디자인과 대조표를 함께 고친다. 코드에만 있고 정본에 없는
조작을 만들지 않는다.

**순서가 정해져 있다.** 008 이 세운 정본 흐름은 `dc.html 의 <style>` → `extract_canon.py`
→ `tokens.css` 이며, `tokens.css` 를 먼저 고치면 다음 추출에서 되돌아간다.

| # | 갱신 대상 | 무엇 |
|---|---|---|
| 1 | `docs/design/008-visual-language/*.dc.html` 의 `<style>` — **18장 전부** | `.srow` 격자에 다섯째 칸 추가 · `.srow-ops` 정의. 18장이 글자 하나까지 같아야 하며 `extract_canon.py --check` 가 그것을 단언한다 |
| 2 | 같은 파일의 **마크업** — 행을 그리는 장 | `Main` · `Paused` · `Run` · `Record` · `Takeover` · `AiWriting` · `Result` · `StepDetail`. 행에 칸 5 를 그린다 |
| 3 | `frontend/src/theme/tokens.css` | `extract_canon.py` 재실행 결과로 갱신한다. 손으로 고치지 않는다 |
| 4 | `docs/design/008-visual-language/conformance/*.md` | 같은 장의 대조표에 칸 5 행 추가. `Edit.md` 의 기준은 `Main.dc.html` 이다 |
| 5 | `docs/design/008-visual-language/replacement-map.md` | 정본 클래스 목록에 `.srow-ops` 추가 |

`Main` 장(편집 국면의 대조 기준)에는 **「이 앞에 추가」 선택 자리**와 **「미저장」 칩**도
함께 들어간다.
