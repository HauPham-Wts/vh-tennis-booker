import type { RunSummary } from "../api/types";

/** A run as GET /api/runs gives it: a scheduled booking of two slots, both booked. */
export function runSummary(id: number, fields: Partial<RunSummary> = {}): RunSummary {
  return {
    id,
    trigger: "scheduled",
    dry_run: false,
    version: "0.6.0",
    started_at: "2026-10-15T05:50:02.120",
    finished_at: "2026-10-15T06:00:11.056",
    play_date: "2026-10-17",
    court: "S6 - Sân tennis",
    status: "ok",
    error: null,
    booked: 2,
    total: 2,
    ...fields,
  };
}
