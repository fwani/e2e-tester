# 사람이 해야 남는 작업 (2026-09-08 기준)

자동으로 닫을 수 있는 작업은 전부 닫혔다. 아래 7건은 **판정하는 주체가 사람이어야
성립하는 것**이며, 준비물은 모두 만들어져 있고 **판정 칸만 비어 있다.**

6·7 은 007(화면 통합)이 진행 중에 등록한 것이다 — 준비물이 아직 만들어지는 중인 항목은
그 사실을 표에 적었다.

이 문서는 색인이다. 절차는 각 항목이 가리키는 문서가 갖는다.

## 왜 자동화로 대체하지 않았는가

추측이 아니라 이번에 관측된 것이다.

- **005 T121** — 「실패한 Step 건너뛰고 계속」은 계약(`ui-contract.md` §6-5)·백엔드
  (`skip_failed`)·통합 테스트가 **모두 통과하는 상태에서 화면 절반이 없었다.** 자동 검증은
  양쪽 끝을 보고 그 사이의 전선은 보지 않았다.
- **005 N-01** — 새로고침이 화면을 잃었는데 변환 함수 테스트는 초록이었다. 변환은 처음부터
  옳았고 틀린 것은 첫 렌더의 국면이었다.
- **002 T099 · 001 T156** — 구현자가 자기 구현을 판정하면 대조가 아니라 자기 확인이 된다.
  이것은 도구의 한계가 아니라 판정의 성질이다.

「전부 통과했다」만 적힌 기록은 다음 사람이 무엇을 걸었는지 알 수 없게 한다. **관측을
남긴다.**

---

## 1. 005 T124 — 「상」 9건 재확인 (SC-221)

| | |
|---|---|
| 절차 | [docs/ux/recheck-protocol-005.md](ux/recheck-protocol-005.md) |
| 기록 | [docs/ux/recheck-sheet-005.csv](ux/recheck-sheet-005.csv) — 18행, `verdict` 비어 있음 |
| 대상 | [005 quickstart §2](../specs/005-ux-walkthrough-repair/quickstart.md) S1~S8 |
| 비교 | [ux-recheck-005.md](ux/ux-recheck-005.md)(직전 관측) · [ux-walkthrough-2026-09-07.md](ux/ux-walkthrough-2026-09-07.md)(원 리포트 22건) |

Phase 12 가 부분 재발 2건(U-03·U-04)과 신규 5건을 닫았다. 그 수정을 **다시 걸어** 확인하는
것이 이 항목이다. 판정은 `해소`·`부분`·`재발` 셋이고 **`부분` 도 조용히 넘기지 않는다** —
직전 재점검의 2건이 그 판정이었고, 등록했기 때문에 Phase 12 가 존재한다.

## 2. 005 T125 — 「부분 성공」 결말 관측 (FR-137)

| | |
|---|---|
| 절차 | [recheck-protocol-005.md §2](ux/recheck-protocol-005.md) |
| 기록 | 같은 시트의 `N-04` · `N-04-file` 행 |
| 대상 | [005 quickstart §3](../specs/005-ux-walkthrough-repair/quickstart.md) S3-5·S3-6 |

직전 재점검이 **「미검증」** 으로 남긴 항목이다. 사유("UI 컨트롤이 없어 도달 불가")는
T121 이 없앴으나 **결말을 제품을 통해 관측한 적이 아직 없다.** 결말을 네 곳에서 본다 —
실행 화면·목록 칩·결과 요약·`.runs/<테스트ID>/result.json` 의 `partial_pass`. 마지막 줄이
요구사항의 실제 기준이다.

## 3. 006 T092 — 편집 경로 S1~S8

| | |
|---|---|
| 절차 | [006 quickstart §2·§3](../specs/006-edit-saved-test/quickstart.md) — 이미 절차 자체다 |
| 기록 | [docs/ux/walkthrough-sheet-006.csv](ux/walkthrough-sheet-006.csv) — 32행, `verdict` 비어 있음 |
| 등록 기준 | [006 quickstart §5](../specs/006-edit-saved-test/quickstart.md) |

**005 T124 와 같은 세션에서 함께 걷는 것을 권한다.** 두 절차가 같은 화면(목록·결과·편집)을
지나고, 006 의 편집 경로가 005 가 고친 어휘·상태 표시를 그대로 쓴다.

이 기능의 주장은 「브라우저를 띄우지 않고 고친다」이므로 시트의 `SC-302`(창 총 개수) 행이
사실상 합격/불합격을 가른다.

## 4. 002 T099 — 디자인 대조 8화면의 판정

| | |
|---|---|
| 대상 | [design-conformance/](../specs/002-defect-fix-design-conformance/design-conformance/) 8개 파일 |
| 규모 | 판정행 **228** — 전부 `미판정` |
| 준비 상태 | `기준값`·`관측값` **100% 채워져 있다** (`scripts/design_baseline.py` · `scripts/design_observed.py`) |
| 완료 조건 | `불일치`·`미판정` **0건** (DC-012 · SC-108) |

각 파일 머리글이 판정 규칙·관측값 읽는 법·확인된 예외를 이미 갖고 있다. **추가 준비는
없다** — 확정 디자인과 제품을 나란히 놓고 축 6개(구조·컴포넌트·치수·타이포색·상태·가감)를
대조하는 일이 남았다.

빈 `관측값` 은 소스로 볼 수 없는 항목(구조·배치·상태 표현)이고 **그쪽이 이 대조의
본체다.** 개수 차이는 대개 불일치가 아니다 — 의미 있는 신호는 **0**(기준값에 있는 값이
구현에서 쓰이지 않음)이다.

