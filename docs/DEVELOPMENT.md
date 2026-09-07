# 개발 안내

`quickstart.md` §0 의 설치·실행 절차를 개발자 관점으로 정리한 문서다 (T153).
제품을 **검증**하는 절차는 `specs/001-interactive-ai-test-builder/quickstart.md` 가 갖고,
이 문서는 **개발할 때 반복하는 것들**을 갖는다.

## 확인된 환경

Python 3.13.0 (pyenv) · Node 23.7.0 / npm 10.9.2 · uv 0.9.7 · macOS 26.2 arm64

Playwright 1.62.0 이 Python 3.13 에서 정상 동작함을 실측했다 (research R1 검증 항목).
3.13 에서 설치가 깨지면 3.12 로 내리고 research.md R1 의 검증 항목을 갱신한다.

## 설치

```bash
cd backend && uv sync && uv run playwright install chromium
cd ../frontend && npm install
```

스키마 생성물은 **커밋 대상**이다 (헌법 Cross-language schema duty). 도메인 모델을 고쳤으면
다시 생성해서 함께 커밋한다.

```bash
cd backend && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
```

생성물을 갱신하지 않으면 `tests/contract/test_schema_drift.py` 가 실패한다. 그 테스트는
"손으로 타입을 만들기 시작하는 것" 을 막는 장치다.

## 실행

```bash
# 1) 검증용 대상 앱 (표준 라이브러리만 쓴다)
python fixtures/sample-app/serve.py --port 4300

# 2) 백엔드 — 로컬 인터페이스에만 바인딩한다 (FR-088a)
cd backend && uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320

# 3) 프론트엔드
cd frontend && npm run dev            # http://127.0.0.1:4310
```

브라우저는 **headed 로 뜬다.** 조작 국면(녹화·사람 인수)은 실제 창을 요구하고, 스크린캐스트는
headed 에서도 동작한다 (T006 실측). 모드를 하나로 유지하는 것이 의도된 설계다.

### 미리보기(미러)가 정적 화면에서도 나온다 (005)

CDP `Page.startScreencast` 는 **화면이 변할 때만** 프레임을 만든다. 그래서 미러에는 두 가지
장치가 있다 — 마지막 프레임 캐시(구독이 뒤늦게 붙어도 현재 화면을 준다)와 무프레임 감시
(마지막 프레임 후 2초 조용하면 스크린샷 한 장). **감시가 도는 것은 정상 동작이며 강등이
아니다** — `mirror_degraded` 를 발행하지 않는다.

이 장치가 없던 동안 정적 화면에서는 프레임이 한 장도 도달하지 않았다(실측 0건).

### 실행 결말은 네 값이다 (005)

`Outcome` 은 `pass · fail · stopped · partial_pass` 다.

| 값 | 언제 | 실패 집계 |
|---|---|---|
| `pass` | 실행 대상 Step 전부 통과 | 아니오 |
| `fail` | 실패 Step 이 있다 · 세션 유실 | 예 |
| `stopped` | 사용자가 중지를 요청했다 | **아니오** |
| `partial_pass` | 실패 Step 을 건너뛰고 나머지를 마쳤다 | 아니오 |

판정은 `itb.domain.run_result.decide_outcome()` **한 곳**이 한다. 화면·목록이 각자
`outcome == "fail"` 로 갈리면 결말이 늘 때 한 곳이 빠뜨린다.

`partial_pass` 라는 이름은 `RunScope.PARTIAL`(부분 실행 = 실행 **범위**)과 구별하기
위한 것이다. 결말과 범위는 다른 축이다 — Step 06~07 만 돌아 전부 통과하면 결말은 `pass`
이고 범위가 `partial` 이다.

**결말 값을 추가하면 스키마를 다시 생성해야 한다.** 순서는 아래를 지킨다.

```bash
cd backend && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
```

어기면 `tests/contract/test_schema_drift.py` 가 실패한다. 드리프트 검사는 **권위 정의에서
스키마 파일까지**만 본다 — 프론트 타입 생성물이 낡았는지는
`tests/contract/test_run_outcome_contract.py` 가 본다. 둘 다 있어야 양쪽 끝이 맞는다.

화면 쪽 어휘는 `frontend/src/lib/wording.ts` 한 곳에서 나온다. 결말 문장·칩·색 역할·
Step 번호 변환이 전부 여기 있고, **알 수 없는 값은 실패로 취급한다**(보수적 기본값) —
통과로 보이면 사용자가 확인하지 않고 넘어가기 때문이다. 사전 밖에서 어휘를 만들지
않는지는 `frontend/tests/OutcomeVocabulary.test.tsx` 와
`frontend/tests/StepNumberConsistency.test.tsx` 가 원문을 훑어 확인한다.

