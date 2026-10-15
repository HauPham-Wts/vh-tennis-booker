/** How a run's result is shown: its stamp, and a short mark for lists. */
import type { TFunction } from "i18next";
import type { RunSummary } from "./api/types";

type RunCounts = Pick<RunSummary, "dry_run" | "status" | "booked" | "total">;

export interface RunMark {
  text: string;
  tone: "booked" | "failed" | "plain";
}

/**
 * Return a run's stamp: "ĐẶT ĐƯỢC 2/2" in stamp blue when every slot was booked, the same
 * words in orange-red when only some were. A dry run says "CHẠY THỬ ĐẠT": it booked nothing.
 */
export function runStamp(t: TFunction, run: RunCounts): RunMark & { tone: "booked" | "failed" } {
  if (run.status === "running") {
    return { text: t("runs.stamp.running"), tone: "booked" };
  }
  if (run.status === "interrupted") {
    return { text: t("runs.stamp.interrupted"), tone: "failed" };
  }
  if (run.booked === 0) {
    return { text: t(run.dry_run ? "runs.stamp.dryFailed" : "runs.stamp.failed"), tone: "failed" };
  }
  const counts = { booked: run.booked, total: run.total };
  return {
    text: t(run.dry_run ? "runs.stamp.dry" : "runs.stamp.booked", counts),
    tone: run.booked === run.total ? "booked" : "failed",
  };
}

/** Return a run's mark for a list: "✓ 2/2", "✕ 0/1", or "…" while it runs. */
export function runResult(run: RunCounts): RunMark {
  if (run.status === "running") {
    return { text: "…", tone: "plain" };
  }
  const counts = run.total === 0 ? "" : ` ${run.booked}/${run.total}`;
  return run.total > 0 && run.booked === run.total && run.status !== "interrupted"
    ? { text: `✓${counts}`, tone: "booked" }
    : { text: `✕${counts}`, tone: "failed" };
}

const TRIGGERS = ["scheduled", "dry_run", "manual", "setup"] as const;

/** Name what started a run ("hẹn giờ", "chạy thử"); an unknown value reads "không rõ". */
export function triggerName(t: TFunction, trigger: string | undefined): string {
  return t(`triggers.${TRIGGERS.find((known) => known === trigger) ?? "unknown"}`);
}
