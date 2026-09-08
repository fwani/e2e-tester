Interactive AI Test Builder — PRD v0.1

1. 제품 개요

1.1 제품 정의

사용자가 브라우저를 직접 조작하거나 자연어로 작업을 지시하여 E2E 테스트를 생성하고, 생성된 테스트를 실행·편집·재사용할 수 있는 브라우저 기반 테스트 자동화 도구.

테스트 작성 과정에서 사용자는 언제든 실행을 멈추고 불필요한 Step을 제거하거나 새로운 Step을 직접 또는 자연어로 추가할 수 있다.

완성된 테스트는 Playwright 기반의 deterministic 테스트로 저장하여 반복 실행한다.

1.2 핵심 가치

기존 E2E 테스트 자동화는 개발자가 직접 Playwright/Selenium 코드를 작성하거나 Recorder가 생성한 코드를 수정해야 한다.

본 제품은 테스트 작성 과정을 다음과 같이 단순화한다.

직접 수행해서 만들거나 → 말로 만들어 달라고 하거나 → 중간에 고쳐서 완성한다.

Manual Record ─────┐
                   │
                   ▼
               Test Steps
                   ▲
                   │
Natural Language ──┘
                   │
                   ▼
           Interactive Edit
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
        Pause    Delete     Add
                   │
                   ▼
               Continue
                   │
                   ▼
             Playwright Test
                   │
                   ▼
              Repeat Run

⸻

2. 문제 정의

2.1 현재 문제

P1. E2E 테스트 작성 비용이 높다

Playwright/Selenium 기반 E2E 테스트는 개발 지식이 필요하다.

기획자나 QA가 테스트 시나리오를 알고 있어도 실제 자동화 테스트를 작성하려면 개발자의 작업이 필요하다.

P2. Recorder 결과는 테스트 의도를 충분히 표현하지 못한다

기존 Recorder는 사용자의 클릭과 입력을 기록할 수 있지만 사용자가 왜 해당 행동을 했는지는 알지 못한다.

예:

click #menu
click #project
fill #name "TEST"
click #save

이 기록의 실제 목적은 다음과 같을 수 있다.

"TEST라는 프로젝트가 정상적으로 생성되는지 확인한다."

P3. 자연어 Browser Agent의 실행은 테스트 자산으로 활용하기 어렵다

AI Browser Agent는 자연어 명령을 수행할 수 있지만 매 실행마다 AI가 화면을 판단하면 다음 문제가 발생한다.

* 실행 결과의 비결정성
* LLM 호출 비용
* 실행 속도 저하
* 모델 변경에 따른 결과 변화
* 테스트 재현성 저하

따라서 AI가 성공적으로 수행한 결과를 deterministic한 테스트로 변환할 필요가 있다.

P4. Recorder로 생성한 테스트를 수정하기 불편하다

실제 사용자가 업무를 녹화하면 테스트에 필요 없는 행동이 포함될 수 있다.

예:

프로젝트 메뉴
→ 데이터 메뉴        # 실수
→ 프로젝트 메뉴      # 복귀
→ 프로젝트 생성

기존 테스트 생성 방식에서는 녹화를 다시 하거나 생성된 코드를 직접 수정해야 하는 경우가 많다.

P5. 테스트 실행 실패 시 수정 루프가 길다

일반적인 흐름:

Run
 ↓
Fail
 ↓
코드/테스트 수정
 ↓
처음부터 Run
 ↓
Fail
 ↓
다시 수정

특히 로그인 → 데이터 준비 → 화면 이동 등 사전 과정이 긴 통합 테스트에서는 반복 비용이 크다.

⸻

3. 목표

3.1 Product Goal

코드를 직접 작성하지 않고 실제 브라우저를 이용해 신뢰할 수 있는 E2E 테스트를 만들 수 있게 한다.

3.2 핵심 목표

G1. Manual Recording

사용자가 직접 브라우저를 조작하여 테스트를 생성할 수 있다.

G2. Natural Language Recording

사용자가 자연어로 원하는 작업을 설명하면 AI가 실제 브라우저에서 해당 작업을 수행하고 그 과정을 테스트로 기록한다.

G3. Interactive Test Editing

생성 또는 실행 중인 테스트를 멈추고 Step을 추가·삭제·수정할 수 있다.

G4. Deterministic Replay

AI를 통해 만들어진 테스트라도 최종적으로는 deterministic한 Playwright 테스트로 반복 실행할 수 있어야 한다.

⸻

4. 핵심 사용자

Developer

반복적인 E2E 테스트 코드를 빠르게 작성하고 싶은 개발자.

QA

코드 작성 없이 통합 테스트 시나리오를 자동화하고 싶은 사용자.

