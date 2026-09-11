# Agent Tools Contract — 016 편집 중 AI 구간 재녹화

**Date**: 2026-09-11 | 기준: `backend/src/itb/authoring/tools.py` (`TOOL_NAMES`·
`STEP_PRODUCING_TOOLS`·`TOOL_SCHEMAS`)

**도구 표면은 계약이다.** 이 문서가 016 이후의 표면 전체를 정의한다.

---

## 1. 표면 전체 — 12 → 16

```
TOOL_NAMES (16)
├─ READ_ONLY_TOOLS      (2)   list_tabs · observe_page
├─ STEP_PRODUCING_TOOLS (9)   click · fill · select · navigate · hover · drag ·
│                             upload · assert_condition · close_tab
│                             ↑ Step 종류와 1:1. 016 이 건드리지 않는다
├─ STEP_EDITING_TOOLS   (4)   update_step · delete_step · move_step · repick_target   ★016
└─ CONTROL_TOOLS        (1)   report_blocked
```

### 검사 (T106·T163 의 후신)

| # | 단언 | 무엇을 막는가 |
|---|---|---|
| 1 | 네 분류의 **합집합 == `TOOL_NAMES`**, 교집합 없음 | 분류에서 빠진 도구, 두 분류에 든 도구 |
| 2 | `STEP_PRODUCING_TOOLS` ↔ Step 종류 **1:1** (기존) | 사람은 만들 수 있는데 AI 는 못 만드는 Step 종류 |
| 3 | `STEP_EDITING_TOOLS` 의 각 도구가 **사람 편집 경로와 같은 함수**를 지난다 | 원칙 I — 작성 주체에 따라 결과가 달라지는 것 |
| 4 | `TOOL_SCHEMAS` 의 키 == `TOOL_NAMES` | 개발용 드라이버에서만 안 되는 도구 |

3번이 이 기능의 원칙 I 증거다. 검사는 「같은 입력으로 도구를 부른 결과」와 「같은 입력으로
`itb.api.routes.steps` 경로를 부른 결과」가 **Step 으로서 같은지**를 본다.

**`report_blocked` 를 `CONTROL_TOOLS` 로 분류한 것이 새로 적히는 사실이다.** 지금 코드는
그것을 `TOOL_NAMES` 에만 두고 분류하지 않는다 — 검사 1번을 세우려면 자리가 있어야 한다.

---

## 2. 편집 도구 4종

### 공통 규칙

| 규칙 | 내용 |
|---|---|
| **권한 범위** | `step_id` 는 **이번 세션이 만든 Step** 이어야 한다 (불변식 8 · FR-037) |
| **거절은 반환값** | 범위 밖이면 예외가 아니라 `{"error": ...}` 를 돌려준다. 에이전트가 읽고 사용자에게 말한다 (FR-038) |
| **호출 상한** | 기존 `AttemptLimits` 를 그대로 쓴다. 편집도 호출 1회로 센다 (FR-042) |
| **같은 함수** | `itb.execution.step_edits` 의 순수 함수를 지난다 (R2) |
| **같은 이벤트** | 결과는 사람의 편집과 같은 이벤트로 나간다 (FR-039) |

### 2-1. `update_step`

Step 의 편집 가능한 속성을 고친다.

```
입력: step_id: str, field: str, value: str
출력 (성공): {"step_id": ..., "field": ..., "label": <바뀐 뒤 표시 이름>}
출력 (거절): {"error": "..."} — 범위 밖 / 그 종류가 갖지 않는 필드 / 값 형식 오류
```

**고칠 수 있는 필드는 사람이 고칠 수 있는 것과 같다** — 표시 이름·입력값·타임아웃·탭·
주소·기대값·파일 이름 (006 FR-183). 목록을 여기 복제하지 않는다. 지나는 함수
(`step_edits.update_step`)가 `FieldNotSupportedError` 로 판정하고, 도구는 그 사유를
그대로 돌려준다.

### 2-2. `delete_step`

```
입력: step_id: str
출력 (성공): {"deleted": step_id, "remaining": <이번 세션이 만든 Step 수>}
출력 (거절): {"error": "..."}
```

**여러 개를 한 번에 지우는 도구는 만들지 않는다.** 에이전트가 하나씩 부르면 되고, 복수
삭제의 전부-또는-전무 보장(011 FR-388)이 필요한 것은 **확정·버리기**이지 에이전트의
정리가 아니다.

### 2-3. `move_step`

```
입력: step_id: str, direction: "up" | "down"
출력 (성공): {"step_id": ..., "index": <새 순번>}
출력 (거절): {"error": "..."} — 범위 밖 / 이미 끝
```

