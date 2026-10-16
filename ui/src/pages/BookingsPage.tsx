import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useRunMonths, useRuns } from "../api/queries";
import type { MonthSummary, RunSummary } from "../api/types";
import { Button } from "../components/Button";
import { QueryView } from "../components/QueryView";
import { Stamp } from "../components/Stamp";
import { Ticket } from "../components/Ticket";
import { DAYS_SHOWN, newestDays, playDay } from "../days";
import { paths } from "../paths";
import { runStamp } from "../runs";
import { useFormat } from "../useFormat";
import styles from "./BookingsPage.module.css";

/** A month holds a few dozen runs at most; it is read in one request. */
const MONTH_LIMIT = 200;

/** One real booking as a ticket: the play date, its slots and court, and its stamp. */
function RunRow({ run }: { run: RunSummary }) {
  const { t } = useTranslation();
  const f = useFormat();
  const stamp = runStamp(t, run);
  const slots = run.slots.map(({ slot }) => f.slot(slot)).join(" · ");
  const booked = { period: f.period(run.started_at), date: f.shortDate(run.started_at) };
  return (
    <Ticket as="li" notch="small" stub={<Stamp tone={stamp.tone}>{stamp.text}</Stamp>}>
      <p className={styles.title}>
        {run.play_date !== null
          ? t("pages.history.play", { day: f.day(run.play_date) })
          : t("pages.history.runOn", { day: f.day(run.started_at) })}
      </p>
      <p className={styles.slots}>
        {slots !== ""
          ? t("pages.history.slots", { slots, court: f.court(run.court ?? "—") })
          : t("pages.history.noSlot")}
      </p>
      <p className={styles.meta}>
        {run.finished_at !== null
          ? t("pages.history.meta", { ...booked, time: f.clock(run.finished_at) })
          : t("pages.history.metaRunning", booked)}
        {" · "}
        <Link to={{ pathname: paths.activity, search: `?run=${run.id}` }}>
          {t("pages.history.activity")}
        </Link>
      </p>
    </Ticket>
  );
}

/**
 * The real bookings of one month, newest first: those of the newest days of play, and more
 * days on request. The month is read whole, so showing more sends no request.
 */
function MonthRuns({ month }: { month: string }) {
  const { t } = useTranslation();
  const runs = useRuns({ month, dry_run: false, limit: MONTH_LIMIT });
  const [days, setDays] = useState(DAYS_SHOWN);
  return (
    <QueryView
      query={runs}
      isEmpty={(list) => list.length === 0}
      empty={t("pages.history.emptyMonth")}
    >
      {(list) => {
        const { shown, more } = newestDays(list, playDay, days);
        return (
          <>
            <ol className={styles.list}>
              {shown.map((run) => (
                <RunRow key={run.id} run={run} />
              ))}
            </ol>
            {more && (
              <Button className={styles.more} onClick={() => setDays(days + DAYS_SHOWN)}>
                {t("common.more")}
              </Button>
            )}
          </>
        );
      }}
    </QueryView>
  );
}

/** Pick the month to show; it is kept in the address, so a reload keeps it. */
function MonthPicker({ months, value }: { months: MonthSummary[]; value: string }) {
  const { t } = useTranslation();
  const f = useFormat();
  const [, setParams] = useSearchParams();
  return (
    <label className={styles.picker}>
      {t("pages.history.month")}
      <select
        className={styles.select}
        value={value}
        onChange={(event) => setParams({ month: event.target.value })}
      >
        {months.map(({ month }) => (
          <option key={month} value={month}>
            {f.month(month)}
          </option>
        ))}
      </select>
    </label>
  );
}

/** List the real bookings month by month, as a ledger of tickets: the first tab of History. */
export function BookingsPage() {
  const { t } = useTranslation();
  const f = useFormat();
  const [params] = useSearchParams();
  const months = useRunMonths();
  const list = months.data ?? [];
  // The month in the address if it has bookings, else the newest one.
  const shown = list.find(({ month }) => month === params.get("month")) ?? list[0];
  return (
    <>
      {shown && (
        <div className={styles.top}>
          <p className={styles.lead}>
            {t("pages.history.summary", {
              month: f.month(shown.month),
              slots: shown.booked,
              runs: shown.runs,
            })}
          </p>
          <MonthPicker months={list} value={shown.month} />
        </div>
      )}
      <QueryView
        query={months}
        isEmpty={(found) => found.length === 0}
        empty={t("pages.history.empty")}
      >
        {() => shown && <MonthRuns key={shown.month} month={shown.month} />}
      </QueryView>
    </>
  );
}
