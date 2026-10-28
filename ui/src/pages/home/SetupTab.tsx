import { useTranslation } from "react-i18next";
import { errorMessage } from "../../api/errors";
import { useAutoSetup } from "../../api/mutations";
import { useOverview } from "../../api/queries";
import type { Overview } from "../../api/types";
import { Button } from "../../components/Button";
import { QueryView } from "../../components/QueryView";
import { MANUAL_STEPS, setManualDone, useManualSteps } from "../../manualSteps";
import { autoLeft, setupDone } from "../../setupState";
import { useFormat } from "../../useFormat";
import styles from "./SetupTab.module.css";

/** The three steps of a first use; shown first until everything is set up. */
function HowTo() {
  const { t } = useTranslation();
  const names = { dryRun: t("pages.ticket.dryRun.button"), daily: t("pages.ticket.autoShort") };
  return (
    <ol className={styles.howto}>
      {(["1", "2", "3"] as const).map((step) => (
        <li key={step}>{t(`pages.setup.start.steps.${step}`, names)}</li>
      ))}
    </ol>
  );
}

/** The steps only the user can do, ticked by the user; the app does not check them. */
function ManualSteps() {
  const { t } = useTranslation();
  const done = useManualSteps();
  return (
    <section aria-labelledby="manual-title">
      <h3 id="manual-title" className={styles.heading}>
        {t("pages.setup.manual.title")}
      </h3>
      <ul className={styles.list}>
        {MANUAL_STEPS.map((step) => (
          <li key={step} className={styles.item}>
            <label className={styles.check}>
              <input
                type="checkbox"
                checked={done[step]}
                onChange={(event) => setManualDone(step, event.target.checked)}
              />
              <span className={styles.text}>
                <span className={styles.title}>{t(`pages.setup.manual.${step}.title`)}</span>
                <span className={styles.hint}>{t(`pages.setup.manual.${step}.hint`)}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * What Court Booker sets up itself, in one line from its last run, and the button that does
 * it again. A running MuMu applies a new screen only after a restart, so auto setup first
 * runs without one; if the screen is still left to fix, the user is asked before MuMu
 * restarts. Nothing here asks MuMu until the button is pressed.
 */
function AutoSetup({ overview }: { overview: Overview }) {
  const { t } = useTranslation();
  const f = useFormat();
  const auto = useAutoSetup();
  const busy = overview.running !== null || auto.isPending;
  const summary = overview.setup;
  let state: { text: string; tone: "ok" | "todo" | "plain" };
  if (summary === null) {
    state = { text: t("pages.setup.auto.never"), tone: "plain" };
  } else {
    const left = autoLeft(summary);
    state =
      left.length > 0
        ? {
            text: t("pages.setup.auto.fix", {
              items: left.map((item) => t(`pages.setup.auto.items.${item}`)).join(", "),
            }),
            tone: "todo",
          }
        : {
            text: t("pages.setup.auto.ok", {
              date: f.shortDate(summary.checked_at),
              time: f.time(summary.checked_at),
            }),
            tone: "ok",
          };
  }
  const restart =
    auto.isSuccess &&
    !auto.variables.restart_mumu &&
    auto.data.some(({ item, status }) => item === "mumu_screen" && status === "fixable");
  return (
    <section aria-labelledby="auto-title">
      <h3 id="auto-title" className={styles.heading}>
        {t("pages.setup.auto.title")}
      </h3>
      <div className={styles.row}>
        <span className={styles.text}>
          <span className={styles.title}>{t("pages.setup.auto.what")}</span>
          <span className={styles[state.tone]}>{state.text}</span>
        </span>
        <Button disabled={busy} onClick={() => auto.mutate({ restart_mumu: false })}>
          {t(auto.isPending ? "pages.setup.auto.running" : "pages.setup.auto.run")}
        </Button>
      </div>
      {restart && (
        <div className={styles.restart}>
          <p>{t("pages.setup.auto.restart")}</p>
          <Button disabled={busy} onClick={() => auto.mutate({ restart_mumu: true })}>
            {t("pages.setup.auto.restartButton")}
          </Button>
        </div>
      )}
      {auto.isError && <p className={styles.problem}>{errorMessage(t, auto.error)}</p>}
      {overview.running !== null && !auto.isPending && (
        <p className={styles.note}>{t("pages.overview.live.locked")}</p>
      )}
    </section>
  );
}

const TROUBLES = ["notRunning", "slotFull", "quota", "loggedOut"] as const;

/** The guide in rows that open one at a time: how to use it, the mornings, the problems. */
function Guide({ overview, howto }: { overview: Overview; howto: boolean }) {
  const { t } = useTranslation();
  const { wake_at: wake, start_at: start } = overview.schedule;
  const labels = { slotFull: t("reasons.slotFull") };
  return (
    <section aria-labelledby="guide-title">
      <h3 id="guide-title" className={styles.heading}>
        {t("pages.setup.guide.title")}
      </h3>
      <div className={styles.list}>
        {howto && (
          <details className={styles.item}>
            <summary className={styles.summary}>{t("pages.setup.guide.howto")}</summary>
            <HowTo />
          </details>
        )}
        <details className={styles.item}>
          <summary className={styles.summary}>{t("pages.setup.guide.morning.title")}</summary>
          <div className={styles.answer}>
            <p>{t("pages.setup.guide.morning.text", { wake, start })}</p>
            <p>
              <strong>{t("pages.setup.guide.morning.needs")}</strong>{" "}
              {t("pages.setup.guide.morning.needsText")}
            </p>
          </div>
        </details>
        <details className={styles.item}>
          <summary className={styles.summary}>{t("pages.setup.guide.trouble.title")}</summary>
          <dl className={styles.answer}>
            {TROUBLES.map((trouble) => (
              <div key={trouble}>
                <dt>{t(`pages.setup.guide.trouble.${trouble}.question`, labels)}</dt>
                <dd>{t(`pages.setup.guide.trouble.${trouble}.answer`)}</dd>
              </div>
            ))}
          </dl>
        </details>
      </div>
    </section>
  );
}

/**
 * The Setup tab: how to start while anything is left, the steps the user ticks, what Court
 * Booker sets up itself and the guide; the notification switch is on the ticket.
 */
export function SetupTab() {
  const { t } = useTranslation();
  const overview = useOverview();
  const manual = useManualSteps();
  return (
    <div className={styles.tab}>
      <QueryView query={overview}>
        {(data) => {
          const done = setupDone(data, manual);
          return (
            <>
              {!done && (
                <section aria-labelledby="start-title" className={styles.start}>
                  <h3 id="start-title" className={styles.startTitle}>
                    {t("pages.setup.start.title", { start: data.schedule.start_at })}
                  </h3>
                  <HowTo />
                </section>
              )}
              <ManualSteps />
              <AutoSetup overview={data} />
              <Guide overview={data} howto={done} />
            </>
          );
        }}
      </QueryView>
    </div>
  );
}
