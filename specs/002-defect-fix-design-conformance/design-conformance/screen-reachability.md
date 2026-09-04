# 독립 화면 도달 경로 — DC-008 · SC-109

**완료 조건**: 확정 디자인이 독립 artboard 로 정의한 8종이 제품에서도 **독립 화면으로
도달 가능**할 것. 다른 화면 안에 합쳐져 있지 않을 것.

001 에서는 8종 중 **4종**(AiRecord·RunnerPaused·Takeover·StepInspector)이 `Runner.tsx`
안의 조건부 패널이었다. 그 얽힘이 "AI 실패가 화면에 안 보이는" 결함의 원인이었다
(research R2).

## 대응표

| # | 확정 디자인 | 제품 파일 | 도달 경로 | 001 → 002 |
|---|---|---|---|---|
| D1 | `TestList.dc.html` | `pages/TestList.tsx` | 프로젝트 열기 → 목록 | 독립 유지 |
| D2 | `CreateTest.dc.html` | `pages/CreateTest.tsx` | 목록 → 「테스트 만들기」 | 독립 유지 |
| D3 | `AiRecord.dc.html` | `pages/AiRecord.tsx` | 만들기 → 「지시문 쓰기」 → 실행 | **패널 → 독립** |
| D4 | `Main.dc.html` | `pages/Runner.tsx` | 만들기 → 「녹화 시작」, 또는 목록에서 「실행」 | 독립 유지 |
| D5 | `RunnerPaused.dc.html` | `pages/RunnerPaused.tsx` | 실행 중 → 「일시정지」, 또는 중지 → 검토 | **패널 → 독립** |
| D6 | `Takeover.dc.html` | `pages/Takeover.tsx` | AI 수행 중 실패 → 자동 전환 | **패널 → 독립** |
| D7 | `RunResult.dc.html` | `pages/RunResult.tsx` | 목록에서 「결과 보기」, 또는 실행 종료 후 | 독립 유지 |
| D8 | `StepInspector.dc.html` | `pages/StepInspector.tsx` | Step 선택 → 「Step 수정」 | **컴포넌트 → 독립 화면** |

## 구조적 근거

`pages/SessionScreen.tsx` 가 세션 구독·상태·명령을 **소유**하고, D3·D4·D5·D6 중
**정확히 하나**를 고른다. 각 페이지는 표시만 하고 세션을 모른다.

```
if (isAiSession && !isPaused && !isTakeover)  → AiRecord   (D3)
if (isTakeover)                               → Takeover   (D6)
if (isPaused || isReview)                     → RunnerPaused (D5)
otherwise                                     → Runner     (D4)
```

**AI 세션 판정은 `authoring_mode` 로 한다** — `view.state` 가 아니다. 그것이 세션의
불변 속성이라, AI 가 실패해 상태가 `paused` 로 바뀌어도 AI 화면과 실패 사유가 유지된다
(DR-020). 001 은 `["ai_running","ai_blocked"].includes(view.state)` 로 판정해, 실패
직후 조건이 거짓이 되면서 오류 표시가 통째로 사라졌다.

D8 은 세션 화면 위에 오른쪽에서 겹쳐 띄운다. 확정 디자인이 `borderLeft: 3px` 를 둔
640×1140 세로 판이므로 옆에서 들어오는 판으로 읽는 것이 자연스럽다 —
`undefined-states.md` 에 기록했다.

## 확정 디자인에 대응이 없는 화면 (DC-010)

1:1 대조 의무가 적용되지 않는다. 8화면의 시각 언어만 따른다.

| 화면 | 제품 파일 | 도달 경로 |
|---|---|---|
| 프로젝트 선택 | `pages/ProjectSetup.tsx` | 첫 진입, 또는 열린 프로젝트가 없을 때 |
| 테스트 정의 보기 | `pages/TestDefinition.tsx` | 목록의 `⋯` → 「정의 보기」 |
| 키 관리 | `pages/KeyManagement.tsx` | 목록 헤더 → 「키 관리」 |
| 비밀 값 관리 | `pages/SecretValues.tsx` | 목록 헤더 → 「비밀 값」 |
| AI 지시문 작성 | `pages/AiCompose.tsx` | 만들기 → 「지시문 쓰기」 (D3 을 `composing` 으로 재사용) |

## 판정

이 표는 **구현자가 채운 도달 경로**다. 실제로 각 화면에 도달하는지는 리뷰어가
`quickstart.md §6` 절차로 확인한다 (T099).
