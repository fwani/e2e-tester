# Phase 1 Data Model: 실행 속도 조절과 로딩 대기

**Feature**: `004-run-pacing-readiness` | **Date**: 2026-09-07

이 기능은 **Step DSL 을 바꾸지 않는다.** 헌법 원칙 I 이 걸린 지점이므로 먼저 못박는다 —
새 Step 종류도, Step 필드도 없다. 바뀌는 것은 실행 옵션(세션), 실행 기록(결과), 사용자
취향(설정) 세 곳뿐이다.

---

## 1. RunPacing — 실행 속도 (신규, 순수)

**위치**: `backend/src/itb/domain/run_pacing.py`

**무엇인가**: 한 실행이 Step 사이에 얼마나 쉬는지. **세션에 속하며 테스트 자산이 아니다**
(FR-110).

```
RunPacing (StrEnum)
├── FAST      "fast"       간격 0ms        — 현재 동작
├── NORMAL    "normal"     간격 500ms
├── SLOW      "slow"       간격 1500ms
└── STEP      "step"       간격 없음, 매 Step 경계에서 자동 일시정지
```

**간격 대응표**

| 값 | `delay_ms` | `auto_pause` | 표시 이름 |
|---|---|---|---|
| `fast` | 0 | false | 빠름 |
| `normal` | 500 | false | 보통 |
| `slow` | 1500 | false | 느림 |
| `step` | 0 | true | 한 스텝씩 |

`slow` 가 1500ms 인 근거는 SC-004(최소 1초 이상 식별 가능한 간격). `normal` 500ms 는
20 Step 테스트에 10초를 더하는 수준으로, 기본값으로 감수할 만하다 (research R8).

**불변식**
- 순수 모듈이다. Playwright·FastAPI·파일 입출력을 임포트하지 않는다.
- `delay_ms` 와 `auto_pause` 는 이 대응표 한 곳에서만 나온다. 러너와 화면이 각자 숫자를
  들고 있으면 두 판단이 갈린다.
- 간격은 **다음 Step 이 존재할 때만** 적용된다. 마지막 Step 뒤에는 쉬지 않는다.

**검증 규칙**
- API 로 들어온 값은 열거형 밖이면 거절한다(422). 임의의 밀리초 값을 받지 않는다 —
  단계를 제한하는 것이 목적이며, 자유 입력을 허용하면 "0ms 로 두고 왜 안 보이냐" 는
  질문이 돌아온다.

---

## 2. BrowserSession 확장 (기존 수정)

**위치**: `backend/src/itb/execution/session.py`

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `pacing` | `RunPacing` | `NORMAL` | 이 세션의 현재 속도. 실행 중 변경 가능 (FR-103) |
| `_pause_requested` | `asyncio.Event` | clear | 일시정지가 **요청**되었다. 간격을 즉시 끊는 신호 (research R6) |

**`_pause_requested` 의 생애**

```
apply(PAUSE)                → set()      간격 대기가 즉시 반환한다
apply(RESUME) / apply(RUN_FROM) → clear()
mark_running()              → clear()
```

**왜 `_resume` 만으로 안 되는가**: `_resume` 은 일시정지에서 `clear()` 된다.
`asyncio.Event` 는 set 을 기다릴 수 있을 뿐 clear 를 기다릴 수 없다. 간격 도중 일시정지를
즉시 감지하려면 **set 되는 방향의 이벤트**가 따로 있어야 한다 (FR-106, SC-007).

두 이벤트는 항상 반대 상태다. 한곳(`apply`)에서만 조작해 어긋나지 않게 한다.

**불변식**
- `pacing` 변경은 브라우저에 아무 명령도 보내지 않는다 (원칙 III 계열).
- `pacing` 변경은 진행 중인 Step 을 끊지 않는다. 다음 경계부터 적용된다 (FR-103).

---

## 3. StepResult 확장 (기존 수정)

**위치**: `backend/src/itb/domain/run_result.py`

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `element_wait_ms` | `int` | 0 | 요소가 나타나기를 폴링하며 기다린 시간 (FR-114) |

**기존 필드와의 관계**

```
duration_ms  ─ Step 하나의 총 소요 (기존)
├── tab_wait_ms      탭이 열리기를 기다린 시간 (기존)
├── element_wait_ms  요소가 나타나기를 기다린 시간 (신규)
└── 나머지           동작 수행 시간
```

