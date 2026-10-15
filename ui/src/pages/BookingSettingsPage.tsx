import { useTranslation } from "react-i18next";

/** Edit the slots, court, day and times to book. */
export function BookingSettingsPage() {
  const { t } = useTranslation();
  return <h2>{t("pages.bookingSettings.title")}</h2>;
}
