# Implementation Plan: 이상 경로 견고성 (비정상 조작 결함 라운드)

**Spec Directory**: `specs/003-error-path-hardening` | **Date**: 2026-09-04 | **Spec**: [spec.md](./spec.md)

**Branch**: `001-interactive-ai-test-builder` — 001·002 와 같은 브랜치에 이어 쌓는다. 새 브랜치를 만들지 않는다

**Input**: Feature specification from `specs/003-error-path-hardening/spec.md`

## Summary

제품을 이상하게 조작했을 때 나오는 오류가 **"제품이 막은 것"인지 "제품이 깨진 것"인지 구분되지
않는다.** 이 라운드는 그 구분을 오류 계약에 새겨 넣고, 이상 조작 51건을 실제로 가해 무너지는
지점을 고치고, 그것을 자동 검증으로 고정한다.

접근은 셋이다.

1. **분류를 계약에 넣는다** — 기존 `{code, message, detail}` 에 `category`(`blocked`/`broken`)와 `next_action` 을 더한다. 분류는 코드로부터 대응표를 통해 결정되므로 호출부가 매번 적지 않는다. 처리되지 않은 오류에 쓰이던 `DEFINITION_INVALID` 재사용을 끝내고 `INTERNAL_ERROR` 를 새로 만든다
2. **이미 있는 이음매를 쓴다** — 오류 계약을 `domain/` 으로 옮기면 기존 스키마 내보내기 파이프라인과 CI 드리프트 잡이 그대로 EC-006 을 지킨다. 상태 기계의 `allowed_commands()` 가 AP-020 의 "지금 무엇이 가능한지"를 만든다. AI 클라이언트 팩터리가 늦은 임포트라 제품 코드 수정 없이 대체된다. 새 의존성은 도입하지 않는다
3. **훑어서 검증한다** — 경로를 하나씩 검사하지 않고 등록된 전체를 열거해 훑는다. 새 경로가 추가되면 자동으로 포함된다 (RG-104)

## Technical Context

**Language/Version**: Python 3.13 (backend), TypeScript 5 / React 19 (frontend)

**Primary Dependencies**: FastAPI, Playwright for Python, Pydantic v2 · React, Vite. **이 라운드에서 새 의존성을 도입하지 않는다**

**Storage**: 로컬 파일 — 테스트 정의 YAML, 프로젝트 등록부 JSON, 비밀 값 저장소

**Testing**: pytest (backend: unit · contract · integration · e2e), Vitest + Testing Library (frontend).
**실행은 `uv run python -m pytest` 여야 한다** — 실행 파일로 돌리면 현재 디렉터리가 경로에 들어가지 않아 공용 픽스처 임포트가 깨진다 (기존 조건, research R7).
**제품 UI 를 실제로 띄우는 검증은 이 저장소에 없었다.** 이 라운드가 만든다 (RG-105)

**Target Platform**: 단독 로컬 도구. 로컬 인터페이스에만 바인딩. 계정·인증·권한 없음

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 이 라운드에 성능 목표 없음. 다만 이상 조작 반복이 자원 누수를 만들지 않아야 한다 (Edge Case)

**Constraints**: 001·002 의 기존 검증 100% 통과 (RG-102). 오류 응답 봉투 변경 금지 — 필드 추가만. 제품 코드에 검증 전용 분기를 남기지 않는다

**Scale/Scope**: 이상 조작 시나리오 51건 (12개 조합 각 3건 이상). 요청 경로 약 30개, 화면 14개, 오류 코드 24개

## Constitution Check

*GATE: Phase 0 이전 통과 필수. Phase 1 이후 재확인.*

