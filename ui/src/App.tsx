import { Outlet, useMatch } from "react-router";
import styles from "./App.module.css";
import { SiteHeader } from "./components/SiteHeader";
import { paths } from "./paths";

/** Lay out every screen: the header, then the current screen in the main area. */
export function App() {
  const welcome = useMatch(paths.welcome) !== null;
  return (
    <div className={styles.page}>
      <SiteHeader navigation={!welcome} />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
