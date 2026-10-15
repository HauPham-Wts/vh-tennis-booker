import styles from "./PillGroup.module.css";

export interface PillOption<T extends string> {
  value: T;
  label: string;
}

interface PillGroupProps<T extends string> {
  /** What the choice is about, such as "Lọc theo loại". */
  label: string;
  options: readonly PillOption<T>[];
  value: T;
  onChange: (value: T) => void;
}

/** One choice among a few, as a row of pill buttons; the chosen one is pressed. */
export function PillGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: PillGroupProps<T>) {
  return (
    <div role="group" aria-label={label} className={styles.group}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          className={styles.pill}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
