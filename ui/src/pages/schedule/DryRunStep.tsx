import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { errorMessage } from "../../api/errors";
import { useStartDryRun } from "../../api/mutations";
import { useRuns } from "../../api/queries";
import type { Running, RunSummary } from "../../api/types";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { Overline } from "../../components/Overline";
import { localToday } from "../../format";
import { paths } from "../../paths";
import { quietEnd } from "../../quiet";
import { failureReason } from "../../reasons";
import { useFormat } from "../../useFormat";
import styles from "./DryRunStep.module.css";

/** The newest dry run in a line: when, and whether it passed or why not. */
function LastDryRun({ run }: { run: RunSummary | undefined }) {
  const { t } = useTranslation();
  const f = useFormat();
  if (run === undefined) {
    return <p className={styles.last}>{t("pages.schedule.dryRun.none")}</p>;
  }
  const at = { when: f.when(run.started_at, localToday()), time: f.time(run.started_at) };
  if (run.status === "running") {
    return null;
  }
  if (run.status === "ok") {
    return <p className={styles.last}>{t("pages.schedule.dryRun.passed", at)}</p>;
  }
  if (run.status === "interrupted") {
    return <p className={styles.failed}>{t("pages.schedule.dryRun.stopped", at)}</p>;
  }
  const reason = run.error ?? run.slots.find((slot) => !slot.ok)?.reason ?? null;
  return (
    <p className={styles.failed}>
      {t("pages.schedule.dryRun.failed", { ...at, reason: failureReason(t, f, reason) })}
    </p>
  );
}

interface DryRunStepProps {
  running: Running | null;
  wake: string;
  start: string;
}

/**
 * Step 1: the dry run walks the whole booking and stops before "Xác nhận"; the schedule
 * needs one to pass. Its steps show on the Overview, not here.
 */
export function DryRunStep({ running, wake, start }: DryRunStepProps) {
  const { t } = useTranslation();
  const dryRun = useStartDryRun();
  const last = useRuns({ dry_run: true, limit: 1 });
  return (
    <Card as="section" aria-labelledby="dry-run-title" className={styles.step}>
      <div className={styles.text}>
        <Overline>{t("pages.schedule.dryRun.step")}</Overline>
        <h2 id="dry-run-title" className={styles.title}>
          {t("pages.schedule.dryRun.title")}
        </h2>
        <p className={styles.about}>{t("pages.schedule.dryRun.about")}</p>
        {running !== null ? (
          <p className={styles.last}>
            {t(
              running.trigger === "dry_run"
                ? "pages.schedule.dryRun.running"
                : "pages.overview.live.locked",
            )}{" "}
            <Link to={paths.overview}>{t("pages.schedule.dryRun.follow")}</Link>
          </p>
        ) : (
          last.data !== undefined && <LastDryRun run={last.data[0]} />
        )}
        {dryRun.isError && <p className={styles.failed}>{errorMessage(t, dryRun.error)}</p>}
      </div>
      <div className={styles.action}>
        <Button
          size="large"
          disabled={running !== null || dryRun.isPending}
          onClick={() => dryRun.mutate()}
        >
          {t(dryRun.isPending ? "pages.schedule.dryRun.starting" : "pages.schedule.dryRun.button")}
        </Button>
        <p className={styles.note}>
          {t("pages.deviceSetup.auto.quiet", {
            from: wake,
            to: quietEnd(start),
          })}
        </p>
      </div>
    </Card>
  );
}
