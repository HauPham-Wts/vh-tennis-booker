import { afterEach, describe, expect, it, vi } from "vitest";
import { overview } from "./test/overview";
import { isFirstOpen, markWelcomeShown, welcomeShown } from "./welcome";

/** The status of an app just installed: no dry run passed, the schedule off. */
function unused() {
  const status = overview();
  return overview({ schedule: { ...status.schedule, enabled: false, dry_run_passed: false } });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("isFirstOpen", () => {
  it("is true while no dry run has passed and the schedule is off", () => {
    expect(isFirstOpen(unused())).toBe(true);
  });

  it("is false once a dry run has passed or the schedule is on", () => {
    const status = unused();

    expect(isFirstOpen({ ...status, schedule: { ...status.schedule, dry_run_passed: true } })).toBe(
      false,
    );
    expect(isFirstOpen({ ...status, schedule: { ...status.schedule, enabled: true } })).toBe(false);
  });

  it("is false while a run goes on", () => {
    const running = { trigger: "dry_run", pid: 4242, since: "2026-10-15T09:12:00.000" };

    expect(isFirstOpen({ ...unused(), running })).toBe(false);
  });
});

describe("welcomeShown", () => {
  it("is false until the welcome screen is marked as shown", () => {
    expect(welcomeShown()).toBe(false);

    markWelcomeShown();

    expect(welcomeShown()).toBe(true);
  });

  it("counts blocked storage as shown, so the user is never sent back", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("Storage is blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Storage is blocked");
    });

    expect(() => markWelcomeShown()).not.toThrow();
    expect(welcomeShown()).toBe(true);
  });
});