| 원칙·게이트 | 판정 | 근거 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | ✅ 통과 | Step DSL 을 건드리지 않는다. 오히려 오류 계약을 `domain/` 으로 들여 Cross-language schema duty 위반(프런트엔드가 `ErrorCode` 23개를 손으로 복제 중)을 **해소한다** |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | ✅ 통과 | 재실행 경로에 LLM 호출을 추가하지 않는다. AI 실패 주입은 **작성 경로에만** 적용되며 검증 코드에만 존재한다. 제품에 실패 주입 스위치를 넣지 않는다 (research R4 에서 그 대안을 기각) |
| **III. Stateful Interactive Runner** | ✅ 통과·강화 | AP-024(거부가 세션을 못 쓰게 만들지 않는다)와 AP-002(에러 뒤 작업 보존)가 이 원칙을 이상 경로로 확장한다. 상태 기계를 바꾸지 않고 `allowed_commands()` 를 읽기만 한다 |
| **IV. Locator Resilience** | ✅ 통과 | 해석 논리를 건드리지 않는다. AS-016(접근 가능한 이름이 없는 요소), AS-031(해석 중 페이지 이동)은 기존 논리가 이상 입력에서 무너지지 않는지 확인할 뿐이다 |
| **V. Asset Portability** | ✅ 통과 | DSL 을 바꾸지 않으므로 내보내기 가능성이 줄지 않는다. Export 구현(릴리스 게이트 RG-1)은 이 라운드 범위 밖이며 **여전히 미완이다** — 출하 전에 별도 라운드가 필요하다 |
| **게이트 1. 원칙 준수** | ✅ | 위 표가 근거다. 재실행 경로에서 LLM 도달 불가는 변경 없음으로 유지된다 |
| **게이트 2. 왕복 무결성** | 해당 없음 | Step DSL·Recorder·Generator 를 바꾸지 않는다 |
| **게이트 3. 테스트 동반** | ✅ | 이 라운드의 산출물 자체가 검증이다. 세 면 각각에 자동 검증을 둔다 (RG-103) |
| **게이트 4. 비활성 테스트 금지** | ✅ | 기존 검증을 지우거나 건너뛰지 않는다. 규약 변경으로 기존 검증이 깨지면 검증이 아니라 구현을 고친다 |
| **게이트 5. 성공 지표 인지** | ✅ | 이 라운드는 PRD §18 의 측정 흐름(테스트 작성·NL 변환·재실행·인수 복구)의 **정상 경로를 바꾸지 않는다.** 이상 경로만 다루므로 지표에 미치는 예상 영향은 없다. RG-102 가 그것을 확인한다 |
| **보안 제약 — 오류 처리** | ✅ 핵심 | "Errors MUST be handled explicitly … never a silent pass or an unhandled crash" 가 EC-007·AP-001 의 직접 근거다 |
| **보안 제약 — 비밀 값** | ✅ | EC-005 와 SC-209 가 오류 경로에서의 노출을 막는다. 기존 가리기 장치를 그대로 쓴다 |
| **단순성** | ✅ | 새 의존성 0. 새 프레임워크 0. 이미 있는 스키마 파이프라인·상태 기계·고정 앱·늦은 임포트를 쓴다 |
| **범위 밖 금지 항목** | ✅ | 모바일·API 테스트 빌더·성능/부하·시각 회귀·자동 자가치유 어느 것도 만들지 않는다 |

**Phase 1 이후 재확인**: 설계 산출물(`data-model.md`, `contracts/`)을 만든 뒤 위 판정에 변동 없음.
`Complexity Tracking` 에 기록할 위반 없음.

## Project Structure

### Documentation (this feature)

