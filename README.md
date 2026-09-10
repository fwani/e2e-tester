# Interactive AI Test Builder

사람이 직접 하거나 AI에게 말해서 브라우저 테스트를 만들고, 실행 중 언제든 멈춰 수정한 뒤
이어서 완성하는 E2E 테스트 자동화 도구.

> Record it. Tell it. Fix it. Replay it.

**단독 로컬 도구**다. 사용자 1인이 자기 장비에서 실행하며 계정·인증·권한이 없다.
서비스는 로컬 인터페이스에만 바인딩한다.

## 현재 상태

MVP 개발 중. **사용자 스토리 7개(US1~US7)의 구현과 자동 검증을 마쳤다.** 남은 것은 자동
테스트로 대체할 수 없는 항목뿐이다 — 사람이 수행하는 수동 측정과 리뷰다.

| 증분 | 범위 | 상태 |
|------|------|------|
| 1 | 가정 검증 · 기반 · US1 직접 녹화 | **완료** |
| 2 | US2 재실행과 실패 진단 | **완료** |
| 3 | US3 Pause → Edit → Resume | **완료** |
| 4 | US4~US6 AI 작성·사람 인수·자연어 Step | **완료** |
| 5 | US7 Locator 진단 · 마감 | **완료** (수동 측정·리뷰 제외) |

### 결함 라운드

MVP 위에서 **이미 만든 것이 무너지는 지점**을 찾아 고치는 라운드를 둘 돌렸다.

| 라운드 | 다룬 것 | 상태 |
|--------|---------|------|
| [002](specs/002-defect-fix-design-conformance/) | 정상 경로의 결함과 확정 디자인 일치 | **완료** (리뷰어 판정 제외) |
| [003](specs/003-error-path-hardening/) | **이상 경로** — 이상 입력·순서 위반·외부 실패·동시 조작 | **완료** ([결과](specs/003-error-path-hardening/outcome.md)) |

003 은 오류가 **"제품이 막은 것"인지 "제품이 깨진 것"인지** 구분되지 않던 문제를 다뤘다.
분류(`category`)와 다음 행동(`next_action`)을 오류 계약에 넣고, 이상 조작 51건을 세 면
(요청 경계 19 · 화면 18 · 외부 경계 14)에서 판정 3축으로 펴 드러난 제품 결함 11건을 고쳤다.

이 라운드가 **제품 화면을 실제 브라우저로 띄우는 검증 계층**을 처음 만들었다 — 그전까지
이 저장소에는 제품 UI 를 실제로 여는 검증이 하나도 없었다. 앞으로 모든 화면 변경이 그
보호를 받는다.

**남은 항목** (사람이 해야 한다):

- quickstart §12 완료 체크리스트 실수행 (T154)
- SC-001·SC-002·SC-004·SC-005 수동 측정 세션 — 시나리오 20건 규모 (T155)
- `checklists/design-review.md` 리뷰어 검토 (T156)
- **릴리스 게이트 RG-1**: Playwright Export 구현 (P2). 생성기(`generator/playwright_gen.py`)는
  준비돼 있고 Export 명령만 남았다. **회수 전에는 출하할 수 없다** (헌법 Compliance review)

진행 상황은 `specs/001-interactive-ai-test-builder/tasks.md` 의 체크박스가 근거다.

## 문서

| 문서 | 내용 |
|------|------|
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | 프로젝트 헌법 v1.1.0. 원칙 I·II는 NON-NEGOTIABLE |
| [`docs/prd.md`](docs/prd.md) | 제품 요구사항 정의서 |
| [`docs/design/008-visual-language/`](docs/design/008-visual-language/) | 화면 디자인 18종 + 시각 언어 v2「계기판」. **대조 기준은 여기 하나다** |
| [`docs/design/_retired/`](docs/design/_retired/) | 폐기된 v1 디자인 (2026-09-08). 기준이 아니다 — 과거 대조 판정을 읽기 위해서만 남긴다 |
| [`specs/001-interactive-ai-test-builder/spec.md`](specs/001-interactive-ai-test-builder/spec.md) | 기능 명세 (FR 136 / SC 12 / US 7) |
| [`.../research.md`](specs/001-interactive-ai-test-builder/research.md) | 기술 결정 R1~R8 + 실측 결과 |
| [`.../data-model.md`](specs/001-interactive-ai-test-builder/data-model.md) | 엔티티·상태 기계·불변식 |
| [`.../contracts/`](specs/001-interactive-ai-test-builder/contracts/) | REST · WebSocket · **Test Step DSL** |
| [`.../quickstart.md`](specs/001-interactive-ai-test-builder/quickstart.md) | 검증 절차 |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | 개발 환경·검증 명령·자주 겪는 문제 |

