# Research — 016 편집 중 AI 구간 재녹화

**Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

계획이 판정해야 했던 9가지다. 각 항목은 **결정 / 근거 / 버린 대안** 순으로 적는다.
근거는 전부 이 저장소의 현재 코드에서 확인했으며 인용한 파일·심볼은 실재한다.

---

## R1 — 원칙 II 경계: AI 세션이 실행을 부를 수 있는가

**결정**: 부를 수 있다. **배선을 `itb.api.routes.sessions` 에 둔다.** 새 계약도, 계약
완화도 필요 없다.

**근거**: `.importlinter` 의 `execution-no-llm` 은 **단방향 금지**다.

```
source_modules   = itb.domain · itb.locator · itb.execution · itb.storage
                   itb.generator · itb.mirror · itb.recording · itb.portability
forbidden_modules = itb.llm · itb.authoring · anthropic · claude_agent_sdk
```

금지되는 것은 `execution → authoring` 이고, **`authoring → execution` 은 허용**이다.
실제로 이미 그렇게 쓰고 있다 — `itb/authoring/tools.py` 가 `BrowserSession`·`StepExecutor`
를, `itb/authoring/blocked.py` 가 `BrowserSession`·`Command` 를 임포트한다.

그리고 도착점 만들기의 주체는 에이전트가 아니라 **API 계층**이다. 지금도 `_start_runner`
(러너)와 `_start_agent`(에이전트)를 부르는 곳이 같은 파일이며, `itb.api` 는 `execution-no-llm`
의 `source_modules` 에 없다. 재녹화는 그 두 호출의 **순서를 정하는 것**일 뿐이다.

원칙 II 가 실제로 요구하는 것은 「저장된 테스트를 재실행하는 동안 언어모델이 도달
불가능」이다. 도착점 만들기는 러너가 도는 구간이고 그 구간에 에이전트 태스크는 존재하지
않는다 — 러너가 `pause_before_index` 에 닿아 멈춘 **뒤에** 에이전트가 시작한다. 두 태스크가
겹치지 않음을 검사로 고정한다 (아래 R9).

**버린 대안**: `itb.authoring` 안에 얇은 실행 호출기를 두는 것. 계약은 통과하지만 러너
수명 관리(`work.runner`·취소·`rebase`)가 두 곳에 생긴다. 지금 `_start_runner` 의 머리주석이
「돌고 있으면 먼저 취소를 끝낸 뒤 새로 시작한다」는 규칙을 갖고 있는데, 그 규칙이 둘로
갈리면 앞선 실행이 결과를 덮어쓰는 결함이 되살아난다.

---

## R2 — AI 편집 도구는 어느 함수를 쓰는가

**결정**: `itb.execution.step_edits` 의 순수 함수를 **그대로 쓴다.** 옮기지 않는다.

**근거**: R1 과 같은 이유로 `authoring → execution` 임포트가 허용된다. 그리고 그 함수들은
이미 순수하다 — `update_step`·`delete_step`·`delete_steps`·`reorder_steps` 는 원본을
바꾸지 않고 새 상태를 `EditResult` 로 돌려준다. 사람의 편집(`itb/api/routes/steps.py`)이
지나는 것과 **같은 함수를 AI 도 지나면**, 원칙 I 의 「같은 구조」가 구현으로 보장된다.
문서로 약속하는 것이 아니라 코드가 한 곳이어서 다를 수가 없다.

대상 재지정(`repick`)만 다르다. 그것은 순수 함수가 아니라 `itb.recording.repick` 의
대기 상태 기계이고, 사람이 **브라우저에서 클릭**하기를 기다린다. AI 는 기다릴 필요가
없다 — 이미 `observe_page` 가 준 `element_ref` 를 갖고 있다. 그래서 AI 의 대상 재지정은
`RepickController` 를 쓰지 않고, `element_ref` → 후보 수집(`itb.locator.collector`) →
Step 의 `target` 교체로 간다. 후보 수집은 **살아 있는 페이지에서** 일어나므로 원칙 IV 가
지켜진다.

