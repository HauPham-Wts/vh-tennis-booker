import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useRunSteps } from "../../api/runSteps";
import type { LogLine, RunDetail as Run, SlotResult, Step } from "../../api/types";
import { QueryView } from "../../components/QueryView";
import { Stamp } from "../../components/Stamp";
import { paths } from "../../paths";
import { failureReason } from "../../reasons";
import { runStamp } from "../../runs";
import { stepMessage } from "../../steps";
import { useFormat } from "../../useFormat";
import styles from "./RunDetail.module.css";
import { runTitle, runWhen } from "./runText";

/** One step: its time, a ✓ or ✕, its words, the time a slot took and the engine's reason. */
function StepLine({ step }: { step: Step }) {
  const { t } = useTranslation();
  const f = useFormat();
  const message = stepMessage(t, f, step);
  const mark = { booked: "✓ ", failed: "✕ ", moment: "", plain: "" }[message.tone];
  return (
    <li className={styles.step}>
      <span className={styles.time}>{f.clock(step.time)}</span>
      <div>
        <p className={styles[message.tone]}>
          {mark !== "" && (
            <span aria-hidden="true" className={styles.mark}>
              {mark}
            </span>
          )}
          {message.tone === "moment" ? <mark>{message.text}</mark> : message.text}
          {message.extra !== undefined && <span className={styles.extra}> ({message.extra})</span>}
        </p>
        {message.detail !== undefined && <p className={styles.reason}>{message.detail}</p>}
      </div>
    </li>
  );
}

/** The run's own log, closed until asked for: a run writes a few hundred lines. */
function TechnicalLog({ lines }: { lines: LogLine[] }) {
  const { t } = useTranslation();
  // "05:50:04.073 INFO    message": the time of day, the level, the message.
  const text = lines
    .map((line) => `${line.time.slice(11)} ${line.level.padEnd(7)} ${line.message}`)
    .join("\n");
  return (
    <details className={styles.technical}>
      <summary>{t("pages.history.technical")}</summary>
      <pre>{text}</pre>
    </details>
  );
}

/**
 * One slot of the run: booked and when, or why not. A dry run stops before "Xác nhận", so a
 * slot it went through booked nothing.
 */
function SlotLine({ slot, dryRun }: { slot: SlotResult; dryRun: boolean }) {
  const { t } = useTranslation();
  const f = useFormat();
  let tag: string;
  let text: string;
  let tone: "booked" | "failed" | "muted";
  if (!slot.ok) {
    tag = t(dryRun ? "pages.history.slot.notThrough" : "pages.history.slot.failed");
    text = failureReason(t, f, slot.reason);
    tone = "failed";
  } else if (dryRun) {
    tag = t("pages.history.slot.through");
    text = t("pages.history.through");
    tone = "muted";
  } else {
    tag = t("pages.history.slot.booked");
    text = t("pages.history.done", {
      time: f.clock(slot.finished_at),
      seconds: f.seconds(slot.seconds),
    });
    tone = "booked";
  }
  return (
    <li className={styles.slot}>
      <span className={styles.slotHead}>
        <span className={styles.slotTime}>{f.slot(slot.slot)}</span>
        <span className={styles[tone]}>{tag}</span>
      </span>
      <span className={styles.slotText}>{text}</span>
    </li>
  );
}

function RunHeader({ run }: { run: Run }) {
  const { t } = useTranslation();
  const f = useFormat();
  const stamp = runStamp(t, run);
  return (
    <div className={styles.header}>
      <div className={styles.heading}>
        <h3 id="run-title" className={styles.title}>
          {runTitle(t, f, run)}
        </h3>
        <Stamp tone={stamp.tone} size="small">
          {stamp.text}
        </Stamp>
      </div>
      <p className={styles.meta}>{runWhen(t, f, run)}</p>
    </div>
  );
}

/**
 * One run in the History: what it was, its result, each slot and why it failed, every step
 * as it happened, and its technical log. A running run adds its steps as they come.
 */
export function RunDetail({ runId }: { runId: number }) {
  const { t } = useTranslation();
  const f = useFormat();
  const { run, steps } = useRunSteps(runId);
  return (
    <div className={styles.detail}>
      <Link to={paths.overview} className={styles.back}>
        {t("pages.history.back")}
      </Link>
      <QueryView query={run}>
        {(detail) => (
          <article aria-labelledby="run-title" className={styles.run}>
            <RunHeader run={detail} />
            {detail.slots.length > 0 ? (
              <ul className={styles.slots}>
                {detail.slots.map((slot) => (
                  <SlotLine key={slot.slot} slot={slot} dryRun={detail.dry_run} />
                ))}
              </ul>
            ) : (
              detail.error !== null && (
                <p className={styles.failed}>{failureReason(t, f, detail.error)}</p>
              )
            )}
            <h4 className={styles.stepsTitle}>{t("pages.history.steps")}</h4>
            <ol className={styles.steps}>
              {steps.map((step) => (
                <StepLine key={step.id} step={step} />
              ))}
            </ol>
            {detail.log_lines.length > 0 && <TechnicalLog lines={detail.log_lines} />}
          </article>
        )}
      </QueryView>
    </div>
  );
}
