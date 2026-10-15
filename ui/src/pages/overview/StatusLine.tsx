import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { Overview } from "../../api/types";
import { localToday } from "../../format";
import { paths } from "../../paths";
import { useFormat } from "../../useFormat";
import styles from "./StatusLine.module.css";

/**
 * One line on whether the next booking can happen, and the one thing to do if not:
 * set up the device, finish its setup, or turn the schedule on.
 */
export function StatusLine({ overview }: { overview: Overview }) {
  const { t } = useTranslation();
  const f = useFormat();
  const { setup, schedule } = overview;
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
