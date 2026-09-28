# 기준선 — 020 이 깨뜨릴 수 있는 것 (T002·T003)

**조사일**: 2026-09-28 · **대상**: FR-033(검증 실패 시 실행을 멈추지 않는다)의 영향권

---

## T003 — 기준선 실행 결과

```
cd backend && uv run pytest -m "not browser and not timing" -q
→ 2259 passed, 14 warnings in 29.17s   (exit 0)
```

이후 실패가 020 때문인지 원래 그랬는지는 이 숫자와 대조해 가른다.

---

## T002 — 「검증 실패가 실행을 멈춘다」를 전제한 검증

### 결론: **0건이다.**

`Runner` 를 통해 **검증 Step 을 실패시키는** 검증이 하나도 없다. 조사 근거:

| 조사 | 결과 |
|---|---|
| `AssertionStep` 을 쓰는 검증 파일 | `us5_support.py` · `sharing_support.py` · `excel_support.py` · `test_generator.py` · `test_definition_summary.py` · `test_manual_step.py` · `test_lazy_loading.py` |
| 그중 `Runner` 로 **실패하는** 검증을 돌리는 것 | 없음 |
| `us5_support.failing_steps()` 의 실패 지점 | **step-06 `ClickStep`** (`_missing_target()`). step-07 의 `AssertionStep` 은 그 뒤라 `NOT_RUN` 이다 |
| `test_lazy_loading.py` 의 실패하는 검증 | `StepExecutor` 를 **직접** 부른다. `Runner` 를 지나지 않으므로 중단 규칙과 무관 |

**동작 Step 실패는 현행대로 멈춘다**(FR-034)는 것이 이 결과의 이유다. 005 가 실패
재료를 만들 때 「존재하지 않는 `testId` 를 가진 버튼 클릭」을 골랐고, 그것이 마침
020 이 건드리지 않는 쪽이었다.

→ **T024 의 작업 범위는 비어 있다.** 고칠 기존 검증이 없다.

---

## 조사 중 발견한 것 — F1 의 실제 기전은 더 나쁘다

정합성 점검(analyze F1)은 「`PARTIAL_PASS` 가 결말에서 검증 실패를 덮는다」로 적었다.
코드를 보니 **덮는 것이 아니라 지운다.**

`Runner.clear_failed_steps()` 는 결과에 있는 **모든** `FAIL` 을 `SKIPPED` 로 바꾼다.

```python
for result in self.results:
    if result.outcome is StepOutcome.FAIL:
        result.outcome = StepOutcome.SKIPPED
```

020 이전에는 이것이 정확했다. **실패는 곧 중단이었으므로 결과에 `FAIL` 이 하나뿐이었고,
그 하나가 곧 사용자가 건너뛰기로 고른 것**이었다. FR-033 이 그 전제를 깬다 —
검증 실패가 쌓인 채로 뒤쪽 동작 Step 에서 멈추면, 사용자가 건너뛰기를 고르는 순간
**아무도 건너뛰지 않은 회귀까지 `SKIPPED` 로 바뀐다.** 결말 판정에 닿기도 전에 증거가
사라진다.

같은 전제를 공유하는 자리가 둘 더 있다 (`api/routes/sessions.py` 의 재개 가드):

| 호출 | 020 이전 | 020 이후의 문제 |
|---|---|---|
| `has_failed_step()` | 「멈춘 실패가 있다」와 같은 말이었다 | 검증 실패만 있어도 참이 되어, **멈추지 않은 실행의 재개를 막는다** |
| `first_failed_index()` | 그 하나의 인덱스 | 가장 앞선 검증 실패를 가리켜, **「Step 03 이 실패해 이어서 갈 수 없습니다」라고 엉뚱한 자리를 지목**한다 |

### 이 발견이 바꾸는 것

T058 의 범위가 `decide_outcome` 한 곳에서 **셋**으로 넓어진다.

1. 건너뛰기는 **멈춘 자리 하나만** 건너뛴다 (`clear_failed_steps` → `skip_blocking_failure`)
2. 재개 가드는 **멈춘 자리**를 본다 (`has_failed_step` → `blocking_failure_index`)
3. `decide_outcome` 은 건너뛰지 않은 실패가 남아 있으면 `PARTIAL_PASS` 로 가지 않는다 (FR-039)

1·2 는 **020 이전 동작을 정확히 보존한다.** 그때는 `FAIL` 이 하나뿐이었고 그것이 곧
멈춘 자리였으므로, 「멈춘 자리 하나」와 「모든 `FAIL`」이 같은 것을 가리켰다. 셋을 다
고쳐야 FR-039 가 실제로 성립한다 — 3만 고치면 1이 이미 증거를 지운 뒤다.

---

## 프론트엔드 기준선 (T003 보완)

```
cd frontend && npm run typecheck && npm test -- --run
→ Test Files  1 failed | 126 passed (127)
        Tests  2 failed | 1495 passed (1497)
```

**실패 2건은 020 이전부터 있던 것이다.** 변경을 전부 stash 한 상태에서 같은 2건이
같은 이유로 실패한다.

| 실패 | 내용 |
|---|---|
| `ScreenSweep > 보고서가 낡지 않았다` | 순회 보고서의 다이제스트가 지금 화면 코드와 다르다 |
| `ScreenSweep > 등록되지 않은 검출이 없다` | 보고서에 WebSocket 403 검출 4건이 등록돼 있다 |

두 번째는 보고서 **내용**의 문제이고 첫 번째는 보고서 **신선도**의 문제다. 020 이
화면 코드를 고치므로 첫 번째는 어차피 다시 나며, 순회 재생성이 마무리 작업에
포함된다 (실제 앱과 브라우저가 필요하다).
