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

### 언어모델 자격 증명 (US4~US6 을 손으로 써 볼 때만)

```bash
ant auth status        # 활성 프로필이 있으면 그대로 쓴다
ant auth login         # 또는 export ANTHROPIC_API_KEY=...
```

**키를 코드·설정 파일에 넣지 않는다** (FR-084). SDK 가 환경 변수 → 프로필 순으로 해석한다.

자동 테스트는 자격 증명을 쓰지 않는다 — `AuthoringAgent` 의 `driver` 자리에 대본대로 도구를
부르는 가짜 모델을 끼운다 (`backend/tests/us4_support.py`).

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
`itb.llm`·`itb.authoring`·`anthropic` 에 닿는 임포트가 생겼다는 뜻이다. 원칙 II 위반이므로
런타임 가드가 아니라 **임포트를 없애서** 고친다.

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