**버린 대안**: 편집 함수를 `itb.domain` 으로 옮겨 양쪽이 도메인만 보게 하는 것.
`domain-is-pure` 계약이 `itb.domain` 의 모든 임포트를 금지하므로 가능하긴 하다. 그러나
`EditResult`·경고 문구·`allocate_step_id` 는 편집 **연산**이지 도메인 **모델**이 아니고,
지금 자리에서 문제가 없다. 움직이면 006·009·011 의 작업이 전부 리베이스된다.

---

## R3 — 도구 표면 계약을 어떻게 넓히는가

**결정**: `TOOL_NAMES` 를 12 → 16 으로 넓히고, **분류 튜플을 하나 더 만들어 전수를
검사한다.**

```
TOOL_NAMES (16)
├─ READ_ONLY_TOOLS      (2)  list_tabs · observe_page
├─ STEP_PRODUCING_TOOLS (9)  click·fill·select·navigate·hover·drag·upload·
│                            assert_condition·close_tab      ← Step 종류와 1:1, 불변
├─ STEP_EDITING_TOOLS   (4)  update_step·delete_step·move_step·repick_target  ← 새로 생김
└─ CONTROL_TOOLS        (1)  report_blocked
```

**근거**: 지금 `TOOL_NAMES` 주석은 「이 목록이 계약이다 — 늘리면 Step 종류와의 1:1 이
깨진다」고 적혀 있고, 검사(T106·T163)가 그것을 고정한다. 그 문장은 **정확히는
`STEP_PRODUCING_TOOLS` 에 대한 것**이다. 실제로 코드는 이미 두 튜플로 갈라져 있고,
`report_blocked` 와 `observe_page` 는 Step 을 만들지 않으면서 `TOOL_NAMES` 에 있다.

그러므로 계약을 **넓히는 것이 아니라 정확히 적는 것**이다. 검사를 이렇게 바꾼다:

| 검사 | 지금 | 바뀐 뒤 |
|---|---|---|
| Step 종류 1:1 | `STEP_PRODUCING_TOOLS` ↔ Step 종류 | **그대로** |
| 표면 전체 | `TOOL_NAMES` 를 손으로 나열 | 네 분류의 합집합 == `TOOL_NAMES`, 교집합 없음 |
| 편집 도구 | 없음 | `STEP_EDITING_TOOLS` 의 각 도구가 사람 편집 경로와 **같은 함수**를 지난다 |

마지막 줄이 이 기능의 원칙 I 증거다.

**버린 대안**: 편집 도구를 `TOOL_NAMES` 밖에 두는 것. 그러면 Claude Code 드라이버의
`QUALIFIED_TOOL_NAMES`·`_deny_unknown_tools` 가 편집 도구를 모르는 도구로 막는다 — 기본
드라이버에서는 되고 개발용 드라이버에서는 안 되는 기능이 생긴다.

---

## R4 — 상태 기계를 어떻게 바꾸는가

**결정**: 전이 **하나만** 더한다.

```
PAUSED + BEGIN_AI → AI_RUNNING
```

턴이 끝나면 호출자가 `PAUSE` 를 적용해 `AI_RUNNING → PAUSED` 로 돌아온다(기존 전이).
막힘은 `AI_RUNNING → AI_BLOCK → AI_BLOCKED`(기존), 5선택지도 기존 전이 그대로다.
새 상태·새 국면은 만들지 않는다.

**근거**: 재녹화 세션의 생애는 이렇게 된다.

```
STARTING ─BEGIN_REPLAY→ REPLAYING ─(pause_before_index 도달)→ PAUSED
                                                                 │
                          ┌──────────────────────────────────────┤
                          │  채팅 턴                              │ 확정·버리기·편집
                          ↓                                      │ (EDIT_STEPS, 기존)
                     ─BEGIN_AI→ AI_RUNNING ─PAUSE→ PAUSED ───────┘
                                    │
                                    └─AI_BLOCK→ AI_BLOCKED ─(5선택지, 기존)→ …
```

