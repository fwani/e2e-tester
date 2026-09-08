# Phase 0 Research: Interactive AI Test Builder

**Feature**: `001-interactive-ai-test-builder` | **Date**: 2026-09-03
**Spec**: [spec.md](./spec.md) | **Constitution**: v1.0.0

확인된 개발 환경: Python 3.13.0 (pyenv) · Node 23.7.0 / npm 10.9.2 · uv 0.9.7 · macOS 26.2 arm64.
패키지 미설치 상태의 신규 프로젝트.

각 항목은 **Decision / Rationale / Alternatives considered / 검증 필요 사항** 순으로 기록한다.

> ## 실측 결과 (2026-09-03, T001~T010 수행 완료)
>
> 스파이크 8건을 실제로 설치·실행해 확인했다. 스크립트는 `scripts/spikes/` 에 있다.
>
> | # | 가정 | 결과 |
> |---|------|------|
> | R1 | Playwright for Python 이 Python 3.13 지원 | **성립** — playwright 1.62.0 / Python 3.13.0 정상. 강등 불필요 |
> | R1 | 장수명 `BrowserContext` 유지 | **성립** — 일시정지 25초 동안 CDP 연결·DOM·입력값·모달 상태 전부 보존, Resume 후 재시작 없이 이어서 실행 |
> | R1 | `context.on("page")` 가 두 새 탭 경로 모두 포착 | **성립** — `target="_blank"` 와 `window.open` 모두 발생. `page.on("popup")` 보완 불필요 |
> | R2 | 바인딩 유실 없음 / 발신 페이지 식별 | **성립** — 네비게이션 후 주입 유지, 새 탭 자동 주입, `source["page"]` 로 탭 구분 |
> | R2 | Shadow DOM `composedPath()` | **성립** |
> | R2 | `change`/`blur` 로 확정 값 1회 포착 | **부분 성립 → 설계 보강** — 둘이 **모두** 발생해 이벤트가 2건 온다. 같은 요소 기준 중복 제거가 필요하다 |
> | R3 | 스크린캐스트 프레임률 | **성립** — headed·headless 모두 **9.5~10 fps**, 1280×800 JPEG q60, 프레임당 ~17KB (R8 목표 5~10 fps 충족) |
> | R3 | 백그라운드 탭에서도 프레임 수신 | **성립 (중요)** — 앞에 없는 탭도 10 fps. 미러가 대상 탭을 따라갈 수 있다 |
> | R3 | ack 중단 시 실행 무영향 | **성립** — 3프레임 후 자연히 멈추고 예외 없음. FR-047b가 백프레셔로 공짜 달성 |
> | R3 | **창 최소화·가려짐 시 동작** | **미확인** — 프로그램으로 재현하지 못했다. 수동 확인 필요 |
> | R4 | `get_by_role(name=...)` 매칭 방식 | **가정과 다름 → 설계 변경** — 기본이 **부분 일치**다. `exact=True` 필수 |
> | R4 | `set_test_id_attribute` 위치 | **성립** — `playwright.selectors.set_test_id_attribute` |
> | R4 | 후보 즉시 `count()` 순회 비용 | **성립** — 5종 총 **5.1ms** |
> | R4 | 기록 시점 검증 가능 | **성립 + 모델 변경** — 후보가 **여러 요소를 매칭하는 경우**가 실측으로 나왔다. 상태 3값으로 표현 불가 → `ambiguous` 추가 |
> | R5 | Anthropic SDK 표면 | **성립** — `beta_async_tool` 존재, `tool_runner` 가 `fallbacks`·`betas`·`output_config` 직접 수용, httpx2 기반 |
> | R5 | **취소 반응 / `fallbacks="default"` 실동작** | **미확인** — 자격 증명 없음. Phase 6 에서 확인 |
> | R6 | 판별 유니온이 TS 판별 유니온으로 | **성립 + 설계 보강** — `extra="forbid"` 를 붙여야 `additionalProperties: false` 가 나가고 TS 인덱스 시그니처가 사라진다 |
> | R7 | PyNaCl 설치 / 공개키 봉인 | **성립** — 1.6.2 휠 설치, 공개키만으로 봉인·비밀키로 개봉 왕복 확인 |
>
> **설계가 바뀐 항목 4건**: R2(중복 제거 필요) · R4(`exact=True` 필수, `ambiguous` 상태 추가) ·
> R6(`extra="forbid"` 필수). 아래 각 절의 Decision 에 반영했다.
>
> **미확인으로 남은 항목 2건**: R3의 창 가려짐 동작, R5의 취소·폴백 실동작. 각 절에 기록했다.

"검증 필요 사항"은 구현 첫 작업에서 실제로 확인해야 하는 가정이다. 단정하지 않는다.

---

## R1. 상태 유지 브라우저 세션 (원칙 III의 핵심 제약)

### Decision

**Playwright `async_api`를 사용하고, 브라우저 수명을 HTTP 요청 수명에서 완전히 분리한 `SessionManager`
싱글턴이 소유한다.**

- `playwright.async_api.async_playwright().start()` 를 FastAPI lifespan 시작 시 1회 호출하고 앱 종료 시
  `stop()` 한다. `async with` 컨텍스트 매니저는 쓰지 않는다 — 블록을 벗어날 때 드라이버가 닫힌다.
- 세션 하나 = `Browser` 1개 + `BrowserContext` 1개 + **`Page` 여러 개**. `SessionManager`가 세션 ID로 보관한다.
- **탭 관리**: `BrowserContext` 하나가 여러 탭을 담는다. `context.on("page")` 로 새 탭을 감지해 열린 순서대로
  `tab_index` 를 부여하고 순서 목록으로 보관한다. `page.on("close")` 로 닫힘을 감지한다.
  활성 탭(`active_tab_index`)을 세션 상태로 들고 다닌다. 동시 탭 상한은 10 (FR-030g).
- 실행은 세션마다 하나의 `asyncio.Task`(러너 태스크)가 담당한다. HTTP 요청은 명령을 큐에 넣고 즉시 반환한다.
- **Pause 구현**: 러너 태스크가 `asyncio.Event` 를 `await` 한다. 브라우저에는 아무 명령도 보내지 않는다.
- **Resume 구현**: 그 Event 를 set 한다.

### Rationale

핵심 통찰은 **일시정지가 브라우저에 대한 조작이 아니라는 것**이다. 장수명 `BrowserContext`를 유지한 채
"명령 전송을 멈추는 것"만으로 인증 상태·화면 위치·입력 내용·페이지 내 JS 상태가 그대로 남는다.
따라서 FR-032(세션 종료 금지)와 FR-038(재시작 없이 이어서 실행)은 상태 저장·복원 로직이 아니라
**태스크 일시 중단**으로 달성된다. 원칙 III가 구현 가능한 이유가 여기에 있다.