## 5. 001 T155 · T156 — MVP 지표 측정과 설계 리뷰

| | T155 (측정) | T156 (리뷰) |
|---|---|---|
| 절차 | [session-protocol.md](measurement/session-protocol.md) | [design-review-guide.md](review/design-review-guide.md) |
| 표본·근거 | [sample-selection.md](measurement/sample-selection.md) | [design-review-pointers.md](review/design-review-pointers.md) — 65항목 전부 `파일:라인` |
| 기록 | [recording-sheet.csv](measurement/recording-sheet.csv) — 20행 17열 | `checklists/design-review.md` — **65항목 미체크** |
| 집계 | `scripts/mvp_metrics_report.py` | `scripts/review_pointers.py` |

T155 는 시나리오 20건 규모의 측정 세션이고, 재는 대상이 **사람의 판단 시간과 실제
언어모델의 결과**다. 자동으로 재는 지표(SC-003·006·007·008·010·011·012)와 수동이 필요한
지표는 [mvp-metrics.md](mvp-metrics.md) 가 구분해 적었다.

T156 은 **요구사항이 잘 쓰였는지**를 본다 — 구현이 동작하는지가 아니다. `[x]` 는 "그 품질
기준이 충족되었다"이고 "그 기능을 만들었다"가 아니다.

## 6. 007 T031 — 통합 화면 artboard 의 승인

| | |
|---|---|
| 대상 | [docs/design/Workbench.dc.html](design/Workbench.dc.html) — 통합 작업 화면 초안 (1440×900) |
| 절차 | [design-conformance-007.md §5](../specs/007-unify-test-screens/contracts/design-conformance-007.md) |
| 승인 대상 | **5건** — research.md R8 의 A1~A5 |
| 완료 조건 | A1~A5 각각에 승인 또는 대체값. 승인 전 초안은 **대조 기준이 아니다** (FR-254c) |

007 은 확정 디자인 6종(`Main`·`RunnerPaused`·`Takeover`·`AiRecord`·`RunResult`·
`StepInspector`)을 **하나의 화면의 일곱 상태**로 합친다. 그러면 002 가 세운 1:1 대응
(DC-008)이 성립하지 않으므로 새 artboard 가 필요하고, **확정 디자인을 새로 정하는 것은
사람의 결정**이다 (DC-001).

초안의 값은 기존 6종에서 **기계적으로 추출한 것만** 썼다. 그래서 승인이 바꿀 여지가 아래
다섯 개로 한정된다.

| # | 항목 | 초안의 값 | 초안의 근거 |
|---|---|---|---|
| A1 | 국면 보조 영역의 자리·최소 높이 | 좌측 대상 앱 영역 아래 · 최소 42px · 내용에 따라 늘어난다 | 자리는 `RunnerPaused`·`Takeover` 의 42px 국면 안내 띠. **「늘어난다」는 확정 디자인에 대응이 없다** — 여기가 실제로 갈리는 지점이다 |
| A2 | 「기록됨」 결말 표식 | 2px 실선 `#9A968A` + 텍스트 라벨 | `RunnerPaused.dc.html` 미실행 행 |
| A3 | 결과 국면 좌측(산출물)의 폭 | 남는 폭 전부 | FR-218a — 좌측만 늘어난다 |
| A4 | 국면 띠의 내용 배치 | 국면 표시 → 테스트 이름 → 결말 요약 → 주요 조작 | `RunResult`·`Main` 의 74px 띠 |
| A5 | 「이 결과 이후 정의가 바뀌었습니다」 알림 | 경고 노랑 `#F5D000` / `#FFF9D6` | 002 §3 경고 색 |

**승인이 거절되거나 값이 바뀌면** 대조 기록과 구현을 그 값으로 고친다. 초안을 근거로
"이미 만들었으니 이대로 두자" 고 하지 않는다 — DC-001 위반의 전형이다.

## 7. 007 T080 — 통합 화면 대조 판정

| | |
|---|---|
| 대상 | [design-conformance/Workbench.md](../specs/007-unify-test-screens/design-conformance/Workbench.md) |
| 준비 상태 | `기준값` 은 `scripts/design_baseline.py` 가 채운다 (`Workbench` 항목 추가됨). **artboard 초안이 있어야 돌아간다** |
| 규모 | 축 6개 × 항목 + **국면 7개의 상태 행** |
| 완료 조건 | `불일치`·`미판정` **0건**. 단 6번 승인 후에만 성립한다 |

002 T099 와 같은 성질의 일이다 — **구현자가 자기 구현을 판정하면 대조가 아니라 자기
확인이다.** 007 도 예외가 아니다.

`상태` 축이 국면마다 행을 갖는 것이 002 와 다른 점이다. 일곱 국면이 하나의 화면이므로
"확정 디자인이 보여주는 상태" 가 하나가 아니다.

---

## 걷기 전에

자동 검증이 통과 상태여야 한다. 깨진 채로 걸으면 제품의 UX 가 아니라 결함을 재게 된다.

```bash
cd backend && uv run playwright install chromium   # 처음 한 번
cd backend && uv run pytest
cd frontend && npx tsc --noEmit && npx vitest run
```

## 걷고 나서

1. 시트를 채운다. **비운 칸을 통과로 읽지 않는다** — 걷지 못한 항목은 `미검증` 과 사유를
   적는다.
2. 기대와 다른 것은 해당 FR/U/N 번호를 들어 그 기능의 `tasks.md` 에 남은 작업으로
   등록한다.
3. 전부 통과면 해당 작업을 `[X]` 로 닫고, **관측 문서를 함께 남긴다.**
