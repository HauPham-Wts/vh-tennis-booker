/**
 * Short words for why a slot or a run failed. The engine writes its reasons in English
 * (flow.py, runner.py); the known ones read as a few words here, the rest point to the
 * activity log, which keeps the engine's own text.
 */
import type { TFunction } from "i18next";
import type { Formatter } from "./useFormat";

type Phrase = (t: TFunction, f: Formatter, match: RegExpExecArray) => string;

/** The reasons the engine gives, as it writes them, and their words. */
const REASONS: [RegExp, Phrase][] = [
  [/^Slot .+ is fully booked$/, (t) => t("reasons.slotFull")],
  [
    /^Court (.+) is fully booked$/,
    (t, f, match) => t("reasons.courtFull", { court: f.court(match[1] ?? "") }),
  ],
  [
    /^The app refused the booking: (.*)$/s,
    (t, _f, match) => t("reasons.refused", { message: match[1] ?? "" }),
  ],
  [/ not open after \d+ attempt/, (t) => t("reasons.notOpen")],
  [/ but the next screen did not appear$/, (t) => t("reasons.stuck")],
  [/^Another run is in progress/, (t) => t("reasons.busy")],
];

/** Return a few words for an engine reason; an unknown one says to see the activity log. */
export function failureReason(t: TFunction, f: Formatter, reason: string | null): string {
  for (const [pattern, phrase] of REASONS) {
    const match = reason === null ? null : pattern.exec(reason);
    if (match !== null) {
      return phrase(t, f, match);
    }
  }
  return t("reasons.other");
}
