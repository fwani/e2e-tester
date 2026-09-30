# Baseline — 026 시작 시점 (2026-09-30)

**목적**: 기존 실패를 새 실패와 섞지 않는다. 끝에서 이 표와 비교한다.

## 전량 검증 결과

| 검증 | 명령 | 결과 |
|---|---|---|
| 백엔드 병렬 계층 | `uv run pytest -m "not timing"` | **4 failed** · 3390 passed · 1 skipped |
| 백엔드 순차 계층 | `uv run pytest -m timing -n 0` | 60 passed |
| ruff | `uv run ruff check src/ tests/` | **2 errors** (E501) |
| lint-imports | `uv run lint-imports` | 4 kept · **0 broken** |
| 프론트 | `npx vitest run` | **2 failed** · 1646 passed (141 파일 중 1 실패) |
| 타입 | `npx tsc --noEmit` | 통과 |

### 기존 실패 — 이것은 026 의 것이 아니다

| # | 실패 | 자리 |
|---|---|---|
| 1~4 | `test_abnormal_screen_operation_is_handled[AS-009]` · `[AS-025]` · `[AS-037]` · `[AS-046]` | `backend/tests/abnormal/test_ui_surface.py` |
| 5~6 | ruff `E501 Line too long` 2건 | `backend/tests/integration/test_negative_assertion.py:126` 외 |
| 7~8 | `ScreenSweep.test.ts` 2건 — WebSocket 403 콘솔 오류 | `frontend/tests/ScreenSweep.test.ts:148` |

**끝에서 이 8건만 실패해야 한다.** 늘면 026 이 깬 것이다.

### 원칙 II 경계는 지금 깨끗하다

`lint-imports` 의 `execution must not reach the LLM boundary (Constitution Principle II)`
가 **KEPT** 다. 026 은 도착점 실행과 되맞춤 실행을 건드리므로 이 줄이 끝에서도 KEPT 여야
한다.

---

## 016 이 그대로 도는지 볼 목록 (T002 · FR-030)

`rerecord` 를 언급하는 파일 전부. **끝에서 이 검사들이 하나도 깨지지 않아야 한다.**

### 백엔드 검사 (10)

```
backend/tests/unit/test_rerecord_transaction.py
backend/tests/us_rerecord/support.py
backend/tests/us_rerecord/test_ai_edit_keeps_position.py
backend/tests/us_rerecord/test_arrival_point.py
backend/tests/us_rerecord/test_blocked_in_rerecord.py
backend/tests/us_rerecord/test_chat_boundary.py
backend/tests/us_rerecord/test_chat_turn.py
backend/tests/us_rerecord/test_commit_and_discard.py
backend/tests/us_rerecord/test_save_after_commit.py
backend/tests/us_rerecord/test_sensitive_in_rerecord.py
```

곁들여 보는 것: `test_principle_ii_timeline.py` · `unit/test_attempt_limits.py` ·
`contract/test_sharing_readiness.py` · `e2e/test_us9_draft_recording.py` ·
`integration/test_draft_to_test.py`

### 프론트 검사 (6)

```
frontend/tests/RerecordStart.test.tsx
frontend/tests/RerecordTransaction.test.tsx
frontend/tests/RerecordRegression.test.tsx
frontend/tests/RerecordBandPlacement.test.tsx
frontend/tests/CapabilityCoverage.test.ts
frontend/tests/AiErrorDismiss.test.tsx
```

`CapabilityCoverage.test.ts` 가 특히 중요하다 — **조작표에 빈칸이 없는지** 보는 검사이며,
026 이 조작 셋을 더하므로 셀을 채우지 않으면 여기서 걸린다.

### 026 이 건드리는 프론트 파일 (기존)

```
frontend/src/api/client.ts · api/ws.ts · app/actions.tsx
frontend/src/lib/actions.ts · lib/capabilities.ts · lib/wording.ts
frontend/src/components/workbench/ActionPalette.tsx · RerecordBar.tsx · StepList.tsx · Workbench.tsx
frontend/src/pages/EditView.tsx · SessionScreen.tsx
```

`RerecordBar.tsx` 가 016 의 확정·버리기 자리다 — 026 의 확정·버리기가 같은 모양이어야
하므로 참고 대상이며, **고치지 않는다.**
