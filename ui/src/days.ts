/** Count runs by day, for the lists that show only the newest days. */
import type { RunSummary } from "./api/types";

/** How many days a list shows at first, and how many more each "Xem thêm" adds. */
export const DAYS_SHOWN = 10;

/** Return the day a run started (`YYYY-MM-DD`); the backend writes local times. */
export function runDay(run: Pick<RunSummary, "started_at">): string {
  return run.started_at.slice(0, 10);
}
