/**
 * 개발 서버 프록시가 **세션 이벤트 WebSocket 을 통과시키는지** (UX U-01).
 *
 * 겪은 일: `/api` 프록시에 `ws` 옵션이 없고 `ws: true` 는 클라이언트가 쓰지 않는 `/ws`
 * 규칙에 붙어 있었다. 그래서 README 에 적힌 방법으로 띄우면 녹화한 Step 이 화면에
 * 하나도 나타나지 않았다 — 서버는 정상 기록 중이었다.
 *
 * 설정 파일과 접속 경로가 **서로 어긋나는 것**이 결함이었으므로 둘을 함께 읽어 대조한다.
 * 프록시를 실제로 태우는 검증은 자동 테스트의 몫이 아니다(개발 서버가 필요하다).
 */
import { describe, expect, it } from "vitest";

// 원문 그대로 읽는다. `?raw` 를 쓰는 것은 이 저장소의 방식이다 — node:fs 를 쓰면
// @types/node 가 필요해진다 (DesignTokens.test.tsx 와 같은 이유).
import config from "../vite.config.ts?raw";
import wsClient from "../src/api/ws.ts?raw";

describe("vite 개발 서버 프록시", () => {

  it("클라이언트는 /api 아래로 WebSocket 을 연다", () => {
    expect(wsClient).toMatch(/new WebSocket\(/);
    expect(wsClient).toMatch(/\/api\/sessions\/\$\{sessionId\}\/events/);
  });

  it("그 경로를 맡는 프록시 규칙이 WebSocket 을 통과시킨다", () => {
    const rule = config
      .split("\n")
      .find((line: string) => line.includes('"/api":'));
    expect(rule, '"/api" 프록시 규칙이 없다').toBeDefined();
    expect(rule).toMatch(/ws:\s*true/);
  });
});