`sync_api`는 배제한다. Playwright의 sync API는 asyncio 이벤트 루프 안에서 호출하면 오류를 낸다
(`It looks like you are using Playwright Sync API inside the asyncio loop`). FastAPI는 asyncio 기반이므로
sync API를 쓰려면 전용 스레드 또는 별도 프로세스와 큐 통신이 추가로 필요하다. 얻는 것이 없다.

**중요한 제약**: Playwright 객체는 생성된 이벤트 루프에 묶인다. 모든 Playwright 호출은 FastAPI 메인 루프에서
일어나야 한다. `run_in_threadpool` 로 감싸면 안 된다. 이는 코드 리뷰 항목으로 둔다.

브라우저는 `headless=False` 로 띄운다. clarify 결정 3(조작 국면 = 실제 창)이 실제 창을 요구하고,
스크린캐스트는 headed 모드에서도 동작하므로 MVP는 모드를 하나로 유지한다. headless 재실행은 P2(CI 연동)의
문제다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| `sync_api` + 전용 스레드 + 큐 | 이벤트 루프 충돌을 우회하려고 스레드 경계를 하나 더 만드는 것. 얻는 이점 없음 |
| 요청마다 브라우저 생성 | FR-032·FR-038 위반. Pause/Resume이 원리적으로 불가능 |
| 브라우저 상태 직렬화 후 복원 (`storage_state`) | 쿠키·localStorage만 복원한다. 화면 위치·DOM 상태·진행 중 입력은 복원되지 않아 FR-032를 만족하지 못한다 |
| 별도 워커 프로세스 | 단독 로컬 도구(FR-088)에 프로세스 경계를 추가할 이유가 없다. 디버깅만 어려워진다 |

### 검증 결과 (T001·T003·T005)

- ✅ **Playwright 1.62.0 이 Python 3.13.0 에서 정상 설치·동작한다.** 3.12 강등 불필요.
  `requires-python = ">=3.12"` 로 두어 3.12 도 허용한다.
- ✅ 장수명 `BrowserContext` 에서 일시정지 25초 동안 CDP 연결이 유지되고, DOM·입력값·모달 열림 상태가
  전부 보존됐다. Resume 후 브라우저 재시작 없이 이어서 실행됐다. (`scripts/spikes/spike_session.py`)
- ✅ `context.on("page")` 가 `target="_blank"` 와 `window.open` **양쪽 모두**에서 발생한다.
  `page.on("popup")` 보완이 필요하지 않다. 탭 닫힘은 `page.on("close")` 로 잡힌다.
  탭 번호 재사용 금지도 확인했다. (`scripts/spikes/spike_tabs.py`)
- ⚠️ 수십 분 규모 장시간 유지는 아직 확인하지 않았다. 25초 규모에서 문제가 없었으므로 위험도는 낮다고
  보되, 통합 테스트에서 더 긴 시간으로 다시 확인한다.

---

## R2. 사용자 조작 기록 (Recorder)

### Decision

**`BrowserContext.add_init_script()` 로 주입한 JS 리코더 + `BrowserContext.expose_binding()` 콜백 채널.**
이벤트는 **키 입력이 아니라 확정된 값**을 잡는다.

| 기록 대상 | 관찰 방법 |
|-----------|-----------|
| 클릭 | `document` 의 `click` 리스너 (capture 단계) |
| 입력 | `change` + `blur` 리스너. **`keydown`/`input` 은 쓰지 않는다.** 같은 요소 기준 중복 제거 필수 (실측 결과) |
| 선택 | `<select>` 의 `change` 리스너 |
| 화면 이동 | Python 측 `page.on("framenavigated")` (main frame) |

`add_init_script`는 모든 새 document·frame에서 실행되므로 화면 이동 후에도 리코더가 살아 있다.
`expose_binding`은 컨텍스트 단위로 등록해 모든 페이지·프레임에서 `window.__itbRecord(payload)` 를
호출할 수 있게 한다. 네비게이션 이전에 등록해야 한다.

**멀티 탭이 사실상 공짜로 따라온다.** `add_init_script` 와 `expose_binding` 을 **`Page` 가 아니라
`BrowserContext` 에 등록**했기 때문에, 이후 열리는 모든 탭에 리코더와 콜백 채널이 자동으로 주입된다.
탭별로 리코더를 다시 붙이는 코드가 필요 없다. 남는 일은 세 가지다.

| 할 일 | 방법 |
|-------|------|
| 새 탭에 참조 부여 | `context.on("page")` → 열린 순서로 `tab_index` 부여 |
| Step이 어느 탭인지 표시 | `expose_binding` 콜백의 `source` 인자에서 발신 `Page` 를 얻어 `tab_index` 로 변환 |
| 탭 닫기 기록 | `page.on("close")` → `close_tab` Step 기록 (FR-030c) |

`expose_binding` 콜백의 첫 인자(`source`)가 어느 페이지·프레임에서 왔는지 알려 준다는 점이 여기서 핵심이다.
페이지별로 별도 바인딩 이름을 만들 필요가 없다.

**새 탭 열림은 Step으로 기록하지 않는다** (FR-030b). 새 탭을 열게 한 클릭이 이미 Step이므로, 재실행하면
같은 클릭이 같은 탭을 다시 열게 된다. 열림을 별도 Step으로 만들면 같은 사건이 두 번 표현된다.

**재실행 시 탭 해석** (FR-030d): Step 실행 직전 `tab_index` 에 해당하는 `Page` 를 찾는다. 아직 없으면
`context.on("page")` 를 대기 시간 상한까지 기다린다. 상한 초과 시 "탭 N이 열리기를 기다렸으나 열리지
않았다"는 사유로 실패시킨다. 조작 국면이면 그 탭에 `page.bring_to_front()` 를 호출한다 (FR-030e).

### Rationale

**실측 보강 (T004)**: `change` 와 `blur` 가 **둘 다** 발생한다. 텍스트 입력 한 번이 이벤트 2건을 만든다.
따라서 `change`/`blur` 선택만으로 FR-025(연속 입력 병합)가 자동 충족되지는 않는다 —
**같은 요소를 대상으로 하는 연속된 입력 이벤트를 최종 값 하나로 접는 중복 제거가 필요하다.**
구현 규칙: 입력 이벤트를 받으면 Step 목록 끝(또는 삽입 위치)의 마지막 Step이 같은 요소·같은 종류인지
확인하고, 같으면 값을 갱신하고 새 Step을 만들지 않는다.

**입력을 `change`/`blur` 로 잡는 결정이 한글 IME 문제를 없앤다.** 키 입력 단위로 기록하면 조합 중인
자모(`ㅎ`, `하`, `한`)가 각각 이벤트로 들어와 조합 완료 값을 재구성해야 한다. `change`/`blur` 는
**조합이 끝난 최종 값**과 함께 한 번만 발생한다. 부수 효과로 FR-025(같은 필드 연속 입력을 최종 값 하나로
병합)가 별도 병합 로직 없이 만족된다. 요구사항 두 개가 이벤트 선택 하나로 해결된다.

