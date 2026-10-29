import { type KeyboardEvent, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useOverview } from "../../api/queries";
import { useMachines } from "../../machines";
import { useManualTicks } from "../../manualSteps";
import { setupLeft } from "../../setupState";
import { HistoryTab } from "./HistoryTab";
import { SetupTab } from "./SetupTab";
import styles from "./SidePanel.module.css";

export type PanelTab = "history" | "setup";

const TABS: readonly PanelTab[] = ["history", "setup"];

/**
 * The panel beside the ticket: the History and the Setup, one tab each. The Setup tab
 * counts the tasks left in red. Arrow keys move between the tabs, as in any tab list.
 */
export function SidePanel({ initialTab, machine }: { initialTab: PanelTab; machine: number }) {
  const { t } = useTranslation();
  const overview = useOverview();
  const ticks = useManualTicks();
  const machines = useMachines();
  const [tab, setTab] = useState(initialTab);
  // Kept here, so it survives opening a run, going back and changing tabs.
  const [withDry, setWithDry] = useState(false);
  const buttons = useRef<Partial<Record<PanelTab, HTMLButtonElement | null>>>({});
  const left = overview.data === undefined ? 0 : setupLeft(ticks, machines);

  function onKeyDown(event: KeyboardEvent) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
      return;
    }
    const other = tab === "history" ? "setup" : "history";
    setTab(other);
    buttons.current[other]?.focus();
  }

  return (
    <section aria-labelledby="panel-title" className={styles.panel}>
      <h2 id="panel-title" className="visually-hidden">
        {t("pages.panel.title")}
      </h2>
      <div
        role="tablist"
        aria-labelledby="panel-title"
        className={styles.tabs}
        onKeyDown={onKeyDown}
      >
        {TABS.map((name) => (
          <button
            key={name}
            ref={(button) => {
              buttons.current[name] = button;
            }}
            type="button"
            role="tab"
            id={`tab-${name}`}
            aria-selected={tab === name}
            aria-controls={`panel-${name}`}
            tabIndex={tab === name ? 0 : -1}
            className={styles.tab}
            onClick={() => setTab(name)}
          >
            {name === "history" ? t("pages.history.title") : t("pages.panel.setup")}
            {name === "setup" && left > 0 && (
              <>
                <span aria-hidden="true" className={styles.badge}>
                  {left}
                </span>
                <span className="visually-hidden">{t("pages.panel.left", { count: left })}</span>
              </>
            )}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`panel-${tab}`}
        aria-labelledby={`tab-${tab}`}
        className={styles.body}
      >
        {tab === "history" ? (
          <HistoryTab withDry={withDry} onWithDry={setWithDry} />
        ) : (
          <SetupTab machine={machine} />
        )}
      </div>
    </section>
  );
}
