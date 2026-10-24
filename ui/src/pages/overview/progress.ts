import type { Step } from "../../api/types";

/** Where a slot of a running run stands. */
export type SlotState = "booked" | "failed" | "current" | "pending";

/** What a running run has done so far, read from its steps alone (no request). */
export interface Progress {
  /** The slots the run will try, in order (from `run_started`). */
  slots: string[];
  dryRun: boolean;
  /** The play date and court, once booking started. */
  date?: string;
  court?: string;
  /** The slot being booked now (the last `slot_started`). */
  current?: string;
  booked: number;
  finished: boolean;
  /** Each slot's state, in the order of `slots`. */
  states: { slot: string; state: SlotState }[];
  /** The slots not started yet, waiting for their turn. */
  waiting: string[];
}

function text(data: Step["data"], key: string): string | undefined {
  const value = data[key];
  return typeof value === "string" && value !== "" ? value : undefined;
}

/** Read a run's progress from its steps, oldest first. */
export function progressOf(steps: readonly Step[]): Progress {
  let slots: string[] = [];
  let dryRun = false;
  let date: string | undefined;
  let court: string | undefined;
  let current: string | undefined;
  let finished = false;
  const done = new Map<string, "booked" | "failed">();
  const started = new Set<string>();
  for (const { kind, data } of steps) {
    if (kind === "run_started") {
      const planned = data["slots"];
      slots = Array.isArray(planned)
        ? planned.filter((slot): slot is string => typeof slot === "string")
        : [];
      dryRun = data["dry_run"] === true;
    } else if (kind === "booking_started") {
      date = text(data, "date");
      court = text(data, "court");
    } else if (kind === "slot_started") {
      current = text(data, "slot");
      if (current !== undefined) {
        started.add(current);
      }
    } else if (kind === "slot_booked" || kind === "slot_failed") {
      const slot = text(data, "slot");
      if (slot !== undefined) {
        done.set(slot, kind === "slot_booked" ? "booked" : "failed");
      }
    } else if (kind === "run_finished") {
      finished = true;
    }
  }
  const states = slots.map((slot): { slot: string; state: SlotState } => ({
    slot,
    state: done.get(slot) ?? (slot === current && !finished ? "current" : "pending"),
  }));
  const booked = [...done.values()].filter((state) => state === "booked").length;
  // A slot skipped after the quota notice fails without starting.
  const waiting = slots.filter((slot) => !started.has(slot) && !done.has(slot));
  return { slots, dryRun, date, court, current, booked, finished, states, waiting };
}
