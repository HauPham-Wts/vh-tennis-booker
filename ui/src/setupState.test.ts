import { describe, expect, it } from "vitest";
import { autoLeft, setupDone, setupLeft } from "./setupState";
import { overview } from "./test/overview";

const ALL = { mumu: true, app: true, login: true };

describe("autoLeft", () => {
  it("keeps the items auto setup fixes, leaving out the user's own", () => {
    const summary = {
      checked_at: "2026-10-14T21:00:00.000",
      left: ["app_installed", "wake_timers", "mumu_screen"],
    };

    expect(autoLeft(summary)).toEqual(["mumu_screen", "wake_timers"]);
  });
});

describe("setupLeft", () => {
  it("counts the steps not ticked and an auto setup that never ran", () => {
    expect(setupLeft(overview({ setup: null }), { mumu: true, app: false, login: false })).toBe(3);
  });

  it("does not count an app auto setup could not see, once the user ticked it", () => {
    const status = overview({
      setup: { checked_at: "2026-10-14T21:00:00.000", left: ["app_installed"] },
    });

    expect(setupLeft(status, ALL)).toBe(0);
  });

  it("counts auto setup once, whatever it left", () => {
    const status = overview({
      setup: { checked_at: "2026-10-14T21:00:00.000", left: ["mumu_screen", "wake_timers"] },
    });

    expect(setupLeft(status, ALL)).toBe(1);
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
