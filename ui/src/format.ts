/**
 * Formatting of the backend's values for the screens.
 *
 * The backend sends local wall-clock times without a time zone (`2026-10-14T06:00:06.123`,
 * `2026-10-16`). `new Date(text)` would read a date alone as UTC and a date with a time in
 * this machine's zone, so the parts are read from the text instead and never shifted.
 * A text that cannot be read is shown as it is: formatting never throws.
 *
 * Words around the values ("giây", "Tháng") live in the language files; `useFormat` adds
 * them. Times use 24 hours in both languages, as the Vinhomes app shows its slots.
 */
import type { Language } from "./i18n";

/** A local date and time as the backend wrote it; the time is 0:00:00 for a date alone. */
export interface LocalTime {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
}

const LOCAL_TIME = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?$/;

/** Read a backend date or date-time; anything else gives null. */
export function parseLocal(text: string): LocalTime | null {
  const match = LOCAL_TIME.exec(text);
  if (match === null) {
    return null;
  }
  const [, year, month, day, hour = "0", minute = "0", second = "0"] = match;
  const parts = {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second),
  };
  // Reject dates that do not exist, such as 2026-02-30.
  const check = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  if (check.getUTCMonth() !== parts.month - 1 || check.getUTCDate() !== parts.day) {
    return null;
  }
  if (parts.hour > 23 || parts.minute > 59 || parts.second > 59) {
    return null;
  }
  return parts;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** The day of `time` at midnight UTC, so Intl names its weekday and month unshifted. */
function utcDay(time: LocalTime): Date {
  return new Date(Date.UTC(time.year, time.month - 1, time.day));
}

function weekday(time: LocalTime, language: Language): string {
  // "Thứ Tư" in Vietnamese; "Wed" in English, where the date follows as "14 Oct".
  const width = language === "vi" ? "long" : "short";
  return new Intl.DateTimeFormat(language, { weekday: width, timeZone: "UTC" }).format(
    utcDay(time),
  );
}

function dayMonth(time: LocalTime, language: Language): string {
  if (language === "vi") {
    // Intl writes "14-10" in Vietnamese; the app and its users write 14/10.
    return `${pad(time.day)}/${pad(time.month)}`;
  }
  const month = new Intl.DateTimeFormat("en", { month: "short", timeZone: "UTC" }).format(
    utcDay(time),
  );
  // "14 Oct": "10/14" or "14/10" would each be misread by some English readers.
  return `${time.day} ${month}`;
}

/** Format a date as day and month: "14/10", "14 Oct". */
export function formatShortDate(text: string, language: Language): string {
  const time = parseLocal(text);
  return time === null ? text : dayMonth(time, language);
}

/** Format a date with its weekday: "Thứ Tư 14/10", "Wed 14 Oct". */
export function formatDay(text: string, language: Language): string {
  const time = parseLocal(text);
  return time === null ? text : `${weekday(time, language)} ${dayMonth(time, language)}`;
}

/** Format a date-time as day, month and minutes: "12/10 06:00", "12 Oct 06:00". */
export function formatDateTime(text: string, language: Language): string {
  const time = parseLocal(text);
  return time === null ? text : `${dayMonth(time, language)} ${pad(time.hour)}:${pad(time.minute)}`;
}

/** Format the time of a date-time to the second: "06:00:06". */
export function formatClock(text: string): string {
  const time = parseLocal(text);
  return time === null ? text : `${pad(time.hour)}:${pad(time.minute)}:${pad(time.second)}`;
}

/** Format the time of a date-time to the minute: "06:00". */
export function formatTime(text: string): string {
  const time = parseLocal(text);
  return time === null ? text : `${pad(time.hour)}:${pad(time.minute)}`;
}

/** Format a number with one decimal in the language's style: "7,0", "7.0". */
export function formatDecimal(value: number, language: Language): string {
  return new Intl.NumberFormat(language, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

/** The part of the day a time falls in; its word is `format.period.*` in the language files. */
export type DayPeriod = "morning" | "afternoon" | "evening";

/** Return the part of the day of a date-time: before 12:00, before 18:00, or later. */
export function dayPeriod(text: string): DayPeriod | null {
  const time = parseLocal(text);
  if (time === null) {
    return null;
  }
  if (time.hour < 12) {
    return "morning";
  }
  return time.hour < 18 ? "afternoon" : "evening";
}

/** A day named by its distance from today. */
export type RelativeDay = "yesterday" | "today" | "tomorrow";

const DAY_MS = 24 * 60 * 60 * 1000;

/** Name the day of `text` from `today` (both as the backend writes them), or null. */
export function relativeDay(text: string, today: string): RelativeDay | null {
  const time = parseLocal(text);
  const base = parseLocal(today);
  if (time === null || base === null) {
    return null;
  }
  const days = Math.round((utcDay(time).getTime() - utcDay(base).getTime()) / DAY_MS);
  if (days === -1) {
    return "yesterday";
  }
  if (days === 0) {
    return "today";
  }
  return days === 1 ? "tomorrow" : null;
}

/** Return today's date on this machine, in the backend's form ("2026-10-15"). */
export function localToday(now: Date = new Date()): string {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

const HH_MM = /^(\d{1,2}):(\d{2})$/;
const DAY_MINUTES = 24 * 60;

/** Return a config time ("06:00") `minutes` later, round the clock; another text as it is. */
export function addMinutes(time: string, minutes: number): string {
  const match = HH_MM.exec(time);
  if (match === null) {
    return time;
  }
  const total = (Number(match[1]) * 60 + Number(match[2]) + minutes) % DAY_MINUTES;
  const wrapped = total < 0 ? total + DAY_MINUTES : total;
  return `${pad(Math.floor(wrapped / 60))}:${pad(wrapped % 60)}`;
}

/** Write a slot as "18:00–19:00"; the app and the config write "18:00 - 19:00". */
export function formatSlot(slot: string): string {
  return slot.replace(/\s*-\s*/, "–");
}

/** Return the start of a slot ("18:00"), for short lists. */
export function slotStart(slot: string): string {
  return slot.split("-", 1)[0]?.trim() ?? slot;
}

/** Return a court's short name: "S6" from "S6 - Sân tennis"; other names stay whole. */
export function courtName(court: string): string {
  const [name = ""] = court.split(" - ", 1);
  return name.trim() === "" ? court : name.trim();
}
