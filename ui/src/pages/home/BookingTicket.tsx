import { useState } from "react";
import { useTranslation } from "react-i18next";
import { errorMessage } from "../../api/errors";
import { useSaveSettings, useStartDryRun, useSwitchSchedule } from "../../api/mutations";
import { useRuns, useSettings } from "../../api/queries";
import type { Overview, Running, RunSummary, ScheduleState, Settings } from "../../api/types";
import { courtChoices, MAX_SLOTS, playDates, slotChoices, toggleSlot } from "../../booking";
import { Button } from "../../components/Button";
import { Overline } from "../../components/Overline";
import { QueryView } from "../../components/QueryView";
import { Switch } from "../../components/Switch";
import { localToday } from "../../format";
import { quietEnd } from "../../quiet";
import { failureReason } from "../../reasons";
import { useFormat } from "../../useFormat";
import styles from "./BookingTicket.module.css";
import { TicketFrame } from "./TicketFrame";

/** The slots sit in rows of this many: the six of the morning, then the seven after. */
const GRID_COLUMNS = 7;

/**
 * The top of the ticket: the daily switch, then the start time large with its day and
 * wake time, or that nothing is booked while the switch is off. The switch stays locked
 * until a dry run has passed; once one has, a switch still off is set off in yellow.
 */
function NextStart({ schedule }: { schedule: ScheduleState }) {
  const { t } = useTranslation();
  const f = useFormat();
  const toggle = useSwitchSchedule();
  const locked = !schedule.enabled && !schedule.dry_run_passed;
  const remind = !schedule.enabled && schedule.dry_run_passed;
  const start = schedule.next_start;
  const when = f.when(start, localToday());
  return (
    <>
      <div className={styles.head}>
        <Overline as="h2" id="next-title">
          {t("pages.ticket.title")}
        </Overline>
        <div className={remind ? `${styles.auto} ${styles.remind}` : styles.auto}>
          <span aria-hidden="true">{t("pages.ticket.auto")}</span>
          <Switch
            label={t("pages.ticket.auto")}
            checked={schedule.enabled}
            disabled={locked || toggle.isPending}
            onChange={(enabled) => toggle.mutate(enabled)}
            onText={t("pages.ticket.on")}
            offText={t("pages.ticket.off")}
          />
        </div>
      </div>
      <div className={styles.start}>
        <p className={schedule.enabled ? styles.time : `${styles.time} ${styles.off}`}>
          {f.time(start)}
        </p>
        <div className={styles.when}>
          {schedule.enabled ? (
            <>
              <p className={styles.day}>{t("pages.ticket.when", { when, day: f.day(start) })}</p>
              <p className={styles.wake}>{t("pages.ticket.wake", { wake: schedule.wake_at })}</p>
            </>
          ) : (
            <>
              <p className={`${styles.day} ${styles.off}`}>
                {t(locked ? "pages.ticket.lockedTitle" : "pages.ticket.offTitle")}
              </p>
              <p className={styles.offLine}>
                {locked ? t("pages.ticket.locked") : t("pages.ticket.offLine", { when })}
              </p>
            </>
          )}
          {toggle.isError && <p className={styles.problem}>{errorMessage(t, toggle.error)}</p>}
        </div>
      </div>
    </>
  );
}

interface ChoicesProps {
  saved: Settings;
  nextStart: string;
}

/**
 * The day, court and slots to book. Each press saves at once: the whole settings go back
 * as they came with the one change, so the developer's values stay. Presses wait while a
 * save is on its way, so two saves never cross.
 */
