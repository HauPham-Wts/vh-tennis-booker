import "@testing-library/jest-dom/vitest";
import "../i18n";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library unmounts on its own only when Vitest's globals are on; they are off here.
afterEach(cleanup);