```text
specs/003-error-path-hardening/
├── plan.md                              # 이 파일
├── spec.md                              # 요구사항 (EC 8 · AP 20 · RG 4 · SC 9)
├── research.md                          # Phase 0 — 결정 6건
├── data-model.md                        # Phase 1 — 오류 계약 · 시나리오 모델
├── quickstart.md                        # Phase 1 — 검증 절차 10단계
├── checklists/
│   └── requirements.md                  # 명세 품질 점검 (16항목 통과)
├── contracts/
│   ├── error-contract.md                # 오류 계약 변경분
│   └── abnormal-scenarios.json          # 이상 조작 시나리오 51건 (권위 목록)
└── tasks.md                             # Phase 2 — /speckit-tasks 가 만든다
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── domain/
│   │   └── error.py                     # 신설 — 오류 계약 권위 정의 (이동)
│   ├── api/
│   │   ├── errors.py                    # 축소 — FastAPI 결합부만. 도메인 모델 재수출
│   │   ├── app.py                       # 수정 — 최종 처리기가 INTERNAL_ERROR 를 쓴다
│   │   └── routes/                      # 수정 — next_action 을 채운다
│   ├── execution/
│   │   └── state_machine.py             # 읽기만 — allowed_commands() 를 오류 detail 에 싣는다
│   ├── storage/
│   │   ├── atomic.py                    # 신설 — 임시 파일 + 바꿔치기 (registry 에서 추출)
│   │   ├── yaml_io.py                   # 수정 — 원자적 쓰기 경유
│   │   └── repository.py                # 수정 — 원자적 쓰기 경유
│   ├── secrets/store.py                 # 수정 — 원자적 쓰기 경유
│   └── schema/export.py                 # 수정 — error-response 를 내보내기 대상에 추가
├── schema/
│   └── error-response.schema.json       # 신설 (생성물)
└── tests/abnormal/                      # 신설 — 이 라운드의 검증
    ├── catalogue.py                     #   목록 로더 · 판정 3축 헬퍼 · 수단 레지스트리
    ├── product_ui.py                    #   제품 UI 실브라우저 픽스처 (RG-105) ★ 이 저장소에 없던 것
    ├── fakes.py                         #   AI 대역 (검증 코드 전용)
    ├── drivers/
    │   ├── api_drivers.py               #   요청 경계 19건의 실행 수단
    │   ├── ui_drivers.py                #   화면 18건의 실행 수단 (실브라우저)
    │   └── boundary_drivers.py          #   외부 경계 14건의 실행 수단
    ├── test_catalogue.py                #   커버리지(SC-206) + 수단 등록 전수성(RG-106)
    ├── test_error_contract.py           #   분류 전수성 · INTERNAL_ERROR (RG-104-1 · EC-003)
    ├── test_route_sweep.py              #   전 경로 훑기 (RG-104-2)
    ├── test_no_bypass.py                #   계약 우회 금지 (RG-104-3)
    ├── test_api_surface.py              #   목록을 읽어 api 19건을 펼친다
    ├── test_ui_surface.py               #   목록을 읽어 ui 18건을 펼친다
    └── test_boundary_surface.py         #   목록을 읽어 boundary 14건을 펼친다

frontend/
├── src/
│   ├── components/ErrorNotice.tsx       # 신설 — 오류 표시 공용 통로 (message + next_action)
│   ├── api/client.ts                    # 수정 — 손으로 쓴 ErrorCode union 삭제, 생성 타입 임포트
│   ├── pages/*.tsx                      # 수정 — 오류 표시를 공용 통로로
│   └── types/generated/error-response.d.ts  # 신설 (생성물)
└── tests/abnormal/                      # 신설 — 화면 쪽 검증 (AP-003 · AP-022 · RG-104-4)

fixtures/sample-app/                     # 수정 — 지연 · 무응답 · 오류 경로 추가 (제품 아님)
```

**Structure Decision**: 001·002 가 쓴 backend/frontend 2층 구조를 그대로 쓴다. 이 라운드가 더하는
것은 **`domain/error.py` 하나와 `tests/abnormal/` 한 벌**이다.

화면 검증을 프런트엔드가 아니라 백엔드에 두는 이유는 **브라우저 자동화 수단이 이미 거기 있기**
때문이다. 프런트엔드에 브라우저 테스트 도구를 새로 넣으면 의존성이 늘고, 이 라운드의 제약
(새 의존성 0)에 걸린다. 기존 컴포넌트 검증 14건은 그대로 둔다 — 빠르고 촘촘해서 다른 값을
가지며, 실브라우저 계층이 그것을 대체하지 않고 위에 얹힌다 (research R7).

