import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useRunMonths, useRuns } from "../api/queries";
import type { MonthSummary, RunSummary } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QueryView } from "../components/QueryView";
import { Stamp } from "../components/Stamp";
import { Ticket } from "../components/Ticket";
import { paths } from "../paths";
import { runStamp } from "../runs";
import { useFormat } from "../useFormat";
import styles from "./HistoryPage.module.css";

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

/** The real bookings of one month, newest first. */
function MonthRuns({ month }: { month: string }) {
  const { t } = useTranslation();
  const runs = useRuns({ month, dry_run: false, limit: MONTH_LIMIT });
  return (
    <QueryView
      query={runs}
      isEmpty={(list) => list.length === 0}
      empty={t("pages.history.emptyMonth")}
    >
      {(list) => (
        <ol className={styles.list}>
          {list.map((run) => (
            <RunRow key={run.id} run={run} />
          ))}
        </ol>
      )}
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

/** List the real bookings month by month, as a ledger of tickets. */
export function HistoryPage() {
  const { t } = useTranslation();
  const f = useFormat();
  const [params] = useSearchParams();
  const months = useRunMonths();
  const list = months.data ?? [];
  // The month in the address if it has bookings, else the newest one.
  const shown = list.find(({ month }) => month === params.get("month")) ?? list[0];
  return (
    <>
      <PageHeader
        title={t("pages.history.title")}
        lead={
          shown &&
          t("pages.history.summary", {
            month: f.month(shown.month),
            slots: shown.booked,
            runs: shown.runs,
          })
        }
      >
        {shown && <MonthPicker months={list} value={shown.month} />}
      </PageHeader>
      <QueryView
        query={months}
        isEmpty={(found) => found.length === 0}
        empty={t("pages.history.empty")}
      >
        {() => shown && <MonthRuns month={shown.month} />}
      </QueryView>
    </>
  );
}
