import { useTranslation } from "react-i18next";
import { TabbedPage } from "../components/TabbedPage";
import { paths } from "../paths";

/** The real bookings and the activity log, each at its own address. */
const TABS = [
  { to: paths.bookings, label: "pages.history.title" },
  { to: paths.activity, label: "pages.activity.title" },
] as const;

/** Hold the real bookings and the activity log, one tab each, as the settings do. */
export function HistoryPage() {
  const { t } = useTranslation();
  return (
    <TabbedPage
      title={t("pages.history.title")}
      label={t("pages.history.tabs")}
      tabs={TABS.map(({ to, label }) => ({ to, label: t(label) }))}
    />
  );
}
