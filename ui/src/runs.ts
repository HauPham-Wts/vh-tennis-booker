/** How a run is shown in the History: its stamp and how it started. */
import type { TFunction } from "i18next";
import type { RunSummary } from "./api/types";

type RunCounts = Pick<RunSummary, "dry_run" | "status" | "booked" | "total">;

export interface RunMark {
  text: string;
  tone: "booked" | "failed" | "muted";
}

/**
 * Return a run's stamp: "ĐÃ ĐẶT 2/2" in stamp blue when every slot was booked, "ĐẶT ĐƯỢC
 * 1/2" in orange-red when only some were, "KHÔNG ĐƯỢC 0/2" when none was. A dry run that
 * went through says "CHẠY THỬ ĐẠT" in grey: it booked nothing.
 */
export function runStamp(t: TFunction, run: RunCounts): RunMark {
  if (run.status === "running") {
    return { text: t("runs.stamp.running"), tone: "booked" };
  }
  if (run.status === "interrupted") {
    return { text: t("runs.stamp.interrupted"), tone: "failed" };
  }
  const counts = { booked: run.booked, total: run.total };
  if (run.dry_run) {
    if (run.booked === 0) {
      return { text: t("runs.stamp.dryFailed"), tone: "failed" };
    }
    return run.booked === run.total
      ? { text: t("runs.stamp.dry"), tone: "muted" }
      : { text: t("runs.stamp.dryPartial", counts), tone: "failed" };
  }
  if (run.booked === 0) {
    // A run that stopped before any slot has no count to show.
    return {
      text: t(run.total === 0 ? "runs.stamp.failed" : "runs.stamp.none", counts),
      tone: "failed",
    };
  }
  return run.booked === run.total
    ? { text: t("runs.stamp.booked", counts), tone: "booked" }
    : { text: t("runs.stamp.partial", counts), tone: "failed" };
}

/** What starts a run (cli.run_trigger); the History tells the 06:00 runs from the others. */
const ORIGINS = ["scheduled", "manual", "dry_run"] as const;

/** Say how a run started ("theo hẹn giờ", "chạy tay"); an unknown value reads "không rõ". */
export function runOrigin(t: TFunction, trigger: string): string {
  return t(`runs.by.${ORIGINS.find((known) => known === trigger) ?? "unknown"}`);
}
