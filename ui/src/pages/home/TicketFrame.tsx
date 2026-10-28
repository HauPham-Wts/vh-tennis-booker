import type { HTMLAttributes, ReactNode } from "react";
import styles from "./TicketFrame.module.css";

interface TicketFrameProps extends HTMLAttributes<HTMLElement> {
  /** Above the perforation: the start time, or the slot being booked. */
  top: ReactNode;
  /** Below it: the choices, or the steps of the run. */
  children: ReactNode;
  /**
   * Keep the ticket within its column, a part of its lower half scrolling inside (the
   * choices, the steps of a run), so it keeps its four rounded corners; else the ticket
   * grows to its content and the column scrolls.
   */
  contained?: boolean;
}

/**
 * The ticket of the home screen, as tall as its column: a top part, then a dashed
 * perforation with a notch cut at each end, then the rest.
 */
export function TicketFrame({ top, children, contained = false, ...props }: TicketFrameProps) {
  return (
    <section
      className={contained ? `${styles.ticket} ${styles.contained}` : styles.ticket}
      {...props}
    >
      <div className={styles.top}>{top}</div>
      <div aria-hidden="true" className={styles.perforation} />
      <div className={styles.bottom}>{children}</div>
    </section>
  );
}
