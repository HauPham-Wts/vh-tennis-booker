import { useTranslation } from "react-i18next";
import { TabbedPage } from "../components/TabbedPage";
import { paths } from "../paths";

/** The two parts of the settings, each at its own address. */
const TABS = [
  { to: paths.bookingSettings, label: "pages.bookingSettings.title" },
  { to: paths.deviceSetup, label: "pages.deviceSetup.title" },
] as const;

/** Hold the booking settings and the device setup, one tab each. */
export function SettingsPage() {
  const { t } = useTranslation();
  return (
    <TabbedPage
      title={t("pages.settings.title")}
      label={t("pages.settings.tabs")}
      tabs={TABS.map(({ to, label }) => ({ to, label: t(label) }))}
    />
  );
}