**`contracts/step-dsl.md` 가 사용자에게 가장 중요한 계약이다.** 제품 UI나 API는 바뀔 수 있지만
그 형식으로 저장된 테스트는 사용자가 git에 커밋해 보관하는 자산이다.

## 설치

```bash
# 백엔드
cd backend && uv sync && uv run playwright install chromium

# 프론트엔드
cd frontend && npm install

# 스키마 생성물 최신화 (헌법 Cross-language schema duty)
cd backend && uv run python -m itb.schema.export
cd ../frontend && npm run gen:types
```

확인된 환경: Python 3.13.0 · Node 23.7.0 · uv 0.9.7 · macOS 26.2 arm64.
Playwright 1.62.0 이 Python 3.13 에서 정상 동작함을 실측했다.

## 저장 위치

서버를 **어느 디렉터리에서 띄우든 상관없다.** 도구가 위치를 알고 있다.

| 대상 | 위치 |
|---|---|
| 프로젝트 (테스트 정의 YAML) | `~/.local/share/itb/projects/<프로젝트>/` |
| 삭제한 프로젝트·테스트 (휴지통) | `~/.local/share/itb/trash/<삭제시각>-<이름>/` |
| 설정·키·프로젝트 목록 | `~/.config/itb/` |

프로젝트는 첫 화면에 자동으로 목록화된다. 다른 곳에 있는 프로젝트는 「기존 프로젝트
열기」로 찾아 열 수 있고, 한 번 열면 목록에 남는다.

### 이름 바꾸기와 삭제

첫 화면 목록의 각 줄에서 한다.

- **이름 바꾸기** — 표시 이름만 바뀐다. 폴더 경로와 테스트 파일은 그대로이므로 git 이력과
  열려 있는 브라우저 세션에 영향이 없다. 확인 절차 없이 그 자리에서 고친다.
- **삭제** — 프로젝트 폴더를 **휴지통으로 옮긴다.** 지우지 않는다. 옮긴 위치를 화면이
  알려 주므로, 되돌리려면 그 폴더를 `~/.local/share/itb/projects/` 로 옮기면 된다.
- **목록에서 치우기** — 목록에서만 뺀다. 디스크의 파일은 그대로다. 관리 위치에 실재하는
  프로젝트는 다음 조회에서 다시 나타난다 (목록이 폴더 스캔 ∪ 기록의 합집합이기 때문이다).

**도구는 휴지통을 자동으로 비우지 않는다.** 사용자 자산을 예고 없이 파괴하지 않기
위해서다. 디스크가 아깝다면 `~/.local/share/itb/trash/` 를 직접 지우면 된다. 도구 안에는
복구 화면이 없으므로 되돌리기는 파일 탐색기로 한다.

## 테스트 그룹

한 프로젝트 안에서 테스트를 묶는다. **그룹은 선택 사항이다** — 만들지 않으면 목록은 지금과
같은 모습이고, 테스트 식별자도 `TC-001` 그대로다.

그룹은 **보이는 이름**과 **식별자 접두어**를 따로 갖는다.

| | 예 | 쓰이는 곳 |
|---|---|---|
| 이름 | `사용자관리 테스트` | 목록의 그룹 띠와 소제목 |
| 접두어 | `USER` | 테스트 식별자 (`USER-001`), 파일 이름, 실행 산출물 디렉터리 |

이름에서 접두어를 자동으로 뽑지 않는 이유는 이름이 한글일 수 있기 때문이다 — 그대로 쓰면
식별자가 길어지고, 로마자로 바꾸면 예측할 수 없는 값이 나온다.