**불변식**
- `tab_wait_ms + element_wait_ms <= duration_ms`. 세 값은 하나의 Step 예산을 나눠 쓴다
  (FR-117).
- **간격은 여기에 포함되지 않는다** (FR-105). 간격은 Step 실행 밖의 시간이다.
- 성공한 Step 에도 기록된다. 실패했을 때만 남기면 "왜 이 Step 만 느린가" 를 볼 수 없다.

**기존 이름을 바꾸지 않는다**: `error_message`, `tab_wait_ms`, `locator_attempts` 는
001·002·003 의 화면과 검증이 읽는 이름이다. 더하기만 한다.

---

## 4. LocatorAttempt — 의미 확장 (기존, 스키마 불변)

**위치**: `backend/src/itb/domain/run_result.py`

필드는 그대로 두고 **기록 방식**만 바뀐다.

| 필드 | 기존 의미 | 신규 의미 |
|---|---|---|
| `waited_ms` | 최상위 후보만 0 이 아님 | **모든 후보**가 폴링에 참여한 총 시간을 갖는다 |
| `match_count` | 1라운드 시점의 값 | **마지막 라운드**의 값 |
| `matched` | `count()==1` | `count()==1` (변경 없음) |

**왜 스키마를 안 바꾸는가**: 결과 화면과 계약 테스트가 이미 이 형태를 읽는다. 폴링은
관측 횟수를 늘릴 뿐 관측 대상이 달라지지 않는다.

**추가되는 사실**: 마지막 라운드 값을 쓰므로, 실패 상세에서 "어떤 후보가 몇 개를
매칭했는지" 가 예산 소진 시점의 상태를 가리킨다. `ELEMENT_AMBIGUOUS` 실패에서 `count>1`
후보가 그대로 드러난다.

---

## 5. Preferences — 사용자 취향 (신규)

**위치**: `backend/src/itb/storage/preferences.py`
**파일**: `~/.config/itb/preferences.json`

```json
{
  "format_version": 1,
  "run_pacing": "normal"
}
```

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `format_version` | `int` | 1 | 형식 판별 |
| `run_pacing` | `RunPacing` | `normal` | 마지막에 고른 속도 (FR-109) |

**왜 `itb-project.yaml` 이 아닌가** (research R8): 속도는 보는 사람의 취향이지 프로젝트의
속성이 아니다. 프로젝트 파일에 넣으면 개인 취향이 팀 저장소에 커밋되고, 원칙 V 가 "사용자가
버전 관리하는 자산" 이라 부르는 트리를 오염시킨다.

**불변식**
- **취향만 담는다.** 자격 증명·경로·프로젝트 식별자를 넣지 않는다 (조직 보안 요건).
- 읽기 실패는 **실행을 막지 않는다.** 기본값으로 진행하고 사유를 경고로 알린다.
  `registry.py` 가 읽기 실패를 경고로만 처리하는 것과 같은 판단이다.
- 알 수 없는 `run_pacing` 값은 기본값으로 대체한다. 파일이 손으로 편집될 수 있다.
- 쓰기는 원자적이다 (`storage/atomic.py` 재사용). 부분 기록된 파일을 남기지 않는다.

---

## 6. ErrorCode 확장 (기존 수정)

**위치**: `backend/src/itb/domain/error.py`

| 코드 | 분류 | 언제 | 다음 행동 |
|---|---|---|---|
| `ELEMENT_NOT_READY` | `blocked` | 예산 안에 어느 후보도 `count()==1` 이 되지 않음 | 대기 예산을 늘리거나 실행 속도를 낮춰 화면을 확인 |
| `ELEMENT_AMBIGUOUS` | `blocked` | 예산 안에 `count()>1` 로만 매칭됨 | Step 상세에서 요소를 다시 집기 |

**기존 `STEP_FAILED` 와의 경계** (FR-120·FR-123)

```
사용할 수 있는 후보가 하나도 없다        → STEP_FAILED       정의 문제
예산 안에 아무도 1개를 매칭하지 못했다    → ELEMENT_NOT_READY  화면이 느린 문제
예산 안에 여러 개만 매칭했다             → ELEMENT_AMBIGUOUS  정의가 낡은 문제
```

