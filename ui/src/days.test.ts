import { describe, expect, it } from "vitest";
import { runDay } from "./days";

describe("runDay", () => {
  it("reads the day a run started", () => {
    expect(runDay({ started_at: "2026-10-15T05:50:02.120" })).toBe("2026-10-15");
  });
});
