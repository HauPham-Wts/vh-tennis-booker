import type { Overview } from "./api/types";

/** Set in `sessionStorage` once the welcome screen has been shown in this window. */
export const WELCOMED_KEY = "court-booker.welcomed";

/**
 * Tell whether the app looks unused: no dry run has passed and the schedule is off. It is
 * read from the status rather than a stored flag, so an app already in use never asks.
 * A run going on is left in view.
 */
export function isFirstOpen({ schedule, running }: Overview): boolean {
  return !schedule.dry_run_passed && !schedule.enabled && running === null;
}

/**
 * Tell whether the welcome screen was shown since the app opened. Storage that cannot be
 * read counts as shown, so the Overview can never send the user back to it again and again.
 */
export function welcomeShown(): boolean {
  try {
    return sessionStorage.getItem(WELCOMED_KEY) !== null;
  } catch {
    return true;
  }
}

/** Remember that the welcome screen was shown, until the app closes. */
export function markWelcomeShown(): void {
  try {
    sessionStorage.setItem(WELCOMED_KEY, "1");
  } catch {
    // Blocked storage already counts as shown.
  }
}
