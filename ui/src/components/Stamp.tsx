import type { ReactNode } from "react";
import styles from "./Stamp.module.css";

interface StampProps {
  /** `booked` in stamp blue ("ĐÃ ĐẶT"), `failed` in orange-red, `muted` for not known yet. */
  tone?: "booked" | "failed" | "muted";
  children: ReactNode;
}

/** An upright rubber stamp on a result, such as "ĐÃ ĐẶT" or "ĐẶT ĐƯỢC 2/2". */
export function Stamp({ tone = "booked", children }: StampProps) {
  return <span className={`${styles.stamp} ${styles[tone]}`}>{children}</span>;
}