- **접두어는 영문 대문자·숫자 1~8자**이고 첫 글자는 영문이다. 식별자가 파일 이름이 되고,
  macOS 기본 파일 시스템은 대소문자를 구별하지 않으므로 한 가지로 고정한다.
- **`TC` 는 예약**이다. 그룹 없는 테스트가 쓴다.
- **번호는 프로젝트 전체에서 고유**하다. 그룹을 옮기면 접두어만 바뀌고 번호는 그대로다
  (`USER-003` → `DATA-003`).

### 그룹을 옮기면 파일이 움직인다

그룹 변경은 표시를 고치는 것이 아니라 **자산을 옮기는 조작**이다.

```
tests/USER-003-로그인.yaml   →  tests/DATA-003-로그인.yaml
.runs/USER-003/              →  .runs/DATA-003/
```

버전 관리에서는 파일 이름 변경으로 보인다. 실행 중인 테스트는 옮길 수 없다.

**그룹을 없애도 테스트는 지워지지 않는다.** 그 안의 테스트가 전부 `TC-###` 로 돌아간다 —
묶음을 푸는 것과 자산을 지우는 것은 다른 조작이다.

## 테스트 삭제

목록에서 한 개씩, 또는 체크해서 여러 개를 한 번에 지운다. **삭제는 휴지통으로 옮기는
것이다** — 개수와 무관하게 결과가 같다.

```
~/.local/share/itb/trash/<삭제시각>-<식별자>-<이름>/
├── <식별자>-<이름>.yaml   ← 정의. 원래 파일명 그대로
└── runs/                  ← 실행 산출물 (있을 때만)
```

되돌리려면 그 `.yaml` 을 프로젝트의 `tests/` 로 옮기면 된다. 실행 산출물까지 되살리려면
`runs/` 를 `.runs/<식별자>/` 로 옮긴다.

**여러 개를 지울 때는 전부 되거나 전부 안 된다.** 하나라도 실행 중이거나 옮길 수 없으면
아무것도 지워지지 않는다.

테스트 정의는 프로젝트 폴더의 `tests/` 에 평문 YAML 로 저장되므로 그대로 버전 관리에
넣을 수 있다. 비밀 값과 실행 산출물은 `.gitignore` 로 제외된다.

## 실행

```bash
# 검증용 대상 앱
python fixtures/sample-app/serve.py --port 4300

# 백엔드 (로컬 인터페이스 전용)
cd backend && uv run itb          # 또는: uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320

# 프론트엔드
cd frontend && npm run dev     # http://127.0.0.1:4310
```

## 검증

```bash
# ★ 헌법 원칙 II (NON-NEGOTIABLE) — 이것이 실패하면 다른 검사는 의미가 없다
cd backend && uv run lint-imports

cd backend && uv run ruff check src/ tests/
cd backend && uv run pytest
cd backend && uv run python -m itb.schema.export --check   # 스키마 드리프트
cd frontend && npx tsc --noEmit && npm test -- --run
```

CI(`.github/workflows/ci.yml`)는 `constitution-boundaries` 잡을 최우선으로 실행하고,
실패하면 후속 잡을 돌리지 않는다.

## 아키텍처 경계 (헌법 원칙 II, 이연 불가)

```text
domain      순수. 아무것도 임포트하지 않는다 (playwright·fastapi 포함)
locator     domain 만 임포트. strategy 는 프레임워크 없이 유지 — Generator 와 공유해야 한다
execution  ─┐
storage     │  itb.llm · itb.authoring · anthropic 을 임포트할 수 없다
generator   │  (.importlinter 의 execution-no-llm 계약이 CI 에서 강제)
recording   │
mirror     ─┘
authoring   llm 임포트 허용 (작성 단계 전용)
llm         Anthropic SDK 와의 유일한 접점
```

저장된 테스트를 재실행할 때 언어모델 호출이 **코드 구조상 도달 불가능**하다. 런타임 플래그가
아니라 임포트 경계로 막으며, 도구가 이를 검사한다.
