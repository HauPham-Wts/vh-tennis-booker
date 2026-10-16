/** Count runs by day, for the lists that show only the newest days. */
import type { RunSummary } from "./api/types";

/** How many days a list shows at first, and how many more each "Xem thêm" adds. */
export const DAYS_SHOWN = 10;

/** Return the day a run started (`YYYY-MM-DD`); the backend writes local times. */
export function runDay(run: Pick<RunSummary, "started_at">): string {
  return run.started_at.slice(0, 10);
}

/** Return the day of play of a booking, or the day it ran if it never reached a date. */
export function playDay(run: Pick<RunSummary, "play_date" | "started_at">): string {
  return run.play_date ?? runDay(run);
}

/**
 * Keep the items of the newest `count` days, in their order, with every item of those
 * days; a day without items does not count. `more` tells whether older items are left out.
 */
export function newestDays<T>(
  items: readonly T[],
  dayOf: (item: T) => string,
  count: number,
): { shown: T[]; more: boolean } {
  const days = new Set([...new Set(items.map(dayOf))].sort().reverse().slice(0, count));
  const shown = items.filter((item) => days.has(dayOf(item)));
  return { shown, more: shown.length < items.length };
}
