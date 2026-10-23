import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { DAYS_SHOWN, runDay } from "../days";
import type { Overview, RunSummary } from "./types";
import {
  type EventsQuery,
  getOverview,
  getRun,
  getSchedule,
  getNotifications,
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
  runDays: ["runs", "days"] as const,
  run: (runId: number) => ["run", runId] as const,
  events: (query: EventsQuery = {}) => ["events", query] as const,
  settings: ["settings"] as const,
  notifications: ["notifications"] as const,
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

/** The most runs a page of days may bring: far more than ten days ever hold. */
export const RUN_DAYS_LIMIT = 500;

/**
 * Return where the page after `page` starts (its last run), or undefined when no older
 * run is left: a page holds fewer days than asked only once the oldest day is in it.
 */
export function nextRunDays(page: RunSummary[]): number | undefined {
  const full = new Set(page.map(runDay)).size === DAYS_SHOWN || page.length === RUN_DAYS_LIMIT;
  return full ? page.at(-1)?.id : undefined;
}

/**
 * Read every run, newest first, ten days of runs at a time; `fetchNextPage` reads the ten
 * days before. A run starting or finishing marks `["runs"]` stale, so the pages shown are
 * read again.
 */
export function useRunDays() {
  return useInfiniteQuery({
    queryKey: queryKeys.runDays,
    queryFn: ({ pageParam }) =>
      listRuns({ days: DAYS_SHOWN, limit: RUN_DAYS_LIMIT, before: pageParam }),
    initialPageParam: undefined as number | undefined,
    getNextPageParam: nextRunDays,
    select: (data) => data.pages.flat(),
  });
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

/** Read the notification settings. */
export function useNotifications() {
  return useQuery({ queryKey: queryKeys.notifications, queryFn: getNotifications });
}

/**
 * Read the device setup checks. They ask Windows, MuMu and adb, so they are never polled,
 * and a screen turns them off (`enabled` false) while a run holds the lock: a check must
 * never slow a booking.
 */
export function useSetupChecks(enabled = true) {
  return useQuery({ queryKey: queryKeys.setup, queryFn: getSetupChecks, enabled });
}

/** Read the daily schedule. */
export function useSchedule() {
  return useQuery({ queryKey: queryKeys.schedule, queryFn: getSchedule });
}
