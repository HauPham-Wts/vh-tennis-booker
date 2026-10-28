import type { TFunction } from "i18next";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { type Court, findCourt, isCourtKind } from "./booking";
import {
  courtName,
  dayPeriod,
  formatClock,
  formatDay,
  formatDecimal,
  formatShortDate,
  formatShortDay,
  formatSlot,
  formatTime,
  relativeDay,
  slotStart,
} from "./format";
import { DEFAULT_LANGUAGE, LANGUAGES, type Language } from "./i18n";

/** Return "BE7 · tập ném 01": the block, then the kind in the current language and number. */
function formatCourtLabel(t: TFunction, court: Court): string {
  const kind = isCourtKind(court.kind) ? t(`courtKinds.${court.kind}`) : court.kind;
  const rest = [kind, court.number].filter((part) => part !== "").join(" ");
  return rest === "" ? court.code : `${court.code} · ${rest}`;
}

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
      /** "T4 14/10", "Wed 14 Oct". */
      shortDay: (text: string) => formatShortDay(text, language),
      /** "14/10", "14 Oct". */
      shortDate: (text: string) => formatShortDate(text, language),
      /** "06:00:06". */
      clock: formatClock,
      /** "06:00". */
      time: formatTime,
      /** "7,0 giây", "7.0 s". */
      seconds: (value: number) => t("format.seconds", { value: formatDecimal(value, language) }),
      /**
       * When a time falls, from `today` ("2026-10-15"): "sáng nay", "sáng mai", "chiều hôm
       * qua", else "sáng Thứ Hai 12/10"; a text it cannot read stays as it is.
       */
      when: (text: string, today: string) => {
        const period = dayPeriod(text);
        if (period === null) {
          return text;
        }
        const words = t(`format.period.${period}`);
        const near = relativeDay(text, today);
        return near === null
          ? t("format.when.other", { period: words, day: formatDay(text, language) })
          : t(`format.when.${near}`, { period: words });
      },
      /** "18:00–19:00". */
      slot: formatSlot,
      /** "18:00". */
      slotStart,
      /**
       * "S8 · nửa sân", "S8 · half court": what tells a court in the catalog from the others
       * of its sport, its kind in the current language; "S1" for "S1 - Sân tennis", a court
       * not in it.
       */
      courtLabel: (court: string) => {
        const known = findCourt(court)?.court;
        return known === undefined ? courtName(court) : formatCourtLabel(t, known);
      },
      /**
       * "Tennis S6", "Bóng rổ S8 · nửa sân": the sport and label of a court in the catalog;
       * "S1" for "S1 - Sân tennis", a court not in it.
       */
      court: (court: string) => {
        const known = findCourt(court);
        if (known === undefined) {
          return courtName(court);
        }
        const label = formatCourtLabel(t, known.court);
        return t("format.court", { sport: t(`sports.${known.sport}`), court: label });
      },
    }),
    [t, language],
  );
}

/** The formatting functions of one language, as `useFormat` returns them. */
export type Formatter = ReturnType<typeof useFormat>;
