# Implementation Plan: AI 의 손이 어디에 있는지 보인다

**Branch**: `024-ai-focus-overlay` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/024-ai-focus-overlay/spec.md`

---

## Summary

AI 가 요소를 조작한 직후, **실행기가 실제로 채택한 그 요소**의 경계 상자를 읽어 실행
기록에 싣는다. AI 작성 경로가 그 값을 꺼내 `ai_focus` 이벤트로 발행하고, 화면은 미러
프레임이 이미 실어 오는 좌표 근거로 변환해 테두리를 그린다.

**새로 만드는 것이 적다.** 좌표 변환의 역방향이 이미 있고(미러 조작), 좌표 근거가 이미
프레임마다 실려 오고, 모든 요소 조작이 이미 한 경로를 지난다. 이 기능은 그 셋 위에
얹힌다.

**대상 화면에는 아무것도 심지 않는다.** 관찰 도구가 관찰 대상을 바꾸지 않는다.

---

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5 / React 18 (frontend)

**Primary Dependencies**: FastAPI, Playwright for Python, React, Tailwind CSS. **새 의존성
없음**

**Storage**: 해당 없음 — 이 기능은 저장되는 것을 만들지 않는다

**Testing**: pytest (backend), Vitest + Testing Library (frontend), lint-imports (임포트
계약)

**Target Platform**: 로컬 데스크톱 워크벤치 (브라우저 UI + 로컬 서버)

**Project Type**: Web application (backend + frontend)

**Performance Goals**: 조작 한 건당 이벤트 한 건. AI 의 동작 빈도(수 초에 한 번)를
넘지 않으므로 채널 부하가 늘지 않는다. 좌표 측정은 이미 요소를 확정한 뒤이므로 요소
탐색이 추가되지 않는다

**Constraints**:
- 표시 실패가 작성을 멈추면 안 된다 (FR-006)
- 재생 경로에서 이 알림이 나가면 안 된다 (FR-007 · 헌법 원칙 II)
- 대상 페이지 DOM 을 바꾸면 안 된다 (FR-025)

**Scale/Scope**: 백엔드 3개 모듈, 프론트 4개 파일 안팎. 새 화면 없음

---

## Constitution Check

*GATE: Phase 0 전에 통과해야 한다. Phase 1 설계 후 재확인한다.*

### I. Unified Step Model (NON-NEGOTIABLE) — 통과

- Step DSL 을 건드리지 않는다. 새 Step 종류도, 새 필드도 없다 (data-model §1).
- 이 기능은 **작성자를 구별하지 않는다.** 사람이 직접 녹화할 때 표시하지 않는 것은
  Step 의 의미 차이가 아니라 **표시할 값이 없기 때문**이다 — 자기가 클릭한 자리를
  되돌려 보여 주는 일이다.
- 만들어지는 Step 이 표시의 유무와 무관하게 같다 (FR-024 · SC-007).

### II. Deterministic Replay (NON-NEGOTIABLE) — 통과, **가장 주의할 자리**

이 기능이 `StepExecutor` 를 건드린다. 그 실행기는 **재생 경로도 쓴다.**

| 지킴 | 어떻게 |
|---|---|
| 실행기는 LLM 을 부르지 않는다 | 바뀌지 않는다. 경계 상자를 읽을 뿐이다 |
| 실행기는 **아무것도 발행하지 않는다** | 값을 반환한다. 발행은 AI 작성 전용 모듈에서만 |
| 재생에서 `ai_focus` 0 건 | 발행 지점이 재생 경로에서 **도달 불가능**하다 |

**콜백을 달지 않은 것이 이 통과의 핵심이다.** 실행기에 `on_element_resolved` 를 두면
재생 배선 한 줄로 위반이 생길 수 있다. 값을 돌려주는 설계에서는 재생 쪽이 이벤트를
내려면 코드를 새로 써야 한다 (research R5).

검증으로 고정한다 — 기존 원칙 II 타임라인 검증에 이 이벤트를 더한다.

### III. Stateful Interactive Runner — 통과

세션 상태·일시정지·인수 경로를 건드리지 않는다. 표시는 세션 밖의 흘러가는 값이며,
사라져도 세션이 잃는 것이 없다.

일시정지 국면에서 사용자가 미러를 조작하는 경로를 **막지 않는다** — 오버레이가 포인터를
받지 않는다 (FR-020).

### IV. Locator Resilience — 통과, **이 기능이 원칙을 근거로 삼는다**

자리를 **실행기가 채택한 요소**에서 읽는 결정(research R1)의 근거가 이 원칙이다. CSS
경로로 다시 재는 설계는 우선순위 전략을 우회하는 두 번째 탐색 경로를 만들며, 원칙이
「한 곳에 있어야 한다」고 정한 로직이 둘로 갈린다.

후보 수집·우선순위·해석 로직을 **한 줄도 고치지 않는다.** 확정된 요소를 읽기만 한다.

### V. Asset Portability — 통과

내보내기에 영향이 없다. 저장 형식이 바뀌지 않으므로 DSL ↔ Playwright 대응도 그대로다.
표시는 제품 UI 의 성질이며 테스트 자산의 일부가 아니다.

### 보안 제약 — 통과

| 요구 | 확인 |
|---|---|
| 하드코딩 비밀 없음 | 해당 없음 |
| 민감 값 마스킹 | 알림에 **값이 실리지 않는다.** 이름표는 `{요소 이름} {동작}` 이며 입력값을 담지 않는다 (research R10) |
| 경계에서 입력 검증 | 페이로드는 서버가 만든다. 좌표는 수치 검증을 거친다 |
| 오류를 명시적으로 처리 | 측정 실패는 `None` 으로 흡수하고 작성을 멈추지 않는다 (FR-006) |
| 생성 코드를 데이터로 | 해당 없음 — 코드를 만들지 않는다 |

**새 보안 위험이 없다.** 이 기능이 내보내는 것은 좌표 숫자 넷과 이미 나가고 있는
이름표다.

### 품질 게이트

| 게이트 | 계획 |
|---|---|
| 원칙 준수 | 위 표. 재생 경로 무도달을 검증으로 고정 |
| 라운드트립 무결성 | DSL·녹화·생성기를 건드리지 않으므로 해당 없음 |
| 테스트 동반 | 단위(변환·판정)·계약(이벤트)·종단(좌표 정확성) 각각 |
| 비활성 테스트 없음 | 기존 테스트를 지우거나 약화하지 않는다 |
| 성공 지표 인식 | 작성 흐름의 **관찰성**을 높인다. 작성 성공률 자체를 바꾸지 않는다 |

### 범위 밖 침범 여부 — 없음

헌법이 금지한 것(모바일·API 테스트·성능·시각 회귀·자동 자가 치유 등) 중 어느 것도
건드리지 않는다.

**결론: 위반 없음. Complexity Tracking 을 채우지 않는다.**

---

## Project Structure

### Documentation (this feature)

```text
specs/024-ai-focus-overlay/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — 결정 11건
├── data-model.md        # Phase 1 — 흘러가는 값들
├── quickstart.md        # Phase 1 — 손으로 확인하는 순서
├── contracts/
│   └── ai-focus.md      # Phase 1 — 이벤트 계약
├── checklists/
│   └── requirements.md  # 명세 품질 점검
└── tasks.md             # /speckit-tasks 가 만든다
```

### Source Code

```text
backend/src/itb/
├── execution/
│   └── step_executor.py        ← 자리를 읽어 StepExecution·StepFailure 에 싣는다
├── authoring/
│   └── tools.py                ← _execute 가 자리를 꺼내 FocusSink 로 알린다
└── api/routes/
    └── sessions.py             ← FocusSink 를 ai_focus 발행에 잇는다 (2곳)

