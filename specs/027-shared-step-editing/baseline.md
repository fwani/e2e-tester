# Baseline — 027 시작 시점 (2026-09-30)

**이 증분은 사용자가 보는 변화가 0 이다.** 그래서 기준선의 뜻이 다른 기능과 반대다 —
「무엇이 새로 되는가」가 아니라 **「무엇이 그대로여야 하는가」**를 적는다.

## 전량 검증 (T001)

| 검증 | 결과 |
|---|---|
| 프론트 `npx vitest run` | **2 failed** · 1663 passed (143 파일 중 1 실패) |
| 프론트 `npx tsc --noEmit` | 통과 |
| 백엔드 병렬 | 4 failed · 3468 passed (026 에서 확인) |
| 백엔드 순차 | 60 passed |
| ruff | 2 errors |
| lint-imports | 4 kept · 0 broken |

### 기존 실패 — 027 의 것이 아니다

| # | 실패 | 자리 |
|---|---|---|
| 1~2 | `ScreenSweep.test.ts` 2건 | `frontend/tests/ScreenSweep.test.ts` |
| 3~6 | `test_abnormal_screen_operation_is_handled[AS-009·025·037·046]` | `backend/tests/abnormal/test_ui_surface.py` |
| 7~8 | ruff `E501` 2건 | `step_executor.py:839` · `test_negative_assertion.py:126` |

**백엔드는 이 증분에서 한 파일도 바뀌지 않는다.** 끝에서 3~8 이 **글자 그대로** 같아야
하며, 다르면 범위를 벗어난 것이다 (T038a).

---

## 회귀 확인 대상 (T002)

이 증분은 화면 구조를 바꾸므로 **화면 검사 전부가 회귀 대상**이다. 아래는 그중 특히
이 증분의 성패를 말하는 것들이다.

| 검사 | 무엇을 지키는가 | 깨지면 |
|---|---|---|
| `CapabilityCoverage.test.ts` | 조작표에 빈칸이 없다 (011) | 조작표를 건드렸다 — 이 증분은 표를 바꾸지 않는다 (FR-020) |
| `CapabilityUI.test.tsx` | 표가 말한 조작이 화면에 있다 (007 SC-004) | 조작이 화면에서 사라졌다 |
| `ScreenSweep.test.ts` | 화면이 깨지지 않았다 (017) | 겉모습이 바뀌었다 (SC-007 위반) |
| `VisualLanguage`·`ClassExistence` | 정본 밖 클래스를 쓰지 않았다 (008) | 새 CSS 를 만들었다 |
| `LabelUniqueness.test.ts` | 한 라벨이 두 조작을 갖지 않는다 (011 FR-235) | 조작 자리를 옮기며 라벨이 겹쳤다 |
| `StepNumberConsistency` | Step 번호 조립이 한 곳이다 | — |
| `RerecordStart`·`RerecordTransaction`·`RerecordRegression`·`RerecordBandPlacement` | 016 재녹화 흐름 | 조작 이전이 016 을 건드렸다 |
| `StepEditEntry`·`StepEditChanges` | 026 Step 수정 흐름 | 조작 이전이 026 을 건드렸다 |
| `AiErrorDismiss`·`ChatPanel` | AI 관련 화면 | — |

**시작 시점 총계: 143 파일 · 1665건 중 1663 통과.**

---

## 지금 어댑터가 처리하는 조작 (T003)

이전이 끝났을 때 **하나도 빠지지 않았는지** 대조할 근거다.

### `SessionScreen` (22종)
```
nav.back · result.show · run.all · run.from · run.fromHere · run.pause · run.resume
run.resumeSkipFailure · run.stop · save · step.addAssertion · step.addNaturalLanguage
step.delete · step.deleteAfter · step.deleteSelected · step.insertManual · step.moveDown
step.moveUp · step.recordStart · step.recordStop · step.update
```

### `EditView` (22종)
```
ai.chat · ai.rerecord · ai.stepEdit · ai.stepEditCommit · ai.stepEditDiscard
browser.openAt · edits.revert · nav.back · result.show · run.all · run.from · save
save.overwriteStale · session.open · step.addNaturalLanguage · step.delete
step.deleteAfter · step.deleteSelected · step.insertManual · step.moveDown · step.moveUp
step.recordStart
```

### `ResultView` (8종)

### 둘 다 처리하는 13종 — **이번에 옮길 것**
```
nav.back · result.show · run.all · run.from · save · step.addNaturalLanguage
step.delete · step.deleteAfter · step.deleteSelected · step.insertManual
step.moveDown · step.moveUp · step.recordStart
```

### 한쪽에만 있는 것 — **정당한 차이일 수 있다**

