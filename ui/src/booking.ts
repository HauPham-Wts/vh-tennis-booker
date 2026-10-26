/**
 * The choices of the booking settings. The developer keeps them in step with the Vinhomes
 * app: its slots, sports and courts change only when the app does, and then this file does
 * too.
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

/** The sports to book, as config.toml names them, in the order of the app's utilities list. */
export const SPORTS = [
  "tennis",
  "multi",
  "volleyball",
  "table-tennis",
  "basketball",
  "football",
  "pickleball",
  "badminton",
] as const;

export type Sport = (typeof SPORTS)[number];

/** A court as the app names it on its court list, and the label that tells it apart. */
export interface Court {
  name: string;
  label: string;
}

/** The courts of each sport at Origami (field notes, "Other sports"). */
export const COURTS: Record<Sport, readonly Court[]> = {
  tennis: [
    { name: "S6 - Sân tennis", label: "S6" },
    { name: "S8 - Sân tennis", label: "S8" },
    { name: "S9 - Sân tennis", label: "S9" },
    { name: "S10 - Sân tennis", label: "S10" },
  ],
  multi: [
    { name: "S7 - Sân đa năng", label: "S7" },
    { name: "S9 - Sân đa năng", label: "S9" },
    { name: "S10 - Sân đa năng", label: "S10" },
  ],
  volleyball: [
    { name: "S8 - Sân bóng chuyền hơi", label: "S8" },
    { name: "S9 - Sân bóng chuyền hơi", label: "S9" },
    { name: "S10 - Sân bóng chuyền hơi 01", label: "S10 · 01" },
    { name: "S10 - Sân bóng chuyền hơi 02", label: "S10 · 02" },
  ],
  "table-tennis": [{ name: "S5 - Sân tập bóng bàn 03", label: "S5" }],
  basketball: [
    { name: "S6 - Sân bóng rổ tập ném 01", label: "S6 · tập ném 01" },
    { name: "S6 - Sân bóng rổ tập ném 02", label: "S6 · tập ném 02" },
    { name: "S8 - Sân bóng rổ nửa sân", label: "S8 · nửa sân" },
    { name: "S9 - Sân bóng rổ tập ném 01", label: "S9 · tập ném 01" },
    { name: "S9 - Sân bóng rổ tập ném 02", label: "S9 · tập ném 02" },
    { name: "S10 - Sân bóng rổ nửa sân 03", label: "S10 · nửa sân 03" },
    { name: "S10 - Sân tập bóng rổ 01", label: "S10 · tập 01" },
  ],
  football: [
    { name: "S5 - Sân bóng đá 5", label: "S5 · sân 5" },
    { name: "S5 - Sân bóng đá 7", label: "S5 · sân 7" },
  ],
  pickleball: [{ name: "S9 - Sân Pickleball", label: "S9" }],
  badminton: [
    { name: "S6 - Sân cầu lông", label: "S6" },
    { name: "S8 - Sân Cầu lông", label: "S8" },
    { name: "S10 - Sân cầu lông", label: "S10" },
  ],
};

/** The most slots to book: the app gives a flat two slots a day. */
export const MAX_SLOTS = 2;

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

/**
 * Turn a slot off, or on as the last one booked: the list's order is the booking order.
 * With two slots chosen another one is not added; more set by hand stay until turned off.
 */
export function toggleSlot(chosen: readonly string[], slot: string): string[] {
  if (chosen.includes(slot)) {
    return chosen.filter((other) => other !== slot);
  }
  return chosen.length >= MAX_SLOTS ? [...chosen] : [...chosen, slot];
}

/** Return whether `value` is a sport the run books. */
export function isSport(value: string): value is Sport {
  return (SPORTS as readonly string[]).includes(value);
}

/** Return the courts of `sport` to offer, and the one the settings hold if it is not one. */
export function courtChoices(sport: string, current: string): string[] {
  const courts = isSport(sport) ? COURTS[sport].map((court) => court.name) : [];
  return courts.includes(current) ? courts : [...courts, current];
}

/** Return the court to book when `sport` is chosen: the first of its list. */
export function firstCourt(sport: Sport): string {
  return COURTS[sport][0]?.name ?? "";
}

/** Return the sport and label of the court the app names `name`, if it is on a list. */
export function findCourt(name: string): { sport: Sport; label: string } | undefined {
  for (const sport of SPORTS) {
    const court = COURTS[sport].find((item) => item.name === name);
    if (court !== undefined) {
      return { sport, label: court.label };
    }
  }
  return undefined;
}
