import { useTranslation } from "react-i18next";

/** Check MuMu, the app and the wake timers, and fix what can be fixed. */
export function DeviceSetupPage() {
  const { t } = useTranslation();
  return <h2>{t("pages.deviceSetup.title")}</h2>;
}
