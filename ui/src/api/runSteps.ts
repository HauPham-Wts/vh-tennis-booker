import { useMemo } from "react";
import { useLiveFeed } from "./liveContext";
import { useRun } from "./queries";
import type { Step } from "./types";

/**
 * Read one run and follow its steps: the steps stored when the run was read, then the
 * ones the live feed brought since, oldest first. A running run thus needs no request
 * per step.
 */
export function useRunSteps(runId: number) {
  const run = useRun(runId);
  const { steps: live } = useLiveFeed();
  const steps = useMemo((): readonly Step[] => {
    const stored = run.data?.steps ?? [];
    // Both lists run in id order; the live feed adds only what the read did not have.
    const last = stored.at(-1)?.id ?? 0;
    const newer = live.filter((step) => step.run_id === runId && step.id > last);
    return newer.length === 0 ? stored : [...stored, ...newer];
  }, [run.data, live, runId]);
  return { run, steps };
}
