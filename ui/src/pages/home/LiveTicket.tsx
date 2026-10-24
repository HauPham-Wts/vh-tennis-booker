import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useRunSteps } from "../../api/runSteps";
import type { Step } from "../../api/types";
import { Overline } from "../../components/Overline";
import { stepMessage } from "../../steps";
import { useFormat } from "../../useFormat";
import styles from "./LiveTicket.module.css";
import { progressOf } from "./progress";
import { TicketFrame } from "./TicketFrame";

/** A closed padlock: the choices wait for the run to end. */
function Padlock() {
  return (
    <svg
      aria-hidden="true"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

/**
 * The run as it goes: the slot being booked large with its round and the progress on top,
 * every step so far under the perforation with the newest one marked, then the slots still
 * to come. It is drawn from the steps the live feed brings: no request per step.
 */
function Live({ steps }: { steps: readonly Step[] }) {
  const { t } = useTranslation();
  const f = useFormat();
  const listRef = useRef<HTMLOListElement>(null);
  const progress = progressOf(steps);
  const big = progress.current ?? progress.slots[0];
  const round = big === undefined ? 0 : progress.slots.indexOf(big) + 1;

  // Keep the newest step in view as the list grows past the ticket: only the slots still
  // to come follow it.
  useEffect(() => {
    const list = listRef.current;
    if (list !== null) {
      list.scrollTop = list.scrollHeight;
    }
  }, [steps.length]);

  const top = (
    <>
      <div className={styles.head}>
        <Overline as="h2" id="live">
          {progress.date !== undefined && progress.court !== undefined
            ? t(progress.dryRun ? "pages.ticket.live.dryRun" : "pages.ticket.live.booking", {
                day: f.day(progress.date),
                court: f.court(progress.court),
              })
            : t("pages.ticket.live.preparing")}
        </Overline>
        {round > 0 && (
          <span className={styles.round}>
            {t("pages.ticket.live.round", { round, rounds: progress.slots.length })}
          </span>
        )}
      </div>
      <div className={styles.now}>
        {big !== undefined && <p className={styles.slot}>{f.slot(big)}</p>}
        <div className={styles.progress}>
          <p>
            <strong className={styles.count}>
              {progress.booked}/{progress.slots.length}
            </strong>{" "}
            {t(progress.dryRun ? "pages.ticket.live.through" : "pages.ticket.live.booked")}
          </p>
          <div aria-hidden="true" className={styles.bars}>
            {progress.states.map(({ slot, state }) => (
              <span key={slot} className={`${styles.bar} ${styles[state]}`} />
            ))}
          </div>
        </div>
      </div>
    </>
  );

  return (
    <TicketFrame aria-labelledby="live" top={top} contained>
      <ol ref={listRef} className={styles.steps}>
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
                {newest ? t("pages.ticket.live.running") : f.clock(step.time)}
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
              {t("pages.ticket.live.waiting", { slot: f.slot(slot) })}
            </span>
          </li>
        ))}
      </ol>
      <p className={styles.locked}>
        <Padlock />
        {t("pages.ticket.live.locked")}
      </p>
    </TicketFrame>
  );
}

function LiveSteps({ runId }: { runId: number }) {
  const { steps } = useRunSteps(runId);
  return <Live steps={steps} />;
}

/**
 * The ticket while a booking or a dry run holds the emulator, in place of the choices; it
 * says "Đang chuẩn bị" while a dry run the app just started has not written a step yet.
 */
export function LiveTicket({ runId }: { runId?: number }) {
  return runId === undefined ? <Live steps={[]} /> : <LiveSteps runId={runId} />;
}
