import styles from "./Icon.module.css";

/** Line drawings on a 16-unit grid, in the colour of the text around them. */
const PATHS = {
  /** A clock: a time set ahead, such as the wake time or a run on schedule. */
  clock: "M8 2.5a5.5 5.5 0 1 0 0 11a5.5 5.5 0 1 0 0-11zM8 5v3.25l2 1.25",
} as const;

export type IconName = keyof typeof PATHS;

/**
 * A small icon before a word or a value, sized to the text. It only adds to the words next
 * to it, so screen readers skip it.
 */
export function Icon({ name }: { name: IconName }) {
  return (
    <svg className={styles.icon} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d={PATHS[name]} />
    </svg>
  );
}