Product Manager / Planner

자신이 정의한 사용자 시나리오를 실제 브라우저 테스트로 만들어 검증하고 싶은 사용자.

⸻

5. 핵심 사용자 Flow

Flow A — Manual Record

Create Test
 ↓
Record 선택
 ↓
Browser 실행
 ↓
사용자가 직접 업무 수행
 ↓
Action Recording
 ↓
Stop
 ↓
Test Step 생성
 ↓
편집
 ↓
Save

예:

[Record]
프로젝트 메뉴 클릭
프로젝트 생성 클릭
프로젝트명 TEST 입력
저장 클릭
[Stop]

결과:

TC-001 프로젝트 생성
01 프로젝트 메뉴 클릭
02 프로젝트 생성 클릭
03 프로젝트명 "TEST" 입력
04 저장 클릭

⸻

6. Natural Language Record

사용자가 자연어로 수행할 업무를 입력한다.

예:

로그인한 다음 프로젝트 메뉴로 이동해서
TEST라는 프로젝트를 생성하고
프로젝트 목록에 TEST가 있는지 확인해.

시스템 처리:

Natural Language
       ↓
      LLM
       ↓
 Browser Agent
       ↓
 실제 Browser
       ↓
Action Recorder
       ↓
 Test Steps

실제 실행:

✓ 로그인
✓ 프로젝트 메뉴 이동
✓ 프로젝트 생성 클릭
✓ TEST 입력
✓ 저장
✓ TEST 표시 확인

이 결과를 테스트로 저장한다.

중요:

자연어 명령 자체를 테스트로 저장하지 않는다.

AI가 실제 브라우저에서 성공적으로 수행한 결과를 실행 가능한 Step으로 변환하여 저장한다.

⸻

7. Interactive Test Editing

본 제품의 핵심 차별화 기능이다.

테스트 실행 중 사용자는 언제든 Pause 할 수 있다.

01 로그인                 ✓
02 프로젝트 메뉴           ✓
03 데이터 메뉴             ✓
          ⏸ PAUSE
04 프로젝트 메뉴
05 프로젝트 생성
...

Pause 상태에서는 다음 작업을 수행할 수 있다.

* Step 삭제
* Step 수정
* Step 추가
* 순서 변경
* 직접 Browser 조작으로 Step 추가
* 자연어로 Step 추가
* Assertion 추가
* 해당 Step부터 다시 실행
* 현재 Browser 상태에서 Continue

7.1 Manual Add

Pause
 ↓
Record Step
 ↓
사용자가 Browser 직접 조작
 ↓
새로운 Step 기록
 ↓
Continue

7.2 AI Add

예:

"생성된 프로젝트가 목록에 있는지 확인해."

AI:

현재 Browser 분석
 ↓
TEST element 탐색
 ↓
Assertion 생성

결과:

05 Assert "TEST" visible

⸻

8. AI Failure → Human Takeover

AI가 작업을 수행하지 못했을 경우 사용자가 즉시 이어받을 수 있어야 한다.

예:

01 로그인                       ✓
02 프로젝트 메뉴                 ✓
03 프로젝트 생성                 ✓
04 TEST 입력                    ✓
05 저장                         ✓
06 프로젝트 삭제                 ✕
AI:
"프로젝트 삭제 버튼을 찾지 못했습니다."
────────────────────────
[직접 수행]
[AI에게 다시 지시]
[건너뛰기]
[종료]

사용자가 직접 수행을 선택하면 현재 Browser Session을 유지한다.

사용자:

⋮ 클릭
→ 삭제 클릭
→ 확인

Recorder:

06 프로젝트 메뉴 클릭
07 삭제 클릭
08 확인 클릭

이후:

▶ Continue

하여 AI 또는 자동 테스트가 이어서 진행한다.

⸻

9. Test Step Model

테스트를 Playwright 코드 자체로 관리하지 않는다.

중간 표현인 Test Step DSL을 사용한다.

예:

id: TC-PROJECT-001
name: 프로젝트 생성
variables:
  PROJECT_NAME: TEST
steps:
  - id: step-01
    type: click
    target:
      role: menuitem
      name: 프로젝트
  - id: step-02
    type: click
    target:
      role: button
      name: 프로젝트 생성
  - id: step-03
    type: fill
    target:
      label: 프로젝트명
    value: "{{PROJECT_NAME}}"
  - id: step-04
    type: click
    target:
      role: button
      name: 저장
  - id: step-05
    type: assertion
    assertion: visible
    target:
      text: "{{PROJECT_NAME}}"

DSL을 기준으로:

* UI Editor
* AI
* Recorder
* Playwright Generator

가 동일한 테스트 모델을 사용한다.

⸻

