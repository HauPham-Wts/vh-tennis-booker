import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Ticket.module.css";

interface TicketProps extends HTMLAttributes<HTMLElement> {
  as?: "section" | "article" | "div" | "li";
  /** The torn-off part on the right: the stamp, the play date, the progress. */
  stub: ReactNode;
  /**
   * `large` for the one ticket a screen leads with (the next booking); `small` for rows of
   * tickets, such as the History list, with less padding and smaller notches.
   */
  notch?: "large" | "small";
}

/**
 * A paper ticket: the main part, then a stub behind a dashed perforation with a notch
 * cut at each end. On a narrow window the stub moves under the main part.
 */
export function Ticket({
  as: Element = "div",
  stub,
  notch = "large",
  className,
  children,
  ...props
}: TicketProps) {
  const classes = [styles.ticket, styles[notch], className].filter(Boolean);
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
