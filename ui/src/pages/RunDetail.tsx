import { useTranslation } from "react-i18next";
import { useRunSteps } from "../api/runSteps";
import type { LogLine, RunDetail as Run, Step } from "../api/types";
import { Card } from "../components/Card";
import { Overline } from "../components/Overline";
import { QueryView } from "../components/QueryView";
import { Stamp } from "../components/Stamp";
import { runStamp, triggerName } from "../runs";
import { stepMessage } from "../steps";
import { useFormat } from "../useFormat";
import styles from "./RunDetail.module.css";

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
      <summary>{t("pages.activity.technical")}</summary>
      <pre>{text}</pre>
    </details>
  );
}

function RunHeader({ run }: { run: Run }) {
  const { t } = useTranslation();
  const f = useFormat();
  const stamp = runStamp(t, run);
  const trigger = triggerName(t, run.trigger);
  const meta =
    run.play_date !== null && run.court !== null
      ? t("pages.activity.meta", {
          trigger,
          day: f.day(run.play_date),
          court: f.court(run.court),
        })
      : trigger;
  return (
    <div className={styles.header}>
      <div className={styles.heading}>
        <h2 id="run-title" className={styles.title}>
          {t("pages.activity.runTitle", {
            period: f.period(run.started_at),
            day: f.day(run.started_at),
          })}
        </h2>
        <Overline>{meta}</Overline>
      </div>
      <Stamp tone={stamp.tone}>{stamp.text}</Stamp>
    </div>
  );
}

/** One run: what it was, its result, every step as it happened, and its technical log. */
export function RunDetail({ runId }: { runId: number }) {
  const { run, steps } = useRunSteps(runId);
  return (
    <Card as="article" aria-labelledby="run-title" className={styles.detail}>
      <QueryView query={run}>
        {(detail) => (
          <>
            <RunHeader run={detail} />
            <ol className={styles.steps}>
              {steps.map((step) => (
                <StepLine key={step.id} step={step} />
              ))}
            </ol>
            {detail.log_lines.length > 0 && <TechnicalLog lines={detail.log_lines} />}
          </>
        )}
      </QueryView>
    </Card>
  );
}
