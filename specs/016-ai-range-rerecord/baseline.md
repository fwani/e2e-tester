# Baseline — 016 구현 시작 시점의 사실

**Date**: 2026-09-11 | **Branch**: `016-ai-range-rerecord` | 작업: T001 · T002

---

## T001 — 기준선 검증

| 검사 | 결과 |
|---|---|
| `uv run lint-imports` | **통과** — Contracts: 3 kept, 0 broken |
| `uv run ruff check src/ tests/` | **통과** — All checks passed |
| `backend/scripts/test-backend.sh` | (아래 §T001-a 참조) |
| `uv run python -m itb.schema.export --check` | 통과 |
| `npx tsc --noEmit` | **통과** |
| `npm test -- --run` | **통과** — 104 파일 · 1295 테스트 |

### T001-a — `uv run pytest` 를 그대로 쓰면 안 된다

README 와 tasks.md 초안이 적은 `uv run pytest` 는 **48개 오류**를 낸다. 이것은 회귀가
아니라 **테스트 계층 분리** 때문이다.

```
E  Failed: 시간을 재는 검증입니다 — 프로세스 8개로는 재는 값이 그 순간의 부하가 됩니다.
   `-n 0` 을 붙이거나 `scripts/test-backend.sh` 로 돌리세요.
```

`backend/tests/tiers.py` 의 `TIMING_MODULES` 에 속한 모듈은 경과 시간을 단언하므로
병렬 실행에서 의미가 없고, 그래서 **스스로 거부한다.** 정규 명령은 이것이다:

```bash
cd backend && bash scripts/test-backend.sh      # 병렬 계층 + 순차(timing) 계층
```

**이 기능의 모든 검증은 이 스크립트를 쓴다.** tasks.md 의 T069 와 각 Phase 종료 검증도
마찬가지다.

---

## T002 — 도구 표면의 현재 사실

`backend/src/itb/authoring/tools.py` 의 `TOOL_NAMES` 12개를
`contracts/agent-tools.md` §1 의 네 분류에 대조했다. **빠짐도 겹침도 없다.**

| 분류 | 도구 | 수 | 코드의 현재 상태 |
|---|---|---|---|
| `READ_ONLY_TOOLS` | `list_tabs` · `observe_page` | 2 | **튜플이 없다.** 이번에 만든다 |
| `STEP_PRODUCING_TOOLS` | `click` · `fill` · `select` · `navigate` · `hover` · `drag` · `upload` · `assert_condition` · `close_tab` | 9 | **이미 있다.** 건드리지 않는다 |
| `STEP_EDITING_TOOLS` | — | 0 | 이번에 만든다 (4종 추가 예정) |
| `CONTROL_TOOLS` | `report_blocked` | 1 | **튜플이 없다.** 이번에 만든다 |
| **합계** | | **12** | `TOOL_NAMES` 와 일치 ✔ |

### 확인된 사실 셋

1. **`TOOL_NAMES` 의 「이 목록이 계약이다 — 늘리면 Step 종류와의 1:1 이 깨진다」는 주석은
   정확히는 `STEP_PRODUCING_TOOLS` 에 대한 것이다.** 실제로 `observe_page`·`list_tabs`·
   `report_blocked` 셋이 Step 을 만들지 않으면서 `TOOL_NAMES` 에 있다. 계약을 넓히는
   것이 아니라 **정확히 적는 것**이라는 research R3 의 판단이 코드로 확인된다.

2. **`TOOL_SCHEMAS` 의 키가 `TOOL_NAMES` 와 같다.** `QUALIFIED_TOOL_NAMES` 가
   `TOOL_SCHEMAS` 에서 파생되므로, 새 도구를 `TOOL_SCHEMAS` 에 등록하면 개발용 드라이버
   (`claude_code_driver`)에 **자동으로 따라 들어온다.** 손으로 더할 것이 없다.

3. **`itb.authoring.tools` 는 이미 `itb.execution` 을 임포트한다** (`BrowserSession`·
   `StepExecutor`). research R1·R2 의 전제가 코드로 확인된다 — `authoring → execution`
   방향은 `.importlinter` 계약이 금지하지 않으며 이미 쓰이고 있다.

---

## 결론

기준선은 **초록**이며, 실패로 보였던 48건은 명령을 잘못 쓴 것이다. R1·R2·R3 의 전제가
전부 코드로 확인되었으므로 계획을 수정할 이유가 없다.
