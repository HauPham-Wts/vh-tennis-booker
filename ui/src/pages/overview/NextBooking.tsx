import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useSettings } from "../../api/queries";
import type { ScheduleState } from "../../api/types";
import { Overline } from "../../components/Overline";
import { QueryView } from "../../components/QueryView";
import { Ticket } from "../../components/Ticket";
import { paths } from "../../paths";
import { useFormat } from "../../useFormat";
import styles from "./NextBooking.module.css";

/** The stub: the play date, the court and the slots the next run will book. */
function Booking({ playDate }: { playDate: string }) {
  const { t } = useTranslation();
  const f = useFormat();
  const settings = useSettings();
  return (
    <QueryView query={settings}>
      {({ court, slots }) => (
        <dl className={styles.facts}>
          <div>
            <Overline as="dt">{t("pages.overview.next.playDate")}</Overline>
            <dd>{f.day(playDate)}</dd>
          </div>
          <div>
            <Overline as="dt">{t("pages.overview.next.court")}</Overline>
            <dd>{f.court(court)}</dd>
          </div>
          <div>
            <Overline as="dt">{t("pages.overview.next.slots")}</Overline>
            {slots.map((slot) => (
              <dd key={slot}>{f.slot(slot)}</dd>
            ))}
          </div>
        </dl>
      )}
    </QueryView>
  );
}

/**
 * The next booking as a ticket: the start time large, when the PC wakes, and what will be
 * booked. With the schedule off it still says what would be booked, and how to turn it on.
 */
export function NextBooking({ schedule }: { schedule: ScheduleState }) {
  const { t } = useTranslation();
  const f = useFormat();
  const start = schedule.next_start;
  return (
    <Ticket
      as="section"
      aria-labelledby="next-run"
      stub={<Booking playDate={schedule.next_play_date} />}
    >
      <Overline as="h2" id="next-run">
        {t(schedule.enabled ? "pages.overview.next.title" : "pages.overview.next.off")}
      </Overline>
      <p className={schedule.enabled ? styles.time : `${styles.time} ${styles.off}`}>
        {f.time(start)}
      </p>
      {schedule.enabled ? (
        <Overline>
          {t("pages.overview.next.when", {
            period: f.period(start),
            day: f.day(start),
            wake: schedule.wake_at,
          })}
        </Overline>
      ) : (
        <p className={styles.offLine}>
          {t("pages.overview.next.offLine", { start: schedule.start_at })}{" "}
          <Link to={paths.schedule}>{t("pages.overview.status.turnOn")}</Link>
        </p>
      )}
    </Ticket>
  );
}
