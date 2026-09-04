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
| [`docs/design/`](docs/design/) | 확정 화면 디자인 8종 |
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
| 설정·키·프로젝트 목록 | `~/.config/itb/` |

프로젝트는 첫 화면에 자동으로 목록화된다. 다른 곳에 있는 프로젝트는 「기존 프로젝트
열기」로 찾아 열 수 있고, 한 번 열면 목록에 남는다.

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
