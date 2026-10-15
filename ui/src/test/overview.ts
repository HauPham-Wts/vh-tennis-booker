import type { Overview } from "../api/types";

/** Everything ready for tomorrow's 06:00, as GET /api/status gives it. */
export function overview(fields: Partial<Overview> = {}): Overview {
  return {
    version: "0.6.0",
    running: null,
    schedule: {
      enabled: true,
      wake_at: "05:50",
      start_at: "06:00",
      next_start: "2026-10-16T06:00",
      next_play_date: "2026-10-18",
      dry_run_passed: true,
    },
    last_run: null,
    setup: { checked_at: "2026-10-14T21:00:00.000", left: [] },
    ...fields,
  };
}
