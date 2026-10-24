import { useTranslation } from "react-i18next";
import { Outlet, useMatch } from "react-router";
import styles from "./App.module.css";
import { SiteHeader } from "./components/SiteHeader";
import { paths } from "./paths";

/**
 * Lay out every screen: the header, then the current screen in the main area. The home
 * screen fills the window; the others make one centred column.
 */
export function App() {
  const { t } = useTranslation();
  const welcome = useMatch(paths.welcome) !== null;
  const home = useMatch(paths.overview) !== null;
  return (
    <div className={home ? `${styles.page} ${styles.fill}` : styles.page}>
      <a className={styles.skipLink} href="#main">
        {t("app.skipToContent")}
      </a>
      <SiteHeader navigation={!welcome} />
      <main id="main" tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
