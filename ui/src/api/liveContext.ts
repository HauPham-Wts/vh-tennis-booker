import type { QueryKey } from "@tanstack/react-query";
import { createContext, useContext } from "react";
import type { LiveState } from "./live";
import { queryKeys } from "./queries";
import type { Step } from "./types";

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

/** Return the cached data a new step makes stale; only the screens shown refetch it. */
export function staleKeysFor(step: Step): QueryKey[] {
  const keys: QueryKey[] = [queryKeys.overview, ["events"]];
  if (step.run_id !== null) {
    keys.push(["runs"], queryKeys.run(step.run_id));
  }
  if (step.category === "setup") {
    keys.push(queryKeys.setup);
  }
  if (step.category === "schedule") {
    keys.push(queryKeys.schedule);
  }
  if (step.category === "settings") {
    keys.push(queryKeys.settings, queryKeys.schedule);
  }
  return keys;
}
