import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import i18n, { DEFAULT_LANGUAGE } from "../i18n";

afterEach(async () => {
  // Testing Library unmounts on its own only when Vitest's globals are on; they are off here.
  cleanup();
  // A test that stood in for fetch (the backend) leaves the real one behind.
  vi.unstubAllGlobals();
  // Every test starts in Vietnamese with nothing stored.
  await i18n.changeLanguage(DEFAULT_LANGUAGE);
  localStorage.clear();
});
