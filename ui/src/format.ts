/**
 * Formatting of the backend's values for the screens.
 *
 * The backend sends local wall-clock times without a time zone (`2026-10-14T06:00:06.123`,
 * `2026-10-16`). `new Date(text)` would read a date alone as UTC and a date with a time in
 * this machine's zone, so the parts are read from the text instead and never shifted.
 */

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
