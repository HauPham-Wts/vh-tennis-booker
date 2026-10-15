import { useTranslation } from "react-i18next";
import { useOverview } from "../api/queries";
import { PageHeader } from "../components/PageHeader";
import { QueryView } from "../components/QueryView";
import { DryRunStep } from "./schedule/DryRunStep";
import { ScheduleStep } from "./schedule/ScheduleStep";

/** Run a dry run, then switch the daily booking on or off. */
export function SchedulePage() {
  const { t } = useTranslation();
  const overview = useOverview();
  const start = overview.data?.schedule.start_at;
  return (
    <>
      <PageHeader
        title={t("pages.schedule.title")}
        lead={start === undefined ? undefined : t("pages.schedule.lead", { start })}
      />
      <QueryView query={overview}>
        {({ running, schedule }) => (
          <>
            <DryRunStep running={running} wake={schedule.wake_at} start={schedule.start_at} />
            <ScheduleStep />
          </>
        )}
      </QueryView>
    </>
  );
}
