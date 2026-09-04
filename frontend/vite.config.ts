import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // 단독 로컬 도구 — 로컬 인터페이스에만 바인딩한다 (FR-088a).
    host: "127.0.0.1",
    port: 4310,
    proxy: {
      "/api": { target: "http://127.0.0.1:4320", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:4320", ws: true },
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
