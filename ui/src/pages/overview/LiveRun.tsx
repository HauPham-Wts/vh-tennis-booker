import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useRunSteps } from "../../api/runSteps";
import type { Step } from "../../api/types";
import { Overline } from "../../components/Overline";
import { Ticket } from "../../components/Ticket";
import { paths } from "../../paths";
import { stepMessage } from "../../steps";
import { useFormat } from "../../useFormat";
import styles from "./LiveRun.module.css";
import { progressOf } from "./progress";

/**
 * The run as it goes: what it books, the slot being booked, every step so far with the
 * newest one marked, the slots still to come, and the progress on the stub. It is drawn
 * from the steps the live feed brings: no request per step.
 */
function LiveTicket({ runId, steps }: { runId?: number; steps: readonly Step[] }) {
  const { t } = useTranslation();
  const f = useFormat();
  const progress = progressOf(steps);
  const big = progress.current ?? progress.slots[0];
  return (
    <Ticket
      as="section"
      aria-labelledby="live"
      stub={
        <>
          <Overline>{t("pages.overview.live.progress")}</Overline>
          <p className={styles.count}>
            {progress.booked}/{progress.slots.length}
          </p>
          <p className={styles.quiet}>
            {t(progress.dryRun ? "pages.overview.live.through" : "pages.overview.live.booked")}
          </p>
          <div aria-hidden="true" className={styles.bars}>
            {progress.states.map(({ slot, state }) => (
              <span key={slot} className={`${styles.bar} ${styles[state]}`} />
            ))}
          </div>
          {runId !== undefined && (
            <Link
              to={{ pathname: paths.activity, search: `?run=${runId}` }}
              className={styles.follow}
            >
              {t("pages.overview.live.follow")}
            </Link>
          )}
        </>
      }
    >
      <Overline as="h2" id="live">
        {progress.date !== undefined && progress.court !== undefined
          ? t("pages.overview.live.booking", {
              day: f.day(progress.date),
              court: f.court(progress.court),
            })
          : t("pages.overview.live.preparing")}
      </Overline>
      {big !== undefined && <p className={styles.slot}>{f.slot(big)}</p>}
      <ol className={styles.steps}>
        {steps.map((step, index) => {
          const message = stepMessage(t, f, step);
          const newest = index === steps.length - 1 && !progress.finished;
          const mark = message.tone === "failed" ? "✕" : "✓";
          return (
            <li
              key={step.id}
              aria-current={newest ? "step" : undefined}
              className={newest ? `${styles.step} ${styles.newest}` : styles.step}
            >
              <span aria-hidden="true" className={styles.marker}>
                {newest ? (
                  <span className={styles.dot} />
                ) : (
                  <span className={message.tone === "failed" ? styles.no : styles.yes}>{mark}</span>
                )}
              </span>
              <span className={styles.text}>{message.text}</span>
              <span className={styles.time}>
                {newest ? t("pages.overview.live.running") : f.clock(step.time)}
              </span>
            </li>
          );
        })}
        {progress.waiting.map((slot) => (
          <li key={slot} className={`${styles.step} ${styles.waiting}`}>
            <span aria-hidden="true" className={styles.marker}>
              <span className={styles.ring} />
            </span>
            <span className={styles.text}>
              {t("pages.overview.live.waiting", { slot: f.slot(slot) })}
            </span>
            <span className={styles.time}>—</span>
          </li>
        ))}
      </ol>
    </Ticket>
  );
}

function LiveRunSteps({ runId }: { runId: number }) {
  const { steps } = useRunSteps(runId);
  return <LiveTicket runId={runId} steps={steps} />;
}

/**
 * The running run, or "Đang chuẩn bị" while a dry run the app just started has not
 * written its first step yet.
 */
export function LiveRun({ runId }: { runId?: number }) {
  const { t } = useTranslation();
  return (
    <>
      {runId === undefined ? <LiveTicket steps={[]} /> : <LiveRunSteps runId={runId} />}
      <p className={styles.note}>{t("pages.overview.live.note")}</p>
    </>
  );
}
