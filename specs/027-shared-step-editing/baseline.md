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