**FR-023c(한글 IME·hover·드래그·파일 선택에서 조작 충실도 유지)는 아키텍처가 이미 보장한다.** clarify 결정 3
에 따라 사용자는 실제 브라우저 창을 조작하고 우리는 입력을 전달(forward)하지 않는다. 전달하지 않으므로
전달 과정에서 깨질 것이 없다. 이는 Recorder가 영리해서가 아니라 **입력 경로에서 제품을 빼냈기 때문**이다.
읽기 전용 미러(R3)를 택한 이유도 같다.

`framenavigated` 는 Python 측에서 듣는다. JS `beforeunload` 로 잡으면 페이지가 사라지는 중에 바인딩 호출이
유실될 수 있다.

**클릭으로 유발된 네비게이션 중복 제거**: 클릭 Step 기록 직후 짧은 시간창(기본 1000ms) 안에 발생한
`framenavigated` 는 별도 Step으로 만들지 않는다. 그렇지 않으면 링크 클릭 하나가 Step 두 개가 된다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| CDP `Input` 도메인 관찰 | CDP는 입력을 **주입**하는 도메인이지 사용자 입력을 관찰하는 이벤트를 주지 않는다. 원리적으로 불가 |
| `playwright codegen` 재사용 | Playwright 코드를 산출한다. 그것을 파싱해 Step 모델로 되돌리는 것은 원칙 I 위반(코드를 저장 형태로 취급) |
| `keydown`/`input` 이벤트 기록 | 한글 IME 조합 재구성 부담. 필드당 이벤트 수십 개. FR-025 병합 로직을 직접 짜야 한다 |
| 폴링으로 DOM diff 감시 | 무엇을 의도했는지 알 수 없다. 클릭 대상 요소를 특정할 수 없다 |

### 알려진 한계 (spec 엣지 케이스와 대응)

- **파일 선택 대화상자**: 사용자가 헤디드 브라우저에서 파일 입력을 직접 클릭하면 OS 네이티브 대화상자가
  열린다. Playwright의 `page.on("filechooser")` 는 Playwright가 클릭을 유발한 경우를 위한 것이므로,
  사용자 조작 경로에서는 신뢰할 수 없다. **MVP는 파일 입력을 감지해 Step을 만들되 파일 경로를 사용자가
  Step 편집기에서 지정하게 한다.** spec의 "운영체제 대화상자는 기록 대상이 아니다" 엣지 케이스에 대응한다.
- **탭 순서 의존**: 탭 참조를 열린 순서로 부여하므로, 재실행 시 탭이 다른 순서로 열리는 대상 앱에서는
  참조가 어긋난다. 이때 해당 Step이 실패로 드러나며 실패 메시지에 순서 불일치 가능성을 포함한다.
  URL 패턴으로 탭을 식별하는 보완 전략은 P2로 둔다 — 순서 방식으로 SC-012(실패율 10% 이하)를 달성하지
  못하는 것이 실측되면 그때 추가한다.
- **iframe**: init script는 모든 프레임에서 돈다. Step에 프레임 URL을 함께 기록하되 MVP 실행은 main frame만
  대상으로 하고, 하위 프레임에서 온 Step은 미지원으로 표시한다.

  **이 결정은 구현되지 않았다가 뒤늦게 고쳐졌다 (실측으로 드러난 결함).** `Step.frame_url` 필드는 있었지만
  채우는 코드도 읽는 코드도 없었고, 리코더는 `expose_binding` 의 `source["frame"]` 을 버리고 `source["page"]`
  만 썼다. 그래서 하위 프레임의 동작은 **미지원 표시 대신 조용히 깨진 Step**이 됐다 — 후보가 프레임 문서
  기준으로만 검증돼 `css: verified` 하나만 남고, 실행이 main frame을 뒤져 `ELEMENT_NOT_READY` 로 끝났다.
  녹화 화면에는 이상이 보이지 않으므로 사용자는 원인을 짚을 단서가 없었다.

  고친 뒤의 동작은 **미지원 표시가 아니라 실행 지원**이다.

  | 단계 | 무엇을 하는가 |
  |------|--------------|
  | 녹화 | `source["frame"]` 으로 그 문서에서 후보를 검증하고 `frame_url` 을 채운다. 녹화 경고로 알린다 |
  | 실행 | `itb.execution.frame_resolver` 가 `frame_url` 로 프레임을 찾아 그 안에서 요소를 찾는다 |
  | 내보내기 | `frameLocator('iframe[src*="<경로>"]')` 로 감싼다 — 표준 Playwright에 주소로 프레임을 잡는 locator가 없다 |

  남은 한계: 프레임 식별은 주소로만 한다. 같은 주소의 프레임이 둘이면 **채택하지 않고** 실패한다(잘못된
  프레임에서 통과하는 것이 실패보다 나쁘다). 주소의 쿼리·프래그먼트가 매번 달라지는 프레임은 그것을 뗀
  주소로 맞추되, 그렇게 맞춘 사실을 결과에 남긴다. 시작 화면의 iframe은 세션이 `install()` 보다 먼저
  주소를 열기 때문에 설치 시점에 **프레임마다** 스크립트를 다시 넣어야 한다 — main frame만 넣던 동안
  그 화면의 iframe에서 한 조작은 Step이 하나도 만들어지지 않았다.
- **Shadow DOM**: capture 단계 `click` 리스너에서 `event.composedPath()[0]` 을 대상 요소로 쓴다.

### 검증 결과 (T004)

`scripts/spikes/spike_binding.py` 로 확인했다.

- ✅ `add_init_script` 를 **컨텍스트에** 등록하면 네비게이션 후에도 주입이 유지된다.
- ✅ `expose_binding` 콜백이 유실 없이 도착한다 (총 15건 수신).
- ✅ 콜백의 `source["page"]` 로 발신 탭을 식별할 수 있다 — 멀티 탭 `tab_index` 변환의 전제가 성립한다.
  새 탭에도 리코더가 자동 주입됐다.
- ✅ Shadow DOM 요소를 `event.composedPath()[0]` 로 포착했다.
- ⚠️ **`change` 와 `blur` 가 모두 발생한다.** 위 Decision 에 중복 제거 규칙을 추가했다.

---

## R3. 관찰용 읽기 전용 미러 뷰

### Decision

**CDP `Page.startScreencast` 를 전용 CDP 세션에서 구동하고, 프레임을 WebSocket으로 프론트에 전달한다.**

- `context.new_cdp_session(page)` 로 **표시 중인 탭에 대해서만** 별도 CDP 세션을 만든다.
- `Page.startScreencast` 파라미터: `format="jpeg"`, `quality=60`, `maxWidth=1280`, `maxHeight=800`,
  `everyNthFrame=1`.
