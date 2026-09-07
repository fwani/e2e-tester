# Data Model: UX 워크스루 결함 수정 (005 라운드 변경분)

**Feature**: `specs/005-ux-walkthrough-repair` | **Date**: 2026-09-07

001 의 도메인 모델을 **확장한다.** 기존 필드의 뜻을 바꾸지 않으며, 값 두 개와 필드 넷이
늘어난다. 이미 저장된 결과 파일은 그대로 읽힌다.

권위 정의는 `backend/src/itb/domain/` 이고 프론트 타입은 생성물이다
(헌법 Cross-language schema duty). 변경 순서는 **백엔드 enum·모델 → 스키마 내보내기 →
프론트 타입 생성**이며, 어기면 `test_schema_drift.py` 가 실패한다.

---

## 1. `Outcome` — 실행 결말 (변경)

`backend/src/itb/domain/run_result.py`

```
pass | fail | stopped | partial      ← stopped, partial 추가
```

| 값 | 판정 조건 | 사용자 표시 | 실패 집계 |
|---|---|---|---|
| `pass` | 실행 대상 Step 전부 통과 | 통과 | 아니오 |
| `fail` | 실패한 Step 이 있다 · 세션 유실로 끝났다 | 실패 | 예 |
| `stopped` | 사용자가 중지를 요청해 끝났다 | 중지 | **아니오** (FR-131) |
| `partial` | 실패 Step 을 건너뛰고 나머지를 마쳤다 | 부분 성공 | 아니오 |

**판정 우선순위** (위에서부터 먼저 걸리는 것이 이긴다):

1. 사용자 중지 요청이 있었다 → `stopped`
2. 실패 Step 을 명시적으로 건너뛰고 계속했다 → `partial`
3. 실패 Step 이 남아 있다 → `fail`
4. 그 외 → `pass`

세션 유실(`session_lost=True`)은 `fail` 이다 — 사고이며 사용자가 요청한 중단이 아니다.
**의도적 중지가 유실로 감지되던 결함**(U-03)은 이 판정이 아니라 감지기 가드에서 고친다
(§6).

**호환**: 읽는 쪽은 알 수 없는 값을 만나면 `fail` 로 취급한다. 값이 더 늘 때 화면이
조용히 통과로 표시하지 않게 하는 보수적 기본값이다.

---

## 2. `RunResult` — 실행 범위 추가 (변경)

```
+ start_index: int = 0            # 이 실행이 시작한 Step (0 = 처음부터)
+ scope: RunScope = "full"        # full | partial
+ attempted_count: int            # 실제 실행 대상 Step 수 (= total_count - 건너뜀)
+ stopped_step_index: int | None  # 사용자가 중지한 시점의 Step (stopped 일 때만)
```

`total_count`(전체 Step 수)와 `passed_count`(통과 수)는 **뜻이 바뀌지 않는다.**
새 필드를 더한다.

**요약 문장은 `attempted_count` 로 만든다.** 지금은 `passed / total` 이라서 5개를 건너뛴
부분 실행이 `0 / 7` 로 보인다(U-02). 부분 실행은 `0 / 2 (5개 건너뜀)` 이어야 한다.

`scope` 는 `start_index > 0` 에서 파생되지만 **저장한다.** 읽는 쪽이 매번 해석하면 같은
규칙이 여러 곳에 복제된다.

### `RunScope` (신규)

```
full | partial
```

---

## 3. `StepOutcome` — 변경 없음

```
pass | fail | skipped | not_run     ← 이미 네 값이다
```

**이 enum 은 손대지 않는다.** 건너뜀과 미실행은 이미 구분되어 저장된다
(`ReplayEngine.skip_before()`). U-02·U-21 은 **화면이 이 구분을 읽지 않는 것**이므로
표시 쪽에서 고친다.

| 값 | 화면 표시 | 기호 |
|---|---|---|
| `pass` | 통과 | ✓ |
| `fail` | 실패 | ✕ |
| `skipped` | **건너뜀** | 회색 칩 + 텍스트 라벨 |
| `not_run` | **미실행** | 점선 + 텍스트 라벨 |

구분은 색에만 의존하지 않는다 — 텍스트 라벨을 병기한다(FR-151, 접근성).

---

## 4. `SessionView` — 화면 복원에 필요한 것 추가 (변경)

`backend/src/itb/api/routes/sessions.py`

```
+ step_results: list[StepProgress] = []   # 이 세션에서 지금까지 확정된 Step 결과
+ pause_settled: bool = True              # 일시정지가 실제로 걸렸는가
+ run_scope: RunScope = "full"            # 현재 실행의 범위
+ run_start_index: int = 0                # 현재 실행의 시작 Step
+ saved_at: datetime | None = None        # 마지막 저장 시각 (없으면 미저장)
```

### `StepProgress` (신규)

```
step_id: str
outcome: StepOutcome
duration_ms: int
```

`StepResult` 전체가 아니라 **화면 복원에 필요한 최소**다. 진단 정보(로케이터 시도·오류
본문)는 결과 조회로 가져온다 — 세션 뷰는 폴링 대상이므로 가볍게 유지한다.