**`direction` 이지 절대 순번이 아니다.** 사람의 조작(`step.moveUp`·`step.moveDown`)과
같은 모양이며, 같은 함수(`reorder_steps`)를 지난다. 절대 순번을 받으면 에이전트가 목록을
다시 관찰하지 않고 낡은 순번을 넘길 수 있다.

**이동 범위도 권한 범위 안이다** — 이번 세션이 만든 Step 들 사이에서만 움직인다. 옛 구간
위로 올라가려 하면 거절한다.

### 2-4. `repick_target`

Step 의 대상 요소를 다시 지정한다.

```
입력: step_id: str, element_ref: str, slot: "target" | "drop_target" = "target"
출력 (성공): {"step_id": ..., "label": <바뀐 뒤 표시 이름>, "candidates": <후보 종류 수>}
출력 (거절): {"error": "..."} — 범위 밖 / 낡은 ref / 그 Step 은 대상을 갖지 않는다
```

**`element_ref` 만 받는다. 셀렉터를 받지 않는다** (헌법 원칙 IV · FR-035).
`observe_page` 가 준 참조여야 하며, 화면이 바뀌어 낡았으면 거절하고 다시 관찰하라고
말한다 — 기존 조작 도구들과 같은 규칙이다.

**후보는 살아 있는 페이지에서 새로 수집한다.** `itb.locator.collector` 를 지나므로
저장되는 것은 단일 셀렉터가 아니라 후보 묶음이다.

**`RepickController` 를 쓰지 않는다.** 그것은 「사람의 다음 클릭 한 번을 대상 지정으로
쓴다」는 대기 상태 기계이고, AI 는 기다릴 것이 없다 — 이미 참조를 갖고 있다. 같은 이름의
두 기제를 하나로 합치려 들면, 사람이 다시 집기를 걸어 둔 상태에서 AI 가 대상을 바꾸는
경우에 어느 쪽이 이기는지가 정의되지 않는다.

`slot` 은 `drag` Step 에만 뜻이 있다 (T166 과 같은 이유).

---

## 3. 시스템 프롬프트 델타

기존 `SYSTEM_PROMPT` 에 더한다. **기존 규칙은 한 줄도 지우지 않는다.**

```
- 지금 만들고 있는 테스트의 Step 목록이 아래에 주어집니다. 그것을 근거로 답하세요.
  목록에 없는 Step 을 지목하지 마세요.
- update_step·delete_step·move_step·repick_target 은 **이번에 당신이 만든 Step 에만**
  쓸 수 있습니다. 다른 Step 을 고치려 하면 거절됩니다 — 사람에게 말하세요.
- 고치기는 방금 만든 것을 다듬을 때만 쓰세요. 만들고 지우기를 반복하지 마세요.
- 교체 구간으로 표시된 Step 은 사용자가 확정할 때 사라집니다. 당신이 지우지 마세요.
```

마지막 줄이 중요하다. 옛 구간을 AI 가 「정리」해 버리면 버리기가 원본을 되찾지 못한다
(불변식 9 붕괴).

### 정의 요약이 붙는 자리

대화의 **첫 사용자 메시지 앞**이 아니라, **매 턴의 사용자 메시지에 덧붙인다.**

```
[지금 테스트]
 1. TC-001-01  시작 주소 열기        navigate    tab 0
 2. TC-001-02  아이디 입력           fill        textbox "아이디"   값 있음
 …
 5. TC-001-05  로그인 버튼 클릭      click       button "로그인"     ◀ 교체 구간
 …
[사용자] 이번엔 SSO 로 로그인해
```

**매 턴에 붙이는 이유**는 FR-003 이다 — 목록은 턴 사이에 바뀐다(AI 가 Step 을 만들고,
사람이 고친다). 첫 메시지에만 넣으면 5분 전 목록을 근거로 답하게 된다.

**대가**: 매 턴 토큰이 든다. 요약이 값을 읽지 않고 한 줄에 한 Step 이므로 Step 100개가
약 4~6KB 수준이며, FR-006 의 축약이 그 위의 상한이다. 실측값은 tasks 단계에서 정한다.

---

## 4. 개발용 드라이버 (`claude_code_driver`)

`QUALIFIED_TOOL_NAMES` 는 `TOOL_SCHEMAS` 에서 자동으로 나오므로 **편집 도구가 저절로
따라 들어온다.** 손으로 더할 것이 없다.

`BLOCKED_BUILTINS` 와 `_deny_unknown_tools` 는 그대로다 — 새 도구는 MCP 서버 쪽에
등록되므로 내장 도구 차단과 무관하다.

**검사 4번**(`TOOL_SCHEMAS` 의 키 == `TOOL_NAMES`)이 이 자동 전파를 지킨다. 스키마를
빠뜨리면 기본 드라이버에서는 되고 개발용에서는 안 되는 도구가 생긴다.
