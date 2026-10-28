import { useState } from "react";
import { useTranslation } from "react-i18next";
import { errorMessage } from "../../api/errors";
import { useSaveSettings, useStartDryRun, useSwitchSchedule } from "../../api/mutations";
import { useAccounts, useRuns, useSettings } from "../../api/queries";
import type {
  AccountSubdivision,
  Overview,
  Running,
  RunSummary,
  ScheduleState,
  Settings,
} from "../../api/types";
import {
  courtChoices,
  firstCourt,
  inSubdivision,
  isSport,
  MAX_SLOTS,
  SUBDIVISIONS,
  shownSubdivision,
  slotChoices,
  sportChoices,
  toggleSlot,
} from "../../booking";
import { Button } from "../../components/Button";
import { Icon } from "../../components/Icon";
import { Overline } from "../../components/Overline";
import { QueryView } from "../../components/QueryView";
import { Switch } from "../../components/Switch";
import { localToday } from "../../format";
import { quietEnd } from "../../quiet";
import { failureReason } from "../../reasons";
import { useFormat } from "../../useFormat";
import styles from "./BookingTicket.module.css";
import { NotifySwitch } from "./NotifySwitch";
import { TicketFrame } from "./TicketFrame";

/** The slots sit in rows of this many: the six of the morning, then the seven after. */
const GRID_COLUMNS = 7;

/** What one MuMu instance books: the top of the settings, or one of their instances. */
type Booking = Pick<Settings, "mumu_index" | "slots" | "subdivision" | "sport" | "court">;

/** Return the subdivision the account of MuMu instance `index` told last, if any. */
function toldBy(accounts: readonly AccountSubdivision[] | undefined, index: number) {
  return accounts?.find((account) => account.device === index)?.subdivision;
}

/** Return what instance `index` books (0: the top of the settings), the last if it is gone. */
function bookingOf(settings: Settings, index: number): { index: number; booking: Booking } {
  const all = [settings, ...settings.instances];
  const place = Math.min(index, all.length - 1);
  return { index: place, booking: all[place] ?? settings };
}

/** Return the settings with ``change`` made to instance ``index`` (0: the top). */
function changed(settings: Settings, index: number, change: Partial<Booking>): Settings {
  if (index === 0) {
    return { ...settings, ...change };
  }
  const instances = settings.instances.map((instance, place) =>
    place === index - 1 ? { ...instance, ...change } : instance,
  );
  return { ...settings, instances };
}

type SaveSettings = ReturnType<typeof useSaveSettings>;

/** Return the settings to show: while a save is on its way, what it saves. */
function shownSettings(saved: Settings, save: SaveSettings): Settings {
  return save.isPending && save.variables !== undefined ? save.variables : saved;
}

interface NextBookingProps {
  schedule: ScheduleState;
  /** What the choices below hold, `undefined` until the settings have loaded. */
  booking: Booking | undefined;
}

/**
 * The top of the ticket shows what is set, and only that: the daily switch and the result
 * notification's beside it, then the play day (always two days after the start) and the court side by side, and the slots in booking
 * order (the choices below number them) on a row of their own, as the choices below hold them; the rows stay put whatever
 * the court's name. While the switch is off a line says that nothing is booked. The switch
 * stays locked until a dry run has passed; once one has, a switch still off is set off.
 */
function NextBooking({ schedule, booking }: NextBookingProps) {
  const { t } = useTranslation();
  const f = useFormat();
  const toggle = useSwitchSchedule();
  const locked = !schedule.enabled && !schedule.dry_run_passed;
  const remind = !schedule.enabled && schedule.dry_run_passed;
  const when = f.when(schedule.next_start, localToday());
  return (
    <>
      <div className={styles.head}>
        <Overline as="h2" id="next-title">
          {t("pages.ticket.title")}
        </Overline>
        <div className={styles.switches}>
          <div className={remind ? `${styles.auto} ${styles.remind}` : styles.auto}>
            <span aria-hidden="true">{t("pages.ticket.autoShort")}</span>
            <Switch
              label={t("pages.ticket.auto")}
              checked={schedule.enabled}
              disabled={locked || toggle.isPending}
              onChange={(enabled) => toggle.mutate(enabled)}
              onText={t("pages.ticket.on")}
              offText={t("pages.ticket.off")}
            />
          </div>
          <NotifySwitch />
        </div>
      </div>
      <dl className={schedule.enabled ? styles.summary : `${styles.summary} ${styles.off}`}>
        <div className={styles.field}>
          <Overline as="dt">{t("pages.ticket.day")}</Overline>
          <dd>{f.shortDay(schedule.next_play_date)}</dd>
        </div>
        <div className={styles.field}>
          <Overline as="dt">{t("pages.ticket.court")}</Overline>
          <dd>{booking === undefined ? "–" : f.court(booking.court)}</dd>
        </div>
        <div className={`${styles.field} ${styles.slotsField}`}>
          <Overline as="dt">{t("pages.ticket.chosenSlots")}</Overline>
          <dd className={styles.chosen}>
            {booking === undefined
              ? "–"
              : booking.slots.map((slot) => (
                  <span key={slot} className={styles.chosenSlot}>
                    {f.slot(slot)}
                  </span>
                ))}
          </dd>
        </div>
      </dl>
      {!schedule.enabled && (
        <p className={styles.plan}>
          <Icon name="clock" />
          <strong>{t(locked ? "pages.ticket.lockedTitle" : "pages.ticket.offTitle")}</strong>{" "}
          {locked ? t("pages.ticket.locked") : t("pages.ticket.offLine", { when })}
        </p>
      )}
      {toggle.isError && <p className={styles.problem}>{errorMessage(t, toggle.error)}</p>}
    </>
  );
}

