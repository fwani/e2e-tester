# Implementation Plan: 작성 화면의 저장·선택·삭제·기록을 실사용에 맞춘다

**Branch**: `011-authoring-ux-repair` | **Date**: 2026-09-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-authoring-ux-repair/spec.md`

## Summary

실사용 보고 7건을 고친다. 다섯은 **이미 있는 것의 자리·물음·표시**를 바꾸는 일이고, 둘은
**없는 기능**을 더하는 일이다.

**접근**: 이 저장소는 007~010 을 거치며 자리 문법과 조작 표를 정본으로 모아 왔다. 011 은
그 정본을 **고치고 지나간다** — 우회하지 않는다. 그래서 작업의 상당 부분이 "정본을 세는 기존
검사를 함께 고치는 일" 이며, 그것이 이 기능의 형태다.

| 보고 | 무엇을 한다 | 새로 만드는 것 |
|---|---|---|
| 1 · 저장 자리 | `save`·`edits.revert`·`test.rename` 의 집을 팔레트 → **국면 띠** | 없음 (자리 이동) |
| 2 · 이름 재요구 | 판정식을 `saved_at` → **`test_id`** 로. 확인 대화상자의 이름칸 조건부 | 없음 (판정 수정) |
| 3 · 지시문 대등성 | `editing` 권한표 두 셀을 `ON` 으로. 실행 앞에 기존 `openBrowser()` 를 붙인다 | 없음 (부품이 다 있다) |
| 4 · 복수 삭제 | 행에 체크 칸. 세션에 배치 삭제 라우트 1개. 편집은 기존 `edits` 로 | 라우트 1개 · 조작 4개 |
| 5 · Step 별 스크린샷 | Step 종료 시 촬영. `StepResult` 에 선택 필드 2개. 서빙 라우트 1개 | 라우트 1개 · 필드 2개 |
| 6 · 상세 자리 | 겹침을 오른쪽 → **왼쪽**. 폭·표는 그대로 | 없음 (자리 이동) |
| 7 · 선택 표시 | 한 클래스 자리를 다투던 셋을 **네 자리로 분리** | 표시 축 2개 |

**설계를 좌우한 두 발견** (research R5·R6):

| 확인한 것 | 결과 | 이것이 없었으면 |
|---|---|---|
| 저장된 테스트 편집 API 가 이미 **편집 연산 목록**을 받는다 | `delete` 를 여러 개 실으면 그대로 원자적 복수 삭제 | 편집 경로에도 배치 라우트를 만들어 원자성 규칙이 두 벌이 됐다 |
| `.runs/<테스트ID>/` 가 이미 「테스트당 하나, 최근 1건만」 | clarify 결정 3(최근 1회분 보관)이 **실행 시작 시 `steps/` 비우기** 한 줄로 충족 | 보관 기간·장수 상한 장치를 새로 만들어야 했다 |

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript + React (frontend)

**Primary Dependencies**: FastAPI, Playwright for Python, React. **새 의존성 없음.**

**Storage**: 파일. 변경은 `.runs/<ID>/steps/*.png` 추가와 `StepResult` 의 선택 필드 2개뿐이다
([data-model.md](data-model.md) §0). **Step DSL 은 바뀌지 않는다.**

**Testing**: pytest (backend, 계층별 tier), vitest + Testing Library (frontend)

**Target Platform**: 로컬 실행. 010 이후 화면 없는 기계에서도 전체 흐름이 돈다 — 011 은 그
전제를 유지한다 (Step 촬영은 헤드리스에서도 된다).

**Project Type**: web application (backend + frontend)

**Performance Goals**:
- Step 별 촬영이 **시간 초과 판정을 바꾸지 않는다** (FR-395 · SC-611). `duration_ms` 확정 후에
  찍는다.
- Step 20~50개 목록에서 체크 칸이 늘어도 렌더가 느려지지 않는다 — `StepListPerformance` 검사가
  기준선을 갖고 있다.

**Constraints**:
- 새 영역·새 국면을 만들지 않는다. 기존 자리 문법(헤더 60 / 국면 띠 48 / ③좌 대상앱·작업영역 /
  Step 패널 460 / 겹침 상세 640)을 그대로 쓴다.
- 조작은 `lib/actions.ts` + `lib/capabilities.ts` `PHASE_TABLE` 이 정본이다. 새 조작 4개는
  열 국면 전부에 값을 갖는다 (`Record<Phase, …>` 가 요구한다).
- 기존 저장 정의·결과 파일 호환을 깨지 않는다 (SC-613).
- 민감 값이 담긴 스크린샷은 디스크에 남지 않는다 (FR-392 · SC-612 · 헌법 §보안).

**Scale/Scope**: 요구사항 50건(FR-360~FR-398 + 하위), 성공 기준 17건, 사용자 이야기 5개.
백엔드 신규 라우트 2개 · 수정 모듈 4~5개, 프론트 신규 표시 축 2개 · 수정 파일 8~10개,
개정되는 기존 검증 10건 (research R8).

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 후 재확인 — 아래 「Phase 1 후 재확인」 참조.*

### I. Unified Step Model (NON-NEGOTIABLE) — 통과

**Step DSL 에 아무것도 더하지 않는다.**

- 근거 1 (저장 형식): [data-model.md](data-model.md) §0 의 Step DSL 줄이 「없음」이다. 변경은
  실행 **결과**(`StepResult`)와 산출물 디렉터리에만 있다. 결과는 정의가 아니다.
- 근거 2 (표시): 지목·삭제 대상은 **화면 상태**이며 서버에 보내지도, 저장되지도 않는다
  (data-model §6 — 「서버에 없다. 저장되지 않는 일시 상태다」).
- 근거 3 (지시문 경로): 지시문으로 더한 Step 은 기존 작성 경로가 만드는 그 Step 이다. 011 은
  그 앞에 「브라우저 열기」를 붙일 뿐 Step 을 만드는 새 경로를 만들지 않는다 (research R7).
- 근거 4 (복수 삭제): 삭제는 목록 연산이다. Step 의 형태를 건드리지 않는다.

### II. Deterministic Replay (NON-NEGOTIABLE) — 통과

**재생 경로에 LLM 을 들이지 않는다.**

- 지시문 수행은 **작성** 경로다. 011 이 바꾸는 것은 그 조작의 활성 조건(권한표 두 셀)이며,
  수행 자체는 기존 경로 그대로다. 「저장된 테스트를 실행」에서 도달할 수 있는 코드가 늘지 않는다.
- Step 별 스크린샷은 촬영이며 판단이 아니다. 화면을 LLM 에 보내 결말을 정하는 경로를 만들지
  않는다 — 그것은 원칙 II 가 명시적으로 막는 것이고 PRD §12 가 미래로 미룬 것이다.
- 촬영이 실패해도 결말이 바뀌지 않는다 (FR-398). 산출물은 결말의 입력이 아니다.

### III. Stateful Interactive Runner — 통과

- 편집 국면에서 브라우저를 자동으로 여는 것은 세션을 **여는** 일이며, 열린 세션을 끊는 변경은
  없다.
- 지시문 수행이 막히면 세션이 열린 채 유지된다 (FR-378) — 기존 규칙 그대로다.
- 복수 삭제는 일시정지 상태에서 일어나고, 삭제 후에도 세션은 유지된다.

### IV. Locator Resilience — 통과 (해당 없음)

Locator 후보 수집·해석 경로를 건드리지 않는다. Step 상세가 `attempts`·`candidates` 를 보여주는
방식도 그대로다.

### V. Asset Portability — 통과

- Step DSL 이 바뀌지 않으므로 내보내기 가능성이 영향받지 않는다.
- 스크린샷은 실행 산출물이며 내보낸 Playwright 프로젝트가 알 필요가 없다. `.runs/` 는 이미
  `.gitignore` 대상이다.
- **Export 자체는 이 기능 범위 밖이다.** 001 에서 등록된 릴리스 게이트 항목이며 011 이
  그것을 새로 미루지 않는다 — 이 기능은 그 항목에 손대지 않는다.

### 품질 게이트

| 게이트 | 이 기능에서 |
|---|---|
| 1. 원칙 준수 | 위 5개 항목. 재생 경로 무변경 근거는 II 에 있다 |
| 2. 왕복 정합성 | Step DSL 무변경이므로 record → store → replay 왕복이 바뀌지 않는다. 다만 **결과 파일 왕복**(구버전 `result.json` 읽기)은 새 검증이 필요하다 → tasks |
| 3. 테스트 | 사용자 이야기 5개 각각에 검증. 신규 라우트 2개에 계약 검증. 기존 검증 10건 개정 (research R8) |
| 4. 비활성 테스트 금지 | 개정되는 10건은 **기대값을 새 계약에 맞춰 고친다.** 지우거나 건너뛰지 않는다 |
| 5. 성공 지표 | 테스트 작성·재생 흐름에 닿는다. 저장 실패로 작업을 잃는 경로가 줄어드는 것이 기대 효과다 (PRD §18 테스트 작성 시간) |

**위반 없음. Complexity Tracking 은 비어 있다.**

### Phase 1 후 재확인

설계 산출물([data-model.md](data-model.md) · [contracts/](contracts/))을 작성한 뒤 다시 확인했다.

- I: `data-model.md` §0 의 「Step DSL — 없음」이 유지됐다. §3 의 화면 모델 추가는 전부 화면 상태다.
- II: `contracts/api-contract.md` 의 신규 라우트 둘 중 어느 것도 LLM 을 부르지 않는다 —
  하나는 목록 삭제, 하나는 PNG 서빙이다.
- V: `contracts/api-contract.md` §5 의 디스크 구조가 `.runs/` 안에만 더한다.
- **새로 드러난 것 하나**: Step 상세가 대상 앱 위를 덮으므로 010 의 미러 조작으로 입력이 새는
  경로가 생긴다. 원칙 위반은 아니지만 실제 결함이 될 수 있어 `UC-011-9`(FR-373b)로 계약에
  고정했다.

## Project Structure

### Documentation (this feature)

```text
specs/011-authoring-ux-repair/
├── plan.md                      # 이 파일
├── spec.md
├── research.md                  # Phase 0 — R1~R9
├── data-model.md                # Phase 1 — 저장 형식·모델·상태 전이
├── quickstart.md                # Phase 1 — 검증 실행 안내
├── contracts/
│   ├── ui-contract.md           # 007 계약에서 바뀌는 줄만 (UC-011-1~25)
│   └── api-contract.md          # 신규 라우트 2개 · 결과 모델 확장
├── checklists/
│   └── requirements.md
└── tasks.md                     # Phase 2 (/speckit-tasks 가 만든다)
```

### Source Code (repository root)

```text
backend/
├── schema/                              # 변경 없음 — Step DSL 은 바뀌지 않는다
├── src/itb/
│   ├── api/routes/
│   │   ├── sessions.py                  # 저장 판정에 test_id 를 내려보내는 부분 확인
│   │   ├── steps.py                      ← POST /steps:delete 추가
│   │   └── tests.py                      ← GET /result/steps/{index}/screenshot 추가
│   │                                       경계 검사 함수 추출 (get_artifact 와 공유)
│   ├── domain/
│   │   └── run_result.py                 ← StepResult.screenshot · screenshot_note
│   ├── execution/
│   │   ├── artifacts.py                  ← write_step_screenshot · clear_step_screenshots
│   │   ├── step_executor.py              ← Step 종료 후 촬영 (duration_ms 확정 뒤)
│   │   ├── runner.py                     ← 실행 시작 시 steps/ 비우기 · 결과 조립
│   │   └── step_edits.py                # 변경 없음 — delete_step 을 그대로 쓴다
│   └── storage/
│       └── repository.py                # 변경 없음 — run_dir 규율을 그대로 쓴다
└── tests/
    ├── contract/test_schema_drift.py     ← 기대값 갱신
    ├── contract/                         ← 신규 라우트 2개 계약 검증
    ├── integration/                      ← 복수 삭제 원자성 · Step 촬영 · 구버전 결과 읽기
    └── unit/                             ← artifacts 촬영·비우기 단위 검증

frontend/
├── src/
│   ├── api/client.ts                     ← 배치 삭제 · Step 스크린샷 URL
│   ├── lib/
│   │   ├── actions.ts                    ← 조작 4개 추가
│   │   ├── capabilities.ts               ← 새 조작 열 국면 채움 · editing 두 셀 ON
│   │   └── wording.ts                    ← 확인 문구 · 없음 사유 · 라벨
│   ├── components/workbench/
│   │   ├── PhaseBar.tsx                  ← 저장·되돌리기·이름 인라인 편집
│   │   ├── ActionPalette.tsx             ← 저장 블록·이름 칸 제거, 복수 삭제 조작 추가
│   │   ├── StepList.tsx                  ← 체크 칸(칸 0) · 네 상태 분리 · 머리의 전부 고르기
│   │   ├── StepDetail.tsx                ← 결과 국면의 스크린샷 자리
│   │   ├── Workbench.tsx                 ← 상세 겹침 자리 우 → 좌 · 입력 차단
│   │   └── model.ts                      ← deleteSelection · isDeleteTarget · screenshot*
│   └── pages/
│       ├── SessionScreen.tsx             ← 저장 판정 test_id · 확인 대화상자 이름칸 조건부
│       ├── EditView.tsx                  ← 녹화·지시문 앞에 openBrowser · 복수 삭제 edits
│       └── ResultView.tsx                ← Step 별 스크린샷 전달
└── tests/                                ← 개정 10건 + 신규 (research R8)
```

**Structure Decision**: 기존 web application 구조(`backend/` + `frontend/`) 그대로다. 새
최상위 디렉터리를 만들지 않는다. 백엔드는 라우트 2개 추가 + 모듈 4개 수정, 프론트엔드는 정본
3개(`actions`·`capabilities`·`wording`) 수정 + 표시 컴포넌트 6개 수정이다.

## 구현 순서와 그 이유

사용자 이야기 우선순위(P1 → P3)를 따르되, **정본을 먼저 고친다.**

1. **정본 먼저** — `actions.ts`·`capabilities.ts`·`contracts/ui-contract.md` 의 조작 4개와
   자리 이동. 표를 나중에 고치면 표시 컴포넌트가 「표에 없는 조작」을 그리게 되고, 그 상태로는
   `CapabilityUI` 검사가 무엇을 세야 할지 모른다.
2. **US1 (P1) 저장·이름** — 자리 이동과 판정 수정. 손실로 이어지는 유일한 항목이다.
3. **US2 (P1) 상세 자리·네 상태 분리** — 표시 축을 나눈다. US4 의 체크 칸이 이 축 위에 올라간다.
4. **US4 (P2) 복수 삭제** — 백엔드 라우트 1개 + 화면. US2 의 칸 0 이 있어야 붙는다.
5. **US3 (P2) 지시문 대등성** — 권한표 두 셀 + `openBrowser()` 선행. 독립적이라 순서가 자유롭지만
   US1 의 「저장하고 열기」 경로와 맞물리므로 그 뒤에 둔다.
6. **US5 (P3) Step 별 스크린샷** — 백엔드 촬영·보관·서빙 + 결과 화면. 가장 독립적이고 가장 크다.
7. **기존 검증 개정** — 각 단계에서 그 단계가 깨뜨린 검사를 **그 단계 안에서** 고친다.
   마지막에 몰면 어느 변경이 어느 검사를 깨뜨렸는지 가릴 수 없다.

## Complexity Tracking

> Constitution Check 에 위반이 없다. 이 표는 비어 있다.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
