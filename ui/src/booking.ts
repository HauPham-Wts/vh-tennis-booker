/**
 * The choices of the booking settings. The developer keeps them in step with the Vinhomes
 * app: its slots and courts change only when the app does, and then this file does too.
 */
import { slotStart } from "./format";

/** The slots the app offers each day (06-12 and 14-21), as config.toml writes them. */
export const SLOTS = [
  "06:00 - 07:00",
  "07:00 - 08:00",
  "08:00 - 09:00",
  "09:00 - 10:00",
  "10:00 - 11:00",
  "11:00 - 12:00",
  "14:00 - 15:00",
  "15:00 - 16:00",
  "16:00 - 17:00",
  "17:00 - 18:00",
  "18:00 - 19:00",
  "19:00 - 20:00",
  "20:00 - 21:00",
] as const;

/** The courts of the venue, as the app names them on its court list. */
export const COURTS = [
  "S6 - Sân tennis",
  "S8 - Sân tennis",
  "S9 - Sân tennis",
  "S10 - Sân tennis",
] as const;

/** How many days after today a booking may be for (the app opens two days ahead). */
export const DAYS_AHEAD = [0, 1, 2] as const;

/** Slots that start before this are the morning ones. */
const NOON = "12:00";

/** The slots to offer, by part of the day. */
export interface SlotChoices {
  morning: string[];
  afternoon: string[];
}

/**
 * Return the slots to offer: the app's, and any other the settings hold, in time order.
 * A slot the developer set by hand is shown, so saving never drops it unseen.
 */
export function slotChoices(chosen: readonly string[]): SlotChoices {
  const all = [...new Set<string>([...SLOTS, ...chosen])].sort();
  return {
    morning: all.filter((slot) => slotStart(slot) < NOON),
    afternoon: all.filter((slot) => slotStart(slot) >= NOON),
  };
}

/** Turn a slot off, or on as the last one booked: the list's order is the booking order. */
export function toggleSlot(chosen: readonly string[], slot: string): string[] {
  return chosen.includes(slot) ? chosen.filter((other) => other !== slot) : [...chosen, slot];
}

/** Return the courts to offer: the venue's, and the one the settings hold if it is not one. */
export function courtChoices(current: string): string[] {
  const courts: string[] = [...COURTS];
  return courts.includes(current) ? courts : [...courts, current];
}
