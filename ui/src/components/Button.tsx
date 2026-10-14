import type { ComponentPropsWithoutRef } from "react";
import styles from "./Button.module.css";

interface ButtonProps extends ComponentPropsWithoutRef<"button"> {
  /** `primary`: the one main action of a screen, filled with ink; `secondary`: outlined. */
  variant?: "primary" | "secondary";
  /** `large` for the action a whole section is about, such as "Chạy thử ngay". */
  size?: "normal" | "large";
}

/** A button of the paper design; it never submits a form unless `type` says so. */
export function Button({
  variant = "secondary",
  size = "normal",
  type = "button",
  className,
  ...props
}: ButtonProps) {
  const classes = [styles.button, styles[variant], styles[size], className].filter(Boolean);
  return <button type={type} className={classes.join(" ")} {...props} />;
}
