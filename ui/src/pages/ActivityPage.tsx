import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useRunDays } from "../api/queries";
import type { RunSummary } from "../api/types";
import { Button } from "../components/Button";
import { QueryView } from "../components/QueryView";
import { runResult, triggerName } from "../runs";
import { useFormat } from "../useFormat";
import styles from "./ActivityPage.module.css";
import { RunDetail } from "./RunDetail";

/** Return the run asked for in the address (`?run=12`), if it is a run id. */
function requestedRun(params: URLSearchParams): number | undefined {
  const id = Number(params.get("run"));
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

interface RunListProps {
  runs: RunSummary[];
  selected: number;
  /** Read the ten days before the oldest run shown; absent when no older run is left. */
  onMore?: () => void;
  /** Whether those days are being read. */
  loadingMore: boolean;
}

/** The runs of the newest days; the one shown is marked, and each opens its steps. */
function RunList({ runs, selected, onMore, loadingMore }: RunListProps) {
  const { t } = useTranslation();
  const f = useFormat();
  return (
    <nav aria-label={t("pages.activity.runs")} className={styles.runs}>
      <ul className={styles.list}>
        {runs.map((run) => {
          const result = runResult(run);
          return (
            <li key={run.id}>
              <Link
                to={{ search: `?run=${run.id}` }}
                aria-current={run.id === selected ? "true" : undefined}
                className={styles.run}
              >
                <span>
                  {f.dateTime(run.started_at)} · {triggerName(t, run.trigger)}
                </span>
                <span className={styles[result.tone]}>{result.text}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      {onMore && (
        <Button className={styles.more} onClick={onMore} disabled={loadingMore}>
          {t(loadingMore ? "common.loading" : "common.more")}
        </Button>
      )}
    </nav>
  );
}

/** Show every step the app took, for finding out what went wrong: the second tab of History. */
export function ActivityPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const runs = useRunDays();
  return (
    <>
      <p className={styles.lead}>{t("pages.activity.lead")}</p>
      <QueryView
        query={runs}
        isEmpty={(list) => list.length === 0}
        empty={t("pages.activity.empty")}
      >
        {(list) => {
          const selected = requestedRun(params) ?? list[0]?.id ?? 0;
          return (
            <div className={styles.layout}>
              <RunList
                runs={list}
                selected={selected}
                onMore={runs.hasNextPage ? () => void runs.fetchNextPage() : undefined}
                loadingMore={runs.isFetchingNextPage}
              />
              <RunDetail runId={selected} />
            </div>
          );
        }}
      </QueryView>
    </>
  );
}
