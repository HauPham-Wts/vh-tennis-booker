import { useTranslation } from "react-i18next";
import styles from "./Switch.module.css";

interface SwitchProps {
  /** What the switch turns on and off; screen readers announce it with the state. */
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  /** The visible state; "Đang bật" / "Đang tắt" unless given. */
  onText?: string;
  offText?: string;
}

/**
 * An on/off switch: a pill with a knob, filled with ink and a yellow knob while on. The
 * state is also written out, so it never depends on color alone.
 */
export function Switch({ label, checked, onChange, disabled, onText, offText }: SwitchProps) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={styles.switch}
      onClick={() => onChange(!checked)}
    >
      <span aria-hidden="true" className={styles.knob} />
      {checked ? (onText ?? t("common.on")) : (offText ?? t("common.off"))}
    </button>
  );
}
