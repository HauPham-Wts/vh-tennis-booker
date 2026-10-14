import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import i18n, { DEFAULT_LANGUAGE } from "../i18n";

afterEach(async () => {
  // Testing Library unmounts on its own only when Vitest's globals are on; they are off here.
  cleanup();
  // Every test starts in Vietnamese with nothing stored.
  await i18n.changeLanguage(DEFAULT_LANGUAGE);
  localStorage.clear();
});