분류가 셋 다 `blocked` 인 것은 의도적이다 — 세 경우 모두 사용자가 할 일이 있다. 구별은
`code` 와 `next_action` 이 한다. `category` 는 "내가 고칠 수 있는가" 에만 답한다 (003 EC-001).

**불변식**
- `category` 는 `CATEGORY` 대응표에서 파생된다. 호출부가 적지 않는다 (기존 규칙).
- 메시지에 내부 경로·스택을 넣지 않는다 (003 EC-005).

---

## 7. 상태 전이 — 변경 없음

**위치**: `backend/src/itb/execution/state_machine.py`

`한 스텝씩` 은 **새 상태를 만들지 않는다** (research R7). 매 Step 경계에서
`Command.PAUSE` 를 자동 적용해 기존 `PAUSED` 로 들어간다.

```
REPLAYING ──[Step 완료 + pacing.auto_pause]──▶ PAUSED
PAUSED    ──[사용자 계속하기]──────────────────▶ REPLAYING
```

두 전이 모두 전이표에 이미 있다. 파일을 수정하지 않는다.

**화면의 구별**: 사용자가 직접 누른 일시정지와 자동 일시정지는 `state` 가 같다. 화면은
**세션의 `pacing`** 으로 문구를 가른다 — `pacing == "step"` 이면 "한 스텝씩 — 다음 Step 을
기다립니다", 아니면 "일시정지됨".

**AI 세션**: `AI_RUNNING` 에서는 간격·자동 일시정지를 적용하지 않는다. AI 가 다음 동작을
판단하는 시간은 Step 실행이 아니다 (spec 엣지 케이스).

---

## 8. 대기 정책 상수 (신규 위치)

**위치**: `backend/src/itb/locator/strategy.py` — Runner 와 Generator 의 **공유 지점**

| 상수 | 사는 곳 | 값 | 근거 |
|---|---|---|---|
| `POLL_INTERVAL_MS` | `locator/strategy.py` (신규) | 100 | research R4 — 오버슈트 89ms, 라운드당 15ms |
| `DEFAULT_TIMEOUT_MS` | `domain/step.py` (기존, 값만 변경) | 5000 → 10000 | research R5 |

**왜 `POLL_INTERVAL_MS` 가 `strategy.py` 인가**: 이 모듈은 이미 우선순위 판단의 유일한
지점이며 순수하다 (`.importlinter` 의 `locator-strategy-is-pure` 계약). 대기 정책도
Runner 와 Generator 가 같은 값을 봐야 하므로 같은 자리에 둔다 (헌법 원칙 IV 후단, FR-118).

**왜 `DEFAULT_TIMEOUT_MS` 를 옮기지 않는가**: `.importlinter` 의 `domain-is-pure` 계약이
`itb.domain` → `itb.locator` 임포트를 **금지한다.** 상수를 `strategy.py` 로 옮기면
`step.py` 가 그것을 임포트해야 하므로 계약이 깨진다. 반대 방향은 이미 허용된다 —
`strategy.py` 가 `itb.domain.locator` 를 임포트하고 있다.

따라서 `DEFAULT_TIMEOUT_MS` 는 `domain/step.py` 에 그대로 두고, 필요한 쪽이 임포트한다.
**값은 한 곳에만 있다.** 생성기는 이미 `step.timeout_ms` 를 읽으므로 추가 배선이 없다.

---

## 요약: 무엇이 바뀌고 무엇이 안 바뀌는가

| | 바뀐다 | 바뀌지 않는다 |
|---|---|---|
| **Step DSL** | — | 종류·필드 전부 (원칙 I) |
| **Step 기본 예산** | 5000 → 10000ms | 상한 60000ms, Step 별 조정 |
| **우선순위 규칙** | — | `PRIORITY` 순서 전부 (원칙 IV) |
| **탐색 알고리즘** | 1회 확인 → 100ms 폴링, `.first` 폴백 제거 | 채택 기준 `count()==1` |
| **상태 기계** | — | 상태·전이 전부 (원칙 III) |
| **세션** | `pacing`, `_pause_requested` 추가 | 나머지 |
| **실행 결과** | `element_wait_ms` 추가 | 기존 필드 이름·의미 |
| **오류 코드** | 2종 추가 | 기존 코드·분류 규칙 |
| **저장 파일** | `~/.config/itb/preferences.json` 신규 | 테스트 자산·프로젝트 파일 |
