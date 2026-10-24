import { useOverview } from "../api/queries";
import { LanguageSwitch } from "./LanguageSwitch";
import styles from "./SiteHeader.module.css";
import { StatusLine } from "./StatusLine";

/** Show the app's name, the status line and the language switch, ruled off in ink. */
export function SiteHeader() {
  const overview = useOverview();
  return (
    <header className={styles.header}>
      <span className={styles.brand}>
        court booker
        <span className={styles.dot} aria-hidden="true">
          .
        </span>
      </span>
      <div className={styles.status}>
        {overview.data && <StatusLine overview={overview.data} />}
      </div>
      <LanguageSwitch />
    </header>
  );
}
