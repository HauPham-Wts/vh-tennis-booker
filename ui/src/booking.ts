/**
 * The choices of the booking settings. The subdivisions, sports and courts come from
 * `catalog.json`, which `tools/export_openapi.py` writes from the backend's catalog.py; the
 * slots change only when the app does, and then this file does too.
 */
import catalog from "./catalog.json";
import { slotStart } from "./format";
import texts from "./i18n/locales/vi.json";

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

/** A sport the language files name, as config.toml keys it. */
export type Sport = keyof typeof texts.sports;

/** A court as the app names it on its court list, and the label that tells it apart. */
export interface Court {
  name: string;
  label: string;
}

/** A sport of a subdivision, with its courts in the order to offer them. */
export interface CatalogSport {
  id: string;
  courts: Court[];
}

/** A subdivision, with the sports its accounts see in the order of the app's list. */
export interface Subdivision {
  id: string;
  name: string;
  sports: CatalogSport[];
}

/** Every subdivision, Origami first: the one shown when nothing tells another. */
export const SUBDIVISIONS: readonly Subdivision[] = catalog;

const ORIGAMI = SUBDIVISIONS[0] as Subdivision;

/** Return the subdivision keyed `id`, or undefined for one not in the catalog. */
export function subdivisionOf(id: string | undefined): Subdivision | undefined {
  return SUBDIVISIONS.find((item) => item.id === id);
}

/**
 * Return the subdivision to show: the one the settings name, else the one the account told
 * last, else Origami.
 */
export function shownSubdivision(chosen: string, told: string | undefined): Subdivision {
  return subdivisionOf(chosen) ?? subdivisionOf(told) ?? ORIGAMI;
}

/** Return the sports to offer in `subdivision`, and the one the settings hold if not one. */
export function sportChoices(subdivision: Subdivision, current: string): string[] {
  const sports = subdivision.sports.map((sport) => sport.id);
  return sports.includes(current) ? sports : [...sports, current];
}

/** Return the courts of `sport` in `subdivision`, and the one the settings hold if not one. */
export function courtChoices(subdivision: Subdivision, sport: string, current: string): string[] {
  const found = subdivision.sports.find((item) => item.id === sport);
  const courts = found === undefined ? [] : found.courts.map((court) => court.name);
  return courts.includes(current) ? courts : [...courts, current];
}

/** Return the court to book when `sport` is chosen in `subdivision`: the first of its list. */
export function firstCourt(subdivision: Subdivision, sport: string): string {
  return subdivision.sports.find((item) => item.id === sport)?.courts[0]?.name ?? "";
}

/**
 * Return the settings that `target` takes when it is chosen: the sport the settings hold if
 * `target` has it, else its first sport, with that sport's first court.
 */
export function inSubdivision(
  target: Subdivision,
  sport: string,
): { subdivision: string; sport: string; court: string } {
  const kept = target.sports.some((item) => item.id === sport);
  const chosen = kept ? sport : (target.sports[0]?.id ?? sport);
  return { subdivision: target.id, sport: chosen, court: firstCourt(target, chosen) };
}

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

/** Return whether `value` is a sport the language files name. */
export function isSport(value: string): value is Sport {
  return Object.hasOwn(texts.sports, value);
}

/** Return the subdivision, sport and label of the court the app names `name`, if listed. */
export function findCourt(
  name: string,
): { subdivision: Subdivision; sport: Sport; label: string } | undefined {
  for (const subdivision of SUBDIVISIONS) {
    for (const sport of subdivision.sports) {
      const court = sport.courts.find((item) => item.name === name);
      if (court !== undefined && isSport(sport.id)) {
        return { subdivision, sport: sport.id, label: court.label };
      }
    }
  }
  return undefined;
}