### 암호구로 잠근 비밀키

키 관리 화면에서 암호구를 걸어 키를 만들었으면, **백엔드를 다시 띄운 뒤에는 그 화면에서 잠금을
해제한다.** 암호구는 백엔드 프로세스 메모리에만 남으므로 재기동하면 다시 잠긴다. 잠긴 채로
실행하면 민감 변수를 쓰는 Step 이 "잠겨 있다" 는 사유와 함께 실패한다 (FR-089f).

사람이 없는 실행(CI·헤드리스)에서는 환경 변수로 공급한다. 셸 히스토리에 남지 않게 `read -rs` 로
받는다 — 값을 명령줄에 직접 적으면 히스토리와 프로세스 목록에 남는다.

```bash
cd backend
read -rs ITB_KEY_PASSPHRASE && export ITB_KEY_PASSPHRASE   # 입력 후 Enter (화면에 안 보임)
uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320
```

값 끝에 개행이 섞이면 열리지 않는다. `export ITB_KEY_PASSPHRASE="$(echo …)"` 같은 방식을 쓰지 않는
이유다. 암호구가 틀리면 기동은 되고 경고가 로그에 남는다 — 민감 변수를 쓰지 않는 테스트가 이것
때문에 막히면 안 되기 때문이다.

### 언어모델 자격 증명 (US4~US6 을 손으로 써 볼 때만)

```bash
ant auth status        # 활성 프로필이 있으면 그대로 쓴다
ant auth login         # 또는 export ANTHROPIC_API_KEY=...
```

**키를 코드·설정 파일에 넣지 않는다** (FR-084). SDK 가 환경 변수 → 프로필 순으로 해석한다.

자동 테스트는 자격 증명을 쓰지 않는다 — `AuthoringAgent` 의 `driver` 자리에 대본대로 도구를
부르는 가짜 모델을 끼운다 (`backend/tests/us4_support.py`).

### 키 없이 AI 경로를 눈으로 보기 (개발용, 선택)

API 키가 없어도 **이미 로그인된 Claude Code** 로 AI 작성 경로를 끝까지 돌려 볼 수 있다.
UX 워크스루에서 S6·S7 이 자격 증명 때문에 미검증으로 남는 것이 이 스위치가 있는 이유다.

```bash
uv sync --extra claude-code    # 선택 의존성. 한 번만
claude                          # 로그인돼 있는지 확인

cd backend
ITB_AI_DRIVER=claude-code uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320
```

| | 기본 (미설정) | `ITB_AI_DRIVER=claude-code` |
|---|---|---|
| 경로 | Messages API (`anthropic`) | 로그인된 Claude Code (`claude-agent-sdk`) |
| 자격 증명 | API 키 / `ant` 프로필 | `claude` 로그인 |
| 도구 | `build_tools` (`@beta_async_tool`) | `build_mcp_tools` (in-process MCP) |
| 모델·effort | `LlmConfig` 대로 | **Claude Code 기본값** (`config` 무시) |

**결과를 품질 근거로 쓰지 않는다.** `output_config.effort`·`betas`/`fallbacks`·
`stop_reason: "refusal"` 은 Messages API 전용이라 이 경로에서 전달되지 않고 모델도 다르다.
SC-002 같은 성공 기준 측정은 **기본 드라이버로만** 한다.

이 경로에서도 에이전트는 브라우저 도구 11종만 쓴다 — Claude Code 가 기본으로 주는
`Read`·`Write`·`Bash` 등은 권한 콜백이 거부한다 (FR-086,
`backend/src/itb/authoring/claude_code_driver.py`). `setting_sources=[]` 로 개발자의
`settings`·`CLAUDE.md`·훅도 읽지 않는다.

정확히 `claude-code` 한 값만 스위치를 켠다. 오타·대문자는 기본으로 떨어지며, 그것을
`backend/tests/unit/test_driver_selection.py` 가 고정한다. 테스트는 이 환경 변수를 항상
지우고 돌린다 (`backend/tests/conftest.py`).

## 저장된 테스트 편집 (006)

**편집 규칙의 구현은 한 곳이다** — `backend/src/itb/execution/step_edits.py`. 그 모듈은
Playwright 도 FastAPI 도 임포트하지 않는 순수 모듈이고, **호출자가 둘**이다.

| 경로 | 호출자 | 실행 위치 |
|---|---|---|
| 일시정지 세션 편집 | `api/routes/steps.py` (`/api/sessions/{id}/steps*`) | 세션의 현재 위치 |
| 저장된 정의 편집 | `api/routes/tests.py` (`PUT /api/tests/{id}/definition`) | 없음 → `0` 을 넘긴다 |

