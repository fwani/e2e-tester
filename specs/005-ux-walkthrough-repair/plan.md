# Implementation Plan: UX 워크스루 결함 수정 — 실행 왕복과 정직한 상태 표시

**Branch**: `005-ux-walkthrough-repair` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-ux-walkthrough-repair/spec.md`

## Summary

제품을 사람이 직접 걸어 찾은 22건(`docs/ux/ux-walkthrough-2026-09-07.md`)을 고친다.
요구사항은 FR-124~174(51건), 성공 기준은 SC-212~222.

**핵심 판단**: 조사 결과 **22건 중 12건 이상이 화면 표시·문구 문제**였고, 백엔드는 이미
올바르게 기록하고 있는 것이 여럿이었다(Step 건너뜀 구분, 일시정지 경계 대기, 저장 중복
방지). 그래서 이 기능은 도메인을 넓히는 작업이 아니라 **네 곳의 진실을 바로잡고 화면이
그것을 읽게 하는 작업**이다.

바로잡을 네 곳:

1. **실행 결말을 두 값에서 네 값으로** — `pass·fail·stopped·partial`. 사용자가 누른 중지가
   실패로 기록되는 것(U-03)과 실패를 건너뛴 실행이 「완료」로 표시되는 것(U-05)이 여기서
   갈린다
2. **세션 생존 판정** — 종료된 세션이 다음 실행을 막지 않게 하고, 생성 경계에 락·예약을
   둬 동시 실행 1건을 실제로 지킨다(U-01·U-06)
3. **세션 뷰에 Step별 결과** — 화면이 실시간 이벤트 없이도 복원된다(U-18·U-05)
4. **미러 프레임 전달** — 마지막 프레임 캐시 + 무프레임 감시. 원인은 이미 실측으로
   확정됐다(U-24)

나머지는 프론트의 표시·문구이며, 재발을 막기 위해 **어휘 사전 한 곳**으로 모은다.

## Technical Context

**Language/Version**: Python 3.13 (backend) · TypeScript 5.7 / React 19 (frontend)

**Primary Dependencies**: FastAPI · Playwright for Python 1.62 · React 19 (의존성 추가
없음 — 라우터를 넣지 않는다, research R8)

**Storage**: 파일. `.runs/<테스트ID>/result.json` (최근 실행) + `result-full.json`
(최근 전체 실행, 신규). 테스트 정의는 YAML

**Testing**: pytest (backend: unit·contract·integration·abnormal) · Vitest +
Testing Library (frontend)

**Target Platform**: 로컬 단독 도구. 백엔드는 `127.0.0.1` 바인딩(FR-088a). 브라우저는
headed 단일 모드

**Project Type**: 웹 애플리케이션 (backend + frontend 분리)

**Performance Goals**: 실행 시작 조작의 화면 반응 **0.3초 이내**(SC-214) · 미리보기 첫
화면 **3초 이내**(SC-218) · 미러 프레임 5~10 fps 유지(기존 실측치)

**Constraints**: 스키마는 백엔드가 권위이고 프론트 타입은 생성물(헌법 Cross-language
schema duty) · 재실행 경로에 언어모델 금지(원칙 II) · 일시정지가 브라우저 상태를 유지
(원칙 III) · 미러는 입력 전달 경로를 갖지 않음(FR-047a)

**Scale/Scope**: 화면 9개 · 백엔드 변경 파일 약 6개 · 프론트 변경 파일 약 12개 ·
요구사항 51건. 신규 화면 없음

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 설계 후 재확인.*

| 원칙 | 이 기능과의 관계 | 판정 |
|---|---|---|
| **I. Unified Step Model** (NON-NEGOTIABLE) | Step DSL 을 **바꾸지 않는다.** `StepOutcome` 도 그대로다(이미 네 값). 변경은 실행 **결과** 모델과 세션 **조회** 형태에 한정된다. 어휘 사전을 한 곳에 모으는 것은 이 원칙의 방향과 같다 | ✅ 통과 |
| **II. Deterministic Replay** (NON-NEGOTIABLE) | 새로 추가되는 진단·안내 문구(부분 실행 경고, 실패 원인 지시, 건너뜀 안내)는 **전부 규칙 기반**이다. 언어모델을 부르는 코드 경로를 만들지 않는다. 결말 판정도 순수 함수다 | ✅ 통과 |
| **III. Stateful Interactive Runner** | 일시정지의 경계 대기 로직을 **바꾸지 않는다**(research R0). 상태 기계에 새 상태를 넣지 않는다(R7) — 004 의 `한 스텝씩` 재사용 결정을 흔들지 않기 위해서다. 실패 Step 재개 차단(FR-136)은 "멈춰서 고치고 이어간다"를 유지하며 **조용한 건너뜀만** 막는다 | ✅ 통과 |
| **IV. Locator Resilience** | 로케이터 로직을 건드리지 않는다. 결과 화면의 로케이터 후보 표시는 이미 있고 유지된다 | ✅ 해당 없음 |
| **V. Asset Portability** | Step DSL 이 바뀌지 않으므로 내보내기 대응이 바뀌지 않는다. 실행 결말은 저장된 정의에 기록되지 않는다(004 FR-110 과 같은 이유) | ✅ 통과 |

**Cross-language schema duty**: `Outcome` 값 추가와 `RunResult` 필드 추가는 `run-result`
스키마에 실린다. **백엔드 모델 → `python -m itb.schema.export` → `npm run gen:types`**
순서를 한 작업으로 묶는다. 부분적으로 재생성하면 `test_schema_drift.py` 가 중간 상태에서
실패해 원인을 가린다.

**Quality Gates**:

| 게이트 | 이행 |
|---|---|
| 1. 원칙 준수 | 원칙 II 증거 — 새 문구 생성 함수가 순수 함수임을 테스트로 단정한다 |
| 2. 왕복 완결성 | Step DSL·리코더·생성기를 바꾸지 않으므로 record → replay → export 왕복이 영향받지 않는다. 기존 왕복 테스트가 그대로 지킨다 |
| 3. 테스트 동반 | 실측이 요구사항인 항목(0.3초·3초·5회 연타)을 **자동 테스트로 고정**한다(research R11). 화면 배치는 quickstart 수동 절차로 남기고 그 사실을 적는다 |
| 4. 비활성 테스트 없음 | 없다. 결말 값이 늘어 기존 단정이 바뀌는 테스트는 **갱신**하되 약화하지 않는다 |
| 5. 성공 지표 인식 | PRD §18 의 Replay Success Rate 에 영향 없음(실행 판정을 바꾸지 않는다). 대신 "실패 후 재실행까지의 왕복 시간"이 개선된다 — 현재는 왕복이 **불가능**하다 |

**위반 없음.** Complexity Tracking 에 기록할 항목이 없다.

## Project Structure

### Documentation (this feature)

```text
specs/005-ux-walkthrough-repair/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — 조사와 11개 결정
├── data-model.md        # Phase 1 — 결말 4값·실행 범위·세션 뷰
├── quickstart.md        # Phase 1 — 검증 절차 (자동/수동 구분)
├── contracts/
│   ├── rest-api.md      #   세션 생성 거절 조건, 세션 뷰 필드, 결과 응답
│   ├── websocket.md     #   mirror_frame 전송 시점, run_finished 값
│   └── ui-contract.md   #   화면 어휘와 컨트롤 상태 (12건 이상이 여기)
├── checklists/
│   └── requirements.md  # specify 단계 산출물 (22/22 추적)
├── spec.md
└── tasks.md             # Phase 2 — /speckit-tasks 산출물
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── domain/
│   │   └── run_result.py          # Outcome 4값, RunScope, RunResult 필드 4개
│   ├── execution/
│   │   ├── runner.py              # 결말 판정, attempted_count, result-full.json
│   │   ├── session.py             # active_session_for_test 생존 판정, 등록 해제
│   │   └── session_loss.py        # REVIEW 가드 + 의도적 중지에서 감지기 분리
│   ├── mirror/
│   │   └── screencast.py          # 마지막 프레임 캐시, 무프레임 감시
│   ├── api/
│   │   ├── ws/session_events.py   # 구독 시 마지막 프레임 1장
│   │   └── routes/sessions.py     # SessionView 필드 5개, 생성 락·예약, stop 결말
│   └── schema/export.py           # (변경 없음 — 재생성만 수행)
├── schema/                        # 생성물. 커밋 대상
└── tests/
    ├── unit/                      # 결말 판정, 어휘, 생존 판정
    ├── contract/                  # 세션 뷰 필드, run_finished 형태, 스키마 드리프트
    ├── integration/               # 중지 결말, 미러 3초, 동시 생성 5건
    └── abnormal/                  # 이미 끝난 세션에 중지, 알 수 없는 결말 값