`PAUSED` 가 기본 자리인 것이 요점이다. 그 국면이 바로 「세션이 살아 있는 채로 멈춰 있고
편집·저장을 받는다」이며, 확정·버리기·교체 대상 보기가 전부 편집이다. 지금 전이표의
`PAUSED` 행에 `RECORD_ACTIONS_START → RECORDING` 이 있는 것과 대칭이다 — 사람이 이어
녹화하는 자리가 있으면 AI 가 이어 만드는 자리도 있어야 한다.

**AI 가 도는 동안 편집이 잠기는 것은 옳다.** `AI_RUNNING` 국면의 권한표가 이미 편집 조작을
`off("AI_RUNNING", remedy: run.stop)` 으로 잠근다. 사용자는 턴이 끝난 뒤(`PAUSED`) 고친다.

**버린 대안 1**: 상태를 `PAUSED` 로 유지하고 `SessionView.ai_busy` 플래그를 더하는 것.
`ai_step`(US6)이 지금 그렇게 한다 — 동기 호출이라 상태를 바꾸지 않는다. 그러나 채팅 턴은
길고 중지 가능해야 하며 막힐 수 있다. 막힘을 표현하려면 `PAUSED → AI_BLOCKED` 를 더해야
하고, 그러면 5선택지의 복귀 지점(`CHOOSE_* → AI_RUNNING`)이 재녹화에서만 달라져야 한다 —
**전이표가 세션 종류를 알아야 하는 상태**가 된다. 전이표는 지금 세션 종류를 모르고, 그것이
전이표가 읽히는 이유다.

**버린 대안 2**: 새 상태 `RERECORDING` 을 만드는 것. 국면표에 열이 하나 늘고
(`capabilities.ts` 는 국면당 48행), 그 열의 값 대부분이 `PAUSED`·`AI_RUNNING` 의 복사가
된다. 007 이 국면을 여덟으로 가른 기준은 「성질이 아니라 조작 목록」인데, 재녹화의 조작
목록은 `PAUSED` 와 같다.

---

## R5 — 재녹화 세션을 어떻게 만드는가

**결정**: 세션 생성 모드에 **`rerecord` 를 더한다.** `authoring_mode` 는 `ai` 이고,
엔진을 세워 `pause_before_index` 까지 실행한다.

```
mode=record    → BEGIN_RECORD  · authoring_mode=record · 러너 없음
mode=replay    → BEGIN_REPLAY  · authoring_mode=record · 러너 있음 (pause_before_index 지원)
mode=ai        → BEGIN_AI      · authoring_mode=ai     · 러너 없음
mode=rerecord  → BEGIN_REPLAY  · authoring_mode=ai     · 러너 있음 ← 새로 생김
```

**근거**: `authoring_mode` 와 `state` 는 다른 축이고, 화면은 **둘 다** 본다.
`phaseOfSession` 의 판정 순서가 이렇다:

```
review → finished → paused → takeover → (authoring_mode === "ai") → recording → running
```

`mode: replay` 로 도착점을 만들면 `authoring_mode` 가 `record` 로 남고, 이후 에이전트가
돌 때 상태 `ai_running` 이 `authoring_mode === "ai"` 를 통과하지 못해 **국면이
`running` 으로 판정된다.** 그 국면의 권한표는 편집 조작 전부를
`off("RUNNING_NO_EDIT")` 로 잠그고 화면은 「실행 중」을 말한다 — 사용자는 AI 와 대화하는
중인데 화면은 재실행 중이라고 주장한다. 이것은 005 U-04 가 기록한 결함과 같은 형태다.

그리고 `authoring_mode` 는 **세션의 불변 속성**이다 (001 DR-020). 도중에 바꾸는 것은
그 설계를 깨는 일이고, 깨면 001 research R2 가 규명한 「AI 로 만들기 무반응」이 되살아난다.
그러므로 **만들 때 정해야 하고**, 그래서 새 모드가 필요하다.

