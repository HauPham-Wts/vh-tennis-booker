import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Ticket.module.css";

interface TicketProps extends HTMLAttributes<HTMLElement> {
  as?: "section" | "article" | "div";
  /** The torn-off part on the right: the stamp, the play date, the progress. */
  stub: ReactNode;
}

/**
 * A paper ticket: the main part, then a stub behind a dashed perforation with a notch
 * cut at each end. On a narrow window the stub moves under the main part.
 */
export function Ticket({ as: Element = "div", stub, className, children, ...props }: TicketProps) {
  const classes = [styles.ticket, className].filter(Boolean);
  return (
    <Element className={classes.join(" ")} {...props}>
      <div className={styles.main}>{children}</div>
      <div className={styles.stub}>
        <span aria-hidden="true" className={`${styles.notch} ${styles.top}`} />
        <span aria-hidden="true" className={`${styles.notch} ${styles.bottom}`} />
        {stub}
      </div>
    </Element>
  );
}
