/**
 * Plain words for every step of the activity log, as the Activity screen and the live
 * Overview show them. The words live in `steps.*` of the language files; a step whose
 * value is missing gets a sentence without it, never "undefined".
 */
import type { TFunction } from "i18next";
import type { Step, StepKind } from "./api/types";
import type { Formatter } from "./useFormat";

/** How a step is marked: ✓ in stamp blue, ✕ in orange-red, the 06:00 moment, or nothing. */
export type StepTone = "booked" | "failed" | "moment" | "plain";

export interface StepMessage {
  text: string;
  /** A muted addition after the text: the time a slot took. */
  extra?: string;
  /** The engine's own English words (a reason, an error), for the technical details. */
  detail?: string;
  tone: StepTone;
}

type Data = Step["data"];

/** Return a non-empty text value, or undefined. */
function text(data: Data, key: string): string | undefined {
  const value = data[key];
  return typeof value === "string" && value !== "" ? value : undefined;
}

/** Return a finite number value, or undefined. */
function number(data: Data, key: string): number | undefined {
  const value = data[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

/** Return the length of a list value, or undefined. */
function length(data: Data, key: string): number | undefined {
  const value = data[key];
  return Array.isArray(value) ? value.length : undefined;
}

const TRIGGERS = ["scheduled", "dry_run", "manual", "setup"] as const;
const SETUP_ITEMS = ["mumu_installed", "mumu_screen", "wake_timers", "app_installed"] as const;
const SETUP_STATUSES = ["ok", "fixed", "fixable", "user", "unknown"] as const;

/** The names of the subdivisions, the same in every language (catalog.py). */
const SUBDIVISION_NAMES: Record<string, string> = { origami: "Origami", bs: "BS" };

function known<T extends string>(values: readonly T[], value: string | undefined): T | undefined {
  return values.find((candidate) => candidate === value);
}

interface Tools {
  t: TFunction;
  f: Formatter;
}

/** The name of whoever started a run, such as "chạy thử". */
function triggerName({ t }: Tools, data: Data): string {
  return t(`triggers.${known(TRIGGERS, text(data, "trigger")) ?? "unknown"}`);
}

/** The time a slot took, when the step has it. */
function took({ f }: Tools, data: Data): string | undefined {
  const seconds = number(data, "seconds");
  return seconds === undefined ? undefined : f.seconds(seconds);
}

type Describe = (tools: Tools, data: Data) => StepMessage;

/** One message per step kind; a kind added to the backend fails the type check here. */
const MESSAGES: Record<StepKind, Describe> = {
  run_started: ({ t }, data) => {
    const trigger = known(["scheduled", "dry_run", "manual"] as const, text(data, "trigger"));
    return { text: t(`steps.run_started.${trigger ?? "other"}`), tone: "plain" };
  },
  device_ready: ({ t }) => ({ text: t("steps.device_ready"), tone: "plain" }),
  app_ready: ({ t }) => ({ text: t("steps.app_ready"), tone: "plain" }),
  account_subdivision: ({ t }, data) => {
    const subdivision = known(Object.keys(SUBDIVISION_NAMES), text(data, "subdivision"));
    return {
      text:
        subdivision === undefined
          ? t("steps.account_subdivision.plain")
          : t("steps.account_subdivision.full", { name: SUBDIVISION_NAMES[subdivision] }),
      tone: "plain",
    };
  },
  waiting: ({ t, f }, data) => {
    const until = text(data, "until");
    return {
      text:
        until === undefined
          ? t("steps.waiting.plain")
          : t("steps.waiting.full", { time: f.clock(until) }),
      tone: "plain",
    };
  },
  booking_started: ({ t, f }, data) => {
    const date = text(data, "date");
    const court = text(data, "court");
    return {
      text:
        date === undefined || court === undefined
          ? t("steps.booking_started.plain")
          : t("steps.booking_started.full", { day: f.day(date), court: f.court(court) }),
      tone: "moment",
    };
  },
  slot_started: ({ t, f }, data) => {
    const slot = text(data, "slot");
    const round = number(data, "round");
    const rounds = number(data, "rounds");
    return {
      text:
        slot === undefined || round === undefined || rounds === undefined
          ? t("steps.slot_started.plain")
          : t("steps.slot_started.full", { round, rounds, slot: f.slot(slot) }),
      tone: "plain",
    };
  },
  calendar_opened: ({ t }, data) => {
    const attempt = number(data, "attempt");
    return {
      text:
        attempt === undefined || attempt <= 1
          ? t("steps.calendar_opened.first")
          : t("steps.calendar_opened.again", { attempt }),
      tone: "plain",
    };
  },
  date_selected: ({ t, f }, data) => {
    const date = text(data, "date");
    return {
      text:
        date === undefined
          ? t("steps.date_selected.plain")
          : t("steps.date_selected.full", { day: f.day(date) }),
      tone: "plain",
    };
  },
  slot_selected: ({ t, f }, data) => {
    const slot = text(data, "slot");
    return {
      text:
        slot === undefined
          ? t("steps.slot_selected.plain")
          : t("steps.slot_selected.full", { slot: f.slot(slot) }),
      tone: "plain",
    };
  },
  court_selected: ({ t, f }, data) => {
    const court = text(data, "court");
    return {
      text:
        court === undefined
          ? t("steps.court_selected.plain")
          : t("steps.court_selected.full", { court: f.court(court) }),
      tone: "plain",
    };
  },
  terms_accepted: ({ t }) => ({ text: t("steps.terms_accepted"), tone: "plain" }),
  slot_booked: (tools, data) => {
    const { t, f } = tools;
    const slot = text(data, "slot");
    // A dry run stops before "Xác nhận": it reached the confirmation, it booked nothing.
    const dry = data["dry_run"] === true;
    const words =
      slot === undefined
        ? t(dry ? "steps.slot_booked.dry_plain" : "steps.slot_booked.plain")
        : t(dry ? "steps.slot_booked.dry" : "steps.slot_booked.full", { slot: f.slot(slot) });
    return { text: words, extra: took(tools, data), tone: "booked" };
  },
  slot_failed: (tools, data) => {
    const { t, f } = tools;
    const slot = text(data, "slot");
    return {
      text:
        slot === undefined
          ? t("steps.slot_failed.plain")
          : t("steps.slot_failed.full", { slot: f.slot(slot) }),
      extra: took(tools, data),
      detail: text(data, "reason"),
      tone: "failed",
    };
  },
  run_finished: ({ t }, data) => {
    const status = text(data, "status");
    const booked = number(data, "booked");
    const total = number(data, "total");
    const error = text(data, "error");
    if (status === "interrupted") {
      return { text: t("steps.run_finished.interrupted"), detail: error, tone: "failed" };
    }
    if (error !== undefined) {
      return { text: t("steps.run_finished.error"), detail: error, tone: "failed" };
    }
    if (booked === undefined || total === undefined) {
      return { text: t("steps.run_finished.plain"), tone: "plain" };
    }
    if (booked === 0) {
      return { text: t("steps.run_finished.none"), tone: "failed" };
    }
    return {
      text: t("steps.run_finished.done", { booked, total }),
      tone: booked === total ? "booked" : "failed",
    };
  },
  lock_cleared: ({ t }) => ({ text: t("steps.lock_cleared"), tone: "plain" }),
  lock_waiting: (tools, data) => ({
    text: tools.t("steps.lock_waiting", { trigger: triggerName(tools, data) }),
    tone: "plain",
  }),
  lock_taken_over: (tools, data) => ({
    text: tools.t("steps.lock_taken_over", { trigger: triggerName(tools, data) }),
    tone: "failed",
  }),
  setup_started: ({ t }) => ({ text: t("steps.setup_started"), tone: "plain" }),
  setup_item: ({ t }, data) => {
    const item = known(SETUP_ITEMS, text(data, "item"));
    const status = known(SETUP_STATUSES, text(data, "status"));
    const detail = text(data, "detail");
    if (item === undefined || status === undefined) {
      return { text: t("steps.setup_item.plain"), detail, tone: "plain" };
    }
    const words = t("steps.setup_item.full", {
      item: t(`setup.items.${item}`),
      status: t(`setup.statuses.${status}`),
    });
    if (status === "ok" || status === "fixed") {
      return { text: words, detail, tone: "booked" };
    }
    return { text: words, detail, tone: status === "user" ? "failed" : "plain" };
  },
  setup_finished: ({ t }, data) => {
    const error = text(data, "error");
    const left = length(data, "left") ?? 0;
    if (error !== undefined) {
      return { text: t("steps.setup_finished.error"), detail: error, tone: "failed" };
    }
    if (left > 0) {
      return { text: t("steps.setup_finished.left", { count: left }), tone: "failed" };
    }
    return { text: t("steps.setup_finished.done"), tone: "booked" };
  },
  settings_saved: ({ t }, data) => {
    const count = length(data, "changed");
    return {
      text:
        count === undefined
          ? t("steps.settings_saved.plain")
          : t("steps.settings_saved.full", { count }),
      tone: "plain",
    };
  },
  schedule_enabled: ({ t }, data) => {
    const wake = text(data, "wake_at");
    const start = text(data, "start_at");
    return {
      text:
        wake === undefined || start === undefined
          ? t("steps.schedule_enabled.plain")
          : t("steps.schedule_enabled.full", { wake, start }),
      tone: "booked",
    };
  },
  schedule_disabled: ({ t }) => ({ text: t("steps.schedule_disabled"), tone: "plain" }),
};

/** Return the words for a step in the current language of `t` and `f`. */
export function stepMessage(t: TFunction, f: Formatter, step: Step): StepMessage {
  // The schema lists every kind, but a database written by a newer engine may hold more.
  const describe = (MESSAGES as Partial<Record<string, Describe>>)[step.kind];
  if (describe === undefined) {
    return { text: t("steps.other", { kind: step.kind }), tone: "plain" };
  }
  return describe({ t, f }, step.data);
}
