import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import { useOverview } from "../api/queries";
import type { Running, RunSummary } from "../api/types";
import { PageTitle } from "../components/PageTitle";
import { QueryView } from "../components/QueryView";
import { paths } from "../paths";
import { isFirstOpen, welcomeShown } from "../welcome";
import styles from "./HomePage.module.css";
import { BookingTicket } from "./home/BookingTicket";
import { HistoryPanel } from "./home/HistoryPanel";
import { LiveTicket } from "./home/LiveTicket";

/**
 * Return the run that holds the lock: the newest run if it started after the lock was
 * taken. It may have finished already: a run lets go of the lock a moment after its last
 * step. A dry run the app just started has no run yet.
 */
function holderRun(running: Running, last: RunSummary | null): number | undefined {
  if (last === null || running.since === null) {
    return undefined;
  }
  return last.started_at >= running.since ? last.id : undefined;
}

/**
 * Show the next booking as a ticket that holds its settings, or the run as it goes, with
 * the History beside it. An app not used yet opens on the welcome screen instead, once per
 * opening.
 */
export function HomePage() {
  const { t } = useTranslation();
  const overview = useOverview();
  if (overview.data !== undefined && isFirstOpen(overview.data) && !welcomeShown()) {
    return <Navigate to={paths.welcome} replace />;
  }
  return (
    <>
      <PageTitle>{t("pages.overview.title")}</PageTitle>
      <h1 className="visually-hidden">{t("pages.overview.title")}</h1>
      <div className={styles.columns}>
        <div className={styles.booking}>
          <QueryView query={overview}>
            {(data) =>
              data.running !== null && data.running.trigger !== "setup" ? (
                // A booking or a dry run: the run as it goes, in place of the choices.
                <LiveTicket runId={holderRun(data.running, data.last_run)} />
              ) : (
                <BookingTicket overview={data} />
              )
            }
          </QueryView>
        </div>
        <HistoryPanel />
      </div>
    </>
  );
}
