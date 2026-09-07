# Quickstart: 실행 속도 조절과 로딩 대기 검증

**Feature**: `specs/004-run-pacing-readiness` | **Date**: 2026-09-07

이 문서는 이 기능이 실제로 성립했는지 **직접 돌려 확인하는 방법**이다. 구현 코드는 담지
않는다.

---

## 0. 전제

```bash
cd backend && uv sync
cd ../frontend && npm install
```

001·002·003 의 구현이 이미 있어야 한다. 이 라운드는 그 실행 경로를 고친다.

**`uv run pytest` 가 아니라 `uv run python -m pytest` 여야 한다.** 실행 파일로 돌리면
현재 디렉터리가 경로에 들어가지 않아 공용 픽스처 임포트가 깨진다 (003 에서 확인된 조건).

---

## 1. 고치기 전 결함이 재현되는가 (기준선)

**구현을 시작하기 전에 먼저 돌린다.** 이 실패를 보지 않고 고치면 무엇을 고쳤는지 알 수 없다.

지연 로딩 픽스처를 추가한 뒤:

```bash
cd backend && uv run python -m pytest tests/integration/test_lazy_loading.py -v
```

**기대(구현 전)**: `test_lower_candidate_appears_late` 가 **실패**한다. 실패 메시지에
"요소를 찾을 수 없습니다" 가 나오고 소요가 대기 예산 전체다.

Phase 0 실측이 이 실패를 이미 확인했다 (research R1: 5004ms 실패). 픽스처가 그 조건을
테스트로 고정한 것이다.

---

## 2. 대기 정책이 결함을 고쳤는가 (US2 · SC-001 · SC-002)

```bash
cd backend && uv run python -m pytest tests/integration/test_lazy_loading.py -v
```

**기대(구현 후)**

| 테스트 | 확인하는 것 |
|---|---|
| `test_element_appears_after_delay` | 2초 뒤 등장하는 요소로 Step 통과 (SC-001) |
| `test_lower_candidate_appears_late` | 최상위 후보가 끝내 안 맞아도 하위 후보로 통과 (SC-002) |
| `test_attached_but_invisible_waits` | DOM 에 붙었지만 안 보이는 요소를 기다린 뒤 조작 |
| `test_ambiguous_does_not_silently_pick_first` | 여러 개 매칭 시 `.first` 로 통과하지 않고 `ELEMENT_AMBIGUOUS` 로 실패 |
| `test_budget_exhausted_reports_not_ready` | 예산 초과 시 `ELEMENT_NOT_READY` (US3) |
| `test_hidden_assertion_still_passes_when_absent` | 처음부터 없는 요소에 대한 `hidden` 검증 통과 (FR-119) |

**`test_ambiguous_…` 가 기존 테스트를 깨뜨린다면** 되돌리지 않는다. 그 테스트는 잘못된
요소에 대해 통과하고 있던 것이다 (research R2, plan 위험표). 대상 정의를 고친다.

---

## 3. 정상 경로가 느려지지 않았는가 (SC-003)

```bash
cd backend && uv run python -m pytest tests/integration/test_performance.py -v -k pacing
```

**기대**: 요소가 즉시 존재하는 Step 의 소요가 이번 변경 전 대비 **100ms 미만** 증가.

근거: 폴링 루프는 1라운드에서 반환하므로 진입하지 않는다. 보임 확인 비용은 실측 4.7ms
(research R7).

빠르게 눈으로 보려면:

```bash
cd backend && uv run python -m pytest tests/integration/test_performance.py -v --durations=10
```

---

## 4. 속도 조절이 동작하는가 (US1)

### 4-1. 간격이 실제로 생기는가 (SC-004)

```bash
cd backend && uv run python -m pytest tests/unit/test_run_pacing.py -v
```

**기대**: 대응표가 `fast=0 / normal=500 / slow=1500 / step=auto_pause` 를 돌려주고,
`slow` 가 1000ms 이상이다. 마지막 Step 뒤에는 간격이 적용되지 않는다.

### 4-2. 속도가 판정을 바꾸지 않는가 (SC-005)

```bash
cd backend && uv run python -m pytest tests/e2e/test_us2_replay_and_diagnose.py -v -k pacing
```

**기대**: 같은 테스트를 네 속도로 실행해 통과/실패 판정과 실패 Step 위치가 모두 같다.

### 4-3. 간격 도중 일시정지·중지가 즉시 먹는가 (SC-007 · FR-106)

```bash
cd backend && uv run python -m pytest tests/integration/test_pacing_interrupt.py -v
```

**기대**: `slow`(1500ms) 간격 도중 일시정지 요청 후 **1초 안에** `state == "paused"`.
중지도 마찬가지다.