function Choices({ saved, nextStart }: ChoicesProps) {
  const { t } = useTranslation();
  const f = useFormat();
  const save = useSaveSettings();
  const [warning, setWarning] = useState<string | null>(null);
  const busy = save.isPending;
  // While a save is on its way, show what it saves.
  const shown = busy && save.variables !== undefined ? save.variables : saved;
  const full = shown.slots.length >= MAX_SLOTS;

  function choose(change: Partial<Settings>) {
    if (busy) {
      return;
    }
    setWarning(null);
    save.mutate({ ...saved, ...change });
  }

  function toggle(slot: string) {
    if (busy) {
      return;
    }
    const chosen = shown.slots.includes(slot);
    if (chosen && shown.slots.length === 1) {
      setWarning(t("pages.ticket.oneSlot"));
    } else if (!chosen && full) {
      setWarning(t("pages.ticket.full", { max: MAX_SLOTS }));
    } else {
      choose({ slots: toggleSlot(shown.slots, slot) });
    }
  }

  let note = <span className={styles.note}>{t("pages.ticket.pressToSave")}</span>;
  if (warning !== null) {
    note = <span className={styles.warning}>{warning}</span>;
  } else if (save.isError) {
    note = <span className={styles.warning}>{errorMessage(t, save.error)}</span>;
  } else if (busy) {
    note = <span className={styles.note}>{t("pages.ticket.saving")}</span>;
  } else if (save.isSuccess) {
    note = <span className={styles.note}>{t("pages.ticket.saved")}</span>;
  }

  const { morning, afternoon } = slotChoices(shown.slots);
  // The morning row keeps its empty places, so the afternoon starts a row of its own.
  const gaps = (GRID_COLUMNS - (morning.length % GRID_COLUMNS)) % GRID_COLUMNS;
  const cells = [...morning, ...Array<null>(gaps).fill(null), ...afternoon];

  return (
    <div aria-busy={busy} className={styles.choices}>
      <div className={styles.row}>
        <div role="group" aria-labelledby="day-label" className={styles.group}>
          <Overline as="span" id="day-label">
            {t("pages.ticket.day")}
          </Overline>
          <div className={styles.buttons}>
            {playDates(nextStart).map(({ daysAhead, date }) => {
              const on = shown.days_ahead === daysAhead;
              return (
                <button
                  key={daysAhead}
                  type="button"
                  aria-pressed={on}
                  aria-disabled={busy || undefined}
                  className={`${styles.choice} ${styles.dayChoice}`}
                  onClick={() => !on && choose({ days_ahead: daysAhead })}
                >
                  <span className={styles.date}>{f.day(date)}</span>
                  <span className={styles.hint}>{t(`pages.ticket.dayHint.${daysAhead}`)}</span>
                </button>
              );
            })}
          </div>
        </div>
        <div role="group" aria-labelledby="court-label" className={styles.group}>
          <Overline as="span" id="court-label">
            {t("pages.ticket.court")}
          </Overline>
          <div className={styles.buttons}>
            {courtChoices(saved.court).map((court) => {
              const on = shown.court === court;
              return (
                <button
                  key={court}
                  type="button"
                  aria-pressed={on}
                  aria-disabled={busy || undefined}
                  className={`${styles.choice} ${styles.court}`}
                  onClick={() => !on && choose({ court })}
                >
                  {f.court(court)}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div role="group" aria-labelledby="slots-label" className={styles.group}>
        <div className={styles.slotsHead}>
          <Overline as="span" id="slots-label">
            {t("pages.ticket.slots", { max: MAX_SLOTS })}
          </Overline>
          <span aria-live="polite">{note}</span>
        </div>
        <div className={styles.grid}>
          {cells.map((slot, index) => {
            if (slot === null) {
              return <span key={`gap-${index}`} aria-hidden="true" />;
            }
            const order = shown.slots.indexOf(slot) + 1;
            const blocked = order === 0 && full;
            return (
              <button
                key={slot}
                type="button"
                aria-pressed={order > 0}
                aria-disabled={busy || blocked || undefined}
                aria-label={
                  order > 0 ? t("pages.ticket.slot", { slot: f.slot(slot), order }) : undefined
                }
                className={blocked ? `${styles.slot} ${styles.blocked}` : styles.slot}
                onClick={() => toggle(slot)}
              >
                {f.slot(slot)}
                {order > 0 && (
                  <span aria-hidden="true" className={styles.order}>
                    {order}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/** The newest dry run in a line: when, and whether it passed or why not. */
function LastDryRun({ run }: { run: RunSummary | undefined }) {
  const { t } = useTranslation();
  const f = useFormat();
  if (run === undefined) {
    return <p>{t("pages.ticket.dryRun.none")}</p>;
  }
  if (run.status === "running") {
    return null;
  }
  const at = { when: f.when(run.started_at, localToday()), time: f.time(run.started_at) };
  let result: string;
  if (run.status === "ok") {
    result = t("pages.ticket.dryRun.passed");
  } else if (run.status === "interrupted") {
    result = t("pages.ticket.dryRun.stopped");
  } else {
    const reason = run.error ?? run.slots.find((slot) => !slot.ok)?.reason ?? null;
    result = t("pages.ticket.dryRun.failed", { reason: failureReason(t, f, reason) });
  }
  return (
    <p>
      {t("pages.ticket.dryRun.last", at)} ·{" "}
      <strong className={run.status === "ok" ? styles.passed : styles.failed}>{result}</strong>
    </p>
  );
}

interface DryRunRowProps {
  running: Running | null;
  schedule: ScheduleState;
}

/**
 * The foot of the ticket: the last dry run and a button for another. The dry run walks
 * the whole booking and stops before "Xác nhận"; the backend refuses one in the quiet
 * time, and none starts while another run holds the emulator.
 */
function DryRunRow({ running, schedule }: DryRunRowProps) {
  const { t } = useTranslation();
  const dryRun = useStartDryRun();
  const last = useRuns({ dry_run: true, limit: 1 });
  return (
    <div className={styles.dryRun}>
      <div className={styles.dryRunText}>
        {running !== null ? (
          <p>{t("pages.overview.live.locked")}</p>
        ) : (
          last.data !== undefined && <LastDryRun run={last.data[0]} />
        )}
        {dryRun.isError ? (
          <p className={styles.problem}>{errorMessage(t, dryRun.error)}</p>
        ) : (
          <p className={styles.quiet}>
            {t("pages.ticket.dryRun.quiet", {
              from: schedule.wake_at,
              to: quietEnd(schedule.start_at),
            })}
          </p>
        )}
      </div>
      <Button disabled={running !== null || dryRun.isPending} onClick={() => dryRun.mutate()}>
        {t(dryRun.isPending ? "pages.ticket.dryRun.starting" : "pages.ticket.dryRun.button")}
      </Button>
    </div>
  );
}

/**
 * The next booking as a ticket that holds its settings: the daily switch and the start
 * time on top; the day, court and slots under the perforation, saved on each press; the
 * dry run at the foot.
 */
export function BookingTicket({ overview }: { overview: Overview }) {
  const settings = useSettings();
  const { schedule, running } = overview;
  return (
    <TicketFrame aria-labelledby="next-title" top={<NextStart schedule={schedule} />}>
      <QueryView query={settings}>
        {(saved) => <Choices saved={saved} nextStart={schedule.next_start} />}
      </QueryView>
      <DryRunRow running={running} schedule={schedule} />
    </TicketFrame>
  );
}
