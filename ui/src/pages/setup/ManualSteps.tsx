import type { UseQueryResult } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { Overview, SetupItem } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Stamp } from "../../components/Stamp";
import { ErrorNotice } from "../../components/States";
import { paths } from "../../paths";
import { isLoggedOut } from "../../reasons";
import styles from "./ManualSteps.module.css";

type State = "done" | "todo" | "unknown" | "checking";

/** What to do next, under a step's text. */
type Hint =
  | "pages.deviceSetup.items.mumu.todo"
  | "pages.deviceSetup.items.app.todo"
  | "pages.deviceSetup.items.app.unknown"
  | "pages.deviceSetup.items.login.todo"
  | "pages.deviceSetup.items.login.unknown";

interface Step {
  key: "mumu" | "app" | "login";
  state: State;
  /** Nothing once the step is done, or while its check has not answered. */
  hint?: Hint;
}

const STAMP_TONES = {
  done: "booked",
  todo: "failed",
  unknown: "muted",
  checking: "muted",
} as const;

function statusOf(checks: SetupItem[] | undefined, item: string) {
  return checks?.find((check) => check.item === item)?.status;
}

/**
 * Return the three steps only the user can do. MuMu and the app come from the checks
 * (MuMu found but not saved yet counts as installed: auto setup saves it); the login has
 * no check of its own, so it comes from the runs: a run the app never let in asks to log
 * in again, a passed dry run shows it done.
 */
function stepsOf(overview: Overview, checks: UseQueryResult<SetupItem[]>): Step[] {
  const mumu = statusOf(checks.data, "mumu_installed");
  const app = statusOf(checks.data, "app_installed");
  // Before the first answer, a step being checked is not "not sure" yet.
  const waiting: State = checks.isFetching ? "checking" : "unknown";
  const steps: Step[] = [];

  if (mumu === undefined || mumu === "unknown") {
    steps.push({ key: "mumu", state: mumu === undefined ? waiting : "unknown" });
  } else if (mumu === "user") {
    steps.push({ key: "mumu", state: "todo", hint: "pages.deviceSetup.items.mumu.todo" });
  } else {
    steps.push({ key: "mumu", state: "done" });
  }

  if (app === undefined) {
    steps.push({ key: "app", state: waiting });
  } else if (app === "unknown") {
    steps.push({ key: "app", state: "unknown", hint: "pages.deviceSetup.items.app.unknown" });
  } else if (app === "user") {
    steps.push({ key: "app", state: "todo", hint: "pages.deviceSetup.items.app.todo" });
  } else {
    steps.push({ key: "app", state: "done" });
  }

  if (isLoggedOut(overview.last_run?.error ?? null)) {
    steps.push({ key: "login", state: "todo", hint: "pages.deviceSetup.items.login.todo" });
  } else if (overview.schedule.dry_run_passed) {
    steps.push({ key: "login", state: "done" });
  } else {
    steps.push({ key: "login", state: "unknown", hint: "pages.deviceSetup.items.login.unknown" });
  }
  return steps;
}

interface ManualStepsProps {
  overview: Overview;
  checks: UseQueryResult<SetupItem[]>;
  /** A run holds the lock: the checks wait for it to end. */
  running: boolean;
  onCheck: () => void;
}

/** The steps only the user can do, each marked done or not, with what to do next. */
export function ManualSteps({ overview, checks, running, onCheck }: ManualStepsProps) {
  const { t } = useTranslation();
  const steps = stepsOf(overview, checks);
  const done = steps.filter((step) => step.state === "done").length;
  const current = steps.find((step) => step.state !== "done");
  return (
    <section aria-labelledby="manual-title" className={styles.section}>
      <div className={styles.head}>
        <h2 id="manual-title" className={styles.title}>
          {t("pages.deviceSetup.manual.title")}
        </h2>
        <span className={styles.count}>
          {t("pages.deviceSetup.manual.done", { done, total: steps.length })}
        </span>
        <Button onClick={onCheck} disabled={running || checks.isFetching}>
          {t(
            checks.isFetching
              ? "pages.deviceSetup.manual.checking"
              : "pages.deviceSetup.manual.check",
          )}
        </Button>
      </div>
      {running && <p className={styles.quiet}>{t("pages.deviceSetup.manual.waitRun")}</p>}
      {checks.isError && <ErrorNotice error={checks.error} />}
      <ol className={styles.list}>
        {steps.map((step, index) => (
          <Card
            as="li"
            key={step.key}
            className={step === current ? `${styles.step} ${styles.current}` : styles.step}
          >
            <span aria-hidden="true" className={styles.number}>
              {index + 1}
            </span>
            <div className={styles.body}>
              <h3 className={styles.name}>{t(`pages.deviceSetup.items.${step.key}.title`)}</h3>
              <p className={styles.text}>{t(`pages.deviceSetup.items.${step.key}.text`)}</p>
              {step.hint !== undefined && (
                <p className={styles.hint}>
                  {t(step.hint)}
                  {step.key === "login" && step.state === "unknown" && (
                    <>
                      {" "}
                      <Link to={paths.schedule}>{t("pages.deviceSetup.items.login.link")}</Link>
                    </>
                  )}
                </p>
              )}
            </div>
            <Stamp tone={STAMP_TONES[step.state]}>
              {t(`pages.deviceSetup.state.${step.state}`)}
            </Stamp>
          </Card>
        ))}
      </ol>
    </section>
  );
}
