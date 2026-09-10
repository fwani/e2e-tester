# Phase 1 — 데이터 모델

**대상**: [spec.md](spec.md) · [research.md](research.md)

## 0. 저장 형식 변경 요약

| 저장물 | 변경 | 기존 파일 호환 |
|---|---|---|
| Test Step DSL (`tests/TC-xxx.yaml`) | **없음** | 해당 없음 |
| 실행 결과 (`.runs/<ID>/result.json`) | `StepResult` 에 선택 필드 2개 추가 | 유지 — 둘 다 기본값 `None` 이라 없는 파일도 그대로 읽힌다 |
| 실행 산출물 디렉터리 | `.runs/<ID>/steps/<index>.png` 추가 | 유지 — 기존 `failure.png`·`console.log`·`network.log` 그대로 |
| 프로젝트 설정 | **없음** | 해당 없음 |

**Step DSL 이 바뀌지 않는다는 것이 이 기능의 성격을 말한다.** 스크린샷은 실행의 산출물이지
테스트의 정의가 아니다. 원칙 I(단일 Step 모델)과 원칙 V(자산 이식성)에 영향이 없다 —
내보낸 Playwright 프로젝트가 이 필드를 알 필요가 없다.

---

## 1. 서버 모델 변경

### 1-1. `StepResult` — Step 별 스크린샷 참조 (`backend/src/itb/domain/run_result.py`)

| 필드 | 형 | 기본값 | 뜻 |
|---|---|---|---|
| `screenshot` | `str \| None` | `None` | 그 Step 이 끝난 시점 화면. **프로젝트 루트 기준 상대 경로** (FR-397) |
| `screenshot_note` | `str \| None` | `None` | 남기지 못한 사유. `screenshot` 이 `None` 일 때만 의미가 있다 (FR-391) |

규칙:

- 실행 대상이 아니던 Step(`skipped`·`not_run`)은 **둘 다 `None`** 이다. 사유도 남기지 않는다 —
  찍지 못한 것이 아니라 찍을 일이 없었다 (FR-393).
- 실패한 Step 의 `screenshot` 은 기존 `Artifacts.failure_screenshot` 과 **같은 경로**를 가리킨다.
  파일을 두 벌 만들지 않는다 (FR-394).
- 민감 값이 들어 있어 쓰지 않은 경우: `screenshot = None`, `screenshot_note` 에 사유 (FR-392).
- 절대 경로를 넣지 않는다. 결과 파일이 장비에 묶이고 사용자 홈 경로가 노출된다 (기존 규칙).

### 1-2. `Artifacts` — 변경 없음

`failure_screenshot`·`console_log`·`network_log`·`trace` 그대로다. Step 별 스크린샷은
`StepResult` 에 붙는다 — 실행 전체의 산출물이 아니라 Step 하나의 산출물이기 때문이다.

### 1-3. `ArtifactPaths` / `ArtifactCollector` (`backend/src/itb/execution/artifacts.py`)

새 항목:

| 이름 | 성격 |
|---|---|
| `STEP_SHOTS_DIR = "steps"` | `.runs/<ID>/steps/` |
| `write_step_screenshot(run_dir, project_root, scrubber, page, index) -> (path \| None, note \| None)` | 한 Step 의 화면을 쓴다. 기존 `_write_screenshot` 의 민감 값 검사·오류 처리를 그대로 쓴다 |
| `clear_step_screenshots(run_dir)` | 실행 시작 시 `steps/` 를 비운다 (FR-396a). 실패해도 실행을 막지 않는다 (FR-396c) |

**`_write_screenshot` 을 복제하지 않는다.** 민감 값 검사(`_contains_secret`)가 두 벌이 되면
한쪽만 고쳐지는 날이 온다 — 그날 평문 스크린샷이 디스크에 남는다.

---

## 2. 서버 API 변경

### 2-1. 세션 Step 배치 삭제 (신규)

`POST /api/sessions/{session_id}/steps:delete`

| 항목 | 값 |
|---|---|
| 본문 | `{ "step_ids": ["s1", "s3", "s7"] }` — `min_length=1`, 각 항목 `1..100` 자 |
| 응답 | `StepsResponse` (기존과 같다) |
| 원자성 | 목록을 **한 번에** 교체한다. 하나라도 없는 id 가 있으면 아무것도 지우지 않고 거절 (FR-388) |
| 없는 id | `404` + 어느 id 인지 |

