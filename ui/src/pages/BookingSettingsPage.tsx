import { useTranslation } from "react-i18next";
import { PageTitle } from "../components/PageTitle";

/** Edit the slots, court, day and times to book. */
export function BookingSettingsPage() {
  const { t } = useTranslation();
  const title = t("pages.bookingSettings.title");
  return (
    <>
      <PageTitle>{title}</PageTitle>
      <h2>{title}</h2>
    </>
  );
}
