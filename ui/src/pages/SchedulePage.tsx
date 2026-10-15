import { useTranslation } from "react-i18next";
import { useOverview } from "../api/queries";
import { PageHeader } from "../components/PageHeader";
import { ScheduleSteps } from "./schedule/ScheduleSteps";

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
      <ScheduleSteps />
    </>
  );
}
