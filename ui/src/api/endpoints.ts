import { call, client } from "./client";
import type {
  AutoSetupRequest,
  DryRunStarted,
  Health,
  Overview,
  RunDetail,
  RunSummary,
  ScheduleState,
  Settings,
  SetupItem,
  Step,
  paths,
} from "./types";

/** Filters of the History list: `month` (YYYY-MM of the play date), `trigger`, paging. */
export type RunsQuery = NonNullable<paths["/api/runs"]["get"]["parameters"]["query"]>;
/** Filters of the Activity log: `category`, paging. */
export type EventsQuery = NonNullable<paths["/api/events"]["get"]["parameters"]["query"]>;

/** Check that the backend answers, and its version. */
export function getHealth(): Promise<Health> {
  return call(client.GET("/api/health"));
}

/** Read everything the Overview shows. */
export function getOverview(): Promise<Overview> {
  return call(client.GET("/api/status"));
}

/** List runs newest first. */
export function listRuns(query: RunsQuery = {}): Promise<RunSummary[]> {
  return call(client.GET("/api/runs", { params: { query } }));
}

/** Read one run with its slots, steps and technical log lines. */
export function getRun(runId: number): Promise<RunDetail> {
  return call(client.GET("/api/runs/{run_id}", { params: { path: { run_id: runId } } }));
}

/** List activity log steps newest first. */
export function listEvents(query: EventsQuery = {}): Promise<Step[]> {
  return call(client.GET("/api/events", { params: { query } }));
}

// openapi-fetch widens the response's [x, y] tuples (next_month_xy...) to number[]; the
// backend always sends two numbers, so the settings keep their schema type.

/** Read the booking settings. */
export function getSettings(): Promise<Settings> {
  return call(client.GET("/api/settings")) as Promise<Settings>;
}

/** Save the booking settings; invalid values fail with `invalid_settings` and `problems`. */
export function saveSettings(settings: Settings): Promise<Settings> {
  return call(client.PUT("/api/settings", { body: settings })) as Promise<Settings>;
}

/** Check each device setup item. */
export function getSetupChecks(): Promise<SetupItem[]> {
  return call(client.GET("/api/setup"));
}

/** Fix what auto setup can fix and return the checks again. */
export function runAutoSetup(request: AutoSetupRequest): Promise<SetupItem[]> {
  return call(client.POST("/api/setup/auto", { body: request }));
}

/** Read the daily schedule and the next booking. */
export function getSchedule(): Promise<ScheduleState> {
  return call(client.GET("/api/schedule"));
}

/** Switch the daily schedule on (needs a passed dry run) or off. */
export function switchSchedule(enabled: boolean): Promise<ScheduleState> {
  return call(client.PUT("/api/schedule", { body: { enabled } }));
}

/** Start a dry run in its own process; its steps arrive through the live feed. */
export function startDryRun(): Promise<DryRunStarted> {
  return call(client.POST("/api/runs/dry-run"));
}
