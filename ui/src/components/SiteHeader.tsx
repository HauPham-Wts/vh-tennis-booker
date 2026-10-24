import { useOverview } from "../api/queries";
import { LanguageSwitch } from "./LanguageSwitch";
import { MainNav } from "./MainNav";
import styles from "./SiteHeader.module.css";
import { StatusLine } from "./StatusLine";

/**
 * Show the app's name and the language switch above every screen, ruled off in ink, with the
 * navigation and the status line unless the screen leads the user step by step (the
 * first-launch welcome).
 */
export function SiteHeader({ navigation }: { navigation: boolean }) {
  const overview = useOverview();
  return (
    <header className={styles.header}>
      <span className={styles.brand}>
        court booker
        <span className={styles.dot} aria-hidden="true">
          .
        </span>
      </span>
      {navigation && <MainNav />}
      <div className={styles.status}>
        {navigation && overview.data && <StatusLine overview={overview.data} />}
      </div>
      <LanguageSwitch />
    </header>
  );
}
