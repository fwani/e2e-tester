# 기준선 — 028 시작 시점

**왜 적는가**: 이 저장소에는 028 이전부터 실패하던 검증이 있다. 새로 깨뜨린 것과 원래
깨져 있던 것을 가르지 못하면 회귀 판정이 전부 틀린다 (tasks T001·T002).

**측정 시점**: 2026-09-30, 브랜치 `028-list-group-assignment`, 커밋 `da2d985` 기준.

---

## 백엔드 — `cd backend && bash scripts/test-backend.sh`

| 계층 | 결과 |
|---|---|
| 병렬 (시간을 재지 않는 검증) | **6 failed · 3493 passed · 1 skipped** (350s) |
| 순차 (`-m timing`) | 61 passed (152s) |

**원래 빨간 6건** — 전부 실제 브라우저를 쓰는 검증이다.

```
tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-009]
tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-025]
tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-037]
tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-046]
tests/integration/test_mirror_recording_parity.py::test_new_tab_becomes_the_mirrored_tab
tests/integration/test_state_assertion.py::test_the_wait_is_bounded_by_the_timeout
```

> **단서**: 이 측정은 Phase 2 구현과 일부 겹쳐 돌았다(도메인 파일을 고치는 중이었다).
> 여섯 건 모두 브라우저 계층이고 접두어·식별자와 무관해 기준선으로 쓰지만, **마지막
> 전량 검증(T045)에서 같은 여섯 건인지 반드시 다시 대조한다.** 수가 늘면 그때 판단한다.

## 백엔드 린트·스키마

| 명령 | 결과 |
|---|---|
| `uv run ruff check src/ tests/` | **2 errors** (원래 빨강) |
| `uv run lint-imports` | 4 kept · 0 broken — 통과 |
| `uv run python -m itb.schema.export --check` | 드리프트 없음 |

## 프론트 — `cd frontend && npx vitest run`

**2 files failed · 3 tests failed · 1717 passed (1720)** (123s)

```
tests/ScreenSweep.test.ts > 보고서가 낡지 않았다 — 지금 화면 코드로 잰 것이다
tests/ScreenSweep.test.ts > 등록되지 않은 검출이 없다 — 새로 깨진 곳이 없다
tests/EditEntryPoints.test.tsx > 목록 행 메뉴의 「편집」이 편집 가능한 화면으로 데려간다
```

`npx tsc --noEmit` — 통과 (출력 없음).

---

## 회귀 확인 대상 — 접두어·식별자를 쓰는 검증

이 증분이 건드리는 것은 「식별자를 읽는 방법」이다. 아래가 새로 깨지면 그것은 이
증분의 회귀다.

| 검증 | 무엇을 보나 |
|---|---|
| `tests/unit/test_repository.py` | 파일 이름 ↔ 식별자, 그룹별 번호 채번 |
| `tests/unit/test_domain_invariants.py` | 식별자·접두어 규칙이 허용 목록인가 |
| `tests/unit/test_import_planning.py` | 엑셀 들여오기의 접두어 판정·번호 재부여 |
| `tests/unit/test_sharing_group_mapping.py` | 공유 묶음의 그룹 대응 |
| `tests/contract/test_test_groups_api.py` | 그룹 만들기·이름 바꾸기·해체 |
| `tests/unit/test_excel_columns.py` · 엑셀 계열 | 내보내기 시트 구성 |

**합계 기준선**: 백엔드 3554 통과 / 6 실패 · 프론트 1717 통과 / 3 실패.

---

## 마지막 대조 (T045) — 2026-10-01

| 대상 | 시작 | 끝 | 판정 |
|---|---|---|---|
| 백엔드 통과 | 3493 | **3582** | +89 (신규 검증) |
| 백엔드 실패 | 6 | **4** | −2 — 새로 깨진 것 없음 |
| 프론트 통과 | 1717 | **1752** | +35 |
| 프론트 실패 | 3 | **2** | −1 — 새로 깨진 것 없음 |
| ruff | 2 errors | **2 errors** | 같음 |
| lint-imports | 통과 | 통과 | 같음 |
| 스키마 드리프트 | 없음 | 없음 | 같음 |
| `tsc --noEmit` | 통과 | 통과 | 같음 |

**끝에 남은 실패 — 전부 기준선에 있던 것이다.**

```
백엔드: AS-009 · AS-025 · AS-037 · AS-046 (tests/abnormal/test_ui_surface.py)
프론트: ScreenSweep 2건
```

시작 시점에 빨갰던 `test_mirror_recording_parity` 와 `test_state_assertion`,
프론트의 `EditEntryPoints` 는 이번 실행에서 통과했다 — **이 증분이 고친 것이 아니라
흔들리는 검증이다.** 성과로 세지 않는다.

**건드리지 않은 것**: 028 은 접두어·식별자·목록 화면만 바꿨고 위 실패들은 실제 브라우저
계층(AS 계열)과 화면 순회 보고서다. 접두어를 쓰지 않는다.
