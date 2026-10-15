import type { UseQueryResult } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { errorMessage } from "../../api/errors";
import { useAutoSetup } from "../../api/mutations";
import type { Overview, SetupItem } from "../../api/types";
import { Button } from "../../components/Button";
import { Ticket } from "../../components/Ticket";
import { addMinutes } from "../../format";
import styles from "./AutoSetup.module.css";

/** The items auto setup takes care of, in the order it does them. */
const ITEMS = ["mumu_installed", "mumu_screen", "wake_timers"] as const;

/** No dry run or auto setup may start until this long after the start time. */
const QUIET_AFTER_START = 5;

interface AutoSetupProps {
  overview: Overview;
  checks: UseQueryResult<SetupItem[]>;
  running: boolean;
}

/**
 * What Court Booker sets up itself, each item as it stands, and the button that does it.
 * A running MuMu applies a new screen only after a restart, so auto setup first runs
 * without one; if the screen is still left to fix, the user is asked before MuMu restarts.
 */
export function AutoSetup({ overview, checks, running }: AutoSetupProps) {
  const { t } = useTranslation();
  const auto = useAutoSetup();
  const rows = ITEMS.flatMap((item) => {
    const check = checks.data?.find((found) => found.item === item);
    return check === undefined ? [] : [{ item, status: check.status }];
  });
  const restart =
    auto.isSuccess &&
    !auto.variables.restart_mumu &&
    rows.some(({ item, status }) => item === "mumu_screen" && status === "fixable");
  const busy = running || auto.isPending;
  const { wake_at: wake, start_at: start } = overview.schedule;

  return (
    <Ticket
      as="section"
      aria-labelledby="auto-title"
      stub={
        <>
          <Button
            variant="primary"
            size="large"
            disabled={busy}
            onClick={() => auto.mutate({ restart_mumu: false })}
          >
            {t(auto.isPending ? "pages.deviceSetup.auto.running" : "pages.deviceSetup.auto.run")}
          </Button>
          {restart && (
            <div className={styles.restart}>
              <p>{t("pages.deviceSetup.auto.restart")}</p>
              <Button disabled={busy} onClick={() => auto.mutate({ restart_mumu: true })}>
                {t("pages.deviceSetup.auto.restartButton")}
              </Button>
            </div>
          )}
          {auto.isError && <p className={styles.problem}>{errorMessage(t, auto.error)}</p>}
          {running && !auto.isPending && (
            <p className={styles.note}>{t("pages.overview.live.locked")}</p>
          )}
          <p className={styles.note}>
            {t("pages.deviceSetup.auto.quiet", {
              from: wake,
              to: addMinutes(start, QUIET_AFTER_START),
            })}
          </p>
        </>
      }
    >
      <div className={styles.heading}>
        <h2 id="auto-title" className={styles.title}>
          {t("pages.deviceSetup.auto.title")}
        </h2>
        <p className={styles.lead}>{t("pages.deviceSetup.auto.lead")}</p>
      </div>
      {rows.length > 0 && (
        <table className={styles.table}>
          <caption className="visually-hidden">{t("pages.deviceSetup.auto.caption")}</caption>
          <tbody>
            {rows.map(({ item, status }) => (
              <tr key={item}>
                <th scope="row">{t(`pages.deviceSetup.auto.items.${item}`)}</th>
                <td className={styles[status]}>
                  <span>{t(`pages.deviceSetup.auto.statuses.${status}`)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Ticket>
  );
}
