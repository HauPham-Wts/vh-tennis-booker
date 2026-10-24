import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useRunDays } from "../../api/queries";
import type { RunSummary } from "../../api/types";
import { Button } from "../../components/Button";
import { QueryView } from "../../components/QueryView";
import { EmptyState } from "../../components/States";
import { Stamp } from "../../components/Stamp";
import { DAYS_SHOWN, runDay } from "../../days";
import { failureReason } from "../../reasons";
import { runStamp } from "../../runs";
import { useFormat } from "../../useFormat";
import styles from "./HistoryPanel.module.css";
import { RunDetail } from "./RunDetail";
import { runTitle, runWhen } from "./runText";

/** Return the run asked for in the address (`?run=12`), if it is a run id. */
function requestedRun(params: URLSearchParams): number | undefined {
  const id = Number(params.get("run"));
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

/**
 * Each slot of a run by its start: "✓ 18:00", "✕ 19:00 Hết chỗ"; a dry run marks a slot it
 * went through with "○", having booked nothing. A run that stopped before any slot says why.
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
          return (
            <span key={slot} className={styles.failed}>
              ✕ {start} {failureReason(t, f, reason)}
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

/** One run: what it booked, its stamp, when and how it went, and each slot; it opens the run. */
function RunRow({ run }: { run: RunSummary }) {
  const { t } = useTranslation();
  const f = useFormat();
  const stamp = runStamp(t, run);
  return (
    <li className={styles.item}>
      <Link to={{ search: `?run=${run.id}` }} className={styles.row}>
        <span className={styles.head}>
          <span className={styles.title}>{runTitle(t, f, run)}</span>
          <Stamp tone={stamp.tone} size="small">
            {stamp.text}
          </Stamp>
        </span>
        <span className={styles.meta}>{runWhen(t, f, run)}</span>
        <SlotMarks run={run} />
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

/**
 * The History beside the next booking: the list of runs, or the run the address asks for
 * (`?run=12`) with every step, and a way back to the list.
 */
export function HistoryPanel() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  // Kept here, so it survives opening a run and going back.
  const [withDry, setWithDry] = useState(false);
  const runId = requestedRun(params);
  return (
    <section aria-labelledby="history-title" className={styles.panel}>
      <div className={styles.tabs}>
        <h2 id="history-title" className={styles.tab}>
          {t("pages.history.title")}
        </h2>
      </div>
      {runId === undefined ? (
        <RunList withDry={withDry} onWithDry={setWithDry} />
      ) : (
        <RunDetail key={runId} runId={runId} />
      )}
    </section>
  );
}
