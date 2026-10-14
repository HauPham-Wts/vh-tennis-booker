import { useQuery } from "@tanstack/react-query";
import type { Overview } from "./types";
import {
  type EventsQuery,
  getOverview,
  getRun,
  getSchedule,
  getSettings,
  getSetupChecks,
  listEvents,
  listRunMonths,
  listRuns,
  type RunsQuery,
} from "./endpoints";

/**
 * The cache keys of the backend data. A list key starts with its kind, so invalidating
 * `["runs"]` refreshes every filtered History page at once.
 */
export const queryKeys = {
  overview: ["overview"] as const,
  runs: (query: RunsQuery = {}) => ["runs", query] as const,
  months: ["runs", "months"] as const,
  run: (runId: number) => ["run", runId] as const,
  events: (query: EventsQuery = {}) => ["events", query] as const,
  settings: ["settings"] as const,
  setup: ["setup"] as const,
  schedule: ["schedule"] as const,
};

/** How often the Overview is read while a run is starting or letting go of the emulator. */
export const SETTLING_POLL_MS = 2000;

/**
 * Return how often to read the Overview again, or false. A run writes its first step a
 * moment after taking the lock and gives the lock back a moment after its last step, and
 * no step marks that moment; auto setup ends the same way. Only then is the Overview read
 * every 2 s, never while a booking goes on (the run is "running" then).
 */
export function settlingInterval(overview: Overview | undefined): number | false {
  const running = overview?.running;
  if (running === null || running === undefined) {
    return false;
  }
  const settling = running.trigger === "setup" || overview?.last_run?.status !== "running";
  return settling ? SETTLING_POLL_MS : false;
}

/** Read everything the Overview shows. */
export function useOverview() {
  return useQuery({
    queryKey: queryKeys.overview,
    queryFn: getOverview,
    refetchInterval: (query) => settlingInterval(query.state.data),
  });
}

/** Read the runs of the History list. */
export function useRuns(query: RunsQuery = {}) {
  return useQuery({ queryKey: queryKeys.runs(query), queryFn: () => listRuns(query) });
}

/** Read the months of real bookings; a finished run refreshes them with the runs. */
export function useRunMonths() {
  return useQuery({ queryKey: queryKeys.months, queryFn: listRunMonths });
}

/** Read one run in full. */
export function useRun(runId: number) {
  return useQuery({ queryKey: queryKeys.run(runId), queryFn: () => getRun(runId) });
}

/** Read the activity log. */
export function useEvents(query: EventsQuery = {}) {
  return useQuery({ queryKey: queryKeys.events(query), queryFn: () => listEvents(query) });
}

/** Read the booking settings. */
export function useSettings() {
  return useQuery({ queryKey: queryKeys.settings, queryFn: getSettings });
}

/** Read the device setup checks; they ask Windows and MuMu, so they are not polled. */
export function useSetupChecks() {
  return useQuery({ queryKey: queryKeys.setup, queryFn: getSetupChecks });
}

/** Read the daily schedule. */
export function useSchedule() {
  return useQuery({ queryKey: queryKeys.schedule, queryFn: getSchedule });
}
