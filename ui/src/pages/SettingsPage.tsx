import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";
import { PageHeader } from "../components/PageHeader";
import { paths } from "../paths";
import styles from "./SettingsPage.module.css";

/** The two parts of the settings, each at its own address. */
const TABS = [
  { to: paths.bookingSettings, label: "pages.bookingSettings.title" },
  { to: paths.deviceSetup, label: "pages.deviceSetup.title" },
] as const;

/**
 * Hold the booking settings and the device setup, one tab each. The tabs are links, so
 * each part keeps its address and the current one is marked with aria-current="page".
 */
export function SettingsPage() {
  const { t } = useTranslation();
  return (
    <>
      <div className={styles.top}>
        <PageHeader title={t("pages.settings.title")} />
        <nav aria-label={t("pages.settings.tabs")} className={styles.tabs}>
          {TABS.map(({ to, label }) => (
            <NavLink key={to} to={to} className={styles.tab}>
              {t(label)}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </>
  );
}