`current_step_index=0` 으로 부르면 "이미 실행된 구간을 고쳤다" 경고가 하나도 생기지 않는다.
그래서 정의 편집이 그 모듈을 **고치지 않고** 쓸 수 있다.

**세 번째 구현을 만들지 말 것.** 편집 조작이 필요하면 `step_edits` 에 인자를 더한다.
`backend/tests/unit/test_definition_edit_core.py` 가 그 구조를 테스트로 고정한다 —
두 번째 구현이 생기면 그 파일이 깨진다.

같은 이유로 변수 파생은 `domain/test_case.py` 의 `derive_variables()` 한 곳이다. 두 벌이면
한쪽에서 민감 표시가 비민감으로 강등되고, 재실행이 빈 값을 채운다 (조용한 실패다).

### 저장 요청은 편집 결과가 아니라 편집 연산 목록이다

```
PUT /api/tests/TC-001/definition
{ "revision": "<GET 이 준 지문>", "edits": [{"op": "update", "step_id": "step-02", "value": "operator"}] }
```

결과 전체를 받으면 "어느 Step 종류가 값을 갖는가" 같은 판정이 프론트로 넘어가고, 그것이
규칙의 두 번째 구현이 된다. 연산을 받으면 서버가 규칙의 주인으로 남는다.

`revision` 은 정의 파일 내용의 SHA-256 앞 16자다. 불일치면 `409 DEFINITION_STALE` 이고
응답에 현재 정의가 실린다 — 사용자가 편집기로 YAML 을 직접 고치는 것은 정상 사용이므로
(헌법 원칙 V) 실제로 일어난다. **강제 플래그는 없다**: 덮어쓰기는 응답이 준 새 `revision` 을
실어 다시 보내는 것이다. 플래그는 습관이 되고, 습관이 되면 감지가 무의미해진다.

### locator 후보는 편집할 수 없다

편집 요청 모델에 `target`·`css`·`test_id` 류 필드가 **아예 없다.** 후보는 살아 있는
페이지에서만 수집·검증되므로(원칙 IV), 손으로 넣은 값은 `verified` 를 얻을 수 없다.
`verified` 로 적으면 거짓말이고, 아니면 실행에 쓰이지 않는 조용한 무효 편집이다.

요소를 다시 집어야 하면 편집 화면의 「브라우저 열어 Step nn 에서 멈추기」를 쓴다 —
`POST /api/sessions` 에 `pause_before_index` 를 실으면 러너가 그 Step **직전**에서 기존
`PAUSED` 로 들어간다. 사용자가 달리는 실행을 「일시정지」로 잡을 필요가 없다.

## 검증

```bash
# ★ 헌법 원칙 II (NON-NEGOTIABLE). 이것이 실패하면 다른 검사는 의미가 없다
cd backend && uv run lint-imports

cd backend && uv run ruff check src/ tests/
cd backend && uv run pytest
cd backend && uv run python -m itb.schema.export --check
cd frontend && npx tsc --noEmit && npx vitest run
```

CI(`.github/workflows/ci.yml`)는 경계 검사 잡을 최우선으로 실행하고 실패하면 후속 잡을
돌리지 않는다.

### 테스트 계층

| 경로 | 무엇을 보는가 | 브라우저 |
|------|---------------|----------|
| `tests/unit/` | 순수 로직 — 도메인 불변식, 상태 기계, 후보 우선순위, 생성기, 시도 상한 | 없음 |
| `tests/contract/` | REST·WebSocket·DSL 계약, 스키마 드리프트 | 대부분 없음 |
| `tests/integration/` | 픽스처 앱 대상 실제 동작 — 녹화·재실행·일시정지·AI·비밀값 | 있음 |
| `tests/e2e/` | 사용자 스토리별 quickstart 절차 | 있음 |

전체 실행은 6분 안팎이다. 브라우저를 띄우지 않는 계층만 빠르게 돌리려면:

```bash
cd backend && uv run pytest tests/unit tests/contract -q      # 30초 안팎
```

### 테스트를 지우거나 건너뛰지 않는다

헌법 품질 게이트 4다. 깨진 테스트는 고치거나, 정말 낡았다면 **이유를 기록하고** 지운다.
`skip` 으로 덮으면 검증하지 않은 것이 통과로 보인다.

## 자주 겪는 문제

**녹화한 Step 의 후보가 전부 `not_collected` 로 나온다**
클릭이 화면 이동을 유발하면 후보 검증이 그 이동과 경쟁한다. CSS·testId 는 동작 시점에
페이지 안에서 검증하므로 영향을 받지 않지만(`recorder.js` 의 `statusOf`), `role`·`label`·
`text` 는 Playwright 로 검증하므로 놓칠 수 있다. 테스트에서는 사람처럼 조작한다 —
`us2_support.click_like_a_person` 이 마우스를 올려 두고 잠깐 기다린 뒤 누른다.

