import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  courtName,
  dayPeriod,
  formatClock,
  formatDateTime,
  formatDay,
  formatDecimal,
  formatShortDate,
  formatSlot,
  formatTime,
  monthParts,
  slotStart,
} from "./format";
import { DEFAULT_LANGUAGE, LANGUAGES, type Language } from "./i18n";

function asLanguage(language: string | undefined): Language {
  return LANGUAGES.find((known) => known === language) ?? DEFAULT_LANGUAGE;
}

/**
 * Return the formatting functions of `format.ts` in the current language, with the words
 * around the values ("7,0 giây") from the language files.
 */
export function useFormat() {
  const { t, i18n } = useTranslation();
  const language = asLanguage(i18n.resolvedLanguage);
  return useMemo(
    () => ({
      language,
      /** "Thứ Tư 14/10", "Wed 14 Oct". */
      day: (text: string) => formatDay(text, language),
      /** "14/10", "14 Oct". */
      shortDate: (text: string) => formatShortDate(text, language),
      /** "12/10 06:00", "12 Oct 06:00". */
      dateTime: (text: string) => formatDateTime(text, language),
      /** "06:00:06". */
      clock: formatClock,
      /** "06:00". */
      time: formatTime,
      /** "7,0 giây", "7.0 s". */
      seconds: (value: number) => t("format.seconds", { value: formatDecimal(value, language) }),
      /** "Tháng 10/2026", "October 2026"; a text it cannot read stays as it is. */
      month: (text: string) => {
        const parts = monthParts(text, language);
        return parts === null ? text : t("format.month", { name: parts.name, year: parts.year });
      },
      /** "sáng", "morning"; empty for a text it cannot read. */
      period: (text: string) => {
        const period = dayPeriod(text);
        return period === null ? "" : t(`format.period.${period}`);
      },
      /** "18:00–19:00". */
      slot: formatSlot,
      /** "18:00". */
      slotStart,
      /** "S6". */
      court: courtName,
    }),
    [t, language],
  );
}

/** The formatting functions of one language, as `useFormat` returns them. */
export type Formatter = ReturnType<typeof useFormat>;
