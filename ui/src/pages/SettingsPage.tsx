import { useTranslation } from "react-i18next";
import { TabbedPage } from "../components/TabbedPage";
import { paths } from "../paths";

/** The parts of the settings, each at its own address. */
const TABS = [
  { to: paths.deviceSetup, label: "pages.deviceSetup.title" },
  { to: paths.notificationSettings, label: "pages.notificationSettings.title" },
] as const;

/** Hold the device setup and the notification, one tab each. */
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