frontend/
├── src/
│   ├── theme/
│   │   └── wording.ts             # 신규. 결말 어휘 + stepLabel 유일 변환점
│   ├── hooks/
│   │   └── useScreenUrl.ts        # 신규. history.pushState ↔ Screen 상태
│   ├── components/
│   │   ├── MirrorView.tsx         # 빈 상태 문구
│   │   ├── PacingControl.tsx      # 녹화 국면 라벨
│   │   └── Badges.tsx             # 결말 칩 4값
│   ├── pages/
│   │   ├── RunResult.tsx          # 재실행 경로 통일, 부분 실행 표시, 증거 탭 문구
│   │   ├── SessionScreen.tsx      # 전이 상태, 종료 후 버튼, 결과 복원, 중복 요약
│   │   ├── RunnerPaused.tsx       # 저장 성공 표시, 계속하기 차단
│   │   ├── TestList.tsx           # stepLabel, 행 버튼, RUNNING 칩, 배너 갱신
│   │   └── Runner.tsx             # 진행/결말 표시
│   ├── App.tsx                    # startRun 단일 경로, URL 동기화
│   └── types/                     # 생성물
└── tests/                         # 컴포넌트 테스트
```

**Structure Decision**: 기존 backend + frontend 분리 구조를 그대로 쓴다. **신규 디렉터리는
`frontend/src/hooks/` 하나**이고 신규 파일은 `wording.ts`·`useScreenUrl.ts` 둘이다.
새 화면·새 엔드포인트·새 이벤트 타입은 없다.

## Phase 요약

| Phase | 산출물 | 상태 |
|---|---|---|
| 0 — 조사 | [research.md](./research.md) — 결정 11건. 이미 맞게 되어 있는 것 5건 확인, 열린 항목 2건 판정 | 완료 |
| 1 — 설계 | [data-model.md](./data-model.md) · [contracts/](./contracts/) 3건 · [quickstart.md](./quickstart.md) | 완료 |
| 2 — 작업 분해 | tasks.md | `/speckit-tasks` |

## 구현 순서 (Phase 2 입력)

의존 관계와 **값이 일찍 나오는 순서**를 함께 고려했다. 앞의 것이 뒤의 것의 전제인 곳만
직렬이고, 나머지는 병렬 가능하다.

### 1단계 — 계약 먼저 (직렬. 뒤의 전부가 여기에 의존한다)

1. `Outcome` 4값 · `RunScope` · `RunResult` 필드 4개 → **스키마 내보내기 → 프론트 타입
   생성**을 한 작업으로
2. `SessionView` 필드 5개 (`step_results`·`pause_settled`·`run_scope`·
   `run_start_index`·`saved_at`)

### 2단계 — 백엔드 진실 (병렬 가능. 서로 다른 파일)

3. 결말 판정 우선순위 + `attempted_count` + `result-full.json` (`runner.py`)
4. 활성 세션 생존 판정 + 종료 세션 등록 해제 (`session.py`)
5. 테스트별 생성 락·예약 (`api/routes/sessions.py`)
6. 유실 감지 `REVIEW` 가드 + 의도적 중지에서 감지기 분리 (`session_loss.py`)
7. 미러 마지막 프레임 캐시 + 무프레임 감시 + 구독 시 1장
   (`mirror/screencast.py`, `api/ws/session_events.py`)

### 3단계 — 프론트 토대 (병렬 가능)

8. `wording.ts` — 결말 어휘 사전 + `stepLabel()` 유일 변환점
9. `startRun()` 단일 실행 경로 + in-flight 가드 (`App.tsx`)
10. `useScreenUrl` — 뒤로가기 이탈 방지를 **먼저**, 그다음 결과 화면 복원

### 4단계 — 화면 (병렬 가능. 화면별로 독립)

11. `RunResult` — 재실행 버튼(라벨에 번호·보조 문구·in-flight), 부분 실행 요약,
    건너뜀/미실행 구분, 증거 탭 문구, 최근 전체 실행 보조 표시
12. `SessionScreen`/`Runner` — 일시정지 전이 표시, 종료 후 「닫기」, 중지 결과 화면,
    Step 결과 복원, 중복 요약 제거, 진행→결말 전환
13. `RunnerPaused` — 저장 성공 인라인 확인, 「변경 저장」, 실패 Step 재개 차단
14. `TestList` — `stepLabel` 적용, 행 버튼 둘, `RUNNING` 칩, 배너 갱신·구분
15. `PacingControl`·`MirrorView` — 국면 라벨, 빈 상태 문구

### 5단계 — 고정

16. 실측 요구사항 자동 테스트 (research R11 표의 6건)
17. quickstart §2 수동 절차를 걸어 상 9건 재발 여부 확인 (SC-221)

**독립 배포 가능한 최소 조각**: 1단계 + 2단계 4·5 + 3단계 9 + 4단계 11 이면 US1(실패 →
재실행 왕복)이 성립한다. 리포트가 "가장 아픈 것"으로 지목한 것이 그것이다.

## 위험과 대응

| 위험 | 어떻게 드러나는가 | 대응 |
|---|---|---|
| 결말 값 추가가 기존 화면 분기를 조용히 지나간다 | `outcome === "fail"` 로만 분기하던 곳이 중지를 통과로 오인 | 프론트에서 결말을 **사전 함수로만** 읽게 하고, 분기는 4값 전부를 다루는 `switch` 로 강제한다. 타입 생성물이 누락을 컴파일 시점에 잡는다 |
| 생성 락이 정상 요청을 직렬화한다 | 브라우저 기동(약 1초) 동안 다른 테스트 실행이 막힌다 | 락은 **테스트별**이고, 락 안에서 예약만 하고 즉시 놓는다. 브라우저 기동은 락 밖이다(research R4) |
| 미러 감시가 부하를 준다 | 정적 화면에서 2초마다 스크린샷 | 기존 강등 경로와 같은 코드이며 1 fps 보다 느리다. 프레임이 흐르는 동안에는 감시가 발동하지 않는다 |
| `pause_settled` 를 화면이 잘못 읽어 전이가 영구 표시된다 | 정지했는데 「일시정지 중…」이 남는다 | 낙관적 표시는 **응답으로 반드시 확정**한다. 응답 실패 시에도 전이 표시를 걷는다 |
| URL 동기화가 기존 화면 전환과 충돌 | 뒤로가기가 세션을 잃는다 | 실행 화면은 `session=<id>` 로 복원한다. 라우터를 넣지 않으므로 변경 지점이 `App.tsx` 한 곳이다 |
| 결과 파일 두 개가 어긋난다 | 부분 실행 후 보조 표시가 옛 전체 실행을 가리킨다 | 그것이 의도다(최근 전체 실행). 표시 문구에 "최근 전체 실행"을 명시한다 |
| 22건을 한 번에 고치다 회귀 | 기존 성질이 조용히 깨진다 | quickstart §3 에 지켜야 할 기존 성질 8개를 적어 두었다. 각각 기존 테스트가 있다 |

## Complexity Tracking

> Constitution Check 에 위반이 없으므로 비운다.

헌법 위반·정당화가 필요한 복잡성 **없음**. 신규 의존성 없음(라우터를 넣지 않는 결정,
research R8). 신규 상태 기계 상태 없음(research R7). 도메인 변경은 실행 결말 한 곳으로
최소화(research R0·R1).
