import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 기본값은 제품이 쓰는 포트다. 검증이 제품 서버를 빈 포트에 띄울 때만 다른 값을 넘긴다 —
// 개발용 제품이 떠 있어도 화면 검증을 돌릴 수 있어야 한다 (003 RG-105).
const apiPort = Number(process.env.ITB_API_PORT ?? 4320);

export default defineConfig({
  plugins: [react()],
  server: {
    // 단독 로컬 도구 — 로컬 인터페이스에만 바인딩한다 (FR-088a).
    host: "127.0.0.1",
    port: Number(process.env.ITB_UI_PORT ?? 4310),
    proxy: {
      "/api": { target: `http://127.0.0.1:${apiPort}`, changeOrigin: true },
      "/ws": { target: `ws://127.0.0.1:${apiPort}`, ws: true },
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
