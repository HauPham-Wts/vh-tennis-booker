import { useTranslation } from "react-i18next";
import { useOverview } from "../api/queries";
import type { Running, RunSummary } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QueryView } from "../components/QueryView";
import { LastBooking } from "./overview/LastBooking";
import { LiveRun } from "./overview/LiveRun";
import { NextBooking } from "./overview/NextBooking";
import { RunningBanner } from "./overview/RunningBanner";
import { StatusLine } from "./overview/StatusLine";

/**
 * Return the run that holds the lock: the newest run if it started after the lock was
 * taken. It may have finished already: a run lets go of the lock a moment after its last
 * step. A dry run the app just started has no run yet.
 */
function holderRun(running: Running, last: RunSummary | null): number | undefined {
  if (last === null || running.since === null) {
    return undefined;
  }
  return last.started_at >= running.since ? last.id : undefined;
}

/** Show whether the next booking is ready, the next booking and the last one. */
export function OverviewPage() {
  const { t } = useTranslation();
  const overview = useOverview();
  return (
    <>
      <PageHeader title={t("pages.overview.title")}>
        {overview.data && <StatusLine overview={overview.data} />}
      </PageHeader>
      <QueryView query={overview}>
        {({ schedule, running, last_run }) => (
          <>
            {running !== null && <RunningBanner running={running} startAt={schedule.start_at} />}
            {running !== null && running.trigger !== "setup" ? (
              // A booking or a dry run: the run as it goes, in place of the rest.
              <LiveRun runId={holderRun(running, last_run)} />
            ) : (
              <>
                <NextBooking schedule={schedule} />
                <LastBooking />
              </>
            )}
          </>
        )}
      </QueryView>
    </>
  );
}
