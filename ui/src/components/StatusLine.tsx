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
 * One line in the header on whether the next booking can happen: the run going on, else
 * the one thing to do (set up the device, finish its setup, turn the schedule on), else
 * ready for the next start.
 */
export function StatusLine({ overview }: { overview: Overview }) {
  const { t } = useTranslation();
  const f = useFormat();
  const { running, setup, schedule } = overview;
  if (running !== null) {
    return <RunningStatus running={running} startAt={schedule.start_at} />;
  }
  let words: string;
  let link: { to: string; text: string };
  let ready = false;
  if (setup === null) {
    words = t("pages.overview.status.noSetup");
    link = { to: paths.deviceSetup, text: t("pages.overview.status.setupLink") };
  } else if (setup.left.length > 0) {
    words = t("pages.overview.status.setupLeft", { count: setup.left.length });
    link = { to: paths.deviceSetup, text: t("pages.overview.status.setupLink") };
  } else if (!schedule.enabled) {
    words = t("pages.overview.status.scheduleOff");
    link = { to: paths.schedule, text: t("pages.overview.status.turnOn") };
  } else {
    ready = true;
    words = t("pages.overview.status.ready", {
      time: f.time(schedule.next_start),
      when: f.when(schedule.next_start, localToday()),
    });
    link = { to: paths.deviceSetup, text: t("pages.overview.status.check") };
  }
  return (
    <p className={styles.status}>
      <span className={ready ? styles.ready : styles.todo}>
        <span aria-hidden="true">● </span>
        {words}
      </span>
      <Link to={link.to} className={styles.link}>
        {link.text}
      </Link>
    </p>
  );
}
