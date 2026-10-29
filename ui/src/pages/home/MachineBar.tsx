import { useTranslation } from "react-i18next";
import type { Machine } from "../../machines";
import { useManualTicks } from "../../manualSteps";
import { machineLeft } from "../../setupState";
import styles from "./MachineBar.module.css";

interface MachineBarProps {
  machines: readonly Machine[];
  /** The machine shown (0: the first). */
  machine: number;
  onMachine: (place: number) => void;
}

/**
 * The machines on top of the ticket, as index cards like the panel's tabs: the one pressed
 * shows its choices on the ticket and its setup in the Setup tab. A red mark tells a
 * machine that books with something of its own left to set up; a machine switched off is
 * pale. Nothing shows with one machine.
 */
export function MachineBar({ machines, machine, onMachine }: MachineBarProps) {
  const { t } = useTranslation();
  const ticks = useManualTicks();
  if (machines.length < 2) {
    return null;
  }
  const shown = Math.min(machine, machines.length - 1);
  return (
    <div role="group" aria-label={t("pages.ticket.instance")} className={styles.bar}>
      {machines.map((item) => (
        <button
          key={item.key}
          type="button"
          aria-pressed={item.place === shown}
          title={item.mumuIndex === null ? undefined : `MuMu ${item.mumuIndex}`}
          className={item.enabled ? styles.machine : `${styles.machine} ${styles.off}`}
          onClick={() => onMachine(item.place)}
        >
          {t("pages.ticket.instanceName", { number: item.place + 1 })}
          {!item.enabled && (
            <span className="visually-hidden">{`, ${t("pages.ticket.instanceOff")}`}</span>
          )}
          {machineLeft(ticks, item) && (
            <>
              <span aria-hidden="true" className={styles.mark}>
                !
              </span>
              <span className="visually-hidden">{`, ${t("pages.ticket.instanceLeft")}`}</span>
            </>
          )}
        </button>
      ))}
    </div>
  );
}
