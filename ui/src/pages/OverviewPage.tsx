import { useTranslation } from "react-i18next";
import { useOverview } from "../api/queries";
import { PageHeader } from "../components/PageHeader";
import { QueryView } from "../components/QueryView";
import { LastBooking } from "./overview/LastBooking";
import { LiveRun } from "./overview/LiveRun";
import { NextBooking } from "./overview/NextBooking";
import { RunningBanner } from "./overview/RunningBanner";
import { StatusLine } from "./overview/StatusLine";

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
              <LiveRun runId={last_run?.status === "running" ? last_run.id : undefined} />
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
