# Interface Contracts

`001-interactive-ai-test-builder` 가 외부에 노출하는 인터페이스 세 가지.

| 계약 | 파일 | 소비자 |
|------|------|--------|
| REST API | [rest-api.md](./rest-api.md) | React 프론트엔드 |
| WebSocket 이벤트 | [websocket.md](./websocket.md) | React 프론트엔드 |
| Test Step DSL | [step-dsl.md](./step-dsl.md) | **사용자** (git에 커밋되는 자산), 향후 Playwright Export |

## 경계 설계 원칙

**명령은 REST, 관찰은 WebSocket.** WebSocket은 서버 → 클라이언트 단방향으로만 쓴다. 클라이언트가
WebSocket으로 명령을 보내는 경로를 두지 않는다 — 같은 명령이 두 경로로 들어오면 검증과 권한 처리가
두 벌이 되고, 어느 쪽이 진실인지 모호해진다.

**단독 로컬 도구이므로 인증이 없다** (FR-088a). 대신 서비스는 로컬 인터페이스에만 바인딩하고 외부 네트워크에
노출하지 않는다. 이것이 인증을 두지 않는 전제이므로, 바인딩 주소를 넓히는 변경은 헌법 개정 사안이다.

**복호화된 민감 값을 반환하는 응답은 어떤 엔드포인트에도 없다** (FR-089d). 비밀 관련 엔드포인트는 변수
이름과 존재 여부만 다룬다.
