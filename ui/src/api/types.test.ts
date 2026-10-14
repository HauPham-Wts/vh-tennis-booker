import { describe, expectTypeOf, it } from "vitest";
import type { Overview, Problem, RunSummary, SetupStatus, Step } from "./types";

// These checks run in `npm run typecheck`: a backend change that breaks them fails there.
describe("API types", () => {
  it("name the setup states", () => {
    expectTypeOf<SetupStatus>().toEqualTypeOf<"ok" | "fixed" | "fixable" | "user" | "unknown">();
  });

  it("describe an error as a code, a detail and optional problems", () => {
    expectTypeOf<Problem>().toEqualTypeOf<{
      error: string;
      detail: string;
      problems?: string[] | null;
    }>();
  });

  it("let the overview have no run, no last run and no setup yet", () => {
    expectTypeOf<Overview["running"]>().toBeNullable();
    expectTypeOf<Overview["last_run"]>().toEqualTypeOf<RunSummary | null>();
    expectTypeOf<Overview["setup"]>().toBeNullable();
  });

  it("give a step its values as an object", () => {
    expectTypeOf<Step["data"]>().toEqualTypeOf<Record<string, unknown>>();
  });
});