- `Page.screencastFrame` 이벤트를 받아 base64 프레임을 WebSocket으로 보내고 `Page.screencastFrameAck` 로
  확인한다.
- **미러 모듈은 CDP `Input` 도메인을 절대 호출하지 않는다.** FR-047a를 코드 구조로 보장한다.
- **WebSocket이 끊기면 ack를 멈추고 `Page.stopScreencast` 를 호출한다. 러너 태스크는 영향받지 않는다.**
  FR-047b.
- 폴백: 스크린캐스트를 시작할 수 없으면 1 fps `page.screenshot()` 으로 강등하고 사용자에게 알린다.
- **실측 확인**: 앞에 없는 백그라운드 탭에서도 프레임이 정상 수신된다. 미러가 현재 Step 대상 탭을
  따라가는 설계(FR-030f)가 성립한다.
- **멀티 탭**: 스크린캐스트는 **한 번에 한 탭만** 돌린다. 사용자가 미러에서 탭을 바꾸면 이전 탭에
  `Page.stopScreencast` 를 보내고 새 탭에 `Page.startScreencast` 를 시작한다 (FR-030f, FR-047c).
  실행 중에는 현재 Step이 대상으로 하는 탭을 자동으로 따라간다. 모든 탭을 동시에 스트리밍하지 않는다 —
  관찰 목적에 불필요한 대역폭이고, 프레임률 목표(R8)를 탭 수로 나누게 된다.

### Rationale

스크린캐스트는 **화면이 변할 때만** 프레임을 밀어 준다. 폴링이 아니므로 유휴 상태에서 비용이 0에 가깝다.
또한 `page.screenshot()` 과 달리 러너가 쓰는 `Page` 객체의 API를 경유하지 않으므로, 미러가 러너의 명령과
경쟁하지 않는다. 이 분리가 FR-047b(미러가 끊겨도 실행 무영향)를 구조적으로 만든다.

Chromium 전용 기능이지만 MVP는 Chromium만 지원하므로(spec Assumptions) 제약이 아니다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| 주기적 `page.screenshot()` | 매 호출이 프레임 캡처를 강제한다. 5 fps면 러너와 같은 Page 객체를 두고 경쟁한다. 유휴 상태에서도 비용이 든다 |
| 실제 브라우저 창을 화면 캡처 | OS 권한 필요. 창이 가려지면 못 찍는다. 이식성 없음 |
| Playwright `video` 녹화 | 파일로 떨어진다. 실시간 표시용이 아니다. 게다가 영상은 P2 |
| CDP `Page.captureScreenshot` 반복 | 스크린캐스트와 같은 일을 폴링으로 하는 것 |

### 검증 결과 (T006)

`scripts/spikes/spike_screencast.py` 로 실측했다.

| 조건 | 프레임률 | 프레임 크기 |
|------|----------|-------------|
| headless · 앞에 있는 탭 | 9.7 fps | 평균 17,226 B |
| headless · 백그라운드 탭 | 10.1 fps | 평균 16,836 B |
| headed · 앞에 있는 탭 | 9.5 fps | 평균 17,231 B |
| **headed · 백그라운드 탭** | **10.0 fps** | 평균 16,840 B |
| ack 없음 (WS 끊김 모사) | 3프레임 후 정지 | — |

- ✅ R8 목표(5~10 fps)를 충족한다. 대역폭은 약 170 KB/s — localhost 기준 문제없다.
- ✅ **백그라운드 탭에서도 프레임이 온다.** 이것이 확인되지 않았다면 미러가 대상 탭을 따라가는 설계를
  포기하고 "활성 탭만 표시"로 후퇴해야 했다.
- ✅ **ack 를 멈추면 3프레임 후 자연히 정지하고 예외가 발생하지 않는다.** FR-047b(미러 끊김이 실행에
  영향 없음)가 별도 처리 없이 CDP 의 백프레셔로 달성된다.
- ❌ **미확인: 창이 최소화·가려졌을 때의 동작.** 프로그램으로 창을 최소화할 수 없어 재현하지 못했다.
  백그라운드 탭이 정상 동작하므로 위험도는 낮다고 보되, **단정하지 않는다.** 개발 중 수동으로 확인하고
  멈춘다면 UI에 "창이 가려져 미러가 멈췄습니다"를 표시하는 처리를 추가한다.

---

## R4. Locator 후보 수집과 우선순위 해석 (원칙 IV)

### Decision

**순수 함수 `choose_strategy(target) -> LocatorStrategy` 하나를 Runner와 Generator가 공유한다.**
`LocatorStrategy` 는 실행 가능한 객체가 아니라 **의도의 표현**(종류 + 인자)이다.

```
LocatorStrategy(kind, args)
   ├─ Runner    → Playwright Locator 로 변환
   └─ Generator → Playwright 코드 문자열로 변환   (P2 Export)
```

후보 → Playwright 대응:

| 순위 | 후보 | Playwright 표현 |
|------|------|-----------------|
| 1 | testId | `page.get_by_test_id(v)` |
| 2 | role + accessible name | `page.get_by_role(role, name=n, exact=True)` — **`exact=True` 필수** (실측) |
| 3 | label | `page.get_by_label(v)` |
| 4 | text | `page.get_by_text(v, exact=True)` |
| 5 | 고정 속성 | `page.locator(f'[{attr}="{val}"]')` |
| 6 | CSS | `page.locator(css)` |

**testId 속성명은 프로젝트 설정으로 둔다.** Playwright 기본값은 `data-testid` 이며
`playwright.selectors.set_test_id_attribute(...)` 로 바꾼다. 대상 앱이 `data-test`, `data-cy` 등을 쓰는
경우가 흔하다.

**탭 대상**: `choose_strategy` 는 순수 함수이므로 탭을 알지 못한다. Runner가 Step의 `tab` 으로 대상
`Page` 를 먼저 해석한 뒤(R2 재실행 시 탭 해석), 그 `Page` 에 전략을 적용한다. Generator도 같은 전략에
탭별 페이지 변수를 붙인다. 탭 해석과 후보 해석을 분리해 두는 것이 `choose_strategy` 를 순수하게 유지하는
조건이다 — 여기에 탭 개념이 들어오면 Generator와 공유할 수 없다.

**해석 알고리즘** (Step 예산 = 기본 5000ms, **대상 탭 해석 시간을 제외한 나머지**):

1. 우선순위대로 각 후보에 대해 대기 없이 `count()` 를 확인한다 (즉시, 저렴).
2. 정확히 1개가 매칭되는 첫 후보를 채택한다.
3. 어느 후보도 즉시 매칭되지 않으면(요소가 늦게 나타날 수 있다) 최상위 후보에 남은 예산 전체를 걸고 기다린다.
4. 채택된 후보를 실행 결과에 기록한다.
5. **후보들이 서로 다른 요소를 가리키면 불일치를 실행 로그에 남긴다** (spec 엣지 케이스).

