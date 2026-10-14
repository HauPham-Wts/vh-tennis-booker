import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useRuns } from "../../api/queries";
import type { RunSummary, SlotResult } from "../../api/types";
import { Card } from "../../components/Card";
import { Overline } from "../../components/Overline";
import { Stamp } from "../../components/Stamp";
import { localToday, relativeDay } from "../../format";
import { paths } from "../../paths";
import { failureReason } from "../../reasons";
import { runStamp } from "../../runs";
import { useFormat } from "../../useFormat";
import styles from "./LastBooking.module.css";

/** One slot of the last booking: the slot large, its stamp, and when it was done or why not. */
function SlotCard({ run, slot }: { run: RunSummary; slot: SlotResult }) {
  const { t } = useTranslation();
  const f = useFormat();
  return (
    <Card as="article" className={styles.slot}>
      <div className={styles.slotHead}>
        <p className={styles.slotTime}>{f.slot(slot.slot)}</p>
        <Stamp tone={slot.ok ? "booked" : "failed"}>
          {t(slot.ok ? "pages.overview.last.booked" : "pages.overview.last.notBooked")}
        </Stamp>
      </div>
      {run.play_date !== null && run.court !== null && (
        <Overline>
          {t("pages.overview.last.meta", { day: f.day(run.play_date), court: f.court(run.court) })}
        </Overline>
      )}
      <p className={styles.result}>
        {slot.ok
          ? t("pages.overview.last.done", {
              time: f.clock(slot.finished_at),
              seconds: f.seconds(slot.seconds),
            })
          : failureReason(t, f, slot.reason)}
      </p>
    </Card>
  );
}

/**
 * The newest real booking: its stamp and one card per slot. Dry runs are left out: they
 * book nothing. Nothing shows until a first real booking.
 */
export function LastBooking() {
  const { t } = useTranslation();
  const f = useFormat();
  const runs = useRuns({ dry_run: false, limit: 1 });
  const run = runs.data?.[0];
  if (run === undefined) {
    return null;
  }
  const stamp = runStamp(t, run);
  const today = localToday();
  // "sáng nay 15/10"; a day further away names itself already ("sáng Thứ Hai 12/10").
  const when =
    relativeDay(run.started_at, today) === null
      ? f.when(run.started_at, today)
      : `${f.when(run.started_at, today)} ${f.shortDate(run.started_at)}`;
  return (
    <section aria-labelledby="last-run" className={styles.section}>
      <div className={styles.head}>
        <h2 id="last-run" className={styles.title}>
          {t("pages.overview.last.title")} <span className={styles.when}>· {when}</span>
        </h2>
        <Stamp tone={stamp.tone}>{stamp.text}</Stamp>
      </div>
      {run.slots.length > 0 ? (
        <div className={styles.slots}>
          {run.slots.map((slot) => (
            <SlotCard key={slot.slot} run={run} slot={slot} />
          ))}
        </div>
      ) : (
        <p className={styles.result}>{failureReason(t, f, run.error)}</p>
      )}
      <Link to={paths.history} className={styles.more}>
        {t("pages.overview.last.history")}
      </Link>
    </section>
  );
}
