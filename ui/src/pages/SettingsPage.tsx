import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

/** Hold the booking settings and the device setup, one tab each. */
export function SettingsPage() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t("pages.settings.title")}</h1>
      <Outlet />
    </>
  );
}
