import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/** `court-booker serve` listens here; the dev and preview servers forward /api to it. */
const BACKEND = "http://127.0.0.1:8765";
const proxy = { "/api": { target: BACKEND, ws: true } };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Vitest blanks CSS imports, even `?raw` ones; the contrast test reads the tokens.
    css: { include: [/tokens\.css/] },
  },
});
