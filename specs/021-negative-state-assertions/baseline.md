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

### 3.1 소요 시간 비교

### 3.2 결과가 바뀐 검증 — **무엇이 왜 바뀌었는지**

> 실패에서 통과로 바뀐 것이 있으면 여기에 적는다. 방향이 개선이더라도
> **조용히 초록으로 넘어가면 안 된다.**

---

## 4. 원본 출력

### 4.1 백엔드 (T002)

원본 출력은 세션 임시 디렉터리에 남겼고, 위 §1.2 가 그 요약이다. 재현 명령:

```bash
cd backend && bash scripts/test-backend.sh
```
