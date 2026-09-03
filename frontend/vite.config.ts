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
  },
});
