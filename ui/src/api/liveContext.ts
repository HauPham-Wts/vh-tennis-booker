import type { QueryKey } from "@tanstack/react-query";
import { createContext, useContext } from "react";
import type { LiveState } from "./live";
import { queryKeys } from "./queries";
import type { Step, StepKind } from "./types";

/** How many recent steps the app keeps for the screens that show them live. */
export const MAX_LIVE_STEPS = 200;

/** The live feed as the screens see it: the connection and the recent steps, oldest first. */
export interface LiveFeed {
  state: LiveState;
  steps: readonly Step[];
}

export const LiveContext = createContext<LiveFeed | null>(null);

/** Read the live feed; the app's LiveProvider keeps the one connection. */
export function useLiveFeed(): LiveFeed {
  const feed = useContext(LiveContext);
  if (feed === null) {
    throw new Error("useLiveFeed needs a LiveProvider above it");
  }
  return feed;
}

/**
 * The steps of a run after which the backend reports something new: the run starts, a
 * slot ends, the run ends. The steps in between are shown from the live feed itself.
 */
const RUN_BOUNDARIES: ReadonlySet<StepKind> = new Set<StepKind>([
  "run_started",
  "slot_booked",
  "slot_failed",
  "run_finished",
]);

/**
 * Return the cached data a new step makes stale; only the screens shown refetch it. A run
 * sends no request for its ordinary steps, so a window left open at 06:00 costs the
 * booking nothing between them.
 */
export function staleKeysFor(step: Step): QueryKey[] {
  if (step.run_id !== null) {
    if (!RUN_BOUNDARIES.has(step.kind)) {
      return [];
    }
    const keys: QueryKey[] = [queryKeys.overview, ["runs"]];
    if (step.kind === "run_finished") {
      // Its final status and technical log; the overview says whether a dry run has passed.
      keys.push(queryKeys.run(step.run_id));
    }
    return keys;
  }
  const keys: QueryKey[] = [queryKeys.overview];
  if (step.category === "settings") {
    keys.push(queryKeys.settings);
  }
  return keys;
}
