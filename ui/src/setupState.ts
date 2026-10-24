/** How far the setup has come: what is left to do, and whether everything is done. */
import type { Overview, SetupSummary } from "./api/types";
import { MANUAL_STEPS, type ManualDone } from "./manualSteps";

/**
 * The items auto setup fixes, in the order it does them. Auto setup also reports whether
 * MuMu and the Vinhomes app are installed; those are the user's own ticks instead.
 */
export const AUTO_ITEMS = ["mumu_installed", "mumu_screen", "wake_timers"] as const;

export type AutoItem = (typeof AUTO_ITEMS)[number];

/** Return the items auto setup left to fix the last time it ran, in its order. */
export function autoLeft(summary: SetupSummary): AutoItem[] {
  return AUTO_ITEMS.filter((item) => summary.left.includes(item));
}

/**
 * Count the setup tasks left: each step the user has not ticked, and auto setup when it
 * never ran or left something to fix.
 */
export function setupLeft(overview: Overview, manual: ManualDone): number {
  const steps = MANUAL_STEPS.filter((step) => !manual[step]).length;
  const auto = overview.setup === null || autoLeft(overview.setup).length > 0;
  return steps + (auto ? 1 : 0);
}

/** Tell whether nothing is left: the setup done, a dry run passed and the schedule on. */
export function setupDone(overview: Overview, manual: ManualDone): boolean {
  const { schedule } = overview;
  return setupLeft(overview, manual) === 0 && schedule.dry_run_passed && schedule.enabled;
}