**통합 테스트가 "픽스처 앱이 뜨지 않았다" 로 실패한다**
`fixtures/sample-app/serve.py` 가 쓰는 포트가 막혔거나 파이썬 실행 파일이 다르다.
`conftest.py` 는 실패를 **건너뛰지 않고 명확한 사유로 실패시킨다** — 조용히 건너뛰면
검증하지 않은 것을 통과로 오인하기 때문이다.

**`lint-imports` 가 깨졌다**
`itb.execution`(또는 `storage`·`generator`·`locator`·`domain`·`mirror`·`recording`)에서
`itb.llm`·`itb.authoring`·`anthropic`·`claude_agent_sdk` 에 닿는 임포트가 생겼다는 뜻이다.
원칙 II 위반이므로 런타임 가드가 아니라 **임포트를 없애서** 고친다.

**AI 경로가 상한에 걸려 멈춘다**
도구 호출 40회, 동일 요소 연속 실패 3회가 상한이다 (FR-066). 상한 도달은 예외가 아니라
상태로 남고, 에이전트 루프가 매 턴 그 상태를 보고 끊는다 — SDK 가 도구 예외를 잡아 모델에게
돌려주므로 예외로는 루프를 끊을 수 없기 때문이다.

## 저장 레이아웃

```text
<프로젝트 디렉터리>/
├── itb-project.yaml      # 커밋 대상
├── tests/TC-001-*.yaml   # 커밋 대상 — 사용자 자산
├── secrets.local.yaml    # .gitignore 대상 (암호문)
└── .runs/                # .gitignore 대상 (실행 산출물)
```

키 쌍은 프로젝트 밖에 있다: `~/.config/itb/keys/`.

**실행 속도도 프로젝트 밖에 있다**: `~/.config/itb/preferences.json`. 속도는 보는 사람의
취향이지 프로젝트의 속성이 아니므로, 프로젝트 파일에 넣으면 개인 취향이 팀 저장소에
커밋된다. 파일이 없거나 깨져도 실행은 막히지 않는다 — 기본값(`보통`)으로 진행하고 사유를
경고로 알린다.

## 실행 속도 (004)

Step 사이에 사람이 따라올 시간을 준다. 네 단계이며 실행 중에도 바꿀 수 있다.

| 값 | 간격 | 쓰는 자리 |
|---|---|---|
| `fast` | 없음 | **무인 실행·CI.** 004 이전 동작이다 |
| `normal` | 500ms | 기본값 |
| `slow` | 1500ms | 화면 변화를 눈으로 확인할 때 |
| `step` | 자동 일시정지 | 한 Step 씩 확인하며 편집할 때 |

**무인 실행은 `fast` 를 명시해야 한다.** 저장된 취향이 CI 를 느리게 만들지 않는 유일한
방법이다.

```bash
curl -X POST http://127.0.0.1:4320/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"mode":"replay","test_id":"TC-001","pacing":"fast"}'
```

시간을 재는 테스트도 마찬가지다 — `tests/integration/test_performance.py` 의 오버헤드
측정이 `fast` 를 고정하는 이유가 그것이다. 간격은 일부러 준 시간이지 제품이 낭비한
시간이 아니다.

**속도는 저장된 테스트를 실행할 때만 걸린다.** AI 로 만드는 **중**에는 적용되지 않는다 —
작성 루프가 러너 태스크를 쓰지 않기 때문이다. AI 가 만든 테스트를 저장한 뒤 재실행하면
사람이 만든 테스트와 똑같이 적용된다.

## 지연 로딩 픽스처 (004)

로딩 중인 요소를 "없음" 으로 판정하던 결함(004 US2)을 재현하는 화면이다.

| 경로 | 지연 | 무엇을 재는가 |
|---|---|---|
| `/lazy.html?ms=2000` | 2000ms (기본) | 하위 후보로만 늦게 나타나는 요소를 기다리는가 |
| `/lazy.html` 로딩 중 | — | 같은 텍스트 스켈레톤 2개. 잘못된 요소를 잡지 않는가 |
| `/late-visible.html?ms=1000` | 1000ms | DOM 에 붙었지만 안 보이는 요소를 기다리는가 |

**`lazy.html` 의 2000ms 를 함부로 줄이지 말 것.** 옛 대기 예산(5000ms)보다도 작은데 004
이전 코드는 실패한다 — 결함이 예산 부족이 아니라 알고리즘 때문임을 이 값이 증명한다.
