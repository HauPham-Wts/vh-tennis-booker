import type { ReactNode } from "react";
import styles from "./Stamp.module.css";

interface StampProps {
  /** `booked` in stamp blue ("ĐÃ ĐẶT"), `failed` in orange-red, `muted` for nothing booked. */
  tone?: "booked" | "failed" | "muted";
  /** `small` for the rows of a list, such as the History. */
  size?: "normal" | "small";
  children: ReactNode;
}

/** An upright rubber stamp on a result, such as "ĐÃ ĐẶT 2/2" or "ĐẶT ĐƯỢC 1/2". */
export function Stamp({ tone = "booked", size = "normal", children }: StampProps) {
  const classes = [styles.stamp, styles[tone], size === "small" && styles.small].filter(Boolean);
  return <span className={classes.join(" ")}>{children}</span>;
}