**버린 대안**: `mode: ai` + `pause_before_index`. 지금 `ai` 분기는 엔진을 세우지 않고
(`_build_engine` 을 부르지 않는다) 곧바로 `_start_agent` 로 간다. 인자 하나로 그 분기
안에서 「러너를 먼저 돌리고 에이전트는 나중에」를 하면, 한 모드가 두 가지 생애를 갖게
되어 `sessions.py` 의 분기가 세 갈래에서 다섯 갈래가 된다.

---

## R6 — US1 의 「브라우저 없이 대화만」이 성립하는가

**결정**: **성립하지 않는다. 채팅은 세션 안에서만 산다.** US1 은 「구간 재녹화 세션 안에서
테스트를 아는 AI 와 대화한다」로 좁아진다.

**근거 셋**:

1. **가치의 대부분이 화면에서 나온다.** 정의만 아는 AI 는 "6번이 왜 필요하냐" 에 추측으로
   답한다. 화면을 볼 수 있어야 "6번은 저장 확인 모달의 확인 버튼입니다" 가 된다.
2. **이력이 갈리면 FR-009 가 성립하지 않는다.** 세션 없는 경로를 따로 두면 대화 이력이
   화면과 서버 두 곳에 생기고, 「사용자의 말·AI 의 답·막힘 답변·인수 후 재개가 같은
   이력에 붙는다」를 지킬 수 없다.
3. **009 가 같은 판단을 이미 내렸다.** 편집 국면에서 브라우저가 필요한 AI 조작을 누르면
   **제품이 브라우저를 연다** (FR-374a · `cond("C7")`). 두 길이 대등하게 보이지 않던
   문제를 그렇게 고쳤고, 여기서 반대로 가면 규칙이 조작마다 달라진다.

**대가와 완화**: 요약 하나 물으려 해도 브라우저가 뜬다. 조작 이름과 안내가 그것을 **미리**
말한다 — `browser.openAt` 이 하는 것과 같다.

**명세 조정**: spec.md 의 US1 「Independent Test」와 Acceptance 1 이 "브라우저를 열지 않고"
를 전제한다. 이 결정으로 무효가 되며, plan 단계에서 명세를 고친다 (아래 [plan.md](./plan.md)
「명세 조정」).

**버린 대안**: 세션 없는 읽기 전용 질의 경로(`POST /api/chat`)를 따로 두는 것. 싸지만
채팅 구현이 둘이 되고, 헌법의 단순성 규칙(원칙에 요구되지 않는 복잡도는 정당화하거나
제거한다)에 걸린다.

---

## R7 — 되돌리기: 스냅샷이 필요한가

**결정**: **필요 없다.** 세션이 「이번에 만든 Step 의 id 목록」과 「교체 대상 구간의 id
목록」 둘만 들면 확정·버리기가 모두 표현된다.

**근거**: FR-037 이 AI 의 편집 권한을 **이번 세션이 만든 Step** 으로 한정했다. 그래서
재녹화 중에 **옛 구간과 구간 밖은 바뀌지 않는다.** 바뀌지 않는 것을 스냅샷으로 떠 둘
이유가 없다.

| 결말 | 하는 일 |
|---|---|
| 확정 | `range_step_ids` 를 `delete_steps` 로 **한 번에** 지운다 (전부-또는-전무, 011 FR-388) |
| 버리기 | `created_step_ids` 를 `delete_steps` 로 **한 번에** 지운다 → 목록이 시작 전과 동일 |

두 결말이 **같은 함수의 다른 인자**다. 이것이 FR-037 을 「구간 한정」으로 정한 결정의 큰
이득이며, 명세의 결정 절에 적힌 「좁히는 것은 어렵다」의 구체적 내용이다.

**FR-024(교체 대상 표시)는 Step 모델을 건드리지 않는다.** 세션이 `range_step_ids` 를
`SessionView` 에 실어 보내고 **화면이 계산한다.** Step 에 「교체 대상」 필드를 더하면
그것은 작성 주체 외의 의미 필드이고, 저장 형식에 새 뜻이 생겨 원칙 I 이 흔들린다 — 게다가
확정되지 않은 상태가 디스크에 내려갈 수 있게 된다 (FR-029 위반의 문).

