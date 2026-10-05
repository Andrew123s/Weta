import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The dev server proxies /api to the FastAPI process (docs/deployment.md section 3).
const API_TARGET = process.env.WETA_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": { target: API_TARGET, changeOrigin: false } },
  },
  build: { sourcemap: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
