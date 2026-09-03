# itb — Interactive AI Test Builder (backend)

브라우저 기반 E2E 테스트 자동화 도구의 백엔드. 단독 로컬 도구로 동작하며 로컬 인터페이스에만
바인딩한다.

- 명세: `../specs/001-interactive-ai-test-builder/`
- 헌법: `../.specify/memory/constitution.md`
- 개발 절차: `../specs/001-interactive-ai-test-builder/quickstart.md`

## 아키텍처 경계 (헌법 원칙 II, NON-NEGOTIABLE)

`itb.execution` · `itb.storage` · `itb.generator` · `itb.locator` · `itb.domain` 에서
`itb.llm` · `itb.authoring` · `anthropic` 을 임포트할 수 없다. `.importlinter` 계약으로 강제하며
CI가 `lint-imports` 를 다른 검사보다 먼저 실행한다.