backend/tests/
├── unit/                       ← 자리가 실려 돌아오는가
├── contract/                   ← 이벤트 모양·발행 조건
├── e2e/                        ← 좌표 정확성 · 대상 화면 무변경
└── test_principle_ii_timeline.py  ← 재생에서 0 건

frontend/src/
├── components/mirror/
│   ├── useMirrorInput.ts       ← toDisplayRect 정변환 (역변환과 같은 파일)
│   └── FocusOverlay.tsx        ← 테두리를 그리는 것 (신규)
├── components/
│   └── MirrorView.tsx          ← 래퍼 + 오버레이 배치. 판정은 하지 않는다
├── pages/
│   └── SessionScreen.tsx       ← ai_focus 수신 · 수명 · 변환 · 그릴지 판정
└── api/
    └── ws.ts                   ← SessionEvent 유니온에 ai_focus

frontend/tests/                 ← 변환·라운드트립·그리지 않는 조건·포인터 통과
```

**Structure Decision**: 기존 backend/frontend 2분할 구조 그대로다. 새 최상위 디렉터리를
만들지 않는다. 신규 파일은 `FocusOverlay.tsx` 하나이며, 나머지는 기존 파일에 더한다.

정변환을 역변환과 **같은 파일**에 두는 것이 구조상의 유일한 강제다 — 둘은 서로의
역이어야 하고, 떨어져 있으면 한쪽만 고쳐지는 날이 온다 (research R3).

---

## 구현 순서 (권고)

각 단계가 그 자체로 검증 가능하다.

| 순서 | 무엇 | 왜 이 순서인가 |
|---|---|---|
| 1 | 실행기가 자리를 반환한다 | 아래 전부의 입력. 화면 없이 검증된다 |
| 2 | 정변환 + 라운드트립 검증 | 브라우저 없이 검증된다. 여기가 틀리면 나머지가 다 틀린다 |
| 3 | 통로·이벤트·계약 | 서버 쪽이 완결된다 |
| 4 | 화면 수신·수명·판정 | 그릴지 말지가 전부 여기서 결정된다 (research R8) |
| 5 | 오버레이 그리기 | 마지막. 앞이 다 맞아야 의미가 있다 |
| 6 | 재생 0 건 · 대상 화면 무변경 | 헌법 경계 고정 |
| 7 | 종단 — 실제 좌표 정확성 | 사람이 보는 것과 같은 것을 기계가 본다 |

---

## 명세와 달라진 것

**상태를 「수행 중·성공·실패」에서 「성공·실패」로 좁혔다.**

명세 Key Entities 가 「수행 중」을 예시했으나, 자리는 요소가 확정된 뒤에야 알 수 있고 그
시점은 이미 조작이 시작된 뒤다. 「수행 중」을 표시하려면 추측한 자리를 써야 하고, 그것은
이 기능의 값을 깎는다 (research R2).

요구 자체(FR-008)는 「성공했는지 실패했는지」만 요구하므로 요구는 그대로 충족된다.
명세의 해당 줄을 이 결정에 맞춰 좁혔다.

---

## Complexity Tracking

Constitution Check 에 위반이 없으므로 비운다.
