import { addMinutes } from "./format";

/** No dry run or auto setup may start until this long after the start (lock.py SCHEDULE_AFTER). */
const AFTER_START_MINUTES = 5;

/** Return when the quiet time before and after a booking ends: the start time + 5 minutes. */
export function quietEnd(start: string): string {
  return addMinutes(start, AFTER_START_MINUTES);
}
