/** How far the setup has come: what is left to do, and whether everything is done. */
import type { Overview } from "./api/types";
import { enabledMachines, type Machine } from "./machines";
import {
  doneOf,
  MANUAL_STEPS,
  type ManualDone,
  type ManualTicks,
  SHARED_STEPS,
} from "./manualSteps";

/** The first machine alone, as when the settings have not loaded. */
const ONE: readonly Machine[] = [{ place: 0, mumuIndex: null, key: "", enabled: true }];

/** The steps of one machine's own, not ticked. */
function ownLeft(done: ManualDone): number {
  return MANUAL_STEPS.filter((step) => !SHARED_STEPS.includes(step) && !done[step]).length;
}

/**
 * Count the setup tasks left: each step not ticked, the shared ones once, the others for
 * each machine the runs book with. The rest (MuMu's place and screen, waking the PC) the
 * runs and the daily switch do themselves.
 */
export function setupLeft(ticks: ManualTicks, machines: readonly Machine[] = ONE): number {
  const shared = SHARED_STEPS.filter((step) => !ticks.first[step]).length;
  const own = enabledMachines(machines).reduce(
    (sum, machine) => sum + ownLeft(doneOf(ticks, machine.key)),
    0,
  );
  return shared + own;
}

/** Tell whether `machine` books and has a step of its own left. */
export function machineLeft(ticks: ManualTicks, machine: Machine): boolean {
  return machine.enabled && ownLeft(doneOf(ticks, machine.key)) > 0;
}

/** Tell whether nothing is left: the setup done, a dry run passed and the schedule on. */
export function setupDone(
  overview: Overview,
  ticks: ManualTicks,
  machines: readonly Machine[] = ONE,
): boolean {
  const { schedule } = overview;
  return setupLeft(ticks, machines) === 0 && schedule.dry_run_passed && schedule.enabled;
}