**수집 시점 검증 (record-time verification)**: 클릭을 기록한 직후, 수집한 각 후보가 **방금 클릭한 그 요소를
실제로 가리키는지** 확인해 후보별로 상태를 남긴다. 상태는 **4종**이다 (실측으로 `ambiguous` 가 추가됐다).

| 상태 | 의미 | 판정 |
|------|------|------|
| `verified` | 그 후보로 찾은 요소가 기록 대상 요소와 동일 | `count()==1` 이고 요소 동일 |
| `ambiguous` | 후보가 **여러 요소를 매칭한다** | `count()>1` |
| `unverified` | 1개를 매칭하지만 다른 요소를 가리킨다 | `count()==1` 이고 요소 다름 |
| `not_collected` | 후보 값을 확보하지 못했다 | 값 없음 또는 `count()==0` |

`ambiguous` 는 실행 시 어느 요소를 잡을지 알 수 없으므로 **사용 가능한 후보로 세지 않는다.**
실측에서 픽스처 앱의 "프로젝트 생성" 버튼에 대해 `text` 후보가 2개, `css` 후보가 3개를 매칭했다 —
이 구분이 없으면 두 후보를 확보된 것으로 오인해 SC-008 측정이 부풀려진다.

### Rationale

`choose_strategy` 를 순수 함수로 두는 것이 FR-022(제품 내 실행과 생성 코드의 해석 규칙 동일)와 원칙 IV를
**한 지점에서** 만족시키는 방법이다. Runner와 Generator가 각자 우선순위를 구현하면 두 곳이 반드시 갈라진다.

**수집 시점 검증이 이 설계에서 가장 값어치가 큰 결정이다.** 디자인 `StepInspector.dc.html` 은 후보별로
`사용 중` / `대체 1` / `대체 2` / `최후` / `수집되지 않음` 을 표시한다. 검증 없이는 이 표시가 추측이 된다.
검증하면 실제 데이터가 되고, SC-008(식별 후보 2개 이상 확보 Step 비율 90% 이상)을 **기록 시점에 측정할 수
있게** 된다 — 나중에 실행이 깨져서야 알게 되는 대신.

role과 accessible name은 주입한 JS에서 계산한다: 명시적 `role` 속성 → 태그별 기본 role 매핑,
name은 `aria-label` → `aria-labelledby` → 연결된 `<label>` → 텍스트 내용 → `alt` → `title` → `placeholder`
순으로 본다. CDP `Accessibility.getPartialAXTree` 가 더 권위 있지만 클릭마다 왕복이 필요하고, 위의 수집 시점
검증이 근사 계산의 오류를 잡아 주므로 근사로 충분하다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| Runner와 Generator가 각자 우선순위 구현 | FR-022 위반. 두 구현은 반드시 갈라진다 |
| CSS 셀렉터 하나만 저장 | FR-017 위반. 형제 요소 삽입만으로 깨진다 |
| 후보별로 동일한 짧은 타임아웃 부여 | 요소가 늦게 나타나는 경우 모든 후보가 함께 실패한다. 최상위 후보에 예산을 집중하는 것이 맞다 |
| CDP AX 트리로 매 클릭 role/name 계산 | 클릭마다 CDP 왕복. 수집 시점 검증이 있으면 이득이 근소하다 |

### 검증 결과 (T007)

`scripts/spikes/spike_locator.py` 로 확인했다.

- ❌ **가정과 달랐다: `get_by_role(name=...)` 의 이름 매칭은 기본이 부분 일치다.**
  픽스처 앱에서 `name="프로젝트"` 가 `"프로젝트 생성"` 버튼을 잡았다(count=1). `exact=True` 를 주면
  0개가 된다. **`exact=True` 를 반드시 붙인다.** 붙이지 않으면 대체 후보가 조용히 다른 요소를 잡아
  테스트가 잘못된 대상에 대해 통과할 수 있다 — 실패보다 나쁜 결과다.
- ✅ `set_test_id_attribute` 는 `Playwright` 인스턴스의 `selectors` 에 있다:
  `playwright.selectors.set_test_id_attribute("data-testid")`.
- ✅ 후보 5종 즉시 `count()` 순회 총 **5.1ms**. 해석 알고리즘 1단계의 "저렴하다"는 전제가 성립한다.
- ✅ 기록 시점 검증이 동작하며, **`ambiguous` 상태가 실제로 발생한다.** 위 Decision 에 4종 상태를
  반영했다. `data-model.md` §6 의 `Candidate.status` 와 spec FR-019a 도 함께 갱신했다.

---

## R5. 언어모델 제공자와 Browser Agent 구조 (원칙 II)

### Decision — 모델과 SDK

- **제공자**: Anthropic Claude API. **모델 ID: `claude-opus-5`** (컨텍스트 1M, 입력 $5 / 출력 $25 per 1M).
- **SDK**: 공식 `anthropic` Python SDK. FastAPI가 asyncio이므로 `anthropic.AsyncAnthropic()` 을 쓴다.
- **인증**: 인자 없는 생성자를 쓴다. SDK가 `ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` →
  `ant auth login` 프로필 순으로 자격 증명을 해석한다. **키를 코드에 넣지 않는다** (FR-084).
- **사고(thinking)**: Opus 5는 기본으로 adaptive thinking이 켜져 있다. `thinking` 파라미터를 생략한다.
  깊이는 `output_config={"effort": ...}` 로 조절한다. 브라우저 에이전트는 장기 도구 사용 작업이므로
  `effort="xhigh"` 를 기본으로 한다.
- **거부 폴백**: Opus 5는 `stop_reason: "refusal"` 을 낼 수 있다. `betas=["server-side-fallback-2026-07-01"]`
  + `fallbacks="default"` 를 기본으로 켠다. `content` 를 읽기 전에 `stop_reason` 을 항상 확인한다.
- **에이전트 루프**: `@beta_async_tool` 데코레이터로 브라우저 도구를 정의하고
  `client.beta.messages.tool_runner(...)` 를 `async for` 로 돈다. 루프를 직접 짜지 않는다.
- **주의**: `budget_tokens` 는 Opus 5에서 제거되었다(400). `temperature`/`top_p`/`top_k` 도 제거되었다.
  어시스턴트 프리필도 400을 낸다. 이 세 가지는 학습 시점 지식과 다르므로 리뷰 항목으로 둔다.
- `anthropic` 1.x 는 `httpx` 가 아니라 `httpx2` 기반이다. HTTP 관련 객체를 직접 다룰 때 주의한다.

**서버 도구는 쓰지 않는다.** 브라우저 도구는 전부 클라이언트 측 도구이므로 `pause_turn` 상황이 발생하지
않는다. Python tool runner가 `pause_turn` 을 자동 재개하지 못하는 알려진 함정을 회피한다.

