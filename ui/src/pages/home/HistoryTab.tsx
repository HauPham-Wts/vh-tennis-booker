import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useRunDays } from "../../api/queries";
import type { RunSummary } from "../../api/types";
import { Button } from "../../components/Button";
import { Icon, type IconName } from "../../components/Icon";
import { QueryView } from "../../components/QueryView";
import { EmptyState } from "../../components/States";
import { Stamp } from "../../components/Stamp";
import { DAYS_SHOWN, runDay } from "../../days";
import { failureReason } from "../../reasons";
import { runMark, runOrigin, runStamp } from "../../runs";
import { useFormat } from "../../useFormat";
import styles from "./HistoryTab.module.css";
import { RunDetail } from "./RunDetail";
import { runShortTitle } from "./runText";

/** Return the run asked for in the address (`?run=12`), if it is a run id. */
function requestedRun(params: URLSearchParams): number | undefined {
  const id = Number(params.get("run"));
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

/**
 * Each slot of a run by its start: "✓ 18:00", "✕ 19:00"; a dry run marks a slot it went
 * through with "○", having booked nothing. Why a slot failed shows on hover and in the run
 * itself, so the row stays one line. A run that stopped before any slot says why.
 */
function SlotMarks({ run }: { run: RunSummary }) {
  const { t } = useTranslation();
  const f = useFormat();
  if (run.slots.length === 0) {
    return run.error === null ? null : (
      <span className={styles.slots}>
        <span className={styles.failed}>✕ {failureReason(t, f, run.error)}</span>
      </span>
    );
  }
  return (
    <span className={styles.slots}>
      {run.slots.map(({ slot, ok, reason }) => {
        const start = f.slotStart(slot);
        if (!ok) {
          const why = failureReason(t, f, reason);
          return (
            <span key={slot} className={styles.failed} title={why}>
              ✕ {start}
              <span className="visually-hidden"> {why}</span>
            </span>
          );
        }
        return run.dry_run ? (
          <span key={slot}>○ {start}</span>
        ) : (
          <span key={slot} className={styles.booked}>
            ✓ {start}
          </span>
        );
      })}
    </span>
  );
}

/** The icon of how a run started: a clock on schedule, a person by hand or as a dry run. */
const ORIGIN_ICONS: Record<string, IconName> = {
  scheduled: "clock",
  manual: "person",
  dry_run: "person",
};

/**
 * When a run started, short ("15/10 08:32", the day alone on schedule), after the icon of how
 * it started; the MuMu instance of a run beside the first ends it.
 */
function StartedAt({ run }: { run: RunSummary }) {
  const { t } = useTranslation();
  const f = useFormat();
  const origin = runOrigin(t, run.trigger);
  const icon = ORIGIN_ICONS[run.trigger];
  return (
    <span className={styles.when} title={origin}>
      {icon !== undefined && <Icon name={icon} />}
      <span className="visually-hidden">{origin} </span>
      {f.shortDate(run.started_at)}
      {/* A run on schedule starts at the wake time, the same every day. */}
      {run.trigger === "scheduled" ? "" : ` ${f.time(run.started_at)}`}
      {run.device ? ` · ${t("pages.ticket.instanceName", { index: run.device })}` : ""}
    </span>
  );
}

/**
 * One run in two lines: what it booked and its mark ("2/2"), then each slot and when it
 * started; it opens the run, where the full stamp, the reasons and the steps are.
 */
function RunRow({ run }: { run: RunSummary }) {
  const { t } = useTranslation();
  const f = useFormat();
  const mark = runMark(t, run);
  const stamp = runStamp(t, run);
  return (
    <li className={styles.item}>
      <Link to={{ search: `?run=${run.id}` }} className={styles.row}>
        <span className={styles.head}>
          <span className={styles.title}>{runShortTitle(t, f, run)}</span>
          <span title={stamp.text}>
            <span aria-hidden="true">
              <Stamp tone={mark.tone} size="small">
                {mark.text}
              </Stamp>
            </span>
            <span className="visually-hidden">{stamp.text}</span>
          </span>
        </span>
        <span className={styles.line}>
          <SlotMarks run={run} />
          <StartedAt run={run} />
        </span>
      </Link>
    </li>
  );
}

/**
 * The runs of the newest days, newest first: real bookings only unless dry runs are asked
 * for, and ten more days on request. Leaving dry runs out sends no request.
 */
function RunList({ withDry, onWithDry }: { withDry: boolean; onWithDry: (on: boolean) => void }) {
  const { t } = useTranslation();
  const runs = useRunDays();
  // The days read so far; the list names them while older days are left to read.
  const days = new Set(runs.data?.map(runDay)).size;
  return (
    <>
      <div className={styles.toolbar}>
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={withDry}
            onChange={(event) => onWithDry(event.target.checked)}
          />
          {t("pages.history.withDry")}
        </label>
        {runs.hasNextPage && (
          <span className={styles.days}>{t("pages.history.days", { count: days })}</span>
        )}
      </div>
      <div className={styles.scroll}>
        <QueryView
          query={runs}
          isEmpty={(list) => list.length === 0}
          empty={t("pages.history.empty")}
        >
          {(list) => {
            const shown = withDry ? list : list.filter((run) => !run.dry_run);
            return (
              <>
                {shown.length > 0 ? (
                  <ul className={styles.list}>
                    {shown.map((run) => (
                      <RunRow key={run.id} run={run} />
                    ))}
                  </ul>
                ) : (
                  <EmptyState>
                    {runs.hasNextPage
                      ? t("pages.history.emptyRealDays", { count: days })
                      : t("pages.history.emptyReal")}
                  </EmptyState>
                )}
                {runs.hasNextPage && (
                  <Button
                    className={styles.more}
                    onClick={() => void runs.fetchNextPage()}
                    disabled={runs.isFetchingNextPage}
                  >
                    {runs.isFetchingNextPage
                      ? t("common.loading")
                      : t("pages.history.more", { count: DAYS_SHOWN })}
                  </Button>
                )}
              </>
            );
          }}
        </QueryView>
      </div>
    </>
  );
}

interface HistoryTabProps {
  withDry: boolean;
  onWithDry: (on: boolean) => void;
}

/**
 * The History tab: the list of runs, or the run the address asks for (`?run=12`) with
 * every step, and a way back to the list.
 */
export function HistoryTab({ withDry, onWithDry }: HistoryTabProps) {
  const [params] = useSearchParams();
  const runId = requestedRun(params);
  return runId === undefined ? (
    <RunList withDry={withDry} onWithDry={onWithDry} />
  ) : (
    <RunDetail key={runId} runId={runId} />
  );
}