설계상 지연은 0에 가깝다 — 이벤트가 set 되는 즉시 `asyncio.wait_for` 가 반환한다
(research R6). 1초는 여유 있는 상한이다.

---

## 5. 화면에서 직접 확인 (US1 · US3)

서버와 화면을 띄운다.

```bash
cd backend  && uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320
cd frontend && npm run dev            # http://127.0.0.1:4310
```

샘플 앱의 지연 로딩 화면:

```bash
cd fixtures/sample-app && python3 serve.py
```

**확인 절차**

1. 테스트를 하나 열고 **속도를 `느림`** 으로 바꿔 실행한다.
   → Step 사이에 눈에 보이는 간격이 생기고, 간격 동안 방금 끝난 Step 과 결과가 보인다
   (FR-107).
2. 실행 중에 **속도를 `빠름` 으로 바꾼다.**
   → 진행 중인 Step 이 끊기지 않고, 다음 Step 부터 간격이 사라진다 (FR-103).
3. **`한 스텝씩`** 으로 실행한다.
   → 매 Step 마다 멈추고, 화면 문구가 "한 스텝씩 — 다음 Step 을 기다립니다" 로 나온다
   (일반 일시정지의 "일시정지됨" 과 구별). 이 상태에서 Step 편집이 된다 (FR-108).
4. 브라우저를 새로고침해 **재연결**한다.
   → 속도 표시가 그대로다 (`SessionView.pacing`).
5. 세션을 닫고 **새로 실행**한다.
   → 마지막에 고른 속도가 기본으로 제시된다 (FR-109).
6. 대기 예산을 1000ms 로 줄이고 지연 로딩 화면의 Step 을 실행해 **실패**시킨다.
   → 결과 화면에 기다린 시간과 후보별 시도 내역이 나오고, "속도를 낮춰 확인하거나 대기
   시간을 늘리라" 는 다음 행동이 제시된다 (FR-121·FR-122, SC-006).

---

## 6. 헌법 게이트

### 6-1. 임포트 계약 (원칙 II · IV)

```bash
cd backend && uv run lint-imports
```

**기대**: 세 계약 모두 통과.

- `execution-no-llm` — 이번 변경이 전부 이 계약 안쪽 모듈에서 일어난다
- `domain-is-pure` — `domain/run_pacing.py` 가 아무것도 임포트하지 않는다
- `locator-strategy-is-pure` — `POLL_INTERVAL_MS` 를 더해도 순수성이 유지된다

### 6-2. 스키마 파이프라인 (Cross-language schema duty)

```bash
cd backend  && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
git diff --stat frontend/src/types/generated/
```

**기대**: 신규 오류 코드와 `element_wait_ms` 가 생성 타입에 반영된다. 생성 파일을 손으로
고치지 않는다.

```bash
cd backend && uv run python -m pytest tests/contract/test_schema_drift.py -v
```

### 6-3. 왕복 무결성 (품질 게이트 2)

```bash
cd backend && uv run python -m pytest tests/integration/test_roundtrip.py tests/contract/test_dsl_roundtrip.py -v
```

**기대**: 예산 기본값 상향(5000 → 10000)이 생성 Playwright 코드의 `timeout:` 에 반영되고,
기록 → 저장 → 재실행 → 내보내기 → 실행이 같은 결과를 낸다.

**알려진 한계**: 내보낸 테스트는 다후보 폴링을 하지 않는다. 제품 안에서 하위 후보로 통과한
Step 은 내보낸 코드에서 최상위 후보로만 시도된다 (plan Complexity Tracking).

### 6-4. 전체 회귀

```bash
cd backend && uv run ruff check src/ tests/
cd backend && uv run python -m pytest
```

**기대**: 기존 921건이 줄지 않는다. 테스트를 지우거나 건너뛰어 통과시키지 않는다
(품질 게이트 4).

---

## 7. 성공 기준 대조표

| 기준 | 확인 방법 | 절 |
|---|---|---|
| SC-001 지연 등장 요소 100% 통과 | `test_lazy_loading.py::test_element_appears_after_delay` | §2 |
| SC-002 하위 후보 지연 등장도 통과 | `test_lazy_loading.py::test_lower_candidate_appears_late` | §2 |
| SC-003 정상 경로 100ms 미만 증가 | `test_performance.py -k pacing` | §3 |
| SC-004 `느림` 에 1초 이상 간격 | `test_run_pacing.py` | §4-1 |
| SC-005 네 속도의 판정 동일 | `test_us2_replay_and_diagnose.py -k pacing` | §4-2 |
| SC-006 실패 사유에서 대기 시간·다음 행동 확인 | 화면 절차 6 | §5 |
| SC-007 간격 중 일시정지·중지 1초 이내 | `test_pacing_interrupt.py` | §4-3 |
| SC-008 내보내기 판정 동일 | `test_roundtrip.py` | §6-3 |
