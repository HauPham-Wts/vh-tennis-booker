import { describe, expect, it } from "vitest";
import { step } from "../../test/liveSocket";
import { progressOf } from "./progress";

const SLOTS = ["15:00 - 16:00", "16:00 - 17:00"];

const STARTED = step(1, { kind: "run_started", data: { slots: SLOTS, dry_run: false } });
const BOOKING = step(2, {
  kind: "booking_started",
  data: { date: "2026-10-17", court: "S6 - Sân tennis" },
});
const FIRST = step(3, { kind: "slot_started", data: { slot: SLOTS[0], round: 1, rounds: 2 } });
const FIRST_BOOKED = step(4, { kind: "slot_booked", data: { slot: SLOTS[0], seconds: 6 } });
const SECOND = step(5, { kind: "slot_started", data: { slot: SLOTS[1], round: 2, rounds: 2 } });
const SECOND_FAILED = step(6, { kind: "slot_failed", data: { slot: SLOTS[1], reason: "x" } });
const FINISHED = step(7, { kind: "run_finished", data: { status: "partial" } });

const states = (steps: Parameters<typeof progressOf>[0]) =>
  progressOf(steps).states.map(({ state }) => state);

describe("progressOf", () => {
  it("knows the slots to try before booking starts", () => {
    const progress = progressOf([STARTED]);

    expect(progress.slots).toEqual(SLOTS);
    expect(progress.date).toBeUndefined();
    expect(progress.current).toBeUndefined();
    expect(states([STARTED])).toEqual(["pending", "pending"]);
  });

  it("follows each slot from current to booked or failed", () => {
    expect(states([STARTED, BOOKING, FIRST])).toEqual(["current", "pending"]);
    expect(states([STARTED, BOOKING, FIRST, FIRST_BOOKED])).toEqual(["booked", "pending"]);
    expect(states([STARTED, BOOKING, FIRST, FIRST_BOOKED, SECOND])).toEqual(["booked", "current"]);
    expect(progressOf([STARTED, BOOKING, FIRST]).waiting).toEqual([SLOTS[1]]);
    expect(progressOf([STARTED, BOOKING, FIRST, FIRST_BOOKED, SECOND]).waiting).toEqual([]);
    const all = [STARTED, BOOKING, FIRST, FIRST_BOOKED, SECOND, SECOND_FAILED, FINISHED];
    expect(states(all)).toEqual(["booked", "failed"]);

    const progress = progressOf(all);
    expect(progress.booked).toBe(1);
    expect(progress.finished).toBe(true);
    expect(progress.date).toBe("2026-10-17");
    expect(progress.court).toBe("S6 - Sân tennis");
  });

  it("leaves no slot current once the run ended", () => {
    expect(states([STARTED, BOOKING, FIRST, FINISHED])).toEqual(["pending", "pending"]);
  });

  it("knows a dry run, and ignores values of the wrong type", () => {
    const dry = step(1, {
      kind: "run_started",
      data: { slots: ["10:00 - 11:00", 9], dry_run: true },
    });

    expect(progressOf([dry])).toMatchObject({ slots: ["10:00 - 11:00"], dryRun: true, booked: 0 });
    expect(progressOf([]).slots).toEqual([]);
  });
});
