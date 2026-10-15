import { useTranslation } from "react-i18next";
import type { Running } from "../../api/types";
import styles from "./RunningBanner.module.css";

const TRIGGERS = ["scheduled", "dry_run", "manual", "setup"] as const;

/**
 * The ink banner while a run holds the emulator: what runs, and that dry run and auto setup
 * wait until it ends. Screen readers hear it once, when it appears.
 */
export function RunningBanner({ running, startAt }: { running: Running; startAt: string }) {
  const { t } = useTranslation();
  const trigger = TRIGGERS.find((known) => known === running.trigger) ?? "other";
  return (
    <div role="status" className={styles.banner}>
      <p className={styles.what}>
        <span aria-hidden="true" className={styles.light} />
        {t(`pages.overview.live.banner.${trigger}`, { start: startAt })}
      </p>
      <p className={styles.locked}>{t("pages.overview.live.locked")}</p>
    </div>
  );
}
