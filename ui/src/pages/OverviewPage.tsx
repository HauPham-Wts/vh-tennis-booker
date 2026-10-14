import { useTranslation } from "react-i18next";
import { useOverview } from "../api/queries";
import { PageHeader } from "../components/PageHeader";
import { QueryView } from "../components/QueryView";
import { LastBooking } from "./overview/LastBooking";
import { NextBooking } from "./overview/NextBooking";
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
        {({ schedule }) => (
          <>
            <NextBooking schedule={schedule} />
            <LastBooking />
          </>
        )}
      </QueryView>
    </>
  );
}
