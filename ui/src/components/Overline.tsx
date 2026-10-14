import type { ReactNode } from "react";
import styles from "./Overline.module.css";

interface OverlineProps {
  /** `h2` when it names a section, `dt` above a value, `p` or `span` otherwise. */
  as?: "p" | "h2" | "dt" | "span";
  id?: string;
  children: ReactNode;
}

/**
 * The small monospaced capitals above a value ("NGÀY CHƠI"). The text is written in
 * normal case and set in capitals by the style, so the language files stay readable.
 */
export function Overline({ as: Element = "p", id, children }: OverlineProps) {
  return (
    <Element id={id} className={styles.overline}>
      {children}
    </Element>
  );
}
