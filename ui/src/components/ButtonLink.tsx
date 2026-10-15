import type { ComponentPropsWithoutRef } from "react";
import { Link } from "react-router";
import styles from "./Button.module.css";

interface ButtonLinkProps extends ComponentPropsWithoutRef<typeof Link> {
  /** `primary`: the one main action of a screen, filled with ink; `secondary`: outlined. */
  variant?: "primary" | "secondary";
  /** `large` for the action a whole section is about. */
  size?: "normal" | "large";
}

/** A link to another screen that looks like a button, for moves such as "Tiếp". */
export function ButtonLink({
  variant = "secondary",
  size = "normal",
  className,
  ...props
}: ButtonLinkProps) {
  const classes = [styles.button, styles[variant], styles[size], className].filter(Boolean);
  return <Link className={classes.join(" ")} {...props} />;
}
