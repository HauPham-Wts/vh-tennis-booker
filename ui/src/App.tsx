import { Outlet } from "react-router";
import styles from "./App.module.css";
import { SiteHeader } from "./components/SiteHeader";

/** Lay out every screen: the header, then the current screen in the main area. */
export function App() {
  return (
    <div className={styles.page}>
      <SiteHeader />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