기존 `DELETE /api/sessions/{id}/steps/{step_id}` 는 **남긴다.** 한 개를 지우는 행 조작이 그대로
쓰고 있고, 그것을 배치로 대체하면 한 개 삭제가 더 비싸진다 (research R9).

### 2-2. 저장된 테스트 편집 — 라우트 추가 없음

`PUT /api/tests/{id}/definition` 의 `edits` 목록에 `{"op": "delete", "step_id": …}` 를 여러 개
실으면 이미 원자적 복수 삭제다 (research R5). 서버는 그대로 두고 화면이 그렇게 보낸다.

### 2-3. Step 별 스크린샷 서빙 (신규)

`GET /api/tests/{test_id}/result/steps/{index}/screenshot`

| 항목 | 값 |
|---|---|
| `index` | 0 기반 Step 인덱스 (`ge=0`) |
| 응답 | `FileResponse`, `image/png` |
| 결과 없음 | `404 TEST_NOT_FOUND` |
| 인덱스 범위 밖 | `404` + 그 실행의 Step 수 |
| `screenshot` 이 `None` | `404` + `screenshot_note` 를 사유로 (FR-391·FR-396b) |
| 경로가 프로젝트 밖 | `400 INVALID_PATH` — 기존 `get_artifact` 의 경계 검사를 공유한다 |

기존 `GET …/result/artifacts/{kind}` 의 `kind` 를 늘리지 않는다 (research R6).

---

## 3. 화면 모델 변경

### 3-1. `WorkbenchStep` (`frontend/src/components/workbench/model.ts`)

| 필드 | 형 | 뜻 |
|---|---|---|
| `isDeleteTarget` | `boolean` | 지금 삭제 대상으로 골라져 있는가 (FR-380) |
| `screenshotUrl` | `string \| null` | 결과 국면에서 그 Step 의 화면. 없으면 `null` |
| `screenshotNote` | `string \| null` | 없는 사유 (FR-391) |

`focusedStepId`(지목)는 **그대로 둔다.** 삭제 대상과 성격이 다른 상태이며, 하나로 합치면
보고 7번이 다시 생긴다 (research R4).

### 3-2. `WorkbenchModel`

| 필드 | 형 | 뜻 |
|---|---|---|
| `deleteSelection` | `string[]` | 삭제 대상 Step id 집합. **id 로 갖는다** — 인덱스로 가지면 순서 변경 때 다른 Step 이 지워진다 (FR-380b) |

### 3-3. 조작 식별자 (`frontend/src/lib/actions.ts`)

| 신규 | 자리 | 뜻 |
|---|---|---|
| `step.toggleDeleteTarget` | Step 행 (칸 0) | 한 행을 삭제 대상에 넣고 뺀다 |
| `step.selectAllDeleteTargets` | Step 패널 머리 | 전부 고르기 / 전부 풀기 (FR-380c) |
| `step.deleteSelected` | 팔레트 | 고른 것 전부 지우기 (FR-382) |
| `step.deleteAfter` | 팔레트 | 지목한 Step 다음 전부 지우기 (FR-383) |

`step.delete`(행 하나)는 남는다.

### 3-4. 조작의 집 — 바뀌는 줄만

007 `ui-contract.md` §2-7 「조작의 집」에서 **이 세 줄이 바뀐다** (그 표는 011 이 계약으로 올렸다).

| 조작 | 이전 집 | 새 집 |
|---|---|---|
| `save` | 팔레트 | **국면 띠** |
| `edits.revert` | 팔레트 | **국면 띠** |
| `test.rename` | 팔레트 (입력칸) | **국면 띠** (이름 표시를 그 자리에서 고침) |

`test.setStartUrl`·`ai.compose` 는 팔레트에 남는다 (research R1).

### 3-5. 권한표 (`frontend/src/lib/capabilities.ts`) — 바뀌는 셀

| 국면 | 조작 | 이전 | 이후 |
|---|---|---|---|
| `editing` | `step.recordStart` | `off("NEEDS_BROWSER", "browser.openAt")` | `cond("C7")` (누르면 자동으로 연다) |
| `editing` | `step.addNaturalLanguage` | `off("NEEDS_BROWSER", "browser.openAt")` | `cond("C7")` (같음) |