### Decision — 에이전트 도구 표면

에이전트에게 주는 도구는 **Step 모델과 1:1 대응하는 것만** 둔다. 이것이 원칙 I을 에이전트 쪽에서 지키는
방법이다. 에이전트가 임의 JS를 실행할 수 있게 하면 그 동작은 Step으로 표현할 수 없고, 따라서 결정적 테스트로
컴파일할 수 없다.

| 도구 | 대응 Step | 비고 |
|------|-----------|------|
| `list_tabs()` | — | 열린 탭 목록(참조·제목·URL)과 활성 탭 반환. 읽기 전용 |
| `observe_page(tab)` | — | 지정 탭의 접근성 트리 요약 + 상호작용 가능 요소 목록. 읽기 전용 |
| `click(element_ref)` | click | 성공 시에만 Step 기록 |
| `fill(element_ref, value)` | fill | 민감 값은 변수 참조로 |
| `select(element_ref, value)` | select | |
| `navigate(url)` | navigate | |
| `assert_condition(kind, ...)` | assertion | FR-013a의 4종만 |
| `close_tab(tab)` | close_tab | FR-030c |
| `report_blocked(reason)` | — | 수행 불가 선언. FR-069의 실패 경로로 이어진다 |

도구는 모두 탭 인자를 받는다. 새 탭이 열리면 도구 결과에 "새 탭 N이 열렸다"를 덧붙여 에이전트가 알 수
있게 한다 — 에이전트가 탭 전환을 스스로 판단하려면 열림을 관측할 수 있어야 한다.

`element_ref` 는 `observe_page()` 가 부여한 안정적 참조다. 에이전트에게 CSS 셀렉터를 짜게 하지 않는다.
셀렉터를 짜게 하면 R4의 후보 수집을 건너뛰게 되어 원칙 IV가 무너진다. 도구 실행 시 실제 요소에서 후보를
수집하는 것은 **제품**이다.

**`execute_javascript` 도구는 두지 않는다.** 표현할 수 있는 Step이 없고, FR-086(브라우저 조작 범위를 넘는
동작 금지)에도 걸린다.

### Decision — 시도 상한 (FR-066)

**하드 루프 카운터를 1차 방어선으로 둔다.** 도구 호출 총 횟수 상한(기본 40회)과 동일 요소 대상 연속 실패
상한(기본 3회)을 제품 코드가 센다. 상한 도달 시 루프를 끊고 FR-069의 실패 경로로 넘긴다.

Task budget(`output_config.task_budget`, beta `task-budgets-2026-03-13`, 최소 20,000 토큰, 스트리밍 필요)은
모델이 스스로 페이스를 조절하게 하는 **권고적** 장치다. 하드 카운터를 대체하지 못한다. MVP는 하드 카운터만
구현하고 task budget은 후속 개선으로 둔다.

### Decision — 원칙 II 격리를 코드 구조로 강제

런타임 플래그가 아니라 **임포트 경계**로 막는다.

```
authoring/  ──임포트 허용──▶  llm/  ──▶  anthropic SDK
execution/  ──임포트 금지──▶  llm/          (도달 불가)
domain/     어느 쪽도 임포트하지 않음 (순수)
locator/    domain 만 임포트
```

**`import-linter` 로 CI에서 강제한다.** `forbidden` 계약을 선언한다:

```ini
[importlinter:contract:execution-no-llm]
name = execution must not reach the LLM boundary
type = forbidden
source_modules = itb.execution, itb.storage, itb.generator, itb.locator, itb.domain
forbidden_modules = itb.llm, itb.authoring, anthropic
```

이 계약이 깨지면 빌드가 실패한다. 사람의 주의력이 아니라 도구가 원칙 II를 지킨다.
추가로 SC-006(재실행 시 언어모델 호출 0건) 검증 테스트는 `anthropic` 클라이언트 생성 지점에 스파이를 심고
저장된 테스트를 실행해 호출이 0건임을 확인한다. 정적 검사와 동적 검사를 모두 둔다.

### Rationale

`claude-opus-5` 를 쓴다. 브라우저 에이전트는 화면을 보고 다음 동작을 정하는 장기 도구 사용 작업이고,
SC-002(자연어 변환 성공률 70% 이상)가 직접 모델 성능에 걸린다. 비용을 이유로 낮추는 것은 사용자 결정이며,
`effort` 를 낮추는 것이 모델을 내리는 것보다 먼저 시도할 조정이다.

Tool runner를 쓰는 이유는 루프를 직접 짜서 얻을 것이 없기 때문이다. 승인 게이트나 개입이 필요하면
`async for` 본문에서 처리할 수 있다 — AI 실패 시 사용자 선택지 제시(FR-070)가 정확히 그 지점이다.

도구 표면을 Step 모델과 1:1로 묶는 것이 이 설계의 중심이다. **에이전트가 할 수 있는 모든 일이 표현 가능한
Step이므로, "AI 결과를 결정적 Step으로 컴파일"(FR-061)이 별도의 변환 작업이 아니라 기록의 부산물이 된다.**
컴파일 단계에서 표현 불가능한 동작을 만나 실패하는 경우가 원리적으로 없다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| 런타임 플래그로 LLM 호출 차단 | 원칙 II가 감사 불가능해진다. 플래그를 잘못 세팅한 코드 경로 하나로 무너진다 |
| 에이전트에게 `execute_javascript` 제공 | 표현할 수 있는 Step이 없다. 컴파일 불가능한 동작이 생긴다. FR-086 위반 |
| 에이전트가 CSS 셀렉터 직접 작성 | R4의 후보 수집을 우회한다. 원칙 IV 무너짐. 생성된 테스트가 취약해진다 |
| 수동 에이전트 루프 직접 구현 | tool runner가 제공하는 것을 다시 만드는 것. 개입 지점은 runner로도 확보된다 |
| 로컬 모델(Ollama 등) | 작성 품질이 SC-002에 직결된다. 로컬 실행은 P2 이후 선택지 |
| 서버 도구(web_search 등) 사용 | 필요 없다. 게다가 Python tool runner의 `pause_turn` 미재개 함정에 노출된다 |

### 검증 결과 (T008 — 부분)

`scripts/spikes/spike_agent.py` 로 확인했다. **자격 증명이 없어 API 호출은 하지 않았다.**

- ✅ SDK 표면 확인: `anthropic` 1.3.0, `beta_tool`·`beta_async_tool`·`AsyncAnthropic` 존재.
- ✅ `client.beta.messages.tool_runner` 가 `model`·`max_tokens`·`tools`·`messages`·`output_config`·
  `betas`·`fallbacks`·`system` 을 **직접 받는다.** 거부 폴백과 effort 를 `extra_body` 없이 전달할 수 있다.
