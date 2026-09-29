# 기준선 — 025 시작 시점 실측

**측정일**: 2026-09-29 | **커밋**: `7cf0398` (025 작업 목록까지)

이 문서의 목적은 하나다. **기존 실패를 이 기능이 낸 실패와 섞지 않는 것.** 끝에서 다시
돌린 결과와 여기를 대조해, **차이만** 025 의 것으로 본다 (022 T001 과 같은 목적).

---

## T001 — 전량 검증 기준선

| 대상 | 명령 | 결과 |
|---|---|---|
| 백엔드 (병렬 계층) | `bash scripts/test-backend.sh` | **4 failed**, 3266 passed, 1 skipped |
| 백엔드 (순차 계층) | 〃 | 60 passed |
| 백엔드 린트 | `uv run ruff check src/ tests/` | **2 errors** |
| 임포트 계약 | `uv run lint-imports` | **4 kept, 0 broken** ✅ |
| 프론트 테스트 | `npx vitest run` | **2 failed**, 1620 passed (138 파일 중 1 실패) |
| 프론트 타입 | `npx tsc --noEmit` | 통과 ✅ |

### 실패 목록 — 전부 기존 실패다

```
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-009]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-025]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-037]
FAILED tests/abnormal/test_ui_surface.py::test_abnormal_screen_operation_is_handled[AS-046]
```

020 의 `baseline.md` 가 「020 이전과 같음」으로 기록해 둔 것과 같다.

```
ruff: 2 errors — step_executor.py:726, test_negative_assertion.py:126 (021 이 넣은 긴 줄)
vitest: tests/ScreenSweep.test.ts 2건 — 순회 보고서가 019 이후 재생성되지 않았다
```

**임포트 계약 4건이 전부 KEPT 다.** 헌법 원칙 II 가 지금 지켜지고 있고, 이 기능이 그것을
깨뜨리지 않아야 한다 (T079).

### 소요 시간

| 계층 | 시간 |
|---|---|
| 백엔드 병렬 | 4분 54초 |
| 백엔드 순차 | 2분 35초 |
| 프론트 | 35초 |

---

## T002 — 현행 관찰 한 번의 크기

`observe_page` 응답을 JSON 으로 직렬화한 바이트를 잰다. 모델에게 실제로 실리는 것이 그것이다.

### 샘플 앱 화면들

| 화면 | 요소 수 | 본문 글자 | 응답 바이트 |
|---|---:|---:|---:|
| projects.html | 5 | 24 | 1,396 |
| noisy.html | 4 | 4,000 | 10,826 |
| interactions.html | 13 | 78 | 3,489 |
| data.html | 5 | 24 | 1,396 |
| analysis.html | 5 | 24 | 1,396 |

샘플 앱은 작다. **상한 근처를 재려면 합성 화면이 필요하다.**

### 상한 근처 — 실제 관리 화면에 가까운 모양

요소 200개(상한), 긴 접근가능한 이름(「3번 그룹 12번째 항목 상세 보기」), `id`·`placeholder`·
컨테이너 레이블이 붙은 상태. 본문 텍스트 4000자(상한).

```
요소 수          : 200
요소 부분 바이트  : 57,850   (요소당 289)
본문 글자        : 4,000    (8,828 바이트)
응답 전체 바이트  : 66,750
대략 토큰        : 22,250
```

### ⚠️ 설계 문서의 추정치를 정정한다

`research.md` 초안은 관찰 한 번을 **25~35KB** 로 적었다. 실측은 **66.7KB** — **두 배다.**

요소당 289바이트가 나오는 이유는 한글 접근가능한 이름(UTF-8 3바이트/글자)과, 2026-09-11 에
더해진 구별용 필드들(`id`·`placeholder`·`label`·`context`)이다. 그것들은 필요해서 들어간
것이고 빼자는 말이 아니다 — **추정으로 설계를 세우면 안 된다는 사실의 예다.**

이 값이 뜻하는 것: 한 지시에 허용된 도구 호출 40회 중 관찰이 20회면 **약 1.3MB, 44만
토큰**이 한 턴 안에 쌓인다. 접기(US6)의 값이 초안이 생각한 것보다 크다.

## T003 — 한 지시에 모델로 전달되는 총 분량

**직접 실측하지 못했다.** 이 값을 재려면 SDK 의 tool runner 가 내부에 쌓는 messages 를
봐야 하고, 그러려면 모델 자격 증명이 필요하다 (이 환경에 없다). 가짜 드라이버는 SDK 를
대체하므로 그 자리를 대신 재지 못한다 — research R1 이 지적한 바로 그 한계다.

**대신 T002 의 실측값으로 상한을 계산한다.**

| 구성 | 크기 | 근거 |
|---|---|---|
| 시스템 프롬프트 | 약 4KB | 현행 `SYSTEM_PROMPT` |
| 사용자 메시지 (지시문 + 정의 요약) | 최대 8KB + 16KB | `MAX_INSTRUCTION_CHARS`·`DEFAULT_SUMMARY_BUDGET` |
| **화면 관찰 (누적)** | **66.7KB × 관찰 횟수** | T002 실측 |
| 조작 결과·검증 결과 | 회당 수백 바이트 | 작다 |

관찰 20회 기준 **약 1.36MB**. 이것이 SC-008 이 「늘지 않는다」고 말할 때의 비교 대상이다.

**자격 증명이 있는 환경에서 다시 잰다.** T031·T043 이 그 자리다.