10. Locator 전략

Recorder는 CSS Selector 하나만 저장하지 않는다.

Element에 대해 가능한 locator 정보를 수집한다.

{
  "tag": "button",
  "text": "프로젝트 생성",
  "role": "button",
  "testId": "create-project",
  "css": ".project-header button:nth-child(2)"
}

권장 우선순위:

testId
 ↓
role + accessible name
 ↓
label
 ↓
text
 ↓
stable attribute
 ↓
CSS

목표는 화면 구조 변경에 최대한 안정적인 테스트를 생성하는 것이다.

⸻

11. Test Execution

완성된 Test Step은 Playwright로 실행한다.

Test DSL
   ↓
Playwright Generator
   ↓
Playwright Runner
   ↓
Browser
   ↓
Execution Result

결과:

TC-001 프로젝트 생성
✓ 로그인                    421 ms
✓ 프로젝트 이동              302 ms
✓ 프로젝트 생성              581 ms
✓ 이름 입력                  103 ms
✕ 저장                      5.0 sec
Error:
"저장" 버튼을 찾을 수 없습니다.
Screenshot
Trace
Console
Network

⸻

12. AI 사용 원칙

AI는 기본적으로 Test Authoring 과정에서 사용한다.

Natural Language
        ↓
      AI Agent
        ↓
Browser에서 성공적으로 수행
        ↓
Deterministic Step으로 Compile
        ↓
저장
        ↓
이후 Replay
AI 호출 X

이를 통해:

* 실행 비용 감소
* 실행 속도 향상
* 결과 재현성 향상
* LLM 장애 영향 감소

를 목표로 한다.

필요한 경우 사용자가 명시적으로 AI 기반 Step을 유지하는 기능은 향후 검토한다.

⸻

13. Playwright Export

작성된 테스트는 표준 Playwright 프로젝트로 Export 가능해야 한다.

Export
 ↓
playwright-tests/
tests/
 ├── login.spec.ts
 ├── project-create.spec.ts
 └── project-delete.spec.ts
playwright.config.ts
package.json

사용자는 제품을 사용하지 않더라도 생성한 테스트 자산을 계속 사용할 수 있다.

⸻

14. MVP 범위

P0 — 필수

* 프로젝트 생성
* 테스트 생성/저장
* Browser 실행
* Manual Record
* Click 기록
* Input 기록
* Select 기록
* Navigation 기록
* Assertion 추가
* Step Editor
* Step 삭제
* Step 추가
* Step 순서 변경
* Pause
* Continue
* Playwright 실행
* PASS / FAIL
* Screenshot
* 실행 로그

P1 — AI

* 자연어 테스트 입력
* Browser Agent
* Agent 행동 Recording
* AI → deterministic Step 변환
* AI 실패 시 Pause
* Human Takeover
* 자연어 Step 추가

P2 — 운영

* Test Suite
* Environment
* Variables
* Test History
* Trace
* Video
* Schedule
* Playwright Export
* CI/CD 연동

⸻

15. MVP에서 제외

초기 버전에서는 다음 기능을 제외한다.

* Mobile App 테스트
* Native App 테스트
* API Test Builder
* Performance Test
* Load Test
* Visual Regression
* Cross-browser Cloud Farm
* 복잡한 Test Management
* AI Self-Healing 자동 적용
* 테스트 데이터 자동 생성

⸻

16. 핵심 화면

Test List

Integration Tests
Project Tests
TC-001 프로젝트 생성       PASS
TC-002 프로젝트 삭제       PASS
TC-003 데이터 업로드       FAIL
TC-004 분석 실행           PASS
                     [+ Create Test]

Create Test

Create Test
┌───────────────────┐
│ ● Record          │
│                   │
│ 직접 Browser에서   │
│ 테스트를 수행합니다 │
└───────────────────┘
┌───────────────────┐
│ ✨ AI Record       │
│                   │
│ 자연어로 테스트를   │
│ 생성합니다.         │
└───────────────────┘

Interactive Runner

TC-001 프로젝트 생성
Browser                         Test Steps
┌────────────────────┐        01 프로젝트 메뉴       ✓
│                    │        02 프로젝트 생성       ✓
│   Actual Browser   │        03 TEST 입력          ✓
│                    │     →  04 저장               ●
│                    │        05 TEST 확인
└────────────────────┘
                             [+ Step]
[⏸ Pause] [■ Stop]

Pause:

04 저장
[▶ Continue]
[직접 동작 추가]
[✨ AI에게 지시]
[Assertion 추가]
[수정]
[삭제]

⸻

17. 차별화

본 제품은 단순 Browser Recorder가 아니다.

기존 Recorder

Human
 ↓
Record
 ↓
