import type { HTMLAttributes } from "react";
import styles from "./Card.module.css";

interface CardProps extends HTMLAttributes<HTMLElement> {
  /** The element, so a card can be a section, an article or a list item. */
  as?: "section" | "article" | "div" | "li";
  /** A thin edge under the card, for the one card a screen leads with. */
  shadow?: boolean;
}

/** A sheet of paper on the grey ground; content sets its own layout inside. */
export function Card({ as: Element = "div", shadow = false, className, ...props }: CardProps) {
  const classes = [styles.card, shadow && styles.shadow, className].filter(Boolean);
  return <Element className={classes.join(" ")} {...props} />;
}
