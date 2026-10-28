import { describe, expect, it } from "vitest";
import type { Machine } from "./machines";
import type { ManualDone, ManualTicks } from "./manualSteps";
import { machineLeft, setupDone, setupLeft } from "./setupState";
import { overview } from "./test/overview";

const ALL = { mumu: true, app: true, login: true };

/** The ticks of the first machine alone, as before there could be more. */
function first(done: ManualDone): ManualTicks {
  return { first: done, machines: {} };
}

const TWO: Machine[] = [
  { place: 0, mumuIndex: 0, key: "", enabled: true },
  { place: 1, mumuIndex: 1, key: "1", enabled: true },
];
const SECOND_OFF: Machine[] = [TWO[0]!, { ...TWO[1]!, enabled: false }];

describe("setupLeft", () => {
  it("counts the steps not ticked", () => {
    expect(setupLeft(first({ mumu: true, app: false, login: false }))).toBe(2);
    expect(setupLeft(first(ALL))).toBe(0);
  });

  it("counts each machine's own steps, and MuMu once", () => {
    const ticks = { first: ALL, machines: { "1": { mumu: false, app: true, login: false } } };

    expect(setupLeft(ticks, TWO)).toBe(1);
    expect(setupLeft(first({ ...ALL, mumu: false }), TWO)).toBe(3);
  });

  it("leaves out a machine switched off", () => {
    expect(setupLeft(first(ALL), SECOND_OFF)).toBe(0);
  });
});

describe("machineLeft", () => {
  it("tells the machine that books with a step of its own left", () => {
    const ticks = first(ALL);

    expect(machineLeft(ticks, TWO[0]!)).toBe(false);
    expect(machineLeft(ticks, TWO[1]!)).toBe(true);
    expect(machineLeft(ticks, SECOND_OFF[1]!)).toBe(false);
    expect(machineLeft({ first: ALL, machines: { "1": ALL } }, TWO[1]!)).toBe(false);
  });
});

describe("setupDone", () => {
  it("needs the setup, a passed dry run and the schedule on", () => {
    const status = overview();

    expect(setupDone(status, first(ALL))).toBe(true);
    expect(setupDone(status, first({ ...ALL, login: false }))).toBe(false);
    expect(
      setupDone({ ...status, schedule: { ...status.schedule, enabled: false } }, first(ALL)),
    ).toBe(false);
    expect(
      setupDone({ ...status, schedule: { ...status.schedule, dry_run_passed: false } }, first(ALL)),
    ).toBe(false);
  });
});