Code
 ↓
Replay

AI Browser Agent

Prompt
 ↓
AI
 ↓
Browser

본 제품

              Human
                ↓
             Browser
                ↓
             Recorder
                ↑
             Browser
                ↑
               AI
                │
                ▼
            Test Model
                │
                ▼
       Interactive Editor
                │
       Pause / Edit / Resume
                │
                ▼
       Deterministic Test
                │
                ▼
           Playwright

핵심 차별점은 다음 네 가지다.

1. Human과 AI가 동일한 테스트를 작성할 수 있다.

2. AI가 실패하면 현재 상태 그대로 Human이 이어받을 수 있다.

3. 테스트 작성/실행 도중 Pause → Edit → Resume이 가능하다.

4. AI가 작성하더라도 최종 결과는 AI에 의존하지 않는 deterministic Playwright 테스트가 된다.

⸻

18. 핵심 성공 지표

MVP 검증 시 다음 지표를 측정한다.

Test Creation Success Rate

사용자가 코드 수정 없이 테스트 생성에 성공한 비율.

목표:

≥ 80%

Natural Language Success Rate

자연어 시나리오를 AI가 정상적인 deterministic 테스트로 변환한 비율.

초기 목표:

≥ 70%

Replay Success Rate

생성 당시 성공한 테스트가 동일 환경에서 다시 성공하는 비율.

목표:

≥ 95%

Human Takeover Recovery Rate

AI 실패 후 Human Takeover를 이용해 테스트 생성을 완료한 비율.

목표:

≥ 80%

Test Creation Time

기존 Playwright 코드 작성 대비 테스트 생성 시간 감소율.

목표:

≥ 50%

**009 의 영향 (2026-09-08, 헌법 품질 게이트 5)**

이 지표는 처음 만드는 시간뿐 아니라 **고치는 시간**에도 걸린다. 실무에서 테스트는 한 번
만들고 여러 번 고친다.

009 는 Step 을 넣고 옮기고 지우는 조작 횟수를 줄였다 (`specs/009-step-editing-flow/baseline.md`).

| 일 | 이전 | 이후 |
|---|---|---|
| 요소 지목이 필요 없는 Step 을 원하는 자리에 넣기 | 브라우저를 열고 그 자리까지 재생해야 했다 (조립 5단계) | **2회** · 브라우저 없음 |
| 요소가 필요한 Step 을 넣기 위해 그 자리에서 멈추기 | 조립 5단계 | **1회** |
| Step 하나를 세 칸 옮기기 | 6회(편집) · 5회(일시정지) | **3회** |

**시간으로 측정하지 않았다.** 조작 횟수는 대리 지표이며, 브라우저를 열지 않게 된 경로
(첫 줄)에서는 재생 대기 시간이 통째로 없어지므로 감소가 횟수보다 크다. 시간 측정이
필요하다면 별도 계측이 있어야 한다 — **확인 필요 사항으로 남긴다.**

⸻

19. 제품 포지셔닝

제품을 단순히

“AI E2E Testing Tool”

로 정의하지 않는다.

제품의 핵심 포지션은:

Interactive AI Test Builder

설명:

사람이 직접 하거나 AI에게 말해서 브라우저 테스트를 만들고, 실행 중 언제든 멈춰 수정한 뒤 이어서 완성하는 E2E 테스트 자동화 도구.

Short Message:

Record it. Tell it. Fix it. Replay it.

⸻

20. 핵심 가설

본 제품이 검증해야 할 가장 중요한 가설은 다음과 같다.

사용자는 완벽하게 테스트를 자동 생성해주는 AI보다, AI가 대부분을 수행하고 실패하거나 잘못된 부분만 사람이 즉시 수정할 수 있는 방식을 더 신뢰하고 효율적으로 사용할 것이다.

따라서 MVP의 기술적 핵심은 LLM 성능 자체가 아니라 다음 세 가지다.

Recorder

Human과 AI의 모든 브라우저 행동을 동일한 Step Model로 기록한다.

Stateful Interactive Runner

Browser 상태를 유지하면서 Pause → Edit → Resume을 지원한다.

Deterministic Compiler

최종 Step Model을 안정적인 Playwright 테스트로 변환한다.

이 세 요소를 MVP의 핵심 기술 검증 대상으로 한다.

다음 단계에서는 이 PRD에서 바로 **사용자 시나리오 → 기능 요구사항(FR-001...) → 화면 → API/DB → Recorder/Runner 아키텍처 → MVP 개발 순서**로 내려가는 게 좋습니다. 특히 먼저 Pause/Edit/Resume을 기술적으로 어디까지 보장할 것인지를 정의해야 전체 설계가 흔들리지 않습니다.