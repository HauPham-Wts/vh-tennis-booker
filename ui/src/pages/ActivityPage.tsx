import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";
import { useRuns } from "../api/queries";
import type { RunSummary } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QueryView } from "../components/QueryView";
import { runResult, triggerName } from "../runs";
import { useFormat } from "../useFormat";
import styles from "./ActivityPage.module.css";

/** How many recent runs the list shows; older ones are reached from History. */
const RECENT_RUNS = 30;

/** Return the run asked for in the address (`?run=12`), if it is a run id. */
function requestedRun(params: URLSearchParams): number | undefined {
  const id = Number(params.get("run"));
  return Number.isInteger(id) && id > 0 ? id : undefined;
}

/** The recent runs; the one shown is marked, and each opens its steps. */
function RunList({ runs, selected }: { runs: RunSummary[]; selected: number }) {
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
    </nav>
  );
}

/** Show every step the app took, for finding out what went wrong. */
export function ActivityPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const runs = useRuns({ limit: RECENT_RUNS });
  return (
    <>
      <PageHeader title={t("pages.activity.title")} lead={t("pages.activity.lead")} />
      <QueryView
        query={runs}
        isEmpty={(list) => list.length === 0}
        empty={t("pages.activity.empty")}
      >
        {(list) => {
          const selected = requestedRun(params) ?? list[0]?.id ?? 0;
          return (
            <div className={styles.layout}>
              <RunList runs={list} selected={selected} />
            </div>
          );
        }}
      </QueryView>
    </>
  );
}
