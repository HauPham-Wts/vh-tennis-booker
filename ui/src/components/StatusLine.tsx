import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { Overview, Running } from "../api/types";
import { localToday } from "../format";
import { paths } from "../paths";
import { useFormat } from "../useFormat";
import styles from "./StatusLine.module.css";

const TRIGGERS = ["scheduled", "dry_run", "manual", "setup"] as const;

/**
 * The ink pill while a run holds the emulator: what runs. Screen readers hear it once,
 * when it appears.
 */
function RunningStatus({ running, startAt }: { running: Running; startAt: string }) {
  const { t } = useTranslation();
  const trigger = TRIGGERS.find((known) => known === running.trigger) ?? "other";
  return (
    <p role="status" className={styles.running}>
      <span aria-hidden="true" className={styles.light} />
      {t(`pages.overview.live.banner.${trigger}`, { start: startAt })}
    </p>
  );
}

/**
 * One line in the header on whether the next booking can happen, in this order: the run
 * going on; the device setup to do (with a link to it); no dry run passed yet; the daily
 * switch off; else ready for the next start. The ticket holds what fixes the last three.
 */
export function StatusLine({ overview }: { overview: Overview }) {
  const { t } = useTranslation();
  const f = useFormat();
  const { running, setup, schedule } = overview;
  if (running !== null) {
    return <RunningStatus running={running} startAt={schedule.start_at} />;
  }
  let words: string;
  let ready = false;
  if (setup === null || setup.left.length > 0) {
    return (
      <p className={styles.status}>
        <span className={styles.todo}>
          <span aria-hidden="true">● </span>
          {setup === null
            ? t("pages.overview.status.noSetup")
            : t("pages.overview.status.setupLeft", { count: setup.left.length })}
        </span>
        <Link to={paths.deviceSetup} className={styles.link}>
          {t("pages.overview.status.setupLink")}
        </Link>
      </p>
    );
  }
  if (!schedule.dry_run_passed) {
    words = t("pages.overview.status.noDryRun");
  } else if (!schedule.enabled) {
    words = t("pages.overview.status.scheduleOff");
  } else {
    ready = true;
    words = t("pages.overview.status.ready", {
      time: f.time(schedule.next_start),
      when: f.when(schedule.next_start, localToday()),
    });
  }
  return (
    <p className={styles.status}>
      <span className={ready ? styles.ready : styles.todo}>
        <span aria-hidden="true">● </span>
        {words}
      </span>
    </p>
  );
}
