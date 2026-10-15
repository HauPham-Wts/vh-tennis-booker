import { type FormEvent, useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { errorMessage } from "../api/errors";
import { useSaveSettings } from "../api/mutations";
import { useSettings } from "../api/queries";
import type { Settings } from "../api/types";
import { courtChoices, DAYS_AHEAD, slotChoices, toggleSlot } from "../booking";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Overline } from "../components/Overline";
import { QueryView } from "../components/QueryView";
import { useFormat } from "../useFormat";
import styles from "./BookingSettingsPage.module.css";

/** The part of the settings this screen changes; the rest is the developer's. */
interface Choice {
  slots: string[];
  court: string;
  days_ahead: number;
}

const DAY_NAMES = {
  0: "pages.bookingSettings.days.today",
  1: "pages.bookingSettings.days.tomorrow",
  2: "pages.bookingSettings.days.dayAfter",
} as const;

function choiceOf({ slots, court, days_ahead }: Settings): Choice {
  return { slots, court, days_ahead };
}

function sameChoice(a: Choice, b: Choice): boolean {
  return (
    a.court === b.court &&
    a.days_ahead === b.days_ahead &&
    a.slots.length === b.slots.length &&
    a.slots.every((slot, index) => slot === b.slots[index])
  );
}

interface SlotGroupProps {
  label: string;
  slots: string[];
  chosen: string[];
  onToggle: (slot: string) => void;
}

/** One part of the day: a toggle per slot, numbered in the order it will be booked. */
function SlotGroup({ label, slots, chosen, onToggle }: SlotGroupProps) {
  const { t } = useTranslation();
  const f = useFormat();
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} className={styles.group}>
      <Overline id={id}>{label}</Overline>
      <div className={styles.slots}>
        {slots.map((slot) => {
          const order = chosen.indexOf(slot) + 1;
          return (
            <button
              key={slot}
              type="button"
              aria-pressed={order > 0}
              aria-label={
                order > 0
                  ? t("pages.bookingSettings.slots.chosen", { slot: f.slot(slot), order })
                  : f.slot(slot)
              }
              className={styles.slot}
              onClick={() => onToggle(slot)}
            >
              {order > 0 && (
                <span aria-hidden="true" className={styles.order}>
                  {order}
                </span>
              )}
              {f.slot(slot)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface BookingFormProps {
  saved: Settings;
  save: ReturnType<typeof useSaveSettings>;
  onUnsavedChange?: (unsaved: boolean) => void;
}

/**
 * The slots, court and day to book, changed on a draft until saved. The rest of the
 * settings goes back to the backend as it came, so the developer's values stay.
 */
function BookingForm({ saved, save, onUnsavedChange }: BookingFormProps) {
  const { t } = useTranslation();
  const f = useFormat();
  const [draft, setDraft] = useState(() => choiceOf(saved));
  const changed = !sameChoice(draft, choiceOf(saved));

  // A form that goes away takes its draft with it, so it leaves nothing unsaved behind.
  useEffect(() => {
    onUnsavedChange?.(changed);
    return () => onUnsavedChange?.(false);
  }, [changed, onUnsavedChange]);
  const noSlot = draft.slots.length === 0;
  const choices = slotChoices(draft.slots);

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate({ ...saved, ...draft });
  }

  function cancel() {
    setDraft(choiceOf(saved));
    save.reset();
  }

  function toggle(slot: string) {
    setDraft({ ...draft, slots: toggleSlot(draft.slots, slot) });
  }

  let note = <p className={styles.note}>{t("pages.bookingSettings.note")}</p>;
  if (save.isError) {
    note = <p className={styles.problem}>{errorMessage(t, save.error)}</p>;
  } else if (noSlot) {
    note = <p className={styles.problem}>{t("pages.bookingSettings.noSlot")}</p>;
  } else if (save.isSuccess && !changed) {
    note = <p className={styles.note}>{t("pages.bookingSettings.saved")}</p>;
  }

  return (
    <form className={styles.form} onSubmit={submit}>
      <Card as="section" aria-labelledby="slots-title" className={styles.section}>
        <div className={styles.heading}>
          <h2 id="slots-title" className={styles.title}>
            {t("pages.bookingSettings.slots.title")}
          </h2>
          <p className={styles.lead}>{t("pages.bookingSettings.slots.lead")}</p>
        </div>
        <SlotGroup
          label={t("pages.bookingSettings.slots.morning")}
          slots={choices.morning}
          chosen={draft.slots}
          onToggle={toggle}
        />
        <SlotGroup
          label={t("pages.bookingSettings.slots.afternoon")}
          slots={choices.afternoon}
          chosen={draft.slots}
          onToggle={toggle}
        />
      </Card>

      <Card as="section" aria-labelledby="place-title" className={styles.section}>
        <h2 id="place-title" className={styles.title}>
          {t("pages.bookingSettings.place.title")}
        </h2>
        <div className={styles.fields}>
          <label className={styles.field}>
            {t("pages.bookingSettings.place.court")}
            <select
              className={styles.select}
              value={draft.court}
              onChange={(event) => setDraft({ ...draft, court: event.target.value })}
            >
              {courtChoices(saved.court).map((court) => (
                <option key={court} value={court}>
                  {f.court(court)}
                </option>
              ))}
            </select>
          </label>
          <div className={styles.field}>
            <label className={styles.field}>
              {t("pages.bookingSettings.place.day")}
              <select
                className={styles.select}
                value={draft.days_ahead}
                aria-describedby="day-hint"
                onChange={(event) => setDraft({ ...draft, days_ahead: Number(event.target.value) })}
              >
                {DAYS_AHEAD.map((days) => (
                  <option key={days} value={days}>
                    {t(DAY_NAMES[days])}
                  </option>
                ))}
              </select>
            </label>
            <p id="day-hint" className={styles.hint}>
              {t("pages.bookingSettings.place.dayHint")}
            </p>
          </div>
        </div>
      </Card>

      <div className={styles.bar}>
        <div aria-live="polite">{note}</div>
        <div className={styles.buttons}>
          <Button onClick={cancel} disabled={!changed || save.isPending}>
            {t("pages.bookingSettings.cancel")}
          </Button>
          <Button type="submit" variant="primary" disabled={!changed || noSlot || save.isPending}>
            {t(save.isPending ? "pages.bookingSettings.saving" : "pages.bookingSettings.save")}
          </Button>
        </div>
      </div>
    </form>
  );
}

/** A key that changes when the saved choice does, so the draft starts again from it. */
function savedKey(settings: Settings): string {
  return JSON.stringify(choiceOf(settings));
}

interface BookingSettingsPageProps {
  /** Told whether the form holds changes not saved yet, for a screen that leads on from it. */
  onUnsavedChange?: (unsaved: boolean) => void;
}

/** Choose the slots, court and day to book; they apply from the next run. */
export function BookingSettingsPage({ onUnsavedChange }: BookingSettingsPageProps) {
  const settings = useSettings();
  const save = useSaveSettings();
  return (
    <QueryView query={settings}>
      {(saved) => (
        <BookingForm
          key={savedKey(saved)}
          saved={saved}
          save={save}
          onUnsavedChange={onUnsavedChange}
        />
      )}
    </QueryView>
  );
}