**왜 필요한가**: 지금 Step별 결과는 WebSocket 이벤트로만 채워지는 화면 로컬 상태다.
화면을 다시 그리면 사라진다(U-18). WebSocket 계약은 "끊기면 세션 조회로 전체 상태를 다시
받는다"인데 그 전체 상태에 Step 결과가 없었다 — 계약의 구멍을 메운다.

**`pause_settled`**: `false` 면 일시정지 요청이 갔지만 아직 Step 경계에 닿지 않은
**전이 중**이다. 값은 러너의 `at_boundary` 에서 온다. `SessionState` 에 새 상태를 넣지
않는 이유는 research R7 에 있다.

**`saved_at`**: 저장 성공을 화면이 스스로 알 수 있게 한다(FR-154). 지금은 저장 응답
말고는 저장 여부를 알 방법이 없어, 화면을 다시 그리면 다시 미저장처럼 보인다.

---

## 5. 결과 보관 — 파일 두 개 (변경)

`.runs/<테스트ID>/`

| 파일 | 내용 | 갱신 시점 |
|---|---|---|
| `result.json` | 최근 실행 (전체든 부분이든) | 모든 실행 종료 시 |
| `result-full.json` | 최근 **전체** 실행 | `scope == full` 인 실행 종료 시 |

부분 실행이 전체 실행 결과를 덮지 않게 한다(FR-152). 결과 화면은 "이 실행"과 "최근 전체
실행"을 함께 보여줄 수 있다.

**이력은 만들지 않는다.** 요구된 것은 "부분 실행이 전체 실행 결과를 지우지 않는 것"
하나이며, 이력에는 목록·정리·용량 정책이 따라온다(범위 밖).

`result-full.json` 이 없는 기존 프로젝트는 정상이다 — 없으면 보조 표시를 생략한다.

---

## 6. 세션 생존과 유실 감지 (변경 — 값이 아니라 판정)

### 활성 세션 판정

`SessionManager.active_session_for_test()` 는 **살아 있는 세션만** 돌려준다.
판정 근거는 이미 있는 `ACTIVE_STATES` 를 쓴다(새 목록을 만들지 않는다). 종료 상태
(`completed·failed·stopped·review·lost`)에 도달한 세션은 `_by_test` 등록에서 떼어낸다.

### 테스트별 생성 예약

세션 생성은 테스트별 락 안에서 **확인과 예약을 함께** 한다. 예약은 브라우저 기동 전에
자리를 잡고, 생성 실패 시 되돌린다. 락은 짧게 쥐고 놓으므로 정상 요청이 직렬화되지
않는다(FR-128).

### 유실 감지 가드

`session_loss.py` 의 "정상 종료면 유실이 아니다" 가드에 **`REVIEW` 를 더한다.**
현재 `COMPLETED / FAILED / STOPPED / LOST` 만 보므로, `STOP → REVIEW` 로 남는 의도적
중지가 매번 유실로 감지되고 결과가 `fail` 로 확정된다(U-03).

가드에 값을 더하는 것보다 **의도적 중지 경로에서 감지기를 먼저 떼는 것**이 더 안전하다.
둘 다 한다 — 가드는 그물이고, 감지기 분리는 원인 제거다.

---

## 7. 엔티티 관계

```
Test ──1:N── Step
  │
  └──1:1── RunResult (최근)          .runs/<id>/result.json
  └──1:1── RunResult (최근 전체)     .runs/<id>/result-full.json
              │
              ├──1:N── StepResult ── outcome: pass|fail|skipped|not_run
              └──1:1── Artifacts

BrowserSession ──1:1── SessionView (조회 형태)
  │                       └──1:N── StepProgress   ← 신규
  ├── state: SessionState (변경 없음)
  └── test_id ──0:1── 활성 세션 등록 (살아 있는 세션만)   ← 판정 변경
```

---

## 8. 변경 요약과 파급

| 변경 | 파일 | 스키마 재생성 | 기존 데이터 |
|---|---|---|---|
| `Outcome` 값 2개 추가 | `domain/run_result.py` | **필요** | 그대로 읽힘 |
| `RunScope` 신규 | `domain/run_result.py` | **필요** | 기본값 `full` |
| `RunResult` 필드 4개 추가 | `domain/run_result.py` | **필요** | 기본값으로 채워짐 |
| `StepProgress` 신규 · `SessionView` 필드 5개 | `api/routes/sessions.py` | 필요 (세션 뷰 계약) | 해당 없음 (조회 형태) |
| 결말 판정 우선순위 | `execution/runner.py` | 아니오 | 해당 없음 |
| 활성 세션 판정 · 생성 예약 | `execution/session.py`, `api/routes/sessions.py` | 아니오 | 해당 없음 |
| 유실 감지 가드 | `execution/session_loss.py` | 아니오 | 해당 없음 |
| 결과 보관 파일 하나 추가 | `execution/runner.py` (저장), 조회 경로 | 아니오 | 없으면 생략 |

**스키마 재생성이 필요한 변경은 한 작업으로 묶는다.** 부분적으로 재생성하면
`test_schema_drift.py` 가 중간 상태에서 실패해 원인을 가린다.
