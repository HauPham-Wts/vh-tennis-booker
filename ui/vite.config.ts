import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Vitest blanks CSS imports, even `?raw` ones; the contrast test reads the tokens.
    css: { include: [/tokens\.css/] },
  },
});
