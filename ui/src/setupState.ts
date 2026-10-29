/** How far the setup has come: what is left to do, and whether everything is done. */
import type { Overview } from "./api/types";
import { MANUAL_STEPS, type ManualDone } from "./manualSteps";

/**
 * Count the setup tasks left: each step the user has not ticked. The rest (MuMu's place
 * and screen, waking the PC) the runs and the daily switch do themselves.
 */
export function setupLeft(manual: ManualDone): number {
  return MANUAL_STEPS.filter((step) => !manual[step]).length;
}

/** Tell whether nothing is left: the setup done, a dry run passed and the schedule on. */
export function setupDone(overview: Overview, manual: ManualDone): boolean {
  const { schedule } = overview;
  return setupLeft(manual) === 0 && schedule.dry_run_passed && schedule.enabled;
}