- ✅ `httpx2` 설치 확인 — anthropic 1.x 전제와 일치한다.
- ❌ **미확인: 장기 실행 중 취소 반응, `fallbacks="default"` 실동작.** 자격 증명이 필요하다.
  **Phase 6(US4) 시작 시 반드시 확인한다.** 취소가 깨끗하지 않으면 도구 함수 안에서 취소 신호를
  확인하는 방식으로 바꾼다. 이 미확인 항목은 Phase 0~3(녹화·기반)에는 영향이 없다.

---

## R6. Step DSL 스키마의 단일 정의 지점 (헌법 Cross-language schema duty)

### Decision

**Pydantic v2 모델을 권위 정의로 두고, JSON Schema를 내보내 TypeScript 타입을 생성한다.**

```
itb/domain/*.py  (Pydantic v2)          ← 권위 정의, 손으로 관리하는 유일한 곳
      │
      ├─ model_json_schema()  →  schema/step-dsl.schema.json
      │                                │
      │                                └─ json-schema-to-typescript
      │                                        → frontend/src/types/generated/step-dsl.d.ts
      │
      └─ 파일 입출력 검증 (FR-085), API 요청 검증
```

- **저장 형식은 YAML.** PRD §9의 예시가 YAML이고, 사람이 읽을 수 있어야 하며(FR-011) git diff가 의미 있게
  나와야 한다(FR-088b). 안전 로더만 사용한다.
- **모든 도메인 모델에 `model_config = ConfigDict(extra="forbid")` 를 붙인다** (실측으로 확정).
  이유가 둘이다: ① JSON Schema 에 `additionalProperties: false` 가 나가 TypeScript 생성 시
  `[k: string]: unknown` 인덱스 시그니처가 사라진다(없으면 필드명 오타가 타입 검사를 통과한다)
  ② 디스크의 테스트 정의 파일에서 **미지 필드를 거절**해 FR-085 경계 검증을 겸한다.
- **드리프트 방지**: CI 테스트가 스키마를 새로 생성해 커밋된 파일과 바이트 단위로 비교한다. 다르면 실패한다.
  생성물도 커밋한다 — 프론트 개발자가 Python 툴체인 없이 작업할 수 있어야 한다.

### Rationale

권위 정의는 **강제가 일어나는 곳**에 있어야 한다. 신뢰할 수 없는 입력(디스크의 테스트 정의 파일, API 요청,
자연어 입력)을 검증하는 주체는 백엔드다(FR-085). 스키마를 프론트에 두면 백엔드가 검증을 위해 스키마를
역으로 가져와야 하고, 그 경로가 끊기면 검증 없이 파일을 읽는 상태가 조용히 생긴다.

Pydantic v2는 표준 JSON Schema를 내보내므로 중간 포맷을 따로 정의할 필요가 없다. 생성물을 커밋하고 CI가
드리프트를 감시하는 방식은, 생성 단계를 잊었을 때 조용히 어긋나는 것을 막는다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| 양쪽에 손으로 스키마 유지 | 헌법 "두 개의 손으로 관리되는 스키마 복사본은 원칙 I 위반" 명문 위반 |
| Zod(TS)를 권위 정의로 | 백엔드가 검증 주체인데 정의가 프론트에 있게 된다. Python 생성기 품질도 반대 방향보다 못하다 |
| 독립 JSON Schema를 권위 정의로 | 손으로 쓰는 JSON Schema는 읽기·리팩터링이 어렵다. 양쪽 다 생성물이 되어 검증 코드가 생성 타입에 묶인다 |
| Protobuf / JSON Schema + 코드 생성 양방향 | 로컬 단독 도구에 IDL 툴체인을 도입할 이유가 없다 |
| 저장 형식을 JSON으로 | 사람이 읽기 어렵고 주석을 달 수 없다. PRD §9 예시와 어긋난다 |

### 검증 결과 (T009)

`scripts/spikes/spike_schema.py` + `json-schema-to-typescript@15` 로 확인했다.

- ✅ Pydantic v2 판별 유니온이 JSON Schema 에 `oneOf` + `discriminator{propertyName, mapping}` 로
  보존된다. 후처리 단계가 필요하지 않다.
- ✅ 생성된 TypeScript 가 `type X = ClickStep | FillStep | CloseTabStep` 유니온이고 각 멤버가 리터럴
  `type` 필드를 가지므로 TS 가 판별 유니온으로 좁힌다.
- ⚠️ **`extra="forbid"` 가 없으면** 생성된 인터페이스에 `[k: string]: unknown` 이 붙어 타입 안전성이
  사라진다. 붙이면 사라진다 — 실측으로 확인했다. 위 Decision 에 반영했다.

---

## R7. 민감 값 비대칭 암·복호화 (FR-089)

### Decision

**PyNaCl 의 `SealedBox`** (libsodium `crypto_box_seal`: X25519 + XSalsa20-Poly1305).

```python
# 쓰기 — 공개키만 필요 (녹화·작성 단계)
SealedBox(public_key).encrypt(value)

# 읽기 — 비밀키 필요 (실행 단계만)
SealedBox(private_key).decrypt(ciphertext)
```

- 키 위치: `~/.config/itb/keys/` — `private.key` (권한 `0600`), `public.key`.
- 선택적 암호구: `nacl.pwhash.argon2id` 로 키를 파생해 `SecretBox` 로 비밀키 파일을 감싼다 (FR-089e).
- 비밀 파일: 테스트 정의 옆 `secrets.local.yaml`. 변수명 → 암호문(base64) 맵. **공개키 지문을 함께 기록해**
  키가 교체되면 감지한다 (spec 엣지 케이스).
- 프로젝트 초기화 시 `.gitignore` 에 `secrets.local.yaml` 과 키 경로를 자동으로 넣는다.
- **로그 스크러버**: 복호화된 값들을 실행 컨텍스트에 보관하고, 실행 산출물(로그·실패 메시지·콘솔 기록·
  네트워크 기록)을 디스크에 쓰기 **직전에** 그 값들의 출현을 마스킹한다 (FR-089d).

### Rationale

`crypto_box_seal` 은 요구되는 모양과 **정확히 같다**: 익명 발신자가 수신자 공개키만으로 봉인하고, 수신자만
비밀키로 열 수 있다. 이것이 FR-089b(녹화·작성은 비밀키 없이 동작)를 라이브러리 선택 하나로 만족시킨다.

더 중요한 것은 **틀릴 여지가 없다는 점**이다. 모드·패딩·IV·데이터 키 래핑 같은 결정이 하나도 없고,
인증까지 포함되어 있다. 헌법이 요구한 "표준 라이브러리 수준의 검증된 방법, 직접 구현한 암호 방식 금지"에
가장 정직하게 부합한다.