interface ChoicesProps {
  saved: Settings;
  save: SaveSettings;
  /** The subdivision each account told last, `undefined` until read. */
  accounts: readonly AccountSubdivision[] | undefined;
  /** The MuMu instance whose choices show (0: the top of the settings). */
  instance: number;
  onInstance: (index: number) => void;
}

/**
 * The subdivision, sport, court and slots to book, for each MuMu instance when several book
 * side by side, each with its own account. Each press saves at once: the whole settings go
 * back as they came with the one change, so the developer's values stay; another sport takes
 * its first court, another subdivision keeps the sport if it has it. Presses wait while a save
 * is on its way, so two saves never cross. The subdivision follows the account until one is
 * pressed.
 */
function Choices({ saved, save, accounts, instance, onInstance }: ChoicesProps) {
  const { t } = useTranslation();
  const f = useFormat();
  const [warning, setWarning] = useState<string | null>(null);
  const busy = save.isPending;
  const settings = shownSettings(saved, save);
  const instances = [settings, ...settings.instances];
  const { index, booking: shown } = bookingOf(settings, instance);
  const { booking: own } = bookingOf(saved, index);
  const full = shown.slots.length >= MAX_SLOTS;
  const told = toldBy(accounts, shown.mumu_index);
  const subdivision = shownSubdivision(shown.subdivision, told);
  const byAccount = shown.subdivision === "" && told !== undefined;

  function choose(change: Partial<Booking>) {
    if (busy) {
      return;
    }
    setWarning(null);
    save.mutate(changed(saved, index, change));
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

  // A court set by hand stays a choice, but not under another sport on its way.
  const courts = courtChoices(
    subdivision,
    shown.sport,
    own.sport === shown.sport ? own.court : shown.court,
  );
  const { morning, afternoon } = slotChoices(shown.slots);
  // The morning row keeps its empty places, so the afternoon starts a row of its own.
  const gaps = (GRID_COLUMNS - (morning.length % GRID_COLUMNS)) % GRID_COLUMNS;
  const cells = [...morning, ...Array<null>(gaps).fill(null), ...afternoon];

  return (
    <div aria-busy={busy} className={styles.choices}>
      {instances.length > 1 && (
        <div role="group" aria-labelledby="instance-label" className={styles.group}>
          <Overline as="span" id="instance-label">
            {t("pages.ticket.instance")}
          </Overline>
          <div className={styles.buttons}>
            {instances.map((item, place) => (
              <button
                key={item.mumu_index}
                type="button"
                aria-pressed={place === index}
                className={`${styles.choice} ${styles.court}`}
                onClick={() => {
                  setWarning(null);
                  onInstance(place);
                }}
              >
                {t("pages.ticket.instanceName", { index: item.mumu_index })}
              </button>
            ))}
          </div>
        </div>
      )}
      <div role="group" aria-labelledby="subdivision-label" className={styles.group}>
        <div className={styles.slotsHead}>
          <Overline as="span" id="subdivision-label">
            {t("pages.ticket.subdivision")}
          </Overline>
          {byAccount && <span className={styles.note}>{t("pages.ticket.byAccount")}</span>}
        </div>
        <div className={styles.buttons}>
          {SUBDIVISIONS.map((item) => {
            const on = subdivision.id === item.id;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={on}
                aria-disabled={busy || undefined}
                className={`${styles.choice} ${styles.court}`}
                onClick={() =>
                  shown.subdivision !== item.id && choose(inSubdivision(item, shown.sport))
                }
              >
                {item.name}
              </button>
            );
          })}
        </div>
      </div>

      <div role="group" aria-labelledby="sport-label" className={styles.group}>
        <Overline as="span" id="sport-label">
          {t("pages.ticket.sport")}
        </Overline>
        <div className={`${styles.buttons} ${styles.wrap}`}>
          {sportChoices(subdivision, shown.sport).map((sport) => {
            const on = shown.sport === sport;
            return (
              <button
                key={sport}
                type="button"
                aria-pressed={on}
                aria-disabled={busy || undefined}
                className={`${styles.choice} ${styles.sport}`}
                onClick={() => !on && choose({ sport, court: firstCourt(subdivision, sport) })}
              >
                {isSport(sport) ? t(`sports.${sport}`) : sport}
              </button>
            );
          })}
        </div>
      </div>

      <div role="group" aria-labelledby="court-label" className={styles.group}>
        <Overline as="span" id="court-label">
          {t("pages.ticket.court")}
        </Overline>
        <div className={`${styles.buttons} ${styles.wrap}`}>
          {courts.map((court) => {
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
                {f.courtLabel(court)}
              </button>
            );
          })}
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
 * The next booking as a ticket in two parts: on top what is set (the daily switch, the play
 * day, court and slots, when it starts), under the perforation the sport, court and slots to
 * choose, saved on each press, and the dry run at the foot. A press shows on top at once,
 * as the save goes out.
 */
export function BookingTicket({ overview }: { overview: Overview }) {
  const settings = useSettings();
  const accounts = useAccounts();
  const save = useSaveSettings();
  const [instance, setInstance] = useState(0);
  const { schedule, running } = overview;
  const booking =
    settings.data === undefined
      ? undefined
      : bookingOf(shownSettings(settings.data, save), instance).booking;
  return (
    <TicketFrame
      aria-labelledby="next-title"
      top={<NextBooking schedule={schedule} booking={booking} />}
      contained
    >
      <div className={styles.scroll}>
        <QueryView query={settings}>
          {(saved) => (
            <Choices
              saved={saved}
              save={save}
              accounts={accounts.data}
              instance={instance}
              onInstance={setInstance}
            />
          )}
        </QueryView>
      </div>
      <DryRunRow running={running} schedule={schedule} />
    </TicketFrame>
  );
}
