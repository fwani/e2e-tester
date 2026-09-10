import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 기본값은 제품이 쓰는 포트다. 검증이 제품 서버를 빈 포트에 띄울 때만 다른 값을 넘긴다 —
// 개발용 제품이 떠 있어도 화면 검증을 돌릴 수 있어야 한다 (003 RG-105).
const apiPort = Number(process.env.ITB_API_PORT ?? 4320);

export default defineConfig({
  // Tailwind v4 는 PostCSS 체인 없이 Vite 플러그인으로 붙는다 (015 research R1).
  // 이 저장소에 없던 postcss 설정을 새로 들이지 않기 위한 선택이다.
  plugins: [tailwindcss(), react()],
  server: {
    // 단독 로컬 도구 — 로컬 인터페이스에만 바인딩한다 (FR-088a).
    host: "127.0.0.1",
    port: Number(process.env.ITB_UI_PORT ?? 4310),
    proxy: {
      // WebSocket 도 이 규칙을 탄다 — 세션 이벤트 경로가 `/api/sessions/{sid}/events` 다
      // (contracts/websocket.md T160: 전송 방식을 리소스 이름에 섞지 않는다). `ws` 를 빼면
      // 업그레이드 요청이 프록시에서 멎고, 화면은 녹화한 Step 을 하나도 받지 못한다.
      "/api": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: true, ws: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/**/*.test.{ts,tsx}"],
    // 기본값은 CSS 임포트를 빈 값으로 바꾼다. 그러면 DesignTokens.test.tsx 의
    // "border-radius 가 없다" 류 단언이 **빈 문자열을 상대로 통과한다** — 가드가
    // 조용히 가드를 멈춘다. 원문을 실제로 읽어야 대조가 성립한다 (DC-004).
    css: true,
  },
});
