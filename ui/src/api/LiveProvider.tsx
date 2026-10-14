import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { connectLiveFeed, type LiveFeedOptions, type LiveState } from "./live";
import { LiveContext, MAX_LIVE_STEPS, staleKeysFor } from "./liveContext";
import type { Step } from "./types";

interface LiveProviderProps {
  children: ReactNode;
  /** Where and how to connect, for tests; a new object reconnects, so keep the same one. */
  connection?: Pick<LiveFeedOptions, "url" | "createSocket">;
}

/**
 * Keep one live feed connection for the whole app: keep the recent steps for the screens,
 * and mark the data each step changes as stale so the screens shown refresh.
 */
export function LiveProvider({ children, connection }: LiveProviderProps) {
  const cache = useQueryClient();
  const [state, setState] = useState<LiveState>("connecting");
  const [steps, setSteps] = useState<readonly Step[]>([]);

  useEffect(
    () =>
      connectLiveFeed({
        ...connection,
        onState: setState,
        onStep: (step) => {
          setSteps((previous) => [...previous, step].slice(-MAX_LIVE_STEPS));
          for (const queryKey of staleKeysFor(step)) {
            void cache.invalidateQueries({ queryKey });
          }
        },
      }),
    [cache, connection],
  );

  const feed = useMemo(() => ({ state, steps }), [state, steps]);
  return <LiveContext value={feed}>{children}</LiveContext>;
}
