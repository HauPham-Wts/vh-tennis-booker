import { describe, expect, it } from "vitest";
import { setupDone, setupLeft } from "./setupState";
import { overview } from "./test/overview";

const ALL = { mumu: true, app: true, login: true };

describe("setupLeft", () => {
  it("counts the steps not ticked", () => {
    expect(setupLeft({ mumu: true, app: false, login: false })).toBe(2);
    expect(setupLeft(ALL)).toBe(0);
  });
});

describe("setupDone", () => {
  it("needs the setup, a passed dry run and the schedule on", () => {
    const status = overview();

    expect(setupDone(status, ALL)).toBe(true);
    expect(setupDone(status, { ...ALL, login: false })).toBe(false);
    expect(setupDone({ ...status, schedule: { ...status.schedule, enabled: false } }, ALL)).toBe(
      false,
    );
    expect(
      setupDone({ ...status, schedule: { ...status.schedule, dry_run_passed: false } }, ALL),
    ).toBe(false);
  });
});
