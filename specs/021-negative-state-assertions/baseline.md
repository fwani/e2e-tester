# 기준선 — 021 이 무엇을 바꿨는지 가릴 근거

**작성**: 2026-09-28 (T002·T003) | **갱신**: T019 · T042

이 기능은 **기존 동작 하나를 바꾼다** — 화면 전체 텍스트 검증이 지금은 한 번 읽고 판정하는데,
앞으로는 제한 시간까지 기다린다. 그래서 「이 기능 때문에 깨졌는가」와 「원래 그랬는가」를
가릴 수 있어야 하고, 이 문서가 그 근거다.

---

## 1. 변경 전 기준선 (T002)

### 1.1 프런트엔드

```
cd frontend && npm run typecheck && npm test -- --run
```

| 항목 | 값 |
|---|---|
| 파일 | 131 통과 / **1 실패** (132) |
| 검증 | 1539 통과 / **2 실패** (1541) |
| 소요 | 54.22s (벽시계 1:07.42) |

**변경 전부터 실패하고 있던 것** — 021 과 무관하다:

- `frontend/tests/ScreenSweep.test.ts` 2건. 제어 채널 WebSocket 핸드셰이크가 403 으로
  거절되는 콘솔 오류가 화면 훑기에 잡힌다. 021 이 건드리는 코드 경로가 아니다.

> 이 두 건이 **끝까지 실패로 남아야 정상이다.** 021 작업 중 초록으로 바뀌면 그것이
> 오히려 조사 대상이다 — 다른 것을 함께 바꿨다는 뜻이기 때문이다.

### 1.2 백엔드

```
cd backend && bash scripts/test-backend.sh
```

| 계층 | 결과 | 소요 |
|---|---|---|
| 병렬 (`-m "not timing"`) | 3011 통과 / **5 실패** / 1 건너뜀 | 252.03s |
| 순차 (`-m timing -n 0`) | 50 통과 / 3017 제외 | 127.94s |
| 합계 (벽시계) | | **6:21.22** |

**변경 전부터 실패하고 있던 것** — 021 과 무관하다:

```
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-009]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-012]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-025]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-037]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-046]
```

다섯 건 모두 이상 화면의 조작 표면을 보는 같은 검증이고, 021 이 건드리는 코드 경로가
아니다. **끝까지 실패로 남아야 정상이다.**

---

## 2. 대기 규칙 통일의 영향권 (T003)

FR-003 이 텍스트 검증에 폴링을 도입하면, **검증이 실패하는 경로만** 느려진다. 통과하는
검증은 조건이 참이면 즉시 끝나므로 지금과 같다.

### 2.1 실제로 느려지는 것

| 검증 | 왜 |
|---|---|
| `backend/tests/integration/test_expected_value_kept.py` | `fixtures/sample-app/defective-save.html` 에서 **화면 전체 텍스트 검증이 일부러 실패한다**. 실패할 때마다 제한 시간(기본 10초)을 소모하게 된다. 실패 지점이 여럿이라 누적된다 |

이 파일이 **T019 의 작업 범위**다. 고치는 방법은 그 검증의 `timeout_ms` 를 짧게 주는
것이고, **제품의 대기 동작을 되돌리지 않는다.**

### 2.2 영향이 없는 것 — 확인한 근거

| 검증 | 왜 영향이 없는가 |
|---|---|
| `backend/tests/contract/test_assert_condition_mismatch.py` | 실행기를 타지 않는다. 실패를 흉내 내어 기록 경로만 본다 |
| `backend/tests/unit/test_assertion_does_not_halt.py` | 같음. 중단 판단만 본다 |
| `backend/tests/integration/test_duplicate_id_targets.py` · `test_twin_search.py` | 텍스트 검증을 쓰지만 **통과하는** 검증이다. 조건이 참이면 즉시 끝난다 |
| `backend/tests/contract/test_step_edit_api.py` · `test_definition_edit_api.py` | 수동 삽입 서술만 다룬다. 실행하지 않는다 |
| `backend/tests/unit/test_generator.py` · `test_export_keeps_assertion.py` | 생성기만 본다 |

---

## 3. 변경 후 (T019 · T042)

*(작업 진행에 따라 채운다)*

### 3.1 소요 시간 비교 (T019)

| 대상 | 변경 전 | 대기 도입 직후 | 제한 시간 조정 후 |
|---|---|---|---|
| `test_expected_value_kept.py` | (전체에 포함, 개별 미측정) | **65.40s** | **9.41s** |