**버린 대안**: 작업 중 목록 전체를 복사해 스냅샷으로 두는 것. FR-037 이 없었다면 필요했다.
지금은 「바뀌지 않는 것을 복사해 두고 같은지 비교하는」 일이 된다.

---

## R8 — 컨텍스트 주입의 민감값 차단

**결정**: **정의 요약을 만드는 함수 하나가 유일한 통로**가 되게 하고, 그 함수가 값을
**아예 읽지 않는다.**

```
build_definition_summary(steps, range_ids) -> str
  ├ 각 Step 에서 읽는 것: 순번 · id · label · 종류 · 대상 요약 · 탭 · 교체구간 여부
  └ 절대 읽지 않는 것: value (입력값)
      └ 입력값이 있는 Step 은 "값 있음" 또는 변수 참조 이름만 적는다
```

**근거**: 지금 민감값 방어는 두 겹이다 — `SensitiveCapturer` 가 기록 시점에 변수 참조로
바꾸고, `Scrubber` 가 디스크에 쓰기 직전에 걸러 낸다. 컨텍스트 주입에 `Scrubber` 를 거는
것은 **세 번째 겹**을 만드는 일인데, 스크러버는 「민감하다고 알려진 값」만 안다. 아직
민감으로 표시되지 않은 입력값(사용자가 표시를 깜빡한 사번·주소)은 통과한다.

그래서 **거르는 대신 읽지 않는다.** 요약 함수가 `value` 필드에 접근하지 않으면, 무엇이
민감한지 판정할 필요 자체가 없어진다. 검사는 「요약 문자열에 어떤 Step 의 `value` 도
포함되지 않는다」를 값 100종으로 확인하는 property 형태로 고정한다 (SC-008).

대화 이력(FR-013)은 다르다. 거기엔 **사용자가 직접 친 문장**이 들어가고, 사용자가
비밀번호를 채팅에 적을 수 있다. 이것은 제품이 막을 수 없으며, 막으려 들면 정상 문장을
가린다. 대신 **이력을 디스크에 쓰지 않는 것**으로 방어한다 (FR-014) — 세션이 끝나면
사라진다.

**버린 대안**: 요약에 값을 넣고 `Scrubber` 로 거르기. 위 이유로 구멍이 남는다.

---

## R9 — 원칙 II 를 무엇으로 증명하는가

**결정**: 검사 **셋**을 둔다. 하나는 기존 것이고 둘은 새로 만든다.

| # | 검사 | 무엇을 막는가 |
|---|---|---|
| 1 | `uv run lint-imports` (기존) | `execution → authoring/llm` 임포트. **구조적 도달 불가** |
| 2 | 러너와 에이전트 태스크가 **동시에 살아 있지 않다** (새로) | 도착점 실행 중 에이전트가 도는 것 |
| 3 | `mode=rerecord` 세션의 **도착점 구간에서 드라이버가 한 번도 불리지 않는다** (새로) | 되맞춤 실행(FR-031b) 포함 |

**근거**: 1번만으로는 부족하다. `itb.api` 는 계약의 `source_modules` 에 없으므로, API
계층이 러너를 돌리는 **동시에** 에이전트를 돌리는 코드를 써도 린터는 통과한다. 원칙 II 가
금지하는 것은 임포트가 아니라 **재실행 중 언어모델 호출**이므로, 시간 축의 검사가 필요하다.

3번은 기존 테스트 장치를 그대로 쓴다 — `AuthoringAgent.driver` 가 갈아 끼울 수 있게
설계돼 있고(「테스트가 갈아 끼우는 지점이다 — 원칙 II 검증 테스트(SC-006)도 이 지점을
쓴다」), 호출 횟수를 세는 가짜 드라이버를 끼우면 된다.

**버린 대안**: 런타임 플래그로 막기. 헌법이 명시적으로 거절한다 — 「런타임 플래그가 아니라
임포트 경계로 막으며, 도구가 이를 검사한다」.
