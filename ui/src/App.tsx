import { Outlet } from "react-router";
import styles from "./App.module.css";

/** Lay out every screen: the current one fills the main area of the page column. */
export function App() {
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
