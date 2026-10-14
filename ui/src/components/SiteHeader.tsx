import { MainNav } from "./MainNav";
import styles from "./SiteHeader.module.css";

/** Show the app's name and the navigation above every screen, ruled off in ink. */
export function SiteHeader() {
  return (
    <header className={styles.header}>
      <span className={styles.brand}>
        court booker
        <span className={styles.dot} aria-hidden="true">
          .
        </span>
      </span>
      <MainNav />
    </header>
  );
}
