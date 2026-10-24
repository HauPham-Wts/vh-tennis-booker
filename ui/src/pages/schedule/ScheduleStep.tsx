import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { errorMessage } from "../../api/errors";
import { useSwitchSchedule } from "../../api/mutations";
import { useSchedule } from "../../api/queries";
import type { ScheduleState } from "../../api/types";
import { Overline } from "../../components/Overline";
import { QueryView } from "../../components/QueryView";
import { Switch } from "../../components/Switch";
import { Ticket } from "../../components/Ticket";
import { paths } from "../../paths";
import { useFormat } from "../../useFormat";
import styles from "./ScheduleStep.module.css";

/** The habits the PC needs for a task that runs while the user sleeps. */
const HABITS = [
  "pages.schedule.habits.sleep",
  "pages.schedule.habits.signedIn",
  "pages.schedule.habits.plugged",
] as const;

function Habits() {
  const { t } = useTranslation();
  return (
    <>
      <h3 className={styles.habitsTitle}>{t("pages.schedule.habits.title")}</h3>
      <ol className={styles.habits}>
        {HABITS.map((habit) => (
          <li key={habit}>{t(habit)}</li>
        ))}
      </ol>
    </>
  );
}

/** The switch and what it schedules: the times, and the next booking or why it is off. */
function Daily({ state }: { state: ScheduleState }) {
  const { t } = useTranslation();
  const f = useFormat();
  const toggle = useSwitchSchedule();
  // Turning on needs a passed dry run; turning off never does.
  const locked = !state.enabled && !state.dry_run_passed;
  const start = state.next_start;
  return (
    <>
      <div className={styles.head}>
        <div className={styles.heading}>
          <Overline>{t("pages.schedule.daily.step")}</Overline>
          <h2 id="daily-title" className={styles.title}>
            {t("pages.schedule.daily.title")}
          </h2>
        </div>
        <Switch
          label={t("pages.schedule.daily.title")}
          checked={state.enabled}
          disabled={locked || toggle.isPending}
          onChange={(enabled) => toggle.mutate(enabled)}
        />
      </div>
      <dl className={styles.facts}>
        <div>
          <Overline as="dt">{t("pages.schedule.daily.wake")}</Overline>
          <dd>{state.wake_at}</dd>
        </div>
        <div>
          <Overline as="dt">{t("pages.schedule.daily.start")}</Overline>
          <dd>{state.start_at}</dd>
        </div>
        <div>
          <Overline as="dt">{t("pages.schedule.daily.repeat")}</Overline>
          <dd>{t("pages.schedule.daily.everyDay")}</dd>
        </div>
      </dl>
      <p className={styles.next}>
        {state.enabled
          ? t("pages.schedule.daily.next", {
              period: f.period(start),
              day: f.day(start),
              time: f.time(start),
              play: f.day(state.next_play_date),
            })
          : t("pages.schedule.daily.off")}{" "}
        <Link to={paths.overview}>{t("pages.schedule.daily.change")}</Link>
      </p>
      {locked && <p className={styles.note}>{t("errors.dry_run_required")}</p>}
      {toggle.isError && <p className={styles.problem}>{errorMessage(t, toggle.error)}</p>}
    </>
  );
}

/**
 * Step 2: switch the daily booking on or off. The switch creates or removes the Windows
 * task that wakes the PC and books at the start time.
 */
export function ScheduleStep() {
  const schedule = useSchedule();
  return (
    <Ticket as="section" aria-labelledby="daily-title" stub={<Habits />}>
      <QueryView query={schedule}>{(state) => <Daily state={state} />}</QueryView>
    </Ticket>
  );
}