## Phase 요약

| Phase | 상태 | 산출물 |
|---|---|---|
| 0. Research | 완료 | `research.md` — 결정 6건 (R1 분류 얹기 · R2 단일 출처 · R3 시나리오 목록 · R4 실패 재현 · R5 전수 점검 · R6 동시성·원자성) |
| 1. Design & Contracts | 완료 | `data-model.md`, `contracts/error-contract.md`, `contracts/abnormal-scenarios.json` (51건, 12조합 전부 3건 이상), `quickstart.md` |
| 2. Tasks | 미착수 | `/speckit-tasks` 가 `tasks.md` 를 만든다 |

## 구현 순서 (Phase 2 입력)

의존 관계상 아래 순서가 강제된다. tasks 는 이 순서를 지켜야 한다.

1. **오류 계약을 도메인으로** — `domain/error.py` 신설, `category`·`next_action`·`INTERNAL_ERROR`, 대응표, 스키마 내보내기, 프런트 타입 생성. **완료** (커밋 `9023506`)
2. **검증 장치** — 목록 로더 · 판정 3축 헬퍼 · 수단 레지스트리 · **제품 UI 실브라우저 픽스처** · AI 대역 · 고정 앱 지연 경로. 이것이 없으면 시나리오를 한 건도 못 돌린다
3. **훑는 검증 셋** (RG-104-1~3) — 여기서 나오는 실패가 결함 목록이 된다
4. **화면 공용 오류 통로** — `ErrorNotice` 와 각 화면의 경유. 판정축 ②의 전제
5. **면별 실행 수단 셋** — 목록을 읽어 51건을 펼친다. 시나리오마다 작업을 만들지 않는다 (research R8)
6. **드러난 결함 수정** — 원자적 쓰기 통합, 가능한 명령 노출, 그리고 5 가 낸 실패
7. **회귀 확인** (RG-102 · SC-207) — 001·002 검증 전부

## 위험과 대응

| 위험 | 대응 |
|---|---|
| **제품 UI 실브라우저 계층이 이 저장소에 처음 생긴다.** 서버 둘을 띄우므로 느리고, 포트 충돌·도구 부재로 불안정할 수 있다 | 도구·포트가 없으면 **건너뛰지 않고 실패**로 알린다 (RG-106). 조용한 건너뛰기는 SC-201 을 거짓으로 만든다 |
| **다른 세션이 같은 저장소를 동시에 수정 중이다** (2026-09-04 13:51 커밋 `725a9bb` 로 확인). 구현 단계는 `backend/`·`frontend/` 를 폭넓게 건드리므로 충돌 가능성이 실재한다 | 설계 단계 산출물은 `specs/003-error-path-hardening` 아래에만 썼다. **구현 착수 전에 사용자에게 확인이 필요하다** |
| `category`·`next_action` 을 필수로 만들면 오류 생성 지점이 전부 깨진다 | 분류는 대응표에서 자동 결정, `next_action` 은 코드별 기본 문구. 호출부 변경을 최소화한다 |
| 오류 모델 이동으로 기존 임포트가 깨진다 | `api/errors.py` 가 도메인 모델을 재수출한다 (RG-102) |
| 훑는 검증이 경로마다 유효한 거부를 만들어내지 못한다 | 경로별 최소 거부 유발 방법을 목록으로 두되, 목록에 없는 새 경로는 **실패**로 취급한다 — 조용히 건너뛰면 RG-104 가 무의미해진다 |
| 이 라운드가 001·002 의 미완 항목(T155·T156·T099)과 섞인다 | 명세에서 범위 밖으로 명시했다. 그 항목들은 사람이 해야 하며 독립이다 |

## Complexity Tracking

> Constitution Check 에 위반 없음. 기록할 항목 없음.
