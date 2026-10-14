import { MainNav } from "./MainNav";
import styles from "./SiteHeader.module.css";

/**
 * Show the app's name above every screen, ruled off in ink, with the navigation unless the
 * screen leads the user step by step (the first-launch welcome).
 */
export function SiteHeader({ navigation }: { navigation: boolean }) {
  return (
    <header className={styles.header}>
      <span className={styles.brand}>
        court booker
        <span className={styles.dot} aria-hidden="true">
          .
        </span>
      </span>
      {navigation && <MainNav />}
    </header>
  );
}