일부러 어긋나는 검증마다 기본 제한 시간(10초)이 붙어 약 60초가 늘었다. 그 파일이 재는
것은 「어긋나도 Step 이 남는가」이지 「얼마나 기다리는가」가 아니므로, **그 검증들의
제한 시간을 700ms 로 줄여** 회복했다. **제품의 대기 동작은 되돌리지 않았다** — 그
동작은 `tests/integration/test_negative_assertion.py` 가 따로 본다.

이를 위해 작성 도구에 `timeout_ms` 인자를 더했다. 도구 개수는 늘리지 않았다. 부정
검증에서 제한 시간이 **관찰 기간**이 된 이상 작성 시점에 그것을 정할 수단은 설계상
필수이므로, 회피책이 아니라 빠져 있던 것을 채운 것이다.

### 3.2 결과가 바뀐 검증 — **무엇이 왜 바뀌었는지**

| 검증 | 무엇이 바뀌었나 | 왜 |
|---|---|---|
| `test_manual_step.py::test_라벨을_서술에서_파생한다` | 기대 라벨에 비교 방식이 붙음 | FR-023 — 이름이 비교 방식을 담지 않으면 정반대 뜻의 두 Step 이 목록에서 똑같이 보인다. 부정형 사례 2개를 함께 더했다 |
| `test_definition_edit_api.py::test_정의_편집_입구도_같은_step_을_만든다` | 같음 | 같음 |
| `test_error_handling.py::test_step_executor_never_returns_silently_on_failure` | 원문 검색 → 구문 트리 검사 | 관찰 도우미(`settle`·`hold`)가 불리언을 돌려주는데, 원문 검사는 그것이 어느 함수의 것인지 몰라 정당한 도우미와 실패를 삼키는 코드를 구별하지 못했다. **느슨하게 하지 않고 정확하게** 바꿨고, 허용되는 이름을 목록으로 못 박았다 |
| `tests/tiers.py` | `test_negative_assertion.py` 를 순차 계층에 등록 | 벽시계를 읽어 단언하므로 병렬에 섞이면 부하를 제품의 느림으로 보고한다 |

**실패에서 통과로 조용히 바뀐 것은 없다.** 위 넷은 모두 기대를 의도적으로 갱신한 것이고,
근거를 각 파일의 주석에 남겼다.

---

## 4. 원본 출력

## 3.3 전량 검증 (T042)

### 백엔드

| 계층 | 기준선 | 변경 후 | 차이 |
|---|---|---|---|
| 병렬 — 통과 | 3011 | **3123** | +112 |
| 병렬 — 실패 | 5 | **4** | −1 *(아래 참조)* |
| 병렬 — 소요 | 252.03s | 225.41s | −26.6s |
| 순차 — 통과 | 50 | **60** | +10 |
| 순차 — 소요 | 127.94s | 149.44s | +21.5s |
| 합계 (벽시계) | 6:21.22 | **6:16.00** | −5s |

**실패가 하나 줄었지만 021 이 고친 것이 아니다.** `test_ui_surface.py[AS-012]` 가
전량 실행에서 통과했으나, 같은 검증을 **단독으로 돌리면 5건 모두 여전히 실패한다.**

```
$ uv run pytest "tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled"
5 failed, 13 passed
```

즉 AS-012 는 **flaky** 다 — 실행 순서나 부하에 따라 결과가 갈린다. 021 이 건드리는
코드 경로가 아니며, 기준선의 다섯 건이 그대로 남아 있는 것으로 읽어야 한다.
**초록으로 바뀐 것을 개선으로 보고하지 않는다.**

> 이 flakiness 자체는 021 의 범위가 아니다. 별도로 다뤄야 할 사안으로 남긴다.

순차 계층이 21.5초 늘어난 것은 `test_negative_assertion.py` 를 그 계층에 새로
등록했기 때문이다 (벽시계를 읽어 단언하므로 병렬에 섞이면 부하를 제품의 느림으로
보고한다).

### 프런트엔드

| 항목 | 기준선 | 변경 후 |
|---|---|---|
| 통과 | 1539 | **1559** (+20) |
| 실패 | 2 | **2 (동일)** |
| 소요 | 54.22s | 55.63s |

실패 2건은 기준선과 같은 `ScreenSweep.test.ts` 의 WebSocket 403 이다. 그대로인 것이
정상이다.

---

### 4.1 백엔드 (T002)

원본 출력은 세션 임시 디렉터리에 남겼고, 위 §1.2 가 그 요약이다. 재현 명령:

```bash
cd backend && bash scripts/test-backend.sh
```
