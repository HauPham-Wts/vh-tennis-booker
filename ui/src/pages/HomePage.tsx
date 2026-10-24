import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import { useOverview } from "../api/queries";
import { PageTitle } from "../components/PageTitle";
import { QueryView } from "../components/QueryView";
import { manualDone } from "../manualSteps";
import { setupDone } from "../setupState";
import styles from "./HomePage.module.css";
import { BookingTicket } from "./home/BookingTicket";
import { LiveTicket } from "./home/LiveTicket";
import { SidePanel } from "./home/SidePanel";

/**
 * Show the next booking as a ticket that holds its settings, or the run as it goes, with
 * the History and the Setup beside it. The panel opens on the Setup while anything is left
 * to set up, else on the History; a `?run=` in the address opens that run.
 */
export function HomePage() {
  const { t } = useTranslation();
  const overview = useOverview();
  const [params] = useSearchParams();
  const setup =
    overview.data !== undefined && !params.has("run") && !setupDone(overview.data, manualDone());
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
                <LiveTicket runs={data.running.runs} />
              ) : (
                <BookingTicket overview={data} />
              )
            }
          </QueryView>
        </div>
        {/* The tab to open on is chosen once, when the status first comes in. */}
        <SidePanel
          key={overview.data === undefined ? "waiting" : "ready"}
          initialTab={setup ? "setup" : "history"}
        />
      </div>
    </>
  );
}
