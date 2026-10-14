import { Outlet, useMatch } from "react-router";
import styles from "./App.module.css";
import { SiteHeader } from "./components/SiteHeader";
import { paths } from "./paths";

/** Lay out every screen: the header, then the current screen in the main area. */
export function App() {
  const welcome = useMatch(paths.welcome) !== null;
  return (
    <div className={styles.page}>
      <a className={styles.skipLink} href="#main">
        Bỏ qua tới nội dung
      </a>
      <SiteHeader navigation={!welcome} />
      <main id="main" tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
