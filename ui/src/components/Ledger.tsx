import type { ReactNode } from "react";
import styles from "./Ledger.module.css";

interface LedgerProps {
  /** Names the table and its scroll area for screen readers. */
  label: string;
  /** The table's rows: a `thead` and a `tbody`. */
  children: ReactNode;
  /** Below this width the table scrolls sideways instead of squeezing its columns. */
  minWidth?: number;
}

/**
 * A table in the style of a ledger: capital headings over a rule of ink, then dotted
 * rows. A narrow window scrolls it sideways; the scroll area can take keyboard focus.
 */
export function Ledger({ label, children, minWidth = 600 }: LedgerProps) {
  return (
    <div role="region" aria-label={label} tabIndex={0} className={styles.scroll}>
      <table aria-label={label} className={styles.table} style={{ minWidth }}>
        {children}
      </table>
    </div>
  );
}