**한 가지는 분명히 해 둔다**: 공개키와 비밀키가 같은 로컬 장비에 있으면 실질 보호 수준은 "비밀키 파일 하나를
지키는 것"과 같다. 그래도 이 방식이 값어치가 있는 이유는 ① 정의 파일과 비밀값이 물리적으로 분리되고
② 암호문은 그대로 커밋·공유해도 안전하며 ③ 작성 단계가 비밀키를 요구하지 않아 노출 면적이 실행 시점으로
좁혀지기 때문이다. 암호구 보호(FR-089e)는 비밀키 파일 자체가 유출되는 경우를 위한 층이다.

### Alternatives considered

| 대안 | 배제 이유 |
|------|-----------|
| `cryptography` RSA-OAEP + AES-GCM 데이터 키 래핑 | 키 크기·패딩·데이터 키 관리 결정이 늘어난다. 짧은 값 몇 개를 위해 하이브리드 구조를 직접 조립할 이유가 없다 |
| `age` / `rage` 바이너리 호출 | 외부 실행 파일 의존이 생긴다. 값 몇 개 암호화에 프로세스 실행 |
| OS 키체인 (macOS Keychain 등) | 비대칭 키 쌍 요구(사용자 결정)와 어긋난다. 플랫폼별 코드가 생기고 암호문을 이식할 수 없다 |
| 대칭 암호화(AES-GCM) + 단일 키 | 사용자가 비대칭 방식을 지정했다. 또한 작성 단계가 복호화 키를 갖게 되어 FR-089b의 이점이 사라진다 |
| 직접 구현 | 헌법 명문 금지 |

### 검증 결과 (T002)

- ✅ PyNaCl 1.6.2 가 Python 3.13.0 / macOS arm64 에서 **휠로 설치된다.** 소스 빌드 불필요.
- ✅ `SealedBox(public_key).encrypt(...)` → `SealedBox(private_key).decrypt(...)` 왕복 확인.
  **공개키만으로 봉인이 가능하다** — FR-089b(녹화·작성이 비밀키 없이 동작)의 전제가 성립한다.
- ⏳ 로그 스크러버의 형태 범위(부분 문자열·URL 인코딩·base64·JSON 이스케이프)는 T037 단위 테스트에서
  확인한다. 라이브러리 선택과 무관한 구현 사항이다.

---

## R8. 성능 목표 정량화 (clarify에서 이연된 항목)

측정 대상과 목표값을 확정한다. 모두 로컬 단독 도구 기준이며, 대상 앱의 응답 시간은 제외한 **제품이 추가하는
비용**을 본다.

| 항목 | 목표 | 근거 |
|------|------|------|
| Step 실행 제품 오버헤드 | p95 < 50 ms (요소 탐색·앱 응답 제외) | 디자인의 Step 소요 시간이 103~581 ms 범위. 제품 오버헤드가 그 10%를 넘으면 측정값이 왜곡된다 |
| Step 대기 시간 상한(기본값) | 5000 ms | `RunResult.dc.html` 의 `timeout 5000 ms` 표기 |
| 녹화 이벤트 → Step 목록 반영 | p95 < 200 ms | 사람이 즉시성으로 느끼는 임계. 이보다 느리면 녹화 중 무엇이 잡혔는지 확신할 수 없다 |
| 미러 뷰 프레임률 | 5~10 fps (JPEG q60, 최대 1280×800) | **실측 9.5~10 fps 달성** (T006). 관찰 목적이므로 높은 프레임률이 필요 없다 |
| 미러 뷰 프레임 지연 | p95 < 300 ms | 현재 실행 중인 Step과 화면이 어긋나 보이지 않을 정도 |
| 세션 시작 준비 시간 | < 2 s (브라우저 실행·첫 화면 로드 제외) | 테스트 만들기를 누르고 기다리는 체감 |
| Step 목록 UI 처리 규모 | Step 200개까지 지연 없이 | spec Assumptions의 "수십 개 규모" 에 여유를 둔 값 |
| 미러 끊김 시 실행 영향 | 0 | FR-047b. 목표가 아니라 요구사항 |
| 재실행 시 언어모델 호출 | 0건 | SC-006. 목표가 아니라 요구사항 |

**측정 방법**: Step 실행 오버헤드와 녹화 지연은 단위·통합 테스트에 계측을 넣어 회귀를 감시한다. 미러
프레임률·지연은 개발 중 수동 실측으로 확인하고 목표 미달 시 품질·해상도를 먼저 낮춘다.

---

## 결정 요약

| # | 항목 | 결정 |
|---|------|------|
| R1 | 브라우저 세션 | Playwright `async_api` + 장수명 `SessionManager`. 컨텍스트 1개에 탭 여러 개. Pause = `asyncio.Event` await |
| R2 | 사용자 조작 기록 | `add_init_script` + `expose_binding` **컨텍스트 단위 등록** → 멀티 탭 자동 지원. `change`/`blur` 로 확정값 포착 (IME 회피) + **같은 요소 중복 제거** |
| R3 | 미러 뷰 | CDP `Page.startScreencast` 전용 세션 → WebSocket. 한 번에 한 탭만. Input 도메인 미사용 |
| R4 | Locator | 순수 함수 `choose_strategy` 를 Runner·Generator 공유 + 수집 시점 후보 검증(4종 상태, `ambiguous` 포함) + **`exact=True` 필수** |
| R5 | LLM / Agent | `claude-opus-5` + `AsyncAnthropic` + tool runner. Step과 1:1 도구 표면. `import-linter` 로 원칙 II 강제 |
| R6 | DSL 스키마 | Pydantic v2(**`extra="forbid"`**) 권위 정의 → JSON Schema → TS 타입 생성. 저장은 YAML. CI 드리프트 검사 |
| R7 | 민감 값 | PyNaCl `SealedBox` (X25519). 별도 비밀 파일 + 로그 스크러버 |
| R8 | 성능 | Step 오버헤드 p95<50ms, 녹화 반영 p95<200ms, 미러 5~10fps / p95<300ms |

## 미해결 NEEDS CLARIFICATION

없다. spec 단계의 3건은 clarify에서 해소되었고, plan으로 이연된 2건(성능 목표, 언어모델 제공자)은 R8과 R5에서
결정되었다.

각 항목의 검증은 T001~T010 에서 **실제로 수행 완료**했다. 문서 머리의 실측 결과 표가 요약이다.

**남은 미확인 2건** — 둘 다 Phase 0~3 에 영향이 없다.

| 항목 | 미확인 이유 | 확인 시점 |
|------|-------------|-----------|
| R3 창 최소화·가려짐 시 스크린캐스트 동작 | 프로그램으로 창을 최소화할 수 없었다 | 개발 중 수동 확인 |
| R5 tool_runner 취소 반응, `fallbacks="default"` 실동작 | 언어모델 자격 증명 없음 | Phase 6 (US4) 시작 시 |