**`ON` 이 아니라 `cond("C7")` 이다.** 이 둘은 이제 세션을 **만든다** — 그러므로
`browser.openAt` 과 같은 전제를 갖는다. 다른 세션이 그 테스트를 잡고 있으면 서버가 `409
SESSION_ALREADY_ACTIVE` 로 거절하며, `ON` 으로 두면 009 T063 이 고친 결함(활성으로 그렸다가
눌리면 거절)이 이 두 셀에서 되살아난다. `C7` 은 「정의가 편집 가능하다」 = 「이 테스트를 잡은
세션이 없다」이고 해소 방법도 이미 맞다 (`session.open`).

`step.addAssertion` 은 **바꾸지 않는다.** 검증 추가는 요소를 지목해야 하고(원칙 IV) 지목은
살아 있는 화면에서 사용자가 하는 일이다 — 브라우저를 열어 주는 것으로 끝나지 않는다.

새 조작 4개는 열 국면 전부에 값을 채워야 한다 — `Record<Phase, …>` 가 컴파일 시점에 요구한다.
판정은 각 국면의 `step.delete` 와 같게 두었다: 한 개를 지울 수 없는 상태에서 여러 개를 지울 수
있으면 안 되고 그 역도 안 된다. 전 국면 덮어쓰기 `O4`(Step 이 0개)·`O6`(일시정지 전이 중)에도
넷을 함께 넣었다.

---

## 4. 상태 전이

### 4-1. 삭제 대상 선택

```
비어 있음 ──체크──▶ 일부 선택 ──전부 체크──▶ 전부 선택
    ▲                  │  ▲                      │
    └──전부 풀기────────┘  └──────체크 해제───────┘

  삭제 확정 ──────▶ 비어 있음
  Step 목록 변경 ──▶ 사라진 id 는 집합에서 빠진다 (남은 것은 유지)
  화면 이동 ───────▶ 비어 있음
```

지목(`focusedStepId`)은 이 전이에 **참여하지 않는다** (FR-380a).

### 4-2. Step 스크린샷의 생애

```
실행 시작 ──▶ .runs/<ID>/steps/ 를 비운다          (FR-396a)
Step 종료 ──▶ duration_ms 확정 후 촬영             (FR-395)
   ├ 성공 ──▶ steps/<index>.png · screenshot 채움
   ├ 민감 ──▶ 쓰지 않음 · screenshot_note 채움      (FR-392)
   └ 실패 ──▶ 쓰지 않음 · screenshot_note 에 사유   (FR-391)
실행 종료 ──▶ result.json 에 경로가 함께 저장된다
다음 실행 ──▶ 위 첫 줄로 — 이전 실행 것은 사라진다  (FR-396a)
```

`skipped`·`not_run` Step 은 이 흐름에 들어오지 않는다.

---

## 5. 검증 규칙

| 대상 | 규칙 | 어기면 |
|---|---|---|
| `step_ids` (배치 삭제) | 1개 이상, 중복 없음, 전부 존재 | `400` / `404` — 아무것도 지우지 않는다 |
| 삭제 후 Step 수 (세션) | 0개가 되어도 허용 | 저장 조작이 기존 규칙대로 막힌다 (「Step 이 없으면 저장할 수 없습니다」) |
| 삭제 후 Step 수 (편집) | 0개가 되면 **저장이 거절된다** | `400 STEP_LIST_EMPTY` — 편집은 정의 파일을 쓰는 일이라 빈 정의를 남길 수 없다. 세션과 규칙이 다른 유일한 지점이며 011 이 그것을 바꾸지 않는다 |
| 테스트 이름 | 1~200자, 공백만은 불가 | 저장 거절 + 그 자리에서 사유 (FR-366) |
| `index` (스크린샷 서빙) | 0 이상, 그 실행의 Step 수 미만 | `404` |
| `screenshot` 경로 | 프로젝트 루트 안 | `400 INVALID_PATH` |

---

## 6. Key Entities ↔ 구현 대응

| spec 의 엔터티 | 구현 |
|---|---|
| 테스트 정의 | `domain/test_case.Test` — **변경 없음** |
| Step | `domain/step.Step` — **변경 없음** |
| Step 실행 결과 | `domain/run_result.StepResult` — 필드 2개 추가 |
| 삭제 선택 | 화면 상태 `WorkbenchModel.deleteSelection` — **서버에 없다.** 저장되지 않는 일시 상태다 |
| 실행 산출물 | `.runs/<ID>/` — `steps/` 하위 디렉터리 추가 |