| 세션에만 | 편집에만 |
|---|---|
| `run.fromHere` · `run.pause` · `run.resume` · `run.resumeSkipFailure` · `run.stop` · `step.addAssertion` · `step.recordStop` · `step.update` | `ai.chat` · `ai.rerecord` · `ai.stepEdit` · `ai.stepEditCommit` · `ai.stepEditDiscard` · `browser.openAt` · `edits.revert` · `save.overwriteStale` · `session.open` |

**`step.update` 가 눈에 띈다** — 세션에만 있고, 편집 화면은 `StepEditFields` 라는 다른
경로로 같은 일을 한다. 그것이 편집면이 두 벌인 결과다 (T027 이 이것을 옮긴다).

---

## 끝 시점 결과 (T041)

| 검증 | 시작 | 끝 | 판정 |
|---|---|---|---|
| 프론트 | 2 failed · 1663 passed | **2 failed · 1706 passed** | 같다 · 신규 43건 |
| 프론트 타입 | 통과 | **통과** | 같다 |
| 백엔드 병렬 | 4 failed · 3468 passed | **4 failed · 3475 passed** | 같다 |
| 백엔드 순차 | 60 passed | **61 passed** | 같다 |
| ruff | 2 errors | **2 errors** | 같다 |
| lint-imports | 4 kept · 0 broken | **4 kept · 0 broken** | 같다 |

**새로 깨진 것이 없다.** 실패 8건은 시작 시점과 같은 8건이다.

> 백엔드를 한 번 돌렸을 때 5 failed 가 났고, 다시 돌리니 4 failed 였다. 다섯째는
> **불안정한 실패**이며 027 과 무관하다 — 백엔드 파일이 한 개도 바뀌지 않았음을
> `git diff --stat backend/` 가 빈 결과로 확인한다 (T038a).

---

## 지켜야 했던 것들의 결과

| 확인 | 결과 |
|---|---|
| 조작표(`capabilities.ts`) 미변경 (FR-020 · T036) | **한 글자도 안 바뀜** |
| 백엔드 미변경 (FR-023 · T038a) | **한 파일도 안 바뀜** |
| `Workbench` 3층 구조 (FR-019 · T037) | props 교체 + 속성 하나. 구조 그대로 |
| 배선이 국면을 모름 (FR-006 · T038) | `phase`·`enabled` 등 **0회** |
| 새 CSS 클래스 (T040) | **없음** |
| 좁히기 통로 (FR-007 · T020a) | 셋 다 살아 있음 |

---

## T043 — 어댑터 줄 수는 **늘었다**

| | 시작 | 끝 |
|---|---|---|
| `SessionScreen` | 3739 | 3751 |
| `EditView` | 1500 | 1535 |
| `ResultView` | 680 | 692 |

계획은 「줄어야 한다」고 적었고 **늘었다.** research R7 의 실패 정의에 해당하는지
판단했다.

**해당하지 않는다.** R7 이 적은 실패는 둘이다.

| R7 의 실패 정의 | 실제 |
|---|---|
| 배선 모듈이 국면을 알기 시작한다 | **아니다** — 검사가 `phase`·`enabled` 0회를 고정한다 |
| 능력 묶음이 화면마다 다른 모양이 된다 | **아니다** — 세 화면이 같은 `ScreenCapabilities` 하나를 쓴다 |

늘어난 것은 **주석**이다. 능력 묶음마다 「왜 이 구현이 화면마다 다른가」(FR-004·FR-005)를
적었고, 그것이 이 저장소의 관행이다. 실제 로직은 줄었다 — 조작 13개의 중복 구현과
편집면 한 벌이 사라졌다.

**줄 수는 이 증분의 성공 기준이 아니다.** 성공 기준은 SC-001(새 조작을 한 곳만 고쳐도
된다)·SC-002(표가 말한 조작이 100% 동작한다)·SC-006(13개 중복이 사라진다)이고 셋 다
충족됐다.

---

## `fallback` 에 남은 것 (T039)

이행이 끝난 뒤 각 화면의 `fallbackAction` 에 남은 조작들.

```
SessionScreen (7)  nav.editStep · run.fromHere · run.pause · run.resume ·
                   run.resumeSkipFailure · run.stop · step.recordStop
EditView (9)       ai.chat · ai.rerecord · ai.stepEdit · ai.stepEditCommit ·
                   ai.stepEditDiscard · browser.openAt · edits.revert ·
                   save.overwriteStale · session.open
ResultView (5)     console · nav.editStep · network · screenshot · trace
```

**전부 그 화면 고유의 조작이다.** 계약 §5 의 「이행이 끝나면 비워진다」는 기술이
틀렸고 정정했다 — 비는 것이 아니라 **공통인 것만 빠져나가고 고유한 것이 남는다.**
그것이 이 증분이 그은 경계다.
