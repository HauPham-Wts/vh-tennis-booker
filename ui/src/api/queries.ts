import { useQuery } from "@tanstack/react-query";
import {
  type EventsQuery,
  getOverview,
  getRun,
  getSchedule,
  getSettings,
  getSetupChecks,
  listEvents,
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
  run: (runId: number) => ["run", runId] as const,
  events: (query: EventsQuery = {}) => ["events", query] as const,
  settings: ["settings"] as const,
  setup: ["setup"] as const,
  schedule: ["schedule"] as const,
};

/** Read everything the Overview shows. */
export function useOverview() {
  return useQuery({ queryKey: queryKeys.overview, queryFn: getOverview });
}

/** Read the runs of the History list. */
export function useRuns(query: RunsQuery = {}) {
  return useQuery({ queryKey: queryKeys.runs(query), queryFn: () => listRuns(query) });
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
